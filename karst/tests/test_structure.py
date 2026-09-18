"""Confirmed structure: what was knowable when, and what a later bar may add to it.

Every series here is built from turning points in this file — no ticker, no vendor,
no recorded history. What is under test is the arithmetic of structure (which pivot
is a higher high, which close broke a level, which wick only borrowed it) and the one
property everything else rests on: replaying the same series bar by bar reproduces
the same confirmed events, never a better-informed version of them.
"""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from karst import charts, structure
from karst.packet import read_json

IDENTITY = ("anchor_time", "confirmed_at", "level", "direction", "kind", "event_id")


def path(turns, *, leg=4, wick=0.6, start=date(2026, 1, 5), volume=1000.0,
         incomplete_last=False):
    """Daily bars walking straight between ``turns``; each turn becomes a pivot.

    A turning bar gets the long shadow on the side it turned, so its extreme is
    strictly beyond its neighbours' — which is what the confirmed-pivot rule asks
    for. Everything between two turns is a plain step.
    """
    prices, turning = [turns[0]], [False]
    for target in turns[1:]:
        base = prices[-1]
        for step in range(1, leg + 1):
            prices.append(base + (target - base) * step / leg)
            turning.append(step == leg)
    bars, previous = [], prices[0]
    for index, (close, turn) in enumerate(zip(prices, turning)):
        rising = close >= previous
        top, bottom = max(previous, close), min(previous, close)
        day = start + timedelta(days=index)
        bars.append({"at": f"{day.isoformat()}T20:00:00Z", "open": previous, "close": close,
                     "high": top + (wick if turn and rising else wick / 3),
                     "low": bottom - (wick if turn and not rising else wick / 3),
                     "volume": volume + (index % 5) * 50,
                     "complete": not (incomplete_last and index == len(prices) - 1)})
        previous = close
    return bars


def kinds(result, kind):
    return [event for event in result["events"] + result["swings"] if event["kind"] == kind]


def labels(result):
    return [event["label"] for event in result["swings"]]


class SwingTests(unittest.TestCase):
    def test_an_uptrend_reads_as_higher_highs_higher_lows_and_breaks_in_its_direction(self):
        result = structure.events(path([10, 20, 16, 26, 22, 32, 28, 38]))
        self.assertEqual(result["state"]["trend"], "up")
        highs = [event["label"] for event in result["swings"] if event["direction"] == "up"]
        lows = [event["label"] for event in result["swings"] if event["direction"] == "down"]
        self.assertEqual(highs[1:], ["HH"] * (len(highs) - 1))
        self.assertEqual(lows[1:], ["HL"] * (len(lows) - 1))
        self.assertIsNone(highs[0], "the first swing has nothing to be higher than")
        breaks = kinds(result, "bos")
        self.assertTrue(breaks)
        self.assertTrue(all(event["direction"] == "up" for event in breaks))
        self.assertEqual(kinds(result, "choch"), [], "a trend that never turned has no CHoCH")
        for event in result["swings"]:
            self.assertGreater(event["confirmed_at"], event["anchor_time"],
                               "a swing is confirmed by later bars, never on its own day")

    def test_a_downtrend_reads_as_lower_highs_lower_lows(self):
        result = structure.events(path([40, 30, 34, 24, 28, 18, 22, 12]))
        self.assertEqual(result["state"]["trend"], "down")
        self.assertEqual([event["label"] for event in result["swings"]
                          if event["direction"] == "up"][1:], ["LH", "LH"])
        self.assertEqual([event["label"] for event in result["swings"]
                          if event["direction"] == "down"][1:], ["LL", "LL"])
        self.assertTrue(all(event["direction"] == "down" for event in kinds(result, "bos")))
        self.assertEqual(kinds(result, "choch"), [])

    def test_the_first_break_is_a_bos_and_only_a_turn_against_a_trend_is_a_choch(self):
        # Up first (so a trend exists), then a break of the swing low underneath it.
        result = structure.events(path([10, 20, 16, 26, 22, 30, 18, 14]))
        first = next(event for event in result["events"]
                     if event["kind"] in ("bos", "choch"))
        self.assertEqual(first["kind"], "bos")
        self.assertEqual(first["trend_before"], "undetermined")
        turn = kinds(result, "choch")
        self.assertEqual(len(turn), 1)
        self.assertEqual(turn[0]["direction"], "down")
        self.assertEqual(turn[0]["trend_before"], "up")
        self.assertEqual(turn[0]["trend_after"], "down")
        self.assertEqual(result["state"]["trend"], "down")
        self.assertEqual(result["state"]["trend_since"], turn[0]["confirmed_at"])
        broken = next(event for event in result["swings"]
                      if event["event_id"] == turn[0]["refs"][0])
        self.assertEqual(broken["level"], turn[0]["level"])
        self.assertEqual(broken["status"], "invalidated")

    def test_a_range_makes_equal_levels_and_never_a_change_of_character(self):
        result = structure.events(path([100, 104, 100, 104, 100, 104, 100, 104, 100]))
        self.assertEqual(result["state"]["trend"], "undetermined")
        self.assertEqual(kinds(result, "choch"), [], "a box has no trend to change")
        self.assertEqual(kinds(result, "bos"), [], "an equal high is not a break of it")
        equal = kinds(result, "equal_levels")
        self.assertTrue(equal)
        self.assertEqual({event["direction"] for event in equal}, {"up", "down"})
        for event in equal:
            self.assertLessEqual(event["zone"]["upper"] - event["zone"]["lower"],
                                 event["tolerance"])
            self.assertEqual(len(event["refs"]), 2, "equal levels name both swings")
        # A high that only matches the last one is not a higher high: what says the two
        # are the same level is the equal_levels event, not the label.
        self.assertEqual(set(labels(result)[2:]), {"LH", "LL"})

    def test_a_wider_tolerance_is_what_makes_two_levels_equal(self):
        bars = path([100, 104, 100, 105.6, 100.4])
        strict = structure.events(bars, atr_multiple=0.01)
        loose = structure.events(bars, atr_multiple=3.0)
        self.assertEqual(kinds(strict, "equal_levels"), [])
        self.assertTrue(kinds(loose, "equal_levels"))


