"""The source port: every adapter lands the same shape, and the registry believes it.

Offline throughout: each adapter gets its own fake client, nothing reaches a network,
and the only identity in the file comes from the fixtures themselves.
"""
import tempfile
import unittest
from pathlib import Path

from karst import service
from karst.fetch import broker, defeatbeta, edgar, longbridge, port, prices
from karst.fetch.port import LandedRecord
from karst.fetch.registry import EvidenceRegistry, evidence_kind, load_meta
from karst.tests.test_fetch import EdgarHarness, FakeTicker, PricesTests, submissions_fixtures
from karst.tests.test_longbridge import FakeClient

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def security_for(ticker, cik, exchange="NASDAQ"):
    """Identity arrives as a parameter; nothing below this line knows a company."""
    return {"ticker": ticker, "issuer_id": f"cik:{cik}", "security_id": f"{exchange}:{ticker}",
            "exchange": exchange, "currency": "USD", "name": f"{ticker} fixture"}


class LandedRecordTests(unittest.TestCase):
    def test_a_record_must_name_its_kind_and_explain_anything_but_ok(self):
        record = LandedRecord(kind="prices", path=Path("a.json"), meta_path=Path("a.meta.json"))
        self.assertEqual((record.kind, record.status, record.status_reason), ("prices", "ok", None))
        for bad in (dict(kind="", path=Path("a"), meta_path=Path("m")),
                    dict(kind="prices", path=Path("a"), meta_path=Path("m"), status="FAILED",
                         status_reason="x"),
                    dict(kind="prices", path=None, meta_path=Path("m")),
                    dict(kind="prices", path=None, meta_path=Path("m"), status="error")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                LandedRecord(**bad)

    def test_one_status_judgement_covers_error_envelopes_then_emptiness(self):
        for response, expected in (({"error_code": 2101400, "message": "nope"}, "error"),
                                   ({"ret_code": -1}, "error"), ({"data": []}, "empty"),
                                   (None, "empty"), ([], "empty"), ({"data": {"a": 1}}, "ok"),
                                   ([{"a": 1}], "ok")):
            with self.subTest(response=response):
                status, _error, reason = port.response_status(response)
                self.assertEqual(status, expected)
                self.assertEqual(reason is None, expected == "ok")


class AdapterPortTests(unittest.TestCase):
    """Each adapter's fetch(security, out_dir, since=, client=) -> declared LandedRecords."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def check(self, records, *, kinds=None):
        self.assertTrue(records)
        for record in records:
            with self.subTest(meta=record.meta_path.name):
                self.assertIsInstance(record, LandedRecord)
                self.assertTrue(record.kind)
                self.assertIn(record.status, ("ok", "empty", "error"))
                if record.status != "ok":
                    self.assertTrue(record.status_reason, "a failure must say why")
                meta, _ = load_meta(record.meta_path)
                # The declared kind is what the legacy inference produced, so declaring
                # it does not re-identify evidence that is already registered.
                self.assertEqual(record.kind, evidence_kind(meta))
        if kinds is not None:
            self.assertEqual({record.kind for record in records}, kinds)
        return records

    def test_edgar_lands_for_any_security_by_parameter_only(self):
        for index, path in enumerate(submissions_fixtures()):
            harness = EdgarHarness(path, self.root / f"harness{index}")
            records = edgar.fetch(security_for(harness.ticker, harness.cik),
                                  self.root / f"out{index}",
                                  client={"http_get": harness.http_get,
                                          "submissions_dir": harness.submissions_dir,
                                          "tenk_cache_dir": harness.tenk_hit,
                                          "n_10k": 1, "n_10q": 1, "n_8k": 1})
            self.check(records)
            self.assertIn("filing_index", {record.kind for record in records})
            self.assertIn("filing", {record.kind for record in records})

    def test_edgar_failure_lands_a_diagnostic_with_a_reason(self):
        def broken(_url):
            raise OSError("offline test outage")
        harness = EdgarHarness(submissions_fixtures()[0], self.root / "harness")
        records = edgar.fetch(security_for(harness.ticker, harness.cik), self.root / "out",
                              client={"http_get": broken, "submissions_dir": harness.submissions_dir,
                                      "tenk_cache_dir": harness.tenk_miss,
                                      "forms": ("10-Q",), "n_10q": 1})
        self.check(records)
        failed = [record for record in records if record.status == "error"]
        self.assertEqual(len(failed), 1)
        self.assertIsNone(failed[0].path, "a failed fetch lands its sidecar, not an invented body")
        self.assertIn("offline test outage", failed[0].status_reason)

    def test_defeatbeta_declares_transcript_apart_from_its_catalogue(self):
        try:
            import pandas as pd  # noqa: PLC0415
        except ImportError:
            self.skipTest("pandas needed for the offline DefeatBeta harness")
        ticker = load_meta(FIXTURES / "defeatbeta/info.meta.json")[0]["params"]["ticker"]
        records = self.check(defeatbeta.fetch(
            security_for(ticker, "0000000001"), self.root,
            client=lambda _t: FakeTicker(FIXTURES / "defeatbeta", pd)))
        kinds = [record.kind for record in records]
        self.assertEqual(kinds.count("transcript"), 2)  # latest two for the research mandate
        self.assertIn("filing_index", kinds)  # the catalogue is an index, not transcript text
        self.assertTrue([r for r in records if r.status == "empty" and r.status_reason])

    def test_longbridge_derives_its_own_vendor_symbol(self):
        records = self.check(longbridge.fetch(security_for("DEMO", "0000000001"), self.root,
                                              since="2026-01-01", client=FakeClient()),
                             kinds={"prices", "profile"})
        self.assertEqual(len(records), 4)

    def test_longbridge_without_credentials_reports_the_reason(self):
        records = self.check(longbridge.fetch(security_for("DEMO", "0000000001"), self.root,
                                              client=lambda: None))
        self.assertTrue(all(record.status == "error" for record in records))
        self.assertTrue(all(longbridge.MISSING_CREDENTIALS in record.status_reason
                            for record in records))

    def test_prices_lands_the_merged_series(self):
        case = PricesTests("test_fetch_daily_lands_csv_and_meta")
        case.setUp()
        local = {"rows": case.local, "shard": prices.shard_for(case.meta["params"]["cik"]),
                 "manifest_rows": case.meta.get("local_manifest_rows", []),
                 "roles": {"primary": len(case.local)},
                 "tickers": {case.local[0]["ticker"]: len(case.local)}}
        records = self.check(prices.fetch(
            security_for(case.meta["params"]["ticker"], case.meta["params"]["cik"]), self.root,
            client={"local": local, "vendor_rows": case.vendor, "days": len(case.local)}),
            kinds={"prices"})
        self.assertEqual(len(records), 1)

    def test_broker_lands_only_what_the_agent_already_holds(self):
        security = security_for("DEMO", "0000000001")
        self.assertEqual(broker.fetch(security, self.root), [])
        records = self.check(broker.fetch(security, self.root, client=[
            {"source": "longbridge", "tool": "mcp__longbridge__consensus",
             "params": {"symbol": "DEMO.US"}, "response": {"data": [{"eps": 1}]}},
            {"source": "futu", "tool": "mcp__futu__quote_short_interest",
             "params": {"code": "US.DEMO"}, "response": {"data": []}},
        ]), kinds={"consensus", "short_interest"})
        empty = [record for record in records if record.status == "empty"]
        self.assertEqual(len(empty), 1)
        self.assertIn("not covered", empty[0].status_reason)

    def test_a_broker_tool_off_the_public_allowlist_has_no_kind(self):
        with self.assertRaises(ValueError):
            broker.kind_for({"tool": "mcp__futu__quote_something_new"})


class RegistryBelievesTheAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = EvidenceRegistry(self.root / "bundle")

    def landed(self, response, tool="mcp__longbridge__consensus"):
        broker.land(self.root / "staging", "longbridge", tool, "DEMO.US", {"symbol": "DEMO.US"},
                    response, fetched_at="2026-01-01T00:00:00Z")
        records = broker.fetch(security_for("DEMO", "0000000001"), self.root / "staging")
        # fetch() with no client lands nothing; scan the directory the landing used.
        self.assertEqual(records, [])
        return port.scan(self.root / "staging" / "longbridge", broker.kind_for)

    def test_the_declared_kind_is_used_as_it_stands(self):
        record, = self.landed({"data": [{"eps": 1}]})
        stored = self.registry.register(record, entity_ids=["issuer:fixture"])
        self.assertEqual(stored["kind"], "consensus")
        # Declared beats inferred: the registry registers, it does not classify.
        forced = self.registry.register(
            LandedRecord(kind="other_public", path=record.path, meta_path=record.meta_path,
                         status=record.status, status_reason=record.status_reason),
            entity_ids=["issuer:fixture"])
        self.assertEqual(forced["kind"], "other_public")

    def test_an_adapter_judged_status_is_not_judged_again(self):
        record, = self.landed({"error_code": 500, "message": "upstream"})
        stored = self.registry.register(record, entity_ids=["issuer:fixture"])
        self.assertEqual(stored["status"], "error")
        self.assertEqual(stored["status_reason"], record.status_reason)
        self.assertTrue(stored["status_reason"])


class FakeAdapter:
    KINDS = ("test_kind",)

    def __init__(self, explode=False):
        self.calls, self.explode = [], explode

    def fetch(self, security, out_dir, *, since=None, client=None):
        self.calls.append({"security": security, "out_dir": Path(out_dir), "since": since,
                           "client": client})
        if self.explode:
            raise RuntimeError("source is down")
        return []


class AdapterTableTests(unittest.TestCase):
    """service iterates one {name: adapter} table; there is no per-source branch left."""

    def test_kind_routing_is_composed_from_what_each_adapter_declares(self):
        expected = {kind: name for name, module in service.ADAPTERS.items()
                    for kind in module.KINDS}
        self.assertEqual(service.KIND_ADAPTERS, expected)
        self.assertEqual(service.KIND_ADAPTERS["filing"], "edgar")
        self.assertEqual(service.KIND_ADAPTERS["transcript"], "defeatbeta")
        self.assertEqual(service.KIND_ADAPTERS["prices"], "longbridge")

    def test_every_requested_adapter_is_called_through_the_same_entry(self):
        good, bad = FakeAdapter(), FakeAdapter(explode=True)
        original = dict(service.ADAPTERS)
        service.ADAPTERS.update({"good": good, "bad": bad})
        self.addCleanup(lambda: (service.ADAPTERS.clear(), service.ADAPTERS.update(original)))
        security = security_for("DEMO", "0000000001")
        landed, coverage = service._run_adapters("staging", security, {"good", "bad"},
                                                 "2026-01-01", {"good": "client-object"})
        self.assertEqual(landed, [])
        self.assertEqual(sorted(coverage), ["bad", "good"])
        broken = coverage["bad"]["feeds"][0]
        self.assertEqual((coverage["bad"]["status"], broken["cause"]), ("failed", "error"))
        self.assertIn("source is down", broken["reason"])
        # Landing nothing is not coverage either, but it is told apart from a crash.
        self.assertEqual(coverage["good"]["feeds"][0]["cause"], "empty")
        self.assertEqual(good.calls[0]["since"], "2026-01-01")
        self.assertEqual(good.calls[0]["client"], "client-object")
        self.assertEqual(good.calls[0]["security"], security)
        self.assertEqual(len(bad.calls), 1, "one broken source must not hide the others")


class CoverageTests(unittest.TestCase):
    def record(self, name, status="ok"):
        return LandedRecord(kind="prices", path=Path(name) if status == "ok" else None,
                            meta_path=Path(name + ".meta.json"), status=status,
                            status_reason=None if status == "ok" else "vendor said no")

    def test_single_feed_adapter_is_derived_from_its_records(self):
        records, report = port.cover("vendor", lambda: [self.record("a"), self.record("b", "empty")])
        self.assertEqual(len(records), 2)
        self.assertEqual(report["status"], "partial")
        self.assertEqual([(f["feed"], f["status"], f["cause"]) for f in report["feeds"]],
                         [("b", "failed", "empty"), ("vendor", "ok", None)])
        self.assertEqual(port.cover("vendor", lambda: [self.record("a")])[1]["status"], "ok")

    def test_timeout_is_a_cause_and_no_report_is_not_complete(self):
        def slow():
            raise TimeoutError("read timed out")
        _, report = port.cover("vendor", slow)
        self.assertEqual((report["status"], report["feeds"][0]["cause"]), ("failed", "timeout"))
        self.assertFalse(port.complete({"vendor": report}))
        self.assertFalse(port.complete({}))
        with self.assertRaises(ValueError):
            port.FeedOutcome("x", "failed")  # a failure must say why

    def test_a_vendor_quota_is_its_own_cause_and_is_not_retried(self):
        from karst.fetch import limits
        text = ("OpenApiException: (kind=ErrorKind.OpenApi, code=301607, trace_id=) history "
                "candlestick symbol count out of limit, requested:100/limit:100")
        calls = []

        def refused():
            calls.append(1)
            raise RuntimeError(text)
        with self.assertRaises(RuntimeError):
            limits.call("longbridge", refused)
        self.assertEqual(len(calls), 1)  # no backoff retry can free an account allowance
        self.assertEqual(port.failure_cause(RuntimeError(text)), "quota")
        self.assertEqual(port.reason_cause(f"RuntimeError: {text}"), "quota")
        self.assertEqual(port.cover("vendor", refused)[1]["feeds"][0]["cause"], "quota")
        self.assertEqual(port.failure_cause(RuntimeError("code=301600 bad request")), "error")


class FailureIsVisibleTests(unittest.TestCase):
    """A broken source must read differently from a source with nothing to report."""

    def test_the_reason_reaches_whoever_searches_the_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            security = security_for("DEMO", "0000000001")
            security["symbols"] = {"longbridge": "DEMO.US"}
            result = service.refresh_sources(root, security, ["prices"],
                                             clients={"longbridge": lambda: None})
            self.assertEqual(result["added"] + result["changed"] + result["unchanged"], [])
            self.assertEqual(len(result["failed"]), 4)
            found = service.search_evidence(result["bundle"])
            self.assertEqual(found["count"], 4)
            for row in found["results"]:
                with self.subTest(evidence=row["evidence_id"]):
                    self.assertEqual(row["status"], "error")
                    self.assertIn(longbridge.MISSING_CREDENTIALS, row["status_reason"])


class ImportDirectionTests(unittest.TestCase):
    def test_the_cli_shell_is_imported_by_nobody(self):
        offenders = []
        for path in sorted((Path(service.__file__).parent).rglob("*.py")):
            if path.name == "pipeline.py" or "tests" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            if "from .pipeline import" in text or "from ..pipeline import" in text \
                    or "import karst.pipeline" in text:
                offenders.append(path.name)
        self.assertEqual(offenders, [], "pipeline.py is a CLI shell: adapters -> service -> domain")


if __name__ == "__main__":
    unittest.main()
