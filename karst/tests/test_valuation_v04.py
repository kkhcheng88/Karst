"""Contract 0.4 valuation: method dispatch, dated discounting, bridges, sensitivity, reverse solve.

Every expected number is either a hand computation written out in the test or an
invariant (scale equivalence, monotonicity, a refused mix-up). No golden file, and no
company identity: the fixture carries the ticker, the tests carry arithmetic.
"""
import copy
import tempfile
import unittest
from pathlib import Path

from karst import calculations, service
from karst.agents.research import intake
from karst.packet import check_packet, check_research, read_json
from karst.publish import publish, verify_release
from karst.schema import ContractError, canonical, digest
from karst.tests.v03_fixture import (BRIDGE, LEGACY_DCF, LEGACY_PER_SHARE, ROLE_META,
                                     build_bundle, calculated_valuation, citable,
                                     dated_dcf, ev_multiple, forward_pe, payload)

VALUATION_DATE = '2026-01-01'
# 2026-01-01 -> 2026-04-02 is 91 days; -> 2027-04-02 is 456 days (2026 is not a leap year).
STUB_DAYS, YEAR_TWO_DAYS = 91, 456
STUB_MODEL = {
    'method': 'fcff_dcf_dated', 'currency': 'USD', 'scale': 'absolute',
    'model': {'valuation_date': VALUATION_DATE, 'day_count': 'act/365',
              'timing': 'end_of_period', 'discount_rate': 0.10,
              'flows': [{'date': '2026-04-02', 'amount': 50.0, 'is_stub': True,
                         'label': '首三個月的 stub'},
                        {'date': '2027-04-02', 'amount': 100.0, 'is_stub': False,
                         'label': '首個完整年'}],
              'terminal': {'date': '2027-04-02', 'final_expansion_fcff': 100.0,
                           'normalized_fcff': 120.0, 'growth': 0.02,
                           'basis': '正常化後的成熟現金流。'}},
    'bridge': copy.deepcopy(BRIDGE),
}


def per_share(calculation):
    return calculations.calculate_valuation(calculation)["outputs"]["fair_value_per_share"]


class LegacyRegressionTests(unittest.TestCase):
    """The 0.2 / 0.3 annual convention keeps its exact meaning under the new dispatcher."""

    def test_annual_convention_reproduces_the_recorded_per_share(self):
        self.assertEqual(calculations.fcff_dcf(LEGACY_DCF)["fair_value_per_share"],
                         LEGACY_PER_SHARE)
        receipt = calculations.calculate_valuation(LEGACY_DCF)
        self.assertEqual(receipt["method"], "fcff_dcf")
        self.assertEqual(receipt["outputs"]["fair_value_per_share"], LEGACY_PER_SHARE)
        self.assertEqual(receipt["inputs_digest"], digest(canonical(LEGACY_DCF)))
        # A 0.3 calculation carries no scale at all and still means absolute.
        old = {key: value for key, value in LEGACY_DCF.items() if key != "scale"}
        self.assertEqual(calculations.fcff_dcf(old)["fair_value_per_share"], LEGACY_PER_SHARE)

    def test_millions_and_absolute_agree_per_share_and_report_absolute_money(self):
        millions = {**LEGACY_DCF, "scale": "millions",
                    "cashflows": [flow / 1e6 for flow in LEGACY_DCF["cashflows"]],
                    "cash": LEGACY_DCF["cash"] / 1e6, "debt": LEGACY_DCF["debt"] / 1e6,
                    "diluted_shares": LEGACY_DCF["diluted_shares"] / 1e6}
        absolute = calculations.fcff_dcf(LEGACY_DCF)
        scaled = calculations.fcff_dcf(millions)
        self.assertAlmostEqual(scaled["fair_value_per_share"], LEGACY_PER_SHARE, places=9)
        # Money is reported absolute either way: equity value, not "equity value in millions".
        self.assertAlmostEqual(scaled["equity_value"], absolute["equity_value"], places=3)
        self.assertAlmostEqual(scaled["enterprise_value"], absolute["enterprise_value"], places=3)
        self.assertAlmostEqual(scaled["terminal_share_of_enterprise_value"],
                               absolute["terminal_share_of_enterprise_value"], places=12)

    def test_unknown_method_and_unknown_scale_are_refused(self):
        with self.assertRaisesRegex(ContractError, "Unknown valuation method"):
            calculations.calculate_valuation({**LEGACY_DCF, "method": "vibes"})
        with self.assertRaisesRegex(ContractError, "Unknown money scale"):
            calculations.fcff_dcf({**LEGACY_DCF, "scale": "lakhs"})