class SweepTests(unittest.TestCase):
    def build(self, poke_high, poke_close):
        """An established uptrend, then one bar reaching over the last swing high."""
        bars = path([10, 20, 16, 26, 22, 30, 26])
        level = structure.events(bars)["state"]["swing_high"]["price"]
        last = bars[-1]
        bars.append({"at": "2026-03-01T20:00:00Z", "open": last["close"],
                     "high": level + poke_high, "low": last["close"] - 1.0,
                     "close": level + poke_close, "volume": 2000.0, "complete": True})
        return bars, level

    def test_a_wick_over_the_high_that_closes_back_is_a_sweep_not_a_break(self):
        bars, level = self.build(poke_high=1.5, poke_close=-0.5)
        result = structure.events(bars)
        sweeps = [event for event in kinds(result, "sweep")
                  if event["confirmed_at"] == bars[-1]["at"]]
        self.assertEqual(len(sweeps), 1)
        self.assertEqual(sweeps[0]["direction"], "up")
        self.assertEqual(sweeps[0]["level"], level)
        self.assertEqual(sweeps[0]["basis"], "same_bar")
        self.assertEqual(sweeps[0]["reached"], bars[-1]["high"])
        self.assertEqual([event for event in result["events"]
                          if event["kind"] in ("bos", "choch")
                          and event["confirmed_at"] == bars[-1]["at"]], [])
        self.assertEqual(result["state"]["swing_high"]["price"], level,
                         "a swept level is still the level")
        self.assertEqual(result["state"]["swing_high"]["status"], "touched")

    def test_a_close_over_the_same_high_is_a_break_not_a_sweep(self):
        bars, level = self.build(poke_high=1.5, poke_close=0.5)
        result = structure.events(bars)
        last = [event for event in result["events"] if event["confirmed_at"] == bars[-1]["at"]]
        self.assertEqual([event["kind"] for event in last], ["bos"])
        self.assertEqual(last[0]["level"], level)
        self.assertIsNone(result["state"]["swing_high"], "a broken level is no longer armed")
        self.assertEqual(result["state"]["prior_high"]["price"], level)
        self.assertEqual(result["state"]["prior_high"]["broken_at"], bars[-1]["at"])
        self.assertIsNone(result["state"]["prior_high"]["retested_at"])

    def test_a_break_given_back_inside_the_window_becomes_a_sweep_across_bars(self):
        bars, level = self.build(poke_high=1.5, poke_close=0.5)
        for offset, close in enumerate((level - 1.0, level - 2.0), start=1):
            day = date(2026, 3, 1) + timedelta(days=offset)
            bars.append({"at": f"{day.isoformat()}T20:00:00Z", "open": level, "close": close,
                         "high": level + 0.2, "low": close - 0.3, "volume": 1500.0,
                         "complete": True})
        wide = structure.events(bars, reclaim_window=5)
        broke = next(event for event in wide["events"] if event["kind"] == "bos"
                     and event["confirmed_at"] == "2026-03-01T20:00:00Z")
        self.assertEqual(broke["status"], "invalidated")
        self.assertEqual(broke["status_at"], "2026-03-02T20:00:00Z")
        reclaim = [event for event in kinds(wide, "sweep")
                   if event["refs"] == [broke["event_id"]]]
        self.assertEqual(len(reclaim), 1)
        self.assertEqual(reclaim[0]["basis"], "cross_bar_reclaim")
        self.assertEqual(reclaim[0]["level"], level)
        self.assertEqual(reclaim[0]["confirmed_at"], "2026-03-02T20:00:00Z")
        # The same break, watched for no bars at all, is never given back.
        narrow = structure.events(bars, reclaim_window=0)
        self.assertEqual(next(event for event in narrow["events"] if event["kind"] == "bos"
                              and event["confirmed_at"] == "2026-03-01T20:00:00Z")["status"],
                         "confirmed")
        self.assertEqual([event for event in kinds(narrow, "sweep")
                          if event.get("basis") == "cross_bar_reclaim"], [])

    def test_a_gap_straight_through_a_level_is_a_break_and_leaves_no_sweep(self):
        bars = path([10, 20, 16, 26, 22, 30, 26])
        level = structure.events(bars)["state"]["swing_high"]["price"]
        bars.append({"at": "2026-03-01T20:00:00Z", "open": level + 4.0, "high": level + 6.0,
                     "low": level + 3.5, "close": level + 5.0, "volume": 9000.0,
                     "complete": True})
        result = structure.events(bars)
        last = [event for event in result["events"] if event["confirmed_at"] == bars[-1]["at"]]
        self.assertEqual([event["kind"] for event in last], ["bos"])
        self.assertEqual(last[0]["level"], level, "the level broken is the one that existed")
        self.assertLess(last[0]["level"], bars[-1]["low"], "price never traded back to it")

    def test_a_broken_level_that_price_returns_to_is_marked_retested(self):
        bars, level = self.build(poke_high=1.5, poke_close=0.5)
        for offset, close in enumerate((level + 2.0, level + 0.2), start=1):
            day = date(2026, 3, 1) + timedelta(days=offset)
            bars.append({"at": f"{day.isoformat()}T20:00:00Z", "open": level + 1.0,
                         "close": close, "high": close + 0.3, "low": level - 0.1,
                         "volume": 1200.0, "complete": True})
        prior = structure.events(bars)["state"]["prior_high"]
        self.assertEqual(prior["price"], level)
        self.assertEqual(prior["retested_at"], "2026-03-02T20:00:00Z")


