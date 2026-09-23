"""Incremental triage through its interface: plan inputs, check outcomes, the news window."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from karst import bars, service, triage, updates
from karst.schema import ContractError
from karst.store import Store
from karst.tests.test_updates import EARLY, baseline, watch
from karst.tests.v03_fixture import SECURITY

URL = 'https://example.com/research/power/note'


class InputsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.store = Store(self.root / 'state.sqlite')
        self.addCleanup(self.store.close)
        self.subject = SECURITY['security_id']
        self.bundle = service.ensure_company(self.store, self.root, SECURITY)['bundle']
        protocol = service.get_research_protocol('research')['version']
        prior = baseline([])['payload'] | {'method_version': protocol['declared'] + '+' + protocol['digest'][:12]}
        self.research = self.store.save_research_version(self.subject, prior, evidence=[], as_of=EARLY)

    def ingest(self, entity, excerpt, *, author='Selected Analyst', kind='industry_report'):
        bundle = service.company_paths(self.root, entity)['bundle']
        return service.ingest_source(bundle, url=URL, excerpt=excerpt, author=author,
                                     published_at='2026-09-19', kind=kind, entity_ids=[entity],
                                     title='Outlook', source_type='broker_report', store=self.store)

    def watching(self, **changes):
        w = watch()
        w.update({'dependencies': [], 'validation_deadline': None, **changes})
        return self.store.save_watch(self.subject, w, self.research['version_id'])

    def inputs(self, **kwargs):
        return triage.inputs(self.store, self.bundle, self.subject, data_dir=self.root, **kwargs)

    def test_report_subscription_selects_the_watched_author_from_another_store(self):
        chosen = self.ingest('industry:power', 'Margin forecast 20 percent')
        self.ingest('industry:power', 'Higher capacity forecast', author='Other Analyst')
        w = watch()['subscriptions'][0] | {'authors': ['Selected Analyst'], 'source_types': ['broker_report']}
        self.watching(subscriptions=[w])
        found = self.inputs()
        self.assertEqual([r['evidence_id'] for r in found['records']], [chosen['evidence_id']])
        plan = updates.plan(**found)
        self.assertEqual([c['evidence_id'] for c in plan['source_changes']], [chosen['evidence_id']])
        self.assertEqual(plan, triage.plan(self.store, self.bundle, self.subject, data_dir=self.root)
                         | {'checked_at': plan['checked_at']})
        # Without a data directory other company stores are never read.
        self.assertEqual(triage.inputs(self.store, self.bundle, self.subject)['records'], [])

    def test_cross_company_dependency_carries_its_own_exposure(self):
        supplier = self.ingest('supplier:chips', 'Lead times extend', kind='other_public')
        self.ingest('unrelated:co', 'Unrelated note', kind='other_public')
        self.watching(subscriptions=[], dependencies=[{
            'input_kind': 'entity', 'input_id': 'supplier:chips', 'input_version': 'one',
            'assumption_id': 'supply', 'assumption_version': 'one', 'layers': ['L3'],
            'exposure': 'Longer lead times delay our shipments'}])
        found = self.inputs()
        self.assertEqual([r['evidence_id'] for r in found['records']], [supplier['evidence_id']])
        change = updates.plan(**found)['source_changes'][0]
        self.assertEqual(change['dependencies'][0]['exposure'], 'Longer lead times delay our shipments')
        self.assertTrue({'L3', 'L4', 'L6'} <= set(change['layers']))

    def test_price_condition_reads_only_this_security_s_own_bars(self):
        self.ingest('industry:power', 'Supplier note')
        self.watching(conditions=[{'kind': 'price', 'description': 'Breakout', 'operator': 'gte',
                                   'value': 100, 'currency': 'USD'}])
        bar = {'at': '2026-09-18T20:00:00+00:00', 'open': 105.0, 'high': 111.0, 'low': 104.0,
               'close': 110.0, 'volume': 1.0, 'complete': True}
        series = bars.Series([bar], {'price_basis': 'raw daily', 'evidence_id': 'ev-own'},
                             {'adjust': 'NoAdjust'}, [], bars.Session())
        with patch.object(bars, 'series_for', return_value=series) as read:
            found = self.inputs()
        # The subscribed supplier note is a plan input, never this security's price.
        self.assertEqual(len(found['records']), 1)
        self.assertEqual(read.call_args.kwargs['records'], triage._records(self.bundle))
        self.assertEqual(read.call_args.args[1]['security_id'], self.subject)
        self.assertEqual(found['market'], {'price': 110.0, 'at': bar['at'], 'complete': True,
                                           'currency': 'USD', 'basis': 'raw daily',
                                           'adjustment': 'NoAdjust', 'evidence_id': 'ev-own'})
        plan = updates.plan(**found)
        self.assertEqual(plan['conditions'][0]['status'], 'threshold_met')
        self.assertIn('L5', plan['affected_layers'])

    def test_source_failure_is_disclosed_and_blocks_an_unchanged_check(self):
        self.watching()
        self.store.record_refresh(self.subject, 'longbridge', {'adapter': 'longbridge', 'status': 'failed'})
        found = self.inputs()
        self.assertEqual([s['status'] for s in found['refresh_status']], ['failed'])
        plan = updates.plan(**found)
        self.assertIn('refresh_incomplete', [r['kind'] for r in plan['reasons']])
        with self.assertRaisesRegex(ContractError, 'Incomplete'):
            triage.record_check(self.store, self.bundle, self.subject, plan['plan_id'],
                                'unchanged', 'Nothing new', data_dir=self.root)
        saved = triage.record_check(self.store, self.bundle, self.subject, plan['plan_id'],
                                    'incomplete', 'Retry the price source', data_dir=self.root)
        self.assertEqual(saved['payload']['outcome'], 'incomplete')

    def test_future_cutoff_is_refused(self):
        with self.assertRaises(ContractError):
            self.inputs(as_of='2999-01-01T00:00:00Z')


class NewsWindowTests(unittest.TestCase):
    PLAN = {'base_version_id': 'rv-one', 'reasons': [], 'diagnostics': [], 'refresh_status': []}

    def test_window_starts_after_an_unchanged_check_only(self):
        research = {'as_of': '2026-09-18T21:00:00Z'}
        now = datetime(2026, 9, 23, tzinfo=timezone.utc)
        self.assertEqual(triage.news_since(None, None, now), '2026-09-20T00:00:00+00:00')
        self.assertEqual(triage.news_since(research, None, now), research['as_of'])
        for outcome in ('incomplete', 'needs_reassessment'):
            check = {'created_at': '2026-09-21T12:00:00Z', 'payload': {'outcome': outcome}}
            self.assertEqual(triage.news_since(research, check, now), research['as_of'])
        check = {'created_at': '2026-09-21T12:00:00Z', 'payload': {'outcome': 'unchanged'}}
        self.assertEqual(triage.news_since(research, check, now), '2026-09-20T12:00:00+00:00')

    def test_unchanged_needs_complete_coverage_and_research(self):
        triage.check_outcome(self.PLAN, 'unchanged', 'Read everything')
        for broken in ({'diagnostics': [{'status': 'error'}]},
                       {'refresh_status': [{'status': 'partial'}]},
                       {'base_version_id': None},
                       {'reasons': [{'kind': 'missing_baseline_inputs'}]}):
            with self.assertRaises(ContractError):
                triage.check_outcome(self.PLAN | broken, 'unchanged', 'Read everything')
            triage.check_outcome(self.PLAN | broken, 'incomplete', 'Retry later')
        for outcome, reason in (('maybe', 'Why'), ('unchanged', ' ')):
            with self.assertRaises(ContractError):
                triage.check_outcome(self.PLAN, outcome, reason)

    def test_queue_stays_unread_until_a_later_check_of_the_same_research(self):
        queued = {'layers': ['L2', 'L6'], 'since': '2026-09-21T00:00:00Z', 'base_version_id': 'rv-one'}
        self.assertTrue(triage.unread_queue(queued, None, 'rv-one'))
        self.assertTrue(triage.unread_queue(queued, '2026-09-20T00:00:00Z', 'rv-one'))
        self.assertFalse(triage.unread_queue(queued, '2026-09-22T00:00:00Z', 'rv-one'))
        self.assertFalse(triage.unread_queue(queued, None, 'rv-two'))
        self.assertFalse(triage.unread_queue({}, None, 'rv-one'))
        self.assertTrue(triage.news_pending(queued))
        self.assertFalse(triage.news_pending(queued | {'layers': ['L5', 'L6']}))
        self.assertFalse(triage.news_pending(None))


if __name__ == '__main__':
    unittest.main()
