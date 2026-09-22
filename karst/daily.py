"""Daily intake at scale: prices + dated news leads, a daily snapshot per member.

A run refreshes every monitored member with a bounded pool of workers; each network
call is capped per source by ``karst.fetch.limits``, so widening the pool never
multiplies the load on a provider. Progress is an append-only checkpoint — a header
file plus one line per finished member — so a run interrupted anywhere (a crash, a
container restart) resumes by run ID without redoing the members already done, and
saving progress costs one line, not the whole receipt again.

Per member the refresh is incremental: prices are fetched from the last complete
bar, merged into the stored series (equal to a full rebuild; tested), and the daily
snapshot (``karst.daily_snapshot``) is rebuilt mechanically. Research versions, update
checks and publications are never written here. Nothing names a security or a date.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from . import bars, daily_snapshot, service, store as store_module
from .company_bundle import CompanyBundle
from .fetch import longbridge, port
from .packet import instant, read_json
from .schema import ContractError

# Members refreshed at once. Provider load is capped per source in fetch.limits, so
# this only bounds local work: eight keeps a 200-member day inside the budget while a
# single container's CPU, SQLite writers and memory stay far from saturation.
WORKERS = 8
RUN_ID = re.compile(r'daily-[0-9a-f]{32}')


def scope(store, universe_id):
    """Explicit monitoring membership, independent of completed research/watches."""
    from . import knowledge
    universe = knowledge.get(store, 'universe', universe_id)
    if universe is None:
        raise ContractError('Monitoring universe not found')
    members = universe['payload']['members']
    eligible = [m for m in members if m['kind'] in ('company', 'security', 'fund')]
    if not eligible:
        raise ContractError('Monitoring universe has no eligible securities')
    return {'universe_id': universe_id, 'universe_version': universe['version'],
            'members': eligible,
            'excluded': [m for m in members if m not in eligible],
            'note': 'Membership does not imply completed analysis or a buy rating.'}


# --- the append-only checkpoint ------------------------------------------------

def _folder(data_dir):
    folder = service.data_root(data_dir) / 'daily_runs'
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _checked(run_id):
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ContractError('Invalid daily run ID')
    return run_id


def _save_header(data_dir, header):
    import tempfile
    folder = _folder(data_dir)
    fd, temporary = tempfile.mkstemp(dir=folder, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(header, handle, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(temporary, folder / (header['run_id'] + '.json'))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class _Members:
    """``<run_id>.members.jsonl``: one line per finished member, appended under a lock."""

    def __init__(self, data_dir, run_id):
        self.path = _folder(data_dir) / (run_id + '.members.jsonl')
        self.lock = threading.Lock()

    def append(self, result):
        line = json.dumps(result, ensure_ascii=False, allow_nan=False) + '\n'
        with self.lock, self.path.open('a', encoding='utf-8') as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())


def _read_members(path):
    """Finished results by subject; a line cut short by a crash is not a result."""
    results = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            try:
                result = json.loads(line)
            except ValueError:
                continue
            results[result['subject']] = result
    return results


def _assemble(header, results):
    """The full receipt from the header and the member lines, in membership order."""
    articles, queue = {}, {}
    ordered = [results[m['entity_id']] for m in header['members'] if m['entity_id'] in results]
    for result in ordered:
        for item in result.get('news_candidates', []):
            key = item.get('source_url') or item['source_id']
            article = articles.setdefault(key, {'title': item['title'],
                'url': item.get('source_url'), 'subjects': [], 'evidence': []})
            if result['subject'] not in article['subjects']:
                article['subjects'].append(result['subject'])
            article['evidence'].append({'subject': result['subject'], 'evidence_id': item['evidence_id']})
        if result.get('reassess_layers'):
            queue[result['subject']] = result['reassess_layers']
    incomplete = [r['subject'] for r in ordered if r['intake_status'] != 'ready_for_review']
    pending = [m['entity_id'] for m in header['members'] if m['entity_id'] not in results]
    finished = header.get('finished_at') is not None
    return {**header, 'results': ordered, 'news_candidates': list(articles.values()),
            'reassessment_queue': queue,
            'incomplete_subjects': incomplete, 'pending_subjects': pending,
            'intake_status': ('incomplete' if incomplete or pending else 'ready_for_review')
                             if finished else 'in_progress'}


def get_run(data_dir, run_id):
    """Read a durable intake checkpoint without accepting arbitrary paths."""
    folder = service.data_root(data_dir) / 'daily_runs'
    header = read_json(folder / (_checked(run_id) + '.json'))
    if 'results' in header:  # a run saved whole, before the append-only checkpoint
        return header
    return _assemble(header, _read_members(folder / (run_id + '.members.jsonl')))


_live, _live_lock = {}, threading.Lock()


def run_summary(receipt):
    """What a caller needs to decide the next step, without every member's detail."""
    finished = receipt.get('finished_at') is not None
    with _live_lock:
        running = receipt['run_id'] in _live
    state = 'finished' if finished else 'running' if running else 'interrupted'
    results = receipt['results']
    return {key: receipt.get(key) for key in
            ('run_id', 'parent_run_id', 'universe_id', 'universe_version', 'since',
             'started_at', 'finished_at', 'elapsed_seconds', 'workers', 'intake_status',
             'incomplete_subjects', 'pending_subjects', 'reassessment_queue',
             'analysis_complete', 'next_action')} | {
        'state': state,
        'counts': {'members': len(receipt['members']), 'done': len(results),
                   'ready': sum(r['intake_status'] == 'ready_for_review' for r in results),
                   'incomplete': len(receipt['incomplete_subjects']),
                   'pending': len(receipt['pending_subjects']),
                   'history_fetches': sum(bool(r.get('history_recovered')) for r in results),
                   'news_articles': len(receipt['news_candidates'])},
        'resume': ('resume_daily_scope(run_id) retries only the incomplete and pending members'
                   if state == 'interrupted' or (finished and receipt['intake_status'] != 'ready_for_review')
                   else None)}


