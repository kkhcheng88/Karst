"""Service layer, offline: fake clients, the packaged synthetic bundle, no model and no network."""
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

from karst import service, store as store_module
from karst.packet import read_json
from karst.schema import ContractError
from karst.tests.test_longbridge import FakeClient

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic"
SECURITY = {"ticker": "DEMO", "issuer_id": "cik:0000000001", "security_id": "XNAS:DEMO",
            "currency": "USD", "exchange": "XNAS", "symbols": {"longbridge": "DEMO.US"}}
ROLE = {"role": "researcher", "execution": "interactive", "provider": "test", "model": "fake-1"}
# Shape owned by karst.agents.review; the service only stores what that module accepts.
REVIEW_RESULT = {
    "research_id": "res-demo-1", "challenges": [], "new_evidence_requests": [],
    "verdict_on_dispute": {"verdict": "challenges_research", "citations": [],
                           "reasoning": "The margin assumption has no cited support."},
    "reviewer": {"role": "reviewer", "execution": "api", "provider": "anthropic",
                 "model_id": "some-model", "prompt_version": "test"},
}


def passthrough_intake(payload, *, bundle, clock, role_meta):
    """Stands in for karst.agents.research.intake, which another work package owns."""
    return payload


class ServiceCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.bundle = self.root / "bundle"
        self.staging = self.root / "staging"
        self.bundle.mkdir()
        self.store = store_module.init(self.root / "karst.sqlite3")
        self.addCleanup(self.store.close)

    def copy_example(self):
        shutil.rmtree(self.bundle)
        shutil.copytree(EXAMPLE, self.bundle)


class ProtocolTests(ServiceCase):
    def test_protocol_is_delegated_never_substituted(self):
        available = importlib.util.find_spec("karst.agents.protocol") is not None
        if not available:
            with self.assertRaises(ContractError) as caught:
                service.get_research_protocol("research")
            self.assertIn("karst.agents.protocol", str(caught.exception))
            return
        result = service.get_research_protocol("research")
        self.assertEqual(set(result) >= {"version", "mode", "text"}, True)


class RefreshTests(ServiceCase):
    def refresh(self, client):
        return service.refresh_sources(self.root, SECURITY, ["prices"], since="2026-01-01",
                                       clients={"longbridge": client}, store=self.store)

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(ContractError):
            service.refresh_sources(self.root, SECURITY, ["telepathy"])

    def test_same_bytes_are_unchanged_new_bytes_are_changed(self):
        first = self.refresh(FakeClient(last_done="10.00"))
        self.assertEqual(len(first["added"]), 4)
        self.assertEqual(first["changed"] + first["unchanged"] + first["failed"], [])

        again = self.refresh(FakeClient(last_done="10.00"))
        self.assertEqual(again["added"] + again["changed"], [])
        self.assertEqual(len(again["unchanged"]), 4)

        moved = self.refresh(FakeClient(last_done="11.50"))
        self.assertEqual(moved["added"], [])
        self.assertTrue(moved["changed"], "a new price must register as a changed source version")
        self.assertNotIn("longbridge", moved["adapter_errors"])

    def test_missing_credentials_lands_as_failed_not_silence(self):
        result = service.refresh_sources(self.root, SECURITY, ["prices"],
                                         clients={"longbridge_factory": lambda: None},
                                         store=self.store)
        self.assertEqual(result["added"] + result["changed"] + result["unchanged"], [])
        self.assertEqual(len(result["failed"]), 4)


class EvidenceTests(ServiceCase):
    def ingest(self, **kwargs):
        return service.ingest_source(self.bundle, entity_ids=["XNAS:DEMO"], **kwargs)

    def test_excerpt_only_is_registered_as_truncated(self):
        record = self.ingest(url="https://example.invalid/note", excerpt="line one",
                             author="An Analyst", published_at="2026-03-04",
                             source_type="broker_report",
                             note="paywalled; only the visible part")
        self.assertEqual(record["kind"], "industry_report")
        self.assertTrue(record["truncated"])
        self.assertEqual(record["published_at"], "2026-03-04")
        plain = self.ingest(excerpt="something the user read")
        self.assertEqual(plain["kind"], "other_public")

    def test_nothing_to_ingest_is_refused(self):
        with self.assertRaises(ContractError):
            self.ingest()

    def test_read_evidence_pages_by_line_number(self):
        body = self.root / "long.txt"
        body.write_text("\n".join(f"line {n}" for n in range(1, 13)), encoding="utf-8")
        record = self.ingest(file_path=str(body), note="twelve lines")
        first = service.read_evidence(self.bundle, record["evidence_id"], 0, 5)
        self.assertEqual((first["first_line"], first["last_line"]), (1, 5))
        self.assertEqual(first["locator"], "L1-L5")
        self.assertTrue(first["has_more"])
        self.assertEqual(first["text"].splitlines()[0], "line 1")
        last = service.read_evidence(self.bundle, record["evidence_id"], 10, 5)
        self.assertEqual((last["first_line"], last["last_line"]), (11, 12))
        self.assertFalse(last["has_more"])
        self.assertEqual(last["total_lines"], 12)
        past_end = service.read_evidence(self.bundle, record["evidence_id"], 99, 5)
        self.assertIsNone(past_end["locator"])
        with self.assertRaises(ContractError):
            service.read_evidence(self.bundle, "ev-nonexistent")
        with self.assertRaises(ContractError):
            service.read_evidence(self.bundle, record["evidence_id"], 0, 0)

    def test_search_filters_and_reports_absence_honestly(self):
        self.ingest(url="https://example.invalid/a", excerpt="alpha", author="Someone",
                    published_at="2026-03-04", source_type="news")
        self.ingest(excerpt="beta")
        everything = service.search_evidence(self.bundle)
        self.assertEqual(everything["count"], 2)
        self.assertEqual(service.search_evidence(self.bundle, kind="industry_report")["count"], 1)
        self.assertEqual(service.search_evidence(self.bundle, query="user_document")["count"], 2)
        miss = service.search_evidence(self.bundle, query="no such thing")
        self.assertEqual(miss["count"], 0)
        self.assertIn("not absence", miss["note"])


