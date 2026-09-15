"""Precision, retrieval outcomes and public fixture shapes from PR 1 review round two."""
import copy
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from karst.packet import check_packet, read_json, resolve_request, time_bounds
from karst.publish import publish, verify_release
from karst.schema import ContractError, canonical, digest, schema_hashes, schemas, validate
from karst.tests.test_core import BundleCase
from karst.tests import test_core as core_tests


class PrecisionTests(BundleCase):
    def date_only(self, field="published_at", zone="America/New_York"):
        self.records[0].update({field: "2025-01-31", field + "_precision": "date",
                                field + "_timezone": zone})

    def replay(self, cutoff):
        self.packet.update(knowledge_basis="public_as_of_replay", as_of=cutoff,
                           created_at="2025-02-03T22:00:00Z")
        self.records[0]["fetched_at"] = "2025-02-03T21:00:00Z"
        return check_packet(self.packet, self.records, self.bundle)

    def test_precision_and_value_must_agree(self):
        for value, precision in (("2025-01-31T00:00:00Z", "date"), ("2025-01-31", "datetime"),
                                 (None, "date"), ("2025-01-31", "unknown")):
            with self.subTest(value=value, precision=precision), self.assertRaises(ContractError):
                validate("evidence", {**self.records[0], "published_at": value,
                                      "published_at_precision": precision})

    def test_date_only_is_usable_when_actually_observed_today(self):
        self.date_only()
        self.check()
        self.assertEqual(self.records[0]["published_at"], "2025-01-31")

    def test_replay_rejects_same_day_ambiguity_and_accepts_end_of_source_day(self):
        self.date_only()
        with self.assertRaisesRegex(ContractError, "ambiguous"):
            self.replay("2025-01-31T22:00:00Z")
        self.replay("2025-02-01T05:00:00Z")

    def test_unknown_zone_uses_conservative_bounds(self):
        self.date_only(zone=None)
        with self.assertRaisesRegex(ContractError, "ambiguous"):
            self.replay("2025-02-01T00:00:00Z")
        self.replay("2025-02-01T14:00:00Z")

    def test_observation_proves_availability_inside_uncertain_day(self):
        self.date_only(zone=None)
        self.packet["knowledge_basis"] = "public_as_of_replay"
        self.check()  # fetched_at is at the cutoff; no midnight was invented.

    def test_future_day_and_invalid_zone_rejected(self):
        self.date_only(zone=None)
        self.records[0]["published_at"] = "2025-02-03"
        with self.assertRaisesRegex(ContractError, "after cutoff"):
            self.check()
        self.date_only(zone="Not/AZone")
        with self.assertRaisesRegex(ContractError, "Unknown IANA"):
            self.check()

    def test_dst_day_is_not_assumed_to_be_24_hours(self):
        self.date_only()
        self.records[0]["published_at"] = "2025-03-09"
        low, high = time_bounds(self.records[0], "published_at")
        self.assertEqual(high-low, timedelta(hours=23))

    def test_unknown_transcript_availability_is_not_call_date(self):
        row = self.records[0]
        row.update(kind="transcript", published_at=None, published_at_precision="unknown",
                   coverage={"report_date": "2025-01-30", "fiscal_year": 2024, "fiscal_quarter": 4})
        self.check()  # Today's observed transcript remains usable.
        self.packet["knowledge_basis"] = "public_as_of_replay"
        with self.assertRaisesRegex(ContractError, "known publication"):
            self.check()

    def test_data_as_of_unknown_stays_unknown_and_date_cannot_be_future(self):
        row = self.records[0]
        row.update(data_as_of=None, data_as_of_precision="unknown",
                   data_as_of_basis="Vendor response contains no timestamp")
        self.check()
        self.assertIsNone(row["data_as_of"])
        self.date_only("data_as_of", "UTC")
        self.records[0]["data_as_of"] = "2025-02-01"
        with self.assertRaisesRegex(ContractError, "after cutoff"):
            self.check()

    def test_timezone_free_datetime_cannot_be_silently_utc(self):
        self.records[0]["published_at"] = "2026-09-14 14:34:56"
        with self.assertRaises(ContractError):
            validate("evidence", self.records[0])


