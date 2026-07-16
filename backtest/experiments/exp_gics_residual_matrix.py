"""GICS sector residual seesaw matrix -- full 11x11 SPDR sector pairwise test,
generalising exp_residual_seesaw.py's method -- 2026-07-16.

WHY: exp_residual_seesaw.py found SOXX-IGV (semis vs software, both QQQ
sub-slices) and, as a cross-sector control, XLE-XLK residual correlation
BEYOND a mechanical Monte-Carlo floor (-0.376 real vs a per-pair null). This
script asks: across ALL 55 pairs of the 11 GICS SPDR sector ETFs (vs SPY),
how many pairs show a genuine "money rotates between us, not just index
math" seesaw, once each pair gets its OWN bespoke mechanical floor (not one
generic floor reused for every pair)?

METHOD (identical machinery to exp_residual_seesaw.py, reused by import --
NOT reimplemented):
  1. rolling_residual(r_i, r_SPY, window=252): each sector's daily log
     return regressed on SPY's via a rolling 252d beta; residual = return not
     explained by rolling market beta. 2016-01-01+ for all sectors except
     XLC (2018-06 IPO -- uses its own native start, no arbitrary truncation,
     so its first ~252 obs are the ones consumed by the rolling window, not
     discarded to hit an unrelated 2016 anchor).
  2. Full-period pairwise residual correlation, all C(11,2)=55 pairs.
  3. PER-PAIR mechanical floor: Monte Carlo (500 draws/pair) builds a
     synthetic SPY out of 11 mutually INDEPENDENT random-walk "sectors"
     weighted by documented approximate GICS cap-weights (not live
     holdings), regresses the pair's two synthetic components on the
     synthetic index with the SAME rolling-252d procedure, and repeats. This
     reproduces the "component minus cap-weighted index residuals are
     mechanically anti-correlated even under zero true rotation" identity
     bespoke to each pair's own weight + volatility combination (heavier
     pairs like XLK-XLF get a deeper mechanical floor than light pairs like
     XLU-XLB) -- a refinement on exp_residual_seesaw.py, which used one
     generic "n_other equal-weight buckets" floor per test.
  4. Verdict per pair: real corr < floor p05 (and, more conservatively,
     < floor p01) -- flagged as a candidate genuine seesaw. 55 simultaneous
     tests at p05 implies ~2.75 false positives are EXPECTED by chance alone
     -- see limitations.
  5. Top-3 "furthest beyond floor" pairs get a regime split (SPY>200SMA &
     63d momentum>0 vs not), same format as exp_residual_seesaw.py SECTION B.

Run: PYTHONUTF8=1 python backtest/experiments/exp_gics_residual_matrix.py
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKTEST_DIR = os.path.dirname(_THIS_DIR)
sys.path.insert(0, _BACKTEST_DIR)
sys.path.insert(0, _THIS_DIR)

from data import load  # noqa: E402
import exp_residual_seesaw as base  # noqa: E402  (reused: rolling_residual, residual_corr, etc.)

SINCE = base.SINCE                 # "2016-01-01"
BETA_WINDOW = base.BETA_WINDOW     # 252
CORR_WINDOW = base.CORR_WINDOW     # 63
SMA_WINDOW = base.SMA_WINDOW       # 200
MOM_WINDOW = base.MOM_WINDOW       # 63
N_SIMS = 500                       # per pair (55 pairs x 500 = 27,500 sims)

SECTORS = ["XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]

# Documented APPROXIMATE S&P 500 GICS sector cap-weights (mid-2026 ballpark,
# NOT live holdings data -- see limitations section of the report for how
# much these have drifted historically, esp. XLK ~20% -> ~30%).
WEIGHTS = {
    "XLK": 0.30, "XLF": 0.13, "XLV": 0.12, "XLY": 0.11, "XLC": 0.09,
    "XLI": 0.08, "XLP": 0.06, "XLE": 0.03, "XLU": 0.025, "XLB": 0.02,
    "XLRE": 0.02,
}
MISC_WEIGHT = max(0.0, 1.0 - sum(WEIGHTS.values()))  # ~0.015 leftover bucket


# ---------------------------------------------------------------------------
# Fast numpy-vectorised equivalent of base.rolling_residual, used ONLY inside
# the Monte Carlo (27,500 sims needs speed; verified equivalent to the
# pandas rolling().cov()/.var() formula base.rolling_residual uses -- same
# ddof=1 sample cov/var, same "beta window includes day t" convention).
# ---------------------------------------------------------------------------
def _rolling_sum(cs: np.ndarray, w: int) -> np.ndarray:
    n = len(cs)
    out = np.full(n, np.nan)
    out[w - 1] = cs[w - 1]
    out[w:] = cs[w:] - cs[:-w]
    return out


def rolling_resid_np(idx: np.ndarray, comp: np.ndarray, window: int) -> np.ndarray:
    csx, csy = np.cumsum(idx), np.cumsum(comp)
    csxy, csxx = np.cumsum(idx * comp), np.cumsum(idx * idx)
    sx, sy = _rolling_sum(csx, window), _rolling_sum(csy, window)
    sxy, sxx = _rolling_sum(csxy, window), _rolling_sum(csxx, window)
    w = window
    cov = (sxy - sx * sy / w) / (w - 1)
    var = (sxx - sx * sx / w) / (w - 1)
    beta = cov / var
    return comp - beta * idx


def resid_corr_np(a: np.ndarray, b: np.ndarray):
    mask = ~np.isnan(a) & ~np.isnan(b)
    if mask.sum() < 30:
        return np.nan
    return float(np.corrcoef(a[mask], b[mask])[0, 1])


def simulate_pair_floor(w_a, vol_a, w_b, vol_b, other_weights, other_vols,
                         resid_n_target, window=BETA_WINDOW, n_sims=N_SIMS, seed=0):
    rng = np.random.default_rng(seed)
    n_days = resid_n_target + window + 10
    ow = np.asarray(other_weights)
    ov = np.asarray(other_vols)
    n_other = len(ow)
    corrs = np.empty(n_sims)
    for s in range(n_sims):
        r_a = rng.normal(0.0, vol_a, n_days)
        r_b = rng.normal(0.0, vol_b, n_days)
        r_other = rng.standard_normal((n_days, n_other)) * ov[None, :]
        idx = w_a * r_a + w_b * r_b + r_other @ ow
        resid_a = rolling_resid_np(idx, r_a, window)
        resid_b = rolling_resid_np(idx, r_b, window)
        corrs[s] = resid_corr_np(resid_a, resid_b)
    return corrs[~np.isnan(corrs)]


def _sanity_check_np_vs_pandas():
    """One-off equivalence check: numpy rolling residual vs base.rolling_residual
    (pandas). Prints max abs diff; should be ~0 (float rounding only)."""
    rng = np.random.default_rng(42)
    n = 800
    idx = rng.normal(0, 0.01, n)
    comp = 0.5 * idx + rng.normal(0, 0.01, n)
    resid_np = rolling_resid_np(idx, comp, BETA_WINDOW)
    resid_pd, _ = base.rolling_residual(pd.Series(comp), pd.Series(idx), BETA_WINDOW)
    resid_np_aligned = resid_np[BETA_WINDOW - 1:][: len(resid_pd)]
    diff = np.nanmax(np.abs(resid_np_aligned - resid_pd.values))
    print(f"[sanity] numpy-vs-pandas rolling residual max abs diff: {diff:.2e} (expect ~1e-12)")


# ---------------------------------------------------------------------------
def load_all():
    out = {}
    for t in SECTORS + ["SPY"]:
        df = load(t, adjusted=True, min_rows=50)
        out[t] = df["close"]
        print(f"{t:5} loaded: {df.index[0].date()} -> {df.index[-1].date()}  n={len(df)}")
    return out


def build_residuals(px: dict):
    spy_ret = base.log_ret(px["SPY"], SINCE)
    resids, rets, betas = {}, {}, {}
    for t in SECTORS:
        since_t = None if t == "XLC" else SINCE  # XLC: native 2018-06 start, no truncation
        r = base.log_ret(px[t], since_t)
        resid, beta = base.rolling_residual(r, spy_ret, BETA_WINDOW)
        resids[t] = resid
        rets[t] = r
        betas[t] = beta
        print(f"{t:5} vs SPY: rolling beta mean={beta.mean():.2f} current={beta.iloc[-1]:.2f} "
              f"n_resid={len(resid)}  span {resid.index[0].date()}->{resid.index[-1].date()}")
    return resids, rets, betas


def main():
    _sanity_check_np_vs_pandas()

    print("\n" + "=" * 78)
    print("Loading 11 GICS SPDR sector ETFs + SPY")
    print("=" * 78)
    px = load_all()

    print("\n" + "=" * 78)
    print("Rolling-beta residualisation vs SPY (252d window)")
    print("=" * 78)
    resids, rets, betas = build_residuals(px)
    vol = {t: float(rets[t].std()) for t in SECTORS}
    avg_vol_all = float(np.mean(list(vol.values())))

    pairs = list(itertools.combinations(SECTORS, 2))
    print(f"\n{len(pairs)} pairs total")

    rows = []
    for i, (a, b) in enumerate(pairs):
        c, n = base.residual_corr(resids[a], resids[b])
        others = [t for t in SECTORS if t not in (a, b)]
        other_weights = [WEIGHTS[t] for t in others] + [MISC_WEIGHT]
        other_vols = [vol[t] for t in others] + [avg_vol_all]
        floor_corrs = simulate_pair_floor(
            WEIGHTS[a], vol[a], WEIGHTS[b], vol[b],
            other_weights, other_vols, resid_n_target=n, seed=1000 + i)
        p05 = float(np.percentile(floor_corrs, 5))
        p01 = float(np.percentile(floor_corrs, 1))
        p50 = float(np.percentile(floor_corrs, 50))
        exceed_p05 = c < p05
        exceed_p01 = c < p01
        rows.append({
            "a": a, "b": b, "real": c, "n": n,
            "floor_p01": p01, "floor_p05": p05, "floor_p50": p50,
            "exceed_p05": exceed_p05, "exceed_p01": exceed_p01,
            "margin_p05": p05 - c,  # positive = beyond floor (more negative than p05)
        })
        flag = " <-- BEYOND p05" if exceed_p05 else ""
        print(f"{a}-{b:6} real={c:+.3f}  n={n:5d}  floor[p01={p01:+.3f} p05={p05:+.3f} "
              f"p50={p50:+.3f}]{flag}")

    df_rows = pd.DataFrame(rows).sort_values("margin_p05", ascending=False)

    n_p05 = int(df_rows["exceed_p05"].sum())
    n_p01 = int(df_rows["exceed_p01"].sum())
    print(f"\n{n_p05}/55 pairs beyond p05 floor ; {n_p01}/55 pairs beyond p01 floor")
    print("(expected false positives under pure chance at p05 threshold: "
          f"{0.05*55:.2f} ; at p01: {0.01*55:.2f})")

    top3 = df_rows[df_rows["exceed_p05"]].head(3)
    print("\nTop candidate genuine-seesaw pairs (by margin beyond p05 floor):")
    print(top3[["a", "b", "real", "floor_p05", "margin_p05"]].to_string(index=False))

    # -----------------------------------------------------------------
    # Regime split for top-3 pairs beyond floor
    # -----------------------------------------------------------------
    spy_close = px["SPY"][px["SPY"].index >= SINCE]
    sma200 = spy_close.rolling(SMA_WINDOW).mean()
    mom63 = spy_close.pct_change(MOM_WINDOW)
    uptrend = ((spy_close > sma200) & (mom63 > 0)).dropna()

    regime_results = {}
    for _, row in top3.iterrows():
        a, b = row["a"], row["b"]
        rc = base.rolling_residual_corr(resids[a], resids[b], CORR_WINDOW)
        common = rc.index.intersection(uptrend.index)
        rc_c, reg_c = rc.loc[common], uptrend.loc[common]
        threshold = row["floor_p05"]
        seesaw_on = rc_c <= threshold
        frac_up = float(seesaw_on[reg_c].mean()) if reg_c.sum() > 0 else float("nan")
        frac_down = float(seesaw_on[~reg_c].mean()) if (~reg_c).sum() > 0 else float("nan")
        mean_up = float(rc_c[reg_c].mean()) if reg_c.sum() > 0 else float("nan")
        mean_down = float(rc_c[~reg_c].mean()) if (~reg_c).sum() > 0 else float("nan")
        current_rc = float(rc_c.iloc[-1])
        current_regime = "uptrend" if bool(reg_c.iloc[-1]) else "chop/pullback"
        print(f"\n[{a}-{b}] rolling63 now={current_rc:+.3f} regime={current_regime} "
              f"mean|uptrend={mean_up:+.3f} mean|chop={mean_down:+.3f} "
              f"%on|uptrend={frac_up*100:.1f}% %on|chop={frac_down*100:.1f}%")
        regime_results[(a, b)] = {
            "current_rc": current_rc, "current_regime": current_regime,
            "mean_up": mean_up, "mean_down": mean_down,
            "frac_up": frac_up, "frac_down": frac_down,
        }

    return {
        "df_rows": df_rows, "n_p05": n_p05, "n_p01": n_p01,
        "top3": top3, "regime_results": regime_results,
        "vol": vol, "betas": betas,
    }


if __name__ == "__main__":
    main()
