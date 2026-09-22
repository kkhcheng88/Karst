"""Offline benchmark of the daily intake (``daily.refresh_scope``), phase by phase.

Synthetic members only: a fake Longbridge client and a fake RSS getter, each with an
injected per-call delay and failure rate, write into a throwaway data directory. No
network, no real security, no cloud state. Phases are measured by wrapping the
functions the daily path already calls (exclusive time, so nested calls are not
counted twice); the daily path itself is not modified.

    python -m karst.daily_bench --members 50 --price-delay 0.05 --news-delay 0.3
"""
import argparse
import datetime as dt
import json
import random
import statistics
import sys
import tempfile
import time
from pathlib import Path

from . import bars, daily, knowledge, service, store as store_module
from .fetch import longbridge, news
from .fetch.registry import EvidenceRegistry

UNIVERSE = 'bench-monitoring'
# (owner, attribute, phase). Exclusive time: a phase excludes the phases it calls.
PHASES = (
    (longbridge, 'fetch', 'fetch_prices'),
    (news, 'fetch', 'fetch_news'),
    (EvidenceRegistry, 'register', 'register_evidence'),
    (EvidenceRegistry, 'records', 'read_registry'),
    (service, '_index', 'index_store'),
    (service, 'prepare_research', 'packet'),
    (bars, 'series_from_evidence', 'series_rebuild'),
    (service, 'plan_update', 'plan_update'),
    (service, 'get_research_protocol', 'protocol_load'),
    (daily, '_save_run', 'checkpoint'),
)


class Faults:
    def __init__(self, delay, failure_rate, rng):
        self.delay, self.failure_rate, self.rng = delay, failure_rate, rng

    def call(self, name):
        if self.delay:
            time.sleep(self.delay)
        if self.rng.random() < self.failure_rate:
            raise ConnectionError(f'injected failure: {name}')


class FakeLongbridge:
    """The four public quote tools; candles end yesterday so every bar is closed."""

    def __init__(self, faults, history_bars):
        self.faults, self.history_bars = faults, history_bars

    def quote(self, symbols):
        self.faults.call('quote')
        return [{'symbol': s, 'last_done': '100.0', 'volume': 1000} for s in symbols]

    def static_info(self, symbols):
        self.faults.call('static_info')
        return [{'symbol': s, 'currency': 'USD', 'exchange': 'NYSE'} for s in symbols]

    def calc_indexes(self, symbols, indexes):
        self.faults.call('calc_indexes')
        return [{'symbol': s, **{name: 1 for name in indexes}} for s in symbols]

    def history_candlesticks_by_date(self, symbol, period, adjust, start, end, sessions=None):
        self.faults.call('history_candlesticks_by_date')
        day, days = dt.date.today() - dt.timedelta(days=1), []
        first = dt.date.fromisoformat(start) if start else None
        while len(days) < self.history_bars and (first is None or day >= first):
            if day.weekday() < 5:
                days.append(day)
            day -= dt.timedelta(days=1)
        return [{'timestamp': f'{d}T04:00:00+00:00', 'open': 100 + i % 7, 'high': 102 + i % 7,
                 'low': 99 + i % 7, 'close': 101 + i % 7, 'volume': 1_000_000}
                for i, d in enumerate(reversed(days))]


def fake_feed(faults, items, tag, shared=True):
    """RSS getter: ``items`` dated articles per feed, unique per ticker and ``tag``."""
    def get(url):
        faults.call('rss')
        ticker = url.rsplit('=', 1)[-1] if 'yahoo' in url else url.split('%22')[1].split('+')[0]
        stamp = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        pub = stamp.strftime('%a, %d %b %Y %H:%M:%S GMT')
        entries = [(f'{ticker} {tag} {i}', f'https://example.invalid/{ticker}/{tag}/{i}')
                   for i in range(items)]
        if shared and items:
            entries.append((f'Market {tag}', f'https://example.invalid/market/{tag}'))
        body = ''.join(f'<item><title>{t}</title><link>{u}</link><pubDate>{pub}</pubDate>'
                       f'<description>synthetic</description></item>' for t, u in entries)
        return f'<rss><channel>{body}</channel></rss>'.encode()
    return get


