"""Vendor symbol derivation: explicit mapping wins, exchange decides the suffix, unknown refuses."""
import unittest

from karst.fetch.longbridge import symbol_for


class SymbolForTests(unittest.TestCase):
    def test_exchange_decides_the_market_suffix(self):
        cases = [
            ({"ticker": "DEMO", "exchange": "NYSE"}, "DEMO.US"),
            ({"ticker": "demo", "exchange": "NASDAQ"}, "DEMO.US"),
            ({"ticker": "DEMO", "exchange": "NYSEARCA"}, "DEMO.US"),
            ({"ticker": "700", "exchange": "HKEX"}, "00700.HK"),
            ({"ticker": "DEMO.US", "exchange": "NYSE"}, "DEMO.US"),
            ({"ticker": "DEMO", "exchange": "NYSE", "symbols": {"longbridge": "OTHER.US"}}, "OTHER.US"),
        ]
        for security, expected in cases:
            with self.subTest(security=security):
                self.assertEqual(symbol_for(security), expected)

    def test_unknown_exchange_is_refused_not_guessed(self):
        with self.assertRaises(ValueError):
            symbol_for({"ticker": "DEMO", "exchange": "TSE"})
        with self.assertRaises(ValueError):
            symbol_for({"exchange": "NYSE"})


if __name__ == "__main__":
    unittest.main()
