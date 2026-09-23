"""A researcher's supplement requests are registered by save_research, not by hand."""
import tempfile
import unittest
from pathlib import Path

from karst import service, store as store_module
from karst.packet import read_json
from karst.schema import ContractError
from karst.tests.v03_fixture import FULL_SCOPE, ROLE_META, build_bundle, citable, payload

SUBJECT = 'FIXTURE:FIXTURE'


def request(request_id, layer='L3'):
    return {'request_id': request_id, 'layer': layer, 'question': '最新逐字稿全文？',
            'reason': '核實指引語氣。', 'status': 'pending', 'evidence_ids': [],
            'resolution': None}


class SaveRequestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.evidence_id = citable(self.bundle, self.records)
        self.store = store_module.init(self.root / 'karst.sqlite3')
        self.addCleanup(self.store.close)

    def save(self, analysis, previous=None):
        return service.save_research(self.store, self.bundle, analysis, subject=SUBJECT,
                                     expected_previous_version_id=previous, role_meta=ROLE_META,
                                     update_scope=FULL_SCOPE if previous else None)

    def test_a_payload_request_is_registered_and_then_accepted(self):
        analysis = payload(self.packet, self.evidence_id)
        analysis['supplement_requests'] = [request('req-transcript')]
        saved = self.save(analysis)
        packet = read_json(self.bundle / 'packet.json')
        self.assertEqual([item['request_id'] for item in packet['supplement_requests']],
                         ['req-transcript'])
        self.assertNotEqual(packet['packet_id'], self.packet['packet_id'])
        self.assertEqual(packet['previous_packet_id'], self.packet['previous_packet_id'])
        self.assertEqual(packet['as_of'], self.packet['as_of'])
        self.assertEqual(packet['created_at'], self.packet['created_at'])
        self.assertEqual(saved['payload']['packet_id'], packet['packet_id'])
        self.assertEqual(saved['status'], 'latest')
        context = service.get_research_context(self.store, self.bundle, SUBJECT)
        self.assertEqual([item['request_id'] for item in context['pending_supplements']],
                         ['req-transcript'])

    def test_an_already_registered_request_does_not_rebuild_the_packet(self):
        first = payload(self.packet, self.evidence_id)
        first['supplement_requests'] = [request('req-transcript')]
        saved = self.save(first)
        registered = read_json(self.bundle / 'packet.json')
        second = payload(registered, self.evidence_id)
        second['supplement_requests'] = [request('req-transcript')]
        second['open_questions'] = ['第二版:同一個補查請求仍未解決。']
        again = self.save(second, saved['version_id'])
        self.assertEqual(read_json(self.bundle / 'packet.json')['packet_id'],
                         registered['packet_id'])
        self.assertEqual(again['payload']['packet_id'], registered['packet_id'])

    def test_a_request_that_is_not_pending_is_refused_before_anything_is_stored(self):
        analysis = payload(self.packet, self.evidence_id)
        analysis['supplement_requests'] = [{**request('req-bad'), 'status': 'fulfilled'}]
        with self.assertRaises(ContractError):
            self.save(analysis)
        self.assertIsNone(self.store.latest_research(SUBJECT))
        self.assertEqual(read_json(self.bundle / 'packet.json')['packet_id'],
                         self.packet['packet_id'])


if __name__ == '__main__':
    unittest.main()
