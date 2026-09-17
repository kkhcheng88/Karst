"""One evidence store per company: repeated research shares it, two companies stay apart."""
import tempfile
import unittest
from pathlib import Path

from karst import service, store as store_module
from karst.tests.test_longbridge import FakeClient

# Parameterized test identities, never production defaults.
FIRST = {"ticker": "DEMO", "issuer_id": "cik:0000000001", "security_id": "XNAS:DEMO",
         "currency": "USD", "exchange": "XNAS", "symbols": {"longbridge": "DEMO.US"}}
SECOND = {"ticker": "TEST", "issuer_id": "cik:0000000002", "security_id": "XNYS:TEST",
          "currency": "USD", "exchange": "XNYS", "symbols": {"longbridge": "TEST.US"}}


class CompanyStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.data = Path(self.directory.name) / "karst-data"
        self.store = store_module.init(self.data / service.DB_NAME)
        self.addCleanup(self.store.close)

    def refresh(self, security, last_done="10.00"):
        return service.refresh_sources(self.data, security, ["prices"], since="2026-01-01",
                                       clients={"longbridge": FakeClient(last_done=last_done)},
                                       store=self.store)

    def test_paths_are_per_company_and_sanitized(self):
        paths = service.ensure_company(self.store, self.data, FIRST)
        self.assertEqual(paths["bundle"], self.data / "companies" / "XNAS_DEMO" / "bundle")
        self.assertTrue(paths["releases"].is_dir())
        self.assertTrue(paths["tmp"].is_dir())
        self.assertEqual(self.store.get_entity("XNAS:DEMO")["kind"], "security")
        self.assertEqual(self.store.get_entity("cik:0000000001")["kind"], "company")

    def test_second_refresh_of_one_company_adds_nothing_new(self):
        first = self.refresh(FIRST)
        self.assertTrue(first["added"])
        self.assertEqual(first["changed"] + first["unchanged"], [])

        again = self.refresh(FIRST)
        self.assertEqual(again["added"] + again["changed"], [])
        self.assertEqual(sorted(again["unchanged"]), sorted(first["added"]))
        self.assertEqual(again["bundle"], first["bundle"])
        # Landing directories are scratch, one per run, under the data root's tmp/.
        self.assertNotEqual(again["staging"], first["staging"])
        self.assertTrue(Path(again["staging"]).is_relative_to(self.data / "tmp"))

    def test_two_companies_do_not_share_a_bundle(self):
        first = self.refresh(FIRST)
        second = self.refresh(SECOND, last_done="11.50")
        self.assertNotEqual(first["bundle"], second["bundle"])
        self.assertTrue(second["added"], "a second company starts with its own empty store")
        self.assertEqual(second["unchanged"], [])
        self.assertEqual(set(first["added"]) & set(second["added"]), set())
        # The registry in each bundle is the record of what that company holds; SQLite
        # keeps no second copy of it.
        theirs = service.search_evidence(second["bundle"])["results"]
        self.assertEqual({row["evidence_id"] for row in theirs}, set(second["added"]))
        ours = service.search_evidence(first["bundle"])["results"]
        self.assertEqual([row["evidence_id"] for row in ours
                          if row["evidence_id"] in second["added"]], [])

    def test_changed_content_registers_as_changed_not_added(self):
        self.refresh(FIRST)
        moved = self.refresh(FIRST, last_done="12.25")
        self.assertEqual(moved["added"], [])
        self.assertTrue(moved["changed"])


if __name__ == "__main__":
    unittest.main()
