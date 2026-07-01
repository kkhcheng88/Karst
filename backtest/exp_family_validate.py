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
import json
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

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".insider_data")
_PXC = os.path.join(_DATA, "px_defeatbeta.pkl")
_HOR = [21, 63]
_MIN_NAMES = 25          # cross-section must have >= this many names on a date to compute an IC


def _px_series(tk):
    try:
        from defeatbeta_api.data.ticker import Ticker
        d = Ticker(tk).price(); d = d.data if hasattr(d, "data") else d
        s = pd.Series(pd.to_numeric(d["close"], errors="coerce").values,
                      index=pd.to_datetime(d["report_date"], errors="coerce")).dropna().sort_index()
        return s if len(s) > 300 else None
    except Exception:
        return None


def _price_universe(tickers, cache_name):
    """Price a ticker list via defeatbeta (no rate limit), disk-cached."""
    pxc = os.path.join(_DATA, cache_name)
    cache = {}
    if os.path.exists(pxc):
        try:
            cache = pickle.load(open(pxc, "rb"))
        except Exception:
            cache = {}
    syms = sorted(set(tickers) | {"SPY"})
    need = [t for t in syms if t not in cache]
    for i, t in enumerate(need):
        cache[t] = _px_series(t)
        if i % 100 == 99:
            pickle.dump(cache, open(pxc, "wb"))
    pickle.dump(cache, open(pxc, "wb"))
    return {t: cache.get(t) for t in syms if cache.get(t) is not None}


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
            rs63 = rs126 = None
            if spy is not None:
                sp = spy.index.searchsorted(t)
                if 126 <= sp < len(spy):
                    rs63 = (s.iloc[pos] / s.iloc[pos - 63]) / (spy.iloc[sp] / spy.iloc[sp - 63]) - 1
                    rs126 = (s.iloc[pos] / s.iloc[pos - 126]) / (spy.iloc[sp] / spy.iloc[sp - 126]) - 1
            lowvol = -ret.iloc[pos - 63:pos].std()
            rv = rsi.iloc[pos]
            rec = {"date": t, "tk": tk, "mom": mom, "rev": -rv if rv == rv else np.nan,
                   "rs63": rs63, "rs126": rs126, "lowvol": lowvol}
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


def _longonly(df, sig, spy):
    """Hold the TOP-QUINTILE by signal each month (equal-weight, long-only, ~21d hold), chain -> CAGR +
    terminal wealth, vs SPY buy&hold over the SAME months. Answers 'do the leaders beat the index?'."""
    b, k = [], []
    for t, g in df.groupby("date"):
        g = g[[sig, "f21"]].dropna()
        if len(g) < _MIN_NAMES:
            continue
        top = g[g[sig] >= g[sig].quantile(0.8)]["f21"].mean()
        sp = spy.index.searchsorted(pd.Timestamp(t))
        mkt = (spy.iloc[sp + 21] / spy.iloc[sp] - 1) if sp + 21 < len(spy) else np.nan
        if top == top and mkt == mkt:
            b.append(top); k.append(mkt)
    if len(b) < 24:
        return None
    b, k = np.array(b), np.array(k)
    yrs = len(b) / 12.0
    bw, sw = float(np.prod(1 + b)), float(np.prod(1 + k))
    return bw ** (1 / yrs) - 1, sw ** (1 / yrs) - 1, bw, sw, len(b)


def run(universe_json=None):
    if universe_json and os.path.exists(universe_json):
        tickers = json.load(open(universe_json))
        print(f"[family-validate] pricing {len(tickers)} universe names via defeatbeta ...")
        px = _price_universe(tickers, "sp500_px.pkl")
        tag = f"clean liquid ({os.path.basename(universe_json)})"
    else:
        if not os.path.exists(_PXC):
            print("no price cache -- run exp_insider_validate.py first"); return
        px = {k: v for k, v in pickle.load(open(_PXC, "rb")).items() if v is not None}
        tag = "insider-active (small-cap tilt)"
    print(f"[family-validate] universe: {len(px)} priced tickers -- {tag}")
    df = _panel(px)
    print(f"[family-validate] panel: {len(df)} name-months, {df['date'].nunique()} rebalance dates "
          f"({df['date'].min().date()}..{df['date'].max().date()})\n")
    fams = {"momentum(12-1)": "mom", "mean-rev(RSI-2)": "rev", "RS-short(63d)": "rs63",
            "RS-med(126d)": "rs126", "low-vol(63d)": "lowvol"}
    sharpes = {}
    print(f"{'family':>18} {'hor':>4} {'IC':>7} {'IC t':>6} {'hit':>5} {'nDates':>6} {'LS Sharpe':>9}")
    for name, sig in fams.items():
        for n in _HOR:
            ic = _ic(df, sig, n); sh, r = _longshort(df, sig, n)
            if sh is not None:
                sharpes[f"{name}/{n}"] = sh
            ics = f"{ic['mean']:+.3f} {ic['t']:>6.2f} {ic['hit']:>4.0%} {ic['n']:>6}" if ic else "  (insufficient)"
            print(f"{name:>18} {n:>3}d {ics} {sh if sh is None else round(sh, 2):>9}")
    # LONG-ONLY top-tier vs SPY buy&hold -- the ACTUAL RS/momentum thesis ("hold the leaders, beat the
    # index"), which the IC/long-short lens above cannot answer (the short side can sink a real long edge).
    spy = px.get("SPY")
    if spy is not None:
        print("\n=== LONG-ONLY: hold the TOP-QUINTILE by signal (equal-wt, ~monthly), vs SPY buy&hold ===")
        print(f"{'family':>18} {'basket CAGR':>11} {'SPY CAGR':>9} {'excess':>7} {'basket x':>9} {'SPY x':>7} {'mos':>5}")
        for name, sig in fams.items():
            r = _longonly(df, sig, spy)
            if r:
                bc, sc, bw, sw, n = r
                print(f"{name:>18} {bc * 100:>10.1f}% {sc * 100:>8.1f}% {(bc - sc) * 100:>+6.1f}% "
                      f"{bw:>8.1f}x {sw:>6.1f}x {n:>5}")
        print("  positive = the top-quintile-of-signal basket beat SPY over the full sample (long-only,"
              " monthly rebalance, costless, current-S&P survivorship). This is the 'hold the leaders' test.")

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
    run(sys.argv[1] if len(sys.argv) > 1 else None)
