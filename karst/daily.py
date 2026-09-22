"""Small daily intake: prices + dated news leads, preserving the research model."""
from datetime import datetime, timezone, timedelta
from pathlib import Path

from . import service, bars
from .identity import security_record
from .packet import read_json, instant
from .schema import ContractError


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


def get_run(data_dir, run_id):
    """Read a durable intake checkpoint without accepting arbitrary paths."""
    import re
    if not isinstance(run_id, str) or not re.fullmatch(r'daily-[0-9a-f]{32}', run_id):
        raise ContractError('Invalid daily run ID')
    return read_json(service.data_root(data_dir) / 'daily_runs' / (run_id + '.json'))


def recent_runs(data_dir, limit=10):
    if not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ContractError('Daily run limit must be 1..50')
    folder = service.data_root(data_dir) / 'daily_runs'
    paths = sorted(folder.glob('daily-*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    keys = ('run_id', 'parent_run_id', 'universe_id', 'universe_version', 'started_at',
            'finished_at', 'intake_status', 'incomplete_subjects', 'pending_subjects')
    return [{k: v for k, v in read_json(p).items() if k in keys} for p in paths[:limit]]


def _save_run(data_dir, receipt):
    import json
    import os
    import tempfile
    folder = service.data_root(data_dir) / 'daily_runs'
    folder.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=folder, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(receipt, handle, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(temporary, folder / (receipt['run_id'] + '.json'))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def refresh_scope(store, data_dir, universe_id, *, since=None, clients=None, resume_run_id=None):
    """Checkpoint every member; resume only failed/unattempted intake in a new run.

    Successful results keep their original timestamps. Resume is recovery of the
    same observation window, not a new day's refresh. No review cursor advances.
    """
    import uuid
    import time
    selected = scope(store, universe_id)
    previous = get_run(data_dir, resume_run_id) if resume_run_id else None
    if previous:
        if (previous['universe_id'] != universe_id or
                previous['universe_version'] != selected['universe_version']):
            raise ContractError('Monitoring membership changed; start a fresh daily run')
        if since is not None and since != previous.get('since'):
            raise ContractError('Resume must preserve the original since window')
        since = previous.get('since')
    clock = time.monotonic()
    results = {r['subject']: r for r in (previous or {}).get('results', [])
               if r['intake_status'] == 'ready_for_review'}
    receipt = {'run_id': 'daily-' + uuid.uuid4().hex, 'parent_run_id': resume_run_id,
               'started_at': service.utc_now(), 'finished_at': None, 'since': since,
               **selected, 'analysis_complete': False,
               'shared_context_required': ['market_news', 'macro_releases_and_calendar', 'value_chain_events'],
               'next_action': 'Review shared events once, verify original articles, update affected '
                              'judgments and save checks before publishing. Intake is not analysis.'}

    def checkpoint(finished=False):
        articles = {}
        ordered = [results[m['entity_id']] for m in selected['members'] if m['entity_id'] in results]
        for result in ordered:
            for item in result.get('news_candidates', []):
                key = item.get('source_url') or item['source_id']
                article = articles.setdefault(key, {'title': item['title'],
                    'url': item.get('source_url'), 'subjects': [], 'evidence': []})
                if result['subject'] not in article['subjects']:
                    article['subjects'].append(result['subject'])
                article['evidence'].append({'subject': result['subject'], 'evidence_id': item['evidence_id']})
        incomplete = [r['subject'] for r in ordered if r['intake_status'] != 'ready_for_review']
        pending = [m['entity_id'] for m in selected['members'] if m['entity_id'] not in results]
        receipt.update(results=ordered, news_candidates=list(articles.values()),
                       incomplete_subjects=incomplete, pending_subjects=pending,
                       elapsed_seconds=time.monotonic()-clock,
                       intake_status=('incomplete' if incomplete or pending else 'ready_for_review')
                                     if finished else 'in_progress')
        if finished:
            receipt['finished_at'] = service.utc_now()
        _save_run(data_dir, receipt)

    checkpoint()
    for member in selected['members']:
        subject = member['entity_id']
        if subject in results:
            continue
        try:
            result = refresh(store, data_dir, subject, since=since, clients=clients)
            coverage = result.get('news_coverage') or {}
            okay = (coverage.get('status') == 'ok' and result['history_ready']
                    and not result['failed'] and not result['adapter_errors'])
            result['intake_status'] = 'ready_for_review' if okay else 'incomplete'
            results[subject] = result
        except Exception as exc:
            results[subject] = {'subject': subject, 'intake_status': 'incomplete',
                                'error': str(exc), 'error_type': type(exc).__name__}
        checkpoint()
    checkpoint(finished=True)
    return receipt


def refresh(store, data_dir, subject, *, since=None, clients=None):
    bundle = service.bundle_for(data_dir, subject)
    packet_path = Path(bundle) / 'packet.json'
    if not packet_path.exists():
        raise ContractError('Register this security with refresh_sources before its first daily check')
    packet = read_json(packet_path)
    security = security_record(packet['security'])
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
    result = service.refresh_sources(data_dir, security, ['prices', 'news'], since=since,
                                     clients=clients, store=store)
    cutoff = result.get('research_input', {}).get('as_of') or service.utc_now()
    series = bars.series_from_evidence(bundle, service._records(bundle), cutoff,
                                      session=bars.Session.for_exchange(security.get('exchange')))
    history_recovered = False
    if not series or len(series['bars']['D']) < 200:
        recovery = service.refresh_sources(data_dir, security, ['prices'], clients=clients, store=store)
        history_recovered = True
        result['failed'].extend(recovery['failed'])
        result['adapter_errors'].update(recovery['adapter_errors'])
        cutoff = recovery.get('research_input', {}).get('as_of') or service.utc_now()
        series = bars.series_from_evidence(bundle, service._records(bundle), cutoff,
                                          session=bars.Session.for_exchange(security.get('exchange')))
    plan = service.plan_update(store, bundle, subject, data_dir=data_dir)
    all_bars = series['bars']['D'] if series else []
    complete = [bar for bar in all_bars if bar['complete']]
    headline = (baseline or {}).get('payload', {}).get('headline', {})
    candidates = [r for r in result['records'] if r['kind'] == 'news' and
                  r['evidence_id'] in result['added'] + result['changed']]
    return {'subject': subject, 'checked_at': service.utc_now(), 'since': since,
            'base_version_id': (baseline or {}).get('version_id'),
            'current_judgment': headline.get('recommendation'),
            'target_date': (baseline or {}).get('payload', {}).get('target_date'),
            'latest_bar': all_bars[-1] if all_bars else None,
            'last_complete_bar': complete[-1] if complete else None,
            'bars_available': len(all_bars), 'history_recovered': history_recovered,
            'history_ready': len(complete) >= 200,
            'news_candidates': candidates, 'news_coverage': result.get('news_coverage'),
            'failed': result['failed'], 'adapter_errors': result['adapter_errors'],
            'plan_id': plan['plan_id'], 'conditions': plan['conditions'],
            'outstanding_source_changes': len(plan['source_changes']),
            'fundamental_model_refreshed': False,
            'next_action': 'Read relevant new articles; assess whether assumptions or execution changed; '
                           'record unchanged/needs_reassessment/incomplete. No automatic rating or publication.'}
