"""Provider-neutral review: task out, challenges back, no second rating."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from karst.agents import adapters
from karst.agents.adapters import anthropic_adapter, openai_adapter
from karst.agents.protocol import get_research_protocol
from karst.agents.review import REVIEW_RESULT_SCHEMA, build_review_task, validate_review
from karst.agents.research import intake
from karst.packet import read_json
from karst.schema import ContractError
from karst.tests.v03_fixture import ROLE_META, build_bundle, citable, payload

BUDGET = {'max_output_tokens': 8000, 'max_cost_usd': 2.0, 'max_turns': 3}


def fake_transport(result):
    """Stands in for a real client: one final answer, in both wire shapes at once."""
    text = json.dumps(result, ensure_ascii=False)

    def send(request):
        assert request['instructions' if 'input' in request else 'system']
        return {'id': 'fake-1', 'usage': {'input_tokens': 1200, 'output_tokens': 300},
                'content': [{'type': 'text', 'text': text}],
                'output': [{'type': 'message',
                            'content': [{'type': 'output_text', 'text': text}]}]}
    return send


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.evidence_id = citable(self.bundle, self.records)
        self.research = intake(payload(self.packet, self.evidence_id), bundle=self.bundle,
                               clock=self.packet['created_at'], role_meta=ROLE_META)
        self.protocol = get_research_protocol('review')
        self.result = {
            'research_id': self.research['research_id'],
            'challenges': [{'target_layer': 'L3', 'claim': '改善主要來自一次性授權收入。',
                            'citations': [{'evidence_id': self.evidence_id, 'locator': 'L1-L3'}],
                            'severity': 'material'}],
            'verdict_on_dispute': {'verdict': 'challenges_research',
                                   'reasoning': '申報段落顯示分項口徑不一致。', 'citations': []},
            'new_evidence_requests': [{'request_id': 'req-transcript', 'layer': 'L3',
                                       'question': '最新逐字稿全文？', 'reason': '核實指引語氣。',
                                       'status': 'pending', 'evidence_ids': [], 'resolution': None}],
            'reviewer': {'role': 'reviewer', 'execution': 'interactive', 'provider': 'fixture',
                         'model_id': 'handwritten-test-fixture', 'prompt_version': 'research-protocol-v1'},
        }

    def test_valid_review_result_passes_and_carries_no_rating(self):
        self.assertEqual(validate_review(copy.deepcopy(self.result)), self.result)
        for forbidden in ('rating', 'execution_state', 'target_price', 'layers'):
            self.assertNotIn(forbidden, REVIEW_RESULT_SCHEMA['properties'])

    def test_malformed_results_are_refused(self):
        for mutate, pattern in (
                (lambda r: r.update(rating='negative'), 'review/'),
                (lambda r: r['challenges'][0].update(target_layer='L9'), 'review/'),
                (lambda r: r['challenges'][0].update(severity='fatal'), 'review/'),
                (lambda r: r['verdict_on_dispute'].update(verdict='sell'), 'review/'),
                (lambda r: r.pop('reviewer'), 'review/'),
                (lambda r: r['reviewer'].update(role='researcher'), 'review/'),
                (lambda r: r['new_evidence_requests'][0].update(status='fulfilled'), 'pending'),
                (lambda r: r['new_evidence_requests'].append(copy.deepcopy(r['new_evidence_requests'][0])), 'Duplicate')):
            bad = copy.deepcopy(self.result)
            mutate(bad)
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ContractError, pattern):
                validate_review(bad)

    def test_review_task_names_the_exact_research_version(self):
        task = self.root / 'review-task'
        context = build_review_task(self.research, '改善是否一次性？', [self.evidence_id],
                                    self.protocol, bundle=self.bundle, destination=task)
        self.assertEqual(context['research_id'], self.research['research_id'])
        self.assertEqual(context['research']['packet_id'], self.packet['packet_id'])
        self.assertEqual(read_json(task / 'output.schema.json'), REVIEW_RESULT_SCHEMA)
        self.assertEqual((task / 'review.md').read_text(encoding='utf-8'), self.protocol['text'])
        self.assertEqual(context['allowed_evidence_ids'], [self.evidence_id])
        with self.assertRaisesRegex(ContractError, 'dispute'):
            build_review_task(self.research, '  ', [self.evidence_id], self.protocol,
                              bundle=self.bundle, destination=self.root / 'x')
        with self.assertRaisesRegex(ContractError, 'review protocol'):
            build_review_task(self.research, 'd', [], get_research_protocol('research'),
                              bundle=self.bundle, destination=self.root / 'y')
        with self.assertRaisesRegex(ContractError, 'usable evidence'):
            build_review_task(self.research, 'd', ['ev-nope'], self.protocol,
                              bundle=self.bundle, destination=self.root / 'z')

    def test_adapters_run_the_staged_task_and_refuse_without_credentials(self):
        """The loop itself is covered in test_review_api; here: the task and the budget."""
        task = self.root / 'review-task'
        build_review_task(self.research, '改善是否一次性？', [self.evidence_id],
                          self.protocol, bundle=self.bundle, destination=task)
        for module, variable in ((anthropic_adapter, 'ANTHROPIC_API_KEY'),
                                 (openai_adapter, 'OPENAI_API_KEY')):
            with self.subTest(variable=variable):
                with self.assertRaisesRegex(ContractError, variable):
                    module.run(task, 'model-under-test', BUDGET, environ={})
                run = module.run(task, 'model-under-test', BUDGET,
                                 transport=fake_transport(self.result))
                self.assertEqual(run['execution'], 'api')
                self.assertEqual(sorted(run['usage']), sorted(adapters.USAGE_KEYS))
                self.assertIsNone(run['usage']['cost_usd'])  # unknown stays unknown
                self.assertEqual(run['result'], self.result)
        with self.assertRaisesRegex(ContractError, 'Budget'):
            anthropic_adapter.run(task, 'm', {'max_turns': 0},
                                  transport=fake_transport(self.result))


if __name__ == '__main__':
    unittest.main()
