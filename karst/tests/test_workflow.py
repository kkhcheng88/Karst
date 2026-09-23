import copy
from datetime import date, timedelta
import tempfile
from pathlib import Path
import unittest

from karst import service, workflow
from karst.schema import ContractError
from karst.store import Store
from karst.tests.test_longbridge import FakeClient


class Candles(FakeClient):
    def candlesticks(self, symbol, period, count, adjust, sessions=None):
        return self.history_candlesticks_by_date(symbol, period, adjust, None, None)

    def history_candlesticks_by_date(self, symbol, period, adjust, start, end, sessions=None):
        days = [date(2026, 1, 1) + timedelta(days=i) for i in range(100)]
        return [{'timestamp': f'{day}T20:00:00Z', 'open': 100+i, 'high': 102+i,
                 'low': 99+i, 'close': 101+i, 'volume': 1000}
                for i, day in enumerate(days) if day.weekday() < 5]


def seed(root, store, subject):
    security = dict(security_id=subject, issuer_id='issuer:'+subject, ticker=subject.split(':')[1], name=subject,
                    exchange='NYSE', currency='USD')
    service.refresh_sources(root, security, ['prices'], clients={'longbridge': Candles()}, store=store)


class WorkflowTests(unittest.TestCase):
    def test_report_is_an_impact_entry_without_forced_price_benchmark_or_company_dcf(self):
        result=workflow.plan(self.store,self.root,subject='industry:compute',kind='report',intent='add',
                             question='Does this report change the margin thesis?')
        self.assertEqual(result['completion']['deliverable'],'report_impact_assessment')
        self.assertEqual(result['completion']['blockers'],[])
        self.assertIn('report_trigger',[s['key'] for s in result['steps']])
        self.assertNotIn('comparison',[s['key'] for s in result['steps']])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'state.sqlite')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_intake_does_not_mutate_or_silently_stop_full_research_at_radar(self):
        args = dict(subject='NYSE:DEMO', kind='stock', question='Can earnings catch up?', benchmark='NYSE:INDEX')
        first = workflow.plan(self.store, self.root, **args, intent='analyze')
        self.assertEqual(first, workflow.plan(self.store, self.root, **args, intent='analyze'))
        self.assertEqual(first['completion']['deliverable'], 'investment_analysis')
        self.assertIn('save', [s['key'] for s in first['steps']])
        self.assertIsNone(self.store.get_entity('NYSE:DEMO'))
        self.assertFalse((self.root / 'companies').exists())
        added = workflow.plan(self.store, self.root, **args, intent='add')
        self.assertEqual(added['completion']['deliverable'], 'comparison_and_radar')

    def test_fund_and_first_update_do_not_claim_saved_company_research(self):
        args = dict(subject='NYSE:FUND', kind='fund', question='Market risk?', benchmark='NYSE:INDEX')
        result = workflow.plan(self.store, self.root, **args, intent='analyze')
        self.assertIn('non_company_formal_research_contract_not_yet_supported', result['completion']['blockers'])
        self.assertNotIn('save', [s['key'] for s in result['steps']])
        updated = workflow.plan(self.store, self.root, **args, intent='update')
        self.assertEqual(updated['completion']['deliverable'], 'comparison_and_radar')
        with self.assertRaises(ContractError):
            workflow.plan(self.store, self.root, subject='chain', kind='value_chain', intent='add', question='Why?')

    def test_registered_comparison_replays_and_checks_identity_currency_and_availability(self):
        for subject in ('NYSE:DEMO', 'NYSE:INDEX'):
            seed(self.root, self.store, subject)
        args = dict(weights={'NYSE:DEMO': 1.0}, benchmark='NYSE:INDEX', cutoff='2026-04-10',
                    selected_on='2026-04-11', as_of='2099-01-01T00:00:00Z', currency='USD')
        first = workflow.compare_registered(self.store, self.root, **args)
        self.assertEqual(first, workflow.compare_registered(self.store, self.root, **args))
        self.assertAlmostEqual(first['output']['members']['NYSE:DEMO']['beta63'], 1)
        for changes in ({'currency': 'EUR'}, {'as_of': '2026-04-11T00:00:00Z'},
                        {'as_of': '2099-01-01'}, {'weights': {'NYSE:MISSING': 1}}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                workflow.compare_registered(self.store, self.root, **(args | changes))
        from karst.packet import read_json
        import json
        bundle = service.company_paths(self.root, 'NYSE:DEMO')['bundle']
        # The store's identity lives in security.json; a bundle written before it
        # existed answers from its packet. A wrong identity is refused either way.
        for name in ('security.json', 'packet.json'):
            p = bundle / name
            value = read_json(p)
            (value if name == 'security.json' else value['security'])['security_id'] = 'NYSE:WRONG'
            p.write_text(json.dumps(value))
            with self.subTest(identity=name), self.assertRaises(ContractError):
                workflow.compare_registered(self.store, self.root, **args)
            (bundle / 'security.json').unlink(missing_ok=True)
