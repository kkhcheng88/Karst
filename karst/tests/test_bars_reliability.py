"""Which price snapshot is read, and which of its bars may be called confirmed.

KARST-250. Three defects are pinned here: the longest snapshot used to win (so an
older, longer one overrode newer prices), a bar was called complete on its calendar
date alone (so yesterday's intraday snapshot looked closed today), and a research
cutoff earlier than the snapshot silently truncated a snapshot that did not exist yet.

Every case is built from parameters — dates, closes, acquisition times — through the
same adapter landing and registry path the real sources use. No stock is hard-coded:
the one recorded sample (BE, below) is a parameterized fixture value, kept because it
is the case that exposed the defect.
"""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from karst import bars as bars_module, charts
from karst.fetch import longbridge
from karst.fetch.port import pair_staging
from karst.fetch.registry import EvidenceRegistry
from karst.packet import instant
from karst.tests.test_publish_bars import SYMBOL, stage_prices
from karst.tests.v03_fixture import SECURITY

ENTITY_IDS = sorted({SECURITY['issuer_id'], SECURITY['security_id']})
# 12:00 Hong Kong on the bar's date: what the SDK hands back for a US day bar. It is a
# date marker, not the moment the session closed — which is the whole point below.
DAY_MARKER = 'T04:00:00+00:00'
CLOSE_UTC = 'T20:00:00Z'  # 16:00 America/New_York in summer; the zone does the arithmetic

# Debugging samples only (not an investment view): the two BE snapshots of 2026-09-17
# whose conflict exposed the selection defect — a later intraday reading must not
# override the one taken after the close.
BE_CONFIRMED = (280.76, 14_236_326.0)
BE_INTRADAY = (280.08, 11_493_859.0)


def weekdays(first, count):
    """``count`` consecutive trading dates from ``first`` (weekends skipped)."""
    day, out = dt.date.fromisoformat(first), []
    while len(out) < count:
        if day.weekday() < 5:
            out.append(day.isoformat())
        day += dt.timedelta(days=1)
    return out


def rows(days, *, close=20.0, step=0.5, last=None):
    """Daily candles for ``days`` in the adapter's landing shape.

    ``last`` overrides the final bar's (close, volume) — which is how two snapshots of
    the same day are made to disagree.
    """
    out = []
    for index, day in enumerate(days):
        price, volume = close + step * index, 1_000_000.0 + index
        if last is not None and index == len(days) - 1:
            price, volume = last
        out.append({'timestamp': day + DAY_MARKER, 'open': str(price - 0.4),
                    'close': str(price), 'high': str(price + 1.0), 'low': str(price - 1.0),
                    'volume': volume})
    return out


class ReliabilityCase(unittest.TestCase):
    """A bundle holding one registered prices record per staged snapshot."""

    def bundle_with(self, *snapshots):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        staging = root / 'staging'
        for index, snapshot in enumerate(snapshots):
            snapshot = dict(snapshot)
            landed = snapshot.pop('rows')
            stage_prices(landed, into=f'snap{index}', **snapshot)(staging)
        registry = EvidenceRegistry(root / 'bundle')
        for meta_path, raws in pair_staging(staging):
            for raw in raws:
                registry.register(raw, meta_path, entity_ids=ENTITY_IDS)
        return root / 'bundle', registry.records()

    def series(self, snapshots, as_of, **kwargs):
        bundle, records = self.bundle_with(*snapshots)
        found = bars_module.series_from_evidence(bundle, records, as_of, **kwargs)
        self.assertIsNotNone(found, 'the bundle holds a registered candlestick series')
        return found


