"""Small daily intake: prices + dated news leads, preserving the research model."""
from datetime import datetime, timezone, timedelta
from pathlib import Path

from . import service, bars
from .identity import security_record
from .packet import read_json
from .schema import ContractError


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
        since = (last['created_at'] if last and last['payload']['outcome'] == 'unchanged'
                 else baseline['as_of'] if baseline else
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