def recent_runs(data_dir, limit=10):
    if not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ContractError('Daily run limit must be 1..50')
    folder = service.data_root(data_dir) / 'daily_runs'
    paths = sorted(folder.glob('daily-*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    keys = ('run_id', 'parent_run_id', 'universe_id', 'universe_version', 'started_at',
            'finished_at', 'intake_status', 'incomplete_subjects', 'pending_subjects')
    return [{k: v for k, v in get_run(data_dir, p.stem).items() if k in keys}
            for p in paths[:limit] if RUN_ID.fullmatch(p.stem)]


# --- running a scope -------------------------------------------------------------

def open_run(store, data_dir, universe_id, *, since=None, resume_run_id=None, workers=WORKERS):
    """Write a new run's header; a resume copies the parent's successes into it first.

    Successful results keep their original timestamps. Resume is recovery of the same
    observation window, not a new day's refresh. No review cursor advances.
    """
    selected = scope(store, universe_id)
    previous = get_run(data_dir, resume_run_id) if resume_run_id else None
    if previous:
        if (previous['universe_id'] != universe_id or
                previous['universe_version'] != selected['universe_version']):
            raise ContractError('Monitoring membership changed; start a fresh daily run')
        if since is not None and since != previous.get('since'):
            raise ContractError('Resume must preserve the original since window')
        since = previous.get('since')
    header = {'run_id': 'daily-' + uuid.uuid4().hex, 'parent_run_id': resume_run_id,
              'started_at': service.utc_now(), 'finished_at': None, 'elapsed_seconds': None,
              'since': since, 'workers': workers, **selected, 'analysis_complete': False,
              'shared_context_required': ['market_news', 'macro_releases_and_calendar', 'value_chain_events'],
              'next_action': 'Review shared events once, verify original articles, work the '
                             'reassessment queue and save checks before publishing. Intake is not analysis.'}
    _save_header(data_dir, header)
    members = _Members(data_dir, header['run_id'])
    for result in (previous or {}).get('results', []):
        if result['intake_status'] == 'ready_for_review':
            members.append(result)
    return header


def _one(store, data_dir, subject, since, clients):
    try:
        result = refresh(store, data_dir, subject, since=since, clients=clients)
        okay = result['sources_complete'] and result['history_ready']
        result['intake_status'] = 'ready_for_review' if okay else 'incomplete'
        return result
    except Exception as exc:  # noqa: BLE001 - one member's failure never stops the others
        return {'subject': subject, 'intake_status': 'incomplete',
                'error': str(exc), 'error_type': type(exc).__name__}


class _SharedClient:
    """One Longbridge client for the whole run, built on first use (a connection per
    member was a login per member). The SDK context is shared across the workers;
    fetch.limits caps how many calls are in flight on it."""

    def __init__(self):
        self.lock, self.client, self.built = threading.Lock(), None, False

    def __call__(self):
        with self.lock:
            if not self.built:
                self.client, self.built = longbridge.client_factory(), True
            return self.client


def execute(store, data_dir, run_id, *, clients=None, workers=None):
    """Refresh every member of ``run_id`` not finished yet; returns the full receipt.

    Each worker thread opens its own connection to ``store``'s database (SQLite
    connections are per thread). ``workers=1`` runs in the calling thread on ``store``.
    A KeyboardInterrupt / SystemExit stops the pool: members already finished are
    recorded, the rest stay pending for a resume, and the interrupt is re-raised.
    """
    clock = time.monotonic()
    folder = service.data_root(data_dir) / 'daily_runs'
    header = read_json(folder / (_checked(run_id) + '.json'))
    members = _Members(data_dir, run_id)
    done = _read_members(members.path)
    todo = [m['entity_id'] for m in header['members'] if m['entity_id'] not in done]
    clients = dict(clients or {})
    clients.setdefault('longbridge', _SharedClient())
    workers = max(1, workers or header.get('workers') or WORKERS)
    if workers == 1:
        for subject in todo:
            members.append(_one(store, data_dir, subject, header['since'], clients))
    else:
        local, opened, opened_lock = threading.local(), [], threading.Lock()

        def work(subject):
            if not hasattr(local, 'store'):
                local.store = store_module.init(store.path, check_same_thread=False)
                with opened_lock:
                    opened.append(local.store)
            return _one(local.store, data_dir, subject, header['since'], clients)

        pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='karst-daily')
        futures = [pool.submit(work, subject) for subject in todo]
        try:
            for future in as_completed(futures):
                members.append(future.result())
        except BaseException:
            pool.shutdown(wait=True, cancel_futures=True)
            recorded = set(_read_members(members.path))
            for future in futures:
                if future.done() and not future.cancelled() and future.exception() is None:
                    result = future.result()
                    if result['subject'] not in recorded:
                        members.append(result)
            raise
        finally:
            pool.shutdown(wait=True)
            for connection in opened:
                connection.close()
    header.update(finished_at=service.utc_now(),
                  elapsed_seconds=(header.get('elapsed_seconds') or 0) + time.monotonic() - clock)
    _save_header(data_dir, header)
    return get_run(data_dir, run_id)


