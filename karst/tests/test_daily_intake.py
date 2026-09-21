import copy
import gzip
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karst import bars, service, daily
from karst.evidence_changes import equivalent
from karst.fetch import news, edgar
from karst.fetch.registry import EvidenceRegistry
from karst.identity import entity_ids
from karst.schema import digest
from karst.tests.test_bars_reliability import ReliabilityCase, rows, weekdays
from karst.tests.test_service import ServiceCase, SECURITY


FEED = b'''<rss><channel><item><title>Demo wins contract</title>
<link>https://example.com/new</link><pubDate>Mon, 21 Sep 2026 12:00:00 GMT</pubDate>
<description>New customer order</description></item>
<item><title>Old earnings</title><link>https://example.com/old</link>
<pubDate>Tue, 01 Sep 2026 12:00:00 GMT</pubDate></item>
<item><title>Undated</title><link>https://example.com/unknown</link></item>
<item><title>Future</title><link>https://example.com/future</link>
<pubDate>Tue, 22 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>'''


class NewsTests(ServiceCase):
    def fetch(self, getter=lambda url: FEED):
        with patch('karst.fetch.news.utc_now', return_value='2026-09-21T15:00:00Z'):
            return news.fetch({'ticker': 'DEMO', 'name': 'Demo Corporation'}, self.staging,
                              since='2026-09-20', client=getter)

    def test_dates_dedupe_and_unknown_are_explicit(self):
        landed = self.fetch()
        registry = EvidenceRegistry(self.bundle)
        records = [registry.register(item, entity_ids=['XNAS:DEMO']) for item in landed]
        self.assertEqual(len(records), 2)  # neither old nor future; duplicate feed URL merged
        self.assertTrue(all(r['truncated'] and r['kind'] == 'news' for r in records))
        self.assertEqual(sum(r['published_at'] is None for r in records), 1)
        self.assertEqual([registry.register(item, entity_ids=['XNAS:DEMO'])['evidence_id']
                          for item in self.fetch()], [r['evidence_id'] for r in records])

    def test_one_feed_failure_does_not_hide_other_feed(self):
        def get(url):
            if 'yahoo' in url:
                raise TimeoutError('provider unavailable')
            return FEED
        self.assertEqual(len(self.fetch(get)), 2)
        coverage = service.read_json(self.staging / news.SOURCE / 'coverage.json')
        self.assertEqual((coverage['status'], coverage['successful_feeds']), ('partial', 1))

    def test_all_failed_is_not_no_news(self):
        with self.assertRaisesRegex(RuntimeError, 'All configured'):
            self.fetch(lambda url: b'<html>Error</html>')

    def test_empty_valid_feed_is_successful_scoped_check(self):
        self.assertEqual(self.fetch(lambda url: b'<rss><channel/></rss>'), [])
        self.assertEqual(service.read_json(self.staging / news.SOURCE / 'coverage.json')['status'], 'ok')

    def test_xml_entities_refused(self):
        with self.assertRaises(ValueError):
            news.parse_feed(b'<!DOCTYPE rss [<!ENTITY x "hello">]><rss><channel/></rss>')


class IdentityHistoryTests(ReliabilityCase):
    def test_same_numeric_cik_spelling_keeps_history_and_newest_overlap(self):
        days = weekdays('2026-08-24', 15)
        bundle, records = self.bundle_with(
            {'rows': rows(days), 'fetched_at': '2026-09-16T21:00:00Z'},
            {'rows': rows([days[-1]], close=80), 'fetched_at': '2026-09-17T21:00:00Z'})
        records.sort(key=lambda r: r['fetched_at'])
        records[0]['entity_ids'] = ['cik:0000000001', 'XNAS:DEMO']
        records[1]['entity_ids'] = ['XNAS:DEMO', 'CIK:1']
        found = bars.series_from_evidence(bundle, records, '2026-09-18T00:00:00Z')
        self.assertEqual(len(found['bars']['D']), 15)
        self.assertEqual(found['bars']['D'][-1]['close'], 80)
        records[1]['entity_ids'] = ['XNAS:DEMO', 'cik:2']
        self.assertEqual(len(bars.series_from_evidence(bundle, records, '2026-09-18T00:00:00Z')['bars']['D']), 1)

    def test_unrecognized_ids_not_guessed(self):
        self.assertNotEqual(entity_ids(['issuer:ABC']), entity_ids(['issuer:abc']))


