"""Contract boundaries and economic invariants, using explicitly synthetic inputs."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karst.calculations import calculate, confirmed_pivots, fcff_dcf, risk_reward, sma
from karst.packet import add_request, check_packet, check_research, confined, load_bundle, read_json, resolve_request
from karst.publish import publish, verify_release
from karst.schema import ContractError, canonical, decode, digest, validate

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic"


class BundleCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        shutil.copytree(EXAMPLE, self.bundle)
        self.packet = read_json(self.bundle / "packet.json")
        self.records = read_json(self.bundle / "evidence.json")
        self.research = read_json(self.bundle / "research.json")

    def write(self):
        for name, value in (("packet", self.packet), ("evidence", self.records), ("research", self.research)):
            (self.bundle / f"{name}.json").write_bytes(canonical(value))

    def check(self):
        selected = check_packet(self.packet, self.records, self.bundle)
        return check_research(self.packet, self.research, selected, self.bundle)


class ContractTests(BundleCase):
    def test_example_loads(self):
        packet, records, research = load_bundle(self.bundle)
        self.assertEqual(packet["packet_id"], research["packet_id"])
        self.assertEqual(len(records), 2)

    def test_unknown_version_and_private_root_field(self):
        for change in ({"contract_version": "999"}, {"holdings": []}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                validate("research", {**self.research, **change})

    def test_duplicate_keys_and_nonfinite_numbers(self):
        for data in (b'{"a":1,"a":2}', b'{"price":NaN}', b'{"price":Infinity}'):
            with self.subTest(data=data), self.assertRaises(ContractError):
                decode(data)
        self.research["market"]["price"] = float("inf")
        with self.assertRaises(ContractError):
            validate("research", self.research)

    def test_invalid_and_timezone_free_dates(self):
        for date in ("2025-02-30T22:00:00Z", "2025-01-31T22:00:00"):
            with self.subTest(date=date), self.assertRaises(ContractError):
                validate("packet", {**self.packet, "as_of": date})

    def test_private_or_secret_selector_rejected(self):
        for key in ("account_id", "cost_basis", "access_token"):
            self.records[0]["params"] = {"nested": [{key: "not-a-real-secret"}]}
            with self.subTest(key=key), self.assertRaises(ContractError):
                self.check()

    def test_future_observation_rejected_but_forward_guidance_period_allowed(self):
        self.records[0]["period"] = {"start": "2025-04-01", "end": "2025-06-30"}
        self.check()  # A future period is not a future publication.
        self.records[0]["published_at"] = "2025-02-01T00:00:00Z"
        with self.assertRaisesRegex(ContractError, "after cutoff"):
            self.check()

    def test_system_observed_and_public_replay_are_distinct(self):
        self.records[0]["fetched_at"] = "2025-01-31T22:01:00Z"
        with self.assertRaisesRegex(ContractError, "not observed"):
            self.check()
        self.packet["knowledge_basis"] = "public_as_of_replay"
        self.check()
        self.records[0]["published_at"] = None
        with self.assertRaisesRegex(ContractError, "known publication"):
            self.check()

    def test_hash_tampering(self):
        (self.bundle / "source.txt").write_text("changed")
        with self.assertRaisesRegex(ContractError, "hash/size"):
            self.check()

    def test_paths_and_symlink_escape(self):
        for path in ("../source.txt", "/tmp/source.txt", "a//b", "", "a/./b", "C:\\x"):
            with self.subTest(path=path), self.assertRaises(ContractError):
                confined(self.bundle, path)
        (self.root / "outside.txt").write_text("outside")
        (self.bundle / "escape.txt").symlink_to(self.root / "outside.txt")
        with self.assertRaises(ContractError):
            confined(self.bundle, "escape.txt")

    def test_citations_must_resolve_and_line_ranges_must_exist(self):
        for citation in ({"evidence_id": "unknown", "locator": "L1"},
                         {"evidence_id": "demo-e1", "locator": "L900"}):
            self.research["headline"]["main_reason"]["citations"] = [citation]
            with self.subTest(citation=citation), self.assertRaises(ContractError):
                self.check()

    def test_dependency_is_exact_version(self):
        self.packet["dependencies"][0]["version"] = "2"
        with self.assertRaisesRegex(ContractError, "version mismatch"):
            self.check()

    def test_pending_evidence_cannot_be_complete(self):
        self.research["coverage"] = "complete"
        with self.assertRaisesRegex(ContractError, "Complete coverage"):
            self.check()

    def test_truncated_and_unread_transcript(self):
        self.records[0]["kind"] = "transcript"
        self.packet["requirements"][0].update(status="available", evidence_ids=["demo-e1"])
        self.records[0]["truncated"] = True
        with self.assertRaisesRegex(ContractError, "Truncated"):
            self.check()
        self.records[0]["truncated"] = False
        self.research["layers"]["L3"]["read_evidence_ids"] = []
        with self.assertRaisesRegex(ContractError, "reading supplied transcripts"):
            self.check()

    def test_missing_transcript_status_rejected(self):
        self.packet["requirements"] = []
        with self.assertRaisesRegex(ContractError, "transcript availability"):
            self.check()

    def test_synthetic_cannot_be_published_as_real_replay(self):
        self.research["mode"] = "offline_replay"
        with self.assertRaisesRegex(ContractError, "Synthetic"):
            self.check()

    def test_future_or_inconsistent_bars(self):
        for update in ({"at": "2025-02-01T21:00:00Z"}, {"low": 999}):
            research = copy.deepcopy(self.research)
            self.research["technical"]["views"]["D"][-1].update(update)
            with self.subTest(update=update), self.assertRaises(ContractError):
                self.check()
            self.research = research

    def test_future_confirmation_rejected(self):
        self.research["technical"]["key_levels"][0]["confirmed_at"] = "2025-02-01T21:00:00Z"
        with self.assertRaisesRegex(ContractError, "not yet confirmed"):
            self.check()

    def test_supplement_preserves_input_and_pins_new_packet(self):
        old = copy.deepcopy(self.packet)
        req = {"request_id": "new-request", "layer": "L2", "question": "Supplier evidence?",
               "reason": "Exposure uncertain", "status": "pending", "evidence_ids": [], "resolution": None}
        pending = add_request(self.packet, req)
        self.assertEqual(self.packet, old)
        fulfilled = resolve_request(pending, "new-request", ["demo-e1"],
                                    resolution="Reviewed existing source", created_at=self.packet["created_at"])
        self.assertEqual(pending["supplement_requests"][-1]["status"], "pending")
        self.assertNotEqual(fulfilled["packet_id"], pending["packet_id"])
        self.packet = fulfilled
        with self.assertRaisesRegex(ContractError, "exact packet"):
            self.check()
        self.research["packet_id"] = fulfilled["packet_id"]
        self.check()

    def test_supplement_requires_registered_evidence(self):
        self.packet = resolve_request(self.packet, "demo-request-1", ["new-evidence"],
                                      resolution="new source", created_at=self.packet["created_at"])
        with self.assertRaisesRegex(ContractError, "Unregistered"):
            self.check()


class CalculationTests(BundleCase):
    def test_dcf_perpetuity_identity_and_equity_bridge(self):
        inputs = copy.deepcopy(self.research["valuation"]["scenarios"][0]["calculation"])
        inputs.update(cashflows=[10, 10], discount_rate=.1, terminal_growth=0,
                      cash=8, debt=3, nonoperating_assets=2, other_claims=1, diluted_shares=2)
        value = fcff_dcf(inputs)
        # A constant $10 annual perpetuity at 10% is $100 EV; equity = 106, /2 shares = 53.
        self.assertAlmostEqual(value["enterprise_value"], 100)
        self.assertAlmostEqual(value["fair_value_per_share"], 53)

    def test_dcf_sensitivity_and_invalid_terminal(self):
        inputs = self.research["valuation"]["scenarios"][1]["calculation"]
        base = fcff_dcf(inputs)["fair_value_per_share"]
        self.assertLess(fcff_dcf({**inputs, "discount_rate": .15})["fair_value_per_share"], base)
        for update in ({"terminal_growth": inputs["discount_rate"]}, {"cashflows": [-10]}):
            with self.subTest(update=update), self.assertRaises(ContractError):
                fcff_dcf({**inputs, **update})

    def test_cost_dividend_and_gap_risk(self):
        plan = {**self.research["plan"], "entry_price": 100, "exit_price": 90,
                "target_price": 125, "stress_price": 70, "round_trip_cost_per_share": 1}
        result = risk_reward(plan, 2)
        self.assertEqual(result["planned_loss_per_share"], 11)
        self.assertEqual(result["reward_per_share"], 26)
        self.assertEqual(result["stress_loss_per_share"], 31)
        self.assertAlmostEqual(result["ratio"], 26/11)
        self.assertFalse(risk_reward({**plan, "exit_price": None})["available"])

    def test_sma_requires_completed_observations(self):
        bars = [{"close": 10, "complete": True}] * 199
        self.assertIsNone(sma(bars + [{"close": 100, "complete": False}]))
        self.assertEqual(sma(bars + [{"close": 30, "complete": True}]), 10.1)

    def test_pivot_is_known_only_after_right_hand_confirmation(self):
        bars = [dict(high=p, low=p-1, at=str(i), complete=True) for i,p in enumerate([2,3,6,3,2])]
        self.assertEqual(confirmed_pivots(bars[:-1]), [])
        pivot = confirmed_pivots(bars)[0]
        self.assertEqual((pivot["at"], pivot["confirmed_at"], pivot["price"]), ("2", "4", 6))

    def test_price_update_changes_gap_and_rr_but_not_intrinsic(self):
        first = calculate(self.research)
        self.research["market"]["price"] += 5
        second = calculate(self.research)
        self.assertEqual(first["valuation"], second["valuation"])
        self.assertLess(second["price_to_value_gap"], first["price_to_value_gap"])
        self.assertLess(second["current_price_risk_reward"]["ratio"], first["current_price_risk_reward"]["ratio"])


class PublicationTests(BundleCase):
    def test_release_idempotency_and_portable_inputs(self):
        first = publish(self.bundle, self.root / "out")
        before = (first / "publication.json").read_bytes()
        self.assertEqual(publish(self.bundle, self.root / "out"), first)
        self.assertEqual((first / "publication.json").read_bytes(), before)
        load_bundle(first / "inputs")
        manifest = verify_release(first)
        self.assertEqual(manifest["packet_id"], self.packet["packet_id"])

    def test_changed_target_creates_new_release_without_overwriting_old(self):
        old = publish(self.bundle, self.root / "out")
        old_research = (old / "inputs/research.json").read_bytes()
        self.research["research_id"] = "demo-research-2"
        self.research["valuation"]["target_prices"][1]["price"] = 95
        self.write()
        new = publish(self.bundle, self.root / "out", previous_publication_id=old.name)
        self.assertNotEqual(old, new)
        self.assertEqual((old / "inputs/research.json").read_bytes(), old_research)
        self.assertEqual(verify_release(new)["previous_publication_id"], old.name)

    def test_modified_release_rejected(self):
        release = publish(self.bundle, self.root / "out")
        (release / "index.html").write_text("tampered")
        with self.assertRaisesRegex(ContractError, "Published asset changed"):
            publish(self.bundle, self.root / "out")

    def test_failure_leaves_no_release_or_lock(self):
        with patch("karst.publish.render", side_effect=RuntimeError("simulated render failure")):
            with self.assertRaises(RuntimeError):
                publish(self.bundle, self.root / "out")
        self.assertEqual(list((self.root / "out").iterdir()), [])

    def test_second_writer_cannot_publish(self):
        output = self.root / "out"
        output.mkdir()
        (output / ".publish.lock").touch()
        with self.assertRaisesRegex(ContractError, "Another publisher"):
            publish(self.bundle, output)
        self.assertTrue((output / ".publish.lock").exists())

    def test_render_escapes_model_and_source_html(self):
        attack = '<script>alert("unsafe")</script>'
        self.research["headline"]["recommendation"]["text"] = attack
        source = self.bundle / "source.txt"
        source.write_text(source.read_text() + attack)
        data = source.read_bytes()
        self.records[0]["artifact"].update(sha256=digest(data), bytes=len(data))
        self.write()
        release = publish(self.bundle, self.root / "out")
        html = (release / "index.html").read_text()
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        for label in ("日線", "週線", "月線", "source-demo-e1", "六層研究", "非真實股票研究"):
            self.assertIn(label, html)


if __name__ == "__main__":
    unittest.main()