def refresh_scope(store, data_dir, universe_id, *, since=None, clients=None, resume_run_id=None,
                  workers=WORKERS):
    """Open a run and refresh every member in this call; returns the full receipt."""
    header = open_run(store, data_dir, universe_id, since=since, resume_run_id=resume_run_id,
                      workers=workers)
    return execute(store, data_dir, header['run_id'], clients=clients, workers=workers)


def start(store, data_dir, universe_id, *, since=None, resume_run_id=None, clients=None,
          workers=WORKERS):
    """Open a run and refresh its members in a background thread; returns the header.

    The background thread has its own database connection. Progress is the
    checkpoint: read it with :func:`get_run` / :func:`run_summary`. After a process
    restart the thread is gone and the run reads ``interrupted``; resume it by ID.
    """
    with _live_lock:
        busy = [run for run, live in _live.items() if live['universe_id'] == universe_id]
    if busy:
        raise ContractError(f'Daily run {busy[0]} of this universe is still running; '
                            'check it with get_daily_runs instead of starting another')
    header = open_run(store, data_dir, universe_id, since=since, resume_run_id=resume_run_id,
                      workers=workers)
    run_id = header['run_id']

    def background():
        own = store_module.init(store.path)
        try:
            execute(own, data_dir, run_id, clients=clients, workers=workers)
        finally:
            own.close()
            with _live_lock:
                _live.pop(run_id, None)

    thread = threading.Thread(target=background, name=f'karst-{run_id}', daemon=True)
    with _live_lock:
        _live[run_id] = {'thread': thread, 'universe_id': universe_id}
    thread.start()
    return header