def tickers(count):
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return ['ZZ' + letters[i // 26 % 26] + letters[i % 26] for i in range(count)]


class Profiler:
    def __init__(self):
        self.totals, self.calls, self.stack = {}, {}, []
        self.checkpoint_bytes = []
        self._saved = []

    def install(self):
        for owner, attribute, phase in PHASES:
            original = getattr(owner, attribute)
            self._saved.append((owner, attribute, original))
            setattr(owner, attribute, self._wrap(original, phase))

    def uninstall(self):
        for owner, attribute, original in reversed(self._saved):
            setattr(owner, attribute, original)
        self._saved.clear()

    def _wrap(self, function, phase):
        def timed(*args, **kwargs):
            self.stack.append(0.0)
            start = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                spent = time.perf_counter() - start
                children = self.stack.pop()
                if self.stack:
                    self.stack[-1] += spent
                self.totals[phase] = self.totals.get(phase, 0.0) + spent - children
                self.calls[phase] = self.calls.get(phase, 0) + 1
                if phase == 'checkpoint':
                    self.checkpoint_bytes.append(len(json.dumps(args[1], ensure_ascii=False)))
        return timed


def peak_rss():
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024  # Linux: KiB
    except ImportError:
        pass
    try:
        import psutil
        info = psutil.Process().memory_info()
        return getattr(info, 'peak_wset', None) or info.rss
    except ImportError:
        return None


def run(members, *, price_delay=0.0, news_delay=0.0, failure_rate=0.0, include_news=True,
        news_items=5, prior_news=20, history_bars=1000, seed=0):
    """Seed ``members`` synthetic securities, then time one ``refresh_scope``."""
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory(prefix='karst-bench-') as folder:
        root = Path(folder)
        state = store_module.init(root / service.DB_NAME)
        try:
            names = tickers(members)
            securities = [dict(security_id=f'NYSE:{t}', issuer_id=f'issuer:{t}', ticker=t,
                               name=f'{t} Holdings', exchange='NYSE', currency='USD') for t in names]
            clean = Faults(0.0, 0.0, rng)
            started = time.perf_counter()
            for security in securities:  # registration: full history + accumulated news
                service.refresh_sources(root, security, ['prices', 'news'], store=state,
                                        clients={'longbridge': FakeLongbridge(clean, history_bars),
                                                 'news_rss': fake_feed(clean, prior_news, 'prior')})
            seed_seconds = time.perf_counter() - started
            knowledge.save(state, 'universe', UNIVERSE, {
                'name': 'Benchmark', 'summary': 'Synthetic daily benchmark membership',
                'members': [dict(entity_id=s['security_id'], name=s['name'], kind='security',
                                 roles=['bench'], comparison_groups=[]) for s in securities],
                'sources': [{'title': 'Synthetic', 'url': 'https://example.invalid/bench'}]})
            rss_before = peak_rss()
            clients = {'longbridge': FakeLongbridge(Faults(price_delay, failure_rate, rng), history_bars),
                       'news_rss': fake_feed(Faults(news_delay if include_news else 0.0,
                                                    failure_rate if include_news else 0.0, rng),
                                             news_items if include_news else 0, 'today')}
            profiler = Profiler()
            profiler.install()
            started = time.perf_counter()
            try:
                receipt = daily.refresh_scope(state, root, UNIVERSE, clients=clients)
            finally:
                wall = time.perf_counter() - started
                profiler.uninstall()
        finally:
            state.connection.close()
    stamps = [dt.datetime.fromisoformat(r['checked_at'].replace('Z', '+00:00'))
              for r in receipt['results'] if 'checked_at' in r]
    measured = sum(profiler.totals.values())
    phases = {phase: {'seconds': round(profiler.totals.get(phase, 0.0), 4),
                      'calls': profiler.calls.get(phase, 0),
                      'share': round(profiler.totals.get(phase, 0.0) / wall, 4) if wall else None}
              for _, _, phase in PHASES}
    phases['other'] = {'seconds': round(wall - measured, 4), 'calls': None,
                       'share': round((wall - measured) / wall, 4) if wall else None}
    statuses = {}
    for result in receipt['results']:
        statuses[result['intake_status']] = statuses.get(result['intake_status'], 0) + 1
    return {'parameters': {'members': members, 'price_delay_per_call': price_delay,
                           'news_delay_per_feed': news_delay if include_news else 0.0,
                           'failure_rate': failure_rate, 'include_news': include_news,
                           'news_items_per_feed': news_items if include_news else 0,
                           'prior_news_per_feed': prior_news, 'history_bars': history_bars, 'seed': seed},
            'seed_seconds': round(seed_seconds, 3), 'refresh_seconds': round(wall, 3),
            'per_member_seconds': round(wall / members, 4),
            'phases': phases,
            'checkpoint': {'writes': len(profiler.checkpoint_bytes),
                           'final_bytes': profiler.checkpoint_bytes[-1] if profiler.checkpoint_bytes else 0,
                           'total_bytes_serialized': sum(profiler.checkpoint_bytes)},
            'intake_status': receipt['intake_status'], 'member_status': statuses,
            'shared_articles': len(receipt['news_candidates']),
            'bars_available_median': statistics.median(r.get('bars_available', 0) for r in receipt['results']),
            'history_recovered': sum(bool(r.get('history_recovered')) for r in receipt['results']),
            'span_seconds': (max(stamps) - min(stamps)).total_seconds() if stamps else None,
            'peak_rss_bytes': {'before_refresh': rss_before, 'after_refresh': peak_rss()}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--members', type=int, action='append', required=True,
                        help='member count; repeat for several runs (e.g. --members 10 --members 50)')
    parser.add_argument('--price-delay', type=float, default=0.0, help='seconds per Longbridge call (4 per member)')
    parser.add_argument('--news-delay', type=float, default=0.0, help='seconds per RSS feed (2 per member, parallel)')
    parser.add_argument('--failure-rate', type=float, default=0.0, help='probability each fake call fails')
    parser.add_argument('--no-news', action='store_true', help='news feeds return empty instantly')
    parser.add_argument('--news-items', type=int, default=5, help='new articles per feed today')
    parser.add_argument('--prior-news', type=int, default=20, help='articles per feed already registered')
    parser.add_argument('--history-bars', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--output', type=Path, help='write JSON here instead of stdout')
    args = parser.parse_args(argv)
    if not 0 <= args.failure_rate <= 1 or min(args.members) < 1:
        parser.error('failure rate must be 0..1 and members >= 1')
    results = [run(n, price_delay=args.price_delay, news_delay=args.news_delay,
                   failure_rate=args.failure_rate, include_news=not args.no_news,
                   news_items=args.news_items, prior_news=args.prior_news,
                   history_bars=args.history_bars, seed=args.seed) for n in args.members]
    text = json.dumps(results, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
