"""Phase-3 magnifier case library — Leg B (price screen, breadth complement to Leg A's
hand-built supercycle map in backtest/results/2026-07-09_magnifier_case_library.md).

Question: which US-listed names moved >=5x within any ~3-year window (2010-2024 start),
across the two Karst price caches we already have on disk? This is a BREADTH screen, not a
signal backtest -- no IC/alpha claim. It exists to catch names Leg A's manual cycle map
might have missed, and to make explicit how much of a raw 5x screen is noise (illiquid
micro-caps, ticker-reuse/data artifacts) vs real thematic hits.

Method: resample each ticker's daily close to month-end; for every start/end month pair
with a 24-42 month gap (~3yr, some slack for the "any 3-year window" ask), take
ratio = end/start; keep the ticker's best (max-ratio) window if ratio >= 5.0 AND the
window START falls in [2010-01, 2024-12].

Universe 1: backtest/.insider_data/sp500_px.pkl      -- 505 CURRENT S&P members. Explicit
            survivorship bias: today's constituents are, by construction, survivors.
Universe 2: backtest/.insider_data/px_defeatbeta.pkl  -- 6,769 tickers, insider-Form4-active
            broad universe (small/mid-cap tilt). Better breadth, but still selection-biased
            toward names with SEC Form 4 filers -- not a full historical/delisted universe.

Output: backtest/experiments/_magnifier_case_library_hits.json (sorted by ratio desc).
Run: python backtest/experiments/exp_magnifier_case_library.py
"""
import json
import os
import pickle

import numpy as np
import pandas as pd

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_magnifier_case_library_hits.json")

WIN_MIN, WIN_MAX = 24, 42  # months -- "any ~3yr window", some slack either side
START_LO, START_HI = pd.Timestamp("2010-01-01"), pd.Timestamp("2024-12-31")


def _load_universe(fname):
    with open(os.path.join(_DATA, fname), "rb") as f:
        return pickle.load(f)


def _scan(d, uni_name):
    hits = []
    for tk, s in d.items():
        if s is None or len(s) < 300:
            continue
        s = s.dropna()
        if len(s) < 300:
            continue
        m = s.resample("ME").last().dropna()
        if len(m) < WIN_MIN + 1:
            continue
        p = m.values.astype(float)
        idx = m.index
        n = len(p)
        best_ratio, best_i, best_j = 0.0, -1, -1
        for i in range(n):
            if p[i] <= 0 or not np.isfinite(p[i]):
                continue
            jlo, jhi = i + WIN_MIN, min(i + WIN_MAX, n - 1)
            if jlo > jhi:
                continue
            seg = p[jlo:jhi + 1]
            if len(seg) == 0:
                continue
            local_max = np.nanmax(seg)
            if local_max / p[i] > best_ratio:
                best_ratio = local_max / p[i]
                best_i, best_j = i, jlo + int(np.nanargmax(seg))
        if best_ratio >= 5.0 and best_i >= 0:
            start_date = idx[best_i]
            if START_LO <= start_date <= START_HI:
                hits.append({
                    "ticker": tk, "universe": uni_name, "ratio": round(float(best_ratio), 2),
                    "start_date": str(start_date.date()), "end_date": str(idx[best_j].date()),
                    "start_px": round(float(p[best_i]), 4), "end_px": round(float(p[best_j]), 4),
                })
    return hits


def main():
    all_hits = []
    for fname, uni_name in [("sp500_px.pkl", "sp500_current"), ("px_defeatbeta.pkl", "insider_broad")]:
        d = _load_universe(fname)
        hits = _scan(d, uni_name)
        print(f"{uni_name}: scanned {len(d)} tickers -> {len(hits)} hits >=5x")
        all_hits.extend(hits)
    all_hits.sort(key=lambda h: -h["ratio"])
    with open(_OUT, "w") as f:
        json.dump(all_hits, f, indent=2)
    print(f"total hits: {len(all_hits)} -> {_OUT}")


if __name__ == "__main__":
    main()
