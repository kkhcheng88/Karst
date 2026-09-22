import unittest

from karst import bars, daily, daily_bench, service


class DailyBenchTests(unittest.TestCase):
    def test_every_phase_is_reported_and_the_daily_path_is_restored(self):
        originals = (daily._Members.append, service.plan_update, bars.series_for)
        result = daily_bench.run(3, prior_news=2, news_items=1, history_bars=250, workers=1)
        self.assertEqual(result['member_status'], {'ready_for_review': 3})
        for phase in ('fetch_prices', 'fetch_news', 'series_rebuild', 'plan_update', 'checkpoint',
                      'snapshot'):
            self.assertGreater(result['phases'][phase]['calls'], 0, phase)
        self.assertEqual(result['checkpoint']['writes'], 3)  # one line per member
        self.assertGreaterEqual(result['phases']['other']['seconds'], -0.01)
        self.assertEqual(result['history_recovered'], 0)
        # The previous day stored every series: today's prices start at its last bar.
        self.assertEqual(result['prices_from_last_complete_bar'], 3)
        self.assertEqual(originals, (daily._Members.append, service.plan_update, bars.series_for))

    def test_injected_failures_leave_members_incomplete(self):
        result = daily_bench.run(2, failure_rate=1.0, prior_news=1, news_items=1, history_bars=250,
                                 backoff=0.0)
        self.assertEqual(result['member_status'], {'incomplete': 2})


if __name__ == '__main__':
    unittest.main()
