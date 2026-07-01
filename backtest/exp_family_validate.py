"""CIO Phase-0 validation for the BACKFILLABLE quant families (the ones that CAN be walk-forward tested,
unlike thesis confidence). One harness, one universe, apples-to-apples forward IC + deflated Sharpe:

  momentum (12-1)      -- buy past winners            (Jegadeesh-Titman; crash-prone/crowded)
  mean-reversion (RSI-2) -- buy short-term oversold   (Connors; low-capacity/decayed)
  relative strength (63d vs SPY) -- ~= momentum
  low-volatility (63d)  -- the low-vol anomaly

Cross-sectional Spearman IC per monthly rebalance (signal_t vs forward N-day return), averaged ->
mean IC + t-stat; plus a quintile long-short -> annualized Sharpe + deflated Sharpe (multiple-testing).

Prices: defeatbeta (DuckDB-cached, no rate limit, retains delisted names). Universe = whatever is in
the shared price cache backtest/.insider_data/px_defeatbeta.pkl (broad, insider-active names -> small-cap
tilt; a caveat, not fatal). Point-in-time safe: signals use data <= t, returns use data > t.

    python backtest/exp_family_validate.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from metrics import deflated_sharpe_ratio as _dsr
except Exception:
    _dsr = None

_PXC = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".insider_data", "px_defeatbeta.pkl")
_HOR = [21, 63]
_MIN_NAMES = 25          # cross-section must have >= this many names on a date to compute an IC


def _rsi2(s):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _panel(px):
    """Long DataFrame: (date, ticker, mom, rev, rs, lowvol, fwd21, fwd63) at month-ends, point-in-time."""
    spy = px.get("SPY")
    rows = []
    for tk, s in px.items():
        if tk == "SPY" or s is None or len(s) < 300:
            continue
        s = s[~s.index.duplicated()].sort_index()
        ret = s.pct_change()
        rsi = _rsi2(s)
        me = s.resample("ME").last().index          # month-end sample dates
        for t in me:
            pos = s.index.searchsorted(t)
            if pos < 252 or pos >= len(s):
                continue
            p0 = s.iloc[pos]
            mom = s.iloc[pos - 21] / s.iloc[pos - 252] - 1 if pos >= 252 else np.nan
            rs = None
            if spy is not None:
                sp = spy.index.searchsorted(t)
                if 63 <= sp < len(spy):
                    rs = (s.iloc[pos] / s.iloc[pos - 63]) / (spy.iloc[sp] / spy.iloc[sp - 63]) - 1
            lowvol = -ret.iloc[pos - 63:pos].std()
            rv = rsi.iloc[pos]
            rec = {"date": t, "tk": tk, "mom": mom, "rev": -rv if rv == rv else np.nan,
                   "rs": rs, "lowvol": lowvol}
            for n in _HOR:
                rec[f"f{n}"] = (s.iloc[pos + n] / p0 - 1) if pos + n < len(s) and p0 > 0 else np.nan
            rows.append(rec)
    return pd.DataFrame(rows)


def _ic(df, sig, n):
    ics = []
    for _, g in df.groupby("date"):
        g = g[[sig, f"f{n}"]].dropna()
        if len(g) >= _MIN_NAMES and g[sig].nunique() > 5:
            ics.append(g[sig].corr(g[f"f{n}"], method="spearman"))
    ics = [x for x in ics if x == x]
    if len(ics) < 12:
        return None
    a = np.array(ics)
    return {"mean": a.mean(), "t": a.mean() / (a.std() / np.sqrt(len(a))), "hit": (a > 0).mean(), "n": len(a)}


def _longshort(df, sig, n):
    """Quintile long-short monthly returns -> annualized Sharpe (per-year scale by 12/(n/21))."""
    rets = []
    for _, g in df.groupby("date"):
        g = g[[sig, f"f{n}"]].dropna()
        if len(g) < _MIN_NAMES:
            continue
        q = g[sig].quantile([0.2, 0.8])
        top = g[g[sig] >= q.iloc[1]][f"f{n}"].mean()
        bot = g[g[sig] <= q.iloc[0]][f"f{n}"].mean()
        if top == top and bot == bot:
            rets.append(top - bot)
    if len(rets) < 12:
        return None, None
    r = np.array(rets)
    per_yr = 12 / (n / 21)
    sharpe = (r.mean() / r.std()) * np.sqrt(per_yr) if r.std() else np.nan
    return sharpe, r


def run():
    if not os.path.exists(_PXC):
        print("no price cache -- run exp_insider_validate.py first to populate px_defeatbeta.pkl"); return
    px = pickle.load(open(_PXC, "rb"))
    px = {k: v for k, v in px.items() if v is not None}
    print(f"[family-validate] universe: {len(px)} priced tickers (defeatbeta cache)")
    df = _panel(px)
    print(f"[family-validate] panel: {len(df)} name-months, {df['date'].nunique()} rebalance dates "
          f"({df['date'].min().date()}..{df['date'].max().date()})\n")
    fams = {"momentum(12-1)": "mom", "mean-rev(RSI-2)": "rev", "rel-strength(63d)": "rs", "low-vol(63d)": "lowvol"}
    sharpes = {}
    print(f"{'family':>18} {'hor':>4} {'IC':>7} {'IC t':>6} {'hit':>5} {'nDates':>6} {'LS Sharpe':>9}")
    for name, sig in fams.items():
        for n in _HOR:
            ic = _ic(df, sig, n); sh, r = _longshort(df, sig, n)
            if sh is not None:
                sharpes[f"{name}/{n}"] = sh
            ics = f"{ic['mean']:+.3f} {ic['t']:>6.2f} {ic['hit']:>4.0%} {ic['n']:>6}" if ic else "  (insufficient)"
            print(f"{name:>18} {n:>3}d {ics} {sh if sh is None else round(sh, 2):>9}")
    # deflated Sharpe on the best family (vs ALL family/horizon variants tried = the multiple-testing set)
    if _dsr and sharpes:
        best = max(sharpes, key=sharpes.get)          # best POSITIVE Sharpe (a tradeable long-short)
        name, ns = best.rsplit("/", 1); n = int(ns)
        _, r = _longshort(df, fams[name], n)
        try:
            ds = _dsr(r, list(sharpes.values()), periods_per_year=int(12 / (n / 21)))
            print(f"\nbest = {best} (Sharpe {sharpes[best]:.2f}); deflated Sharpe vs {len(sharpes)} "
                  f"variants tried: {ds:.3f}   (>0.95 = survives multiple-testing)")
        except Exception as e:
            print(f"\ndeflated Sharpe: n/a ({str(e)[:50]})")
    print("\nNOTE: universe = insider-active names (small-cap tilt); equal-weight, costless, monthly."
          " A SCREEN of which families carry cross-sectional edge, not a live PnL. IC t>~2 = real signal.")


if __name__ == "__main__":
    run()
