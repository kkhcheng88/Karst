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

Source coverage (取源覆蓋) travels through the same port. An adapter that reads
several feeds returns a ``Landing`` — its records plus one ``FeedOutcome`` per
feed; a single-feed adapter returns a plain list and ``cover`` derives the
outcomes from its records. ``cover`` is the one place that decides ok / partial
/ failed; service and daily only read its report.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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


# Why a feed was not covered. timeout / rate_limited are kept apart from error so a
# scheduler can back off or retry that source alone.
FAILURE_CAUSES = ('error', 'timeout', 'rate_limited', 'empty')


@dataclass(frozen=True)
class FeedOutcome:
    """How one feed inside an adapter fared: an RSS URL, a vendor tool, or the adapter itself.

    ``ok`` means the feed answered, even with zero items: checked-and-nothing is
    coverage. ``failed`` carries a cause and a reason; it is never "no news".
    """
    feed: str
    status: str = 'ok'
    cause: str | None = None
    reason: str | None = None
    detail: dict | None = None

    def __post_init__(self):
        if self.status not in ('ok', 'failed'):
            raise ValueError(f'feed status must be ok or failed: {self.status!r}')
        if self.status == 'failed' and (self.cause not in FAILURE_CAUSES or not self.reason):
            raise ValueError(f'a failed feed needs a cause in {FAILURE_CAUSES} and a reason')


class Landing(list):
    """A multi-feed adapter's return: the LandedRecords, plus one FeedOutcome per feed.

    Still a list of records, so callers that only land evidence need not care.
    ``scope`` says what the feeds cover, e.g. that configured RSS is not all news.
    """
    def __init__(self, records=(), feeds=(), scope=None):
        super().__init__(records)
        self.feeds = tuple(feeds)
        self.scope = scope


def failure_cause(exc):
    """error / timeout / rate_limited for an exception an adapter or a feed raised."""
    if isinstance(exc, TimeoutError) or 'timed out' in str(exc).lower():
        return 'timeout'
    if 429 in (getattr(exc, 'code', None), getattr(exc, 'status', None)):
        return 'rate_limited'
    return 'error'


def failed_feed(feed, exc, detail=None):
    return FeedOutcome(feed, 'failed', failure_cause(exc), f'{type(exc).__name__}: {exc}', detail)


def _derived_feeds(adapter, records):
    """A single-feed adapter's outcome, read off its records: every non-ok record is a gap."""
    if not records:
        return (FeedOutcome(adapter, 'failed', 'empty',
                            "adapter landed nothing: 'not covered' is not 'no data'"),)
    gaps = tuple(FeedOutcome(r.meta_path.name[: -len('.meta.json')], 'failed',
                             'empty' if r.status == 'empty' else 'error', r.status_reason)
                 for r in records if r.status != 'ok')
    good = sum(r.status == 'ok' for r in records)
    return gaps + ((FeedOutcome(adapter, detail={'records': good}),) if good else ())


def cover(adapter, fetch):
    """Run ``fetch()`` for one adapter -> (records, coverage report).

    The report is ``{'adapter', 'status': ok|partial|failed, 'scope', 'feeds': [...]}``:
    ok when every feed answered, failed when none did, partial otherwise. An adapter
    that raises is one failed feed, so one broken source never hides the others.
    """
    try:
        landed = fetch()
    except Exception as exc:  # noqa: BLE001 - the failure is the report
        landed = Landing(feeds=[failed_feed(adapter, exc)])
    feeds = getattr(landed, 'feeds', None) or _derived_feeds(adapter, landed)
    good = sum(f.status == 'ok' for f in feeds)
    status = 'ok' if good == len(feeds) else 'failed' if good == 0 else 'partial'
    return list(landed), {'adapter': adapter, 'status': status,
                          'scope': getattr(landed, 'scope', None),
                          'feeds': [asdict(f) for f in feeds]}


def complete(coverage):
    """Did every source in a coverage report (adapter -> report) come back ok?"""
    return bool(coverage) and all(report['status'] == 'ok' for report in coverage.values())


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
