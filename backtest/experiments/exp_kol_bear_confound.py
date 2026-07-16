"""KOL bear-call momentum confound test -- "順哥" (royal flush 皇者顺888).

QUESTION
--------
backtest/results/2026-07-17_kol_shunge_scorecard.md found his BEARISH claims (n=676
episodes) beat SPY/QQQ with 54-56% hit rate and +0.9%/+2.4%/+4.2% median excess
(21/63/126d, sign-flipped). The gatekeeper note at the bottom of that report flagged
an untested confound: his bear calls may simply land on stocks ALREADY FALLING, and
the "excess" may just be momentum continuation ("losers keep losing") that a
mechanical rule would capture just as well -- in which case there is no KOL-specific
information and no reason to pipe his book into the radar.

This script is the A/B that decides it. It does NOT re-extract anything -- it reads
the already-scored intermediates from exp_kol_shunge_ledger.py:
    thesis/.raw/discord/claims.json   (episodes: ticker/date/dir)
    thesis/.raw/discord/scored.json   (his actual forward excess, xs_spy_h/xs_qqq_h,
                                        already sign-flipped for bear claims)

FOUR TESTS (pre-registered design; each below states the rule BEFORE any output is
read to keep the confound test itself honest about its own knobs)
--------------------------------------------------------------------------------
T1. STATE DESCRIPTION -- for every bear episode, compute at the LAST CLOSE BEFORE
    ENTRY (no look-ahead: same "asof" index the scoring already uses, i.e.
    entry_idx - 1):
      - mom_63   = 63-trading-day trailing total return
      - pct_off_high = distance below the trailing 252-day rolling high (0 = at
        the high; 0.30 = 30% below it)
      - RS_63    = mom_63(ticker) - mom_63(SPY)  (relative strength)
    Report the FULL distribution (min/p10/p25/median/p75/p90/max), not just a mean.

T2. MATCHED CONTROL (the core test) -- for every bear episode, on the SAME calendar
    day, draw N=20 tickers from a POOL (his own 359 ever-mentioned tickers first,
    the full current S&P 500 as backup filler) whose (mom_63, pct_off_high) falls in
    the SAME fixed bucket-pair as the called ticker (bucket edges fixed below,
    BEFORE any control return was computed). Score each control with the IDENTICAL
    next-close entry + bear-sign convention as his own claim. For each episode,
    compute the percentile rank of his ACTUAL excess (already in scored.json) inside
    the 20 controls' excess distribution. Aggregate that percentile across episodes:
      >~p75 median  -> he beats the momentum-matched crowd -> information beyond
                       momentum.
      ~p25-p75      -> statistically indistinguishable from a momentum-matched
                       random pick -> he IS a momentum rule.
    Also report the POOLED control distribution (hit/median/mean/p10) side-by-side
    with his own bear-book table, for a second, coarser read of the same question.

T3. MECHANICAL REPLICATION -- a single fixed rule: "63-trading-day return < -15% ->
    auto-bear signal, 7-CALENDAR-day cooldown per ticker" (same cooldown convention
    as the KOL episode-collapse rule, R4 in the ledger script), scanned over his own
    359-ticker mentioned pool (not the S&P 500 backup -- keeps the universe/liquidity
    mix constant so this is a fair "would a dumb rule on the SAME stocks he covers
    have done as well" test) over the SAME calendar span his corpus covers. Scored
    identically. Reported side-by-side with his actual bear-book table.

T4. SEGMENTATION -- split his 676 bear episodes by pct_off_high at call time:
      "near highs"      : pct_off_high < 10%  (bearish while the stock is NOT
                           already falling -- the only sub-group that could be a
                           genuine call rather than momentum-chasing)
      "already falling"  : pct_off_high >= 10%
    Report n + hit/median/mean/p10 for each segment separately (bucket boundary
    fixed BEFORE reading either segment's result -- taken verbatim from the task
    brief, not tuned).

STATISTICAL HONESTY
--------------------
- Effective-N disclosure: forward windows (esp. 126d) overlap heavily inside a 3.3
  year corpus. For each (segment, horizon) we report both raw n AND an approximate
  independent-cluster count (connected components of the "windows overlap" graph --
  two episodes are in the same cluster if their [entry, entry+h] date ranges
  intersect). This is a lower bound on the effective sample size; hit-rate read-outs
  should be judged against the cluster count, not the raw n.
- Matched-control under-fill: if a bucket-pair has < 20 eligible candidates on that
  day, we take all available and flag it rather than silently padding with a
  different bucket.
- Coverage: pool tickers whose price history fails to fetch/resolve are dropped and
  counted, not silently treated as absent-from-universe.

Stages: python exp_kol_bear_confound.py --fetch | --analyze | --all
Fetch caches new S&P 500-only tickers under thesis/.raw/discord/prices/ (the SAME
cache directory exp_kol_shunge_ledger.py already uses for his 359 mentioned tickers
-- gitignored, reused read-only for the 359, extended for the ~409 S&P 500-only
additions). Deliverable -> backtest/results/2026-07-17_kol_bear_confound.md
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backtest.experiments.exp_kol_shunge_ledger import (  # noqa: E402
    CLAIMS, HORIZONS, PRICES, RAW, SCORED, _fwd_matrix, _px,
)

SEED = 20260717
RNG_GLOBAL = np.random.default_rng(SEED)

OUT = RAW / "bear_confound_report.json"
SP500_PKL = ROOT / "backtest" / ".insider_data" / "sp500_px.pkl"

BENCH_EXCLUDE = {"SPY", "QQQ"}   # the two benchmarks -- never a "matched control stock"
N_MATCH = 20                     # controls drawn per bear episode

# --- T2/T3 bucket edges: FIXED before any control/mechanical return was computed --
MOM_BINS = [-1.0, -0.40, -0.25, -0.15, -0.05, 0.05, 0.15, 0.30, np.inf]
OFFHIGH_BINS = [0.0, 0.10, 0.25, 0.40, 0.60, 1.01]
MECH_THRESHOLD = -0.15           # T3: 63d return < -15%
MECH_COOLDOWN_DAYS = 7           # T3: matches R4's episode-collapse cooldown
NEAR_HIGH_CUTOFF = 0.10          # T4: pct_off_high < 10% = "near highs"


# ---------------------------------------------------------------------------
# Pool construction
# ---------------------------------------------------------------------------
def mentioned_pool() -> list[str]:
    blob = json.loads(CLAIMS.read_text(encoding="utf-8"))
    tks = {e["ticker"] for e in blob["episodes"]}
    return sorted(tks - BENCH_EXCLUDE)


def sp500_pool() -> list[str]:
    with open(SP500_PKL, "rb") as f:
        d = pickle.load(f)
    return sorted(set(d.keys()) - BENCH_EXCLUDE)


def stage_fetch(workers: int = 10) -> None:
    """Ensure adjusted-close CSVs exist for the FULL pool (mentioned U S&P500).
    Reuses exp_kol_shunge_ledger._px -- same cache dir, same yfinance-adjusted
    methodology as his own 359-ticker prices, so the combined pool is measured on
    one consistent basis (no defeatbeta-vs-yfinance basis mismatch)."""
    mp, sp = set(mentioned_pool()), set(sp500_pool())
    add = sorted(sp - mp)
    print(f"mentioned pool={len(mp)}  sp500 pool={len(sp)}  "
          f"overlap={len(mp & sp)}  new-to-fetch={len(add)}")
    ok, fail = 0, 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_px, t): t for t in add}
        for i, fut in enumerate(as_completed(futs), 1):
            t = futs[fut]
            try:
                s = fut.result()
                ok += 1 if s is not None else 0
                fail += 0 if s is not None else 1
            except Exception:
                fail += 1
            if i % 50 == 0:
                print(f"  {i}/{len(add)} fetched (ok={ok} fail={fail})", flush=True)
    print(f"fetch done: ok={ok} fail={fail} / {len(add)}")


# ---------------------------------------------------------------------------
# Feature panel
# ---------------------------------------------------------------------------
def _load_pool_panel():
    pool = sorted(set(mentioned_pool()) | set(sp500_pool()))
    spy = _px("SPY")
    cal = spy.index
    px, missing = {}, []
    for t in pool:
        s = _px(t)
        if s is not None and len(s) >= 63:
            px[t] = s
        else:
            missing.append(t)
    close = pd.DataFrame({t: s.reindex(cal) for t, s in px.items()})
    spy_c = spy.reindex(cal)
    mom63 = close / close.shift(63) - 1.0
    spy_mom63 = spy_c / spy_c.shift(63) - 1.0
    roll_max = close.rolling(252, min_periods=40).max()
    pct_off_high = (roll_max - close) / roll_max
    rs63 = mom63.sub(spy_mom63, axis=0)
    return {
        "pool": pool, "px": px, "missing": missing, "cal": cal,
        "close": close, "mom63": mom63, "pct_off_high": pct_off_high,
        "rs63": rs63, "spy": spy_c,
    }


def _bucket(mom: pd.Series, off: pd.Series) -> pd.DataFrame:
    mb = pd.cut(mom, MOM_BINS, labels=False, include_lowest=True)
    ob = pd.cut(off, OFFHIGH_BINS, labels=False, include_lowest=True)
    return mb, ob


# ---------------------------------------------------------------------------
# Effective-N via overlap clustering
# ---------------------------------------------------------------------------
def _effective_clusters(entries: list[str], h: int) -> int:
    """Two episodes cluster together if their [entry, entry+h trading days] windows
    intersect. Returns the number of connected components -- a rough LOWER BOUND
    on the number of independent observations (see module docstring)."""
    if not entries:
        return 0
    idx = sorted(pd.Timestamp(e) for e in entries)
    # approx window length in calendar days (~1.45 cal days per trading day)
    span = pd.Timedelta(days=int(h * 1.45) + 2)
    clusters = 1
    cur_end = idx[0] + span
    for d in idx[1:]:
        if d <= cur_end:
            cur_end = max(cur_end, d + span)
        else:
            clusters += 1
            cur_end = d + span
    return clusters


# ---------------------------------------------------------------------------
# T1 + T2: state description + matched control
# ---------------------------------------------------------------------------
def stage_analyze() -> dict:
    scored = pd.DataFrame(json.loads(SCORED.read_text(encoding="utf-8")))
    bear = scored[scored["dir"] == "bear"].reset_index(drop=True)

    panel = _load_pool_panel()
    cal, mom63, offh, rs63 = panel["cal"], panel["mom63"], panel["pct_off_high"], panel["rs63"]
    pos = {d: i for i, d in enumerate(cal)}

    mp_set = set(mentioned_pool())
    all_pool_cols = list(mom63.columns)

    rows = []
    for _, r in bear.iterrows():
        t = r["ticker"]
        entry = pd.Timestamp(r["entry"])
        if entry not in pos or t not in mom63.columns:
            continue
        entry_idx = pos[entry]
        asof = entry_idx - 1
        if asof < 0:
            continue
        m = mom63[t].iloc[asof]
        o = offh[t].iloc[asof]
        rs = rs63[t].iloc[asof]
        if not (np.isfinite(m) and np.isfinite(o)):
            continue
        rows.append({"ticker": t, "date": r["date"], "entry": r["entry"],
                      "entry_idx": entry_idx, "asof": asof,
                      "mom63": float(m), "pct_off_high": float(o),
                      "rs63": float(rs) if np.isfinite(rs) else None,
                      "xs_spy_21": r.get("xs_spy_21"), "xs_spy_63": r.get("xs_spy_63"),
                      "xs_spy_126": r.get("xs_spy_126"),
                      "xs_qqq_21": r.get("xs_qqq_21"), "xs_qqq_63": r.get("xs_qqq_63"),
                      "xs_qqq_126": r.get("xs_qqq_126")})
    feat = pd.DataFrame(rows)
    n_total_bear = len(bear)
    n_featured = len(feat)

    # ---- T1: distribution ----
    def _dist(s: pd.Series) -> dict:
        s = s.dropna()
        return {"n": int(len(s)), "min": float(s.min()), "p10": float(s.quantile(.10)),
                "p25": float(s.quantile(.25)), "median": float(s.median()),
                "p75": float(s.quantile(.75)), "p90": float(s.quantile(.90)),
                "max": float(s.max())}

    t1 = {
        "n_total_bear_episodes": n_total_bear,
        "n_featured": n_featured,
        "n_dropped_missing_feature": n_total_bear - n_featured,
        "mom63": _dist(feat["mom63"]),
        "pct_off_high": _dist(feat["pct_off_high"]),
        "rs63": _dist(feat["rs63"].dropna()),
        "share_near_high_lt10pct": float((feat["pct_off_high"] < NEAR_HIGH_CUTOFF).mean()),
        "share_already_falling_ge10pct": float((feat["pct_off_high"] >= NEAR_HIGH_CUTOFF).mean()),
    }

    # ---- forward-return panels for matched control + mechanical rule ----
    fwd = {h: _fwd_matrix(panel["px"], cal, h) for h in HORIZONS}
    spy_fr = {h: _fwd_matrix({"SPY": panel["spy"]}, cal, h)["SPY"] for h in HORIZONS}

    mb, ob = _bucket(feat["mom63"], feat["pct_off_high"])

    # bucket assignment for the FULL pool is computed PER ROW (asof index differs
    # per episode), inside the loop below
    t2_pctiles = {h: [] for h in HORIZONS}
    pooled_ctrl = {h: [] for h in HORIZONS}
    fill_stats = {"n_episodes": 0, "underfilled": 0, "from_sp500_backup": 0,
                  "from_mentioned": 0, "total_drawn": 0}

    for i, r in feat.iterrows():
        t, asof = r["ticker"], int(r["asof"])
        m_bucket = mb.iloc[i]
        o_bucket = ob.iloc[i]
        if pd.isna(m_bucket) or pd.isna(o_bucket):
            continue
        # candidates: same asof-row bucket-pair, excluding self, finite features
        col_mom = mom63.iloc[asof]
        col_off = offh.iloc[asof]
        cand_mb = pd.cut(col_mom, MOM_BINS, labels=False, include_lowest=True)
        cand_ob = pd.cut(col_off, OFFHIGH_BINS, labels=False, include_lowest=True)
        eligible = col_mom.index[(cand_mb == m_bucket) & (cand_ob == o_bucket)]
        eligible = [c for c in eligible if c != t]
        mentioned_elig = [c for c in eligible if c in mp_set]
        backup_elig = [c for c in eligible if c not in mp_set]

        rng = np.random.default_rng(SEED + i)
        chosen = list(rng.choice(mentioned_elig, size=min(N_MATCH, len(mentioned_elig)),
                                  replace=False)) if mentioned_elig else []
        n_from_mentioned = len(chosen)
        if len(chosen) < N_MATCH and backup_elig:
            need = N_MATCH - len(chosen)
            extra = list(rng.choice(backup_elig, size=min(need, len(backup_elig)),
                                     replace=False))
            chosen += extra
        n_from_backup = len(chosen) - n_from_mentioned

        fill_stats["n_episodes"] += 1
        fill_stats["total_drawn"] += len(chosen)
        fill_stats["from_mentioned"] += n_from_mentioned
        fill_stats["from_sp500_backup"] += n_from_backup
        if len(chosen) < N_MATCH:
            fill_stats["underfilled"] += 1
        if not chosen:
            continue

        entry_idx = int(r["entry_idx"])
        for h in HORIZONS:
            rr = np.array([fwd[h][c][entry_idx] for c in chosen])
            rb = spy_fr[h][entry_idx]
            valid = np.isfinite(rr) & np.isfinite(rb)
            if not valid.any():
                continue
            ctrl_xs = -1.0 * (rr[valid] - rb)   # bear sign, identical to his own scoring
            pooled_ctrl[h].extend(ctrl_xs.tolist())
            his_xs = r.get(f"xs_spy_{h}")
            if his_xs is None or not np.isfinite(his_xs):
                continue
            pct = float(np.mean(ctrl_xs < his_xs))
            t2_pctiles[h].append(pct)

    def _agg_series(vals: list[float]) -> dict:
        v = np.array(vals, dtype="float64")
        v = v[np.isfinite(v)]
        if len(v) == 0:
            return {}
        return {"n": int(len(v)), "hit": float((v > 0).mean()), "median": float(np.median(v)),
                "mean": float(np.mean(v)), "p10": float(np.quantile(v, 0.10))}

    t2 = {
        "fill_stats": fill_stats,
        "his_actual_bear_book": {h: _agg_series(feat[f"xs_spy_{h}"].dropna().tolist())
                                  for h in HORIZONS},
        "pooled_matched_control": {h: _agg_series(pooled_ctrl[h]) for h in HORIZONS},
        "percentile_rank_of_his_actual_within_matched_controls": {
            h: {
                "n_episodes": len(t2_pctiles[h]),
                "median_percentile": float(np.median(t2_pctiles[h])) if t2_pctiles[h] else None,
                "mean_percentile": float(np.mean(t2_pctiles[h])) if t2_pctiles[h] else None,
                "share_gt_p75": float(np.mean(np.array(t2_pctiles[h]) > 0.75)) if t2_pctiles[h] else None,
                "share_in_p25_p75": float(np.mean((np.array(t2_pctiles[h]) >= 0.25) &
                                                   (np.array(t2_pctiles[h]) <= 0.75))) if t2_pctiles[h] else None,
                "share_lt_p25": float(np.mean(np.array(t2_pctiles[h]) < 0.25)) if t2_pctiles[h] else None,
            } for h in HORIZONS
        },
    }

    # ---- T3: mechanical replication, scanned over the MENTIONED pool only ----
    claims_blob = json.loads(CLAIMS.read_text(encoding="utf-8"))
    all_dates = [pd.Timestamp(e["date"]) for e in claims_blob["episodes"]]
    span_start, span_end = min(all_dates), max(all_dates)
    cal_in_span = [d for d in cal if span_start <= d <= span_end]
    lo_pos, hi_pos = pos[cal_in_span[0]], pos[cal_in_span[-1]]

    mech_signals = []
    for t in sorted(mp_set):
        if t not in mom63.columns:
            continue
        col = mom63[t].iloc[lo_pos:hi_pos + 1]
        trig_idx = np.where(col.to_numpy() < MECH_THRESHOLD)[0] + lo_pos
        if len(trig_idx) == 0:
            continue
        last_date = None
        for gi in trig_idx:
            d = cal[gi]
            if last_date is not None and (d - last_date).days <= MECH_COOLDOWN_DAYS:
                continue
            last_date = d
            mech_signals.append({"ticker": t, "signal_idx": int(gi), "date": str(d.date())})

    mech_rows = []
    for sig in mech_signals:
        gi = sig["signal_idx"]
        entry_idx = gi + 1
        if entry_idx >= len(cal):
            continue
        rec = {"ticker": sig["ticker"], "date": sig["date"],
               "entry": str(cal[entry_idx].date())}
        for h in HORIZONS:
            r = fwd[h][sig["ticker"]][entry_idx]
            rb = spy_fr[h][entry_idx]
            if not (np.isfinite(r) and np.isfinite(rb)):
                continue
            rec[f"xs_spy_{h}"] = -1.0 * (r - rb)
        mech_rows.append(rec)
    mech_df = pd.DataFrame(mech_rows)
    t3 = {
        "rule": f"mom63 < {MECH_THRESHOLD:.0%}, {MECH_COOLDOWN_DAYS}-calendar-day cooldown, "
                f"scanned over his {len(mp_set)}-ticker mentioned pool, "
                f"{span_start.date()}..{span_end.date()}",
        "n_signals": len(mech_df),
        "his_actual_bear_book": t2["his_actual_bear_book"],
        "mechanical_rule": {h: _agg_series(mech_df[f"xs_spy_{h}"].dropna().tolist())
                             if f"xs_spy_{h}" in mech_df.columns else {} for h in HORIZONS},
    }

    # ---- T4: segmentation ----
    near = feat[feat["pct_off_high"] < NEAR_HIGH_CUTOFF]
    far = feat[feat["pct_off_high"] >= NEAR_HIGH_CUTOFF]
    t4 = {
        "near_highs_lt10pct": {
            "n": int(len(near)),
            **{f"h{h}": _agg_series(near[f"xs_spy_{h}"].dropna().tolist()) for h in HORIZONS},
            **{f"h{h}_qqq": _agg_series(near[f"xs_qqq_{h}"].dropna().tolist()) for h in HORIZONS},
        },
        "already_falling_ge10pct": {
            "n": int(len(far)),
            **{f"h{h}": _agg_series(far[f"xs_spy_{h}"].dropna().tolist()) for h in HORIZONS},
            **{f"h{h}_qqq": _agg_series(far[f"xs_qqq_{h}"].dropna().tolist()) for h in HORIZONS},
        },
    }

    # ---- effective-N disclosure ----
    eff_n = {
        "all_bear": {h: _effective_clusters(feat["entry"].tolist(), h) for h in HORIZONS},
        "near_highs": {h: _effective_clusters(near["entry"].tolist(), h) for h in HORIZONS},
        "already_falling": {h: _effective_clusters(far["entry"].tolist(), h) for h in HORIZONS},
        "mechanical_signals": {h: _effective_clusters(mech_df["entry"].tolist(), h)
                                if len(mech_df) else 0 for h in HORIZONS},
    }

    report = {
        "pool_sizes": {"mentioned": len(mp_set), "sp500": len(sp500_pool()),
                       "union": len(all_pool_cols), "missing_price_history": len(panel["missing"])},
        "t1_state_description": t1,
        "t2_matched_control": t2,
        "t3_mechanical_replication": t3,
        "t4_segmentation": t4,
        "effective_n_clusters": eff_n,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1, default=str))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.fetch or a.all:
        stage_fetch()
    if a.analyze or a.all:
        stage_analyze()