def wait(data_dir, run_id, seconds):
    """Block up to ``seconds`` for a background run to finish; returns its summary."""
    with _live_lock:
        live = _live.get(run_id)
    if live is not None:
        live['thread'].join(seconds)
    return run_summary(get_run(data_dir, run_id))


# --- one member ------------------------------------------------------------------

def _prices_client(clients, start_day):
    """The Longbridge option set with the candle start pinned to ``start_day``."""
    clients = dict(clients or {})
    given = clients.get('longbridge')
    options = dict(given) if isinstance(given, dict) else {'client': given}
    options.setdefault('start', start_day)
    clients['longbridge'] = options
    return clients


def _stored_series(company, security, cutoff, records):
    """The stored daily series, or one rebuilt from every registered snapshot."""
    stored = company.daily_series()
    if stored is not None and stored.get('records_seen', 0) <= len(records):
        return stored, False
    series = bars.series_for(company.root, security, cutoff, records=records)
    return {'bars': series.daily, 'basis': series.basis, 'source': series.source,
            'records_seen': len(records)}, True


def _extended(company, security, stored, records, cutoff):
    """``stored`` plus the snapshots registered since it was built.

    The new snapshots are newer than everything behind ``stored``, so when the newest
    of them has the same identity and basis the rebuild keeps ``stored``'s days before
    it and takes the rest from it — which is what :func:`daily_snapshot.merge_bars`
    does. Anything else (another basis, another symbol, nothing readable) is rebuilt
    from every snapshot. Returns ``(bars, basis, source, rebuilt)``.
    """
    fresh = records[stored['records_seen']:]
    if not fresh:
        return stored['bars'], stored['basis'], stored['source'], False
    new = bars.series_for(company.root, security, cutoff, records=fresh)
    if not new.daily:
        return stored['bars'], stored['basis'], stored['source'], False
    by_id = {record.get('evidence_id'): record for record in records}
    old_source, new_source = stored.get('source') or {}, new.source or {}
    old, chosen = by_id.get(old_source.get('evidence_id')), by_id.get(new_source.get('evidence_id'))
    same = (old is not None and chosen is not None and new.basis is not None
            and bars._identity(old) == bars._identity(chosen)
            and bars._comparable(new.basis) == bars._comparable(stored['basis'] or {})
            and (chosen.get('fetched_at') or '') > (old.get('fetched_at') or ''))
    if same:
        return daily_snapshot.merge_bars(stored['bars'], new.daily), new.basis, new.source, False
    full = bars.series_for(company.root, security, cutoff, records=records)
    return full.daily, full.basis, full.source, True


def _last_complete_day(daily):
    last = next((bar for bar in reversed(daily) if bar['complete']), None)
    return None if last is None else last['at'][:10]