class ProvisionalTests(unittest.TestCase):
    def test_a_break_on_an_unfinished_bar_is_a_candidate_and_changes_nothing(self):
        bars = path([10, 20, 16, 26, 22, 30, 26])
        level = structure.events(bars)["state"]["swing_high"]["price"]
        bars.append({"at": "2026-03-01T20:00:00Z", "open": level - 1.0, "high": level + 2.0,
                     "low": level - 1.5, "close": level + 1.0, "volume": 800.0,
                     "complete": False})
        result = structure.events(bars)
        candidate = next(event for event in result["events"]
                         if event["confirmed_at"] == bars[-1]["at"])
        self.assertEqual(candidate["status"], "provisional")
        self.assertEqual(candidate["kind"], "bos")
        self.assertFalse(result["state"]["last_bar_complete"])
        self.assertEqual(result["state"]["swing_high"]["price"], level,
                         "an unfinished bar has not taken the level")
        before = structure.events(bars[:-1])["state"]
        self.assertEqual(result["state"]["trend"], before["trend"])
        self.assertEqual(result["state"]["prior_high"], before["prior_high"],
                         "nothing about structure moved on an unfinished bar")

    def test_the_same_bar_once_closed_confirms_it(self):
        bars = path([10, 20, 16, 26, 22, 30, 26])
        level = structure.events(bars)["state"]["swing_high"]["price"]
        bars.append({"at": "2026-03-01T20:00:00Z", "open": level - 1.0, "high": level + 2.0,
                     "low": level - 1.5, "close": level + 1.0, "volume": 800.0,
                     "complete": False})
        provisional = structure.events(bars)["events"][-1]
        bars[-1] = {**bars[-1], "complete": True}
        confirmed = structure.events(bars)["events"][-1]
        self.assertEqual(provisional["event_id"], confirmed["event_id"])
        self.assertEqual({key: provisional[key] for key in IDENTITY},
                         {key: confirmed[key] for key in IDENTITY})
        self.assertEqual((provisional["status"], confirmed["status"]),
                         ("provisional", "confirmed"))


