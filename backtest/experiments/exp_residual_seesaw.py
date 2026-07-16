"""Residual seesaw test: hardware (SOXX) vs software (IGV/MAGS) after removing
common QQQ beta -- 2026-07-16.

USER HYPOTHESIS: SOXX (semis) and IGV/MAGS (software/Mag7) show ~zero long-run
NOMINAL correlation because a shared uptrend (beta to QQQ) masks the underlying
picture. Strip out the common factor (regress each on QQQ, keep the residual =
"idiosyncratic" return not explained by beta) and the residuals should be
NEGATIVELY correlated -- money rotating between hardware and software shows up
as a seesaw once the shared trend is removed. User believes this generalizes
across US sectors, but is strongest for hardware/software specifically.

THE STATISTICAL TRAP THIS SCRIPT IS BUILT TO CONTROL FOR (its core contribution):
SOXX and IGV are BOTH constituents of QQQ. "Component minus index" residuals are
MECHANICALLY, ARITHMETICALLY prone to some negative correlation even with ZERO
real rotation, because of the accounting identity index = sum(w_i * component_i)
-- if one constituent's residual is unusually positive, the weighted-average
identity puts some downward pressure on the others' residuals purely by
construction. So a naive "residual correlation is negative -> seesaw confirmed"
reading is not admissible on its own. This script instead:

  1. MECHANICAL FLOOR (Monte Carlo): builds a synthetic index out of N mutually
     INDEPENDENT random-walk "components" weighted like real sectors (semis ~20%,
     software ~15%, rest ~65% split across other components), regresses each
     component on the synthetic index with the SAME rolling-252d-beta procedure
     used on real data, and measures the resulting residual correlation. Repeated
     1000x -> a null distribution of "how negative does pure mechanics make this,
     with ZERO true rotation baked in by design."
  2. REAL TEST: SOXX/IGV/MAGS/CIBR each regressed on QQQ (rolling 252d beta),
     pairwise residual correlation, full period + rolling 63d. 2016+ (MAGS from
     its 2023 inception).
  3. VERDICT: is the real residual correlation MORE NEGATIVE than the mechanical
     null distribution would produce by chance (e.g. below its 5th percentile)?
     Only that counts as evidence of a genuine seesaw, not just accounting.
  4. REGIME SPLIT: does the (SOXX,IGV) rolling residual correlation only go
     strongly negative when QQQ is chopping/pulling back (price<200SMA or 63d
     momentum<=0), vs staying near the mechanical floor during clean uptrends?
     Also: is the seesaw "on" right now, and what % of history has it been on?
  5. CROSS-SECTOR CONTROL: repeat the exact same real-vs-null test on two SPY
     sector pairs from DIFFERENT parents -- XLE vs XLK, XLV vs XLF -- to see
     whether hardware/software is special or this is a universal artifact of
     any two sub-sectors of any cap-weighted index.
  6. PRACTICAL READ: one honest line on what this would mean IF it holds --
     this experiment only tests EXISTENCE of the phenomenon, not whether a
     tradeable timing signal can actually catch it.

Run: PYTHONUTF8=1 python backtest/experiments/exp_residual_seesaw.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load

SINCE = "2016-01-01"
BETA_WINDOW = 252      # rolling beta window (~1 trading year)
CORR_WINDOW = 63        # rolling residual-correlation window (~1 quarter)
N_SIMS = 1000
SMA_WINDOW = 200
MOM_WINDOW = 63

TICKERS = ["SOXX", "IGV", "MAGS", "CIBR", "QQQ", "SPY", "XLE", "XLK", "XLV", "XLF"]


def load_all():
    out = {}
    for t in TICKERS:
        try:
            df = load(t, adjusted=True, min_rows=50)
            out[t] = df["close"]
            print(f"{t:5} loaded: {df.index[0].date()} -> {df.index[-1].date()}  n={len(df)}")
        except Exception as e:
            print(f"{t:5} SKIP: {str(e)[:60]}")
    return out


def log_ret(px: pd.Series, since: str | None = None) -> pd.Series:
    r = np.log(px).diff().dropna()
    if since:
        r = r[r.index >= since]
    return r


# ---------------------------------------------------------------------------
# Rolling-beta residualization -- shared by the REAL test and the NULL simulation
# so both sides use an identical procedure (apples-to-apples).
# ---------------------------------------------------------------------------
def rolling_residual(r_i: pd.Series, r_idx: pd.Series, window: int = BETA_WINDOW):
    """Residual of r_i after removing a ROLLING beta on r_idx.

    beta_t = Cov(r_i, r_idx; trailing `window` days incl. t) / Var(r_idx; same
    window). Note: beta_t's window includes day t's own return, a standard
    simplification in this kind of rolling-beta study; it introduces a small
    same-day look-ahead in the beta estimate (not in the residual sign/timing
    itself). Documented, not treated as trade-grade.
    """
    d = pd.DataFrame({"i": r_i, "x": r_idx}).dropna()
    cov = d["i"].rolling(window).cov(d["x"])
    var = d["x"].rolling(window).var()
    beta = cov / var
    resid = (d["i"] - beta * d["x"]).dropna()
    return resid, beta.dropna()


def residual_corr(resid_a: pd.Series, resid_b: pd.Series):
    common = resid_a.index.intersection(resid_b.index)
    if len(common) < 30:
        return np.nan, len(common)
    return float(resid_a.loc[common].corr(resid_b.loc[common])), len(common)


def rolling_residual_corr(resid_a: pd.Series, resid_b: pd.Series, window: int = CORR_WINDOW):
    common = resid_a.index.intersection(resid_b.index)
    a, b = resid_a.loc[common], resid_b.loc[common]
    return a.rolling(window).corr(b).dropna()


# ---------------------------------------------------------------------------
# 1. Mechanical floor: Monte Carlo null distribution of residual correlation
#    from the weighted-index accounting identity ALONE (zero true rotation --
#    components are independent random walks by construction).
# ---------------------------------------------------------------------------
def simulate_null_floor(w_a, w_b, vol_a, vol_b, vol_other, resid_n_target,
                         window: int = BETA_WINDOW, n_sims: int = N_SIMS,
                         n_other: int = 8, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n_days = resid_n_target + window + 10
    w_rest = max(1.0 - w_a - w_b, 0.0)
    ow = np.full(n_other, w_rest / n_other)
    corrs = np.empty(n_sims)
    for s in range(n_sims):
        r_a = pd.Series(rng.normal(0, vol_a, n_days))
        r_b = pd.Series(rng.normal(0, vol_b, n_days))
        r_other = rng.normal(0, vol_other, (n_days, n_other))
        idx = pd.Series(w_a * r_a.values + w_b * r_b.values + r_other @ ow)
        resid_a, _ = rolling_residual(r_a, idx, window)
        resid_b, _ = rolling_residual(r_b, idx, window)
        c, _ = residual_corr(resid_a, resid_b)
        corrs[s] = c
    return corrs[~np.isnan(corrs)]


def floor_summary(corrs: np.ndarray) -> dict:
    return {
        "n_sims": int(len(corrs)),
        "p05": float(np.percentile(corrs, 5)),
        "p25": float(np.percentile(corrs, 25)),
        "p50": float(np.percentile(corrs, 50)),
        "p75": float(np.percentile(corrs, 75)),
        "p95": float(np.percentile(corrs, 95)),
        "mean": float(np.mean(corrs)),
    }


def percentile_of_real(corrs: np.ndarray, real_value: float) -> float:
    """% of null draws BELOW the real value. Low % -> real value sits in the
    left (very negative) tail of the null -> more negative than mechanics alone
    would produce by chance -> evidence of a genuine effect, not just the
    weighted-index identity."""
    if np.isnan(real_value):
        return float("nan")
    return float((corrs < real_value).mean() * 100)


def print_floor_vs_real(label: str, real_value: float, real_n: int, corrs: np.ndarray):
    fs = floor_summary(corrs)
    pct = percentile_of_real(corrs, real_value)
    print(f"\n{label}")
    print(f"  REAL full-period residual corr: {real_value:+.3f}  (n={real_n})")
    print(f"  MECHANICAL null (n_sims={fs['n_sims']}): "
          f"p05={fs['p05']:+.3f}  p25={fs['p25']:+.3f}  p50={fs['p50']:+.3f}  "
          f"p75={fs['p75']:+.3f}  p95={fs['p95']:+.3f}  mean={fs['mean']:+.3f}")
    verdict = "BEYOND mechanical floor (genuine)" if pct <= 10 else (
        "within mechanical floor (accounting alone explains it)" if pct >= 25 else
        "borderline -- partially beyond floor")
    print(f"  real value is more negative than {100-pct:.0f}% of null draws -> {verdict}")
    return {"real": real_value, "real_n": real_n, "floor": fs, "pct_below": pct, "verdict": verdict}


# ---------------------------------------------------------------------------
# 2+3. Hardware vs software/Mag7/cyber -- real residualization + verdict
# ---------------------------------------------------------------------------
def section_hw_sw(px: dict):
    print("\n" + "=" * 78)
    print("SECTION A -- hardware (SOXX) vs software (IGV/MAGS/CIBR): real residual")
    print("correlation vs the mechanical floor")
    print("=" * 78)

    qqq_ret = log_ret(px["QQQ"], SINCE)
    names = [t for t in ["SOXX", "IGV", "MAGS", "CIBR"] if t in px]
    resids = {}
    for t in names:
        r = log_ret(px[t], SINCE)
        resid, beta = rolling_residual(r, qqq_ret, BETA_WINDOW)
        resids[t] = resid
        print(f"{t:5} vs QQQ: rolling beta mean={beta.mean():.2f} current={beta.iloc[-1]:.2f} "
              f"n_resid={len(resid)}  span {resid.index[0].date()}->{resid.index[-1].date()}")

    pairs = [("SOXX", "IGV"), ("SOXX", "MAGS"), ("SOXX", "CIBR"), ("IGV", "MAGS")]
    print("\nreal residual correlation, full period + rolling 63d snapshot:")
    print(f"{'pair':16}{'full corr':>10}{'n':>7}{'roll mean':>11}{'roll now':>10}")
    pair_stats = {}
    for a, b in pairs:
        if a not in resids or b not in resids:
            continue
        c, n = residual_corr(resids[a], resids[b])
        rc = rolling_residual_corr(resids[a], resids[b], CORR_WINDOW)
        pair_stats[(a, b)] = {"full": c, "n": n, "rolling": rc}
        rmean = float(rc.mean()) if len(rc) else float("nan")
        rnow = float(rc.iloc[-1]) if len(rc) else float("nan")
        print(f"{a}-{b:12}{c:10.3f}{n:7d}{rmean:11.3f}{rnow:10.3f}")

    # Mechanical floor -- ONLY for (SOXX, IGV): these are the one pair here that
    # map cleanly onto two DISJOINT, well-defined QQQ sub-weights (semis vs
    # application software, no overlapping names). MAGS (mega-cap, overlaps SOXX
    # via NVDA/AAPL) and CIBR (small, mixed hw/sw names) don't have a clean
    # "two independent QQQ buckets" weight assumption, so no bespoke null is
    # built for them -- they're reported as real-data-only supporting context.
    vol = {t: float(log_ret(px[t], SINCE).std()) for t in ["SOXX", "IGV", "XLE", "XLK", "XLV", "XLF"]}
    vol_other = float(np.mean([vol["XLE"], vol["XLK"], vol["XLV"], vol["XLF"]]))
    real_c, real_n = pair_stats[("SOXX", "IGV")]["full"], pair_stats[("SOXX", "IGV")]["n"]
    floor_soxx_igv = simulate_null_floor(
        w_a=0.20, w_b=0.15, vol_a=vol["SOXX"], vol_b=vol["IGV"], vol_other=vol_other,
        resid_n_target=real_n, seed=1)
    verdict = print_floor_vs_real(
        "SOXX (semis, ~20% of QQQ) vs IGV (software, ~15% of QQQ) -- documented "
        "approximate Nasdaq-100 sub-weights, not live holdings data:",
        real_c, real_n, floor_soxx_igv)

    print("\n[judgement] SOXX-IGV real residual correlation vs mechanical floor: "
          f"{verdict['verdict']}. Secondary reads (SOXX-MAGS, SOXX-CIBR, IGV-MAGS) "
          "shown for context only (no clean disjoint-weight null available).")
    return {"resids": resids, "pair_stats": pair_stats, "floor_soxx_igv": floor_soxx_igv,
            "verdict_soxx_igv": verdict}


# ---------------------------------------------------------------------------
# 4. Regime split -- does the seesaw only engage during QQQ chop/pullback?
# ---------------------------------------------------------------------------
def section_regime(px: dict, resid_soxx: pd.Series, resid_igv: pd.Series, floor_corrs: np.ndarray):
    print("\n" + "=" * 78)
    print("SECTION B -- regime split: is the SOXX/IGV seesaw only 'on' during")
    print("QQQ chop/pullback, and is it on right now?")
    print("=" * 78)

    qqq_close = px["QQQ"][px["QQQ"].index >= SINCE]
    sma200 = qqq_close.rolling(SMA_WINDOW).mean()
    mom63 = qqq_close.pct_change(MOM_WINDOW)
    uptrend = ((qqq_close > sma200) & (mom63 > 0)).dropna()

    rc = rolling_residual_corr(resid_soxx, resid_igv, CORR_WINDOW)
    common = rc.index.intersection(uptrend.index)
    rc_c, reg_c = rc.loc[common], uptrend.loc[common]

    threshold = floor_summary(floor_corrs)["p05"]
    seesaw_on = rc_c <= threshold

    frac_on_overall = float(seesaw_on.mean())
    frac_on_up = float(seesaw_on[reg_c].mean()) if reg_c.sum() > 0 else float("nan")
    frac_on_down = float(seesaw_on[~reg_c].mean()) if (~reg_c).sum() > 0 else float("nan")
    mean_corr_up = float(rc_c[reg_c].mean()) if reg_c.sum() > 0 else float("nan")
    mean_corr_down = float(rc_c[~reg_c].mean()) if (~reg_c).sum() > 0 else float("nan")

    current_rc = float(rc_c.iloc[-1])
    current_regime = "uptrend (price>200SMA & 63d mom>0)" if bool(reg_c.iloc[-1]) else "chop/pullback"
    current_on = bool(seesaw_on.iloc[-1])

    print(f"seesaw-on threshold (mechanical floor 5th pct): rolling 63d residual corr <= {threshold:+.3f}")
    print(f"n obs with regime label: {len(common)}  "
          f"(uptrend days: {int(reg_c.sum())}, chop/pullback days: {int((~reg_c).sum())})")
    print(f"\nmean rolling residual corr | uptrend regime  : {mean_corr_up:+.3f}")
    print(f"mean rolling residual corr | chop/pullback regime: {mean_corr_down:+.3f}")
    print(f"\n% of days seesaw 'on' (rolling corr <= floor p05):")
    print(f"  overall        : {frac_on_overall*100:5.1f}%")
    print(f"  during uptrend : {frac_on_up*100:5.1f}%")
    print(f"  during chop/pullback: {frac_on_down*100:5.1f}%")
    print(f"\nRIGHT NOW: rolling 63d residual corr = {current_rc:+.3f}  "
          f"regime = {current_regime}  seesaw currently {'ON' if current_on else 'off'}")

    if frac_on_down > frac_on_up * 1.3:
        j = "seesaw engages materially more during chop/pullback -- regime-dependent, as hypothesised."
    elif abs(frac_on_down - frac_on_up) < 0.05:
        j = "seesaw is roughly equally 'on' in both regimes -- not clearly regime-gated."
    else:
        j = "seesaw shows a mild regime tilt, not a clean on/off switch."
    print(f"\n[judgement] {j}")

    return {"threshold": threshold, "frac_on_overall": frac_on_overall,
            "frac_on_up": frac_on_up, "frac_on_down": frac_on_down,
            "mean_corr_up": mean_corr_up, "mean_corr_down": mean_corr_down,
            "current_rc": current_rc, "current_regime": current_regime,
            "current_on": current_on, "judgement": j}


# ---------------------------------------------------------------------------
# 5. Cross-sector control -- is hw/sw special, or a universal artifact?
# ---------------------------------------------------------------------------
def section_cross_sector(px: dict, hw_sw_verdict: dict):
    print("\n" + "=" * 78)
    print("SECTION C -- cross-sector control: XLE vs XLK, XLV vs XLF (vs SPY)")
    print("Is hardware/software special, or does every sector pair show this?")
    print("=" * 78)

    spy_ret = log_ret(px["SPY"], SINCE)
    names = ["XLE", "XLK", "XLV", "XLF"]
    resids = {}
    for t in names:
        r = log_ret(px[t], SINCE)
        resid, beta = rolling_residual(r, spy_ret, BETA_WINDOW)
        resids[t] = resid
        print(f"{t:5} vs SPY: rolling beta mean={beta.mean():.2f} current={beta.iloc[-1]:.2f} n_resid={len(resid)}")

    vol = {t: float(log_ret(px[t], SINCE).std()) for t in names}

    results = {}
    # documented approximate S&P 500 sector cap-weights (rough, not live holdings)
    configs = [
        ("XLE", "XLK", 0.03, 0.30, ["XLV", "XLF"]),
        ("XLV", "XLF", 0.12, 0.13, ["XLE", "XLK"]),
    ]
    for i, (a, b, wa, wb, other_pool) in enumerate(configs, start=2):
        c, n = residual_corr(resids[a], resids[b])
        rc = rolling_residual_corr(resids[a], resids[b], CORR_WINDOW)
        vol_other = float(np.mean([vol[t] for t in other_pool]))
        floor_corrs = simulate_null_floor(
            w_a=wa, w_b=wb, vol_a=vol[a], vol_b=vol[b], vol_other=vol_other,
            resid_n_target=n, seed=i)
        v = print_floor_vs_real(
            f"{a} (~{wa*100:.0f}% of SPY) vs {b} (~{wb*100:.0f}% of SPY):", c, n, floor_corrs)
        v["rolling_mean"] = float(rc.mean()) if len(rc) else float("nan")
        v["rolling_now"] = float(rc.iloc[-1]) if len(rc) else float("nan")
        results[(a, b)] = v

    hw_sw_pct = hw_sw_verdict["pct_below"]
    others_pct = [v["pct_below"] for v in results.values()]
    if hw_sw_pct <= min(others_pct) - 10:
        j = ("SOXX/IGV sits further into the null's left tail than either cross-sector control pair -- "
             "hardware/software looks like a genuinely stronger seesaw, not just 'any two sub-sectors do this'.")
    elif hw_sw_pct >= max(others_pct) + 10:
        j = "cross-sector control pairs show an equal-or-stronger effect -- this looks like a generic index-math artifact, not something special to hardware/software."
    else:
        j = "hardware/software is in the same ballpark as the cross-sector controls -- some rotation is a general feature of sub-sector residuals, not unique to hw/sw."
    print(f"\n[judgement] {j}")
    results["judgement"] = j
    return results


def run():
    px = load_all()
    required = {"SOXX", "IGV", "QQQ", "SPY", "XLE", "XLK", "XLV", "XLF"}
    missing = required - set(px)
    if missing:
        print(f"missing required tickers {missing} -- abort.")
        return

    a = section_hw_sw(px)
    b = section_regime(px, a["resids"]["SOXX"], a["resids"]["IGV"], a["floor_soxx_igv"])
    c = section_cross_sector(px, a["verdict_soxx_igv"])

    print("\n" + "=" * 78)
    print("DONE")
    print("=" * 78)
    return a, b, c


if __name__ == "__main__":
    run()
