"""Insider BREADTH x MARKET-CAP TIER (Phase-3 P0-c revisit, 2026-07-11 addendum to
exp_insider_breadth.py). Motivation: exp_insider_breadth.py's pooled OLS (owners + value + mcap, all
in one regression across the FULL universe) found owners' t-stat collapses from ~2.3 to ~0.3-0.4 at
every horizon once market cap is added as a control. But a pooled regression only answers "does
owners explain anything ONCE you strip out the *average*, market-wide size effect" -- it does NOT
answer "within a given size tier, does owners count still discriminate forward returns". Per
KARS_MEMORY's standing lesson ("insider 教訓: edge成日喺細價股"), if the breadth effect is real but
TIER-SPECIFIC (e.g. only within micro/small-cap), a single pooled control can fully absorb it even
though it is a genuine, exploitable, size-conditional signal -- pooled OLS cannot distinguish
"owners is a size proxy with zero effect anywhere" from "owners matters a lot in micro-caps and not
at all elsewhere, and pooling those two regimes together washes it out".

This script re-cuts the SAME 9,963 matured cluster-buy events (owners>=2 & $>=500k, 2006q1-2025q2,
already fat-finger-filtered) produced by exp_insider_breadth.build() into market-cap tiers -- SAME
boundaries as exp_insider_mktcap.py for continuity with prior work:
  micro <$300M / small $300M-2B / mid $2B-10B / large >=$10B
-- and, independently WITHIN each tier: (1) owners-bucket x forward-excess table, (2) Spearman
monotonicity, (3) OLS forward excess ~ log2(owners) [+ log10(value)] [+ log10(mcap) as a WITHIN-TIER
continuous residual-size control, since a coarse tier still spans a 3x-33x mcap range internally].
A market-cap QUARTILE cut (balanced n, no arbitrary $ boundaries) is run alongside as a robustness
check on the tier choice itself.

    python backtest/experiments/exp_insider_breadth_mcaptier.py
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_insider_breadth as B  # noqa: E402  (reuses B.build(): same data + data-quality monkeypatch)

HORS = B.HORS
stat = B.stat
ols = B.ols
print_ols = B.print_ols

TIERS = [
    ("micro <$300M", 0.0, 3e8),
    ("small $300M-2B", 3e8, 2e9),
    ("mid $2B-10B", 2e9, 1e10),
    ("large >=$10B", 1e10, float("inf")),
]


def owners_bucket_table(sub):
    H = f"{'n':>5}{'mean%':>8}{'med%':>8}{'hit':>6}{'t':>7}"
    buckets = [("owners=2", sub.owners == 2), ("owners=3-4", sub.owners.between(3, 4)),
               ("owners>=5", sub.owners >= 5)]
    for lbl, m in buckets:
        g = sub[m]
        if len(g) == 0:
            print(f"  {lbl:<12} n=0")
            continue
        print(f"  {lbl:<12} n={len(g):<5} median $value=${g['value'].median()/1e3:,.0f}k")
        for h in HORS:
            print(f"    {str(h)+'d':<6}{stat(g[h])}")
    print(f"  (header cols per horizon row: {H})")


def owners_step_test(sub, h):
    """owners=2 vs owners>=3 diff-of-means t-test, 1 horizon -- the coarse step that survived in the
    pooled (non-tiered) report's §3b."""
    a = sub.loc[sub.owners == 2, h].dropna().values.astype(float)
    b = sub.loc[sub.owners >= 3, h].dropna().values.astype(float)
    if len(a) < 15 or len(b) < 15:
        return None
    t, p = sps.ttest_ind(b, a, equal_var=False)
    return dict(n2=len(a), n3=len(b), mean2=a.mean(), mean3=b.mean(), t=t, p=p)


