"""Buyback yield / net share issuance — MARKET-CAP TIER extension of exp_buyback_capital_allocation.py.

The original script (exp_buyback_capital_allocation.py) tested trailing-4Q buyback_yield /
net_issuance vs forward SPY-excess on the top-10 US holdings of all 11 SPDR sector ETFs (~90-110
names) — a MEGA/LARGE-CAP-TILTED universe (SPDR top-10 holdings are, definitionally, the biggest
names in each sector). This script asks: does the same factor hold across the FULL market-cap
spectrum (micro/small/mid/large), using the repo's broad ~6700-ticker pool
(backtest/.insider_data/px_defeatbeta.pkl / mktcap_defeatbeta.pkl — the same pool used by
exp_institutional_attention_proxy.py and exp_families_mktcap_tiers.py)?

Reuses BC (exp_buyback_capital_allocation) helpers verbatim: _cf_rows, _pooled_ic, _fm_ic,
_quintile_spread, _fwd_excess, HORIZONS, MIN_NAMES, MIN_DATES. Does NOT reuse BC's own universe
(SPDR top-10) or BC's own px/mcap cache (buyback_cap_alloc.pkl) — this script sources price and
market cap from the broad px_defeatbeta.pkl / mktcap_defeatbeta.pkl dicts instead, and pulls its
OWN quarterly_cash_flow data (cached to buyback_cf_tiers.pkl) for a NEW, broader candidate sample.

LAG_DAYS = 100 (WIDER than the original's 75) — WHY:
  SEC filing deadlines depend on filer status (public float, not just market cap, but market cap is
  the operative proxy available here):
    - Large Accelerated Filer (float >= $700M): 10-K due 60 days after FYE, 10-Q due 40 days.
    - Accelerated Filer ($75M-$700M float):     10-K due 75 days,           10-Q due 40 days.
    - Non-Accelerated Filer (<$75M float, common among micro-caps and many small-caps):
                                                  10-K due 90 days,           10-Q due 45 days.
  The original script's LAG_DAYS=75 was sized for large-accelerated filers only (60d 10-K + buffer).
  Extending the SAME 75-day assumption down into micro/small-cap tiers risks a real look-ahead bug:
  treating trailing-4Q cash-flow data as "known" to the market before a slow non-accelerated filer
  has actually filed it. LAG_DAYS=100 (90-day worst-case 10-K deadline + 10-day buffer) is the safe
  uniform choice. It is applied to ALL FOUR TIERS (including large-cap) so the cross-tier comparison
  is apples-to-apples on methodology — a tier difference in results is not confounded by using a
  different lag for different tiers.

Point-in-time discipline (mirrors BC.build_panel exactly, see that file for the full mirror/
increment/horizon writeup): signal = trailing 4 quarters of cash-flow rows keyed by period-end
q_end; known_date = q_end + LAG_DAYS calendar days; forward-return window starts at the first
trading day ON OR AFTER known_date (px.index.searchsorted, never before); denominator (market cap)
is point-in-time mcap.asof(known_date) — the SAME point-in-time value used to assign this row's
DYNAMIC tier (a name can cross a tier boundary over the ~2022-2026 sample window, so tiering is
done per-observation at known_date, not from the ticker's sampling-time median market cap).

Universe / sampling: candidate tickers are drawn from the SAME broad pool as
exp_institutional_attention_proxy.build_sample_universe() / exp_families_mktcap_tiers.py — tickers
with a usable point-in-time market-cap series and >=500 daily price rows, bucketed into 4 tiers by
MEDIAN market cap over their full history (TIERS_BINS/TIERS_LABELS below, identical to those two
scripts), then a SYSTEMATIC evenly-spaced sample (not random, not alphabetical-first-N) of up to
N_PER_TIER tickers per tier. This median-mcap bucketing is ONLY used to pick the candidate sample;
the actual reported tier for every panel row is the DYNAMIC point-in-time tier (see above).

Run: python backtest/experiments/exp_buyback_mktcap_tier.py
"""
from __future__ import annotations

import contextlib
import io
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_buyback_capital_allocation as BC  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    from defeatbeta_api.data.ticker import Ticker

TIERS_BINS = [0, 3e8, 2e9, 1e10, np.inf]
TIERS_LABELS = ["micro <$300M", "small $300M-2B", "mid $2B-10B", "large >$10B"]
N_PER_TIER = 150               # see run() docstring note if this was reduced at run time
LAG_DAYS = 100                 # WIDER than BC's 75 — see module docstring
_CF_CACHE = os.path.join(BC._DATA, "buyback_cf_tiers.pkl")


