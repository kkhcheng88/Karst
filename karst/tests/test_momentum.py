import copy
import unittest
from datetime import date, timedelta

from karst.momentum import compare, rsi


def inputs():
    x, y = 100.0, 100.0
    series = {'market':[], 'stock':[]}
    for i in range(90):
        if i:
            change = (.01 if i % 3 else -.015)
            x *= 1 + change
            y *= 1 + 2*change
        day = (date(2026,1,1)+timedelta(days=i)).isoformat()
        for key, value in [('market',x),('stock',y)]:
            series[key].append({'date':day,'close':value,'complete':True})
    return dict(series=series,benchmark='market',weights={'stock':1.0},cutoff=day,
                selected_on='2026-04-01',basis='split_adjusted_price',currency='USD')


class MomentumTests(unittest.TestCase):
    def test_known_beta_and_future_replay(self):
        args=inputs(); result=compare(**args)
        self.assertAlmostEqual(result['basket']['beta63'],2,places=10)
        self.assertEqual(result['basket']['beta_observations'],63)
        self.assertAlmostEqual(result['benchmark_profile']['beta63'],1)
        cut=args['series']['market'][-8]['date']
        earlier=compare(**(args|{'cutoff':cut}))
        truncated=copy.deepcopy(args)
        truncated['cutoff']=cut
        for k in truncated['series']:
            truncated['series'][k]=truncated['series'][k][:-7]
        self.assertEqual(earlier,compare(**truncated))

    def test_missing_session_partial_cutoff_and_weight_drift_refused(self):
        for mutation in ('gap','partial','weight','duplicate'):
            args=inputs()
            if mutation=='gap':args['series']['stock'].pop(-8)
            if mutation=='partial':args['series']['stock'][-1]['complete']=False
            if mutation=='weight':args['weights']['stock']=.9
            if mutation=='duplicate':args['series']['stock'].append(args['series']['stock'][-1])
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): compare(**args)

    def test_short_history_and_flat_benchmark_are_not_zero_beta(self):
        args=inputs()
        for k in args['series']:args['series'][k]=args['series'][k][-10:]
        result=compare(**args)
        self.assertIsNone(result['basket']['beta63'])
        self.assertIsNone(result['basket']['windows']['20']['excess_pp'])
        self.assertIsNone(result['basket']['median_rsi14'])
        args=inputs()
        for bar in args['series']['market']:bar['close']=100
        self.assertIsNone(compare(**args)['basket']['beta63'])

    def test_wilder_seed_and_flat_series(self):
        values=[44.34,44.09,44.15,43.61,44.33,44.83,45.10,45.42,45.84,46.08,45.89,46.03,45.61,46.28,46.28]
        self.assertAlmostEqual(rsi(values)[-1],70.46413502109705)
        self.assertEqual(rsi([1]*20)[-1],50)
        self.assertEqual(rsi(list(range(1,21)))[-1],100)

    def test_basket_compounds_daily_weights_not_average_total_returns(self):
        args=inputs(); dates=[x['date'] for x in args['series']['market'][-3:]]
        args['series']={k:[{'date':d,'close':c,'complete':True} for d,c in zip(dates,closes)]
                        for k,closes in {'market':[100,100,100],'a':[100,200,100],'b':[100,100,200]}.items()}
        args['weights']={'a':.5,'b':.5}
        self.assertAlmostEqual(compare(**args)['basket']['last'],187.5)


if __name__=='__main__':unittest.main()
