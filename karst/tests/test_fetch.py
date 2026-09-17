"""Source adapters, offline: fixtures under tests/fixtures are the only inputs; every network call is a fake."""
import csv
import datetime as dt
import gzip
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

from karst.fetch import broker, common, defeatbeta, edgar, prices

FIXTURES = Path(__file__).resolve().parent / "fixtures"
META_EXTRAS = {"status", "status_reason", "source_url", "file", "data_as_of", "error", "symbol",
               "continuation_error"}


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def assert_meta_shape(case, produced_path, fixture_path):
    produced, fixture = set(read_json(produced_path)), set(read_json(fixture_path))
    case.assertTrue(fixture <= produced, f"{produced_path.name}: missing {sorted(fixture - produced)}")
    case.assertTrue(produced - fixture <= META_EXTRAS, f"{produced_path.name}: unexpected {sorted(produced - fixture - META_EXTRAS)}")
    meta = read_json(produced_path)
    case.assertIn(meta["status"], common.STATUSES)
    case.assertTrue(meta["fetched_at"].endswith("Z"))
    case.assertEqual(list(meta)[: len(common.META_ORDER)], [k for k in common.META_ORDER if k in meta])


class CommonTests(unittest.TestCase):
    def test_to_utc_z(self):
        cases = [
            ("2026-07-30T20:15:25.000Z", "2026-07-30T20:15:25Z"),
            ("2026-09-14T18:26:44+00:00", "2026-09-14T18:26:44Z"),
            ("2026-09-14T14:32:00-04:00", "2026-09-14T18:32:00Z"),
            ("2026-09-14T18:32:08.444Z", "2026-09-14T18:32:08.444Z"),
            ("2026-07-30", "2026-07-30"),
            ("2026-07-30T20:15:25", None),
            ("not a date", None),
            ("", None),
            (None, None),
            (dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=dt.timezone(dt.timedelta(hours=8))), "2026-01-01T19:04:05Z"),
            (dt.datetime(2026, 1, 2, 3, 4, 5), None),
            (dt.date(2026, 1, 2), "2026-01-02"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(common.to_utc_z(value), expected)

    def test_html_to_text(self):
        html = ("<html><head><style>x{color:red}</style><script>var a=1;</script></head><body>"
                "<p>A&amp;B&nbsp;C</p><!-- hidden --><table><tr><td>1</td><td>2</td></tr></table></body></html>")
        text = common.html_to_text(html)
        self.assertEqual(text.split(), ["A&B", "C", "1", "2"])
        for forbidden in ("<", "script", "color", "hidden"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(common.html_to_text(html.encode("utf-8")), text)

    def test_write_meta_order_defaults_and_file_record(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / "thing.json"
            data.write_bytes(b'{"a": 1}\n')
            meta_path = common.write_meta(data, source="futu", tool="t", params={}, zeta="last")
            self.assertEqual(meta_path.name, "thing.meta.json")
            meta = read_json(meta_path)
            self.assertEqual(list(meta), list(common.META_ORDER) + ["zeta", "file"])
            self.assertEqual(meta["status"], "ok")
            self.assertIsNone(meta["source_url"])
            self.assertTrue(meta["fetched_at"].endswith("Z"))
            self.assertEqual(meta["file"], {"name": "thing.json", "bytes": 9, "sha256": common.sha256_bytes(b'{"a": 1}\n')})
            with self.assertRaises(ValueError):
                common.write_meta(data, source="futu", status="partial")
            error_meta = common.write_meta(Path(temp) / "gone.meta.json", source="edgar", status="error", error="x")
            self.assertNotIn("file", read_json(error_meta))

    def test_ticker_to_cik_both_shapes(self):
        with tempfile.TemporaryDirectory() as temp:
            flat = Path(temp) / "flat.json"
            flat.write_text(json.dumps({"TEST": "0000000001"}), encoding="utf-8")
            numbered = Path(temp) / "numbered.json"
            numbered.write_text(json.dumps({"0": {"cik_str": 1, "ticker": "TEST", "title": "t"}}), encoding="utf-8")
            self.assertEqual(common.ticker_to_cik("test", flat), "0000000001")
            self.assertEqual(common.ticker_to_cik("TEST", numbered), "0000000001")
            with self.assertRaises(KeyError):
                common.ticker_to_cik("NOPE", flat)


def submissions_fixtures():
    return sorted(FIXTURES.glob("edgar/*.submissions_slice.json"))


class EdgarHarness:
    """Rebuild a local submissions dir, a 10-K cache and an offline HTTP map from one fixture set."""

    def __init__(self, slice_path: Path, temp: Path):
        temp.mkdir(parents=True, exist_ok=True)
        self.slice = read_json(slice_path)
        self.slice_meta = read_json(slice_path.with_suffix(".meta.json"))
        self.cik = self.slice_meta["params"]["cik"]
        self.ticker = self.slice_meta["params"]["ticker"]
        self.docs = {}
        for meta_path in sorted(FIXTURES.glob("edgar/*.meta.json")):
            if meta_path.name.endswith("submissions_slice.meta.json"):
                continue
            self.docs[meta_path.name[: -len(".meta.json")]] = read_json(meta_path)
        # index rows = the slice, plus the fixture documents the slice window does not reach (older 10-K / 8-K)
        rows = list(self.slice["filings"])
        known = {r["accessionNumber"] for r in rows}
        for meta in self.docs.values():
            p = meta["params"]
            if p["kind"] == "primary" and p["accession"] not in known:
                rows.append({"accessionNumber": p["accession"], "form": p["form"], "filingDate": meta["filingDate"],
                             "reportDate": meta["reportDate"], "acceptanceDateTime": meta["published_at"], "items": meta["items"],
                             "primaryDocument": p["document"], "primaryDocDescription": "", "isXBRL": 1, "isInlineXBRL": 1, "size": 0})
                known.add(p["accession"])
        self.rows = rows
        self.submissions_dir = temp / "submissions"
        self.submissions_dir.mkdir()
        recent = {field: [row.get(field) for row in rows] for field in edgar.ROW_FIELDS}
        header = {k: v for k, v in self.slice.items() if k not in ("filings", "total_filings_local", "slice_rule", "ticker")}
        files = [{"name": p["name"], "filingCount": p.get("filingCount")} for p in self.slice_meta["params"].get("paged_files", [])]
        (self.submissions_dir / f"CIK{self.cik}.json").write_text(
            json.dumps({**header, "filings": {"recent": recent, "files": files}}), encoding="utf-8")
        self.urls = {}
        for base, meta in self.docs.items():
            raw_name = meta["files"]["raw"]["name"]
            raw = (FIXTURES / "edgar" / raw_name).read_bytes()
            if raw_name.endswith(".gz"):
                raw = gzip.decompress(raw)
            self.urls[meta["params"]["url"]] = raw
            if "attachments_listed" in meta:
                rows = "".join(
                    f'<tr><td>{i}</td><td>{a["description"]}</td><td><a href="{a["href"]}">{a["file"]}</a></td><td>{a["type"]}</td><td>1</td></tr>'
                    for i, a in enumerate(meta["attachments_listed"], 1))
                self.urls[meta["index_page"]] = f"<html><body><table>{rows}</table></body></html>".encode("utf-8")
        self.tenk_hit = temp / "tenk_hit"
        self.tenk_hit.mkdir()
        self.tenk_miss = temp / "tenk_miss"
        self.tenk_miss.mkdir()
        for base, meta in self.docs.items():
            if meta["params"]["form"] == "10-K" and meta["params"]["kind"] == "primary":
                accession = edgar.accession_nodash(meta["params"]["accession"])
                text = (FIXTURES / "edgar" / meta["files"]["text"]["name"]).read_text(encoding="utf-8")
                with gzip.open(self.tenk_hit / f"{self.ticker}_{accession}.txt.gz", "wt", encoding="utf-8") as handle:
                    handle.write(text)
                entry = {"ticker": self.ticker, "cik": self.cik, "accession": accession, "form": "10-K", "url": meta["params"]["url"]}
                (self.tenk_hit / "manifest.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
        self.calls = []

    def http_get(self, url):
        self.calls.append(url)
        if url not in self.urls:
            raise urllib.error.URLError(f"offline: {url}")
        return self.urls[url]

    def fixture_by(self, form, kind):
        return {b: m for b, m in self.docs.items() if m["params"]["form"] == form and m["params"]["kind"] == kind}


class EdgarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.harnesses = [EdgarHarness(path, self.root / path.stem) for path in submissions_fixtures()]
        self.assertTrue(self.harnesses, "no submissions fixture found")

    def test_index_load_and_selection(self):
        for h in self.harnesses:
            with self.subTest(cik=h.cik):
                index = edgar.load_submissions(h.cik, h.submissions_dir)
                self.assertEqual(len(index["rows"]), len(h.rows))
                self.assertEqual([r["filingDate"] for r in index["rows"]], sorted((r["filingDate"] for r in index["rows"]), reverse=True))
                self.assertTrue(all(p["found_locally"] is False for p in index["paged_files"]))
                chosen = edgar.select_filings(index["rows"], n_10k=1, n_10q=1, n_8k=2)
                by_form = {}
                for row in chosen:
                    by_form.setdefault(row["form"], []).append(row["accessionNumber"])
                self.assertEqual(by_form["10-K"], [m["params"]["accession"] for m in h.fixture_by("10-K", "primary").values()])
                self.assertTrue(set(by_form["8-K"]) <= {m["params"]["accession"] for m in h.fixture_by("8-K", "primary").values()})
                self.assertTrue(all("2.02" in r["items"] for r in chosen if r["form"] == "8-K"))
                self.assertEqual(edgar.select_filings(index["rows"], forms=("8-K",), n_8k=1, eightk_items=None)[0]["form"], "8-K")

    def test_fetch_local_cache_hit_and_online_documents(self):
        for h in self.harnesses:
            with self.subTest(cik=h.cik):
                out = self.root / f"out_{h.cik}"
                results = edgar.fetch_filings(h.cik, out, n_10k=1, n_10q=1, n_8k=2, ticker=h.ticker, submissions_dir=h.submissions_dir,
                                              tenk_cache_dir=h.tenk_hit, http_get=h.http_get)
                self.assertTrue(all(r["status"] == "ok" for r in results), results)
                landed = out / "edgar"
                index_meta = read_json(landed / f"CIK{h.cik}.submissions_slice.meta.json")
                self.assertEqual(index_meta["params"]["cik"], h.cik)
                self.assertTrue(any("not held locally" in g for g in index_meta["known_gaps"]))
                # 10-K came from the local cache: no HTTP call for it, text identical to the cached text
                for base, meta in h.fixture_by("10-K", "primary").items():
                    self.assertNotIn(meta["params"]["url"], h.calls)
                    got = read_json(landed / f"{base}.meta.json")
                    self.assertTrue(got["local_cache_check"]["hit"])
                    self.assertIn("local", got["tool"])
                    self.assertEqual(got["source_url"], meta["params"]["url"])
                    self.assertFalse((landed / f"{base}.raw.htm.gz").exists())
                    self.assertEqual(got["files"]["text"]["sha256_full_text"],
                                     common.sha256_bytes((FIXTURES / "edgar" / meta["files"]["text"]["name"]).read_bytes()))
                # 10-Q online: verbatim bytes hash equals the fixture's, derived text hash equals the fixture's
                for base, meta in h.fixture_by("10-Q", "primary").items():
                    got = read_json(landed / f"{base}.meta.json")
                    self.assertEqual(got["files"]["raw"]["sha256"], meta["files"]["raw"]["sha256"])
                    self.assertEqual(got["files"]["text"]["sha256_full_text"], meta["files"]["text"]["sha256_full_text"])
                    self.assertEqual(got["published_at"], common.to_utc_z(meta["published_at"]))
                    self.assertEqual(got["source_url"], meta["params"]["url"])
                    self.assertFalse(got["truncated"]["is_truncated"])
                    self.assertTrue((landed / got["files"]["raw"]["name"]).exists())
                # 8-K + EX-99.1 through the index page
                for base, meta in h.fixture_by("8-K", "primary").items():
                    got = read_json(landed / f"{base}.meta.json")
                    self.assertEqual(got["index_page"], meta["index_page"])
                    self.assertEqual([a["file"] for a in got["attachments_listed"]], [a["file"] for a in meta["attachments_listed"]])
                    self.assertEqual(got["files"]["raw"]["sha256"], meta["files"]["raw"]["sha256"])
                    exhibit = read_json(landed / f"{base}.EX-99.1.meta.json")
                    self.assertEqual(exhibit["status"], "ok")
                    self.assertEqual(exhibit["exhibit_type"], "EX-99.1")
                    self.assertEqual(exhibit["params"]["kind"], "exhibit")
                    self.assertEqual(exhibit["files"]["raw"]["sha256"], h.docs[f"{base}.EX-99.1"]["files"]["raw"]["sha256"])
                    self.assertEqual(exhibit["published_at"], got["published_at"])

    def test_fetch_cache_miss_goes_online_and_truncation_is_recorded(self):
        for h in self.harnesses:
            with self.subTest(cik=h.cik):
                out = self.root / f"miss_{h.cik}"
                edgar.fetch_filings(h.cik, out, forms=("10-K",), ticker=h.ticker, submissions_dir=h.submissions_dir,
                                    tenk_cache_dir=h.tenk_miss, http_get=h.http_get, max_text_chars=1000)
                for base, meta in h.fixture_by("10-K", "primary").items():
                    self.assertIn(meta["params"]["url"], h.calls)
                    got = read_json(out / "edgar" / f"{base}.meta.json")
                    self.assertFalse(got["local_cache_check"]["hit"])
                    self.assertEqual(got["files"]["raw"]["sha256"], meta["files"]["raw"]["sha256"])
                    self.assertEqual(got["files"]["text"]["sha256_full_text"], meta["files"]["text"]["sha256_full_text"])
                    self.assertEqual(got["truncated"]["kept_chars"], 1000)
                    self.assertEqual(len((out / "edgar" / f"{base}.txt").read_text(encoding="utf-8")), 1000)

    def test_fetch_failure_writes_error_meta_only(self):
        def broken(url):
            raise urllib.error.URLError("down")

        for h in self.harnesses:
            with self.subTest(cik=h.cik):
                out = self.root / f"err_{h.cik}"
                results = edgar.fetch_filings(h.cik, out, forms=("10-Q", "8-K"), n_10q=1, n_8k=1, ticker=h.ticker,
                                              submissions_dir=h.submissions_dir, tenk_cache_dir=h.tenk_miss, http_get=broken)
                self.assertTrue(results)
                self.assertTrue(all(r["status"] == "error" for r in results), results)
                for r in results:
                    meta = read_json(out / "edgar" / f"{r['base']}.meta.json")
                    self.assertEqual(meta["status"], "error")
                    self.assertIn("URLError", meta["error"])
                    self.assertIsNone(meta["files"])
                    self.assertFalse((out / "edgar" / f"{r['base']}.txt").exists())

    def test_parse_index_attachments(self):
        html = ('<table><tr><th>Seq</th></tr><tr><td>1</td><td>FORM 8-K</td><td><a href="/ix?doc=/x/y/main.htm">main.htm</a></td>'
                '<td>8-K</td><td>10</td></tr><tr><td>2</td><td>EXHIBIT 99.1</td><td><a href="/x/y/ex.htm">ex.htm</a></td><td>EX-99.1</td><td>5</td></tr></table>')
        rows = edgar.parse_index_attachments(html)
        self.assertEqual([r["file"] for r in rows], ["main.htm", "ex.htm"])
        self.assertEqual(edgar.find_exhibit(rows)["file"], "ex.htm")
        self.assertIsNone(edgar.find_exhibit(rows[:1]))


def price_fixture_rows():
    path = next(iter(sorted(FIXTURES.glob("prices/*.csv"))), None)
    if path is None:
        return None, []
    with open(path, encoding="utf-8", newline="") as handle:
        return path, list(csv.DictReader(handle))


class PricesTests(unittest.TestCase):
    def setUp(self):
        self.path, rows = price_fixture_rows()
        if not rows:
            self.skipTest("no price fixture")
        self.meta = read_json(self.path.with_suffix(".meta.json"))
        self.local = [{**r, "source": "local"} for r in rows if r["source"] == "local"]
        self.vendor = [{**r, "adj_close": None, "source": "defeatbeta", "source_detail": prices.VENDOR_DETAIL} for r in rows]
        self.expected_vendor = sum(1 for r in rows if r["source"] == "defeatbeta")

    def test_merge_continuation_and_overlap(self):
        merged = prices.merge_daily(self.local, self.vendor, days=len(self.local))
        self.assertEqual(merged["local_rows"], len(self.local))
        self.assertEqual(merged["vendor_rows"], self.expected_vendor)
        self.assertEqual(merged["continuation_from"], self.meta["params"]["continuation_from"])
        self.assertEqual(merged["duplicate_dates"], 0)
        report = merged["overlap_check"]
        self.assertEqual(report["overlap_days"], len(self.local))
        self.assertEqual(report["days_close_rel_diff_over_0.5pct"], 0)
        self.assertLess(report["close_rel_diff_max"], 1e-9)
        self.assertEqual(report["local_dates_missing_in_defeatbeta"], [])
        self.assertEqual([r["source"] for r in merged["rows"]][-self.expected_vendor:], ["defeatbeta"] * self.expected_vendor)
        self.assertTrue(all(r["adj_close"] is None for r in merged["rows"] if r["source"] == "defeatbeta"))

    def test_overlap_disagreement_is_reported_not_merged(self):
        vendor = [dict(r) for r in self.vendor]
        target = vendor[len(self.local) // 2]
        target["close"] = str(float(target["close"]) * 1.02)
        merged = prices.merge_daily(self.local, vendor, days=len(self.local))
        report = merged["overlap_check"]
        self.assertEqual(report["days_close_rel_diff_over_0.5pct"], 1)
        self.assertEqual(report["examples_over_tol"][0]["date"], target["date"])
        local_row = next(r for r in merged["rows"] if r["date"] == target["date"])
        self.assertEqual(local_row["source"], "local")
        self.assertEqual(float(local_row["close"]), float(self.local[len(self.local) // 2]["close"]))

    def test_window_and_no_vendor(self):
        merged = prices.merge_daily(self.local, [], days=10)
        self.assertEqual(merged["local_rows"], 10)
        self.assertEqual(merged["vendor_rows"], 0)
        self.assertIsNone(merged["continuation_from"])
        self.assertIsNone(merged["overlap_check"]["close_rel_diff_max"])

    def land(self, out):
        local = {"rows": self.local, "shard": prices.shard_for(self.meta["params"]["cik"]), "manifest_rows": self.meta.get("local_manifest_rows", []),
                 "roles": {"primary": len(self.local)}, "tickers": {self.local[0]["ticker"]: len(self.local)}}
        return prices.fetch_daily(self.meta["params"]["cik"], self.meta["params"]["ticker"], out, days=len(self.local), local=local, vendor_rows=self.vendor)

    def test_fetch_daily_lands_csv_and_meta(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.land(Path(temp))
            self.assertEqual(result["status"], "ok")
            csv_path = Path(temp) / "prices" / "daily.csv"
            with open(csv_path, encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), len(self.local) + self.expected_vendor)
            self.assertEqual(list(rows[0]), list(prices.COLUMNS))
            meta = read_json(Path(temp) / "prices" / "daily.meta.json")
            self.assertEqual(meta["period"]["rows"], len(rows))
            self.assertEqual(meta["data_as_of"], rows[-1]["date"])
            self.assertIsNone(meta["published_at"])
            self.assertEqual(meta["overlap_check"]["overlap_days"], len(self.local))
            self.assertEqual(meta["file"]["sha256"], common.sha256_file(csv_path))


class BrokerTests(unittest.TestCase):
    def test_private_keys_and_tools_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            for tool, params, response in (
                ("mcp__futu__quote_stock_quote", {"acc_id": 1}, {"data": []}),
                ("mcp__futu__quote_stock_quote", {}, {"data": {"positions": []}}),
                ("mcp__futu__quote_stock_quote", {}, [{"cost_price": 1.0}]),
                ("mcp__futu__quote_stock_quote", {}, {"pl_ratio": 0.1}),
                ("mcp__futu__account_positions", {}, {"data": [1]}),
                ("mcp__plugin_longbridge_longbridge__stock_positions", {}, {"x": 1}),
                ("mcp__plugin_longbridge_longbridge__submit_order", {}, {"x": 1}),
                ("mcp__futu__sim_trade_cash_info", {}, {"x": 1}),
            ):
                with self.subTest(tool=tool, params=params, response=response), self.assertRaises(broker.PrivateDataError):
                    broker.land(temp, "futu", tool, "X", params, response)
            self.assertFalse(list(Path(temp).rglob("*.json")))
            for tool in ("mcp__futu__quote_order_book", "mcp__plugin_longbridge_longbridge__trading_days",
                         "mcp__plugin_longbridge_longbridge__trades", "mcp__plugin_longbridge_longbridge__cash_flow",
                         "mcp__plugin_longbridge_longbridge__fund_holder", "mcp__plugin_longbridge_longbridge__balance_sheet_x",
                         "mcp__plugin_longbridge_longbridge__short_positions", "mcp__futu__quote_insider_trade_list"):
                with self.subTest(tool=tool):
                    self.assertEqual(broker.land(temp, "longbridge", tool, "X", {"symbol": "X"}, {"data": {"cash_flow": 1}})["status"], "ok")
            with self.assertRaises(ValueError):
                broker.land(temp, "ibkr", "quote", "X", {}, {"a": 1})

    def test_status_and_meta_shape(self):
        with tempfile.TemporaryDirectory() as temp:
            for response, expected in (({"error_code": 2101400, "message": "internal server error", "recoverable": "none"}, "error"),
                                       ({"ret_code": -1, "ret_msg": "x"}, "error"),
                                       ({"data": []}, "empty"), (None, "empty"), ([], "empty"),
                                       ({"data": {"a": 1}}, "ok"), ([{"a": 1}], "ok"), ({"ret_code": 0, "data": [1]}, "ok")):
                with self.subTest(response=response):
                    result = broker.land(temp, "futu", "mcp__futu__quote_x", "US.X", {"code": "US.X"}, response, fetched_at="2026-01-01T00:00:00Z")
                    self.assertEqual(result["status"], expected)
                    outer = read_json(Path(temp) / "futu" / "quote_x.json")
                    self.assertEqual(list(outer), ["tool", "symbol", "fetched_at", "params", "response"])
                    self.assertEqual(outer["response"], response)
                    meta = read_json(Path(temp) / "futu" / "quote_x.meta.json")
                    self.assertEqual(meta["status"], expected)
                    self.assertEqual(meta["fetched_at"], "2026-01-01T00:00:00Z")
                    self.assertIsNone(meta["published_at"])
                    self.assertIn("現時快照", meta["published_at_basis"])
                    self.assertEqual(meta["error"] is not None, expected == "error")


class FakeStatement:
    def __init__(self, data, row_meta):
        self.data, self.row_meta = data, row_meta


class FakeTranscripts:
    def __init__(self, frame, listing, texts):
        self._frame, self._listing, self._texts = frame, listing, texts

    def get_transcripts_list(self):
        return self._frame(self._listing)

    def get_transcript(self, fiscal_year, fiscal_quarter):
        return self._frame(self._texts[(fiscal_year, fiscal_quarter)])


class FakeTicker:
    """DefeatBeta Ticker stand-in built from the fixture JSON files (records back into DataFrames)."""

    def __init__(self, fixture_dir: Path, pd):
        self._pd = pd
        self._payload = {p.name[:-5]: read_json(p) for p in fixture_dir.glob("*.json") if not p.name.endswith(".meta.json")}
        self._texts = {}
        for name, payload in self._payload.items():
            if name.startswith("earning_call_transcript."):
                self._texts[(payload["params"]["fiscal_year"], payload["params"]["fiscal_quarter"])] = payload

    def _frame(self, payload):
        return self._pd.DataFrame.from_records(payload.get("records") or [], columns=payload.get("columns") or None)

    def earning_call_transcripts(self):
        return FakeTranscripts(self._frame, self._payload["earning_call_transcripts.list"], self._texts)

    def info(self):
        return self._frame(self._payload["info"])

    def currency(self):
        raise RuntimeError("not available offline")

    def __getattr__(self, name):
        if name.startswith("_") or name not in self._payload:
            raise AttributeError(name)
        payload = self._payload[name]
        if name in defeatbeta.STATEMENTS:
            return lambda: FakeStatement(self._frame(payload), payload.get("row_meta"))
        return lambda: self._frame(payload)


class MetaShapeTests(unittest.TestCase):
    """Every adapter's meta carries at least the keys of the fixture meta of the same kind, plus only known extras."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_edgar(self):
        for path in submissions_fixtures():
            h = EdgarHarness(path, self.root / path.stem)
            out = self.root / f"out_{h.cik}"
            edgar.fetch_filings(h.cik, out, n_10k=1, n_10q=1, n_8k=2, ticker=h.ticker, submissions_dir=h.submissions_dir,
                                tenk_cache_dir=h.tenk_miss, http_get=h.http_get)
            produced = {p.name: p for p in (out / "edgar").glob("*.meta.json")}
            self.assertGreaterEqual(len(produced), 4)
            for name, meta_path in produced.items():
                with self.subTest(meta=name):
                    self.assertTrue((FIXTURES / "edgar" / name).exists(), f"no fixture meta named {name}")
                    assert_meta_shape(self, meta_path, FIXTURES / "edgar" / name)

    def test_defeatbeta(self):
        try:
            import pandas as pd  # noqa: PLC0415
        except ImportError:
            self.skipTest("pandas not installed")
        fixture_dir = FIXTURES / "defeatbeta"
        ticker = read_json(fixture_dir / "info.meta.json")["params"]["ticker"]
        statuses = defeatbeta.fetch_company(ticker, self.root, transcripts=1, ticker_factory=lambda _t: FakeTicker(fixture_dir, pd))
        self.assertNotIn("error", statuses.values(), statuses)
        produced = {p.name: p for p in (self.root / "defeatbeta").glob("*.meta.json")}
        self.assertEqual(set(produced), {p.name for p in fixture_dir.glob("*.meta.json")})
        for name, meta_path in produced.items():
            with self.subTest(meta=name):
                assert_meta_shape(self, meta_path, fixture_dir / name)
                fixture_meta = read_json(fixture_dir / name)
                got = read_json(meta_path)
                self.assertEqual(got["period"], fixture_meta["period"])
                self.assertEqual(got["published_at"], fixture_meta["published_at"])
        self.assertEqual({n for n, s in statuses.items() if s == "empty"},
                         {p.name[:-len(".meta.json")] for p in fixture_dir.glob("*.meta.json")
                          if any("empty DataFrame" in g for g in read_json(p)["known_gaps"])})
        listing = read_json(self.root / "defeatbeta" / "earning_call_transcripts.list.json")
        self.assertEqual(len(listing["records"]), read_json(fixture_dir / "earning_call_transcripts.list.meta.json")["period"]["count"])

    def test_prices(self):
        case = PricesTests("test_fetch_daily_lands_csv_and_meta")
        case.setUp()
        case.land(self.root)
        assert_meta_shape(self, self.root / "prices" / "daily.meta.json", case.path.with_suffix(".meta.json"))

    def test_broker(self):
        for source in ("futu", "longbridge"):
            for data_path in sorted((FIXTURES / source).glob("*.json")):
                if data_path.name.endswith(".meta.json"):
                    continue
                outer = read_json(data_path)
                response = outer["response"] if outer.get("response") is not None else outer.get("error")
                fixture_meta = read_json(data_path.with_suffix(".meta.json"))
                with self.subTest(source=source, tool=fixture_meta["tool"]):
                    result = broker.land(self.root, source, fixture_meta["tool"], outer.get("symbol"), fixture_meta["params"], response)
                    assert_meta_shape(self, Path(result["meta"]), data_path.with_suffix(".meta.json"))
                    self.assertEqual(result["status"], "error" if fixture_meta.get("status") == "FAILED" else "ok")


if __name__ == "__main__":
    unittest.main()
