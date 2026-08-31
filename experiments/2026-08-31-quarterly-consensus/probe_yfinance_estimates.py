"""KARST-125: what quarterly consensus does yfinance actually hand back, and how deep?

Pure reconnaissance. For each ticker dumps:
  - get_earnings_dates(limit=N)  -> per-quarter EPS Estimate vs Reported EPS (the deep one)
  - earnings_history             -> same idea, shallower
  - earnings_estimate            -> forward 0q/+1q/0y/+1y consensus (current snapshot)
  - revenue_estimate, eps_trend, eps_revisions, growth_estimates

Run:  set PYTHONUTF8=1 && python probe_yfinance_estimates.py
Output: out/yf_<TICKER>_<endpoint>.csv + out/yfinance_probe.txt
"""
import os
import traceback

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

TICKERS = [
    "AAPL",   # mega cap
    "AXTI",   # the micro cap named on the ticket
    "NVDA",   # heavily covered
    "PLUG",   # loss-making small cap
    "XLK",    # sector ETF - does an ETF get estimates at all?
    "CROX",   # mid cap
]

log_lines = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log_lines.append(s)


def dump(df, ticker, name):
    import pandas as pd
    if df is None:
        log(f"  [{name}] None")
        return
    if not isinstance(df, pd.DataFrame):
        log(f"  [{name}] {type(df)}: {str(df)[:300]}")
        return
    if df.empty:
        log(f"  [{name}] EMPTY")
        return
    log(f"  [{name}] shape={df.shape} columns={list(df.columns)}")
    log(f"  index name={df.index.name} first={df.index[0]} last={df.index[-1]}")
    log(df.to_string()[:4000])
    path = os.path.join(OUT, f"yf_{ticker}_{name}.csv")
    df.to_csv(path, encoding="utf-8")
    log(f"  saved -> {path}")


def main():
    import yfinance as yf
    log("yfinance version:", yf.__version__)

    for t in TICKERS:
        log(f"\n================ {t} ================")
        tk = yf.Ticker(t)

        # The deep one: how many quarters back does Yahoo keep estimate-vs-actual?
        for limit in (12, 40, 100):
            try:
                ed = tk.get_earnings_dates(limit=limit)
                n = 0 if ed is None else len(ed)
                log(f"  get_earnings_dates(limit={limit}) -> {n} rows")
                if limit == 100:
                    dump(ed, t, "earnings_dates_100")
            except Exception as e:
                log(f"  get_earnings_dates(limit={limit}) FAILED: {type(e).__name__}: {str(e)[:200]}")

        for name in ("earnings_history", "earnings_estimate", "revenue_estimate",
                     "eps_trend", "eps_revisions", "growth_estimates"):
            try:
                dump(getattr(tk, name), t, name)
            except Exception as e:
                log(f"  [{name}] FAILED: {type(e).__name__}: {str(e)[:200]}")

        # Does .info carry a forward EPS / forward PE (the would-be denominator)?
        try:
            info = tk.info
            keys = ("forwardEps", "trailingEps", "forwardPE", "trailingPE",
                    "numberOfAnalystOpinions", "mostRecentQuarter", "lastFiscalYearEnd")
            log("  info subset:", {k: info.get(k) for k in keys})
        except Exception as e:
            log(f"  info FAILED: {type(e).__name__}: {str(e)[:200]}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log(traceback.format_exc())
    with open(os.path.join(OUT, "yfinance_probe.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print("\nlog ->", os.path.join(OUT, "yfinance_probe.txt"))
