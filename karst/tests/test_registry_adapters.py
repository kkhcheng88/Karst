"""Current local adapters -> registry, using their shared offline fixture harnesses."""
import tempfile
import unittest
from pathlib import Path

from karst.fetch import broker, defeatbeta, edgar
from karst.fetch.registry import EvidenceRegistry, load_meta
from karst.packet import read_json
from karst.tests import test_fetch as adapter_cases
from karst.tests.test_fetch import EdgarHarness, FakeTicker, submissions_fixtures

FIXTURES = Path(__file__).parent / 'fixtures'


class AdapterRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.staging = self.root / 'staging'
        self.registry = EvidenceRegistry(self.root / 'bundle')

    def register_landed(self):
        records = []
        for path in sorted(self.staging.rglob('*.meta.json')):
            meta, _ = load_meta(path)
            stem = str(path)[:-len('.meta.json')]
            candidates = [Path(stem + suffix) for suffix in ('.txt', '.json', '.csv')]
            raw = next((p for p in candidates if p.exists()), None)
            record = self.registry.register(raw, path, entity_ids=['issuer:fixture'])
            self.assertEqual(record['status'], meta['status'])
            records.append(record)
        self.assertTrue(records)
        return records

    def test_all_broker_landings_including_nested_error_envelope(self):
        for source in ('futu', 'longbridge'):
            for path in sorted((FIXTURES / source).glob('*.json')):
                if path.name.endswith('.meta.json'):
                    continue
                payload = read_json(path)
                meta, _ = load_meta(path.with_suffix('.meta.json'))
                response = payload['response'] if payload.get('response') is not None else payload.get('error')
                broker.land(self.staging, source, meta['tool'], payload.get('symbol'), meta['params'], response,
                            fetched_at=meta['fetched_at'])
        records = self.register_landed()
        self.assertEqual(len(records), 30)
        self.assertEqual(sum(r['status'] == 'error' for r in records), 1)

    def test_defeatbeta_current_adapter(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest('pandas needed for local adapter integration harness')
        ticker = read_json(FIXTURES / 'defeatbeta/info.meta.json')['params']['ticker']
        defeatbeta.fetch_company(ticker, self.staging,
                                ticker_factory=lambda _: FakeTicker(FIXTURES / 'defeatbeta', pd))
        records = self.register_landed()
        self.assertEqual(len(records), 10)
        self.assertEqual(sum(r['status'] == 'empty' for r in records), 2)
        self.assertEqual(sum(r['kind'] == 'transcript' for r in records), 1)

    def test_broker_observation_time_does_not_create_false_economic_update(self):
        payload = {'price': '12.50', 'timestamp': '2026-09-14T18:00:00Z'}
        def land(at, response):
            result = broker.land(self.staging, 'longbridge', 'mcp__longbridge__quote',
                                 'TEST.US', {'symbols': ['TEST.US']}, response, fetched_at=at)
            return self.registry.register(result['path'], result['meta'], entity_ids=['issuer:test'])
        first = land('2026-09-14T18:01:00Z', payload)
        again = land('2026-09-14T18:02:00Z', payload)
        self.assertEqual(first, again)
        self.assertEqual(len(self.registry.records()), 1)
        updated = land('2026-09-14T18:03:00Z', {**payload, 'timestamp': '2026-09-14T18:02:30Z'})
        self.assertNotEqual(updated['evidence_id'], first['evidence_id'])

    def test_daily_csv_adapter_and_file_hash(self):
        case = adapter_cases.PricesTests('test_fetch_daily_lands_csv_and_meta')
        case.setUp()
        case.land(self.staging)
        record, = self.register_landed()
        self.assertEqual(record['kind'], 'prices')
        self.assertEqual(record['data_as_of_precision'], 'date')
        raw = self.staging / 'prices/daily.csv'
        raw.write_bytes(raw.read_bytes() + b'corruption')
        with self.assertRaisesRegex(ValueError, 'hash/size'):
            self.registry.register(raw, entity_ids=['issuer:fixture'])

    def test_edgar_online_and_cached_text(self):
        for index_path in submissions_fixtures():
            harness = EdgarHarness(index_path, self.root / 'harness')
            edgar.fetch_filings(harness.cik, self.staging, n_10k=1, n_10q=1, n_8k=2,
                                ticker=harness.ticker, submissions_dir=harness.submissions_dir,
                                tenk_cache_dir=harness.tenk_hit, http_get=harness.http_get)
        records = self.register_landed()
        self.assertGreaterEqual(len(records), 7)
        self.assertEqual(sum(r['kind'] == 'filing' for r in records), 6)

    def test_edgar_metadata_only_failures_are_diagnostics(self):
        def broken(_):
            raise OSError('offline test outage')
        for index_path in submissions_fixtures():
            harness = EdgarHarness(index_path, self.root / 'harness')
            edgar.fetch_filings(harness.cik, self.staging, forms=('10-Q',), n_10q=1,
                                ticker=harness.ticker, submissions_dir=harness.submissions_dir,
                                tenk_cache_dir=harness.tenk_miss, http_get=broken)
        records = self.register_landed()
        failures = [r for r in records if r['status'] == 'error']
        self.assertEqual(len(failures), 1)
        self.assertIn('diagnostic sidecar', ' '.join(failures[0]['known_gaps']))
        self.assertEqual(failures[0]['kind'], 'filing')
