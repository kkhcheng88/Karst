"""KARST-125: how WIDE is yfinance's quarterly estimate-vs-actual coverage?

Depth was measured elsewhere; this measures breadth across market-cap tiers and
asset types, because a denominator that only exists for mega caps is useless for
a sector/stock-level gauge.

Run: set PYTHONUTF8=1 && python probe_yf_coverage.py
Output: out/yf_coverage.csv
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

UNIVERSE = {
    "mega": ["AAPL", "MSFT", "NVDA", "AMZN", "JPM"],
    "mid": ["CROX", "DKS", "OLLI", "SAIA", "EXPO"],
    "small": ["AXTI", "PLUG", "VUZI", "AMSC", "BBAI"],
    "micro": ["GEVO", "INVZ", "MVIS", "SES", "NNDM"],
    "reit": ["O", "PLD", "SPG"],
    "sector_etf": ["XLK", "XLF", "XLE", "XLV", "SPY"],
}


def main():
    import pandas as pd
    import yfinance as yf

    rows = []
    for tier, tickers in UNIVERSE.items():
        for t in tickers:
            rec = {"tier": tier, "ticker": t, "n_quarters": 0, "n_with_est": 0,
                   "oldest": None, "newest": None, "has_fwd_consensus": False,
                   "n_analysts_0q": None, "error": None}
            try:
                tk = yf.Ticker(t)
                ed = tk.get_earnings_dates(limit=100)
                if ed is not None and not ed.empty:
                    rec["n_quarters"] = len(ed)
                    rec["n_with_est"] = int(ed["EPS Estimate"].notna().sum())
                    rec["oldest"] = str(ed.index[-1])[:10]
                    rec["newest"] = str(ed.index[0])[:10]
                ee = tk.earnings_estimate
                if ee is not None and not ee.empty and "0q" in ee.index:
                    rec["has_fwd_consensus"] = bool(pd.notna(ee.loc["0q", "avg"]))
                    rec["n_analysts_0q"] = ee.loc["0q", "numberOfAnalysts"]
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {str(e)[:80]}"
            print(rec)
            rows.append(rec)

    df = pd.DataFrame(rows)
    p = os.path.join(OUT, "yf_coverage.csv")
    df.to_csv(p, index=False, encoding="utf-8")
    print("\nsaved ->", p)
    print("\n--- by tier ---")
    print(df.groupby("tier").agg(
        n=("ticker", "size"),
        with_history=("n_with_est", lambda s: int((s > 0).sum())),
        median_quarters=("n_with_est", "median"),
        with_fwd=("has_fwd_consensus", "sum")).to_string())


if __name__ == "__main__":
    main()