class DatedDiscountingTests(unittest.TestCase):
    """Hand-computed stub example: 91 days, then 456 days, terminal at the same date."""

    def expected(self, timing):
        rate, growth = 0.10, 0.02
        if timing == "end_of_period":
            years = [STUB_DAYS / 365, YEAR_TWO_DAYS / 365]
        else:  # midpoint of each period measured from the valuation date
            years = [STUB_DAYS / 2 / 365, (STUB_DAYS + YEAR_TWO_DAYS) / 2 / 365]
        explicit = 50.0 / (1 + rate) ** years[0] + 100.0 / (1 + rate) ** years[1]
        terminal = 120.0 * (1 + growth) / (rate - growth)  # 122.4 / 0.08 = 1530.0
        present_terminal = terminal / (1 + rate) ** (YEAR_TWO_DAYS / 365)
        enterprise = explicit + present_terminal
        # bridge: +100 cash +20 non-operating -60 debt -10 minority -0 redeemable -5 converts
        equity = enterprise + 45.0
        return enterprise, equity, equity / 50.0

    def test_end_of_period_matches_the_hand_computation(self):
        outputs = calculations.calculate_valuation(STUB_MODEL)["outputs"]
        enterprise, equity, value = self.expected("end_of_period")
        self.assertAlmostEqual(outputs["enterprise_value"], enterprise, places=9)
        self.assertAlmostEqual(outputs["equity_value"], equity, places=9)
        self.assertAlmostEqual(outputs["fair_value_per_share"], value, places=9)
        self.assertAlmostEqual(outputs["terminal_value_at_terminal_date"], 1530.0, places=9)
        self.assertAlmostEqual(outputs["stub_years"], STUB_DAYS / 365, places=12)
        self.assertAlmostEqual(outputs["years_to_terminal"], YEAR_TWO_DAYS / 365, places=12)
        # The terminal is normalized apart from the last expansion year, and says so.
        self.assertAlmostEqual(outputs["normalization_step"], 1.2, places=12)

    def test_mid_period_discounts_earlier_and_matches_its_own_hand_computation(self):
        model = copy.deepcopy(STUB_MODEL)
        model["model"]["timing"] = "mid_period"
        outputs = calculations.calculate_valuation(model)["outputs"]
        _, _, value = self.expected("mid_period")
        self.assertAlmostEqual(outputs["fair_value_per_share"], value, places=9)
        self.assertGreater(outputs["fair_value_per_share"], per_share(STUB_MODEL))

    def test_terminal_date_is_discounted_from_its_own_date(self):
        later = copy.deepcopy(STUB_MODEL)
        later["model"]["terminal"]["date"] = "2029-04-02"
        self.assertLess(per_share(later), per_share(STUB_MODEL))
        earlier = copy.deepcopy(STUB_MODEL)
        earlier["model"]["terminal"]["date"] = "2026-04-02"
        with self.assertRaisesRegex(ContractError, "terminal date cannot precede"):
            per_share(earlier)

    def test_a_past_or_out_of_order_cashflow_is_refused(self):
        past = copy.deepcopy(STUB_MODEL)
        past["model"]["flows"][0]["date"] = "2025-12-31"
        with self.assertRaisesRegex(ContractError, "past"):
            per_share(past)
        same_day = copy.deepcopy(STUB_MODEL)
        same_day["model"]["flows"][0]["date"] = VALUATION_DATE
        with self.assertRaisesRegex(ContractError, "past"):
            per_share(same_day)
        unordered = copy.deepcopy(STUB_MODEL)
        unordered["model"]["flows"][1]["date"] = "2026-03-01"
        with self.assertRaisesRegex(ContractError, "strictly increase"):
            per_share(unordered)

    def test_only_the_first_period_can_be_a_stub_and_the_terminal_must_be_valuable(self):
        late_stub = copy.deepcopy(STUB_MODEL)
        late_stub["model"]["flows"][1]["is_stub"] = True
        with self.assertRaisesRegex(ContractError, "first period"):
            per_share(late_stub)
        for change in ({"normalized_fcff": -1.0}, {"growth": 0.10}):
            broken = copy.deepcopy(STUB_MODEL)
            broken["model"]["terminal"].update(change)
            with self.subTest(change=change), self.assertRaises(ContractError):
                per_share(broken)