class OutcomeTests(BundleCase):
    def diagnostic(self, status="error"):
        row = copy.deepcopy(self.records[0])
        row.update(evidence_id="diagnostic-1", source_id="diagnostic-source", kind="ownership",
                   published_at=None, published_at_precision="unknown", status=status,
                   status_reason="Endpoint failed" if status == "error" else "Query returned zero rows")
        data = canonical({"error": "server error"} if status == "error" else {"rows": []})
        (self.bundle / "diagnostic.json").write_bytes(data)
        row["artifact"] = {"path": "diagnostic.json", "sha256": digest(data), "bytes": len(data)}
        self.records.append(row)
        self.packet["diagnostic_ids"] = [row["evidence_id"]]
        return row

    def test_error_and_empty_are_archived_but_not_usable_evidence(self):
        row = self.diagnostic()
        for status in ("error", "empty"):
            row["status"] = status
            self.check()
            self.packet["evidence_ids"].append(row["evidence_id"])
            with self.subTest(status=status), self.assertRaises(ContractError):
                self.check()
            self.packet["evidence_ids"].pop()

    def test_diagnostic_cannot_satisfy_requirement_citation_or_read_log(self):
        row = self.diagnostic()
        for target in ("requirement", "citation", "read_log"):
            old_packet, old_research = copy.deepcopy(self.packet), copy.deepcopy(self.research)
            if target == "requirement":
                self.packet["requirements"].append({"kind": "ownership", "status": "available",
                                                    "evidence_ids": [row["evidence_id"]], "reason": "Failed request"})
            elif target == "citation":
                self.research["headline"]["main_reason"]["citations"] = [{"evidence_id": row["evidence_id"], "locator": "L1"}]
            else:
                self.research["layers"]["L3"]["read_evidence_ids"].append(row["evidence_id"])
            with self.subTest(target=target), self.assertRaises(ContractError):
                self.check()
            self.packet, self.research = old_packet, old_research

    def test_diagnostic_cannot_fulfil_supplement(self):
        row = self.diagnostic()
        self.packet = resolve_request(self.packet, "demo-request-1", [row["evidence_id"]],
                                      resolution="Incorrectly claimed fulfilment", created_at=self.packet["created_at"])
        with self.assertRaises(ContractError):
            self.check()

    def test_later_failure_cannot_leak_into_historical_replay(self):
        row = self.diagnostic()
        row["fetched_at"] = "2025-02-01T00:00:00Z"
        self.packet.update(knowledge_basis="public_as_of_replay", created_at="2025-02-02T00:00:00Z")
        with self.assertRaisesRegex(ContractError, "not observed"):
            check_packet(self.packet, self.records, self.bundle)

    def test_release_preserves_diagnostic_and_displays_status(self):
        self.diagnostic()
        self.write()
        release = publish(self.bundle, self.root / "out")
        manifest = verify_release(release)
        self.assertEqual(manifest["contract_version"], "0.2.0")
        self.assertEqual(manifest["schema_hashes"], schema_hashes("0.2.0"))
        self.assertIn("取得失敗", (release / "index.html").read_text(encoding="utf-8"))
        self.assertTrue((release / "inputs/diagnostic.json").exists())


class CompatibilityTests(BundleCase):
    def test_v01_is_still_valid_and_pins_v01_schemas(self):
        # Drop v0.2 additions, as an old bundle would have none; old schemas remain untouched.
        for record in self.records:
            for key in set(record) - set(schemas("0.1.0")["evidence"]["properties"]):
                del record[key]
            record["contract_version"] = "0.1.0"
        self.packet.pop("diagnostic_ids")
        self.packet["contract_version"] = self.research["contract_version"] = "0.1.0"
        self.write()
        release = publish(self.bundle, self.root / "out")
        manifest = verify_release(release)
        self.assertEqual(manifest["schema_hashes"], schema_hashes("0.1.0"))

    def test_mixed_versions_rejected(self):
        self.research["contract_version"] = "0.1.0"
        with self.assertRaisesRegex(ContractError, "same contract version"):
            self.check()

    def test_manual_research_on_public_data_is_marked_as_integration_example(self):
        for row in self.records:
            row["provenance"] = "public_market"
        self.research["mode"] = "integration_example"
        self.write()
        release = publish(self.bundle, self.root / "out")
        self.assertIn("判斷為測試輸入", (release / "index.html").read_text(encoding="utf-8"))

    def test_windows_privilege_skip_is_specific_and_path_test_still_runs(self):
        denied = OSError("No privilege")
        denied.winerror = 1314
        suite = unittest.TestSuite([core_tests.ContractTests("test_path_escape"), core_tests.ContractTests("test_symlink_escape")])
        with patch.object(Path, "symlink_to", side_effect=denied):
            result = unittest.TestResult()
            suite.run(result)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.skipped), 1)
        self.assertFalse(result.errors or result.failures)
        with patch.object(Path, "symlink_to", side_effect=OSError("Unexpected I/O failure")):
            result = unittest.TestResult()
            core_tests.ContractTests("test_symlink_escape").run(result)
        self.assertEqual(len(result.errors), 1)


class FixtureShapeTests(BundleCase):
    def test_source_period_shapes_fit_without_inventing_fiscal_dates(self):
        fixtures = Path(__file__).parent / "fixtures"
        cases = [
            ("edgar/0001437749-26-027677.10-Q.meta.json", "2026-06-30", "2026-06-30"),
            ("defeatbeta/earning_call_transcript.FY2026Q2.meta.json", None, None),
            ("defeatbeta/quarterly_income_statement.meta.json", "2022-06-30", "2026-06-30"),
            ("longbridge/quote.meta.json", "2026-09-14", "2026-09-14"),
            ("longbridge/institutional_views.meta.json", None, None),
            ("longbridge/consensus.meta.json", None, None),
            ("longbridge/finance_calendar.meta.json", None, None),
        ]
        if not all((fixtures / path).exists() for path, _, _ in cases):
            self.skipTest("Public fixtures are available in repository checkout, not wheel installation")
        for path, start, end in cases:
            meta = read_json(fixtures / path)
            row = copy.deepcopy(self.records[0])
            row.update(coverage=meta["period"], period={"start": start, "end": end})
            with self.subTest(path=path):
                validate("evidence", row)
                self.assertEqual(row["coverage"], meta["period"])
                self.assertEqual(row["period"], {"start": start, "end": end})

    def test_more_specific_kinds_and_strict_identifiers(self):
        for kind in ("ownership", "short_interest", "calendar", "profile", "valuation", "filing_index"):
            with self.subTest(kind=kind):
                validate("evidence", {**self.records[0], "kind": kind})
        with self.assertRaises(ContractError):
            validate("evidence", {**self.records[0], "source_id": "Company (snapshot)"})
        with self.assertRaises(ContractError):
            validate("evidence", {**self.records[0], "entity_ids": []})
