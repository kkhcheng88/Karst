"""A research version owns its inputs: the company store may grow, the version may not.

Covers the four promises of KARST-245 — an old version republishes byte-identically
after new evidence arrives, the second release points back at the first, "what is
available now" and "what did that version use" are different questions with different
answers, and verification is reused only behind a fingerprint. Identity comes from the
shared fixture; nothing here is written for one stock.
"""
import tempfile
import unittest
from pathlib import Path

from karst import publish as publish_module, service, store as store_module
from karst.agents.research import Verified, intake
from karst.fetch.common import utc_now
from karst.fetch.registry import EvidenceRegistry
from karst.packet import build_packet, check_packet, confined, read_json
from karst.schema import ContractError, canonical
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

    def test_an_edited_conclusion_is_verified_again_and_refused(self):
        research = intake(payload(self.packet, self.evidence_id), bundle=self.bundle,
                          clock=utc_now, role_meta=ROLE_META)
        tampered = Verified(research)
        tampered.verified = research.verified  # a credential for the text before the edit
        tampered['packet_id'] = 'packet-not-this-one'
        with self.assertRaises(ContractError):
            self.save(tampered, previous=self.first['version_id'],
                      intake=lambda analysis, **_: analysis)
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

    def test_verification_is_reused_once_and_only_behind_the_fingerprint(self):
        """The credential removes the second identical check, not the checking."""
        calls = []
        real = service.check_packet

        def counted(packet, records, root):
            calls.append(packet['packet_id'])
            return real(packet, records, root)

        service.check_packet = counted
        self.addCleanup(setattr, service, 'check_packet', real)
        grown, _ = grow(self.bundle, '第二版的新摘錄。')
        second = self.save(payload(grown, self.evidence_id), previous=self.first['version_id'])
        self.assertEqual(calls, [])  # intake already checked exactly this content

        analysis = payload(grown, self.evidence_id)
        analysis['open_questions'] = ['第三版:同一批證據,另一個問題。']
        # A research that arrives without a credential (an injected intake cannot make
        # one) is checked in full, however well-formed it looks.
        plain = dict(intake(analysis, bundle=self.bundle, clock=utc_now, role_meta=ROLE_META))
        self.save(plain, previous=second['version_id'], intake=lambda given, **_: given)
        self.assertEqual(calls, [grown['packet_id']])


class SelectionTests(unittest.TestCase):
    """The cheap selection must name the same records as the verifying one."""

    def test_selected_matches_check_packet_order_and_membership(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle, packet, records = build_bundle(Path(directory))
            self.assertEqual([record['evidence_id'] for record in service._selected(packet, records)],
                             list(check_packet(packet, records, bundle)))
            with self.assertRaises(ContractError):
                service._selected({**packet, 'evidence_ids': ['ev-missing']}, records)


if __name__ == '__main__':
    unittest.main()