class BridgeTests(unittest.TestCase):
    """An equity multiple and an enterprise multiple never share a bridge."""

    def setUp(self):
        self.ev = ev_multiple("2026-01-01", "2026-12-31")
        self.pe = forward_pe("2026-01-01", "2026-12-31", "2026-01-01", "2026-12-31")

    def test_enterprise_multiple_bridges_to_equity(self):
        outputs = calculations.calculate_valuation(self.ev)["outputs"]
        self.assertAlmostEqual(outputs["enterprise_value"], 120.0 * 11.0)
        self.assertAlmostEqual(outputs["equity_value"], 120.0 * 11.0 + 45.0)
        self.assertAlmostEqual(outputs["fair_value_per_share"], (120.0 * 11.0 + 45.0) / 50.0)

    def test_equity_multiple_never_adds_cash_or_debt(self):
        outputs = calculations.calculate_valuation(self.pe)["outputs"]
        # 3.00 EPS x 14 = 42.00 at the horizon, discounted one year at 10%.
        self.assertAlmostEqual(outputs["value_per_share_at_horizon"], 42.0)
        self.assertAlmostEqual(outputs["fair_value_per_share"],
                               42.0 / 1.10 ** (364 / 365), places=9)
        self.assertTrue(outputs["discounted"])
        self.assertAlmostEqual(outputs["equity_value"],
                               outputs["fair_value_per_share"] * 50.0, places=9)

    def test_mixing_the_two_bridges_is_refused_by_the_calculator(self):
        with self.assertRaisesRegex(ContractError, "double count"):
            calculations.calculate_valuation({**self.pe, "bridge": copy.deepcopy(BRIDGE)})
        with self.assertRaisesRegex(ContractError, "enterprise method"):
            calculations.calculate_valuation({**self.ev, "equity": {"diluted_shares": 50.0}})
        wrong_basis = copy.deepcopy(self.pe)
        wrong_basis["model"]["multiple_basis"] = "enterprise_value"
        with self.assertRaisesRegex(ContractError, "multiple_basis=equity"):
            calculations.calculate_valuation(wrong_basis)
        wrong_basis = copy.deepcopy(self.ev)
        wrong_basis["model"]["multiple_basis"] = "equity"
        with self.assertRaisesRegex(ContractError, "multiple_basis=enterprise_value"):
            calculations.calculate_valuation(wrong_basis)

    def test_an_unpriced_convertible_must_be_named_not_dropped(self):
        silent = copy.deepcopy(self.ev)
        silent["bridge"]["convertibles_dilution"] = None
        with self.assertRaisesRegex(ContractError, "unsupported_claims"):
            calculations.calculate_valuation(silent)
        named = copy.deepcopy(silent)
        named["bridge"]["unsupported_claims"] = ["2029 年到期可轉債的攤薄未計價。"]
        self.assertAlmostEqual(calculations.calculate_valuation(named)["outputs"]["equity_value"],
                               120.0 * 11.0 + 50.0)

    def test_sum_of_the_parts_adds_enterprise_value_once_and_bridges_once(self):
        parts = {"method": "sotp", "currency": "USD", "scale": "absolute",
                 "parts": [{"name": "核心", "kind": "ev_multiple", "stake": 1.0,
                            "model": copy.deepcopy(self.ev["model"])},
                           {"name": "非全資子公司", "kind": "fcff_dcf_dated", "stake": 0.6,
                            "model": copy.deepcopy(STUB_MODEL["model"])}],
                 "bridge": copy.deepcopy(BRIDGE)}
        outputs = calculations.calculate_valuation(parts)["outputs"]
        subsidiary = calculations.calculate_valuation(STUB_MODEL)["outputs"]["enterprise_value"]
        expected = 120.0 * 11.0 + 0.6 * subsidiary
        self.assertAlmostEqual(outputs["enterprise_value"], expected, places=9)
        self.assertAlmostEqual(outputs["fair_value_per_share"], (expected + 45.0) / 50.0, places=9)
        self.assertEqual(outputs["parts"][1]["stake"], 0.6)


