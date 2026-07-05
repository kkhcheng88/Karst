"""Test VCP as a PATTERN (not isolated TA rules) -- does the contraction STRUCTURE add value over a
plain breakout? Operationalises the VCP shape faithfully via a zigzag contraction SEQUENCE, then:

  A/B     : on the same trend-template + breakout candidates, compare
            A = every breakout   vs   B = breakouts whose base is a genuine VCP (structure)
  forward IC: correlate a continuous VCP-SIMILARITY score (how VCP-like the base is) with forward
            excess return -> "is more VCP-ness -> better?" (tests the pattern as a graded structure)

A pattern can only be backtested once OPERATIONALISED; this is the faithful-structure operationalisation
(sequence of contracting pullbacks + volume dry-up), which is still falsifiable -- unlike a human/ML
gestalt (subjective, survivorship, look-ahead). If B ~= A and IC ~= 0 -> the VCP shape adds nothing over
a momentum breakout (it is discretionary dressing). If B > A / IC > 0 -> the structure is real.

Look-ahead-safe (base + zigzag use only bars <= breakout day; entry next bar). Prices: defeatbeta cache.

    python backtest/experiments/exp_vcp_pattern.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
_PIVOT, _BASE_WIN = 30, 65
_HORS = [5, 10, 21, 42, 63]     # VCP is a SWING breakout method -> the edge (if any) is SHORT-horizon;
                                # a monthly / 63d window is misleading. Test the breakout follow-through.


def _universe():
    px = {}
    for f in ["px_defeatbeta.pkl", "sp500_px.pkl"]:
        p = os.path.join(_DATA, f)
        if os.path.exists(p):
            for k, v in pickle.load(open(p, "rb")).items():
                if v is not None and k not in px:
                    s = (v["close"] if isinstance(v, pd.DataFrame) else v)
                    vol = v["volume"] if isinstance(v, pd.DataFrame) and "volume" in v else None
                    px[k] = (s[~s.index.duplicated()].sort_index(),
                             vol[~vol.index.duplicated()].sort_index() if vol is not None else None)
    return px


def _swings(p, w=3):
    """Alternating swing pivots (i, price, 'H'|'L') from local extrema over a +/-w window
    (robust for contraction detection; a pct-zigzag misses tight late pullbacks)."""
    n = len(p)
    raw = []
    for i in range(w, n - w):
        seg = p[i - w:i + w + 1]
        if p[i] == seg.max():
            raw.append((i, p[i], "H"))
        elif p[i] == seg.min():
            raw.append((i, p[i], "L"))
    out = []
    for pv in raw:                                # collapse consecutive same-type -> keep the extreme
        if out and out[-1][2] == pv[2]:
            if (pv[2] == "H" and pv[1] > out[-1][1]) or (pv[2] == "L" and pv[1] < out[-1][1]):
                out[-1] = pv
        else:
            out.append(pv)
    return out


def _vcp(base_close, base_vol):
    """From a base window -> (is_vcp, score 0..1, n_contractions, pivot_high). Structure = a sequence of
    contracting pullbacks (each shallower than the last) + volume dry-up into the tightness."""
    p = base_close.values
    sw = _swings(p, 3)
    depths = []                                   # each H->L pullback >= 2% counts as a contraction
    for k in range(len(sw) - 1):
        if sw[k][2] == "H" and sw[k + 1][2] == "L":
            d = (sw[k][1] - sw[k + 1][1]) / sw[k][1]
            if d >= 0.02:
                depths.append(d)
    if len(depths) < 2:
        return False, 0.0, len(depths), np.nan
    # monotonic tightening: each contraction shallower than the prior
    steps = [depths[i + 1] < depths[i] for i in range(len(depths) - 1)]
    monotonic = np.mean(steps)
    final_tight = 1.0 - min(depths[-1], 1.0)                     # tighter last pullback -> higher
    # volume dry-up: volume in the last third of the base < first third
    dry = np.nan
    if base_vol is not None and base_vol.notna().sum() > 20:
        v = base_vol.values; n = len(v)
        early, late = np.nanmean(v[:n // 3]), np.nanmean(v[-n // 3:])
        dry = np.clip(1 - (late / early), 0, 1) if early and early == early else np.nan
    dryf = dry if dry == dry else 0.5
    score = float(np.clip(monotonic * final_tight * (0.5 + 0.5 * dryf), 0, 1))
    is_vcp = (2 <= len(depths) <= 6) and monotonic >= 0.5 and depths[-1] <= 0.15  # 2-6 tightening, last tight
    pivot_high = max((h for i, h, t in sw if t == "H"), default=np.nan)
    return is_vcp, score, len(depths), pivot_high


def run():
    px = _universe()
    spy = px["SPY"][0]
    sp200 = spy.rolling(200).mean()
    spy_gate = spy.where(spy > sp200)
    recs = []
    n_stocks = 0
    for tk, (s, vol) in px.items():
        if tk == "SPY" or s is None or len(s) < 320:
            continue
        sma50, sma150, sma200 = s.rolling(50).mean(), s.rolling(150).mean(), s.rolling(200).mean()
        hi52, lo52 = s.rolling(252).max(), s.rolling(252).min()
        piv = s.rolling(_PIVOT).max().shift(1)
        trend = ((s > sma150) & (s > sma200) & (sma150 > sma200) & (sma50 > sma150) & (s > sma50)
                 & (sma200 > sma200.shift(21)) & (s >= lo52 * 1.30) & (s >= hi52 * 0.75))
        brk = (s > piv) & (s <= piv * 1.05)
        cand = (trend & brk & spy_gate.reindex(s.index).notna()).values
        idx = s.index
        pos = np.where(cand)[0]
        n_stocks += 1
        last = -1
        for i in pos:
            if i <= last or i + 1 >= len(s) or i < _BASE_WIN + 1:
                continue
            bc = s.iloc[i - _BASE_WIN:i]
            bv = vol.iloc[i - _BASE_WIN:i] if vol is not None else None
            is_vcp, score, ncon, _ = _vcp(bc, bv)
            ei = i + 1
            if ei + _HORS[0] >= len(s):
                continue
            rec = {"tk": tk, "date": idx[i], "is_vcp": is_vcp, "score": score, "ncon": ncon}
            for h in _HORS:
                if ei + h < len(s):
                    fwd = s.iloc[ei + h] / s.iloc[ei] - 1
                    b0, b1 = spy.asof(idx[ei]), spy.asof(idx[ei + h])
                    rec[f"exc{h}"] = fwd - (b1 / b0 - 1) if (b0 == b0 and b1 == b1 and b0 > 0) else np.nan
                else:
                    rec[f"exc{h}"] = np.nan
            recs.append(rec)
            last = i + _HORS[1] // 2
    df = pd.DataFrame(recs)
    print(f"[vcp] scanned {n_stocks} stocks | breakout candidates: {len(df)}")
    print(f"[vcp] contractions: {df['ncon'].value_counts().sort_index().to_dict()} | "
          f"is_vcp: {int(df['is_vcp'].sum())} ({df['is_vcp'].mean()*100:.0f}%)\n")

    # A SWING method -> test the breakout follow-through at SHORT horizons (monthly/63d is misleading)
    print("=== A/B by HORIZON: VCP-structure breakout vs plain breakout, SWING follow-through (excess vs SPY) ===")
    print(f"{'hor':>4} | {'A all breakout':>16} | {'B VCP breakout':>16} | {'not-VCP breakout':>16} | {'IC(score)':>9}")
    print(f"{'':>4} | {'excess% (t) n':>16} | {'excess% (t) n':>16} | {'excess% (t) n':>16} |")

    def stat(sub, col):
        e = sub[col].dropna()
        if len(e) < 20:
            return f"{'n/a':>16}"
        t = e.mean() / (e.std() / np.sqrt(len(e))) if e.std() else float("nan")
        return f"{e.mean()*100:>+5.2f} ({t:>4.1f}) {len(e):>5}"

    for h in _HORS:
        col = f"exc{h}"
        d = df.dropna(subset=[col])
        A, B, N = stat(d, col), stat(d[d.is_vcp], col), stat(d[~d.is_vcp], col)
        dd = d[d.score > 0]
        ic = dd["score"].corr(dd[col], method="spearman") if len(dd) > 50 else float("nan")
        print(f"{h:>3}d | {A} | {B} | {N} | {ic:>+9.3f}")

    print("\nREAD: VCP is a SWING breakout method -> its edge (if any) should show at SHORT horizons (5-21d),"
          " NOT a monthly/63d hold. If B (VCP breakout) > A / not-VCP at 5-21d -> the contraction structure"
          " improves the breakout swing. If B ~ others at every horizon -> the shape adds nothing even for"
          " the swing. CAVEATS: costless; survivorship; base=65d, swings w=3/2% are choices; no fundamentals.")


if __name__ == "__main__":
    run()