class SelectionTests(ReliabilityCase):
    def test_the_newer_snapshot_wins_at_equal_length(self):
        days = weekdays('2026-09-07', 9)
        found = self.series([{'rows': rows(days, last=(300.0, 9_000_000.0)),
                              'fetched_at': '2026-09-17' + CLOSE_UTC},
                             {'rows': rows(days, last=(305.5, 9_100_000.0)),
                              'fetched_at': '2026-09-17T21:05:00Z'}],
                            '2026-09-18T12:00:00Z')
        self.assertEqual(found['bars']['D'][-1]['close'], 305.5)
        self.assertEqual(found['source']['fetched_at'], '2026-09-17T21:05:00Z')
        self.assertEqual(len(found['source']['segments']), 1,
                         'an older snapshot that adds no earlier day adds no segment')

    def test_a_longer_older_snapshot_only_extends_the_earlier_history(self):
        old_days, new_days = weekdays('2026-08-24', 15), weekdays('2026-09-10', 5)
        found = self.series([{'rows': rows(old_days, close=50.0, last=(61.0, 8_000_000.0)),
                              'fetched_at': '2026-09-16T21:05:00Z'},
                             {'rows': rows(new_days, close=70.0, last=(74.25, 9_900_000.0)),
                              'fetched_at': '2026-09-17T21:05:00Z'}],
                            '2026-09-18T12:00:00Z')
        daily = found['bars']['D']
        overlap = {bar['at'][:10]: bar['close'] for bar in daily if bar['at'][:10] in new_days}
        self.assertEqual(daily[0]['at'][:10], old_days[0], 'the older snapshot extends the start')
        self.assertEqual(len(daily), len(set(old_days) | set(new_days)))
        self.assertEqual(overlap, {day: 70.0 + 0.5 * index for index, day in enumerate(new_days[:-1])}
                         | {new_days[-1]: 74.25},
                         'every day the newer snapshot covers comes from the newer snapshot')
        segments = found['source']['segments']
        self.assertEqual([segment['fetched_at'] for segment in segments],
                         ['2026-09-17T21:05:00Z', '2026-09-16T21:05:00Z'])
        self.assertEqual(segments[0]['first_bar'], new_days[0])
        self.assertEqual(segments[1]['last_bar'], old_days[old_days.index(new_days[0]) - 1],
                         'the older segment stops where the newer one starts')
        self.assertEqual(found['source']['evidence_id'], segments[0]['evidence_id'])
        self.assertEqual(len({segment['evidence_id'] for segment in segments}), 2)

    def test_the_recorded_be_intraday_reading_does_not_override_the_close(self):
        days = weekdays('2026-09-01', 13)  # ends 2026-09-17
        found = self.series([{'rows': rows(days, close=250.0, last=BE_INTRADAY),
                              'fetched_at': '2026-09-17T18:30:00Z'},
                             {'rows': rows(days, close=250.0, last=BE_CONFIRMED),
                              'fetched_at': '2026-09-17T21:05:00Z'}],
                            '2026-09-18T12:00:00Z')
        last = found['bars']['D'][-1]
        self.assertEqual((last['close'], last['volume']), BE_CONFIRMED)
        self.assertTrue(last['complete'], 'the snapshot was taken after that session closed')
        self.assertNotIn(BE_INTRADAY[0], [bar['close'] for bar in found['bars']['D']])

    def test_an_incompatible_basis_is_reported_instead_of_merged(self):
        days = weekdays('2026-09-01', 13)
        found = self.series([{'rows': rows(days, close=250.0, last=BE_CONFIRMED),
                              'fetched_at': '2026-09-17T21:05:00Z', 'adjust': 'NoAdjust'},
                             {'rows': rows(weekdays('2026-08-03', 30), close=100.0),
                              'fetched_at': '2026-09-17T21:06:00Z', 'adjust': 'ForwardAdjust'}],
                            '2026-09-18T12:00:00Z')
        self.assertEqual(found['source']['price_basis'],
                         'adjust=ForwardAdjust period=day session=unknown')
        self.assertEqual(len(found['source']['segments']), 1)
        self.assertEqual(len(found['source']['gaps']), 1)
        self.assertIn('different basis', found['source']['gaps'][0])
        self.assertNotIn(BE_CONFIRMED[0], [bar['close'] for bar in found['bars']['D']],
                         'an adjusted and an unadjusted series are never spliced together')

    def test_a_quote_snapshot_does_not_displace_the_candlestick_series(self):
        days = weekdays('2026-09-07', 9)
        bundle, records = self.bundle_with({'rows': rows(days, last=(305.5, 9_100_000.0)),
                                            'fetched_at': '2026-09-17T21:05:00Z'})
        staging = bundle.parent / 'staging' / 'quote'
        # A live quote registers as prices too, and it is always the newest thing in the
        # bundle. It is not a series: it must not become the source of one.
        longbridge.land(staging, 'quote', SYMBOL, {'symbols': [SYMBOL]},
                        [{'symbol': SYMBOL, 'last_done': '306.10', 'open': '304.0',
                          'high': '307.0', 'low': '303.0', 'volume': 1_000,
                          'timestamp': '2026-09-18' + DAY_MARKER}],
                        fetched_at='2026-09-18T13:00:00Z')
        registry = EvidenceRegistry(bundle)
        for meta_path, raws in pair_staging(staging):
            for raw in raws:
                registry.register(raw, meta_path, entity_ids=ENTITY_IDS)
        found = bars_module.series_from_evidence(bundle, registry.records(),
                                                 '2026-09-18T14:00:00Z')
        self.assertEqual(found['source']['fetched_at'], '2026-09-17T21:05:00Z')
        self.assertEqual(len(found['bars']['D']), len(days))


