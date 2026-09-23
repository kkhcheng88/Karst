"""Weekly analyst-consensus snapshot (每週分析員預期快照) for the radar's estimate revisions.

Longbridge ``financial-consensus-detail`` with ``period_type=af`` returns, per fiscal
year, the consensus estimate of revenue, EBIT, net income and EPS (GAAP and
normalized). The vendor keeps no history of these numbers, so a revision needs our own
earlier copy: once per ISO week this module stores the unreported fiscal years of every
symbol in scope, one JSON line per symbol, at ``<data>/consensus/<YYYY-Www>.jsonl``.
A restart resumes the week; ``<week>.done.json`` marks it complete. Reported years and
forecast-vs-actual are fetched on demand, not stored (資料來源.md §四 10-0(d): the radar
is the cross-sectional scan product that may store multi-stock series).

Scope is every US main-board symbol at or above a market-cap floor, or an explicit list.
Quote data only; no account, position or order method is called.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import threading
import time
from pathlib import Path

from . import service
from .fetch import limits
from .fetch.common import load_env_file, utc_now, write_json

SOURCE = 'longbridge_consensus'
ENDPOINT = '/v1/quote/financial-consensus-detail'
MIN_CAP = 5e8           # USD; the narrative-member floor, so every radar candidate is covered
MAX_FAILED = 0.1        # a pass with more failures than this stays open for the next check
BATCH = 500             # static_info / calc_indexes batch size


def week_id(now=None):
    year, week, _ = (now or dt.datetime.now(dt.timezone.utc)).isocalendar()
    return f'{year}-W{week:02d}'


def counter_id(symbol):
    """``AAPL.US`` -> ``ST/US/AAPL``; a share-class dot stays in the ticker (``BRK.B.US``)."""
    ticker, market = symbol.rsplit('.', 1)
    return f'ST/{market}/{ticker}'


def forecasts(response):
    """The fiscal years not yet reported, each as ``{fiscal_year, period, estimates}``."""
    years = []
    for entry in (response or {}).get('list') or []:
        details = entry.get('details') or []
        if any(d.get('actual') not in ('', None) for d in details):
            continue
        estimates = {d['key']: float(d['estimate']) for d in details
                     if d.get('estimate') not in ('', None)}
        if estimates:
            years.append({'fiscal_year': entry.get('fiscal_year'),
                          'period': entry.get('period_text'), 'estimates': estimates})
    return years


def universe(context, min_cap=MIN_CAP):
    """``{symbol: market cap}`` for US main-board listings at or above ``min_cap``."""
    # ponytail: ETFs pass the floor (fund size counts as cap) and answer with no estimates:
    # about 1,200 wasted calls, 13 min a week. Filter by security type if the pass runs long.
    from longport.openapi import CalcIndex, Market, SecurityListCategory  # noqa: PLC0415
    listed = [row.symbol for row in limits.call(
        'longbridge', context.security_list, Market.US, SecurityListCategory.Overnight)]
    main = []
    for i in range(0, len(listed), BATCH):
        main += [row.symbol for row in limits.call('longbridge', context.static_info,
                                                   listed[i:i + BATCH])
                 if 'USMain' in str(row.board)]
    caps = {}
    for i in range(0, len(main), BATCH):
        for row in limits.call('longbridge', context.calc_indexes, main[i:i + BATCH],
                               [CalcIndex.TotalMarketValue]):
            if row.total_market_value is not None and float(row.total_market_value) >= min_cap:
                caps[row.symbol] = float(row.total_market_value)
    return caps


def _clients():
    from longport.openapi import Config, HttpClient, QuoteContext  # noqa: PLC0415
    from .fetch.longbridge import ENV_KEYS, credentials  # noqa: PLC0415
    values = credentials()
    if not values:
        raise RuntimeError('longbridge credentials missing')
    keys = [values[key] for key in ENV_KEYS]
    context = QuoteContext(Config.from_apikey(*keys, enable_print_quote_packages=False))
    return HttpClient.from_apikey(*keys), context


def snapshot(root, *, symbols=None, min_cap=MIN_CAP, week=None, http=None, context=None):
    """Complete one week's snapshot; returns its summary. A finished week is not refetched."""
    week = week or week_id()
    folder = Path(root) / 'consensus'
    lines, done = folder / f'{week}.jsonl', folder / f'{week}.done.json'
    if done.exists():
        return json.loads(done.read_text(encoding='utf-8'))
    started = utc_now()
    if http is None or (symbols is None and context is None):
        http, context = _clients()
    caps = universe(context, min_cap) if symbols is None else {s: None for s in symbols}
    have = set()
    if lines.exists():
        have = {json.loads(line)['symbol']
                for line in lines.read_text(encoding='utf-8').splitlines() if line.strip()}
    folder.mkdir(parents=True, exist_ok=True)
    failed = {}
    with open(lines, 'a', encoding='utf-8', newline='\n') as out:
        for symbol in sorted(set(caps) - have):
            path = f'{ENDPOINT}?counter_id={counter_id(symbol)}&period_type=af'
            try:
                response = limits.call(SOURCE, http.request, 'get', path)
            except Exception as exc:  # noqa: BLE001 - recorded per symbol, the pass goes on
                failed[symbol] = str(exc)[:200]
                continue
            out.write(json.dumps({'symbol': symbol, 'fetched_at': utc_now(),
                                  'market_cap': caps[symbol],
                                  'currency': (response or {}).get('currency') or None,
                                  'years': forecasts(response)}, ensure_ascii=False) + '\n')
            out.flush()
    stored = [json.loads(line) for line in lines.read_text(encoding='utf-8').splitlines()
              if line.strip()]
    summary = {'week': week, 'started_at': started, 'finished_at': utc_now(),
               'min_cap': None if symbols is not None else min_cap, 'scope': len(caps),
               'stored': len(stored), 'with_estimates': sum(1 for r in stored if r['years']),
               'failed': failed}
    if len(failed) <= MAX_FAILED * max(len(caps), 1):
        write_json(done, summary)
    return summary


def last_week(root):
    """The newest completed week id, or None."""
    marks = sorted((Path(root) / 'consensus').glob('*.done.json'))
    return marks[-1].name.split('.')[0] if marks else None


def run_weekly(root, *, days=(5, 6), interval=3600):
    """Background loop for the HTTP service: on the given UTC weekdays (Sat, Sun), finish
    this ISO week's snapshot. Checks at start and then every ``interval`` seconds."""
    def loop():
        while True:
            if dt.datetime.now(dt.timezone.utc).weekday() in days:
                try:
                    snapshot(root)
                except Exception as exc:  # noqa: BLE001 - the next check retries
                    print(f'karst consensus snapshot failed: {exc}', file=sys.stderr)
            time.sleep(interval)
    thread = threading.Thread(target=loop, name='karst-consensus-weekly', daemon=True)
    thread.start()
    return thread


def main(argv=None):
    parser = argparse.ArgumentParser(prog='python -m karst.consensus', description=__doc__)
    parser.add_argument('--data-dir', default=None)
    parser.add_argument('--symbols', default=None, help='comma list (AAPL.US,...); default: universe')
    parser.add_argument('--min-cap', type=float, default=MIN_CAP)
    parser.add_argument('--week', default=None, help='YYYY-Www; default: this ISO week (UTC)')
    args = parser.parse_args(argv)
    load_env_file()
    symbols = args.symbols.split(',') if args.symbols else None
    summary = snapshot(service.data_root(args.data_dir), symbols=symbols,
                       min_cap=args.min_cap, week=args.week)
    print(json.dumps({**summary, 'failed': len(summary['failed'])}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
