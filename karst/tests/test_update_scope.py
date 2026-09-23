"""Incremental scope control (KARST-262): an update rewrites only what its scope allows.

A daily-snapshot price event issues a scope of L4_price / L5 / L6; the save is held to
it. Identity comes from the shared fixture; nothing here is written for one stock.
"""
import copy
import tempfile
import unittest
from pathlib import Path

from karst import scope as scope_module, service, store as store_module
from karst.agents.research import PAYLOAD_KEYS
from karst.company_bundle import CompanyBundle
from karst.fetch.common import utc_now
from karst.schema import ContractError
from karst.tests.v03_fixture import ROLE_META, SECURITY, build_bundle, citable, payload

SUBJECT = SECURITY['security_id']
OUTSIDE = ('L1', 'L2', 'L3', 'L4')


class ScopedUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.evidence_id = citable(self.bundle, self.records)
        self.store = store_module.init(self.root / 'karst.sqlite3')
        self.addCleanup(self.store.close)
        self.analysis = payload(self.packet, self.evidence_id)
        self.analysis['plan']['next_review_at'] = self.analysis['target_date'] + 'T20:00:00Z'
        self.first = self.save(self.analysis)
        now = utc_now()
        CompanyBundle(self.bundle).save_daily_snapshot({
            'date': now[:10], 'checked_at': now, 'queue': {
                'layers': ['L5', 'L6'], 'since': now, 'base_version_id': self.first['version_id'],
                'reasons': [{'kind': 'price_event', 'events': [{'kind': 'sma200_cross'}]}]}})
        self.scope = service.plan_update(self.store, self.bundle, SUBJECT)['scope']

    def save(self, analysis, previous=None, update_scope=None):
        return service.save_research(self.store, self.bundle, analysis, subject=SUBJECT,
                                     expected_previous_version_id=previous,
                                     role_meta=ROLE_META, update_scope=update_scope)

    def price_update(self):
        """A price-event update that sends only what it touches: quote, TA and plan."""
        update = {key: copy.deepcopy(self.analysis[key])
                  for key in ('market', 'technical', 'plan', 'headline', 'rating',
                              'execution_state', 'coverage', 'target_date', 'open_questions',
                              'phases', 'read_evidence_ids', 'supplement_requests')}
        update['market']['price'] += 1
        update['headline']['change_since_last']['text'] = '收市跌穿 200 日線，只改技術與計劃。'
        update['layers'] = {name: copy.deepcopy(self.analysis['layers'][name]) for name in ('L5', 'L6')}
        update['layers']['L5']['conclusion']['text'] = '收市跌穿 200 日線。'
        update['layers']['L6']['conclusion']['text'] = '等待重新站回 200 日線。'
        return update

    def scoped(self, **extra):
        return {'scope_id': self.scope['scope_id'], **extra}

    def test_a_price_event_issues_a_price_scope(self):
        self.assertEqual(self.scope['layers'], ['L4_price', 'L5', 'L6'])
        self.assertEqual(self.scope['base_version_id'], self.first['version_id'])
        kinds = {trigger['kind'] for trigger in self.scope['triggers']}
        self.assertIn('daily_snapshot', kinds)
        self.assertEqual(self.store.get_update_scope(self.scope['scope_id']), self.scope)

    def test_out_of_scope_layers_are_carried_field_for_field(self):
        second = self.save(self.price_update(), self.first['version_id'], self.scoped())
        before, after = self.first['payload'], second['payload']
        for name in OUTSIDE:
            self.assertEqual(after['layers'][name], before['layers'][name])  # incl. assessed_at
        for key in ('valuation', 'modules'):
            self.assertEqual(after[key], before[key])
        rows = self.store.get_research(second['version_id'])['provenance']['layers']
        self.assertEqual({name: rows[name]['status'] for name in rows},
                         {**{name: 'carried' for name in OUTSIDE},
                          'L4_price': 'changed', 'L5': 'changed', 'L6': 'changed'})
        self.assertEqual(rows['L3']['assessed_at'], before['layers']['L3']['assessed_at'])
        self.assertEqual(rows['L3']['previous_version_id'], self.first['version_id'])
        self.assertTrue(rows['L5']['triggers'])

    def test_an_undeclared_change_outside_the_scope_is_refused_and_a_declared_one_recorded(self):
        update = self.price_update()
        update['layers']['L3'] = copy.deepcopy(self.analysis['layers']['L3'])
        update['layers']['L3']['conclusion']['text'] = '舊版毛利率口徑算錯，更正。'
        with self.assertRaisesRegex(ContractError, 'L3 is outside'):
            self.save(update, self.first['version_id'], self.scoped())
        self.assertEqual(self.store.latest_research(SUBJECT)['version_id'], self.first['version_id'])
        reason = '更正舊版毛利率口徑錯誤，與今日價格無關。'
        second = self.save(update, self.first['version_id'],
                           self.scoped(expansions={'L3': reason}))
        row = self.store.get_research(second['version_id'])['provenance']['layers']['L3']
        self.assertEqual((row['status'], row['reason']), ('expanded', reason))

    def test_a_valuation_rewrite_on_a_price_move_needs_an_expansion(self):
        update = self.price_update()
        update['valuation'] = copy.deepcopy(self.analysis['valuation'])
        update['valuation']['gap_reason'] = '改寫估值缺口。'
        with self.assertRaisesRegex(ContractError, 'L4 is outside'):
            self.save(update, self.first['version_id'], self.scoped())
        update['valuation'] = copy.deepcopy(self.analysis['valuation'])
        update['valuation']['implied_requirements']['text'] = '新價隱含收入加速三季。'
        second = self.save(update, self.first['version_id'], self.scoped())
        rows = self.store.get_research(second['version_id'])['provenance']['layers']
        self.assertEqual((rows['L4']['status'], rows['L4_price']['status']), ('carried', 'changed'))

    def test_an_in_scope_layer_needs_a_change_or_a_review(self):
        update = self.price_update()
        update['layers']['L5'] = copy.deepcopy(self.analysis['layers']['L5'])  # silent copy
        with self.assertRaisesRegex(ContractError, 'L5 is in this update.s scope'):
            self.save(update, self.first['version_id'], self.scoped())
        second = self.save(update, self.first['version_id'],
                           self.scoped(reviewed={'L5': [self.evidence_id]}))
        row = self.store.get_research(second['version_id'])['provenance']['layers']['L5']
        self.assertEqual((row['status'], row['evidence_ids']), ('reviewed', [self.evidence_id]))
        self.assertEqual(second['payload']['layers']['L5']['assessed_at'], row['assessed_at'])

    def test_an_update_without_a_system_scope_is_refused(self):
        update = self.price_update()
        for declaration, message in ((None, 'needs update_scope'),
                                     ({'scope_id': 'scope-made-up'}, 'Unknown update scope'),
                                     ({'full_reason': ' '}, 'full_reason')):
            with self.subTest(declaration=declaration), self.assertRaisesRegex(ContractError, message):
                self.save(update, self.first['version_id'], declaration)
        second = self.save(update, self.first['version_id'], self.scoped())
        # The scope was issued for the first version; the second cannot reuse it.
        with self.assertRaisesRegex(ContractError, 'another research version'):
            self.save(self.price_update() | {'open_questions': ['新問題？']},
                      second['version_id'], self.scoped())

    def test_provenance_reads_back_through_the_context(self):
        second = self.save(self.price_update(), self.first['version_id'], self.scoped())
        frozen = service.get_research_context(self.store, self.bundle, SUBJECT,
                                              as_of_version=second['version_id'])
        self.assertEqual(frozen['layer_provenance']['scope_id'], self.scope['scope_id'])
        current = service.get_research_context(self.store, self.bundle, SUBJECT)
        rows = {row['version_id']: row for row in current['versions']}
        self.assertEqual(rows[second['version_id']]['layers']['L3'],
                         {'assessed_at': self.first['payload']['layers']['L3']['assessed_at'],
                          'status': 'carried'})
        self.assertEqual(rows[self.first['version_id']]['layers']['L3']['status'], 'initial')
        # The next update has its own scope, built on the new version.
        self.assertEqual(current['update_plan']['scope']['base_version_id'], second['version_id'])


