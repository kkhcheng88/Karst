# -*- coding: utf-8 -*-
"""Download monthly adjusted prices for every ticker in PAIRS and measure the
actual trough-to-peak multiple inside each pair's window. No multiple is taken
on faith - if yfinance has no data, the row says NO_DATA.

Run:  PYTHONUTF8=1 python fetch_prices.py
"""
import json
import pathlib
import sys

import pandas as pd
import yfinance as yf

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pairs import PAIRS  # noqa: E402

DATA = HERE / "data"
OUT = HERE / "out"
DATA.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

TICKERS = sorted({p["winner"] for p in PAIRS} | {p["loser"] for p in PAIRS} | {"SPY"})


def fetch():
    frames = {}
    for t in TICKERS:
        try:
            df = yf.download(t, start="2005-01-01", end="2026-09-02",
                             interval="1mo", progress=False, auto_adjust=True)
            # Split-adjusted closes are right for returns and wrong for market
            # cap: SEC share counts are as-reported at the time, so multiplying
            # them by a back-adjusted price understates the cap of any company
            # that later split. Keep the unadjusted close alongside.
            raw = yf.download(t, start="2005-01-01", end="2026-09-02",
                              interval="1mo", progress=False, auto_adjust=False)
        except Exception as exc:  # noqa: BLE001
            print(f"{t}: FETCH_ERROR {exc}")
            continue
        if df is None or df.empty:
            print(f"{t}: NO_DATA")
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        out = df[["Close", "Volume"]].rename(
            columns={"Close": "close", "Volume": "volume"})
        if raw is not None and not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            out["close_unadjusted"] = raw["Close"].reindex(out.index)
        else:
            out["close_unadjusted"] = float("nan")
        frames[t] = out
        print(f"{t}: {len(df)} months {df.index[0].date()} -> {df.index[-1].date()}")
    panel = pd.concat(frames, names=["symbol", "month_end"])
    panel.to_parquet(DATA / "prices_monthly.parquet")

    # Split history. yfinance ALWAYS split-adjusts its price history (even with
    # auto_adjust=False), so a market cap built from an as-reported SEC share
    # count needs the share count moved onto the same post-split basis.
    srows = []
    for t in TICKERS:
        try:
            sp = yf.Ticker(t).splits
        except Exception as exc:  # noqa: BLE001
            print(f"{t}: SPLITS_ERROR {exc}")
            continue
        for dt, r in sp.items():
            srows.append(dict(symbol=t, date=str(pd.Timestamp(dt).date()), ratio=float(r)))
    sdf = pd.DataFrame(srows)
    sdf.to_csv(DATA / "splits.csv", index=False, encoding="utf-8")
    print(f"splits recorded: {len(sdf)} events across {sdf.symbol.nunique() if len(sdf) else 0} tickers")
    return panel


def measure(panel):
    rows = []
    spy = panel.loc["SPY", "close"]
    for p in PAIRS:
        for role in ("winner", "loser"):
            t = p[role]
            if t not in panel.index.get_level_values(0):
                rows.append(dict(pid=p["pid"], role=role, symbol=t, status="NO_DATA"))
                continue
            s = panel.loc[t, "close"].dropna()
            w0, w1 = pd.Timestamp(p["window"][0]), pd.Timestamp(p["window"][1])
            win = s[(s.index >= w0) & (s.index <= w1)]
            if len(win) < 6:
                rows.append(dict(pid=p["pid"], role=role, symbol=t,
                                 status="WINDOW_TOO_SHORT", n_months=len(win)))
                continue
            trough_dt = win.idxmin()
            after = win[win.index >= trough_dt]
            peak_dt = after.idxmax()
            trough, peak = float(win.min()), float(after.max())
            end_val = float(win.iloc[-1])
            # base-year end price and prior-12m relative strength vs SPY
            by_end = pd.Timestamp(f"{p['base_year']}-12-31")
            hist = s[s.index <= by_end]
            rs12 = None
            px_base = None
            if len(hist) >= 1:
                px_base = float(hist.iloc[-1])
            if len(hist) >= 13:
                r_stock = float(hist.iloc[-1] / hist.iloc[-13] - 1)
                sh = spy[spy.index <= by_end]
                r_spy = float(sh.iloc[-1] / sh.iloc[-13] - 1)
                rs12 = r_stock - r_spy
            # DECIDABLE multiple: buy at base-year end, hold. The trough is only
            # knowable after the fact, so trough-to-peak flatters everyone.
            fwd = s[(s.index > by_end) & (s.index <= w1)]
            mult_hold_peak = mult_hold_end = None
            peak_hold_month = None
            if len(fwd) >= 6 and px_base:
                mult_hold_peak = round(float(fwd.max()) / px_base, 2)
                mult_hold_end = round(float(fwd.iloc[-1]) / px_base, 2)
                peak_hold_month = str(fwd.idxmax().date())
            # same for SPY over the identical span, as the benchmark
            spy_hold_peak = None
            sf = spy[(spy.index > by_end) & (spy.index <= w1)]
            if len(sf) >= 6:
                spy_hold_peak = round(float(sf.max()) / float(spy[spy.index <= by_end].iloc[-1]), 2)
            # max drawdown over base year + prior year
            dd = None
            hist24 = hist.tail(24)
            if len(hist24) >= 6:
                dd = float((hist24 / hist24.cummax() - 1).min())
            rows.append(dict(
                pid=p["pid"], role=role, symbol=t, status="OK",
                first_month=str(s.index[0].date()), last_month=str(s.index[-1].date()),
                trough_month=str(trough_dt.date()), trough=round(trough, 4),
                peak_month=str(peak_dt.date()), peak=round(peak, 4),
                multiple_trough_to_peak=round(peak / trough, 2),
                window_end_price=round(end_val, 4),
                multiple_trough_to_windowend=round(end_val / trough, 2),
                base_year=p["base_year"],
                price_at_base_year_end=None if px_base is None else round(px_base, 4),
                mult_hold_from_base_year_end_to_peak=mult_hold_peak,
                peak_month_after_base_year=peak_hold_month,
                mult_hold_from_base_year_end_to_windowend=mult_hold_end,
                spy_mult_same_span_to_peak=spy_hold_peak,
                rs12_vs_spy_at_base_year_end=None if rs12 is None else round(rs12, 4),
                maxdd_24m_to_base_year_end=None if dd is None else round(dd, 4),
            ))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    panel = fetch()
    res = measure(panel)
    res.to_csv(OUT / "price_measures.csv", index=False, encoding="utf-8")
    print()
    cols = ["pid", "role", "symbol", "status", "base_year",
            "mult_hold_from_base_year_end_to_peak", "peak_month_after_base_year",
            "mult_hold_from_base_year_end_to_windowend", "spy_mult_same_span_to_peak",
            "multiple_trough_to_peak", "rs12_vs_spy_at_base_year_end",
            "maxdd_24m_to_base_year_end"]
    print(res.reindex(columns=cols).to_string(index=False))
    print(json.dumps({"tickers": len(TICKERS), "rows": len(res)}, indent=1))
