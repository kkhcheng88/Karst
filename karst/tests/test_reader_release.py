import copy
import json
from pathlib import Path
import tempfile
import unittest

from karst.reader.release import stage, apply, fingerprint
from karst.tests.test_reader import sample


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.content = self.root / 'reader'
        old = sample()
        folder = self.content / 'reports/stocks/sample'
        folder.mkdir(parents=True)
        (folder / '2026-01-02-r1.json').write_text(json.dumps(old))
        new = copy.deepcopy(old)
        new.update(published_at='2026-01-03T12:00:00Z', revision=2)
        new['summary'] = 'A changed assessment'
        self.manifest = {'editions': [{'report': new, 'provenance': {'scope': 'editorial'}}]}
        self.output = self.root / 'staged'

    def tearDown(self):
        self.tmp.cleanup()

    def test_stage_keeps_source_unchanged_apply_is_retryable_and_history_preserved(self):
        before = fingerprint(self.content)
        receipt = stage(self.content, self.manifest, self.output)
        self.assertEqual(fingerprint(self.content), before)
        self.assertEqual(len(receipt['historical_html']), 1)
        self.assertEqual(apply(self.content, self.output)['status'], 'applied_not_deployed')
        self.assertEqual(apply(self.content, self.output)['status'], 'already_applied')
        saved = self.content / 'archives/stocks/sample/2026-01-03-r2.html'
        self.assertEqual(saved.read_bytes(), (self.output / 'site/stocks/sample/history/2026-01-03-r2/index.html').read_bytes())
        # A later renderer revision cannot rewrite this just-published edition.
        from unittest.mock import patch
        import importlib
        module = importlib.import_module('karst.reader.build')
        original = module.report_page
        def changed(*args, **kwargs):
            path, html = original(*args, **kwargs)
            return path, html.replace('A changed assessment', 'A later renderer changed this')
        with patch.object(module, 'report_page', side_effect=changed):
            stage(self.content, {'editions': []}, self.root / 'future')
        self.assertEqual(saved.read_bytes(), (self.root / 'future/site/stocks/sample/history/2026-01-03-r2/index.html').read_bytes())
        retry = stage(self.content, self.manifest, self.root / 'retry')
        self.assertEqual(retry['build']['reports'], 2)

    def test_existing_edition_rewrite_stale_base_and_tampering_refused(self):
        manifest = copy.deepcopy(self.manifest)
        manifest['editions'][0]['report'].update(published_at='2026-01-02T12:00:00Z', revision=1)
        with self.assertRaises(ValueError):
            stage(self.content, manifest, self.root / 'rewrite')
        stage(self.content, self.manifest, self.output)
        original = self.content / 'notes.txt'
        original.write_text('concurrent work')
        with self.assertRaises(ValueError):
            apply(self.content, self.output)
        original.unlink()
        (self.output / 'content' / 'tampered.txt').write_text('changed')
        with self.assertRaises(ValueError):
            apply(self.content, self.output)
