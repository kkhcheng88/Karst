"""Registration invariants and all 48 real public raw + meta fixture pairs."""
import copy
import gzip
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from karst.fetch.registry import EvidenceRegistry, load_meta, normalize_period
from karst.packet import build_packet, check_packet, confined
from karst.schema import ContractError, canonical, decode, digest

FIXTURES = Path(__file__).parent / 'fixtures'
SECURITY = {'security_id': 'security:TEST.US', 'issuer_id': 'issuer:test', 'ticker': 'TEST',
            'name': 'Synthetic test issuer', 'currency': 'USD', 'exchange': 'NASDAQ'}
AS_OF = '2026-09-15T23:00:00Z'


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = EvidenceRegistry(self.root / 'bundle')
        self.raw = self.root / 'response.json'
        self.meta_path = self.root / 'response.meta.json'
        self.meta = {'source': 'test-public', 'tool': 'public_document', 'kind': 'transcript',
                     'source_url': 'https://example.org/earnings', 'params': {'symbol': 'TEST'},
                     'entity_ids': [SECURITY['issuer_id']], 'published_at': '2026-09-14',
                     'published_at_precision': 'date', 'published_at_timezone': 'America/New_York',
                     'published_at_basis': 'Issuer publication date; hour unknown',
                     'fetched_at': '2026-09-15T12:00:00Z',
                     'period': {'fiscal_year': 2026, 'quarter': 2},
                     'truncated': {'is_truncated': False}, 'known_gaps': [], 'status': 'ok'}
        self.raw.write_bytes(b'{"paragraphs":["Prepared remarks", "Q&A"]}\n')

    def register(self):
        self.meta_path.write_bytes(canonical(self.meta))
        return self.registry.register(self.raw, self.meta_path)

    def packet(self, records, **kwargs):
        return build_packet(records, AS_OF, SECURITY, created_at=AS_OF,
                            required_kinds=('transcript',), root=self.registry.root, **kwargs)

    def test_version_idempotency_and_observation_receipts(self):
        first = self.register()
        self.assertEqual(first, self.register())
        self.meta['fetched_at'] = '2026-09-15T13:00:00Z'
        self.assertEqual(first, self.register())
        self.assertEqual(len(self.registry.records()), 1)
        receipts = [decode(line) for line in (self.registry.directory / 'observations.jsonl').read_bytes().splitlines()]
        self.assertEqual(len(receipts), 2)
        self.assertEqual(confined(self.registry.root, receipts[-1]['metadata']['path']).read_bytes(), self.meta_path.read_bytes())
        self.raw.write_bytes(b'{"paragraphs":["Corrected remarks"]}\n')
        corrected = self.register()
        self.assertEqual(corrected['source_id'], first['source_id'])
        self.assertNotEqual(corrected['source_version'], first['source_version'])
        self.assertEqual(corrected['supersedes'], first['evidence_id'])
        self.assertEqual(len(self.registry.records()), 2)

    def test_same_bytes_different_sources_preserve_identity(self):
        a = self.register()
        self.meta['source'] = 'another-public-source'
        b = self.register()
        self.assertEqual(a['artifact'], b['artifact'])
        self.assertNotEqual(a['evidence_id'], b['evidence_id'])

    def test_metadata_correction_is_a_new_version(self):
        a = self.register()
        self.meta['published_at'] = '2026-09-13'
        b = self.register()
        self.assertEqual(a['artifact'], b['artifact'])
        self.assertNotEqual(a['source_version'], b['source_version'])

    def test_timestamp_precision_and_replay_cutoff(self):
        record = self.register()
        self.assertEqual(record['published_at'], '2026-09-14')
        self.assertEqual(record['published_at_precision'], 'date')
        self.packet([record])
        with self.assertRaisesRegex(ContractError, 'ambiguous'):
            build_packet([record], '2026-09-14T15:00:00Z', SECURITY, created_at=AS_OF,
                         knowledge_basis='public_as_of_replay')
        self.meta['published_at'] = '2026-09-14 12:00:00'
        self.meta['published_at_precision'] = 'datetime'
        with self.assertRaises(ContractError):
            self.register()

    def test_missing_timezone_never_guessed_and_period_not_inferred(self):
        del self.meta['published_at_precision']
        self.meta['published_at'] = '2026-09-14 12:00:00'
        record = self.register()
        self.assertIsNone(record['published_at'])
        self.assertIsNone(record['data_as_of'])
        self.assertEqual(record['coverage'], self.meta['period'])
        self.assertEqual(record['period'], {'start': None, 'end': None})
        self.assertEqual(normalize_period({'from': '2026-09-14T18:00:00Z', 'to': 'open'}),
                         {'start': None, 'end': None})

    def test_empty_and_error_never_satisfy_transcript(self):
        for payload, status in [({'records': []}, 'empty'), ({'response': None, 'error': {'message': 'failed'}}, 'error')]:
            with self.subTest(status=status):
                self.meta['status'] = status
                self.raw.write_bytes(canonical(payload))
                record = self.register()
                packet = self.packet([record])
                self.assertEqual(packet['evidence_ids'], [])
                self.assertEqual(packet['diagnostic_ids'], [record['evidence_id']])
                self.assertEqual(packet['requirements'][0]['status'], 'missing')
                self.assertEqual(packet['dependencies'], [])

    def test_transcript_available_partial_missing_and_exact_dependencies(self):
        whole = self.register()
        packet = self.packet([whole])
        self.assertEqual(packet['requirements'][0]['status'], 'available')
        self.assertEqual(packet['dependencies'], [{'kind': 'evidence', 'id': whole['evidence_id'], 'version': whole['source_version']}])
        self.meta['truncated']['is_truncated'] = True
        partial = self.register()
        self.assertEqual(self.packet([partial])['requirements'][0]['status'], 'partial')
        self.assertEqual(self.packet([])['requirements'][0]['status'], 'missing')
        with self.assertRaisesRegex(ContractError, 'generated'):
            self.packet([whole], dependencies=packet['dependencies'])

    def test_private_payload_and_broker_tools_rejected(self):
        self.raw.write_bytes(b'{"account_id":"fake-private-account"}')
        with self.assertRaisesRegex(ContractError, 'Private'):
            self.register()
        self.raw.write_bytes(b'{"records":[1]}')
        self.meta.update(source='futu', tool='mcp__futu__account_positions')
        with self.assertRaisesRegex(ContractError, 'allowlist'):
            self.register()
        self.assertEqual(self.registry.records(), [])

    def test_corrupt_object_or_busy_writer_does_not_overwrite(self):
        record = self.register()
        obj = confined(self.registry.root, record['artifact']['path'])
        obj.write_bytes(b'corruption')
        with self.assertRaisesRegex(ContractError, 'corrupt'):
            self.register()
        self.assertEqual(obj.read_bytes(), b'corruption')
        lock = self.registry.directory / 'registry.lock'
        lock.touch()
        with self.assertRaisesRegex(ContractError, 'busy'):
            self.register()
        self.assertTrue(lock.exists())

    def test_raw_html_and_gzip_hash_semantics(self):
        raw = b'<html>Complete source</html>'
        self.raw = self.root / 'filing.raw.htm.gz'
        self.raw.write_bytes(gzip.compress(raw))
        self.meta.update(kind='filing', truncated={'is_truncated': True},
                         files={'raw': {'name': self.raw.name, 'sha256': digest(raw), 'bytes': len(raw)}})
        record = self.register()
        self.assertFalse(record['truncated'])
        self.assertEqual(record['artifact']['sha256'], digest(self.raw.read_bytes()))
        self.meta['files']['raw']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ContractError, 'hash/size'):
            self.register()

    def test_late_duplicate_and_invalid_fetched_time_are_not_silently_accepted(self):
        record = self.register()
        for records in ([record, record], [{**record, 'fetched_at': '2026-09-16T12:00:00Z'}]):
            with self.assertRaises(ContractError):
                self.packet(records)
        self.meta['fetched_at'] = '2026-09-15T12:00:00'
        with self.assertRaises(ContractError):
            self.register()


