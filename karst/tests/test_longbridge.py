"""Longbridge quote adapter, offline: every client is a fake, no SDK or network is touched."""
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from karst.fetch import common, longbridge
from karst.fetch.broker import PrivateDataError

SYMBOL = "DEMO.US"  # parameterized test identity


class FakeQuote:
    """Stands in for an SDK object: attributes only, Decimal prices, no to_dict()."""

    def __init__(self, symbol, last_done):
        self.symbol = symbol
        self.last_done = Decimal(last_done)
        self.volume = 1234

    def method(self):  # callables must not be serialized
        raise AssertionError("adapter called an SDK method while serializing")


class FakeClient:
    def __init__(self, last_done="12.34", candles=1, fail=None):
        self.last_done, self.candles, self.fail = last_done, candles, fail
        self.calls = []

    def _check(self, name):
        self.calls.append(name)
        if self.fail == name:
            raise RuntimeError("upstream refused")

    def quote(self, symbols):
        self._check("quote")
        return [FakeQuote(symbol, self.last_done) for symbol in symbols]

    def static_info(self, symbols):
        self._check("static_info")
        return [{"symbol": symbol, "currency": "USD", "exchange": "NASDAQ"} for symbol in symbols]

    def calc_indexes(self, symbols, indexes):
        self._check("calc_indexes")
        return [{"symbol": symbol, **{name: 1 for name in indexes}} for symbol in symbols]

    def history_candlesticks_by_date(self, symbol, period, adjust, start, end):
        self._check("history_candlesticks_by_date")
        return [{"symbol": symbol, "period": period, "adjust": adjust,
                 "close": Decimal(self.last_done), "timestamp": f"{start}T20:00:00Z"}
                for _ in range(self.candles)]


