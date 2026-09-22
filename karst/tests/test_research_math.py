import math
import unittest
from karst.research_math import calculate

class ValuationBridgeTests(unittest.TestCase):
    def test_index_conversion_keeps_units(self):
        result=calculate({'method':'index_earnings','inputs':{'index_reference':5000,'fund_reference':500,'scenarios':[{'name':'flat','eps':250,'pe':20}]}})
        self.assertEqual(result['outputs']['scenarios'][0]['fund_equivalent'],500)
        with self.assertRaises(ValueError):
            calculate({'method':'index_earnings','inputs':{'index_reference':0,'fund_reference':500,'scenarios':[]}})

    def test_growth_bridge_round_trip(self):
        p={'terminal_pe':20,'years':5,'required_return':.1,'entry_multiples':[30],'growth_rates':[]}
        growth=calculate({'method':'multiple_growth','inputs':p})['outputs']['implied_growth'][0]['annual_eps_growth']
        p['growth_rates']=[growth]
        value=calculate({'method':'multiple_growth','inputs':p})['outputs']['supported_multiples'][0]['multiple']
        self.assertTrue(math.isclose(value,30))
        p['terminal_pe']=float('nan')
        with self.assertRaises(ValueError):calculate({'method':'multiple_growth','inputs':p})