def build_sample_universe(px, mc, n_per_tier):
    """Median-market-cap tiering of the broad pool -> systematic evenly-spaced sample per tier.
    Mirrors exp_institutional_attention_proxy.build_sample_universe() exactly."""
    rows = []
    for t, s in mc.items():
        if not isinstance(s, pd.Series) or s.dropna().empty:
            continue
        p = px.get(t)
        if not isinstance(p, pd.Series) or len(p) < 500:
            continue
        med = s.dropna().median()
        rows.append((t, med))
    df = pd.DataFrame(rows, columns=["t", "medmc"]).sort_values("t")
    df["tier"] = pd.cut(df["medmc"], bins=TIERS_BINS, labels=TIERS_LABELS)
    chosen = {}
    for lab in TIERS_LABELS:
        sub = df[df["tier"] == lab]["t"].tolist()
        if len(sub) <= n_per_tier:
            pick = sub
        else:
            step = len(sub) / n_per_tier
            idx = [int(i * step) for i in range(n_per_tier)]
            pick = [sub[i] for i in idx]
        chosen[lab] = pick
    return chosen, df


def _pull_cf_one(tk):
    out = {"pulled_ok": False, "rep": None, "nci": None, "gross_iss": None, "csp": None}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cf = Ticker(tk).quarterly_cash_flow()
        out["pulled_ok"] = True
        out["rep"], out["nci"], out["gross_iss"], out["csp"] = BC._cf_rows(cf)
    except Exception:
        pass
    return out


def _load_cf_cache(tickers):
    """Disk-cached (pickle) pull of quarterly_cash_flow for the candidate sample. Self-heals
    missing keys. Saves every 25 tickers so an interrupted run can resume without redoing
    completed pulls (mirrors BC._load_universe_data's pattern)."""
    cache = {}
    if os.path.exists(_CF_CACHE):
        try:
            cache = pickle.load(open(_CF_CACHE, "rb"))
        except Exception:
            cache = {}
    need = [t for t in tickers if cache.get(t) is None]
    print(f"[cf-pull] {len(cache)} cached already, {len(need)} to pull ...")
    t0 = time.time()
    for i, t in enumerate(need):
        try:
            cache[t] = _pull_cf_one(t)
        except Exception:
            cache[t] = {"pulled_ok": False, "rep": None, "nci": None, "gross_iss": None, "csp": None}
        if i % 25 == 24:
            pickle.dump(cache, open(_CF_CACHE, "wb"))
            print(f"  ...{i + 1}/{len(need)} pulled, elapsed={time.time() - t0:.0f}s")
    pickle.dump(cache, open(_CF_CACHE, "wb"))
    print(f"[cf-pull] done, elapsed={time.time() - t0:.0f}s")
    return cache


def build_panel(cand_by_tier, cf_cache, px, mc):
    """Long DataFrame of point-in-time name-quarter observations, tagged with BOTH the
    candidate-sampling tier (cand_tier) and the dynamic point-in-time tier (dyn_tier)."""
    spy = px.get("SPY")
    if spy is not None:
        spy = spy[~spy.index.duplicated(keep="last")].sort_index()
    rows = []
    attrition = {lab: {"n_sampled": 0, "n_pulled_ok": 0, "n_both_rows": 0, "n_usable_pxmc": 0}
                 for lab in TIERS_LABELS}
    for lab, tickers in cand_by_tier.items():
        attrition[lab]["n_sampled"] = len(tickers)
        for tk in tickers:
            d = cf_cache.get(tk)
            if not d:
                continue
            if d.get("pulled_ok"):
                attrition[lab]["n_pulled_ok"] += 1
            rep, nci = d.get("rep"), d.get("nci")
            if rep is None or nci is None:
                continue
            attrition[lab]["n_both_rows"] += 1
            p, m = px.get(tk), mc.get(tk)
            if not isinstance(p, pd.Series) or not isinstance(m, pd.Series):
                continue
            p = p[~p.index.duplicated(keep="last")].sort_index()
            m = m[~m.index.duplicated(keep="last")].sort_index()
            quarters = sorted(q for q in rep if q in nci)
            got_one = False
            for i in range(3, len(quarters)):
                win = quarters[i - 3:i + 1]
                rep4 = [abs(rep[q]) for q in win]
                nci4 = [nci[q] for q in win]
                if any(pd.isna(x) for x in rep4) or any(pd.isna(x) for x in nci4):
                    continue
                q_end = quarters[i]
                known = q_end + pd.Timedelta(days=LAG_DAYS)
                mc_val = m.asof(known)                     # point-in-time cap at known-date
                if pd.isna(mc_val) or mc_val <= 0 or len(p) < 30:
                    continue
                dyn_tier = pd.cut([mc_val], bins=TIERS_BINS, labels=TIERS_LABELS)[0]
                if pd.isna(dyn_tier):
                    continue
                row = {"sym": tk, "cand_tier": lab, "dyn_tier": dyn_tier, "q_end": q_end,
                       "known": known, "buyback_yield": sum(rep4) / mc_val,
                       "net_issuance": sum(nci4) / mc_val}
                for h in BC.HORIZONS:
                    row[f"f{h}"] = BC._fwd_excess(p, spy, known, h)
                rows.append(row)
                got_one = True
            if got_one:
                attrition[lab]["n_usable_pxmc"] += 1
    df = pd.DataFrame(rows)
    for lab in TIERS_LABELS:
        attrition[lab]["n_obs_cand_tier"] = int((df["cand_tier"] == lab).sum()) if not df.empty else 0
        attrition[lab]["n_obs_dyn_tier"] = int((df["dyn_tier"] == lab).sum()) if not df.empty else 0
    return df, attrition


