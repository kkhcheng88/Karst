"""Single main researcher: the model hands in analysis, the program owns the record."""
import copy
import tempfile
import unittest
from pathlib import Path

from karst.agents.protocol import get_research_protocol
from karst.agents.research import ANALYSIS_SCHEMA, export_task, intake
from karst.packet import read_json
from karst.schema import ContractError, canonical
from karst.tests.v03_fixture import ROLE_META, build_bundle, citable, payload


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.evidence_id = citable(self.bundle, self.records)
        self.payload = payload(self.packet, self.evidence_id)
        self.clock = self.packet['created_at']

    def take(self, payload_override=None, **kwargs):
        return intake(payload_override or self.payload, bundle=self.bundle, clock=self.clock,
                      role_meta=ROLE_META, **kwargs)

    def test_program_fills_every_engineering_field(self):
        research = self.take(previous_version_id='res-previous')
        self.assertEqual(research['contract_version'], '0.3.0')
        self.assertEqual(research['packet_id'], self.packet['packet_id'])
        self.assertEqual(research['previous_research_id'], 'res-previous')
        self.assertEqual(research['created_at'], self.clock)
        self.assertEqual(research['mode'], 'interactive_research')
        self.assertEqual(research['models'], ROLE_META)
        self.assertTrue(research['research_id'].startswith('res-'))
        for layer in research['layers'].values():
            self.assertEqual(layer['assessed_at'], self.clock)
        protocol = get_research_protocol('research')
        self.assertEqual(research['mandate_version'], protocol['version']['mandate'])
        self.assertEqual(research['strategy_version'], protocol['version']['strategy'])
        self.assertIn(protocol['version']['digest'][:12], research['method_version'])
        # Deterministic: the same payload and clock produce the same record.
        self.assertEqual(research, self.take(previous_version_id='res-previous'))

    def test_api_execution_is_recorded_as_api_research(self):
        meta = [{**ROLE_META[0], 'execution': 'api', 'provider': 'fixture-api'}]
        research = intake(self.payload, bundle=self.bundle, clock=lambda: self.clock, role_meta=meta)
        self.assertEqual(research['mode'], 'api_research')

    def test_payload_carrying_ids_or_versions_is_refused(self):
        for key, value in (('research_id', 'res-模型自稱'), ('packet_id', 'packet-old'),
                           ('created_at', '2026-09-16T00:00:00Z'), ('mode', 'api_research'),
                           ('models', []), ('contract_version', '0.3.0')):
            bad = {**copy.deepcopy(self.payload), key: value}
            with self.subTest(key=key), self.assertRaisesRegex(ContractError, 'engineering fields'):
                self.take(bad)
        bad = copy.deepcopy(self.payload)
        bad['layers']['L3']['assessed_at'] = self.clock
        with self.assertRaises(ContractError):
            self.take(bad)

    def test_citing_unread_or_unavailable_evidence_is_refused(self):
        bad = copy.deepcopy(self.payload)
        bad['layers']['L2']['read_evidence_ids'] = []
        with self.assertRaisesRegex(ContractError, 'read log'):
            self.take(bad)
        bad = copy.deepcopy(self.payload)
        bad['read_evidence_ids'] = [self.evidence_id]
        for layer in bad['layers'].values():
            layer['read_evidence_ids'] = [self.evidence_id]
        bad['market']['citations'] = [{'evidence_id': 'ev-not-in-packet', 'locator': 'L1'}]
        with self.assertRaisesRegex(ContractError, 'read log'):
            self.take(bad)
        bad = copy.deepcopy(self.payload)
        bad['layers']['L1']['conclusion']['citations'] = [
            {'evidence_id': self.evidence_id, 'locator': 'L999999'}]
        with self.assertRaisesRegex(ContractError, 'line range'):
            self.take(bad)

    def test_model_payload_needs_no_fragments_and_schema_hides_engineering_fields(self):
        self.assertNotIn('views', ANALYSIS_SCHEMA['properties']['technical']['properties'])
        for key in ('research_id', 'packet_id', 'created_at', 'mode', 'models'):
            self.assertNotIn(key, ANALYSIS_SCHEMA['properties'])
        self.assertNotIn('assessed_at', ANALYSIS_SCHEMA['$defs']['layer']['properties'])

    def test_export_task_stages_sources_prompt_and_schema_only(self):
        protocol = get_research_protocol('research')
        (self.bundle / 'private-ledger.json').write_text('PRIVATE_SENTINEL', encoding='utf-8')
        task = self.root / 'task'
        context = export_task(self.bundle, {'security': self.packet['security'],
                                            'question': '改善能否延續？'}, task, protocol)
        self.assertEqual(context['method']['version'], protocol['version'])
        self.assertEqual(read_json(task / 'output.schema.json'), protocol['output_schema'])
        self.assertEqual((task / 'prompt.md').read_text(encoding='utf-8'), protocol['text'])
        self.assertIsNone(context['previous_research'])
        blob = b''.join(p.read_bytes() for p in task.rglob('*') if p.is_file())
        self.assertNotIn(b'PRIVATE_SENTINEL', blob)
        self.assertFalse((task / 'research.json').exists())
        canonical(read_json(task / 'input.json'))
        with self.assertRaises(FileExistsError):
            export_task(self.bundle, {}, task, protocol)
        with self.assertRaisesRegex(ContractError, 'research or update'):
            export_task(self.bundle, {}, self.root / 'task2', get_research_protocol('review'))

    def test_update_task_carries_the_previous_version_summary(self):
        previous = self.take()
        context = export_task(self.bundle, {'security': self.packet['security']},
                              self.root / 'update-task', get_research_protocol('update'), previous)
        self.assertEqual(context['previous_research']['research_id'], previous['research_id'])
        self.assertEqual(context['previous_research']['rating'], previous['rating'])
        self.assertNotIn('layers', context['previous_research'])


if __name__ == '__main__':
    unittest.main()
