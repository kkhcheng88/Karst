import unittest

from karst.comparison import fundamental_ratios, price_returns


class ComparisonTests(unittest.TestCase):
    def test_capital_structure_changes_the_sales_comparison(self):
        inputs = dict(market_cap=1000, revenue=100, previous_quarter_revenue=80,
                      adjusted_ebitda=20, operating_income=-10, debt=400,
                      finance_leases=50, cash=100, noncontrolling_interest=10)
        result = fundamental_ratios(**inputs)
        self.assertEqual(result['revenue_qoq_pct'], 25)
        self.assertEqual(result['operating_margin_pct'], -10)
        self.assertEqual(result['ps_annualized_quarter'], 2.5)
        self.assertEqual(result['enterprise_value_proxy'], 1360)
        self.assertEqual(result['ev_annualized_quarter_sales_proxy'], 3.4)
        for key, value in [('revenue', 0), ('cash', -1), ('debt', float('nan'))]:
            with self.assertRaises(ValueError): fundamental_ratios(**(inputs | {key:value}))

    def test_returns_refuse_stale_or_unconfirmed_cutoff(self):
        bars = [{'date':f'2026-01-{i:02}', 'close':float(i), 'complete':True} for i in range(1,5)]
        result = price_returns(bars, cutoff='2026-01-03', windows=(1,3))
        self.assertEqual(result['1']['value_pct'], 50)
        self.assertIsNone(result['3'])
        bars[2]['complete'] = False
        with self.assertRaises(ValueError): price_returns(bars, cutoff='2026-01-03')
        with self.assertRaises(ValueError): price_returns(bars[::-1], cutoff='2026-01-04')


if __name__ == '__main__': unittest.main()
