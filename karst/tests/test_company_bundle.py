"""The company evidence store behind one interface (KARST-258).

The legacy fixture is a bundle exactly as stores written before this interface look
on the cloud data volume: registry manifest, objects, observations, packet.json and
evidence.json — and no security.json. Registry and packet bytes are produced by the
same canonical writers as before, so dropping security.json reproduces that format.
"""
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karst import service, store as store_module
from karst.company_bundle import CompanyBundle
from karst.fetch import registry as registry_module
from karst.packet import read_json
from karst.daily_bench import FakeLongbridge, Faults
from karst.schema import ContractError, digest

# Parameterized test identity, never a production default.
SECURITY = {"ticker": "DEMO", "issuer_id": "cik:0000000001", "security_id": "XNAS:DEMO",
            "name": "Demo Holdings", "currency": "USD", "exchange": "XNAS",
            "symbols": {"longbridge": "DEMO.US"}}


def files(root):
    return {p.relative_to(root).as_posix(): digest(p.read_bytes())
            for p in sorted(Path(root).rglob("*")) if p.is_file()}


class CompanyBundleTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.data = Path(directory.name) / "karst-data"
        self.store = store_module.init(self.data / service.DB_NAME)
        self.addCleanup(self.store.close)
        result = service.refresh_sources(self.data, SECURITY, ["prices"], since="2026-01-01",
                                         clients={"longbridge": FakeLongbridge(Faults(0, 0, random.Random(0)), 30)},
                                         store=self.store)
        self.assertNotIn("packet_error", result)
        self.bundle = Path(result["bundle"])
        self.company = CompanyBundle(self.bundle)

    def legacy(self):
        """The pre-interface format: the identity only in the working packet."""
        (self.bundle / "security.json").unlink()
        return files(self.bundle)

    def test_legacy_bundle_reads_unchanged_and_writes_nothing(self):
        before = self.legacy()
        packet = read_json(self.bundle / "packet.json")
        self.assertEqual(self.company.security()["security_id"], packet["security"]["security_id"])
        self.assertEqual(self.company.security()["exchange"], "XNAS")
        self.assertEqual(self.company.working(), (packet, read_json(self.bundle / "evidence.json")))
        self.assertEqual(len(self.company.records()), len(packet["evidence_ids"]) +
                         len(packet["diagnostic_ids"]))
        self.assertTrue(self.company.observations())
        context = service.get_research_context(self.store, self.bundle, "XNAS:DEMO",
                                               data_dir=self.data)
        self.assertEqual(context["packet_id"], packet["packet_id"])
        self.assertEqual(context["security"]["security_id"], "XNAS:DEMO")
        service.search_evidence(self.bundle)
        charts = service.render_charts(self.bundle, self.data / "charts")
        self.assertTrue(charts["artifacts"])
        self.assertEqual(files(self.bundle), before, "reading a legacy store must not rewrite it")

    def test_first_claim_on_a_legacy_bundle_only_adds_the_identity(self):
        before = self.legacy()
        service.ensure_company(self.store, self.data, SECURITY)
        after = files(self.bundle)
        self.assertEqual({k: v for k, v in after.items() if k != "security.json"}, before)
        self.assertEqual(read_json(self.bundle / "security.json")["symbols"], SECURITY["symbols"])

    def test_identity_is_one_record_and_another_security_is_refused(self):
        self.assertEqual(self.company.security(), read_json(self.bundle / "security.json"))
        # A caller that only knows the id does not erase what the store learned.
        self.company.claim({"security_id": "XNAS:DEMO"})
        self.assertEqual(self.company.security()["symbols"], SECURITY["symbols"])
        with self.assertRaises(ContractError):
            self.company.claim({"security_id": "XNAS:OTHER"})
        entity = self.store.get_entity("XNAS:DEMO")
        self.assertEqual((entity["exchange"], entity["currency"]), ("XNAS", "USD"))

    def test_chart_clock_comes_from_the_identity_not_the_title(self):
        seen = []
        original = service.bars_module.series_for

        def spy(bundle, security, as_of, **kwargs):
            seen.append(security)
            return original(bundle, security, as_of, **kwargs)
        with patch.object(service.bars_module, "series_for", spy):
            service.render_charts(self.bundle, self.data / "charts", title="HKEX:SOMETHING")
        self.assertEqual(seen[0]["exchange"], "XNAS")

    def test_a_failed_write_leaves_the_previous_snapshot_whole(self):
        packet, records = self.company.working()
        before = files(self.bundle)
        with patch.object(registry_module.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.company.save_working({**packet, "as_of": "2000-01-01T00:00:00Z"}, records)
        self.assertEqual(files(self.bundle), before, "no torn file and no stray temporary")


if __name__ == "__main__":
    unittest.main()
