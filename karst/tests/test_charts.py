"""Model-readable month / week / day / recent charts: the picture and the numbers.

The bars are generated here (no company, no vendor): what is under test is what the
chart actually plots — candles, volume, and moving averages computed over the whole
history before the window is cut — plus the derived numbers and the rule that no
price array is ever written. The series are parameterized shapes (trend, gap, long
wicks, false breakout, unfinished period), not one recorded stock.
"""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from statistics import fmean

from karst import charts, service
from karst.agents.protocol import get_research_protocol
from karst.agents.research import CHARTS_NOTE, export_task
from karst.packet import read_json
from karst.schema import ContractError
from karst.tests.test_publish_bars import candles, stage_prices
from karst.tests.v03_fixture import build_bundle

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
VIEWS = ("M", "W", "D", "DR")


def series(count, *, end=None, start=20.0, drift=0.0, swing=0.0, period=20, wick=0.4,
           gap_at=None, gap=0.0, open_last=False):
    """``count`` consecutive daily bars, oldest first, from plain shape parameters.

    ``drift`` is the per-bar trend, ``swing``/``period`` a triangular oscillation (so
    a moving average is never a flat line), ``wick`` the share of the body drawn as
    shadow, ``gap`` a one-bar jump at ``gap_at``, and ``open_last`` leaves the final
    bar unfinished.
    """
    end = end or date(2026, 9, 15)
    rows, price = [], start
    for offset in range(count):
        day = end - timedelta(days=count - 1 - offset)
        step = abs((offset % period) - period / 2) / (period / 2)  # 1 -> 0 -> 1
        price = start + drift * offset + swing * step
        if gap_at is not None and offset >= gap_at:
            price += gap
        body = max(abs(drift), 0.05)
        opening = price - body
        rows.append({"at": f"{day.isoformat()}T20:00:00Z", "open": opening, "close": price,
                     "high": max(opening, price) + wick, "low": min(opening, price) - wick,
                     "volume": 1000.0 + (offset % 7) * 120,
                     "complete": not (open_last and offset == count - 1)})
    return rows


