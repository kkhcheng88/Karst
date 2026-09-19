"""Transient bars at publication: read back from registered candlesticks, never saved."""
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from karst import bars as bars_module, service, store as store_module
from karst.fetch import longbridge
from karst.packet import instant, read_json
from karst.schema import ContractError, canonical
from karst.agents.research import intake
from karst.tests.v03_fixture import ROLE_META, build_bundle, citable, payload

SYMBOL = 'DEMO.US'  # parameterized identity
SUBJECT = 'FIXTURE:FIXTURE'


def candles(days=8, end=None, start_price=10.0):
    """Daily candles ending on ``end`` (default: yesterday, UTC), in the landing shape."""
    end = end or datetime.now(timezone.utc).date() - timedelta(days=1)
    first = end - timedelta(days=days - 1)
    rows = []
    for offset in range(days):
        day = first + timedelta(days=offset)
        price = start_price + offset
        rows.append({'close': str(price + .5), 'open': str(price), 'low': str(price - 1),
                     'high': str(price + 1), 'volume': 1000 + offset,
                     'turnover': str(price * 1000),
                     'timestamp': f'{day.isoformat()}T04:00:00Z',
                     'trade_session': 'Intraday'})
    return rows


def stage_prices(rows, *, fetched_at=None, into=None, adjust='NoAdjust'):
    """Land one candlestick snapshot the way the adapter does.

    ``fetched_at`` pins when the snapshot was acquired (a research cutoff earlier than
    that is a replay, and a replay does not read snapshots from its future);
    ``into`` names a subdirectory so a bundle can hold several snapshots of one series.
    """
    def stage(staging):
        longbridge.land(Path(staging) / into if into else staging,
                        'history_candlesticks_by_date', SYMBOL,
                        {'symbol': SYMBOL, 'period': 'day', 'adjust_type': adjust,
                         'trade_session': 'unknown'}, rows, fetched_at=fetched_at,
                        period={'start': rows[0]['timestamp'][:10],
                                'end': rows[-1]['timestamp'][:10]})
    return stage


class PublicationBarTests(unittest.TestCase):
    def build(self, stage=None, bars_count=(0, 0, 0)):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root, stage=stage)
        self.evidence_id = citable(self.bundle, self.records)
        self.store = store_module.init(self.root / 'karst.sqlite3')
        self.addCleanup(self.store.close)
        research = intake(payload(self.packet, self.evidence_id, bars_count=bars_count),
                          bundle=self.bundle,
                          clock=self.packet['created_at'], role_meta=ROLE_META)
        (self.bundle / 'research.json').write_bytes(canonical(research))
        self.version = self.store.save_research_version(SUBJECT, research,
                                                        as_of=self.packet['as_of'])
        return research

    def publish(self, **kwargs):
        return service.publish_research(self.store, self.bundle, self.version['version_id'],
                                        self.root / 'releases', **kwargs)

    def test_registered_candlesticks_are_charted_but_not_saved(self):
        rows = candles()
        self.build(stage_prices(rows))
        released = self.publish()
        html = Path(released['index_html']).read_text(encoding='utf-8')
        self.assertIn('<svg', html)
        saved = read_json(Path(released['publication_dir']) / 'inputs' / 'research.json')
        self.assertNotIn('views', saved['technical'])  # the arrays stayed transient
        self.assertNotIn('"volume"', canonical(saved).decode('utf-8'))

    def test_bars_read_from_evidence_carry_the_prices_and_completeness(self):
        rows = candles(days=4)
        self.build(stage_prices(rows))
        found = bars_module.from_evidence(self.bundle, read_json(self.bundle / 'evidence.json'),
                                          self.packet['as_of'])
        self.assertEqual(len(found['D']), 4)
        self.assertEqual(found['D'][0]['close'], float(rows[0]['close']))
        self.assertTrue(all(bar['complete'] for bar in found['D']))  # all days are past
        self.assertEqual([bar['at'] for bar in found['D']],
                         sorted(bar['at'] for bar in found['D']))

    def test_without_any_candlesticks_the_page_still_publishes(self):
        self.build()
        released = self.publish()
        html = Path(released['index_html']).read_text(encoding='utf-8')
        self.assertNotIn('<svg', html)
        self.assertIn('價格資料截止', html)
        self.assertIsNone(bars_module.from_evidence(
            self.bundle, read_json(self.bundle / 'evidence.json'), self.packet['as_of']))

    def test_a_provider_supplies_bars_when_nothing_is_registered(self):
        self.build()
        rows = candles(days=3, end=date.fromisoformat(self.packet['as_of'][:10]) - timedelta(days=1))
        seen = []

        def provider(security, as_of):
            seen.append((security['ticker'], as_of))
            return [{'at': row['timestamp'], 'open': float(row['open']), 'high': float(row['high']),
                     'low': float(row['low']), 'close': float(row['close']),
                     'volume': row['volume'], 'complete': True} for row in rows]

        released = self.publish(bars_provider=provider)
        self.assertEqual(seen, [(self.packet['security']['ticker'], self.packet['as_of'])])
        self.assertIn('<svg', Path(released['index_html']).read_text(encoding='utf-8'))

    def test_bars_after_the_cutoff_are_refused(self):
        self.build()
        late = {'D': [{'at': '2099-01-01T00:00:00Z', 'open': 1.0, 'high': 2.0, 'low': .5,
                       'close': 1.5, 'volume': 10, 'complete': True}]}
        with self.assertRaisesRegex(ContractError, 'after the research cutoff'):
            self.publish(bars=late)

    def explicit_bars(self, days=3):
        """Bars the caller vouches for, the way a runner hands over the series it charted."""
        rows = candles(days=days,
                       end=date.fromisoformat(self.packet['as_of'][:10]) - timedelta(days=1))
        return [{'at': row['timestamp'], 'open': float(row['open']), 'high': float(row['high']),
                 'low': float(row['low']), 'close': float(row['close']),
                 'volume': row['volume'], 'complete': True} for row in rows]

    def test_a_chart_thinner_than_the_version_measured_is_refused_not_published(self):
        # The saved version stands on 300 daily bars. Its own evidence holds no series to
        # rebuild them from, so the page would publish with no pivots and no 200-day
        # average — and nothing on it saying a figure went missing.
        self.build(bars_count=(300, 60, 15))
        with self.assertRaisesRegex(ContractError, 'no prices evidence'):
            self.publish()
        released = self.publish(bars=self.explicit_bars())
        self.assertIn('<svg', Path(released['index_html']).read_text(encoding='utf-8'))

    def test_a_short_rebuilt_series_is_refused_as_loudly_as_none_at_all(self):
        # The dangerous half: a handful of bars still draws a plausible-looking chart.
        self.build(stage_prices(candles(days=6)), bars_count=(300, 60, 15))
        with self.assertRaisesRegex(ContractError, '300 daily bars'):
            self.publish()

    def test_rows_that_are_not_candles_are_dropped_not_repaired(self):
        self.build()
        cutoff = self.packet['as_of']
        broken = [{'close': '1', 'timestamp': '2026-01-02T04:00:00Z'},          # no OHLC
                  {'open': '1', 'high': '2', 'low': '3', 'close': '1.5',
                   'timestamp': '2026-01-03T04:00:00Z'},                        # low above open
                  {'open': '1', 'high': '2', 'low': '.5', 'close': '1.5',
                   'timestamp': '2026-01-04'}]                                  # no zone
        self.assertEqual([bars_module._bar(row, instant(cutoff)) for row in broken], [None] * 3)


if __name__ == '__main__':
    unittest.main()