class SensitivityAndReverseSolveTests(unittest.TestCase):
    def test_a_sensitivity_receipt_points_back_at_the_untouched_scenario(self):
        receipt = calculations.sensitivity(
            STUB_MODEL, [{"input_path": "model.discount_rate", "value": 0.12}])
        self.assertEqual(receipt["inputs_digest"], digest(canonical(STUB_MODEL)))
        self.assertEqual(receipt["method"], "fcff_dcf_dated")
        outputs = receipt["outputs"]
        self.assertAlmostEqual(outputs["base_fair_value_per_share"], per_share(STUB_MODEL))
        self.assertLess(outputs["delta_per_share"], 0)
        self.assertNotEqual(outputs["changed_inputs_digest"], receipt["inputs_digest"])
        self.assertEqual(STUB_MODEL["model"]["discount_rate"], 0.10)  # input untouched

    def test_an_unknown_or_empty_input_path_is_an_error_not_a_silent_no_op(self):
        for path in ("model.disount_rate", "model.flows.9.amount", "bridge", "nope"):
            with self.subTest(path=path), self.assertRaisesRegex(ContractError, "input path"):
                calculations.sensitivity(STUB_MODEL, [{"input_path": path, "value": 1}])
        with self.assertRaisesRegex(ContractError, "at least one input"):
            calculations.sensitivity(STUB_MODEL, [])

    def test_reverse_solve_finds_the_rate_that_produces_the_target(self):
        target = per_share({**STUB_MODEL, "model": {**STUB_MODEL["model"],
                                                    "discount_rate": 0.13}})
        result = calculations.solve_implied(STUB_MODEL, target, "model.discount_rate",
                                            {"lower": 0.05, "upper": 0.40})
        self.assertEqual(result["outputs"]["outcome"], "solved")
        self.assertAlmostEqual(result["outputs"]["value"], 0.13, places=8)
        self.assertEqual(result["inputs_digest"], digest(canonical(STUB_MODEL)))
        # The answer is checkable: put it back and the model produces the target.
        again = calculations.apply_changes(
            STUB_MODEL, [{"input_path": "model.discount_rate",
                          "value": result["outputs"]["value"]}])
        self.assertAlmostEqual(per_share(again), target, places=6)

    def test_out_of_reach_and_undefined_ranges_are_reported_as_such(self):
        far = calculations.solve_implied(STUB_MODEL, 1e9, "model.discount_rate",
                                         {"lower": 0.05, "upper": 0.40})
        self.assertEqual(far["outputs"]["outcome"], "no_solution")
        self.assertIsNone(far["outputs"]["value"])
        # Growth at or above the discount rate has no perpetuity: a hole, not an answer.
        target = per_share(calculations.apply_changes(
            STUB_MODEL, [{"input_path": "model.terminal.growth", "value": 0.04}]))
        holes = calculations.solve_implied(STUB_MODEL, target, "model.terminal.growth",
                                           {"lower": 0.0, "upper": 0.30})
        self.assertEqual(holes["outputs"]["outcome"], "solved")
        self.assertAlmostEqual(holes["outputs"]["value"], 0.04, places=8)
        self.assertGreater(holes["outputs"]["undefined_samples"], 0)
        with self.assertRaisesRegex(ContractError, "lower < upper"):
            calculations.solve_implied(STUB_MODEL, 1.0, "model.discount_rate",
                                       {"lower": 0.4, "upper": 0.1})

    def test_two_roots_are_reported_as_multiple_solutions_not_as_one_answer(self):
        """Alternating signs give the classic two-IRR shape: EV=0 at r=10% and r=20%."""
        model = copy.deepcopy(STUB_MODEL)
        model["model"]["flows"] = [
            {"date": "2027-01-01", "amount": -100.0, "is_stub": False, "label": "投入"},
            {"date": "2028-01-01", "amount": 230.0, "is_stub": False, "label": "回收"},
            {"date": "2029-01-01", "amount": -132.0, "is_stub": False, "label": "退役成本"}]
        model["model"]["terminal"] = {"date": "2029-01-01", "final_expansion_fcff": 1e-9,
                                      "normalized_fcff": 1e-9, "growth": 0.0,
                                      "basis": "終值可忽略。"}
        # Per share is (EV + 45) / 50; just above EV = 0 the curve crosses twice.
        result = calculations.solve_implied(model, 45.0 / 50.0 + 0.00001,
                                            "model.discount_rate",
                                            {"lower": 0.05, "upper": 0.30})
        self.assertEqual(result["outputs"]["outcome"], "multiple_solutions")
        self.assertGreaterEqual(len(result["outputs"]["brackets"]), 2)
        self.assertIsNone(result["outputs"]["value"])


