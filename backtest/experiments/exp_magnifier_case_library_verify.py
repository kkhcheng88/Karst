"""Phase-3 magnifier case library -- direct yfinance verification helper.

Companion to exp_magnifier_case_library.py (Leg B breadth screen). That screen only covers
tickers already sitting in the two repo price caches (sp500_px.pkl / px_defeatbeta.pkl).
Many Leg-A case-library names (uranium/lithium/space/nuclear-SMR/semicap/crypto-miner/
AI-penny/SPAC-EV tickers named in the hand-built supercycle map, backtest/results/
2026-07-09_magnifier_case_library.md) are NOT in either cache, or their in-cache multiple
was capped by the screen's fixed 24-42 month window. This script downloads full price
history directly via yfinance (period="max", same vendor as backtest/data.py's primary
source) and reports both (a) the same "best 24-42mo window ratio" metric used by the
screen, for apples-to-apples comparison, and (b) lifetime hi/lo/current, since several of
the most extreme moves in this case library (e.g. SNDK's 78.8x in <2yr) fall OUTSIDE the
screen's fixed window and only show up in the lifetime view.

Known data-quality trap this script's output must be read with: several SPAC/reverse-split/
reverse-merger tickers (NKLA, LCID, CHPT, QS, SPCE, WKHS in the batches below) show
implausible pre-merger or pre-split price levels in raw yfinance history -- almost
certainly ticker-reuse (a shell/predecessor entity traded under the same symbol before the
SPAC merger) or a bad tick, NOT a real price. The result file cross-checks these against
independently WebSearch-verified public facts rather than trusting the raw number; this
script's job is only to surface the anomaly, not to silently "fix" it.

Run: python backtest/experiments/exp_magnifier_case_library_verify.py
"""
import sys
import time

import numpy as np
import pandas as pd
import yfinance as yf

# Batch 1: uranium / lithium / rare-earth / space / nuclear-SMR / semicap names referenced
# in the case-library cycles that are absent (or capped) in the two repo price caches.
BATCH_1 = ["ALB", "AMAT", "AXTI", "BLDP", "CCJ", "CLF", "CLS", "CRDO", "DNN", "ETN",
           "FSLR", "LTHM", "MP", "MRVL", "NNE", "NUE", "NVO", "NXE", "OKLO", "PLL",
           "PWR", "RKLB", "SGML", "SMR", "SNDK", "SPWR", "TSM", "UEC", "URG", "UROY",
           "USAR", "UUUU", "WOLF"]

# Batch 2: AI-penny-stock speculative names, crypto miners/AI-datacenter pivots, and the
# SPAC-EV bust cluster (several known ticker-reuse traps -- see module docstring).
BATCH_2 = ["SOUN", "BBAI", "IONQ", "RGTI", "QUBT", "RIOT", "CIFR", "IREN", "MARA",
           "NKLA", "LCID", "RIVN", "CHPT", "QS", "FSR", "GOEV", "RIDE", "CANOO",
           "SPCE", "LAZR", "VLDR", "WKHS", "MULN"]

WIN_MIN, WIN_MAX = 24, 42  # months, matches exp_magnifier_case_library.py


def _best_window_ratio(s):
    m = s.resample("ME").last().dropna()
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
            best_ratio, best_i, best_j = local_max / p[i], i, jlo + int(np.nanargmax(seg))
    if best_i < 0:
        return None
    return {"ratio": round(best_ratio, 2), "start": str(idx[best_i].date()),
            "end": str(idx[best_j].date()), "start_px": round(float(p[best_i]), 3),
            "end_px": round(float(p[best_j]), 3)}


def verify(tickers):
    for tk in dict.fromkeys(tickers):  # dedupe, preserve order
        try:
            df = yf.download(tk, period="max", auto_adjust=False, progress=False)
            if df is None or len(df) == 0:
                print(f"{tk:6} NO DATA")
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            s = df["Close"].dropna()
            s.index = pd.to_datetime(s.index).tz_localize(None)
            lo, hi = s.min(), s.max()
            lo_d, hi_d = s.idxmin(), s.idxmax()
            last_px, last_d = s.iloc[-1], s.index[-1]
            w = _best_window_ratio(s)
            wtxt = (f"win={w['ratio']}x {w['start']}->{w['end']} "
                    f"({w['start_px']}->{w['end_px']})") if w else "win=n/a(<5x or <24mo history)"
            print(f"{tk:6} first={s.index.min().date()} lo={lo:.3f}@{lo_d.date()} "
                  f"hi={hi:.3f}@{hi_d.date()} last={last_px:.3f}@{last_d.date()} "
                  f"from_hi={(last_px / hi - 1) * 100:.1f}%  {wtxt}")
        except Exception as e:
            print(f"{tk:6} ERROR {type(e).__name__}: {str(e)[:100]}")
        sys.stdout.flush()
        time.sleep(0.3)


if __name__ == "__main__":
    print("--- batch 1: uranium/lithium/rare-earth/space/SMR/semicap ---")
    verify(BATCH_1)
    print("--- batch 2: AI-penny/crypto-miner/SPAC-EV (ticker-reuse traps likely) ---")
    verify(BATCH_2)
