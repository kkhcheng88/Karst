"""A research version owns its inputs: the company store may grow, the version may not.

Covers the four promises of KARST-245 — an old version republishes byte-identically
after new evidence arrives, the second release points back at the first, "what is
available now" and "what did that version use" are different questions with different
answers — and the research intake of KARST-259: one save reads the packet once, checks
it once, and stores exactly what the old path stored. Identity comes from the shared
fixture; nothing here is written for one stock.
"""
import functools
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karst import company_bundle, publish as publish_module, service, store as store_module
from karst.agents import research as research_module
from karst.agents.research import intake
from karst.fetch.common import utc_now
from karst.fetch.registry import EvidenceRegistry
from karst.packet import build_packet, check_packet, confined, read_json
from karst.schema import ContractError, canonical, digest
from karst.tests import v03_fixture
from karst.tests.v03_fixture import ROLE_META, SECURITY, build_bundle, citable, payload

SUBJECT = SECURITY['security_id']


def grow(bundle, note):
    """Register one more source and move the company's packet on to it."""
    service.ingest_source(bundle, excerpt=note, entity_ids=[SUBJECT])
    records = EvidenceRegistry(bundle).records(contract_version='0.3.0')
    as_of = max(record['fetched_at'] for record in records)
    packet = build_packet(records, as_of, SECURITY, created_at=max(utc_now(), as_of),
                          root=bundle, contract_version='0.3.0')
    (bundle / 'evidence.json').write_bytes(canonical(records))
    (bundle / 'packet.json').write_bytes(canonical(packet))
    return packet, records


class VersionInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.releases = self.root / 'releases'
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.evidence_id = citable(self.bundle, self.records)
        self.store = store_module.init(self.root / 'karst.sqlite3')
        self.addCleanup(self.store.close)
        self.first = self.save(payload(self.packet, self.evidence_id))

    def save(self, analysis, previous=None, **kwargs):
        return service.save_research(self.store, self.bundle, analysis, subject=SUBJECT,
                                     expected_previous_version_id=previous,
                                     role_meta=ROLE_META, **kwargs)

    def publish(self, version):
        return service.publish_research(self.store, self.bundle, version['version_id'],
                                        self.releases)

    def test_a_saved_version_carries_the_packet_and_evidence_it_was_checked_against(self):
        stored = self.store.get_research(self.first['version_id'])
        self.assertEqual(stored['packet']['packet_id'], self.packet['packet_id'])
        self.assertEqual([record['evidence_id'] for record in stored['evidence']],
                         self.packet['evidence_ids'] + self.packet['diagnostic_ids'])

    def test_new_company_evidence_does_not_change_an_old_version_s_release(self):
        released = self.publish(self.first)
        self.assertEqual(released['inputs_from'], 'version_snapshot')
        page = Path(released['index_html']).read_bytes()

        grown, _ = grow(self.bundle, '新登記的一份摘錄,舊版不應該見到。')
        self.assertNotEqual(grown['packet_id'], self.packet['packet_id'])

        again = self.publish(self.first)
        self.assertEqual(again['publication_dir'], released['publication_dir'])
        self.assertEqual(Path(again['index_html']).read_bytes(), page)
        manifest = publish_module.verify_release(Path(again['publication_dir']))
        self.assertEqual(manifest['packet_id'], self.packet['packet_id'])
        # The frozen index is the one the release publishes, not today's registry.
        index = read_json(Path(again['publication_dir']) / 'inputs' / 'evidence.json')
        self.assertEqual(len(index), len(self.packet['evidence_ids']
                                         + self.packet['diagnostic_ids']))

    def test_the_second_release_points_back_at_the_first(self):
        first = self.publish(self.first)
        grown, _ = grow(self.bundle, '第二版讀到的新摘錄。')
        second = self.save(payload(grown, self.evidence_id), previous=self.first['version_id'])
        released = self.publish(second)
        self.assertNotEqual(released['publication_dir'], first['publication_dir'])
        manifest = read_json(Path(released['publication_dir']) / 'publication.json')
        self.assertEqual(manifest['previous_publication_id'], first['publication_id'])
        # Both directions are readable from the context and from the data room page.
        context = service.get_research_context(self.store, self.bundle, SUBJECT)
        rows = {row['version_id']: row for row in context['versions']}
        self.assertEqual(rows[second['version_id']]['previous_version_id'],
                         self.first['version_id'])
        self.assertEqual(rows[self.first['version_id']]['publication_id'],
                         first['publication_id'])
        room = Path(released['company_index']).read_text(encoding='utf-8')
        self.assertIn(f'指回 {first["publication_id"][:16]}', room)
        self.assertIn('無前版', room)

    def test_current_sources_and_as_of_research_sources_are_different_questions(self):
        grown, _ = grow(self.bundle, '登記在第一版之後的資料。')
        added = set(grown['evidence_ids']) - set(self.packet['evidence_ids'])
        self.assertTrue(added)

        current = service.get_research_context(self.store, self.bundle, SUBJECT)
        historic = service.get_research_context(self.store, self.bundle, SUBJECT,
                                                as_of_version=self.first['version_id'])
        self.assertEqual((current['sources_view'], historic['sources_view']),
                         ('current', 'as_of_research'))
        self.assertEqual(current['packet_id'], grown['packet_id'])
        self.assertEqual(historic['packet_id'], self.packet['packet_id'])
        now_ids = {row['evidence_id'] for row in current['sources']}
        then_ids = {row['evidence_id'] for row in historic['sources']}
        self.assertTrue(added <= now_ids)
        self.assertEqual(added & then_ids, set())

        found_now = service.search_evidence(self.bundle)
        found_then = service.search_evidence(self.bundle, store=self.store,
                                             as_of_version=self.first['version_id'])
        self.assertEqual((found_now['scope'], found_then['scope']),
                         ('current', 'as_of_research'))
        self.assertGreater(found_now['count'], found_then['count'])
        self.assertIn('as this version was validated against'.split()[-1],
                      found_then['note'])

    def test_a_version_without_a_snapshot_is_never_answered_with_todays_sources(self):
        legacy = self.store.save_research_version('OTHER:SUBJECT', {'headline': 'no snapshot'})
        with self.assertRaises(ContractError) as caught:
            service.get_research_context(self.store, self.bundle, 'OTHER:SUBJECT',
                                         as_of_version=legacy['version_id'])
        self.assertIn('not guessed', str(caught.exception))
        with self.assertRaises(ContractError):
            service.search_evidence(self.bundle, store=self.store, as_of_version='rv-nonexistent')

    def test_a_finished_research_object_is_not_a_payload(self):
        """Intake takes analysis only: a complete research (with its IDs) is refused."""
        research = intake(payload(self.packet, self.evidence_id), bundle=self.bundle,
                          clock=utc_now, role_meta=ROLE_META)
        with self.assertRaisesRegex(ContractError, 'engineering fields'):
            self.save(research, previous=self.first['version_id'])
        self.assertEqual(self.store.latest_research(SUBJECT)['version_id'],
                         self.first['version_id'])

    def test_an_edited_evidence_file_is_refused_on_save_and_on_publish(self):
        cited = confined(self.bundle, next(record['artifact']['path'] for record in self.records
                                           if record['evidence_id'] == self.evidence_id))
        original = cited.read_bytes()
        cited.write_bytes(original + '\n偷偷加一行。'.encode('utf-8'))
        with self.assertRaisesRegex(ContractError, 'hash/size mismatch'):
            self.save(payload(self.packet, self.evidence_id),
                      previous=self.first['version_id'])
        with self.assertRaisesRegex(ContractError, 'hash/size mismatch'):
            self.publish(self.first)
        cited.write_bytes(original)
        self.assertTrue(self.publish(self.first)['publication_dir'])

    def test_one_save_reads_the_packet_once_and_checks_it_once(self):
        """KARST-259: one read, one check, and the stored index is the checked one."""
        reads, checks = [], []

        def read(path):
            if Path(path).name == 'packet.json':
                reads.append(path)
            return read_json(path)

        def check(packet, records, root):
            checks.append(packet['packet_id'])
            return check_packet(packet, records, root)

        grown, _ = grow(self.bundle, '第二版的新摘錄。')
        analysis = payload(grown, self.evidence_id)
        analysis['supplement_requests'] = [{
            'request_id': 'req-once', 'layer': 'L3', 'question': '最新逐字稿全文？',
            'reason': '核實指引語氣。', 'status': 'pending', 'evidence_ids': [],
            'resolution': None}]
        with patch.object(company_bundle, 'read_json', read), \
                patch.object(research_module, 'check_packet', check):
            second = self.save(analysis, previous=self.first['version_id'])
        self.assertEqual(len(reads), 1)
        stored = self.store.get_research(second['version_id'])
        # The one check ran on the packet with the request registered, and that packet
        # is what the version froze and what the bundle now holds.
        self.assertEqual(checks, [stored['packet']['packet_id']])
        self.assertEqual(read_json(self.bundle / 'packet.json')['packet_id'],
                         stored['packet']['packet_id'])
        self.assertEqual([record['evidence_id'] for record in stored['evidence']],
                         stored['packet']['evidence_ids'] + stored['packet']['diagnostic_ids'])

    def test_a_conflicting_save_leaves_the_working_packet_as_it_was(self):
        analysis = payload(self.packet, self.evidence_id)
        analysis['supplement_requests'] = [{
            'request_id': 'req-late', 'layer': 'L3', 'question': '最新逐字稿全文？',
            'reason': '核實指引語氣。', 'status': 'pending', 'evidence_ids': [],
            'resolution': None}]
        stale = self.save(analysis, previous=None)  # first already exists: stale
        self.assertTrue(stale['conflict'])
        self.assertEqual(read_json(self.bundle / 'packet.json')['packet_id'],
                         self.packet['packet_id'])