class ReplayTests(ReliabilityCase):
    def test_a_replay_reads_only_the_snapshot_that_existed_then(self):
        days = weekdays('2026-09-01', 7)  # ends 2026-09-09
        later = weekdays('2026-09-01', 13)
        found = self.series([{'rows': rows(days, close=40.0, last=(44.5, 2_000_000.0)),
                              'fetched_at': '2026-09-09T21:05:00Z'},
                             {'rows': rows(later, close=40.0, last=(58.0, 3_000_000.0)),
                              'fetched_at': '2026-09-17T21:05:00Z'}],
                            '2026-09-10T20:00:00Z')
        self.assertEqual(found['source']['fetched_at'], '2026-09-09T21:05:00Z')
        self.assertEqual(found['bars']['D'][-1]['at'][:10], days[-1])
        self.assertEqual(found['bars']['D'][-1]['close'], 44.5)
        self.assertEqual(len(found['source']['gaps']), 1)
        self.assertIn('after the cutoff', found['source']['gaps'][0],
                      'the excluded snapshot is named, not silently dropped')

    def test_a_cutoff_before_every_snapshot_leaves_nothing_to_chart(self):
        bundle, records = self.bundle_with({'rows': rows(weekdays('2026-09-01', 7)),
                                            'fetched_at': '2026-09-17T21:05:00Z'})
        self.assertIsNone(bars_module.series_from_evidence(bundle, records,
                                                           '2026-09-10T20:00:00Z'))


