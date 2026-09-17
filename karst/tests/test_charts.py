"""Model-readable day / week / month charts: pictures plus the numbers behind them.

The bars are generated here (no company, no vendor): what is under test is the
aggregation, the derived numbers and the rule that no price array is ever written.
"""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from karst import charts, service
from karst.agents.protocol import get_research_protocol
from karst.agents.research import CHARTS_NOTE, export_task
from karst.packet import read_json
from karst.schema import ContractError
from karst.tests.test_publish_bars import candles, stage_prices
from karst.tests.v03_fixture import build_bundle

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def daily_bars(count, end=None):
    """``count`` consecutive complete trading-day bars, oldest first."""
    end = end or date(2026, 9, 15)
    rows = []
    for offset in range(count):
        day = end - timedelta(days=count - 1 - offset)
        base = 10.0 + (offset % 20) * 0.5 + offset * 0.01
        rows.append({"at": f"{day.isoformat()}T20:00:00Z", "open": base, "close": base + 0.2,
                     "high": base + 0.6, "low": base - 0.4, "volume": 1000 + offset,
                     "complete": True})
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

    def test_three_views_are_drawn_and_only_derived_numbers_are_kept(self):
        bars = daily_bars(260)
        result = charts.render(bars, self.out)
        for name in ("daily", "weekly", "monthly"):
            path = self.out / f"{name}.png"
            with self.subTest(view=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.read_bytes()[:8], PNG_MAGIC)
                self.assertGreater(path.stat().st_size, 2000)
        derived = read_json(self.out / "derived.json")
        self.assertEqual(derived, result["derived"])
        self.assertFalse(price_arrays_in(derived), "the chart JSON must not carry the series")
        text = json.dumps(derived, ensure_ascii=False)
        for field in ('"open"', '"volume"'):  # "high"/"low" survive as pivot labels
            self.assertNotIn(field, text)
        self.assertEqual(derived["files"], {"D": "daily.png", "W": "weekly.png",
                                            "M": "monthly.png"})
        self.assertEqual(derived["views"]["D"]["bars_count"], 260)
        self.assertEqual(derived["data_as_of"], bars[-1]["at"])

    def test_weeks_and_months_aggregate_the_days_they_contain(self):
        bars = daily_bars(90)
        weekly = charts.resample(bars, "W")
        monthly = charts.resample(bars, "M")
        expected_weeks = {date.fromisoformat(bar["at"][:10]).strftime("%G-%V") for bar in bars}
        expected_months = {bar["at"][:7] for bar in bars}
        self.assertEqual(len(weekly), len(expected_weeks))
        self.assertEqual(len(monthly), len(expected_months))
        first = [bar for bar in bars if bar["at"][:7] == monthly[0]["at"][:7]]
        self.assertEqual(monthly[0]["open"], first[0]["open"])
        self.assertEqual(monthly[0]["close"], first[-1]["close"])
        self.assertEqual(monthly[0]["high"], max(bar["high"] for bar in first))
        self.assertEqual(monthly[0]["volume"], sum(bar["volume"] for bar in first))
        self.assertFalse(weekly[-1]["complete"], "the period still running is not complete")
        self.assertTrue(weekly[0]["complete"])

    def test_the_moving_average_needs_its_window_and_levels_come_from_pivots(self):
        short = charts.render(daily_bars(30), self.out)["derived"]
        self.assertIsNone(short["views"]["D"]["sma200"])
        self.assertIsNone(short["views"]["W"]["sma200"], "a 200-day line is a daily measurement")
        long_run = charts.render(daily_bars(300), self.out)["derived"]
        self.assertIsNotNone(long_run["views"]["D"]["sma200"])
        levels = long_run["views"]["D"]["levels"]
        self.assertGreater(levels["pivots"], 0)
        for side in ("support", "resistance"):
            if levels[side]:
                self.assertIn("confirmed_at", levels[side])

    def test_nothing_to_chart_is_refused_rather_than_drawn_empty(self):
        with self.assertRaises(ContractError):
            charts.render([], self.out)


class ServiceChartTests(unittest.TestCase):
    def build(self, stage=None):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root, stage=stage)

    def test_charts_come_from_the_registered_candlesticks(self):
        rows = candles(days=40)
        self.build(stage_prices(rows))
        result = service.render_charts(self.bundle, self.root / "charts")
        self.assertEqual(sorted(result["files"]), ["D", "M", "W"])
        self.assertEqual(result["derived"]["views"]["D"]["bars_count"], len(rows))
        self.assertTrue(all(Path(path).is_file() for path in result["files"].values()))
        self.assertFalse(price_arrays_in(read_json(self.root / "charts" / "derived.json")))

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
        for view in ("D", "W", "M"):
            staged = task / context["charts"]["files"][view]
            with self.subTest(view=view):
                self.assertEqual(staged.read_bytes()[:8], PNG_MAGIC)
        self.assertIn("derived.json", (task / "charts" / "derived.json").name)
        self.assertFalse(price_arrays_in(read_json(task / "charts" / "derived.json")))
        prompt = (task / "prompt.md").read_text(encoding="utf-8")
        self.assertIn(CHARTS_NOTE, prompt)
        self.assertIn("derived.json", context["charts"]["note"])
        self.assertFalse(price_arrays_in(read_json(task / "input.json")))


if __name__ == "__main__":
    unittest.main()