class ExpiryTests(unittest.TestCase):
    PLAN = {'subject': 'X:A', 'base_version_id': 'rv-old', 'plan_id': 'upd-x',
            'source_changes': [], 'reasons': []}

    def baseline(self, assessed, next_review_at=None):
        return {'version_id': 'rv-old', 'payload': {
            'layers': {f'L{i}': {'assessed_at': assessed} for i in range(1, 7)},
            'plan': {'next_review_at': next_review_at}}}

    def test_an_old_carried_layer_enters_the_next_scope(self):
        issued = scope_module.issue(self.PLAN, self.baseline('2026-05-01T00:00:00Z'),
                                    as_of='2026-07-01T00:00:00Z')
        expired = {t['layers'][0] for t in issued['triggers'] if t['kind'] == 'expired'}
        self.assertEqual(expired, {name for name, days in scope_module.MAX_CARRY_DAYS.items()
                                   if days < 61})
        self.assertIn('L5', issued['layers'])
        self.assertNotIn('L3', issued['layers'])

    def test_a_passed_verification_date_expires_the_layers_waiting_for_it(self):
        issued = scope_module.issue(self.PLAN, self.baseline('2026-06-28T00:00:00Z',
                                                             '2026-06-30T00:00:00Z'),
                                    as_of='2026-07-01T00:00:00Z')
        rules = {t['layers'][0]: t['rule'] for t in issued['triggers']}
        self.assertEqual(rules, {name: 'verification_passed'
                                 for name in scope_module.VERIFICATION_LAYERS})
        self.assertEqual(issued['layers'], ['L3', 'L4', 'L4_price', 'L6'])

    def test_every_analysis_key_has_one_owner(self):
        self.assertEqual(set(scope_module.OWNERS) | {'layers'}, set(PAYLOAD_KEYS))


if __name__ == '__main__':
    unittest.main()
