import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from karst import daily, knowledge, store

class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = store.init(self.root / 'state.db')
        self.universe = knowledge.save(self.state, 'universe', 'monitor', {
            'name': 'Monitor', 'summary': 'Explicit coverage',
            'members': [dict(entity_id=x, name=x, kind=k, roles=['tracked'], comparison_groups=[])
                        for x, k in [('EX:A', 'company'), ('EX:B', 'fund'), ('theme', 'theme')]],
            'sources': [{'title': 'Scope', 'url': 'https://example.com/scope'}]})

    def tearDown(self):
        self.state.connection.close()
        self.temp.cleanup()

    def test_no_research_required_and_failure_does_not_skip_next_member(self):
        def run(state, root, subject, **kwargs):
            if subject == 'EX:A':
                raise TimeoutError('unavailable')
            return dict(subject=subject, news_coverage={'status':'ok'}, history_ready=True,
                        failed=[], adapter_errors={}, news_candidates=[])
        with patch.object(daily, 'refresh', side_effect=run) as mocked:
            result = daily.refresh_scope(self.state, self.root, 'monitor')
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(result['incomplete_subjects'], ['EX:A'])
        self.assertEqual(result['results'][1]['intake_status'], 'ready_for_review')
        self.assertFalse(result['analysis_complete'])
        self.assertIsNone(self.state.latest_update_check('EX:B'))
        saved = json.loads((self.root/'daily_runs'/(result['run_id']+'.json')).read_text())
        self.assertEqual(saved, result)

    def test_partial_news_not_complete_and_shared_url_keeps_both_subjects(self):
        def run(state, root, subject, **kwargs):
            return dict(subject=subject, news_coverage={'status':'partial'}, history_ready=True,
                        failed=[], adapter_errors={}, news_candidates=[{'title':'Shared event',
                        'source_url':'https://example.com/event', 'evidence_id':subject,'source_id':'news'}])
        with patch.object(daily, 'refresh', side_effect=run):
            result = daily.refresh_scope(self.state, self.root, 'monitor')
        self.assertEqual(result['incomplete_subjects'], ['EX:A','EX:B'])
        self.assertEqual(len(result['news_candidates']), 1)
        self.assertEqual(result['news_candidates'][0]['subjects'], ['EX:A','EX:B'])
        self.assertEqual(result['universe_version'], self.universe['version'])

    def test_latest_explicit_membership_is_used(self):
        payload = self.universe['payload']
        payload['members'] = payload['members'][1:]
        knowledge.save(self.state, 'universe', 'monitor', payload, expected_version=self.universe['version'])
        self.assertEqual([m['entity_id'] for m in daily.scope(self.state,'monitor')['members']], ['EX:B'])

if __name__ == '__main__':
    unittest.main()
