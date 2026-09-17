"""The source port: one landing shape and one status judgement for every adapter.

An adapter exposes ``KINDS`` (the evidence kinds it covers) and

    fetch(security, out_dir, *, since=None, client=None) -> list[LandedRecord]

It lands raw returns under ``<out_dir>/<source>/`` as before and reports one
record per landed representation: **which kind of evidence it is — the adapter
says so, nobody infers it downstream** — where it landed, when it was published
and fetched, what period it covers, and whether it came back ok / empty / error
and why. Vendor symbol conversion stays inside the adapter.

This is a shape, not a plugin framework: adding a source is adding one module
with ``KINDS`` and ``fetch``, and naming it in ``service.ADAPTERS``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .common import STATUSES

# Public tool method -> evidence kind. These are public tool names, NOT
# symbol-specific mappings; a broker tool that is not here cannot be registered
# at all (see registry.evidence_kind).
PUBLIC_KINDS = {
    'quote_company_profile': 'profile', 'quote_owner_plate': 'profile',
    'quote_market_snapshot': 'prices', 'quote_daily_short_volume': 'short_interest',
    'quote_short_interest': 'short_interest', 'quote_valuation_detail': 'valuation',
    'quote_financials_earnings_price_history': 'financials',
    'quote_insider_holder_list': 'ownership', 'quote_insider_trade_list': 'ownership',
    'quote_shareholders_institutional': 'ownership',
    'quote_research_analyst_consensus': 'consensus',
    'quote_research_rating_summary': 'ratings',
    'quote_research_morningstar_report': 'industry_report',
    'business_segments': 'financials', 'consensus': 'consensus',
    'forecast_eps': 'consensus', 'filings': 'filing_index',
    'finance_calendar': 'calendar', 'fund_holder': 'ownership',
    'shareholder': 'ownership', 'short_positions': 'short_interest',
    'quote': 'prices', 'history_candlesticks_by_date': 'prices',
    'static_info': 'profile', 'calc_indexes': 'prices',
    'industry_valuation': 'valuation', 'valuation': 'valuation',
    'valuation_history': 'valuation', 'security_facts': 'other_public',
    'institution_rating': 'ratings', 'institution_rating_history': 'ratings',
    'institutional_views': 'ratings',
}


@dataclass(frozen=True)
class LandedRecord:
    """What one adapter landed, in the adapter's own words.

    ``path`` is None for a metadata-only failure: the sidecar itself is the
    preserved diagnostic and no source body is invented.
    """
    kind: str
    path: Path | None
    meta_path: Path
    published_at: str | None = None
    fetched_at: str | None = None
    period: dict | None = None
    coverage: dict | None = None
    status: str = 'ok'
    status_reason: str | None = None

    def __post_init__(self):
        if not self.kind:
            raise ValueError('An adapter must name the evidence kind it landed')
        if self.status not in STATUSES:
            raise ValueError(f'status must be one of {STATUSES}: {self.status!r}')
        if self.status == 'ok' and self.path is None:
            raise ValueError('A landed record with status ok must name a landed file')
        if self.status != 'ok' and not self.status_reason:
            raise ValueError('empty/error must say why: "no data" and "fetch broke" differ')


def response_status(response):
    """ok / empty / error for one provider return, plus the reason and the error body.

    The single judgement: error envelopes first (error_code / error / ret_code),
    then emptiness. Adapters call this once when they land; the registry records
    the answer instead of parsing the body a second time.
    """
    error = None
    if isinstance(response, dict):
        if response.get('error_code') not in (None, 0, '0') or response.get('error'):
            error = response.get('error') if isinstance(response.get('error'), dict) else response
        elif 'ret_code' in response and response.get('ret_code') not in (0, '0', None):
            error = response
        if error is not None:
            return 'error', error, ('source returned an error envelope; a failed fetch is not '
                                    "'no data' (資料來源 §零)")
        body = response.get('data', response.get('result', response))
        if body in (None, [], {}, ''):
            return 'empty', None, "empty return: 'nothing to report' and 'not covered' are different"
        return 'ok', None, None
    if response in (None, [], '', ()):
        return 'empty', None, "empty return: 'nothing to report' and 'not covered' are different"
    return 'ok', None, None


def pair_staging(staging):
    """[(sidecar, [raw representations])]; the longest matching stem owns each landed file.

    Exhibits land beside their parent document with a longer stem, so a plain
    prefix test would give the parent both. Longest match keeps them apart.
    """
    metas = {path: path.name[: -len('.meta.json')]
             for path in sorted(Path(staging).rglob('*.meta.json'))}
    raws = {path: [] for path in metas}
    for path in sorted(Path(staging).rglob('*')):
        if not path.is_file() or path.name.endswith('.meta.json'):
            continue
        owner = max((meta for meta, stem in metas.items()
                     if meta.parent == path.parent and path.name.startswith(stem + '.')),
                    key=lambda meta: len(metas[meta]), default=None)
        if owner is not None:
            raws[owner].append(path)
    return [(meta, raws[meta]) for meta in metas]


def scan(directory, kind_for):
    """Every sidecar under ``directory`` -> one LandedRecord per landed representation.

    ``kind_for(meta)`` is the adapter's own declaration. Nothing is re-judged here:
    status, reason, times and coverage are read back from the sidecar the adapter wrote.
    """
    directory = Path(directory)
    if not directory.exists():
        return []
    records = []
    for meta_path, raws in pair_staging(directory):
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        kind = kind_for(meta)
        status = meta.get('status', 'ok')
        reason = meta.get('status_reason')
        if status != 'ok' and not reason:
            reason = f'adapter reported {status}; see known gaps and the preserved sidecar'
        if not raws and status == 'ok':
            raise ValueError(f'{meta_path}: sidecar says ok but nothing landed beside it')
        for raw in raws or [None]:
            records.append(LandedRecord(
                kind=kind, path=raw, meta_path=meta_path,
                published_at=meta.get('published_at'), fetched_at=meta.get('fetched_at'),
                period=meta.get('period'), coverage=meta.get('coverage', meta.get('period')),
                status=status, status_reason=reason))
    return records


def options_for(client, primary):
    """``client`` is either the adapter's primary client, or a mapping of landing options.

    One rule for all five adapters: pass the thing the adapter calls (an HTTP getter,
    an SDK client, a Ticker factory), or a mapping when a test or a replay needs to
    pin more of the landing (a fixture directory, an injected row set).
    """
    return dict(client) if isinstance(client, dict) else {primary: client}


def cik_for(security):
    """The 10-digit CIK of a security record; refused rather than guessed."""
    value = security.get('cik') or str(security.get('issuer_id', '')).split(':')[-1]
    if not str(value).isdigit():
        raise ValueError("security must carry a CIK (cik or issuer_id 'cik:<digits>')")
    return str(value).zfill(10)


def ticker_for(security):
    ticker = str(security.get('ticker') or '').strip()
    if not ticker:
        raise ValueError('security has no ticker')
    return ticker
