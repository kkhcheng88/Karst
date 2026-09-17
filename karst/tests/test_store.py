"""SQLite state: version conflicts, restart durability, job hand-off. Offline, no fixtures needed."""
import tempfile
import unittest
from pathlib import Path

from karst import store as store_module
from karst.schema import ContractError

SUBJECT = "US:DEMO"  # parameterized test identity, never a production default


def payload(headline):
    return {"headline": headline, "rating": "neutral", "execution_state": "wait_price"}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "state" / "karst.sqlite3"
        self.store = store_module.init(self.path)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.store.close)

    def test_entities_round_trip(self):
        self.store.upsert_entity("cik:0000000001", "company", name="Demo")
        self.store.upsert_entity("XNAS:DEMO", "security", exchange="XNAS", currency="USD",
                                 symbols={"longbridge": "DEMO.US"})
        self.store.upsert_entity("XNAS:DEMO", "security", exchange="XNAS", currency="USD",
                                 symbols={"longbridge": "DEMO.US", "futu": "US.DEMO"})
        security = self.store.get_entity("XNAS:DEMO")
        self.assertEqual(security["symbols"], {"longbridge": "DEMO.US", "futu": "US.DEMO"})
        self.assertEqual(self.store.get_entity("cik:0000000001")["kind"], "company")
        self.assertIsNone(self.store.get_entity("XNAS:NOTHING"))

    def test_index_sources_indexes_text_and_never_copies_the_manifest(self):
        """The registry owns evidence identity; SQLite only holds the text index."""
        root = Path(self.directory.name) / "bundle"
        (root / "evidence" / "objects" / "aa").mkdir(parents=True)
        (root / "evidence" / "objects" / "aa" / "aa.txt").write_text("backlog rose again",
                                                                     encoding="utf-8")
        record = {"evidence_id": "ev-1", "source_id": "src-1", "source": "edgar", "kind": "filing",
                  "published_at": "2026-01-02", "fetched_at": "2026-01-03T00:00:00Z",
                  "period": {"start": None, "end": "2026-01-02"}, "status": "ok",
                  "media_type": "text/plain",
                  "artifact": {"path": "evidence/objects/aa/aa.txt"}, "entity_ids": ["cik:1"]}
        self.assertEqual(self.store.index_sources([record], root=root), 1)
        self.assertEqual(self.store.index_sources([record], root=root), 0)  # idempotent
        self.assertEqual(self.store.index_sources([record]), 0)  # no root: nothing to index
        if self.store.fts5:
            self.assertEqual([hit["evidence_id"] for hit in self.store.search_text("backlog")],
                             ["ev-1"])
        tables = {row[0] for row in self.store.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("sources", tables)

    def test_stale_expected_previous_does_not_overwrite(self):
        first = self.store.save_research_version(SUBJECT, payload("first"))
        second = self.store.save_research_version(
            SUBJECT, payload("second"), expected_previous_version_id=first["version_id"])
        self.assertEqual(second["previous_version_id"], first["version_id"])
        # A researcher still holding the first version tries to save on top of it.
        conflict = self.store.save_research_version(
            SUBJECT, payload("third"), expected_previous_version_id=first["version_id"])
        self.assertTrue(conflict["conflict"])
        self.assertEqual(conflict["current_version_id"], second["version_id"])
        self.assertEqual(self.store.latest_research(SUBJECT)["version_id"], second["version_id"])
        self.assertEqual(len(self.store.list_research(SUBJECT)), 2)
        self.assertEqual(self.store.get_research(first["version_id"])["status"], "superseded")

    def test_first_save_requires_no_previous(self):
        conflict = self.store.save_research_version(SUBJECT, payload("a"),
                                                    expected_previous_version_id="rv-nonexistent")
        self.assertTrue(conflict["conflict"])
        self.assertIsNone(self.store.latest_research(SUBJECT))

    def test_identical_payload_is_not_stored_twice(self):
        first = self.store.save_research_version(SUBJECT, payload("same"))
        again = self.store.save_research_version(
            SUBJECT, payload("same"), expected_previous_version_id=first["version_id"])
        self.assertTrue(again["conflict"])

    def test_a_version_keeps_the_inputs_it_was_validated_against(self):
        packet = {"packet_id": "packet-1", "as_of": "2026-01-01T00:00:00Z"}
        evidence = [{"evidence_id": "ev-1", "artifact": {"sha256": "abc"}}]
        saved = self.store.save_research_version(SUBJECT, payload("pinned"), packet=packet,
                                                 evidence=evidence)
        stored = self.store.get_research(saved["version_id"])
        self.assertEqual(stored["packet"], packet)
        self.assertEqual(stored["evidence"], evidence)
        # The directory listing stays light: one version can be megabytes of evidence.
        row = self.store.list_research(SUBJECT)[0]
        self.assertNotIn("packet", row)
        self.assertNotIn("evidence", row)
        # A version saved without them reads back as None, never as someone else's inputs.
        plain = self.store.save_research_version(SUBJECT, payload("unpinned"),
                                                 expected_previous_version_id=saved["version_id"])
        self.assertIsNone(self.store.get_research(plain["version_id"])["packet"])
        self.assertIsNone(self.store.latest_research(SUBJECT)["evidence"])

    def test_survives_restart(self):
        saved = self.store.save_research_version(SUBJECT, payload("kept"), as_of="2026-01-01T00:00:00Z")
        job = self.store.create_job("review", input_ref={"subject": SUBJECT})
        self.store.close()
        reopened = store_module.init(self.path)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.latest_research(SUBJECT)["version_id"], saved["version_id"])
        self.assertEqual(reopened.latest_research(SUBJECT)["payload"], payload("kept"))
        self.assertEqual(reopened.get_job(job["job_id"])["status"], "pending")

    def test_job_claim_is_exclusive(self):
        job = self.store.create_job("review", role="reviewer", execution="interactive",
                                    input_ref={"subject": SUBJECT, "dispute": "terminal growth"})
        claimed = self.store.transition(job["job_id"], "claimed", claimed_by="client-b")
        self.assertEqual(claimed["status"], "claimed")
        self.assertEqual(claimed["claimed_by"], "client-b")
        self.assertIsNotNone(claimed["started_at"])
        with self.assertRaises(ContractError):
            self.store.transition(job["job_id"], "claimed", claimed_by="client-c")
        done = self.store.transition(job["job_id"], "done",
                                     result_ref={"verdict": "partly agree"},
                                     usage={"input_tokens": 10})
        self.assertEqual(done["result_ref"], {"verdict": "partly agree"})
        self.assertIsNotNone(done["finished_at"])
        self.assertEqual([j["job_id"] for j in self.store.list_jobs(kind="review", status="done")],
                         [job["job_id"]])

    def test_an_illegal_transition_is_refused_and_changes_nothing(self):
        job = self.store.create_job("review", input_ref={"subject": SUBJECT})
        self.store.transition(job["job_id"], "running")
        self.store.transition(job["job_id"], "done", result_ref={"verdict": "agrees"})
        for target in ("running", "claimed", "done", "failed"):
            with self.assertRaises(ContractError) as caught:
                self.store.transition(job["job_id"], target, error="second thoughts")
            self.assertIn("done", str(caught.exception))
        finished = self.store.get_job(job["job_id"])
        self.assertEqual(finished["status"], "done")
        self.assertIsNone(finished["error"])
        # Recording usage on a finished job is not a state change and stays allowed.
        self.assertEqual(self.store.transition(job["job_id"], usage={"input_tokens": 3})["usage"],
                         {"input_tokens": 3})

    def test_bad_kind_status_field_and_job_are_refused(self):
        with self.assertRaises(ContractError):
            self.store.create_job("nonsense")
        job = self.store.create_job("refresh")
        with self.assertRaises(ContractError):
            self.store.transition(job["job_id"], "finished-ish")
        with self.assertRaises(ContractError):
            self.store.transition(job["job_id"], "running", verdict="not a job column")
        with self.assertRaises(ContractError):
            self.store.transition("job-nonexistent", "running")
        self.assertEqual(self.store.get_job(job["job_id"])["status"], "pending")


if __name__ == "__main__":
    unittest.main()
