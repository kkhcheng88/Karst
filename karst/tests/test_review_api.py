"""API review path, offline: every transport is a fake, no SDK, key or network is touched."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from karst import service, store as store_module
from karst.agents.adapters import ResultUnknown, anthropic_adapter, openai_adapter
from karst.agents.research import intake
from karst.schema import ContractError, canonical
from karst.tests.v03_fixture import ROLE_META, build_bundle, citable, payload

SUBJECT = 'FIXTURE:FIXTURE'  # parameterized identity: the fixture security
DISPUTE = '改善是否一次性？'
BUDGET = {'max_turns': 4, 'max_output_tokens': 4000}


def anthropic_reply(blocks, usage=None):
    return {'id': 'msg-fake', 'content': blocks,
            'usage': usage or {'input_tokens': 1200, 'cache_read_input_tokens': 0,
                               'output_tokens': 300}}


def openai_reply(items, usage=None):
    return {'id': 'resp-fake', 'output': items,
            'usage': usage or {'input_tokens': 1200, 'output_tokens': 300,
                               'input_tokens_details': {'cached_tokens': 64}}}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.evidence_id = citable(self.bundle, self.records)
        self.research = intake(payload(self.packet, self.evidence_id), bundle=self.bundle,
                               clock=self.packet['created_at'], role_meta=ROLE_META)
        self.task = self.root / 'review-task'
        self.result = review_result(self.research['research_id'], self.evidence_id)
        from karst.agents.protocol import get_research_protocol
        from karst.agents.review import build_review_task
        build_review_task(self.research, DISPUTE, [self.evidence_id],
                          get_research_protocol('review'), bundle=self.bundle,
                          destination=self.task)

    def test_missing_credentials_is_an_explicit_error_without_a_call(self):
        for module, variable in ((anthropic_adapter, 'ANTHROPIC_API_KEY'),
                                 (openai_adapter, 'OPENAI_API_KEY')):
            with self.subTest(variable=variable), \
                 self.assertRaisesRegex(ContractError, variable):
                module.run(self.task, 'model-under-test', BUDGET, environ={})

    def test_the_model_reads_evidence_through_the_local_tools_only(self):
        seen = []

        def transport(request):
            seen.append(request)
            if len(seen) == 1:
                return anthropic_reply([{'type': 'tool_use', 'id': 'tu-1',
                                         'name': 'list_evidence', 'input': {}}])
            if len(seen) == 2:
                return anthropic_reply([{'type': 'tool_use', 'id': 'tu-2',
                                         'name': 'read_evidence',
                                         'input': {'evidence_id': self.evidence_id,
                                                   'offset': 0, 'limit': 3}}])
            return anthropic_reply([{'type': 'text',
                                     'text': '```json\n' + json.dumps(self.result) + '\n```'}])

        run = anthropic_adapter.run(self.task, 'model-under-test', BUDGET, transport=transport)
        self.assertEqual(run['provider'], 'anthropic')
        self.assertEqual(run['execution'], 'api')
        self.assertEqual(run['result'], self.result)
        self.assertEqual(run['usage']['input_tokens'], 3600)  # accumulated over the turns
        self.assertIsNone(run['usage']['cost_usd'])  # unknown stays unknown
        tool_results = [block for message in seen[-1]['messages']
                        for block in (message['content'] if isinstance(message['content'], list) else [])
                        if isinstance(block, dict) and block.get('type') == 'tool_result']
        self.assertEqual(len(tool_results), 2)
        self.assertFalse(any(block['is_error'] for block in tool_results))
        read_back = json.loads(tool_results[1]['content'])
        self.assertEqual(read_back['locator'], 'L1-L3')
        self.assertTrue(read_back['text'])

    def test_a_tool_error_is_returned_to_the_model_not_raised(self):
        turns = []

        def transport(request):
            turns.append(request)
            if len(turns) == 1:
                return anthropic_reply([{'type': 'tool_use', 'id': 'tu-1', 'name': 'read_evidence',
                                         'input': {'evidence_id': 'ev-not-staged'}}])
            return anthropic_reply([{'type': 'text', 'text': json.dumps(self.result)}])

        run = anthropic_adapter.run(self.task, 'm', BUDGET, transport=transport)
        errored = [block for block in turns[-1]['messages'][-1]['content']
                   if block.get('is_error')]
        self.assertEqual(len(errored), 1)
        self.assertIn('not staged', errored[0]['content'])
        self.assertEqual(run['result'], self.result)

    def test_openai_wire_runs_the_same_task_shape(self):
        turns = []

        def transport(request):
            turns.append(request)
            if len(turns) == 1:
                return openai_reply([{'type': 'function_call', 'call_id': 'call-1',
                                      'name': 'list_evidence', 'arguments': '{}'}])
            return openai_reply([{'type': 'message', 'content': [
                {'type': 'output_text', 'text': json.dumps(self.result)}]}])

        run = openai_adapter.run(self.task, 'model-under-test', BUDGET, transport=transport)
        self.assertEqual(run['provider'], 'openai')
        self.assertEqual(run['result'], self.result)
        self.assertEqual(run['usage']['cached_input_tokens'], 128)
        self.assertEqual([item['type'] for item in turns[-1]['input']
                          if isinstance(item, dict) and 'type' in item],
                         ['function_call', 'function_call_output'])

    def test_turn_limit_and_budget_shape_are_enforced(self):
        endless = lambda request: anthropic_reply(  # noqa: E731
            [{'type': 'tool_use', 'id': 'tu', 'name': 'list_evidence', 'input': {}}])
        with self.assertRaisesRegex(ContractError, 'Turn limit'):
            anthropic_adapter.run(self.task, 'm', {'max_turns': 2}, transport=endless)
        with self.assertRaisesRegex(ContractError, 'Budget'):
            anthropic_adapter.run(self.task, 'm', {'max_turns': -1}, transport=endless)
        with self.assertRaisesRegex(ContractError, 'Input token budget'):
            anthropic_adapter.run(self.task, 'm', {'max_input_tokens': 1000},
                                  transport=endless)

    def test_a_sent_request_with_an_unknown_outcome_is_not_a_plain_failure(self):
        def transport(request):
            raise TimeoutError('read timed out')

        with self.assertRaises(ResultUnknown):
            anthropic_adapter.run(self.task, 'm', BUDGET, transport=transport)

    def test_a_result_that_misses_the_schema_is_refused(self):
        broken = copy.deepcopy(self.result)
        broken['challenges'][0]['severity'] = 'fatal'
        with self.assertRaisesRegex(ContractError, 'result/'):
            anthropic_adapter.run(self.task, 'm', BUDGET, transport=lambda request:
                                  anthropic_reply([{'type': 'text', 'text': json.dumps(broken)}]))
        with self.assertRaisesRegex(ContractError, 'no JSON object'):
            anthropic_adapter.run(self.task, 'm', BUDGET, transport=lambda request:
                                  anthropic_reply([{'type': 'text', 'text': '我讀完了。'}]))


def review_result(research_id, evidence_id):
    return {
        'research_id': research_id,
        'challenges': [{'target_layer': 'L3', 'claim': '改善主要來自一次性授權收入。',
                        'citations': [{'evidence_id': evidence_id, 'locator': 'L1-L3'}],
                        'severity': 'material'}],
        'verdict_on_dispute': {'verdict': 'challenges_research',
                               'reasoning': '申報段落顯示分項口徑不一致。', 'citations': []},
        'new_evidence_requests': [],
        'reviewer': {'role': 'reviewer', 'execution': 'api', 'provider': 'anthropic',
                     'model_id': 'model-under-test', 'prompt_version': 'research-protocol-v1'},
    }


class ServiceReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.evidence_id = citable(self.bundle, self.records)
        self.store = store_module.init(self.root / 'karst.sqlite3')
        self.addCleanup(self.store.close)
        research = intake(payload(self.packet, self.evidence_id), bundle=self.bundle,
                          clock=self.packet['created_at'], role_meta=ROLE_META)
        (self.bundle / 'research.json').write_bytes(canonical(research))
        self.version = self.store.save_research_version(SUBJECT, research,
                                                        as_of=self.packet['as_of'])
        self.result = review_result(research['research_id'], self.evidence_id)

    def request(self, transport, dispute=DISPUTE, task='task'):
        return service.request_review(
            self.store, subject=SUBJECT, version_id=self.version['version_id'],
            dispute=dispute, evidence_ids=[self.evidence_id],
            reviewer={'execution': 'api', 'provider': 'anthropic', 'model': 'model-under-test'},
            bundle=self.bundle, task_dir=self.root / task, transport=transport, budget=BUDGET)

    def final(self, result):
        return lambda request: anthropic_reply([{'type': 'text', 'text': json.dumps(result)}])

    def test_success_stores_the_validated_result_and_the_usage(self):
        job = self.request(self.final(self.result))
        self.assertEqual(job['status'], 'done')
        self.assertEqual(job['result_ref']['verdict_on_dispute']['verdict'], 'challenges_research')
        self.assertEqual(job['usage']['output_tokens'], 300)
        self.assertTrue((self.root / 'task' / 'input.json').is_file())
        context = service.get_research_context(self.store, self.bundle, SUBJECT)
        summary = context['latest_review']
        self.assertEqual(summary['verdict'], 'challenges_research')
        self.assertEqual(summary['strongest_challenge']['target_layer'], 'L3')
        self.assertEqual(summary['new_evidence_requests'], 0)

    def test_a_rejected_result_fails_the_job_without_storing_it(self):
        broken = copy.deepcopy(self.result)
        broken['new_evidence_requests'] = [{'request_id': 'req-1', 'layer': 'L3',
                                            'question': 'q', 'reason': 'r',
                                            'status': 'fulfilled', 'evidence_ids': [],
                                            'resolution': None}]
        job = self.request(self.final(broken), dispute='另一個爭議', task='task-2')
        self.assertEqual(job['status'], 'failed')
        self.assertIsNone(job['result_ref'])
        self.assertIn('rejected', job['error'])

    def test_a_sent_request_with_an_unknown_outcome_waits_for_a_human(self):
        def transport(request):
            raise ConnectionError('connection reset after send')

        job = self.request(transport, dispute='第三個爭議', task='task-3')
        self.assertEqual(job['status'], 'needs_check')
        self.assertIn('unknown', job['error'])
        self.assertIsNone(job['result_ref'])

    def test_the_same_dispute_is_not_paid_for_twice(self):
        first = self.request(self.final(self.result))
        calls = []

        def transport(request):
            calls.append(request)
            return anthropic_reply([{'type': 'text', 'text': json.dumps(self.result)}])

        again = self.request(transport)
        self.assertEqual(again['job_id'], first['job_id'])
        self.assertEqual(calls, [])  # the adapter was never called a second time
        # A failed job is not a paid result: the same dispute may be tried again.
        failed = self.request(self.final({'nonsense': True}), dispute='會失敗的爭議',
                              task='task-4')
        self.assertEqual(failed['status'], 'failed')
        retry = self.request(self.final(self.result), dispute='會失敗的爭議', task='task-5')
        self.assertNotEqual(retry['job_id'], failed['job_id'])
        self.assertEqual(retry['status'], 'done')

    def test_interactive_execution_still_returns_a_pending_job(self):
        job = service.request_review(self.store, subject=SUBJECT,
                                     version_id=self.version['version_id'],
                                     dispute='互動覆核', evidence_ids=[],
                                     reviewer={'execution': 'interactive'})
        self.assertEqual(job['status'], 'pending')
        self.assertEqual(service.claim_review(self.store, job['job_id'], 'client-b')['status'],
                         'running')


if __name__ == '__main__':
    unittest.main()
