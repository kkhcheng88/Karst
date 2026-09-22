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
            return dict(subject=subject, sources_complete=True, history_ready=True,
                        failed=[], news_candidates=[])
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
            return dict(subject=subject, sources_complete=False, history_ready=True,
                        failed=[], news_candidates=[{'title':'Shared event',
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

    def test_interrupted_run_can_resume_without_refetching_success(self):
        def run(state, root, subject, **kwargs):
            if subject == 'EX:B':
                raise KeyboardInterrupt('worker interrupted')
            return dict(subject=subject, sources_complete=True, history_ready=True,
                        failed=[], news_candidates=[], observed_at='original-time')
        with patch.object(daily, 'refresh', side_effect=run), self.assertRaises(KeyboardInterrupt):
            daily.refresh_scope(self.state, self.root, 'monitor', since='2026-09-21')
        first = daily.recent_runs(self.root)[0]
        self.assertEqual(first['pending_subjects'], ['EX:B'])
        def good(state, root, subject, **kwargs):
            self.assertEqual(subject, 'EX:B')
            self.assertEqual(kwargs['since'], '2026-09-21')
            return dict(subject=subject, sources_complete=True, history_ready=True,
                        failed=[], news_candidates=[])
        with patch.object(daily, 'refresh', side_effect=good) as call:
            done = daily.refresh_scope(self.state, self.root, 'monitor', resume_run_id=first['run_id'])
        self.assertEqual(call.call_count, 1)
        self.assertEqual(done['results'][0]['observed_at'], 'original-time')
        self.assertEqual(done['intake_status'], 'ready_for_review')
        self.assertNotEqual(done['run_id'], first['run_id'])
        self.assertEqual(daily.get_run(self.root, first['run_id'])['intake_status'], 'in_progress')
        self.assertIsNone(self.state.latest_update_check('EX:B'))

    def test_resume_rejects_membership_drift_and_path_traversal(self):
        def run(state, root, subject, **kwargs):
            raise TimeoutError('down')
        with patch.object(daily, 'refresh', side_effect=run):
            first = daily.refresh_scope(self.state, self.root, 'monitor')
        payload = self.universe['payload']; payload['members'] = payload['members'][1:]
        knowledge.save(self.state, 'universe', 'monitor', payload, expected_version=self.universe['version'])
        from karst.schema import ContractError
        with self.assertRaises(ContractError):
            daily.refresh_scope(self.state, self.root, 'monitor', resume_run_id=first['run_id'])
        with self.assertRaises(ContractError):
            daily.get_run(self.root, '../state.db')

if __name__ == '__main__':
    unittest.main()
