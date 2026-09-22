"""KARST-256: daily refresh at scale — limits, batch registration, incremental series,
daily snapshot routing and the background / resumable run."""
import copy
import datetime as dt
import tempfile
import threading
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from karst import bars, daily, daily_snapshot, knowledge, store as store_module, updates
from karst.company_bundle import CompanyBundle
from karst.fetch import limits, longbridge, port
from karst.fetch.port import pair_staging
from karst.fetch.registry import EvidenceRegistry
from karst.tests.test_bars_reliability import ENTITY_IDS, ReliabilityCase, rows, weekdays
from karst.tests.test_publish_bars import stage_prices
from karst.tests.v03_fixture import SECURITY, calculated_valuation


class LimitTests(unittest.TestCase):
    def setUp(self):
        saved = limits.configure(timeout=0.05, retries=1, backoff=0.0)
        self.addCleanup(limits.LIMITS.update, saved)

    def test_timeout_and_429_are_reported_as_their_cause(self):
        with self.assertRaises(TimeoutError) as caught:
            limits.call('longbridge', time.sleep, 0.3)
        self.assertEqual(port.failure_cause(caught.exception), 'timeout')
        calls = []

        def throttled():
            calls.append(1)
            raise urllib.error.HTTPError('https://example.invalid', 429, 'Too Many', {}, None)
        with self.assertRaises(limits.RateLimited) as caught:
            limits.call('yahoo_rss', throttled)
        self.assertEqual(len(calls), 2, 'one retry after the first 429')
        self.assertEqual(port.failure_cause(caught.exception), 'rate_limited')

    def test_a_slow_vendor_lands_as_a_timeout_in_the_port_coverage(self):
        class Slow:
            def __getattr__(self, name):
                return lambda *args, **kwargs: time.sleep(0.3)
        with tempfile.TemporaryDirectory() as folder:
            _, report = port.cover('longbridge', lambda: longbridge.fetch(
                {**SECURITY, 'symbols': {'longbridge': 'DEMO.US'}}, folder, client=Slow()))
        self.assertEqual(report['status'], 'failed')
        self.assertEqual({feed['cause'] for feed in report['feeds']}, {'timeout'})

    def test_concurrency_is_capped_per_source(self):
        limits.configure(concurrency=2, rate=1000, timeout=5)
        live, peak, lock = [0], [0], threading.Lock()

        def work():
            with lock:
                live[0] += 1
                peak[0] = max(peak[0], live[0])
            time.sleep(0.05)
            with lock:
                live[0] -= 1
        threads = [threading.Thread(target=limits.call, args=('edgar', work)) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(peak[0], 2)


class BatchRegistrationTests(unittest.TestCase):
    def test_register_many_equals_registering_one_by_one(self):
        days = weekdays('2026-08-03', 20)
        outputs = []
        for batch in (False, True):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                for index, fetched in enumerate(('2026-09-01T21:00:00Z', '2026-09-02T21:00:00Z',
                                                 '2026-09-02T21:00:00Z')):
                    stage_prices(rows(days, close=20.0 + (index == 1)), fetched_at=fetched,
                                 into=f'snap{index}')(root / 'staging')
                pairs = [(raw, meta) for meta, raws in pair_staging(root / 'staging') for raw in raws]
                registry = EvidenceRegistry(root / 'bundle')
                if batch:
                    registry.register_many(pairs, entity_ids=ENTITY_IDS)
                else:
                    for raw, meta in pairs:
                        registry.register(raw, meta, entity_ids=ENTITY_IDS)
                bundle = root / 'bundle' / 'evidence'
                outputs.append(((bundle / 'manifest.jsonl').read_bytes(),
                                (bundle / 'observations.jsonl').read_bytes()))
        self.assertEqual(outputs[0], outputs[1])


class IncrementalSeriesTests(ReliabilityCase):
    """A stored series extended by newer snapshots equals a rebuild from all of them."""

    def check(self, snapshots, stored_from, cutoff='2026-12-31T00:00:00Z'):
        bundle, records = self.bundle_with(*snapshots)
        records.sort(key=lambda r: r['fetched_at'])
        company = CompanyBundle(bundle)
        base = bars.series_for(bundle, SECURITY, cutoff, records=records[:stored_from])
        stored = {'bars': base.daily, 'basis': base.basis, 'source': base.source,
                  'records_seen': stored_from}
        merged, basis, _, rebuilt = daily._extended(company, SECURITY, stored, records, cutoff)
        full = bars.series_for(bundle, SECURITY, cutoff, records=records)
        self.assertEqual(merged, full.daily)
        self.assertEqual(basis, full.basis)
        # The technical reading built on either is the same, number for number.
        self.assertEqual(daily_snapshot.charts.measure(merged), daily_snapshot.charts.measure(full.daily))
        return rebuilt

    def test_short_daily_snapshots_extend_the_long_history(self):
        long_days = weekdays('2025-09-01', 260)
        tail = weekdays(long_days[-1], 3)
        snapshots = [{'rows': rows(long_days), 'fetched_at': f'{long_days[-1]}T21:00:00Z'},
                     # the next day re-reads the last complete bar with a revised close
                     {'rows': rows(tail[:2], close=160.0), 'fetched_at': f'{tail[1]}T21:00:00Z'},
                     {'rows': rows(tail[1:], close=161.0), 'fetched_at': f'{tail[2]}T21:00:00Z'}]
        self.assertFalse(self.check(snapshots, 1))
        self.assertFalse(self.check(snapshots, 2))

    def test_a_snapshot_on_another_basis_falls_back_to_a_rebuild(self):
        long_days = weekdays('2025-09-01', 260)
        snapshots = [{'rows': rows(long_days), 'fetched_at': f'{long_days[-1]}T21:00:00Z'},
                     {'rows': rows(long_days[-2:], close=90.0), 'adjust': 'ForwardAdjust',
                      'fetched_at': '2026-12-01T21:00:00Z'}]
        self.assertTrue(self.check(snapshots, 1))


def bar(day, close, *, open_=None, complete=True):
    open_ = close if open_ is None else open_
    return {'at': f'{day}T20:00:00+00:00', 'open': open_, 'high': max(open_, close) + 0.2,
            'low': min(open_, close) - 0.2, 'close': close, 'volume': 1000.0, 'complete': complete}


def history(count=260):
    days = weekdays('2025-06-02', count + 5)
    return [bar(day, 20.0 + 0.3 * ((i % 10) - 5) / 5) for i, day in enumerate(days[:count])], days[count:]


RESEARCH = {'version_id': 'v1', 'payload': {
    'market': {'price': 20.0}, 'technical': {'quote_to_bar_factor': 1},
    'target_date': '2027-03-31',
    'plan': {'entry_price': 18.0, 'exit_price': 15.0, 'target_price': 30.0, 'stress_price': 14.0,
             'round_trip_cost_per_share': 0.02},
    'valuation': calculated_valuation('2026-09-18T00:00:00Z', [])}}


class SnapshotRoutingTests(unittest.TestCase):
    """The four daily cases: pure price day, price-event day, news day, incomplete coverage."""

    def day(self, bars_, previous, *, news=(), complete=True, research=RESEARCH, reviewed_at=None,
            at='2026-09-22T21:30:00Z'):
        return daily_snapshot.build(subject='EX:DEMO', checked_at=at, bars=bars_,
                                    new_bars=bars_[-2:], research=research, previous=previous,
                                    news_candidates=list(news), coverage_complete=complete,
                                    reviewed_at=reviewed_at)

    def setUp(self):
        self.bars, self.next_days = history()
        self.first = self.day(self.bars, None, at='2026-09-21T21:30:00Z')

    def test_first_snapshot_has_plan_distances_triggers_rr_and_fair_value(self):
        plan = self.first['plan']
        self.assertEqual(plan['triggers'], {'entry': 'above', 'invalidation': 'holding', 'target': 'below'})
        self.assertAlmostEqual(plan['levels']['entry_price']['distance'],
                               18.0 - self.bars[-1]['close'])
        self.assertTrue(plan['risk_reward_at_close']['available'])
        self.assertEqual(set(self.first['valuation']['fair_value']), {'bear', 'base', 'bull'})
        self.assertIsNotNone(self.first['technical']['sma200'])

    def test_pure_price_day_queues_nothing(self):
        today = self.bars + [bar(self.next_days[0], self.bars[-1]['close'])]
        snapshot = self.day(today, self.first)
        self.assertEqual(snapshot['events'], [])
        self.assertIsNone(snapshot['queue'])

    def test_price_event_day_queues_the_price_layers(self):
        today = self.bars + [bar(self.next_days[0], 17.5, open_=self.bars[-1]['close'])]
        snapshot = self.day(today, self.first)
        kinds = {event['kind'] for event in snapshot['events']}
        self.assertIn('trigger_changed', kinds)
        self.assertEqual(snapshot['plan']['triggers']['entry'], 'at_or_below')
        self.assertEqual(snapshot['queue']['layers'], sorted(updates.PRICE_EVENT_LAYERS))

    def test_gap_beyond_the_atr_threshold_is_an_event(self):
        close = self.bars[-1]['close']
        today = self.bars + [bar(self.next_days[0], close + 3.0, open_=close + 3.0)]
        kinds = {event['kind'] for event in self.day(today, self.first)['events']}
        self.assertIn('gap', kinds)

    def test_news_day_queues_the_news_layers(self):
        today = self.bars + [bar(self.next_days[0], self.bars[-1]['close'])]
        snapshot = self.day(today, self.first, news=[{'evidence_id': 'news-1'}])
        self.assertEqual(snapshot['queue']['layers'], sorted(updates.KIND_LAYERS['news']))
        self.assertTrue(snapshot['news']['pending_review'])

    def test_incomplete_coverage_queues_nothing_and_says_so(self):
        today = self.bars + [bar(self.next_days[0], self.bars[-1]['close'])]
        snapshot = self.day(today, self.first, complete=False)
        self.assertIsNone(snapshot['queue'])
        self.assertFalse(snapshot['news']['coverage_complete'])

    def test_queue_carries_forward_until_a_check_is_recorded(self):
        today = self.bars + [bar(self.next_days[0], self.bars[-1]['close'])]
        queued = self.day(today, self.first, news=[{'evidence_id': 'news-1'}])
        tomorrow = today + [bar(self.next_days[1], self.bars[-1]['close'])]
        kept = self.day(tomorrow, queued, at='2026-09-23T21:30:00Z')
        self.assertEqual(kept['queue']['layers'], queued['queue']['layers'])
        cleared = self.day(tomorrow, queued, at='2026-09-23T21:30:00Z',
                           reviewed_at='2026-09-23T10:00:00Z')
        self.assertIsNone(cleared['queue'])

    def test_radar_member_gets_technical_only(self):
        today = self.bars + [bar(self.next_days[0], 17.5)]
        snapshot = self.day(today, None, research=None, news=[{'evidence_id': 'news-1'}])
        self.assertIsNone(snapshot['plan'])
        self.assertIsNone(snapshot['valuation'])
        self.assertIsNone(snapshot['queue'])
        self.assertIsNotNone(snapshot['technical']['close'])

    def test_snapshot_does_not_change_the_research(self):
        research = copy.deepcopy(RESEARCH)
        self.day(self.bars, None, research=research)
        self.assertEqual(research, RESEARCH)


class BackgroundRunTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = store_module.init(self.root / 'state.db')
        self.addCleanup(self.state.close)
        knowledge.save(self.state, 'universe', 'monitor', {
            'name': 'Monitor', 'summary': 'Explicit coverage',
            'members': [dict(entity_id=f'EX:{c}', name=c, kind='security', roles=['tracked'],
                             comparison_groups=[]) for c in 'ABCDEF'],
            'sources': [{'title': 'Scope', 'url': 'https://example.com/scope'}]})

    @staticmethod
    def ok(state, root, subject, **kwargs):
        return dict(subject=subject, sources_complete=True, history_ready=True, failed=[],
                    news_candidates=[], reassess_layers=['L5', 'L6'] if subject == 'EX:C' else [])

    def test_background_run_answers_with_a_summary_and_finishes(self):
        with patch.object(daily, 'refresh', side_effect=self.ok):
            header = daily.start(self.state, self.root, 'monitor', workers=3)
            summary = daily.wait(self.root, header['run_id'], 10)
        self.assertEqual(summary['state'], 'finished')
        self.assertEqual(summary['counts']['done'], 6)
        self.assertEqual(summary['reassessment_queue'], {'EX:C': ['L5', 'L6']})
        self.assertNotIn('results', summary)

    def test_restart_mid_run_resumes_only_the_unfinished_members(self):
        header = daily.open_run(self.state, self.root, 'monitor', since='2026-09-22')
        # The container died after two members: their lines are the whole progress.
        members = daily._Members(self.root, header['run_id'])
        for subject in ('EX:A', 'EX:B'):
            members.append({**self.ok(None, None, subject), 'intake_status': 'ready_for_review'})
        with members.path.open('a', encoding='utf-8') as handle:
            handle.write('{"subject": "EX:C", "cut sh')  # a line the crash cut short
        summary = daily.run_summary(daily.get_run(self.root, header['run_id']))
        self.assertEqual(summary['state'], 'interrupted')
        self.assertEqual(summary['pending_subjects'], ['EX:C', 'EX:D', 'EX:E', 'EX:F'])
        seen = []

        def refresh(state, root, subject, **kwargs):
            seen.append(subject)
            self.assertEqual(kwargs['since'], '2026-09-22')
            return self.ok(state, root, subject)
        with patch.object(daily, 'refresh', side_effect=refresh):
            resumed = daily.start(self.state, self.root, 'monitor', resume_run_id=header['run_id'])
            done = daily.wait(self.root, resumed['run_id'], 10)
        self.assertEqual(sorted(seen), ['EX:C', 'EX:D', 'EX:E', 'EX:F'])
        self.assertEqual(done['intake_status'], 'ready_for_review')

    def test_a_second_run_of_a_running_universe_is_refused(self):
        gate = threading.Event()

        def slow(state, root, subject, **kwargs):
            gate.wait(5)
            return self.ok(state, root, subject)
        with patch.object(daily, 'refresh', side_effect=slow):
            header = daily.start(self.state, self.root, 'monitor', workers=2)
            try:
                with self.assertRaises(daily.ContractError):
                    daily.start(self.state, self.root, 'monitor')
                self.assertEqual(daily.wait(self.root, header['run_id'], 0)['state'], 'running')
            finally:
                gate.set()
                daily.wait(self.root, header['run_id'], 10)


if __name__ == '__main__':
    unittest.main()
