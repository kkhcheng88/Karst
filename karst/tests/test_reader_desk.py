import copy
import json
from pathlib import Path
import tempfile
import unittest

from karst.reader import desk
from karst.tests.test_reader import sample


def projection():
    return {'schema_version':1,'as_of':'2026-01-02','price_as_of':'2026-01-01',
            'summary':'Changes','method':'Prices only',
            'market':{'kind':'stocks','slug':'sample','title':'Market','summary':'Summary'},
            'groups':[{'kind':'stocks','slug':'sample','name':'Example','members':'Two members',
                       'state':'Cooling','assessment':'Mixed','breadth':'1/2','rsi':'50','beta':'—',
                       'windows':{k:{'return_pct':1.0,'excess_pp':-.5} for k in ('1','5','20')},
                       'spark':[{'date':'2025-12-31','value':100},{'date':'2026-01-01','value':99}]}],
            'events':[{'date':None,'when':'Next quarter','status':'unscheduled','title':'Results','impact':'Test revenue',
                       'kind':'stocks','slug':'sample','source':'https://example.com'}]}


class DeskTests(unittest.TestCase):
    def load(self,d):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'desk.json').write_text(json.dumps(d))
            return desk.load(p,[sample()])

    def test_refuses_future_spark_broken_link_internal_field_and_invented_date(self):
        for edit in ('future','link','internal','date','nan'):
            d=projection()
            if edit=='future':d['groups'][0]['spark'][-1]['date']='2026-01-03'
            if edit=='link':d['market']['slug']='missing'
            if edit=='internal':d['evidence_id']='private'
            if edit=='date':d['events'][0]['date']='2026-02-01'
            if edit=='nan':d['groups'][0]['windows']['1']['return_pct']=float('nan')
            with self.subTest(edit=edit),self.assertRaises(ValueError):self.load(d)

    def test_no_js_default_is_weekly_and_expired_events_are_not_upcoming(self):
        d=self.load(projection())
        html=desk.rotation(d)
        self.assertIn('data-window="5"><span',html)
        self.assertIn('data-window="1" hidden',html)
        self.assertIn('相對 SPY',html)
        d['events'].append(copy.deepcopy(d['events'][0])|{'date':'2026-01-01','status':'confirmed','title':'Expired event'})
        self.assertNotIn('Expired event',desk.events(d))
        self.assertIn('日期待公布',desk.events(d))


if __name__=='__main__':unittest.main()
