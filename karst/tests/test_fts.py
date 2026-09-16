"""Full-text search over registered evidence: FTS5 or an explicit refusal, never a quiet miss."""
import tempfile
import unittest
from pathlib import Path

from karst import service, store as store_module
from karst.schema import ContractError

SUBJECT = "XNAS:DEMO"  # parameterized test identity, never a production default
BODY = """Management said the gross margin expansion came from product mix.
Free cash flow was negative for the quarter because of the new fab.
The backlog grew, but the customer concentration did not change.
"""


class FullTextTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.data = self.root / "karst-data"
        self.store = store_module.init(self.data / service.DB_NAME)
        self.addCleanup(self.store.close)
        self.bundle = service.ensure_company(
            self.store, self.data, {"security_id": SUBJECT})["bundle"]

    def ingest(self, text, name, **kwargs):
        body = self.root / name
        body.write_text(text, encoding="utf-8")
        return service.ingest_source(self.bundle, file_path=str(body), entity_ids=[SUBJECT],
                                     store=self.store, **kwargs)

    def test_indexed_text_is_searchable_with_a_snippet_and_line(self):
        if not self.store.fts5:
            self.skipTest("SQLite built without FTS5")
        record = self.ingest(BODY, "call.txt", note="transcript excerpt")
        self.ingest("Nothing about margins here at all.\n", "other.txt", note="unrelated")

        found = service.search_evidence(self.bundle, text="backlog", store=self.store)
        self.assertEqual(found["count"], 1)
        hit = found["results"][0]
        self.assertEqual(hit["evidence_id"], record["evidence_id"])
        self.assertIn("backlog", hit["snippet"])
        self.assertEqual(hit["line"], 3)

        both = service.search_evidence(self.bundle, text="margin OR margins", store=self.store)
        self.assertEqual(both["count"], 2)

    def test_field_filters_still_apply_to_a_text_search(self):
        if not self.store.fts5:
            self.skipTest("SQLite built without FTS5")
        self.ingest(BODY, "call.txt", note="transcript excerpt")
        self.assertEqual(
            service.search_evidence(self.bundle, kind="industry_report", text="backlog",
                                    store=self.store)["count"], 0)
        self.assertEqual(
            service.search_evidence(self.bundle, kind="other_public", text="backlog",
                                    store=self.store)["count"], 1)

    def test_a_word_that_is_not_there_returns_nothing_but_says_so(self):
        if not self.store.fts5:
            self.skipTest("SQLite built without FTS5")
        self.ingest(BODY, "call.txt")
        miss = service.search_evidence(self.bundle, text="dividend", store=self.store)
        self.assertEqual(miss["count"], 0)
        self.assertIn("not absence", miss["note"])

    def test_without_fts5_the_search_refuses_instead_of_degrading(self):
        self.store.fts5, self.store.fts5_reason = False, "no such module: fts5"
        with self.assertRaises(ContractError) as caught:
            self.store.search_text("backlog")
        self.assertIn("FTS5", str(caught.exception))
        with self.assertRaises(ContractError):
            service.search_evidence(self.bundle, text="backlog", store=self.store)

    def test_text_search_without_a_store_is_refused(self):
        with self.assertRaises(ContractError):
            service.search_evidence(self.bundle, text="backlog")


if __name__ == "__main__":
    unittest.main()