class ServiceCalculateTests(unittest.TestCase):
    """What a model can actually call, and what it gets back."""

    def test_every_listed_method_runs_through_the_one_calculator(self):
        for method, params in (("fcff_dcf", LEGACY_DCF),
                               ("fcff_dcf_dated", STUB_MODEL),
                               ("ev_multiple", ev_multiple("2026-01-01", "2026-12-31")),
                               ("forward_pe", forward_pe("2026-01-01", "2026-12-31",
                                                         "2026-01-01", "2026-12-31"))):
            with self.subTest(method=method):
                answer = service.calculate(method, {k: v for k, v in params.items()
                                                    if k != "method"})
                self.assertEqual(answer["receipt"]["method"], method)
                self.assertEqual(answer["receipt"]["inputs_digest"],
                                 digest(canonical(params)))
                self.assertEqual(answer["result"], answer["receipt"]["outputs"])
                self.assertEqual(answer["calculator_version"], calculations.VERSION)
        self.assertIn("sensitivity", service.CALCULATION_METHODS)
        self.assertIn("solve_implied", service.CALCULATION_METHODS)

    def test_the_tool_facade_takes_one_dict_and_reuses_the_same_function(self):
        answer = service.calculate_tool({"method": "sensitivity", "params": {
            "calculation": STUB_MODEL,
            "changes": [{"input_path": "model.discount_rate", "value": 0.12}]}})
        self.assertEqual(answer["receipt"]["inputs_digest"], digest(canonical(STUB_MODEL)))
        self.assertLess(answer["result"]["delta_per_share"], 0)
        self.assertEqual(sorted(service.CALCULATE_TOOL["schema"]["properties"]),
                         ["method", "params"])
        self.assertEqual(service.CALCULATE_TOOL["schema"]["properties"]["method"]["enum"],
                         sorted(service.CALCULATION_METHODS))
        for bad in ({"method": "fcff_dcf"}, {"method": "fcff_dcf", "params": {}, "extra": 1}):
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                service.calculate_tool(bad)

    def test_missing_required_params_are_named(self):
        with self.assertRaisesRegex(ContractError, "bridge"):
            service.calculate("ev_multiple", {"model": {}})


