"""Insider BREADTH probe (Phase-3 P0-c revisit, 2026-07-11) -- tests Peter Lynch's *Beating the
Street* graded-breadth hypothesis: "7 vice presidents buying 1,000 shares each is more bullish than
1 president buying 5,000 shares." exp_insider_validate's build_events() already collapses this to a
BINARY threshold (owners>=2 & val>=$500k = cluster). This script re-cuts the SAME events (no re-pull)
by the owners COUNT itself to test whether forward return scales with breadth, and separates that
from the dollar-value confound (more insiders buying tends to co-occur with a bigger total $, and
with bigger companies that have more officers to begin with).

Tests:
  1. owners bucket (2 / 3-4 / >=5) x forward excess return (21/63/126d vs SPY): mean/median/hit/t
  2. monotonicity: Spearman corr(owners, forward excess) per horizon
  3. confound control: (a) value-quartile x owners(2 vs >=3) double sort, (b) OLS of forward excess
     on log2(owners) + log10(value) [+ log10(mcap) as a 2nd control -- bigger co's have more insiders
     almost by construction]

    python backtest/experiments/exp_insider_breadth.py            # 2006q1..2025q2 (full cached history)
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_insider_validate as IV       # noqa: E402
import exp_insider_mktcap as MC         # noqa: E402

HORS = [21, 63, 126]

# DATA-QUALITY GUARD (same issue diagnosed in exp_insider_market_ratio.py, 2026-07-11): SEC bulk
# Form345 has rare fat-finger filings (e.g. a mis-keyed TRANS_PRICEPERSHARE) that turn a single row
# into a multi-TRILLION "purchase" -- IV.build_events()'s per-event `value` is a SUM over a trailing
# window, so one bad row poisons that whole event's $value (149/9997 events here have value>$10B,
# max $34.6 QUADRILLION for one AGO 2008-04 event -- not real). This matters for THIS script because
# 3b/3c below use $value directly (log10(value) in an OLS has real leverage from such outliers,
# unlike a median). Monkeypatch the transaction-level loader with a sanity cap before aggregating --
# no single open-market Form-4 PURCHASE row is genuinely >$1B.
_orig_load_quarter = IV._load_quarter


def _clean_load_quarter(qtr):
    df = _orig_load_quarter(qtr)
    before = len(df)
    df = df[df["value"] <= 1_000_000_000]
    dropped = before - len(df)
    if dropped:
        print(f"[breadth][{qtr}] data-quality filter dropped {dropped} fat-finger row(s)")
    return df


IV._load_quarter = _clean_load_quarter


def stat(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 15:
        return f"{len(x):>5}   n<15"
    t = x.mean() / (x.std() / np.sqrt(len(x)))
    return f"{len(x):>5}{x.mean()*100:>+8.2f}{np.median(x)*100:>+8.2f}{(x > 0).mean()*100:>6.0f}%{t:>7.2f}"


def build(start="2006q1", end="2025q2"):
    ev = IV.build_events(IV._quarters(start, end))
    print(f"[breadth] {start}..{end}: {len(ev)} cluster events / {ev['ticker'].nunique()} tickers "
          f"(threshold: owners>=2, val>=${IV._MIN_VALUE:,})")
    print(f"[breadth] owners distribution: {ev['owners'].value_counts().sort_index().to_dict()}")
    IV._batch_prices(ev["ticker"].tolist())
    MC._batch_mcap(ev["ticker"].tolist())
    spy = IV._px("SPY")
    rows = []
    for _, e in ev.iterrows():
        s = IV._px(e["ticker"])
        if s is None:
            continue
        mc = MC._MCAP.get(e["ticker"])
        rec = {"ticker": e["ticker"], "date": e["date"], "owners": e["owners"], "value": e["value"],
               "mcap": mc.asof(pd.Timestamp(e["date"])) if mc is not None else np.nan}
        ok = False
        for h in HORS:
            r, b = IV._fwd(s, e["date"], h), IV._fwd(spy, e["date"], h)
            rec[h] = (r - b) if (r is not None and b is not None) else np.nan
            ok = ok or (r is not None)
        if ok:
            rows.append(rec)
    return pd.DataFrame(rows)


def ols(y, X):
    """OLS with intercept. y: 1D array. X: dict{name: 1D array}. Returns dict or None if too few rows."""
    cols = list(X.keys())
    mask = np.isfinite(y)
    for c in cols:
        mask &= np.isfinite(X[c])
    yy = y[mask]
    XX = np.column_stack([np.ones(mask.sum())] + [X[c][mask] for c in cols])
    n, k = XX.shape
    if n < k + 10:
        return None
    coef, *_ = np.linalg.lstsq(XX, yy, rcond=None)
    resid = yy - XX @ coef
    s2 = float(resid @ resid) / (n - k)
    xtx_inv = np.linalg.inv(XX.T @ XX)
    se = np.sqrt(np.diag(s2 * xtx_inv))
    t = coef / se
    ss_tot = ((yy - yy.mean()) ** 2).sum()
    r2 = 1 - (resid @ resid) / ss_tot if ss_tot > 0 else np.nan
    return dict(n=n, cols=["const"] + cols, coef=coef, t=t, r2=r2)


def print_ols(tag, res):
    if res is None:
        print(f"  {tag}: n too small"); return
    print(f"  {tag}  (n={res['n']}, R2={res['r2']:.4f})")
    for c, b, t in zip(res["cols"], res["coef"], res["t"]):
        print(f"    {c:<14} coef={b:>+10.5f}  t={t:>+6.2f}")


def main():
    df = build()
    print(f"\n事件 matured (有價) n={len(df)}\n")

    print("=== 1. OWNERS 分桶 x forward excess vs SPY (mean%/med%/hit/t) ===")
    H = f"{'n':>5}{'mean%':>8}{'med%':>8}{'hit':>6}{'t':>7}"
    buckets = [("owners=2", df.owners == 2), ("owners=3-4", df.owners.between(3, 4)),
               ("owners>=5", df.owners >= 5)]
    for lbl, m in buckets:
        sub = df[m]
        print(f"\n{lbl}  n={len(sub)}  median $value=${sub['value'].median()/1e3:,.0f}k  "
              f"median mcap=${sub['mcap'].median()/1e9:.2f}B" if len(sub) else f"\n{lbl}  n=0")
        for h in HORS:
            print(f"  {str(h)+'d':<8}{H}") if h == HORS[0] and False else None
            print(f"  {str(h)+'d':<8}{stat(sub[h])}")
    print(f"\n(header cols: {H})")

    print("\n=== 2. 單調性(monotonicity): Spearman corr(owners, forward excess) ===")
    for h in HORS:
        sub = df.dropna(subset=[h, "owners"])
        rho, p = sps.spearmanr(sub["owners"], sub[h])
        print(f"  {h}d: rho={rho:+.4f}  p={p:.4f}  n={len(sub)}")

    print("\n=== 3a. CONFOUND: owners vs $value 相關 ===")
    sub = df.dropna(subset=["owners", "value"])
    rho, p = sps.spearmanr(sub["owners"], sub["value"])
    print(f"  Spearman corr(owners, value) = {rho:+.4f}  p={p:.4f}  n={len(sub)}  "
          f"(>0 confirms breadth buckets are also $-bigger)")

    print("\n=== 3b. Value-quartile x owners(2 vs >=3) double sort, 21d excess ===")
    d = df.dropna(subset=["value", 21]).copy()
    d["vq"] = pd.qcut(d["value"], 4, labels=["Q1(小)", "Q2", "Q3", "Q4(大)"])
    print(f"{'value quartile':<16}{'owners=2':<28}{'owners>=3':<28}")
    print(f"{'':<16}{H:<28}{H:<28}")
    for vq in ["Q1(小)", "Q2", "Q3", "Q4(大)"]:
        g = d[d.vq == vq]
        print(f"{vq:<16}{stat(g[g.owners == 2][21]):<28}{stat(g[g.owners >= 3][21]):<28}")

    print("\n=== 3c. OLS: forward excess ~ log2(owners) [+ log10(value)] [+ log10(mcap)], per horizon ===")
    for h in HORS:
        y = df[h].values.astype(float)
        lo = np.log2(df["owners"].values.astype(float))
        lv = np.log10(df["value"].values.astype(float))
        mcap_arr = df["mcap"].values.astype(float)
        lm = np.where(mcap_arr > 0, np.log10(np.where(mcap_arr > 0, mcap_arr, 1.0)), np.nan)
        print(f"\n --- horizon {h}d ---")
        print_ols("(a) owners only          ", ols(y, {"log2(owners)": lo}))
        print_ols("(b) value only           ", ols(y, {"log10(value)": lv}))
        print_ols("(c) owners + value       ", ols(y, {"log2(owners)": lo, "log10(value)": lv}))
        print_ols("(d) owners + value + mcap", ols(y, {"log2(owners)": lo, "log10(value)": lv,
                                                        "log10(mcap)": lm}))

    print("\nREAD: bucket 1 要單調上升 + rho 顯著正 + OLS (c)/(d) 入面 log2(owners) 嘅 coef 仍然顯著正,"
          " 先算breadth 本身有 marginal edge(非純粹 $/mcap 代理)。若 (a) 顯著但 (c)/(d) 唔顯著 -> owners"
          " 只係 value/size 嘅 proxy,冇獨立信息。")


if __name__ == "__main__":
    main()