def price_arrays_in(value):
    """Any list of OHLC candles hiding anywhere in a saved payload."""
    if isinstance(value, list):
        if any(isinstance(item, dict) and {"open", "high", "low", "close"} <= set(item)
               for item in value):
            return True
        return any(price_arrays_in(item) for item in value)
    if isinstance(value, dict):
        return any(price_arrays_in(item) for item in value.values())
    return False


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "charts"

    def test_four_views_are_drawn_and_only_derived_numbers_are_kept(self):
        bars = series(320, drift=0.05, swing=4.0, wick=1.2)
        result = charts.render(bars, self.out, title="DEMO.US")
        for view, name in zip(VIEWS, ("monthly", "weekly", "daily", "daily_recent")):
            path = self.out / result["derived"]["files"][view]
            with self.subTest(view=name):
                self.assertTrue(path.name.startswith(name + "-"))
                self.assertTrue(path.is_file())
                self.assertEqual(path.read_bytes()[:8], PNG_MAGIC)
                self.assertGreater(path.stat().st_size, 5000)
        derived = read_json(self.out / "derived.json")
        self.assertEqual(derived, result["derived"])
        self.assertFalse(price_arrays_in(derived), "the chart JSON must not carry the series")
        text = json.dumps(derived, ensure_ascii=False)
        for field in ('"open"', '"close":'):  # "high"/"low" survive as pivot kinds
            self.assertNotIn(field, text)
        self.assertNotIn(str(self.out), text, "no host path travels in the JSON")
        self.assertEqual(sorted(derived["views"]), sorted(VIEWS))
        # Named after its own content: a later render lands beside this file, not on it.
        self.assertRegex(derived["files"]["DR"], r"^daily_recent-[0-9a-f]{12}\.png$")
        self.assertTrue(derived["files"]["DR"].startswith("daily_recent-"))
        self.assertEqual(derived["views"]["D"]["bars_count"], 320)
        self.assertEqual(derived["views"]["DR"]["drawn_bars"], charts.RECENT_BARS)
        self.assertEqual(derived["data_as_of"], bars[-1]["at"])

    def test_the_drawn_average_is_a_curve_computed_over_the_whole_history(self):
        bars = series(420, drift=0.03, swing=6.0, period=40, wick=1.5)
        closes = [bar["close"] for bar in bars]
        drawn = charts.render(bars, self.out)["plotted"]
        for view in ("D", "DR"):
            line = drawn[view]["overlays"]["sma200"]
            with self.subTest(view=view):
                self.assertIsNotNone(line[-1])
                self.assertAlmostEqual(line[-1], fmean(closes[-200:]), places=9)
                self.assertAlmostEqual(line[-2], fmean(closes[-201:-1]), places=9)
                self.assertGreater(len(set(v for v in line if v is not None)), 10,
                                   "a moving average drawn as one level is not a curve")
        recent = drawn["DR"]["overlays"]["sma200"]
        self.assertEqual(len(recent), charts.RECENT_BARS)
        self.assertIsNotNone(recent[0], "the window is cut after the average is computed")
        self.assertEqual(recent, drawn["D"]["overlays"]["sma200"][-charts.RECENT_BARS:])
        self.assertEqual(drawn["DR"]["overlays"]["ema20"][-1],
                         charts.ema_series(charts.resample(bars, "D"), 20)[-1])

    def test_a_weekly_chart_maps_the_daily_average_instead_of_recomputing_it(self):
        bars = series(420, drift=0.03, swing=5.0, period=30)
        by_day = {bar["at"][:10]: index for index, bar in enumerate(bars)}
        rendered = charts.render(bars, self.out)
        weekly = charts.resample(bars, "W")
        line = rendered["plotted"]["W"]["overlays"]["sma200"]
        self.assertEqual(len(line), len(weekly))
        for offset in (-1, -5, -20):
            week = weekly[offset]
            upto = by_day[week["end"][:10]] + 1
            closes = [bar["close"] for bar in bars[:upto] if bar["complete"]]
            with self.subTest(week=week["at"]):
                self.assertAlmostEqual(line[offset], fmean(closes[-200:]), places=9)
        self.assertEqual(rendered["derived"]["views"]["W"]["overlays"], ["sma200"])
        self.assertIn("200-day SMA", charts.OVERLAYS["sma200"][0])
        self.assertLess(len(weekly), 200, "a 200-WEEK average could not exist on this series")

    def test_derived_reports_the_averages_direction_volume_ratio_and_atr(self):
        bars = series(300, drift=0.04, swing=1.0)
        daily = charts.render(bars, self.out)["derived"]["daily"]
        sma = daily["moving_averages"]["sma200"]
        self.assertAlmostEqual(sma["value"], fmean(bar["close"] for bar in bars[-200:]), places=9)
        self.assertEqual(sma["direction"]["bars"], charts.DIRECTION_BARS)
        self.assertEqual(sma["direction"]["label"], "rising")
        self.assertGreater(sma["direction"]["change"], 0)
        self.assertAlmostEqual(sma["distance_from_close"],
                               bars[-1]["close"] - sma["value"], places=9)
        volume = daily["volume"]
        self.assertEqual(volume["bars_compared"], charts.VOLUME_BASE)
        self.assertAlmostEqual(volume["average"],
                               fmean(bar["volume"] for bar in bars[-21:-1]), places=9)
        self.assertAlmostEqual(volume["ratio"], bars[-1]["volume"] / volume["average"], places=9)
        self.assertGreater(daily["atr"], 0)
        self.assertAlmostEqual(daily["atr"], charts.atr(charts.resample(bars, "D")), places=12)
        self.assertIn("Wilder", charts.render(bars, self.out)["derived"]["views"]["D"]["atr"]["method"])

    def test_an_unfinished_week_and_month_are_marked_and_do_not_move_the_average(self):
        # A Wednesday end: the week and the month are both still running.
        bars = series(320, end=date(2026, 9, 16), drift=0.02, swing=2.0, open_last=True)
        rendered = charts.render(bars, self.out)
        derived = rendered["derived"]
        for view in ("W", "M", "D", "DR"):
            with self.subTest(view=view):
                self.assertFalse(derived["views"][view]["last_bar_complete"])
        self.assertTrue(charts.resample(bars, "W")[-2]["complete"])
        closed = [bar["close"] for bar in bars if bar["complete"]]
        for view in ("D", "W", "M"):
            line = rendered["plotted"][view]["overlays"]["sma200"]
            with self.subTest(view=view):
                self.assertAlmostEqual(line[-1], fmean(closed[-200:]), places=9)
        self.assertEqual(derived["daily"]["moving_averages"]["sma200"]["at"],
                         bars[-2]["at"], "an open bar cannot be the average's last point")

    def test_average_direction_ignores_unfinished_session_points(self):
        for count in (219, 220, 300):
            for unfinished in (0, 1, 2):
                with self.subTest(complete_sessions=count, unfinished=unfinished):
                    bars = series(count + unfinished, drift=0.04, swing=1.0)
                    for bar in bars[count:]:
                        bar["complete"] = False
                    curves = {"sma200": charts.sma_series(bars, 200),
                              "sma50": charts.sma_series(bars, 50),
                              "ema20": charts.ema_series(bars, 20)}
                    averages = charts._averages(bars, curves)
                    closed_curves = {"sma200": charts.sma_series(bars[:count], 200),
                                     "sma50": charts.sma_series(bars[:count], 50),
                                     "ema20": charts.ema_series(bars[:count], 20)}
                    baseline = charts._averages(bars[:count], closed_curves)
                    for name in curves:
                        self.assertEqual(averages[name]["direction"],
                                         baseline[name]["direction"])
                    direction = averages["sma200"]["direction"]
                    if count < 220:
                        self.assertIsNone(direction,
                                          "unfinished bars cannot supply direction warmup")
                    else:
                        closes = [bar["close"] for bar in bars[:count]]
                        self.assertAlmostEqual(direction["value_now"], fmean(closes[-200:]))
                        self.assertAlmostEqual(direction["value_before"],
                                               fmean(closes[-220:-20]))

    def test_a_false_breakout_leaves_anchors_whose_confirmation_comes_later(self):
        # Up to a high, back down, one bar poking above it, then failure back inside.
        bars = series(60, swing=3.0, period=12, wick=0.3)
        peak = max(bar["high"] for bar in bars[:50])
        bars[52] = {**bars[52], "high": peak + 1.5, "close": peak - 0.5, "open": peak - 0.8,
                    "low": peak - 1.2}
        for index in (53, 54, 55, 56, 57, 58, 59):
            bars[index] = {**bars[index], "high": peak - 1.0, "close": peak - 2.0,
                           "open": peak - 1.5, "low": peak - 2.5}
        levels = charts.render(bars, self.out)["derived"]["views"]["D"]["levels"]
        failed = [anchor for zone in levels["zones"] for anchor in zone["anchors"]
                  if anchor["price"] > peak]
        self.assertTrue(failed, "the bar that poked above the range is an anchor of its own")
        for anchor in failed:
            self.assertGreater(anchor["confirmed_at"], anchor["formed_at"],
                               "a pivot is confirmed by later bars, never on its own day")
        formed = [anchor["formed_at"] for anchor in levels["zones"][0]["anchors"]]
        self.assertEqual(formed, sorted(formed), "anchors are kept in formation order")
        self.assertIsNotNone(levels["resistance"])
        self.assertLessEqual(levels["resistance"]["lower"], levels["resistance"]["upper"])
        self.assertGreater(levels["tolerance"], 0)

    def test_a_daily_pullback_inside_a_weekly_uptrend_reads_as_both(self):
        bars = series(320, drift=0.05, swing=0.5)
        for index in range(len(bars) - 12, len(bars)):  # the last two and a half weeks fall
            step = index - (len(bars) - 12) + 1
            bars[index] = {**bars[index], "close": bars[index]["close"] - step * 0.25,
                           "open": bars[index]["open"] - step * 0.2,
                           "low": bars[index]["low"] - step * 0.3,
                           "high": bars[index]["high"] - step * 0.15}
        derived = charts.render(bars, self.out)["derived"]
        averages = derived["daily"]["moving_averages"]
        self.assertEqual(averages["sma200"]["direction"]["label"], "rising")
        self.assertLess(derived["views"]["D"]["last_close"], averages["ema20"]["value"],
                        "price below the fast average is the pullback half of the reading")
        self.assertGreater(derived["views"]["D"]["last_close"], averages["sma200"]["value"])

    def test_weeks_and_months_aggregate_the_days_they_contain(self):
        bars = series(90)
        weekly = charts.resample(bars, "W")
        monthly = charts.resample(bars, "M")
        expected_weeks = {date.fromisoformat(bar["at"][:10]).strftime("%G-%V") for bar in bars}
        self.assertEqual(len(weekly), len(expected_weeks))
        self.assertEqual(len(monthly), len({bar["at"][:7] for bar in bars}))
        first = [bar for bar in bars if bar["at"][:7] == monthly[0]["at"][:7]]
        self.assertEqual(monthly[0]["open"], first[0]["open"])
        self.assertEqual(monthly[0]["close"], first[-1]["close"])
        self.assertEqual(monthly[0]["high"], max(bar["high"] for bar in first))
        self.assertEqual(monthly[0]["volume"], sum(bar["volume"] for bar in first))
        self.assertEqual(monthly[0]["end"], first[-1]["at"], "a period ends on its last day")
        self.assertFalse(weekly[-1]["complete"], "the period still running is not complete")
        self.assertTrue(weekly[0]["complete"])

    def test_the_moving_average_needs_its_window_before_it_is_drawn(self):
        short = charts.render(series(30), self.out)
        self.assertIsNone(short["derived"]["daily"]["moving_averages"]["sma200"]["value"])
        self.assertEqual([v for v in short["plotted"]["D"]["overlays"]["sma200"]
                          if v is not None], [])
        self.assertIsNone(short["derived"]["daily"]["moving_averages"]["sma200"]["direction"])
        long_run = charts.render(series(300, drift=0.02), self.out)["derived"]
        self.assertIsNotNone(long_run["daily"]["moving_averages"]["sma200"]["value"])

    def test_a_wide_range_gets_a_log_axis_and_a_narrow_one_stays_linear(self):
        wide = charts.render(series(300, start=5.0, drift=0.2), self.out)["derived"]
        self.assertEqual(wide["views"]["D"]["scale"], "log")
        self.assertEqual(charts.render(series(300, start=100.0, drift=0.01),
                                       self.out)["derived"]["views"]["D"]["scale"], "linear")
        self.assertEqual(charts.render(series(300, start=5.0, drift=0.2), self.out,
                                       scale="linear")["derived"]["views"]["D"]["scale"],
                         "linear")

    def test_every_artifact_carries_its_hash_source_and_parameters(self):
        source = {"evidence_id": "ev-prices-1", "sha256": "0" * 64, "source": "fixture"}
        result = charts.render(series(120, drift=0.02), self.out, source=source,
                               title="DEMO.US", as_of="2026-09-15T20:00:00Z")
        self.assertEqual(sorted(a["view"] for a in result["artifacts"]), sorted(VIEWS))
        for artifact in result["artifacts"]:
            data = Path(artifact["path"]).read_bytes()
            with self.subTest(view=artifact["view"]):
                self.assertEqual(artifact["artifact_id"], "cha-" + artifact["sha256"])
                self.assertEqual(len(data), artifact["bytes"])
                self.assertEqual(artifact["media_type"], "image/png")
                self.assertEqual(artifact["source_evidence_id"], "ev-prices-1")
                self.assertEqual(artifact["bars_as_of"], "2026-09-15T20:00:00Z")
                self.assertEqual(artifact["params_digest"],
                                 result["derived"]["params_digest"])
        # Same bars, same parameters, same picture: the id is the content.
        again = charts.render(series(120, drift=0.02), Path(self.temp.name) / "again",
                              source=source, title="DEMO.US", as_of="2026-09-15T20:00:00Z")
        self.assertEqual([a["artifact_id"] for a in again["artifacts"]],
                         [a["artifact_id"] for a in result["artifacts"]])

    def test_a_later_render_lands_beside_the_earlier_one_not_over_it(self):
        first = charts.render(series(120, drift=0.02), self.out)
        second = charts.render(series(121, drift=0.02), self.out)
        for view in VIEWS:
            with self.subTest(view=view):
                self.assertNotEqual(first["files"][view], second["files"][view])
                self.assertTrue(Path(first["files"][view]).is_file(),
                                "the chart an earlier run showed must still be there")
        kept = sorted(path.name for path in self.out.glob("derived-*.json"))
        self.assertEqual(len(kept), 2, "each render keeps its own derived numbers")
        self.assertEqual(read_json(self.out / "derived.json"), second["derived"])

    def test_nothing_to_chart_is_refused_rather_than_drawn_empty(self):
        with self.assertRaises(ContractError):
            charts.render([], self.out)