class CalculateTests(ServiceCase):
    def test_unknown_method_is_refused(self):
        with self.assertRaises(ContractError) as caught:
            service.calculate("vibes", {})
        self.assertIn("fcff_dcf", str(caught.exception))

    def test_receipt_carries_inputs_and_version(self):
        params = {"cashflows": [100.0, 110.0, 120.0], "discount_rate": 0.1,
                  "terminal_growth": 0.02, "cash": 50.0, "nonoperating_assets": 0.0,
                  "debt": 20.0, "other_claims": 0.0, "diluted_shares": 100.0}
        receipt = service.calculate("fcff_dcf", params)
        self.assertEqual(receipt["inputs"], params)
        self.assertTrue(receipt["calculator_version"])
        self.assertGreater(receipt["result"]["fair_value_per_share"], 0)
        with self.assertRaises(ContractError):
            service.calculate("fcff_dcf", {"cashflows": [1.0]})


class ResearchTests(ServiceCase):
    def setUp(self):
        super().setUp()
        self.copy_example()
        self.payload = read_json(self.bundle / "research.json")
        self.subject = "XNAS:DEMO"

    def save(self, payload, previous=None):
        return service.save_research(self.store, self.bundle, payload, subject=self.subject,
                                     expected_previous_version_id=previous, role_meta=ROLE,
                                     intake=passthrough_intake)

    def test_save_validates_then_stores_with_a_receipt(self):
        saved = self.save(self.payload)
        self.assertEqual(saved["status"], "latest")
        self.assertEqual(saved["role"], "researcher")
        self.assertEqual(saved["model"], "fake-1")
        self.assertIn("valuation", saved["calc_receipt"])
        self.assertEqual(self.store.latest_research(self.subject)["version_id"],
                         saved["version_id"])

    def test_invalid_payload_leaves_nothing_behind(self):
        broken = {**self.payload, "packet_id": "packet-not-this-one"}
        with self.assertRaises(ContractError):
            self.save(broken)
        self.assertIsNone(self.store.latest_research(self.subject))

    def test_stale_save_returns_a_conflict(self):
        first = self.save(self.payload)
        second = self.save({**self.payload, "research_id": "demo-research-2"}, first["version_id"])
        stale = self.save({**self.payload, "research_id": "demo-research-3"}, first["version_id"])
        self.assertTrue(stale["conflict"])
        self.assertEqual(stale["current_version_id"], second["version_id"])

    def test_context_lists_versions_sources_and_open_reviews(self):
        saved = self.save(self.payload)
        job = service.request_review(self.store, subject=self.subject,
                                     version_id=saved["version_id"], dispute="terminal growth",
                                     evidence_ids=[], reviewer={"execution": "interactive"})
        context = service.get_research_context(self.store, self.bundle, self.subject)
        self.assertEqual(context["latest_version_id"], saved["version_id"])
        self.assertEqual(context["versions"][0]["execution_state"],
                         self.payload["execution_state"])
        self.assertNotIn("rating", context["versions"][0])  # null stays absent, not invented
        self.assertTrue(context["sources"])
        self.assertEqual([r["job_id"] for r in context["reviews"]], [job["job_id"]])
        self.assertNotIn("text", context["sources"][0])

    def test_publish_records_the_page_path(self):
        saved = self.save(self.payload)
        released = service.publish_research(self.store, self.bundle, saved["version_id"],
                                            self.root / "releases")
        page = Path(released["index_html"])
        self.assertTrue(page.is_file())
        self.assertEqual(self.store.get_research(saved["version_id"])["publication_path"],
                         str(page))
        with self.assertRaises(ContractError):
            service.publish_research(self.store, self.bundle, "rv-nope", self.root / "releases")


class ReviewTests(ServiceCase):
    def test_request_claim_submit(self):
        # Interactive: the job waits for another client to claim it. The api path runs
        # the adapter inside request_review and is covered in test_review_api.
        job = service.request_review(self.store, subject="XNAS:DEMO", version_id="rv-1",
                                     dispute="is the improvement durable?",
                                     evidence_ids=["ev-1"],
                                     reviewer={"execution": "interactive",
                                               "provider": "anthropic",
                                               "model": "some-model"})
        self.assertEqual(job["status"], "pending")
        self.assertEqual(job["input_ref"]["dispute"], "is the improvement durable?")
        running = service.claim_review(self.store, job["job_id"], "client-b")
        self.assertEqual(running["status"], "running")
        with self.assertRaises(ContractError):
            service.claim_review(self.store, job["job_id"], "client-c")
        done = service.submit_review(self.store, job["job_id"], REVIEW_RESULT)
        self.assertEqual(done["status"], "done")
        stored = service.get_job(self.store, job["job_id"])["result_ref"]
        self.assertEqual(stored["verdict_on_dispute"]["verdict"], "challenges_research")
        with self.assertRaises(ContractError):
            service.submit_review(self.store, job["job_id"], "not an object")
        with self.assertRaises(ContractError):
            service.get_job(self.store, "job-nonexistent")

    def test_bad_reviewer_execution_is_refused(self):
        with self.assertRaises(ContractError):
            service.request_review(self.store, subject="s", version_id="v", dispute="d",
                                   evidence_ids=[], reviewer={"execution": "telepathy"})


if __name__ == "__main__":
    unittest.main()
