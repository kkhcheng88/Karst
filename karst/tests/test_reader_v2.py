"""Reader contract boundaries: history, public OHLC and decision order."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from karst.reader.build import build, validate
from karst.reader.interactive import validate as chart_validate, project
from karst.tests.test_reader import sample


class ReaderV2Tests(unittest.TestCase):
    def test_competition_is_not_rendered_as_a_supply_arrow(self):
        from karst.reader.workbench import network
        graph={'nodes':[{'key':key,'label':key.upper(),'role':'Cloud'} for key in ('a','b')],
               'edges':[{'from':'a','to':'b','label':'Alternative providers','basis':'inference',
                         'relation_type':'competes','source':'https://example.com'}]}
        self.assertIn('A · B', network(graph))
        self.assertNotIn('A → B', network(graph))
        graph['edges'][0]['relation_type']='supplies'
        self.assertIn('A → B', network(graph))

    def test_chart_cutoff_unknown_fields_and_ohlc_are_checked(self):
        bars = [{"at":"2026-01-01T21:00:00Z", "open":10,"high":12,"low":9,"close":11,"volume":50,"complete":True}]
        data = project({"D":bars},name="Example",currency="USD",price_basis="raw",as_of="2026-01-01")
        self.assertEqual(data["views"]["M"]["bars"][0]["complete"], False)
        for field, value in (("time","2026-01-02"),("close",100),("volume",float("nan"))):
            bad=copy.deepcopy(data);bad["views"]["D"]["bars"][0][field]=value
            with self.assertRaises(ValueError):chart_validate(bad)
        with self.assertRaises(ValueError):chart_validate(data | {"evidence_id":"private"})

    def test_v2_preserves_v1_archive_and_presents_plan_second(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); content=root/'content'; folder=content/'reports/stocks/sample'; folder.mkdir(parents=True)
            old=sample(); (folder/'2026-01-02-r1.json').write_text(json.dumps(old))
            build(content,root/'before')
            oldpath='stocks/sample/history/2026-01-02-r1/index.html'
            before=(root/'before'/oldpath).read_bytes()
            new=copy.deepcopy(old);new.update(schema_version=2,published_at='2026-01-03T12:00:00Z',revision=2)
            new['sections'][0]['tables']=[{'title':'Independent axes','columns':['EPS','40×','60×'],'rows':[['4','160','240']]}]
            (folder/'2026-01-03-r2.json').write_text(json.dumps(new))
            build(content,root/'after')
            self.assertEqual(before,(root/'after'/oldpath).read_bytes())
            html=(root/'after/stocks/sample/index.html').read_text()
            self.assertLess(html.index('id="plan"'),html.index('id="fundamentals"'))
            self.assertIn('data-search',(root/'after/index.html').read_text())

    def test_interactive_requires_fallback_and_graph_cannot_reference_missing_node(self):
        r=sample();r['schema_version']=2;r['sections'][3]['chart']='prices.json'
        with self.assertRaises(ValueError):validate(r)
        r['sections'][3].pop('chart')
        r['sections'][0]['network']={'nodes':[{'key':'a','label':'A','role':'Supplier'}],
            'edges':[{'from':'a','to':'missing','label':'Supplies','basis':'documented','source':'https://example.com'}]}
        with self.assertRaises(ValueError):validate(r)


if __name__=='__main__':unittest.main()
