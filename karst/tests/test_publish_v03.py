"""0.3 releases: transient bars are charted but not saved; only cited sources are copied."""
import shutil
import tempfile
import unittest
from pathlib import Path

from karst.packet import read_json
from karst.publish import publish, verify_release
from karst.schema import ContractError, canonical
from karst.tests.v03_fixture import ROLE_META, build_bundle, citable, payload
from karst.agents.research import intake

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'synthetic'


def bar(day, price):
    return {'at': f'2026-01-{day:02d}T21:00:00Z', 'open': price, 'high': price + 1,
            'low': price - 1, 'close': price + .5, 'volume': 1000 + day, 'complete': True}


class PublishV03Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.evidence_id = citable(self.bundle, self.records)
        self.bars = {'D': [bar(day, 10 + day) for day in range(1, 8)], 'W': [], 'M': []}
        analysis = payload(self.packet, self.evidence_id, bars_count=(len(self.bars['D']), 0, 0))
        self.research = intake(analysis, bundle=self.bundle, clock=self.packet['created_at'],
                               role_meta=ROLE_META)
        (self.bundle / 'research.json').write_bytes(canonical(self.research))

    def release(self, **kwargs):
        path = publish(self.bundle, self.root / 'releases', **kwargs)
        verify_release(path)
        return path

    def test_bars_are_charted_but_never_saved_and_only_cited_sources_are_copied(self):
        release = self.release(bars=self.bars)
        saved = read_json(release / 'inputs' / 'research.json')
        self.assertNotIn('views', saved['technical'])
        self.assertEqual(saved, self.research)
        self.assertNotIn(b'"volume"', (release / 'inputs' / 'research.json').read_bytes())
        html = (release / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<svg', html)  # the transient arrays did reach the chart
        self.assertIn(self.research['technical']['derived']['data_as_of'], html)
        # The whole evidence index is published; only the cited bytes are copied.
        index = read_json(release / 'inputs' / 'evidence.json')
        self.assertEqual(len(index), len(self.records))
        copied = {p.relative_to(release / 'inputs').as_posix()
                  for p in (release / 'inputs').rglob('*') if p.is_file()}
        cited = {r['artifact']['path'] for r in self.records
                 if r['evidence_id'] in self.research['layers']['L1']['read_evidence_ids']}
        self.assertTrue(cited <= copied)
        self.assertEqual(verify_release(release)['mode'], 'interactive_research')

    def test_page_without_arrays_shows_derived_numbers_and_no_empty_chart(self):
        release = self.release()
        html = (release / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('<svg', html)
        self.assertNotIn('沒有已收定的價格資料', html)  # no empty chart placeholder either
        self.assertIn('價格資料截止', html)
        self.assertIn('不足 200 根已收定日線', html)

    def test_transient_bars_cannot_carry_prices_past_the_cutoff(self):
        late = {'D': [bar(1, 10) | {'at': '2099-01-01T00:00:00Z'}], 'W': [], 'M': []}
        with self.assertRaisesRegex(ContractError, 'after the research cutoff'):
            publish(self.bundle, self.root / 'releases', bars=late)

    def test_old_02_bundle_still_publishes_and_verifies_unchanged(self):
        bundle = self.root / 'legacy'
        shutil.copytree(EXAMPLE, bundle)
        release = publish(bundle, self.root / 'legacy-releases')
        manifest = verify_release(release)
        self.assertEqual(manifest['contract_version'], '0.2.0')
        records = read_json(release / 'inputs' / 'evidence.json')
        copied = {p.relative_to(release / 'inputs').as_posix()
                  for p in (release / 'inputs').rglob('*') if p.is_file()}
        # 0.2 keeps copying every registered source, cited or not.
        self.assertTrue({r['artifact']['path'] for r in records} <= copied)
        with self.assertRaisesRegex(ContractError, 'already stores price arrays'):
            publish(bundle, self.root / 'legacy-releases', bars=self.bars)


if __name__ == '__main__':
    unittest.main()