def refresh(store, data_dir, subject, *, since=None, clients=None):
    bundle = service.bundle_for(data_dir, subject)
    company = CompanyBundle(bundle)
    security = company.security()
    if security is None:
        raise ContractError('Register this security with refresh_sources before its first daily check')
    if security['security_id'] != subject:
        raise ContractError('Daily security does not match the subject')
    baseline = store.latest_research(subject)
    last = store.latest_update_check(subject)
    if since is None:
        # An incomplete check must never advance the news window past unread news.
        if last and last['payload']['outcome'] == 'unchanged':
            # Overlap catches publication during the prior read/check and modest
            # provider indexing delay. Stable article identity deduplicates it.
            since = (instant(last['created_at']) - timedelta(days=1)).isoformat()
        else:
            since = (baseline['as_of'] if baseline else
                     (datetime.now(timezone.utc) - timedelta(days=3)).isoformat())
    now = service.utc_now()
    records = company.records()
    stored, _ = _stored_series(company, security, now, records)
    enough_before = bars.enough(stored['bars'], 'daily_check')
    # Only bars after the last complete one are new; the day itself is re-read so a
    # weekend or holiday still returns a bar to join on. Without enough history the
    # candles start at the news window, as before, and recovery fetches all of it.
    start_day = _last_complete_day(stored['bars']) if enough_before else None
    fetch_clients = _prices_client(clients, start_day) if start_day else clients
    result = service.refresh_sources(data_dir, security, ['prices', 'news'], since=since,
                                     clients=fetch_clients, store=store)

    def read(fetched):
        cutoff = fetched.get('research_input', {}).get('as_of') or service.utc_now()
        records = company.records()
        daily, basis, source, _ = _extended(company, security, stored, records, cutoff)
        return {'bars': daily, 'basis': basis, 'source': source, 'records_seen': len(records)}

    series = read(result)
    history_recovered = False
    if not bars.enough(series['bars'], 'daily_check'):
        recovery = service.refresh_sources(data_dir, security, ['prices'], clients=clients, store=store)
        history_recovered = True
        result['failed'].extend(recovery['failed'])
        # The later full price fetch is the price source's coverage now, as in the store.
        result['coverage'].update(recovery['coverage'])
        stored = series
        series = read(recovery)
    company.save_daily_series(series)
    plan = result.get('update_plan') or service.plan_update(store, bundle, subject, data_dir=data_dir)
    all_bars = series['bars']
    payload = (baseline or {}).get('payload') or {}
    headline = payload.get('headline', {})
    candidates = [r for r in result['records'] if r['kind'] == 'news' and
                  r['evidence_id'] in result['added'] + result['changed']]
    complete = port.complete(result['coverage'])
    snapshot = None
    if all_bars:
        before = next((i for i, bar in enumerate(all_bars)
                       if start_day and bar['at'][:10] >= start_day), max(len(all_bars) - 2, 0))
        snapshot = daily_snapshot.build(
            subject=subject, checked_at=now, bars=all_bars, new_bars=all_bars[before:],
            research=baseline if payload else None, previous=company.daily_snapshot(),
            news_candidates=candidates, coverage_complete=complete,
            reviewed_at=(last or {}).get('created_at'))
        company.save_daily_snapshot(snapshot)
    queue = (snapshot or {}).get('queue') or {}
    last_complete = next((bar for bar in reversed(all_bars) if bar['complete']), None)
    return {'subject': subject, 'checked_at': service.utc_now(), 'since': since,
            'base_version_id': (baseline or {}).get('version_id'),
            'current_judgment': headline.get('recommendation'),
            'target_date': payload.get('target_date'),
            'latest_bar': all_bars[-1] if all_bars else None,
            'last_complete_bar': last_complete,
            'bars_available': len(all_bars), 'prices_from': start_day,
            'history_recovered': history_recovered,
            'history_ready': bars.enough(all_bars, 'daily_check'),
            'news_candidates': candidates, 'coverage': result['coverage'],
            'sources_complete': complete, 'failed': result['failed'],
            'plan_id': plan['plan_id'], 'conditions': plan['conditions'],
            'outstanding_source_changes': len(plan['source_changes']),
            'snapshot': None if snapshot is None else {
                'date': snapshot['date'], 'triggers': (snapshot['plan'] or {}).get('triggers'),
                'events': [event['kind'] for event in snapshot['events']],
                'valuation_position': (snapshot['valuation'] or {}).get('position')},
            'reassess_layers': queue.get('layers', []),
            'fundamental_model_refreshed': False,
            'next_action': 'Read relevant new articles; assess whether assumptions or execution changed; '
                           'record unchanged/needs_reassessment/incomplete. No automatic rating or publication.'}
