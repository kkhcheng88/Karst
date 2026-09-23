"""Weekly consensus snapshot: unreported years only, resume after restart, done marker, throttle retry."""
import json
import tempfile
import unittest
from pathlib import Path

from karst import consensus
from karst.fetch import limits


def detail(key, estimate, actual=''):
    return {'key': key, 'estimate': estimate, 'actual': actual}


RESPONSE = {'currency': 'USD', 'list': [
    {'fiscal_year': 2027, 'period_text': 'FY 2027',
     'details': [detail('revenue', '120.0'), detail('ebit', '30.0'), detail('eps', '')]},
    {'fiscal_year': 2026, 'period_text': 'FY 2026', 'details': [detail('revenue', '100.0')]},
    {'fiscal_year': 2025, 'period_text': 'FY 2025', 'details': [detail('revenue', '90.0', '91.0')]},
]}


class Throttled(Exception):
    code = 429002


class FakeHttp:
    def __init__(self, fail=(), throttle_once=()):
        self.calls, self.fail, self.throttle = [], set(fail), set(throttle_once)

    def request(self, method, path):
        symbol = path.split('counter_id=ST/US/')[1].split('&')[0]
        self.calls.append(symbol)
        if symbol in self.fail:
            raise RuntimeError('no such symbol')
        if symbol in self.throttle:
            self.throttle.discard(symbol)
            raise Throttled('429002')
        return RESPONSE


class ConsensusTests(unittest.TestCase):
    def setUp(self):
        self.old = limits.configure(rate=1000, backoff=0)
        self.addCleanup(limits.LIMITS.update, self.old)
        self.root = Path(tempfile.mkdtemp())

    def test_only_unreported_years_are_kept(self):
        years = consensus.forecasts(RESPONSE)
        self.assertEqual([y['fiscal_year'] for y in years], [2027, 2026])
        self.assertEqual(years[0]['estimates'], {'revenue': 120.0, 'ebit': 30.0})
        self.assertEqual(consensus.counter_id('BRK.B.US'), 'ST/US/BRK.B')

    def test_resume_then_done_then_no_refetch(self):
        lines = self.root / 'consensus' / '2026-W39.jsonl'
        lines.parent.mkdir(parents=True)
        lines.write_text(json.dumps({'symbol': 'AAA.US', 'years': []}) + '\n', encoding='utf-8')
        http = FakeHttp(throttle_once={'BBB'})
        summary = consensus.snapshot(self.root, symbols=['AAA.US', 'BBB.US', 'CCC.US'],
                                     week='2026-W39', http=http)
        self.assertEqual(sorted(set(http.calls)), ['BBB', 'CCC'])  # AAA survived the restart
        self.assertEqual((summary['stored'], summary['with_estimates'], summary['failed']), (3, 2, {}))
        self.assertTrue((self.root / 'consensus' / '2026-W39.done.json').exists())
        self.assertEqual(consensus.last_week(self.root), '2026-W39')
        again = FakeHttp()
        consensus.snapshot(self.root, symbols=['DDD.US'], week='2026-W39', http=again)
        self.assertEqual(again.calls, [])

    def test_too_many_failures_leave_the_week_open(self):
        summary = consensus.snapshot(self.root, symbols=['AAA.US', 'BBB.US'], week='2026-W40',
                                     http=FakeHttp(fail={'BBB'}))
        self.assertIn('BBB.US', summary['failed'])
        self.assertFalse((self.root / 'consensus' / '2026-W40.done.json').exists())


if __name__ == '__main__':
    unittest.main()