def print_attrition(attrition, df):
    print("\n" + "=" * 100)
    print("ATTRITION TABLE (rows = CANDIDATE-SAMPLING tier, i.e. which tier we went looking in)")
    print("=" * 100)
    print(f"  {'tier':16} {'n_sampled':>10} {'pulled_ok':>10} {'rep+nci':>8} "
          f"{'usable px/mc':>13} {'n_obs(cand_tier)':>16} {'n_obs(dyn_tier)':>16}")
    tot = {k: 0 for k in ("n_sampled", "n_pulled_ok", "n_both_rows", "n_usable_pxmc", "n_obs_cand_tier")}
    for lab in TIERS_LABELS:
        a = attrition[lab]
        print(f"  {lab:16} {a['n_sampled']:>10} {a['n_pulled_ok']:>10} {a['n_both_rows']:>8} "
              f"{a['n_usable_pxmc']:>13} {a['n_obs_cand_tier']:>16} {a['n_obs_dyn_tier']:>16}")
        for k in tot:
            tot[k] += a[k]
    print(f"  {'TOTAL':16} {tot['n_sampled']:>10} {tot['n_pulled_ok']:>10} {tot['n_both_rows']:>8} "
          f"{tot['n_usable_pxmc']:>13} {tot['n_obs_cand_tier']:>16} {len(df):>16}")
    if not df.empty:
        match = (df["cand_tier"] == df["dyn_tier"]).mean()
        print(f"\n  tier drift: {match * 100:.1f}% of the {len(df)} panel obs have dyn_tier == "
              f"cand_tier (candidate-sampling used ticker-level median market cap over its whole "
              f"history; dyn_tier is the point-in-time market cap AT THIS OBSERVATION's known_date "
              f"— the rest drifted across a tier boundary between the two).")
        print("\n  dyn_tier distribution (cross-tab vs cand_tier), obs count:")
        ct = pd.crosstab(df["cand_tier"], df["dyn_tier"])
        print(ct.to_string())


def print_tier_metrics(df):
    print("\n" + "=" * 100)
    print("METRICS BY DYNAMIC TIER (point-in-time market-cap tier at each obs's known_date) "
          "+ ALL TIERS POOLED")
    print("=" * 100)
    for sig in ("buyback_yield", "net_issuance"):
        print(f"\n########## {sig}  (HIGH=more buybacks, expect +) ##########" if sig == "buyback_yield"
              else f"\n########## {sig}  (HIGH=more dilution, expect -) ##########")
        for lab in TIERS_LABELS + ["ALL TIERS POOLED"]:
            sub = df if lab == "ALL TIERS POOLED" else df[df["dyn_tier"] == lab]
            nnm = sub["sym"].nunique() if not sub.empty else 0
            nobs_all = len(sub[["buyback_yield"] + [f"f{h}" for h in BC.HORIZONS]].dropna()) if not sub.empty else 0
            print(f"\n--- {lab}  (n_names={nnm}, n_obs_any_horizon={nobs_all}) ---")
            if sub.empty:
                print("  EMPTY")
                continue
            print(f"  {'hor':>4} | {'FM-IC':>7} {'FM-t':>6} {'hit':>5} {'nDt':>4} | "
                  f"{'poolIC':>7} {'pool-t':>6} {'nObs':>5} | {'Q5-Q1':>7} {'sprd-t':>6}  "
                  f"quintile means (Q1..Q5) %")
            for h in BC.HORIZONS:
                fm = BC._fm_ic(sub, sig, h)
                pl = BC._pooled_ic(sub, sig, h)
                qs = BC._quintile_spread(sub, sig, h)
                fm_s = (f"{fm['mean']:+.3f} {fm['t']:>6.2f} {fm['hit']:>4.0%} {fm['n_dates']:>4}"
                        if fm else "   (insufficient) ")
                pl_s = f"{pl['r']:+.3f} {pl['t']:>6.2f} {pl['n']:>5}" if pl else "  (insuff)   "
                if qs:
                    qm = " ".join(f"{m * 100:>6.1f}" for m in qs["means"])
                    qs_s = f"{qs['spread'] * 100:>+6.1f}% {qs['t']:>6.2f}  {qm}"
                else:
                    qs_s = "  (insufficient)"
                print(f"  {h:>3}d | {fm_s} | {pl_s} | {qs_s}")