class ObservationTests(unittest.TestCase):
    def test_gzip_clock_and_cik_spelling_are_not_a_new_filing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            records = []
            for i in (1, 2):
                raw = gzip.compress(b'Identical annual filing', mtime=i)
                path = root / f'{i}.gz'
                path.write_bytes(raw)
                records.append({'source_id': 'same', 'status': 'ok', 'kind': 'filing',
                                'entity_ids': ['cik:0000000001' if i == 1 else 'CIK:1'],
                                'fetched_at': f'2026-09-{i+10}T00:00:00Z',
                                'artifact': {'path': path.name, 'bytes': len(raw), 'sha256': digest(raw)}})
            self.assertTrue(equivalent(*records, root))
            changed = copy.deepcopy(records[1])
            changed['truncated'] = True
            self.assertFalse(equivalent(records[0], changed, root))
            raw = gzip.compress(b'Different annual filing', mtime=2)
            (root / '2.gz').write_bytes(raw)
            records[1]['artifact'].update(bytes=len(raw), sha256=digest(raw))
            self.assertFalse(equivalent(*records, root))

    def test_gzip_landing_is_deterministic(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(edgar, 'GZIP_OVER_BYTES', 1):
            meta = {'source': 'edgar', 'tool': 'test', 'params': {}}
            root = Path(folder)
            edgar._land_document(root, 'document', 'report.htm', b'<p>Same</p>', meta, None)
            first = (root / 'document.raw.htm.gz').read_bytes()
            edgar._land_document(root, 'document', 'report.htm', b'<p>Same</p>', meta, None)
            self.assertEqual(first, (root / 'document.raw.htm.gz').read_bytes())


class DailyTests(ServiceCase):
    def test_daily_only_fetches_prices_and_news_and_recovers_history(self):
        import json
        from unittest.mock import Mock
        (self.bundle / 'packet.json').write_text(json.dumps({'security': SECURITY}))
        state = Mock()
        state.latest_research.return_value = {'as_of': '2026-09-18T21:00:00Z', 'version_id': 'base'}
        state.latest_update_check.return_value = {'created_at': '2026-09-21T12:00:00Z',
                                                 'payload': {'outcome': 'incomplete'}}
        intake = {'records': [], 'added': [], 'changed': [], 'failed': [], 'adapter_errors': {},
                  'news_coverage': {'status': 'partial'}}
        recovery = {'failed': ['failed-price'], 'adapter_errors': {'longbridge': 'unavailable'}}
        plan = {'plan_id': 'p', 'conditions': [], 'source_changes': []}
        with patch.object(service, 'bundle_for', return_value=self.bundle), \
             patch.object(service, '_records', return_value=[]), \
             patch.object(service, 'refresh_sources', side_effect=[intake, recovery]) as fetch, \
             patch.object(service, 'plan_update', return_value=plan), \
             patch.object(bars, 'series_from_evidence', return_value={'bars': {'D': []}}):
            result = daily.refresh(state, self.root, SECURITY['security_id'])
        self.assertEqual(fetch.call_args_list[0].args[2], ['prices', 'news'])
        self.assertEqual(fetch.call_args_list[0].kwargs['since'], '2026-09-18T21:00:00Z')
        self.assertEqual(fetch.call_args_list[1].args[2], ['prices'])
        self.assertNotIn('since', fetch.call_args_list[1].kwargs)
        self.assertFalse(result['history_ready'])
        self.assertFalse(result['fundamental_model_refreshed'])
        self.assertEqual(result['news_coverage']['status'], 'partial')
        self.assertEqual(result['adapter_errors'], {'longbridge': 'unavailable'})
        state.record_update_check.assert_not_called()


if __name__ == '__main__':
    unittest.main()
