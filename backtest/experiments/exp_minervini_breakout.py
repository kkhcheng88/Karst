"""BREAKOUT momentum SPEC A/B — Minervini Trend-Template + base-breakout entry, on individual stocks,
with the distillation's KEY claim tested: is the edge in the ENTRY or in the RISK LAYER (exit/stop)?

Trend Template (price-only subset + RS; cache has no volume so volume-confirmation NOT applied):
  price>150SMA & >200SMA; 150>200; 200 rising (>21d ago); 50>150>200; price>50SMA;
  price >= 1.30x 52wk-low; price >= 0.75x 52wk-high (within 25%); RS percentile >= 80 (126d rel vs SPY,
  cross-sectional rank at month-ends, ffilled — point-in-time).
Entry = template passes AND close = new 20-day high (≈4-week base breakout), enter next bar.
Two EXIT arms (the increment):
  RISK   = 8% stop OR close < 50SMA trail  (practitioner risk layer)
  FIXED  = hold 63 trading days             (isolates the entry's raw forward edge)
Per-trade %/win%/hold[n]/部署效率%/yr, by market-cap tier, FULL + two-halves. If RISK >> FIXED -> the
edge is in the risk layer (Minervini's claim); if similar -> entry carries it.

Individual-stock cache (survivorship — relative). fwd clipped [-0.9,3.0]. 2016+, 2bp/trade round-trip.

    python backtest/experiments/exp_minervini_breakout.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as D  # noqa: E402

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
START = pd.Timestamp("2016-01-01")
SPLIT = pd.Timestamp("2021-01-01")
END = pd.Timestamp("2100-01-01")
RT = 0.0002
TIERS = [("micro <$300M", 0, 3e8), ("small $300M-2B", 3e8, 2e9),
         ("mid $2B-10B", 2e9, 1e10), ("large >$10B", 1e10, 1e99)]


def rs_percentile_panel(px, spy, stocks):
    spy126 = spy / spy.shift(126)
    months = pd.date_range("2015-06-30", "2026-06-30", freq="ME")
    rel = {}
    for tk in stocks:
        s = px[tk]; s = s[~s.index.duplicated()].sort_index()
        r = (s / s.shift(126)) / spy126.reindex(s.index, method="ffill") - 1
        rel[tk] = r.reindex(months, method="ffill")
    panel = pd.DataFrame(rel)
    return (panel.rank(axis=1, pct=True) * 100)   # RS percentile per month × stock


def simulate(p, s50, tmpl, nh20, arm):
    n = len(p); i = 1; out = []
    while i < n - 1:
        if tmpl[i] and nh20[i]:
            e = i + 1                        # enter next bar
            if e >= n:
                break
            ep = p[e]; stop = ep * 0.92; j = e + 1
            while j < n:
                if arm == "risk":
                    if p[j] <= stop or (s50[j] == s50[j] and p[j] < s50[j]):
                        break
                else:
                    if j - e >= 63:
                        break
                j += 1
            xj = min(j, n - 1)
            out.append((float(np.clip(p[xj] / ep - 1, -0.9, 3.0)) - RT, xj - e, e))
            i = xj + 1
        else:
            i += 1
    return out


def run():
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    mc = pickle.load(open(os.path.join(_DATA, "mktcap_defeatbeta.pkl"), "rb"))
    spy = D.load("SPY")["close"]; spy = spy[~spy.index.duplicated()].sort_index()
    stocks = [t for t in px if isinstance(px.get(t), pd.Series) and mc.get(t) is not None and len(px[t]) > 400]
    print(f"[minervini] universe {len(stocks)}; building RS percentile panel ...")
    rspct = rs_percentile_panel(px, spy, stocks)

    pool = {}   # (tier, arm) -> [(ret,hold,entry_date)]
    for tk in stocks:
        s = px[tk]; s = s[~s.index.duplicated()].sort_index()
        if len(s) < 300:
            continue
        s50 = s.rolling(50).mean(); s150 = s.rolling(150).mean(); s200 = s.rolling(200).mean()
        hi52 = s.rolling(252).max(); lo52 = s.rolling(252).min()
        rs = rspct[tk].reindex(s.index, method="ffill") if tk in rspct.columns else pd.Series(np.nan, index=s.index)
        tmpl = ((s > s150) & (s > s200) & (s150 > s200) & (s200 > s200.shift(21)) &
                (s50 > s150) & (s > s50) & (s >= 1.30 * lo52) & (s >= 0.75 * hi52) & (rs >= 80))
        nh20 = (s >= s.shift(1).rolling(20).max())
        cap = mc[tk].dropna()
        if len(cap) == 0:
            continue
        capv = cap.iloc[-1]
        tier = next((t for t, lo, hi in TIERS if lo <= capv < hi), None)
        if tier is None:
            continue
        p = s.values; s50v = s50.values
        tmv = tmpl.fillna(False).values; nhv = nh20.fillna(False).values
        dates = s.index
        for arm in ("risk", "fixed"):
            for ret, hold, ei in simulate(p, s50v, tmv, nhv, arm):
                if dates[ei] >= START:
                    pool.setdefault((tier, arm), []).append((ret, hold, dates[ei]))

    def show(tier, arm, seg, lo_d, hi_d):
        tr = [(r, h) for (r, h, d) in pool.get((tier, arm), []) if lo_d <= d < hi_d]
        if len(tr) < 20:
            return f"{'n<20':>26}"
        r = np.array([a for a, _ in tr]); hh = np.array([b for _, b in tr])
        eff = (r.mean() / max(hh.mean(), 1)) * 252 * 100
        return f"{r.mean()*100:>+5.1f}/{(r>0).mean()*100:>3.0f}/{hh.mean():>3.0f}[{len(tr):>4}]{eff:>+5.0f}%".rjust(26)

    print("\n每格 每筆%/勝%/持有d[n]/部署效率%/yr   (RISK=8%止蝕+50MA trail;FIXED=持63日)")
    for tier, _, _ in TIERS:
        print(f"\n========== {tier} ==========")
        print(f"{'':10}{'FULL 2016+':>26}{'H1 2016-2020':>26}{'H2 2021-now':>26}")
        for arm in ("risk", "fixed"):
            print(f"  {arm.upper():<8}" + show(tier, arm, "FULL", START, END)
                  + show(tier, arm, "H1", START, SPLIT) + show(tier, arm, "H2", SPLIT, END))
    print("\nREAD: RISK vs FIXED = 風控層增量。RISK 明顯高 = edge 喺出場/止蝕(Minervini 講法);相近 = 入場carry。"
          "\n price-only(無量確認,少咗突破質量 filter)。survivorship 偏高睇相對 + 兩半。")


if __name__ == "__main__":
    run()