class ServiceChartTests(unittest.TestCase):
    def build(self, stage=None, security=None):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root, stage=stage,
                                                              security=security)

    def test_charts_come_from_the_registered_candlesticks(self):
        rows = candles(days=40)
        self.build(stage_prices(rows))
        result = service.render_charts(self.bundle, self.root / "charts")
        self.assertEqual(sorted(result["files"]), sorted(VIEWS))
        self.assertEqual(result["derived"]["views"]["D"]["bars_count"], len(rows))
        self.assertTrue(all(Path(path).is_file() for path in result["files"].values()))
        self.assertFalse(price_arrays_in(read_json(self.root / "charts" / "derived.json")))
        # The chart names the registered series it was drawn from.
        source = result["derived"]["source"]
        self.assertEqual(source["kind"], "prices")
        self.assertTrue(source["evidence_id"])
        self.assertTrue(all(a["source_evidence_id"] == source["evidence_id"]
                            for a in result["artifacts"]))

    def test_a_different_security_and_cutoff_need_no_code_change(self):
        other = {"security_id": "FIXTURE2:FIXTURE2", "issuer_id": "cik:0000000001",
                 "ticker": "OTHER", "name": "Second fixture issuer", "currency": "USD",
                 "exchange": "FIXTURE2"}
        rows = candles(days=30, start_price=88.0)
        cutoff = rows[-1]["timestamp"]
        # The snapshot was taken at the cutoff: prices fetched later are not read back
        # into an earlier cutoff (KARST-250), so a replay states when it acquired them.
        self.build(stage_prices(rows, fetched_at=cutoff), security=other)
        result = service.render_charts(self.bundle, self.root / "charts", as_of=cutoff)
        self.assertEqual(result["data_as_of"], cutoff)
        self.assertEqual(result["derived"]["views"]["D"]["bars_count"], len(rows))
        self.assertEqual(result["derived"]["views"]["D"]["last_close"],
                         float(rows[-1]["close"]))

    def test_without_registered_prices_the_service_says_so(self):
        self.build()
        with self.assertRaises(ContractError):
            service.render_charts(self.bundle, self.root / "charts")

    def test_a_task_directory_carries_the_charts_and_says_what_they_are_for(self):
        self.build(stage_prices(candles(days=40)))
        rendered = service.render_charts(self.bundle, self.root / "charts")
        task = self.root / "task"
        context = export_task(self.bundle, {"security": self.packet["security"]}, task,
                              get_research_protocol("research"), charts=rendered)
        for view in VIEWS:
            staged = task / context["charts"]["files"][view]
            with self.subTest(view=view):
                self.assertEqual(staged.read_bytes()[:8], PNG_MAGIC)
        self.assertFalse(price_arrays_in(read_json(task / "charts" / "derived.json")))
        staged = {artifact["artifact_id"]: artifact for artifact in context["charts"]["artifacts"]}
        self.assertEqual(len(staged), len(VIEWS))
        for artifact in staged.values():
            with self.subTest(view=artifact["view"]):
                self.assertFalse(Path(artifact["path"]).is_absolute())
                self.assertEqual((task / artifact["path"]).stat().st_size, artifact["bytes"])
        prompt = (task / "prompt.md").read_text(encoding="utf-8")
        self.assertIn(CHARTS_NOTE, prompt)
        self.assertIn("read_chart", context["charts"]["note"])
        self.assertFalse(price_arrays_in(read_json(task / "input.json")))


if __name__ == "__main__":
    unittest.main()
