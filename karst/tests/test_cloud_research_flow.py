"""Fresh cloud stores can become frozen research; clients can read it back."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from karst import service
from karst.fetch import edgar
from karst.schema import ContractError
from karst.store import Store
from karst.tests.test_fetch import EdgarHarness, submissions_fixtures
from karst.tests.v03_fixture import ROLE_META, SECURITY, build_bundle, citable, payload


class CloudInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.store = Store(self.root / 'state.sqlite')
        self.addCleanup(self.store.close)

    def test_refresh_bootstraps_missing_packet_and_saved_version_reads_back(self):
        h = EdgarHarness(submissions_fixtures()[0], self.root / 'offline')
        (self.bundle / 'packet.json').unlink()
        (self.bundle / 'evidence.json').unlink()
        result = service.refresh_sources(
            self.root, {**SECURITY, 'cik': h.cik}, ['filing'], store=self.store,
            bundle=self.bundle, staging=self.root / 'fresh',
            clients={'edgar': {'http_get': h.http_get, 'submissions_dir': h.submissions_dir,
                               'tenk_cache_dir': h.tenk_miss}})
        self.assertFalse(result['adapter_errors'])
        self.assertNotIn('packet_error', result)
        packet = json.loads((self.bundle / 'packet.json').read_text())
        self.assertEqual(packet['packet_id'], result['research_input']['packet_id'])
        analysis = payload(packet, citable(self.bundle, self.records))
        saved = service.save_research(self.store, self.bundle, analysis,
                                     subject=SECURITY['security_id'], role_meta=ROLE_META)
        context = service.get_research_context(self.store, self.bundle, SECURITY['security_id'],
                                              as_of_version=saved['version_id'])
        self.assertEqual(context['research']['valuation'], analysis['valuation'])
        self.assertEqual(context['research']['headline'], analysis['headline'])
        self.assertIsNotNone(context['calculation_receipt'])
        with self.assertRaises(ContractError):
            service.get_research_context(self.store, self.bundle, 'OTHER:ISSUER',
                                         as_of_version=saved['version_id'])

    def test_prepare_refuses_unknown_selection_and_preserves_old_snapshot(self):
        before = (self.bundle / 'packet.json').read_bytes()
        for ids in (['missing'], [self.records[0]['evidence_id']] * 2):
            with self.assertRaises(ContractError):
                service.prepare_research(self.bundle, SECURITY, evidence_ids=ids)
        with self.assertRaises(ContractError):
            service.prepare_research(self.bundle, SECURITY, as_of='2000-01-01T00:00:00Z')
        self.assertEqual(before, (self.bundle / 'packet.json').read_bytes())


class LiveIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.h = EdgarHarness(submissions_fixtures()[0], self.root / 'fixture')
        self.raw = json.loads((self.h.submissions_dir / f'CIK{self.h.cik}.json').read_text())
        self.raw['cik'] = int(self.h.cik)

    def test_no_local_cache_fetches_index_and_complete_filings(self):
        calls = []
        def get(url):
            calls.append(url)
            if url == f'https://data.sec.gov/submissions/CIK{self.h.cik}.json':
                return json.dumps(self.raw).encode()
            return self.h.http_get(url)
        out = self.root / 'run'
        result = edgar.fetch_filings(self.h.cik, out, http_get=get,
                                    submissions_dir=self.root / 'absent',
                                    tenk_cache_dir=self.h.tenk_miss, n_10q=1)
        self.assertTrue(result)
        self.assertTrue(all(r['status'] == 'ok' for r in result))
        self.assertEqual(calls[0], f'https://data.sec.gov/submissions/CIK{self.h.cik}.json')
        meta = json.loads((out / 'edgar' / f'CIK{self.h.cik}.submissions_slice.meta.json').read_text())
        self.assertIsNone(meta['local_snapshot_mtime_utc'])
        self.assertIn('live snapshot', meta['tool'])

    def test_refresh_failure_discloses_cached_basis_and_identity_mismatch_is_rejected(self):
        def fail(url):
            raise OSError('offline')
        index = edgar.submissions_index(self.h.cik, self.h.submissions_dir, fail, refresh=True)
        self.assertIn('offline', index['refresh_error'])
        self.assertIsNotNone(index['snapshot_mtime_utc'])
        wrong = copy.deepcopy(self.raw)
        wrong['cik'] = 1
        with self.assertRaisesRegex(ValueError, 'does not match'):
            edgar.submissions_index(self.h.cik, self.root / 'absent',
                                    lambda url: json.dumps(wrong).encode())


if __name__ == '__main__':
    unittest.main()