class RealFixtureRegistrationTests(unittest.TestCase):
    def test_all_48_public_raw_meta_pairs(self):
        metadata = sorted(FIXTURES.rglob('*.meta.json'))
        if not metadata:
            self.skipTest('Real public fixtures are available in the repository checkout')
        self.assertEqual(len(metadata), 48, 'Update the explicit fixture census when adding new fixtures')
        with tempfile.TemporaryDirectory() as directory:
            registry = EvidenceRegistry(directory)
            records, by_file, statuses = [], {}, Counter()
            for path in metadata:
                with self.subTest(fixture=path.name):
                    stem = str(path)[:-len('.meta.json')]
                    candidates = [Path(stem + suffix) for suffix in ('.txt', '.json', '.csv')]
                    raw = next((p for p in candidates if p.is_file()), None)
                    self.assertIsNotNone(raw, 'The raw fixture must be present; metadata-only is not this test')
                    meta, _ = load_meta(path)
                    # Identity resolution is an adapter responsibility; the test
                    # explicitly knows this company, and the calendar is market-wide.
                    ids = ['market:US'] if meta['params'].get('market') == 'US' else ['issuer:0001051627']
                    record = registry.register(raw, path, entity_ids=ids)
                    records.append(record)
                    by_file[path.name] = record
                    statuses[record['status']] += 1
                    self.assertEqual(confined(directory, record['artifact']['path']).read_bytes(), raw.read_bytes())
                    self.assertEqual(record['coverage'], meta['period'])
                    self.assertEqual(registry.register(raw, path, entity_ids=ids), record)
            self.assertEqual(statuses, {'ok': 45, 'empty': 2, 'error': 1})
            packet = build_packet(records, AS_OF, SECURITY, created_at=AS_OF, root=directory)
            self.assertEqual(len(check_packet(packet, records, directory)), 48)
            self.assertEqual(len(packet['diagnostic_ids']), 3)
            self.assertEqual(len(packet['dependencies']), 45)
            transcript = by_file['earning_call_transcript.FY2026Q2.meta.json']
            self.assertEqual(transcript['published_at_precision'], 'unknown')
            self.assertFalse(transcript['truncated'])  # 107/107 paragraphs, below the configured size cap.
            self.assertEqual(next(r['status'] for r in packet['requirements'] if r['kind'] == 'transcript'), 'available')
            self.assertEqual(by_file['earning_call_transcripts.list.meta.json']['kind'], 'filing_index')
            primary = by_file['0001437749-26-025061.8-K.meta.json']
            exhibit = by_file['0001437749-26-025061.8-K.EX-99.1.meta.json']
            self.assertNotEqual(primary['source_id'], exhibit['source_id'])
            self.assertEqual(primary['params']['accession'], exhibit['params']['accession'])
            self.assertIsNone(by_file['quote_market_snapshot.meta.json']['published_at'])
            self.assertEqual(by_file['fund_holder.meta.json']['status'], 'error')
            self.assertEqual(by_file['finance_calendar.meta.json']['entity_ids'], ['market:US'])
