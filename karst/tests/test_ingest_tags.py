"""Tagging at the door: a report without nodes, author, date and source type is refused."""
import tempfile
import unittest
from pathlib import Path

from karst import service, store as store_module
from karst.schema import ContractError

SUBJECT = "NASDAQ:DEMO"  # parameterized test identity, never a production default
INDUSTRY = "industry:analog-semis"
COMPLETE = {"kind": "industry_report", "author": "A Broker Analyst",
            "published_at": "2026-03-04", "source_type": "broker_report"}


class IngestTagTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.data = Path(self.directory.name) / "karst-data"
        self.store = store_module.init(self.data / service.DB_NAME)
        self.addCleanup(self.store.close)
        self.bundle = service.ensure_company(
            self.store, self.data, {"security_id": SUBJECT})["bundle"]

    def ingest(self, **kwargs):
        fields = {"excerpt": "the readable part of the report", "store": self.store}
        return service.ingest_source(self.bundle, **{**fields, **kwargs})

    def test_each_missing_field_is_named(self):
        for missing in ("entity_ids", "author", "published_at", "source_type"):
            fields = {**COMPLETE, "entity_ids": [SUBJECT]}
            fields[missing] = [] if missing == "entity_ids" else None
            with self.assertRaises(ContractError) as caught:
                self.ingest(**fields)
            self.assertIn(missing, str(caught.exception))

    def test_an_unknown_source_type_is_refused(self):
        with self.assertRaises(ContractError) as caught:
            self.ingest(**{**COMPLETE, "entity_ids": [SUBJECT], "source_type": "a friend said so"})
        self.assertIn("broker_report", str(caught.exception))

    def test_a_tagged_report_lands_in_the_source_index_and_the_entity_table(self):
        record = self.ingest(**COMPLETE, entity_ids=[SUBJECT, INDUSTRY])
        self.assertEqual(record["kind"], "industry_report")
        self.assertEqual(record["source_type"], "broker_report")
        self.assertEqual(record["entity_ids"], sorted([SUBJECT, INDUSTRY]))
        self.assertEqual(self.store.get_entity(INDUSTRY)["kind"], "industry")
        self.assertEqual(self.store.get_entity(SUBJECT)["kind"], "security")
        rows = self.store.list_sources(entity_id=INDUSTRY)
        self.assertEqual([row["evidence_id"] for row in rows], [record["evidence_id"]])
        self.assertEqual(rows[0]["published_at"], "2026-03-04")

    def test_a_plain_excerpt_needs_no_report_tags(self):
        record = self.ingest(note="something the user read", entity_ids=[SUBJECT])
        self.assertEqual(record["kind"], "other_public")


if __name__ == "__main__":
    unittest.main()