class ReplayTests(unittest.TestCase):
    """The property everything else rests on: history is not rewritten by the future."""

    SERIES = {
        "uptrend": path([10, 20, 16, 26, 22, 32, 28, 38, 33]),
        "downtrend": path([40, 30, 34, 24, 28, 18, 22, 12]),
        "range": path([100, 104, 100, 104, 100, 104, 100, 104, 100]),
        "reversal": path([10, 20, 16, 26, 22, 30, 18, 14, 16, 10]),
        "gap": path([10, 20, 16, 26]) + [
            {"at": "2026-02-14T20:00:00Z", "open": 34.0, "high": 35.0, "low": 33.5,
             "close": 34.5, "volume": 5000.0, "complete": True},
            {"at": "2026-02-15T20:00:00Z", "open": 34.5, "high": 35.2, "low": 30.0,
             "close": 30.5, "volume": 4000.0, "complete": True},
            {"at": "2026-02-16T20:00:00Z", "open": 30.5, "high": 31.0, "low": 24.0,
             "close": 24.5, "volume": 4000.0, "complete": True}],
    }

    def test_every_prefix_keeps_what_the_shorter_one_had_already_confirmed(self):
        for name, bars in self.SERIES.items():
            history, seen = {}, 0
            for length in range(1, len(bars) + 1):
                result = structure.events(bars[:length])
                current = {event["event_id"]: event
                           for event in result["swings"] + result["events"]}
                for event_id, event in history.items():
                    with self.subTest(series=name, at=length, event=event_id):
                        self.assertIn(event_id, current,
                                      "a confirmed event cannot disappear from a later run")
                        later = current[event_id]
                        self.assertEqual({key: event[key] for key in IDENTITY},
                                         {key: later[key] for key in IDENTITY})
                        self.assertGreaterEqual(structure.STATUSES.index(later["status"]),
                                                structure.STATUSES.index(event["status"]),
                                                "status may only move forward")
                        self.assertLessEqual(later["confirmed_at"], bars[:length][-1]["at"])
                        self.assertLessEqual(later["status_at"], bars[:length][-1]["at"])
                history = {event_id: dict(event) for event_id, event in current.items()
                           if event["status"] != "provisional"}
                seen = max(seen, len(current))
            with self.subTest(series=name):
                self.assertGreater(seen, 2, "a series that produces nothing proves nothing")

    def test_a_status_really_does_advance_later_rather_than_standing_still(self):
        bars = self.SERIES["reversal"]
        broken = None
        for length in range(1, len(bars) + 1):
            result = structure.events(bars[:length])
            for event in result["swings"]:
                if event["status"] == "invalidated":
                    broken = event
        self.assertIsNotNone(broken, "this series does break a swing level")
        earlier = next(event for event in structure.events(
            bars[:next(index for index, bar in enumerate(bars)
                       if bar["at"] == broken["confirmed_at"]) + 1])["swings"]
            if event["event_id"] == broken["event_id"])
        self.assertEqual(earlier["status"], "confirmed")
        self.assertGreater(broken["status_at"], earlier["status_at"])

    def test_the_weekly_view_does_not_repaint_when_the_week_is_still_running(self):
        """The cross-timeframe trap: a higher period read mid-period must not decide
        anything it would have to take back when the period actually closes."""
        bars = path([20, 34, 25, 44, 33, 54, 43, 64, 52, 72], leg=12, wick=1.2)
        history = {}
        for length in range(1, len(bars) + 1):
            result = charts.structure(bars[:length], "W")
            current = {event["event_id"]: event
                       for event in result["swings"] + result["events"]}
            for event_id, event in history.items():
                with self.subTest(at=length, event=event_id):
                    self.assertIn(event_id, current)
                    self.assertEqual({key: event[key] for key in IDENTITY},
                                     {key: current[event_id][key] for key in IDENTITY})
            history = {event_id: dict(event) for event_id, event in current.items()
                       if event["status"] != "provisional"}
        self.assertGreater(len(history), 2)

    def test_the_final_run_and_the_replay_agree_on_the_whole_history(self):
        for name, bars in self.SERIES.items():
            replayed = {}
            for length in range(1, len(bars) + 1):
                result = structure.events(bars[:length])
                replayed.update({event["event_id"]: event
                                 for event in result["swings"] + result["events"]
                                 if event["status"] != "provisional"})
            final = structure.events(bars)
            with self.subTest(series=name):
                self.assertEqual(sorted(replayed),
                                 sorted(event["event_id"] for event
                                        in final["swings"] + final["events"]))