def run():
    t_start = time.time()
    print("[load] px_defeatbeta.pkl / mktcap_defeatbeta.pkl ...")
    px = pickle.load(open(os.path.join(BC._DATA, "px_defeatbeta.pkl"), "rb"))
    mc = pickle.load(open(os.path.join(BC._DATA, "mktcap_defeatbeta.pkl"), "rb"))
    print(f"[load] px={len(px)} tickers, mc={len(mc)} tickers, 'SPY' in px={'SPY' in px}, "
          f"'SPY' in mc={'SPY' in mc}")

    n_per_tier = N_PER_TIER
    cand_by_tier, cand_df = build_sample_universe(px, mc, n_per_tier)
    print(f"\n[universe] N_PER_TIER={n_per_tier}  LAG_DAYS={LAG_DAYS}")
    for lab in TIERS_LABELS:
        n_elig = int((cand_df["tier"] == lab).sum())
        print(f"  {lab:16}: {n_elig:>5} eligible (>=500px rows, usable mc) -> sampled {len(cand_by_tier[lab])}")
    all_candidates = sorted({t for lab in TIERS_LABELS for t in cand_by_tier[lab]})
    print(f"[universe] total distinct candidates sampled = {len(all_candidates)}")

    cf_cache = _load_cf_cache(all_candidates)
    n_ok = sum(1 for t in all_candidates if cf_cache.get(t, {}).get("pulled_ok"))
    n_both = sum(1 for t in all_candidates
                 if cf_cache.get(t, {}).get("rep") is not None and cf_cache.get(t, {}).get("nci") is not None)
    print(f"[cf-pull] {n_ok}/{len(all_candidates)} candidates had a successful quarterly_cash_flow pull "
          f"(Ticker call returned data at all); {n_both}/{len(all_candidates)} had BOTH a "
          f"repurchase row and a net-issuance row")

    df, attrition = build_panel(cand_by_tier, cf_cache, px, mc)
    if df.empty:
        print("\nEMPTY PANEL — abort")
        return
    print(f"\n[panel] {len(df)} name-quarter obs, {df['sym'].nunique()} names, "
          f"{df['q_end'].nunique()} report-periods ({df['q_end'].min().date()}..{df['q_end'].max().date()})")

    print_attrition(attrition, df)

    print("\n=== signal distribution (pooled name-quarter obs, whole broad sample) ===")
    for sig in ("buyback_yield", "net_issuance"):
        s = df[sig].dropna()
        qs = s.quantile([0.1, 0.2, 0.5, 0.8, 0.9])
        print(f"  {sig:14}: n={len(s)}  p10={qs.iloc[0] * 100:+.2f}%  p20={qs.iloc[1] * 100:+.2f}%  "
              f"median={qs.iloc[2] * 100:+.2f}%  p80={qs.iloc[3] * 100:+.2f}%  p90={qs.iloc[4] * 100:+.2f}%")

    print_tier_metrics(df)

    elapsed = time.time() - t_start
    print(f"\n[done] total wall-clock = {elapsed:.0f}s ({elapsed / 60:.1f} min)")
    print("\nNOTE: same caveats as BC (exp_buyback_capital_allocation.py) — cross-sectional SCREEN, "
          "equal-weight, costless, overlapping fwd windows -> autocorr, single ~2022-2026 regime "
          "(defeatbeta quarterly_cash_flow depth). LAG_DAYS=100 uniform across tiers (see module "
          "docstring) is WIDER than BC's 75d, so this is not a byte-for-byte apples comparison of "
          "the large tier vs BC's own SPDR-top-10 result — a methodology difference, not just a "
          "universe difference; noted for the reader.")


if __name__ == "__main__":
    run()