CLOCK, LATER = '2031-01-02T03:04:05Z', '2031-02-03T04:05:06Z'
# Captured from the pre-KARST-259 save path (fingerprint credential, packet read four
# times) with the clocks above: the refactor must store exactly the same versions.
BEFORE = {
    '0.3.0': {'first': ('rv-24df85e143f45e7cb18474de824b3aa61b6a2d04513f54989f07740b56e3b15f',
                        '5c54cb61ef9312f64815caf41841ba08de21ba7b8770560e14412661b588247a'),
              'second': ('rv-057d7e194e47f295e601aeb07987b981eeacc82528ea875c6046f16314624b25',
                         '5c54cb61ef9312f64815caf41841ba08de21ba7b8770560e14412661b588247a')},
    '0.4.0': {'first': ('rv-e1a7e6b04cb07332e9cb44bbec82b0b719fd19f42c822dc88e65dac73aa73258',
                        'ce482d23d2f604e087f2f6f70a39437c72710d680f381d989a9983078e958aec'),
              'second': ('rv-d3afd4495424d1302b3ef4064d2f572c779b62c7ae77ae0434fd8fb4afd6e919',
                         'ce482d23d2f604e087f2f6f70a39437c72710d680f381d989a9983078e958aec')},
}


class SameVersionsTests(unittest.TestCase):
    """The same analysis, the same inputs and clock give the same version and receipt."""

    def run_contract(self, contract):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(v03_fixture, 'utc_now', lambda: CLOCK), \
                patch.object(service, 'utc_now', lambda: CLOCK):
            root = Path(directory)
            bundle, packet, records = build_bundle(root, contract_version=contract)
            store = store_module.init(root / 'karst.sqlite3')
            try:
                self.check_saves(store, bundle, packet, records, contract)
            finally:
                store.close()  # before the directory goes: Windows keeps an open file

    def check_saves(self, store, bundle, packet, records, contract):
        evidence_id = citable(bundle, records)
        cite = [{'evidence_id': evidence_id, 'locator': 'L1-L3'}]
        valuation = (v03_fixture.calculated_valuation(packet['as_of'], cite)
                     if contract >= '0.4.0' else None)
        first_payload = payload(packet, evidence_id, valuation=valuation)
        first_payload['supplement_requests'] = [{
            'request_id': 'req-x', 'layer': 'L3', 'question': 'q?', 'reason': 'r.',
            'status': 'pending', 'evidence_ids': [], 'resolution': None}]
        save = functools.partial(service.save_research, store, bundle,
                                 subject=SUBJECT, role_meta=ROLE_META)
        first = save(first_payload)
        second_payload = json.loads(canonical(first_payload))
        second_payload['layers']['L5']['conclusion']['text'] = 'updated technical view'
        with patch.object(service, 'utc_now', lambda: LATER):
            second = save(second_payload, expected_previous_version_id=first['version_id'])
            replay = save(second_payload, expected_previous_version_id=first['version_id'])
        got = {name: (version['version_id'],
                      digest(canonical(store.get_research(version['version_id'])['calc_receipt'])))
               for name, version in (('first', first), ('second', second))}
        self.assertEqual(got, BEFORE[contract])
        self.assertTrue(replay['idempotent_replay'])
        self.assertEqual(replay['version_id'], second['version_id'])
        layers = store.get_research(second['version_id'])['payload']['layers']
        self.assertEqual({name: layer['assessed_at'] for name, layer in layers.items()},
                         {**{name: CLOCK for name in layers}, 'L5': LATER})

    def test_contract_0_3(self):
        self.run_contract('0.3.0')

    def test_contract_0_4(self):
        self.run_contract('0.4.0')


if __name__ == '__main__':
    unittest.main()