def read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class PlainTimestampTests(unittest.TestCase):
    """The SDK returns naive datetimes in host-local time; the landed string must carry
    that zone, or the bar reader (which refuses zoneless bars) drops every candle."""

    def test_naive_datetime_lands_with_host_offset(self):
        import datetime as dt
        from karst import bars
        naive = dt.datetime(2026, 9, 10, 12, 0)
        text = longbridge._plain({"timestamp": naive})["timestamp"]
        self.assertEqual(dt.datetime.fromisoformat(text), naive.astimezone())
        row = {"timestamp": text, "open": "1", "high": "2", "low": "0.5", "close": "1.5"}
        cutoff = dt.datetime(2026, 9, 17, tzinfo=dt.timezone.utc)
        self.assertIsNotNone(bars._bar(row, cutoff))

    def test_aware_datetime_is_kept(self):
        import datetime as dt
        aware = dt.datetime(2026, 9, 10, 4, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(longbridge._plain(aware), aware.isoformat())


class EnvFileTests(unittest.TestCase):
    """Credentials live in a gitignored .env, not in the machine environment."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / ".env"
        self.addCleanup(self.directory.cleanup)

    def test_loads_pairs_and_ignores_blanks_and_comments(self):
        self.path.write_text(
            "# a comment\n\n"
            "LONGPORT_APP_KEY=plain\n"
            "  LONGPORT_APP_SECRET = 'quoted secret' \n"
            'LONGPORT_ACCESS_TOKEN="double"\n'
            "not-a-pair\n", encoding="utf-8")
        environ = {}
        loaded = common.load_env_file(self.path, environ)
        self.assertEqual(sorted(loaded), sorted(longbridge.ENV_KEYS))
        self.assertEqual(environ["LONGPORT_APP_KEY"], "plain")
        self.assertEqual(environ["LONGPORT_APP_SECRET"], "quoted secret")
        self.assertEqual(environ["LONGPORT_ACCESS_TOKEN"], "double")
        self.assertEqual(longbridge.credentials(environ), environ)

    def test_existing_environment_wins(self):
        self.path.write_text("LONGPORT_APP_KEY=from-file\n", encoding="utf-8")
        environ = {"LONGPORT_APP_KEY": "already-set"}
        self.assertEqual(common.load_env_file(self.path, environ), [])
        self.assertEqual(environ["LONGPORT_APP_KEY"], "already-set")

    def test_missing_file_is_not_an_error(self):
        environ = {}
        self.assertEqual(common.load_env_file(self.path / "nope" / ".env", environ), [])
        self.assertEqual(environ, {})


class CredentialTests(unittest.TestCase):
    def test_all_three_required(self):
        full = dict.fromkeys(longbridge.ENV_KEYS, "x")
        self.assertEqual(longbridge.credentials(full), full)
        for missing in longbridge.ENV_KEYS:
            with self.subTest(missing=missing):
                self.assertIsNone(longbridge.credentials({**full, missing: "  "}))
                self.assertIsNone(longbridge.credentials({k: v for k, v in full.items()
                                                          if k != missing}))


class LandingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.out = Path(self.directory.name)
        self.addCleanup(self.directory.cleanup)

    def test_missing_credentials_records_error_without_raising(self):
        statuses = longbridge.fetch_company(SYMBOL, self.out, start="2026-01-01",
                                            end="2026-02-01", factory=lambda: None)
        self.assertEqual(set(statuses.values()), {"error"})
        self.assertEqual(len(statuses), 4)
        for path in sorted((self.out / "longbridge").glob("*.meta.json")):
            meta = read(path)
            self.assertEqual(meta["status"], "error")
            self.assertEqual(meta["status_reason"], longbridge.MISSING_CREDENTIALS)
            self.assertIsNone(meta["published_at"])
        self.assertEqual(list((self.out / "longbridge").glob("*[!a-z].json")), [])
        # No invented body: only sidecars were written.
        self.assertTrue(all(p.name.endswith(".meta.json")
                            for p in (self.out / "longbridge").iterdir()))

    def test_fake_client_lands_envelope_and_meta(self):
        client = FakeClient()
        statuses = longbridge.fetch_company(SYMBOL, self.out, start="2026-01-01",
                                            end="2026-02-01", client=client)
        self.assertEqual(set(statuses.values()), {"ok"})
        self.assertEqual(sorted(client.calls),
                         ["calc_indexes", "history_candlesticks_by_date", "quote", "static_info"])
        envelope = read(self.out / "longbridge" / "quote.json")
        self.assertEqual(envelope["tool"], "quote")
        self.assertEqual(envelope["params"], {"symbols": [SYMBOL]})
        self.assertEqual(envelope["response"][0]["last_done"], "12.34")  # Decimal kept exact
        self.assertNotIn("method", envelope["response"][0])
        meta = read(self.out / "longbridge" / "quote.meta.json")
        self.assertEqual(meta["source"], "longbridge")
        self.assertEqual(meta["status"], "ok")
        self.assertIsNone(meta["published_at"])
        self.assertTrue(meta["fetched_at"].endswith("Z"))
        candles = read(self.out / "longbridge" / "history_candlesticks_by_date.meta.json")
        self.assertEqual(candles["period"], {"start": "2026-01-01", "end": "2026-02-01"})

    def test_empty_return_is_not_an_error(self):
        result = longbridge.history_candlesticks(self.out, SYMBOL, "2026-01-01", "2026-02-01",
                                                 client=FakeClient(candles=0))
        self.assertEqual(result["status"], "empty")
        gaps = read(result["meta"])["known_gaps"]
        self.assertTrue(any("not covered" in gap for gap in gaps))

    def test_sdk_failure_is_recorded_not_invented(self):
        result = longbridge.quote(self.out, [SYMBOL], client=FakeClient(fail="quote"))
        self.assertEqual(result["status"], "error")
        self.assertIn("upstream refused", result["status_reason"])
        self.assertIsNone(result["path"])

    def test_account_shaped_landing_is_refused(self):
        with self.assertRaises(PrivateDataError):
            longbridge.land(self.out, "quote", SYMBOL, {"symbol": SYMBOL},
                            [{"symbol": SYMBOL, "positions": [{"qty": 1}]}])
        with self.assertRaises(PrivateDataError):
            longbridge.land(self.out, "stock_positions", SYMBOL, {}, [])


class RegistryTests(unittest.TestCase):
    def test_landed_output_registers_as_public_evidence(self):
        from karst.fetch.registry import EvidenceRegistry  # local: keeps the adapter test standalone

        with tempfile.TemporaryDirectory() as staging, tempfile.TemporaryDirectory() as bundle:
            longbridge.fetch_company(SYMBOL, staging, start="2026-01-01", end="2026-02-01",
                                     client=FakeClient())
            registry = EvidenceRegistry(bundle)
            kinds = set()
            for meta in sorted((Path(staging) / "longbridge").glob("*.meta.json")):
                raw = meta.with_name(meta.name.replace(".meta.json", ".json"))
                record = registry.register(raw, meta, entity_ids=["XNAS:DEMO"])
                kinds.add(record["kind"])
            self.assertEqual(kinds, {"prices", "profile"})


if __name__ == "__main__":
    unittest.main()
