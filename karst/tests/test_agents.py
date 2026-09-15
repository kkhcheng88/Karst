"""Role ownership, counter isolation, supplements and publication integration."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from karst.agents.assemble import (LAYERS, PAYLOADS, ROLES, UPSTREAM, assemble,
                                    collect_requests, fragment_schema)
from karst.agents.inputs import prepare_inputs, prompt
from karst.packet import build_packet, read_json
from karst.publish import publish, verify_release
from karst.schema import ContractError, canonical, digest, schema_hashes

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'synthetic'


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'
        shutil.copytree(EXAMPLE, self.bundle)
        self.records = read_json(self.bundle / 'evidence.json')
        old_packet = read_json(self.bundle / 'packet.json')
        self.packet = build_packet(self.records, old_packet['as_of'], old_packet['security'],
                                   created_at=old_packet['created_at'], root=self.bundle)
        self.research = read_json(self.bundle / 'research.json')
        self.research['packet_id'] = self.packet['packet_id']
        objection = copy.deepcopy(self.research['headline']['strongest_counter'])
        self.research['layers']['L6']['strongest_counter'] = copy.deepcopy(objection)
        self.fragments = {}
        for role in LAYERS:
            payload = {}
            for key in PAYLOADS[role]:
                if key in ('independent_view', 'strongest_counter', 'counter_response'):
                    payload[key] = copy.deepcopy(objection)
                elif key == 'challenges':
                    payload[key] = [copy.deepcopy(objection)]
                elif key == 'phases' and role != 'technical':
                    payload[key] = []
                else:
                    payload[key] = copy.deepcopy(self.research[key])
            self.fragments[role] = {
                'contract_version': '0.2.0', 'role': role, 'packet_id': self.packet['packet_id'],
                'read_evidence_ids': self.packet['evidence_ids'][:], 'input_hashes': {},
                'layers': {key: copy.deepcopy(self.research['layers'][key]) for key in LAYERS[role]},
                'payload': payload, 'supplement_requests': [],
            }
        self.run = {key: copy.deepcopy(self.research[key]) for key in
                    ('research_id', 'created_at', 'mode', 'strategy_version', 'mandate_version', 'method_version')}
        self.run['models'] = [{'role': role, 'provider': 'synthetic', 'model_id': 'handwritten-test-fixture',
                               'prompt_version': digest(prompt(role).encode())} for role in ROLES]
        self.rehash()

    def rehash(self):
        for role in ('industry', 'company', 'technical', 'counter_initial', 'valuation', 'counter', 'synthesis'):
            self.fragments[role]['input_hashes'] = {
                name: digest(canonical(self.fragments[name])) for name in UPSTREAM[role]}

    def assemble(self, **kwargs):
        return assemble(self.packet, self.records, {role: self.fragments[role] for role in ROLES},
                        bundle_root=self.bundle, run=self.run,
                        counter_initial=self.fragments['counter_initial'], **kwargs)

    def inputs(self, role, **kwargs):
        defaults = dict(bundle_root=self.bundle, destination=self.root / role,
                        allowed_evidence_ids=self.packet['evidence_ids'],
                        mandate={'version': 'test-v1', 'research_only': True, 'text': 'Independent public research, one month to one year.'},
                        discipline_sections={key: 'Reviewed discipline section' for key in (LAYERS[role] or ('counter',))},
                        scenario_questions=['What would invalidate the current narrative?'],
                        upstream={name: self.fragments[name] for name in UPSTREAM[role]})
        defaults.update(kwargs)
        return prepare_inputs(role, self.packet, self.records, **defaults)

    def test_owned_fragments_assemble_and_publish_without_contract_change(self):
        before = schema_hashes()
        for role in LAYERS:
            Draft202012Validator.check_schema(fragment_schema(role))
        result = self.assemble()
        for layer in ('L1', 'L2', 'L3', 'L4', 'L5'):
            self.assertEqual(result['layers'][layer], self.research['layers'][layer])
        self.assertEqual(result['valuation'], self.research['valuation'])
        self.assertIn('對最強反證的回應', result['layers']['L6']['conclusion']['text'])
        for name, value in [('packet', self.packet), ('evidence', self.records), ('research', result)]:
            (self.bundle / (name + '.json')).write_bytes(canonical(value))
        release = publish(self.bundle, self.root / 'releases')
        verify_release(release)
        self.assertTrue((release / 'index.html').is_file())
        self.assertEqual(before, schema_hashes())

    def test_counter_first_context_has_only_evidence_then_only_allowed_layers(self):
        # Deliberately place forbidden material beside the bundle inputs. Export
        # must not inherit any of these ambient files or the existing research.
        (self.bundle / 'private-ledger.json').write_text('PRIVATE_SENTINEL')
        (self.bundle / 'research.json').write_text('SYNTHESIS_SENTINEL')
        initial = self.inputs('counter_initial')
        final = self.inputs('counter')
        self.assertEqual(initial['upstream'], {})
        self.assertEqual(set(final['upstream']), set(UPSTREAM['counter']))
        for role in ('counter_initial', 'counter'):
            task = self.root / role
            files = [p for p in task.rglob('*') if p.is_file()]
            contents = b''.join(p.read_bytes() for p in files)
            self.assertNotIn(b'PRIVATE_SENTINEL', contents)
            self.assertNotIn(b'SYNTHESIS_SENTINEL', contents)
            self.assertFalse((task / 'research.json').exists())
            self.assertFalse((task / 'private-ledger.json').exists())

    def test_counter_cannot_receive_synthesis_or_rewrite_independent_view(self):
        extra = {name: self.fragments[name] for name in UPSTREAM['counter']}
        extra['synthesis'] = self.fragments['synthesis']
        with self.assertRaisesRegex(ContractError, 'allowlist'):
            self.inputs('counter', upstream=extra)
        self.fragments['counter']['payload']['independent_view']['text'] = 'Rewritten after reading analysts'
        self.rehash()
        with self.assertRaisesRegex(ContractError, 'sealed'):
            self.assemble()

    def test_role_cannot_overwrite_another_layer(self):
        self.fragments['synthesis']['layers']['L4'] = self.research['layers']['L4']
        with self.assertRaises(ContractError):
            self.assemble()

    def test_stale_packet_or_upstream_rejected(self):
        self.fragments['company']['packet_id'] = 'packet-old'
        with self.assertRaisesRegex(ContractError, 'packet version'):
            self.assemble()
        self.fragments['company']['packet_id'] = self.packet['packet_id']
        self.fragments['company']['layers']['L3']['conclusion']['text'] += ' Changed.'
        with self.assertRaisesRegex(ContractError, 'upstream hashes'):
            self.assemble()

    def test_unread_and_out_of_range_citations_rejected(self):
        self.fragments['industry']['layers']['L1']['conclusion']['citations'] = [
            {'evidence_id': 'not-in-packet', 'locator': 'L1'}]
        with self.assertRaisesRegex(ContractError, 'read log'):
            self.assemble()
        self.fragments['industry']['layers']['L1']['conclusion']['citations'][0] = {
            'evidence_id': self.packet['evidence_ids'][0], 'locator': 'L999999'}
        with self.assertRaisesRegex(ContractError, 'line range'):
            self.assemble()

    def test_counter_objection_cannot_be_dropped(self):
        self.fragments['synthesis']['payload']['headline']['strongest_counter']['text'] = 'Nothing to worry about'
        with self.assertRaisesRegex(ContractError, 'strongest objection'):
            self.assemble()

    def test_pending_supplement_needs_packet_registration_and_forbids_complete(self):
        request = {'request_id': 'req-inventory', 'layer': 'L3', 'question': 'Latest inventory?',
                   'reason': 'Changes sustainability', 'status': 'pending', 'evidence_ids': [], 'resolution': None}
        self.fragments['company']['supplement_requests'] = [request]
        self.rehash()
        self.assertEqual(collect_requests(self.fragments.values()), [request])
        with self.assertRaisesRegex(ContractError, 'Register outstanding'):
            self.assemble()
        self.packet = build_packet(self.records, self.packet['as_of'], self.packet['security'],
                                   created_at=self.packet['created_at'], supplement_requests=[request], root=self.bundle)
        for fragment in self.fragments.values():
            fragment['packet_id'] = self.packet['packet_id']
        self.rehash()
        self.assertEqual(self.assemble()['coverage'], 'partial')
        self.fragments['synthesis']['payload']['coverage'] = 'complete'
        with self.assertRaisesRegex(ContractError, 'Complete coverage'):
            self.assemble()

    def test_export_requires_reviewed_mandate_and_usable_sources(self):
        with self.assertRaisesRegex(ContractError, 'research-only'):
            self.inputs('company', mandate={'version': 'bad', 'text': 'Some text', 'holdings': []})
        with self.assertRaisesRegex(ContractError, 'usable evidence'):
            self.inputs('company', allowed_evidence_ids=['unregistered'])
        self.inputs('company')
        with self.assertRaises(FileExistsError):
            self.inputs('company')

    def test_output_is_validated_before_writing_and_never_overwrites(self):
        output = self.root / 'research.json'
        self.assemble(output=output)
        before = output.read_bytes()
        with self.assertRaises(FileExistsError):
            self.assemble(output=output)
        self.assertEqual(output.read_bytes(), before)
        output.unlink()
        self.run['models'] = []
        with self.assertRaisesRegex(ContractError, 'actual provider'):
            self.assemble(output=output)
        self.assertFalse(output.exists())