class ResearchIntegrationTests(unittest.TestCase):
    """One saved research version really carries a DCF and two multiples, and publishes."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.evidence_id = citable(self.bundle, self.records)
        self.cite = [{'evidence_id': self.evidence_id, 'locator': 'L1-L3'}]
        self.valuation = calculated_valuation(self.packet['as_of'], self.cite)
        self.payload = payload(self.packet, self.evidence_id, valuation=self.valuation)
        self.research = intake(self.payload, bundle=self.bundle,
                               clock=self.packet['created_at'], role_meta=ROLE_META)

    def test_one_version_holds_three_methods_and_every_receipt_is_its_own(self):
        self.assertEqual(self.research['contract_version'], '0.4.0')
        calculated = calculations.calculate(self.research)
        methods = {name: receipt['method']
                   for name, receipt in calculated['valuation_receipts'].items()}
        self.assertEqual(methods, {'bear': 'ev_multiple', 'base': 'fcff_dcf_dated',
                                   'bull': 'forward_pe'})
        for name, receipt in calculated['valuation_receipts'].items():
            scenario = next(row for row in self.research['valuation']['scenarios']
                            if row['name'] == name)
            self.assertEqual(receipt['inputs_digest'],
                             digest(canonical(scenario['calculation'])))
        self.assertEqual(calculated['alternative_view']['method'], 'ev_multiple')

    def test_changing_one_driver_moves_the_per_share_number_of_its_own_scenario(self):
        for scenario in self.research['valuation']['scenarios']:
            driver = scenario['drivers'][0]
            with self.subTest(scenario=scenario['name'], driver=driver['name']):
                receipt = calculations.sensitivity(
                    scenario['calculation'],
                    [{'input_path': driver['input_path'], 'value': driver['value'] * 0.8}])
                self.assertLess(receipt['outputs']['fair_value_per_share'],
                                receipt['outputs']['base_fair_value_per_share'])

    def test_saved_sensitivities_and_reverse_solve_tie_to_the_same_scenario(self):
        calculated = calculations.calculate(self.research)
        base_digest = calculated['valuation_receipts']['base']['inputs_digest']
        by_scenario = {row['scenario']: row for row in calculated['sensitivities']}
        self.assertEqual(by_scenario['base']['receipt']['inputs_digest'], base_digest)
        self.assertEqual(by_scenario['bear']['receipt']['inputs_digest'],
                         calculated['valuation_receipts']['bear']['inputs_digest'])
        self.assertLess(by_scenario['base']['receipt']['outputs']['delta_per_share'], 0)
        self.assertIsNone(by_scenario['base']['reported_matches'])  # nothing was recorded
        self.assertEqual(calculated['implied']['receipt']['inputs_digest'], base_digest)
        self.assertIn(calculated['implied']['receipt']['outputs']['outcome'],
                      ('solved', 'no_solution', 'multiple_solutions', 'undefined'))

    def test_a_stale_recorded_receipt_is_flagged_rather_than_repeated(self):
        analysis = copy.deepcopy(self.payload)
        good = calculations.sensitivity(
            analysis['valuation']['scenarios'][1]['calculation'],
            analysis['valuation']['sensitivities'][0]['changes'])
        analysis['valuation']['sensitivities'][0]['receipt'] = good
        research = intake(analysis, bundle=self.bundle, clock=self.packet['created_at'],
                          role_meta=ROLE_META)
        self.assertIs(calculations.calculate(research)['sensitivities'][0]['reported_matches'],
                      True)
        stale = copy.deepcopy(good)
        stale['outputs']['fair_value_per_share'] += 5
        analysis['valuation']['sensitivities'][0]['receipt'] = stale
        research = intake(analysis, bundle=self.bundle, clock=self.packet['created_at'],
                          role_meta=ROLE_META)
        self.assertIs(calculations.calculate(research)['sensitivities'][0]['reported_matches'],
                      False)

    def test_a_sensitivity_without_its_scenario_is_refused(self):
        analysis = copy.deepcopy(self.payload)
        analysis['valuation']['sensitivities'][0]['scenario'] = 'bull'
        analysis['valuation']['scenarios'] = [
            row for row in analysis['valuation']['scenarios'] if row['name'] != 'bull']
        analysis['valuation']['status'] = 'unavailable'
        analysis['valuation']['gap_reason'] = '只保留兩個情境作測試。'
        with self.assertRaises(ContractError):
            intake(analysis, bundle=self.bundle, clock=self.packet['created_at'],
                   role_meta=ROLE_META)
        # And the check itself, reached directly with a research that got past the schema.
        research = copy.deepcopy(dict(self.research))
        research['valuation']['sensitivities'][0]['scenario'] = 'bear'
        research['valuation']['scenarios'] = [
            row for row in research['valuation']['scenarios'] if row['name'] != 'bear']
        selected = check_packet(self.packet, self.records, self.bundle)
        with self.assertRaisesRegex(ContractError, 'scenario'):
            check_research(self.packet, research, selected, self.bundle)

    def test_an_equity_multiple_carrying_an_enterprise_bridge_fails_the_contract(self):
        analysis = copy.deepcopy(self.payload)
        analysis['valuation']['scenarios'][2]['calculation']['bridge'] = copy.deepcopy(BRIDGE)
        with self.assertRaises(ContractError):
            intake(analysis, bundle=self.bundle, clock=self.packet['created_at'],
                   role_meta=ROLE_META)

    def test_the_release_shows_each_method_its_drivers_and_the_reverse_solve(self):
        (self.bundle / 'research.json').write_bytes(canonical(self.research))
        release = publish(self.bundle, self.root / 'releases')
        verify_release(release)
        html = (release / 'index.html').read_text(encoding='utf-8')
        for label in ('日期化多階段 FCFF 折現', 'EV 倍數（企業價值）', '前瞻 P/E（股權倍數）',
                      '首個未足一年的 stub', '企業價值到股權的橋接', '經營 driver',
                      '敏感度：改一項輸入，每股變多少', '反推：現價', '計算回執'):
            with self.subTest(label=label):
                self.assertIn(label, html)
        calculated = read_json(release / 'calculations.json')
        self.assertEqual(calculated['calculator_version'], calculations.VERSION)
        self.assertEqual(len(calculated['sensitivities']), 2)

    def test_an_old_03_bundle_still_takes_in_and_publishes(self):
        root = self.root / 'legacy'
        bundle, packet, records = build_bundle(root, contract_version='0.3.0')
        analysis = payload(packet, citable(bundle, records))
        self.assertNotIn('sensitivities', analysis['valuation'])
        research = intake(analysis, bundle=bundle, clock=packet['created_at'],
                          role_meta=ROLE_META)
        self.assertEqual(research['contract_version'], '0.3.0')
        (bundle / 'research.json').write_bytes(canonical(research))
        verify_release(publish(bundle, root / 'releases'))


if __name__ == '__main__':
    unittest.main()