class CompletionTests(ReliabilityCase):
    """A bar is confirmed by its session close, never by the calendar alone."""

    def test_an_intraday_snapshot_is_not_confirmed_by_being_read_the_next_day(self):
        days = weekdays('2026-09-07', 9)  # ends Thursday 2026-09-17
        for fetched_at, expected in (('2026-09-17T18:30:00Z', False),   # before the 20:00Z close
                                     ('2026-09-17T21:05:00Z', True)):   # after it
            with self.subTest(fetched_at=fetched_at):
                found = self.series([{'rows': rows(days), 'fetched_at': fetched_at}],
                                    '2026-09-18T12:00:00Z')
                daily = found['bars']['D']
                self.assertEqual(daily[-1]['complete'], expected)
                self.assertTrue(all(bar['complete'] for bar in daily[:-1]),
                                'the days before it closed long ago either way')

    def test_a_bar_is_not_confirmed_at_a_cutoff_that_falls_before_its_close(self):
        days = weekdays('2026-09-07', 9)
        found = self.series([{'rows': rows(days), 'fetched_at': '2026-09-17T16:00:00Z'}],
                            '2026-09-17T17:00:00Z')  # the research cutoff is itself intraday
        self.assertFalse(found['bars']['D'][-1]['complete'])
        # Even a snapshot taken after the close cannot confirm a bar for a reader who
        # stands before it: the cutoff is the second half of the same rule.
        row = {'timestamp': '2026-09-17' + DAY_MARKER, 'open': '1', 'high': '2',
               'low': '0.5', 'close': '1.5'}
        self.assertFalse(bars_module._bar(row, instant('2026-09-17T17:00:00Z'),
                                          fetched_at=instant('2026-09-17T21:05:00Z'))['complete'])
        self.assertTrue(bars_module._bar(row, instant('2026-09-17T21:00:00Z'),
                                         fetched_at=instant('2026-09-17T21:05:00Z'))['complete'])

    def test_an_unknown_acquisition_time_or_zone_is_never_promoted(self):
        row = {'timestamp': '2026-09-17' + DAY_MARKER, 'open': '1', 'high': '2',
               'low': '0.5', 'close': '1.5'}
        cutoff = instant('2026-09-18T12:00:00Z')
        self.assertFalse(bars_module._bar(row, cutoff)['complete'])
        self.assertFalse(bars_module._bar(row, cutoff, fetched_at=None)['complete'])
        self.assertIsNone(bars_module._moment('2026-09-17T21:05:00'), 'no zone, no moment')
        self.assertIsNone(bars_module._moment(None))

    def test_the_session_calendar_is_configurable(self):
        days, fetched_at = weekdays('2026-09-07', 9), '2026-09-17T17:30:00Z'
        cases = {'regular close': (bars_module.Session(), False),
                 'early close 13:00': (bars_module.Session(
                     half_days={'2026-09-17': dt.time(13, 0)}), True),
                 'declared holiday': (bars_module.Session(holidays=['2026-09-17']), False),
                 'Hong Kong 16:00': (bars_module.Session('Asia/Hong_Kong'), True)}
        for label, (session, expected) in cases.items():
            with self.subTest(session=label):
                found = self.series([{'rows': rows(days), 'fetched_at': fetched_at}],
                                    '2026-09-18T12:00:00Z', session=session)
                self.assertEqual(found['bars']['D'][-1]['complete'], expected)

    def test_a_week_or_month_holding_an_unconfirmed_day_stays_unconfirmed(self):
        # The older snapshot was taken mid-session on Friday 2026-09-11, so the day it
        # ends on never closed for us — and the week that contains it cannot be confirmed
        # even though two later weeks have since finished.
        found = self.series([{'rows': rows(weekdays('2026-08-24', 15), close=50.0),
                              'fetched_at': '2026-09-11T18:30:00Z'},
                             {'rows': rows(weekdays('2026-09-14', 5), close=70.0),
                              'fetched_at': '2026-09-18T21:05:00Z'}],
                            '2026-09-18T22:00:00Z')
        daily = found['bars']['D']
        self.assertEqual([bar['at'][:10] for bar in daily if not bar['complete']],
                         ['2026-09-11'])
        weekly = {week['at']: week['complete'] for week in charts.resample(daily, 'W')}
        self.assertEqual(weekly, {'2026-08-24': True, '2026-08-31': True,
                                  '2026-09-07': False,   # holds the unconfirmed Friday
                                  '2026-09-14': False})  # the week still running
        monthly = {month['at']: month['complete'] for month in charts.resample(daily, 'M')}
        self.assertEqual(monthly, {'2026-08-01': True,     # every August day was confirmed
                                   '2026-09-01': False})   # September holds the open day


if __name__ == '__main__':
    unittest.main()


class ExchangeSessionTests(unittest.TestCase):
    def test_a_session_is_derived_from_the_exchange_code_with_a_us_fallback(self):
        from karst.bars import Session
        hk = Session.for_exchange("HKEX")
        ny = Session.for_exchange("nasdaq")
        unknown = Session.for_exchange(None)
        self.assertEqual(str(hk.zone), "Asia/Hong_Kong")
        self.assertEqual(str(ny.zone), "America/New_York")
        self.assertEqual(str(unknown.zone), "America/New_York")
        # 16:00 Hong Kong is 08:00Z; 16:00 New York in September is 20:00Z.
        self.assertEqual(hk.close_instant("2026-09-17").isoformat(), "2026-09-17T16:00:00+08:00")
        self.assertEqual(ny.close_instant("2026-09-17").utcoffset().total_seconds(), -4 * 3600)
