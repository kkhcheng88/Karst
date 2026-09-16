"""The company data room: what is registered, which versions exist, what is still open."""
import json
import tempfile
import unittest
from pathlib import Path

from karst import service, store as store_module
from karst.agents.research import intake
from karst.page.company import render_company_index
from karst.schema import canonical
from karst.tests.test_review_api import anthropic_reply, review_result
from karst.tests.v03_fixture import ROLE_META, build_bundle, citable, payload

SUBJECT = 'FIXTURE:FIXTURE'


class CompanyIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.releases = self.root / 'releases'
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.evidence_id = citable(self.bundle, self.records)
        self.store = store_module.init(self.root / 'karst.sqlite3')
        self.addCleanup(self.store.close)
        self.research = intake(payload(self.packet, self.evidence_id), bundle=self.bundle,
                               clock=self.packet['created_at'], role_meta=ROLE_META)
        (self.bundle / 'research.json').write_bytes(canonical(self.research))
        self.version = self.store.save_research_version(SUBJECT, self.research,
                                                        as_of=self.packet['as_of'])

    def render(self):
        return render_company_index(self.store, self.bundle, self.packet['security'],
                                    self.releases)

    def test_an_unpublished_company_renders_versions_sources_and_no_dead_link(self):
        html = self.render()
        self.assertIn('<!doctype html>', html)
        self.assertIn(self.packet['security']['ticker'], html)
        self.assertIn(self.evidence_id, html)
        self.assertIn('未發布', html)
        self.assertIn('neutral', html)  # the stored rating, straight from the payload
        self.assertIn('沒有未處理的補查請求', html)
        self.assertIn('未有已完成的覆核結果', html)
        self.assertNotIn('<script', html)
        self.assertNotIn('http://', html.replace('http://www.w3.org', ''))

    def test_publishing_writes_the_data_room_next_to_the_release(self):
        released = service.publish_research(self.store, self.bundle,
                                            self.version['version_id'], self.releases)
        index = Path(released['company_index'])
        self.assertEqual(index, (self.releases / 'index.html').resolve())
        html = index.read_text(encoding='utf-8')
        publication = Path(released['publication_dir']).name
        self.assertIn(f'{publication}/index.html', html)
        self.assertIn('開啟', html)
        self.assertNotIn('未發布', html)
        # The release itself is untouched by the extra file next to it.
        from karst.publish import verify_release
        verify_release(Path(released['publication_dir']))

    def test_the_latest_review_and_the_citation_count_reach_the_page(self):
        result = review_result(self.research['research_id'], self.evidence_id)
        service.request_review(
            self.store, subject=SUBJECT, version_id=self.version['version_id'],
            dispute='改善是否一次性？', evidence_ids=[self.evidence_id],
            reviewer={'execution': 'api', 'provider': 'anthropic', 'model': 'model-under-test'},
            bundle=self.bundle, task_dir=self.root / 'review-task',
            transport=lambda request: anthropic_reply(
                [{'type': 'text', 'text': json.dumps(result)}]))
        html = self.render()
        self.assertIn('challenges_research', html)
        self.assertIn('一次性授權收入', html)
        self.assertIn('material', html)
        self.assertIn('1 個版本', html)  # the cited source names the version that read it


if __name__ == '__main__':
    unittest.main()