def tier_report(df, lbl, lo, hi):
    sub = df[(df.mcap >= lo) & (df.mcap < hi)].copy()
    n = len(sub)
    print(f"\n{'='*88}\nTIER: {lbl}   n(matured, has mcap)={n}"
          f"  ({100*n/len(df):.1f}% of {len(df)} mcap-matched events)")
    if n < 60:
        print("  ** n<60 in this tier -- too few events for ANY reliable per-horizon/per-bucket "
              "inference. Reporting raw numbers below for transparency, but treat as NOISE, not signal. **")
    print(f"  mcap range in tier: median=${sub['mcap'].median()/1e6:,.0f}M  "
          f"[{sub['mcap'].min()/1e6:,.0f}M .. {sub['mcap'].max()/1e6:,.0f}M]")

    print("\n  -- 1. owners bucket x forward excess vs SPY --")
    owners_bucket_table(sub)

    print("\n  -- 2. monotonicity: Spearman corr(owners, forward excess) --")
    mono = {}
    for h in HORS:
        g = sub.dropna(subset=[h, "owners"])
        if len(g) < 30:
            print(f"    {h}d: n={len(g)} -- too few, skipped")
            mono[h] = None
            continue
        rho, p = sps.spearmanr(g["owners"], g[h])
        print(f"    {h}d: rho={rho:+.4f}  p={p:.4f}  n={len(g)}")
        mono[h] = (rho, p)

    print("\n  -- 3. owners=2 vs owners>=3 step test (matches pooled report's strongest surviving cut) --")
    step = {}
    for h in HORS:
        r = owners_step_test(sub, h)
        step[h] = r
        if r is None:
            print(f"    {h}d: insufficient n in one/both groups, skipped")
        else:
            print(f"    {h}d: owners=2 n={r['n2']} mean={r['mean2']*100:+.2f}%  |  "
                  f"owners>=3 n={r['n3']} mean={r['mean3']*100:+.2f}%  |  "
                  f"diff t={r['t']:+.2f}  p={r['p']:.4f}")

    print("\n  -- 4. within-tier OLS: forward excess ~ log2(owners) [+ log10(value)] [+ log10(mcap)] --")
    ols_res = {}
    if n >= 40:
        for h in HORS:
            y = sub[h].values.astype(float)
            lo_ = np.log2(sub["owners"].values.astype(float))
            lv = np.log10(sub["value"].values.astype(float))
            mcap_arr = sub["mcap"].values.astype(float)
            lm = np.where(mcap_arr > 0, np.log10(np.where(mcap_arr > 0, mcap_arr, 1.0)), np.nan)
            print(f"\n    --- horizon {h}d (tier n={n}) ---")
            r_a = ols(y, {"log2(owners)": lo_})
            r_c = ols(y, {"log2(owners)": lo_, "log10(value)": lv})
            r_d = ols(y, {"log2(owners)": lo_, "log10(value)": lv, "log10(mcap)": lm})
            print_ols("    (a) owners only          ", r_a)
            print_ols("    (c) owners + value       ", r_c)
            print_ols("    (d) owners + value + mcap(within-tier)", r_d)
            ols_res[h] = dict(a=r_a, c=r_c, d=r_d)
    else:
        print("    n<40 -- OLS skipped (too few degrees of freedom for a 3-4 parameter regression)")

    return dict(n=n, mono=mono, step=step, ols=ols_res)


def quantile_robustness(df):
    print(f"\n{'='*88}\nROBUSTNESS: market-cap QUARTILE cut (balanced n, no arbitrary $ boundary)")
    d = df.dropna(subset=["mcap"]).copy()
    d["mq"] = pd.qcut(d["mcap"], 4, labels=["Q1(小)", "Q2", "Q3", "Q4(大)"])
    for q in ["Q1(小)", "Q2", "Q3", "Q4(大)"]:
        sub = d[d.mq == q]
        lo_edge, hi_edge = sub["mcap"].min(), sub["mcap"].max()
        print(f"\n  {q}  n={len(sub)}  mcap range ${lo_edge/1e6:,.0f}M-${hi_edge/1e6:,.0f}M")
        for h in HORS:
            r = owners_step_test(sub, h)
            if r is None:
                print(f"    {h}d: insufficient n, skipped")
            else:
                print(f"    {h}d: owners=2 n={r['n2']} mean={r['mean2']*100:+.2f}%  |  "
                      f"owners>=3 n={r['n3']} mean={r['mean3']*100:+.2f}%  |  diff t={r['t']:+.2f}  p={r['p']:.4f}")


def main():
    df = B.build()
    before = len(df)
    df = df.dropna(subset=["mcap"])
    print(f"\n[tier] {before} matured events -> {len(df)} with a valid market cap "
          f"({before-len(df)} dropped for missing mcap)\n")

    results = {}
    for lbl, lo, hi in TIERS:
        results[lbl] = tier_report(df, lbl, lo, hi)

    quantile_robustness(df)

    print(f"\n{'='*88}\n=== SUMMARY across tiers: owners=2 vs owners>=3 step, 21d ===")
    print(f"{'tier':<20}{'n':>7}{'t(21d)':>9}{'p(21d)':>9}{'rho(21d)':>10}{'p(rho)':>9}")
    for lbl, lo, hi in TIERS:
        r = results[lbl]
        s21 = r["step"].get(21)
        m21 = r["mono"].get(21)
        t_s = f"{s21['t']:+.2f}" if s21 else "n/a"
        p_s = f"{s21['p']:.4f}" if s21 else "n/a"
        rho_s = f"{m21[0]:+.3f}" if m21 else "n/a"
        p_r = f"{m21[1]:.4f}" if m21 else "n/a"
        print(f"{lbl:<20}{r['n']:>7}{t_s:>9}{p_s:>9}{rho_s:>10}{p_r:>9}")

    print("\nREAD: 一個 tier 算有『獨立、tier-specific』breadth edge,要(i) owners>=3 vs owners=2 嘅"
          " step test t>=2 且方向啱(owners多正報酬),(ii) monotonicity rho 唔跌到零/唔反號,"
          " (iii) OLS (d)(連 within-tier mcap 都控埋)入面 log2(owners) 嘅 t 仍然顯著。三個部分都通"
          "先算穩;淨係(i)通、(ii)/(iii)唔通 = 好可能仍然係 within-tier residual size 效應,"
          "唔係真正breadth。細 tier(n<60)嘅任何『顯著』結果都要格外小心 multiple-testing"
          "(本script跑咗4 tiers x 3 horizons x 3 tests = 36 shots,5%顯著水平下預期 ~1.8 個假陽性)。")


if __name__ == "__main__":
    main()