class VolatilityTests(unittest.TestCase):
    def test_the_running_atr_ends_where_the_single_value_does(self):
        bars = path([10, 20, 16, 26, 22, 32, 28, 38])
        self.assertEqual(structure.atr_series(bars)[-1], charts.atr(bars))
        self.assertIsNone(structure.atr_series(bars[:8])[-1], "too few ranges to average")
        self.assertIsNone(charts.atr(bars[:8]))
        self.assertIsNone(charts.atr([]))

    def test_an_unfinished_bar_does_not_move_the_running_value(self):
        bars = path([10, 20, 16, 26, 22, 32], incomplete_last=True)
        self.assertEqual(structure.atr_series(bars)[-1], structure.atr_series(bars[:-1])[-1])


class ChartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "charts"

    def bars(self):
        """Long enough for the weekly view and the 200-day average to exist."""
        turns, price = [20.0], 20.0
        for step in range(28):
            price += 6.0 if step % 2 == 0 else -3.5
            turns.append(price)
        return path(turns, leg=6, wick=0.8)

    def test_the_daily_and_weekly_views_carry_structure_and_the_monthly_does_not(self):
        rendered = charts.render(self.bars(), self.out, title="DEMO.US")
        derived = rendered["derived"]
        for view in ("D", "DR", "W"):
            with self.subTest(view=view):
                found = derived["views"][view]["structure"]
                self.assertIn(found["state"]["trend"], ("up", "down", "undetermined"))
                self.assertEqual(found["state"]["timeframe"],
                                 "D" if view.startswith("D") else "W")
                self.assertTrue(found["events"])
                self.assertLessEqual(len(found["events"]), charts.EVENTS_KEPT)
                confirmed = [event["confirmed_at"] for event in found["events"]]
                self.assertEqual(confirmed, sorted(confirmed))
        self.assertNotIn("structure", derived["views"]["M"])
        self.assertEqual(derived["parameters"]["structure"]["events_kept"], charts.EVENTS_KEPT)
        self.assertEqual(read_json(self.out / "derived.json")["views"]["D"]["structure"],
                         derived["views"]["D"]["structure"])

    def test_the_overlay_is_drawn_and_says_in_the_legend_that_it_is_not_a_zone(self):
        rendered = charts.render(self.bars(), self.out)
        for view in ("D", "DR", "W"):
            with self.subTest(view=view):
                self.assertTrue(rendered["plotted"][view]["structure_drawn"])
                self.assertIn(charts.STRUCTURE_LABEL, rendered["plotted"][view]["legend"])
                self.assertIn("200-day SMA", rendered["plotted"][view]["legend"])
        self.assertEqual(rendered["plotted"]["M"]["structure_drawn"], [])
        self.assertNotIn(charts.STRUCTURE_LABEL, rendered["plotted"]["M"]["legend"])
        self.assertNotIn(charts.STRUCTURE_LABEL, (label for label, _, _
                                                  in charts.OVERLAYS.values()))

    def test_fewer_events_can_be_asked_for(self):
        derived = charts.render(self.bars(), self.out, events_kept=3)["derived"]
        self.assertEqual(len(derived["views"]["D"]["structure"]["events"]), 3)

    def test_the_weekly_helper_reads_the_same_daily_array_on_weekly_bars(self):
        bars = self.bars()
        weekly = charts.structure(bars, "W")
        self.assertEqual(weekly["state"]["timeframe"], "W")
        self.assertEqual(weekly["state"]["parameters"]["pivot_width"], 1)
        self.assertEqual(weekly["state"]["last_bar"], charts.resample(bars, "W")[-1]["at"])
        self.assertEqual(charts.structure(bars, "D")["state"]["last_bar"], bars[-1]["at"])
        self.assertNotEqual(weekly["state"]["swings_count"],
                            charts.structure(bars, "D")["state"]["swings_count"])

    def test_an_event_can_name_the_support_or_resistance_band_it_belongs_to(self):
        derived = charts.render(self.bars(), self.out)["derived"]
        events = derived["views"]["D"]["structure"]["events"]
        referenced = [event for event in events if event.get("zone_ref")]
        self.assertTrue(referenced, "a structure level sits inside one of the drawn bands")
        for event in referenced:
            with self.subTest(event=event["event_id"]):
                zone = event["zone_ref"]
                self.assertLessEqual(zone["lower"], event["level"])
                self.assertLessEqual(event["level"], zone["upper"])
                self.assertIn(zone["pivots"], ("high", "low"))


if __name__ == "__main__":
    unittest.main()
