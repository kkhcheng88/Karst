"""Public export boundaries and retained report history."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from karst.reader.build import SECTIONS, build, load_reports, stamp, validate


def sample():
    return {
        'schema_version': 1, 'public': True, 'kind': 'stocks', 'slug': 'sample',
        'name': 'Sample Company', 'symbol': 'TEST', 'published_at': '2026-01-02T12:00:00Z',
        'as_of': '2026-01-01', 'revision': 1, 'review_status': '待覆核',
        'verdict': '等待', 'summary': '等待業績確認', 'change': '首次研究', 'action': '觀察',
        'metrics': [], 'sections': [{'key': k, 'paragraphs': [{'text': '分析文字'}]} for k in SECTIONS],
        'related': [], 'sources': [{'label': '來源', 'url': 'https://example.com/results'}],
    }


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.content = self.root / 'content'
        self.output = self.root / 'site'
        self.content.mkdir()
        self.add(sample())

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, r):
        path = self.content / 'reports' / r['kind'] / r['slug'] / (stamp(r) + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(r), encoding='utf-8')

    def test_latest_report_and_original_snapshot_remain_distinct(self):
        newer = sample()
        newer.update(published_at='2026-01-03T12:00:00Z', verdict='新判斷', change='修正舊假設')
        self.add(newer)
        build(self.content, self.output)
        self.assertIn('新判斷', (self.output/'stocks/sample/index.html').read_text())
        old = (self.output/'stocks/sample/history/2026-01-02-r1/index.html').read_text()
        self.assertIn('<p class="deck">等待</p>', old)
        self.assertIn('這是當時的分析快照', old)

    def test_private_inputs_and_unreferenced_assets_never_leave_content(self):
        (self.content/'provenance').mkdir()
        (self.content/'provenance/secret.json').write_text('{"secret":"private"}')
        (self.content/'assets').mkdir()
        (self.content/'assets/private.txt').write_text('not public')
        build(self.content, self.output)
        self.assertFalse(list(self.output.rglob('*.json')))
        self.assertFalse(list(self.output.rglob('*.txt')))
        self.assertFalse((self.output/'provenance').exists())

    def test_rejects_internal_fields_identifiers_and_unapproved_reports(self):
        for edit in ({'evidence_id': 'internal'}, {'summary': 'ev-' + 'a'*64}, {'public': False}, {'slug':'../../private'}):
            with self.subTest(edit=edit):
                r = sample()
                r.update(edit)
                with self.assertRaises(ValueError):
                    validate(r)

    def test_html_is_escaped_and_sources_cannot_execute_code(self):
        r = sample()
        r['summary'] = '<script>alert(1)</script>'
        self.add(r)
        build(self.content, self.output)
        home = (self.output/'index.html').read_text()
        self.assertNotIn('<script>', home)
        self.assertIn('&lt;script&gt;', home)
        for url in ('javascript:alert(1)', 'https://user:password@example.com/', 'https://example.com/?token=secret'):
            r['sources'][0]['url'] = url
            with self.assertRaises(ValueError):
                validate(r)

    def test_refuses_dirty_output_and_overlapping_directories(self):
        self.output.mkdir()
        (self.output/'private.json').write_text('{}')
        for output in (self.output, self.content/'site', self.content.parent):
            with self.subTest(output=output), self.assertRaises(ValueError):
                build(self.content, output)

    def test_missing_related_page_fails_before_publish(self):
        r = sample()
        r['related'] = [{'kind':'stocks','slug':'missing','label':'Missing'}]
        self.add(r)
        with self.assertRaises(ValueError):
            build(self.content, self.output)

    def test_asset_traversal_and_symlink_are_rejected(self):
        r = sample()
        r['sections'][3]['figure'] = {'file':'../private.png','alt':'Chart','caption':'Chart'}
        with self.assertRaises(ValueError):
            validate(r)
        r['sections'][3]['figure']['file'] = 'chart.png'
        self.add(r)
        (self.content/'assets').mkdir()
        private = self.root/'private.png'
        private.write_bytes(b'\x89PNG\r\n\x1a\nprivate')
        (self.content/'assets/chart.png').symlink_to(private)
        with self.assertRaises(ValueError):
            build(self.content, self.output)

    def test_build_is_deterministic(self):
        second = self.root/'second'
        build(self.content, self.output)
        build(self.content, second)
        files = lambda p: {str(f.relative_to(p)): f.read_bytes() for f in p.rglob('*') if f.is_file()}
        self.assertEqual(files(self.output), files(second))


if __name__ == '__main__':
    unittest.main()
