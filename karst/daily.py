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


def refresh_scope(store, data_dir, universe_id, *, since=None, clients=None):
    """Collect each member once, keep failures visible, and persist an intake receipt.

    Sequential writes share the store connection safely. Individual adapters may
    parallelize I/O. No completed-review cursor, rating or reader is changed here.
    """
    import json
    import os
    import tempfile
    import uuid
    import time
    started = service.utc_now()
    clock = time.monotonic()
    selected = scope(store, universe_id)
    results, articles = [], {}
    for member in selected['members']:
        subject = member['entity_id']
        try:
            result = refresh(store, data_dir, subject, since=since, clients=clients)
            coverage = result.get('news_coverage') or {}
            okay = (coverage.get('status') == 'ok' and result['history_ready']
                    and not result['failed'] and not result['adapter_errors'])
            result['intake_status'] = 'ready_for_review' if okay else 'incomplete'
            for item in result['news_candidates']:
                key = item.get('source_url') or item['source_id']
                article = articles.setdefault(key, {'title': item['title'],
                    'url': item.get('source_url'), 'subjects': [], 'evidence': []})
                if subject not in article['subjects']:
                    article['subjects'].append(subject)
                article['evidence'].append({'subject': subject, 'evidence_id': item['evidence_id']})
            results.append(result)
        except Exception as exc:
            results.append({'subject': subject, 'intake_status': 'incomplete',
                            'error': str(exc), 'error_type': type(exc).__name__})
    incomplete = [r['subject'] for r in results if r['intake_status'] == 'incomplete']
    receipt = {'run_id': 'daily-' + uuid.uuid4().hex, 'started_at': started,
               'finished_at': service.utc_now(), 'elapsed_seconds': time.monotonic() - clock,
               **selected, 'results': results, 'news_candidates': list(articles.values()),
               'intake_status': 'incomplete' if incomplete else 'ready_for_review',
               'incomplete_subjects': incomplete, 'analysis_complete': False,
               'shared_context_required': ['market_news', 'macro_releases_and_calendar',
                                           'value_chain_events'],
               'next_action': 'Review shared market/chain events once; read relevant original articles, '
                              'update affected assumptions and price plans, then save checks/publication. '
                              'RSS URL deduplication does not identify all syndicated events.'}
    folder = service.data_root(data_dir) / 'daily_runs'
    folder.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=folder, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(receipt, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, folder / (receipt['run_id'] + '.json'))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
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
