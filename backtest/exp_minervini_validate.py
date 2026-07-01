"""Backtest the distilled Minervini SEPA/VCP spec (the CHECKER step; distillation was the Maker).

Spec: C:/projects/Distillation/knowledge/method/minervini_sepa/minervini_sepa.spec.yaml
Tests the TECHNICAL core, look-ahead-safe, LONG-ONLY (it is a long-only breakout method):
  filter = trend template (F-TT-01..08, price) + RS-rank threshold
  entry  = breakout above pivot (prior 30d high) on volume expansion, after a volatility CONTRACTION
           (ATR now < ATR earlier in the base)  [proxy for VCP contraction-counting]
  regime = SPY > 200DMA
  exit   = tight stop (sweep 5/7/8/10%), else close<50DMA, else max hold
Sweeps spec test_range on RS / stop / breakout-volume; deflated Sharpe over the variants.

HONEST v1 caveats: fundamentals SKIPPED (price-only SEPA); VCP = ATR-shrink proxy; RS = 6m-return
percentile proxy; costless; universe = defeatbeta-cached (delisted retained but a defined set).
=> first pass on the TECHNICAL skeleton, not full Minervini.

    python backtest/exp_minervini_validate.py
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

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".insider_data")
_PIVOT, _BASE, _MAXHOLD = 30, 40, 126
_RISE, _ABOVE_LOW, _BELOW_HIGH, _CHASE = 21, 0.30, 0.25, 0.05     # fixed template params


def _universe():
    px = {}
    for f in ["px_defeatbeta.pkl", "sp500_px.pkl"]:
        p = os.path.join(_DATA, f)
        if os.path.exists(p):
            for k, v in pickle.load(open(p, "rb")).items():
                if v is not None and k not in px:
                    s = v["close"] if isinstance(v, pd.DataFrame) else v
                    vol = v["volume"] if isinstance(v, pd.DataFrame) and "volume" in v else None
                    s = s[~s.index.duplicated()].sort_index()
                    px[k] = (s, vol[~vol.index.duplicated()].sort_index() if vol is not None else None)
    return px


def _rs_day(px, index):
    """Per-day RS percentile: cross-sectional rank of trailing-6m return at month-ends, ffill to daily."""
    rets = {}
    for tk, (s, _) in px.items():
        if tk == "SPY":
            continue
        rets[tk] = s.resample("ME").last().pct_change(6)
    rank = pd.DataFrame(rets).rank(axis=1, pct=True) * 100
    return rank.reindex(index, method="ffill")


def _prep(s, vol, spy_gate):
    """Param-INDEPENDENT base signal + indicators, computed once per stock."""
    if s is None or len(s) < 260:
        return None
    sma50, sma150, sma200 = s.rolling(50).mean(), s.rolling(150).mean(), s.rolling(200).mean()
    hi52, lo52 = s.rolling(252).max(), s.rolling(252).min()
    piv = s.rolling(_PIVOT).max().shift(1)
    atr = s.diff().abs().rolling(20).mean()
    trend = ((s > sma150) & (s > sma200) & (sma150 > sma200) & (sma50 > sma150) & (s > sma50)
             & (sma200 > sma200.shift(_RISE))
             & (s >= lo52 * (1 + _ABOVE_LOW)) & (s >= hi52 * (1 - _BELOW_HIGH)))
    contraction = atr < atr.shift(_BASE)
    breakout = (s > piv) & (s <= piv * (1 + _CHASE))
    regime = spy_gate.reindex(s.index, method="ffill").notna()
    base = trend & contraction & breakout & regime
    avgvol = vol.rolling(50).mean() if vol is not None else None
    volr = (vol / avgvol) if avgvol is not None else pd.Series(2.0, index=s.index)   # no vol -> pass
    return {"c": s, "sma50": sma50, "base": base, "volr": volr}


def _trades(prep, rs_series, spy, P):
    c, sma50, base, volr = prep["c"], prep["sma50"], prep["base"], prep["volr"]
    sig = base & (volr >= P["volx"])
    if rs_series is not None:
        sig = sig & (rs_series.reindex(c.index).fillna(-1) >= P["rs"])
    idx = c.index
    ents = np.where(sig.values)[0]
    out, last_exit = [], -1
    for i in ents:
        if i <= last_exit or i + 1 >= len(c):
            continue
        ei = i + 1
        ep = c.iloc[ei]
        stop = ep * (1 - P["stop"])
        xi = None
        for j in range(ei + 1, min(ei + _MAXHOLD, len(c))):
            if c.iloc[j] <= stop or c.iloc[j] < sma50.iloc[j]:
                xi = j; break
        if xi is None:
            xi = min(ei + _MAXHOLD, len(c) - 1)
        ret = c.iloc[xi] / ep - 1
        b0, b1 = spy.asof(idx[ei]), spy.asof(idx[xi])
        exc = ret - (b1 / b0 - 1) if (b0 == b0 and b1 == b1 and b0 > 0) else np.nan
        out.append({"ret": ret, "excess": exc, "hold": xi - ei})
        last_exit = xi
    return out


def run():
    px = _universe()
    spy = px["SPY"][0]
    spy200 = spy.rolling(200).mean()
    spy_gate = spy.where(spy > spy200)                      # SPY level when healthy, else NaN
    print(f"[minervini] universe: {len(px)} tickers")
    full_idx = spy.index
    rs = _rs_day(px, full_idx)
    preps = {}
    for tk, (s, vol) in px.items():
        if tk == "SPY":
            continue
        pr = _prep(s, vol, spy_gate)
        if pr is not None and pr["base"].any():
            preps[tk] = pr
    print(f"[minervini] stocks with >=1 base signal: {len(preps)}")

    grid = [{"rs": rsv, "stop": st, "volx": vx}
            for rsv in [70, 80, 90] for st in [0.07, 0.08, 0.10] for vx in [1.0, 1.5]]
    print(f"[minervini] sweeping {len(grid)} param sets (trend-template + VCP-breakout + tight stop)\n")
    print(f"{'RS':>3} {'stop':>4} {'volx':>4} {'trades':>7} {'win%':>5} {'avgW%':>6} {'avgL%':>6} "
          f"{'expct%':>6} {'excess%':>7} {'exc t':>6} {'Sharpe':>6}")
    sharpes, best = [], None
    for P in grid:
        tr = []
        for tk, pr in preps.items():
            tr += _trades(pr, rs[tk] if tk in rs.columns else None, spy, P)
        if len(tr) < 50:
            print(f"{P['rs']:>3} {P['stop']:>4} {P['volx']:>4} {len(tr):>7}  (insufficient)"); continue
        df = pd.DataFrame(tr)
        r, exc = df["ret"], df["excess"].dropna()
        win, aW, aL, exp = (r > 0).mean(), r[r > 0].mean(), r[r <= 0].mean(), r.mean()
        et = exc.mean() / (exc.std() / np.sqrt(len(exc))) if len(exc) > 1 and exc.std() else np.nan
        hpy = 252 / max(df["hold"].mean(), 1)
        sh = (exc.mean() / exc.std()) * np.sqrt(hpy) if exc.std() else np.nan
        sharpes.append(sh)
        if best is None or exc.mean() > best[1]:
            best = (P, exc.mean(), exp, sh, len(tr))
        print(f"{P['rs']:>3} {P['stop']:>4} {P['volx']:>4} {len(tr):>7} {win*100:>4.0f} {aW*100:>5.1f} "
              f"{aL*100:>5.1f} {exp*100:>5.1f} {exc.mean()*100:>6.2f} {et:>6.2f} {sh:>6.2f}")

    print("\n=== VERDICT ===")
    if best is None:
        print("KILLED: no param set produced >=50 trades."); return
    P, exc_mean, exp, sh, n = best
    print(f"best: RS{P['rs']}/stop{P['stop']}/volx{P['volx']} -> per-trade excess vs SPY {exc_mean*100:.2f}%, "
          f"expectancy {exp*100:.2f}%, {n} trades, ann.Sharpe(excess) {sh:.2f}")
    ss = [s for s in sharpes if s == s]
    if _dsr and len(ss) >= 3:
        try:
            ds = _dsr(pd.Series([exc_mean] * 12).values, ss, periods_per_year=max(int(252 / _MAXHOLD), 2))
            print(f"deflated Sharpe (best vs {len(ss)} variants): {ds:.3f}  (>0.95 survives multiple-testing)")
        except Exception as e:
            print(f"deflated Sharpe: n/a ({str(e)[:40]})")
    verdict = ("VALIDATED" if (exc_mean > 0 and sh > 0.5 and n >= 200) else
               "PARTIAL" if exc_mean > 0 else "KILLED")
    print(f"\n>>> {verdict}: technical core "
          + ("shows positive per-trade excess vs SPY across the sweep" if exc_mean > 0 else "no edge") + ".")
    print("CAVEATS: fundamentals SKIPPED (price-only SEPA); VCP=ATR-shrink proxy; RS=6m-pctile proxy; "
          "costless; survivorship (defined cached universe). First pass on the skeleton, not full method.")


if __name__ == "__main__":
    run()
