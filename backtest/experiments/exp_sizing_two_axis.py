"""backtest/experiments/exp_sizing_two_axis.py

DECISION ANALYSIS -- NOT A BACKTEST.

Motivation: thesis/sizing.py currently sizes every active theme using ONLY a linear
`confidence` axis (0-1). There is no "magnitude" axis (how big the payoff is if the thesis
plays out). This script does NOT test that gap against history -- there is no live track
record to backtest (ic_report.json shows 0 matured predictions as of 2026-07-11). Instead it
runs a Monte Carlo simulation over ASSUMED per-theme payoff distributions (magnitude
midpoint + downside, hand-assigned from themes.yaml's cycle_stage/notes -- see
THEME_ASSUMPTIONS below and the companion results doc for rationale) to compare four
candidate sizing schemes on an apples-to-apples basis: identical $41,000 satellite budget,
identical $20,500 total-deployment cap (= the live PRELIMINARY-status 50% cap already baked
into sizing.py).

Schemes compared (see scheme_*_alloc functions):
  A. status quo    -- linear confidence + sizing.py's exact PRELIMINARY dual-cap logic.
                       Reproduced by importing thesis/sizing.py's build_table() DIRECTLY
                       (not reimplemented by hand) -> 0% error by construction.
  B. conf x magnitude -- score = confidence * log2(magnitude_mid), normalized to the deployment
                       cap; binary-tagged themes get a fixed small "option-style" stake instead
                       (real magnitude is unreliable for a discrete catalyst, so size stays
                       small and constant rather than confidence-scaled).
  C. Top-5 concentration -- rank all themes by confidence * magnitude_mid (raw, not log), fund
                       only the top 5, split the cap proportionally among them, everyone else $0.
  D. Kelly-lite    -- f* = (p*b - q)/b per theme (p = success prob, b = magnitude_mid - 1),
                       negative Kelly floored at $0, each theme capped at 25% of the deployment
                       cap ($5,125), then scaled down (never up) to respect the total cap.

Outcome model (shared across all 4 schemes' return simulation so the comparison isolates
"how would you have allocated the same $20.5k", not "different random luck"):
  Each theme gets a 3-state per-path draw: P(kill) = 1 - p_success -> downside_pct;
  remaining p_success mass split 50/50 into "full win" (magnitude_mid - 1) and "half win"
  (half of that). Binary-tagged themes use p_success = 0.5 * confidence (task instruction:
  event-catalyst names split win/lose more sharply than a smooth confidence number implies);
  all other themes use p_success = confidence directly.

ai-power-grid special case: this theme carries an ADDITIVE per-node magnitude_tier (schema
added 2026-07-12) that sizing.py itself still ignores (theme-granular). For the RETURN
simulation only, this script samples which of the 5 nodes "dominates" each path (weighted by
ticker count) and applies that node's own magnitude/downside/binary flag -- richer than a
single point estimate. For the ALLOCATION math (schemes B/C/D, which size at theme
granularity, same as sizing.py), a single blended magnitude_mid (ticker-count-weighted
average across the 5 nodes) is used, computed in code (see NODES_AI_POWER_GRID) rather than
hand-typed.

Sensitivity: confidence values in themes.yaml are explicitly uncalibrated/cold-start (no
track record yet). This script re-runs everything with all confidence values haircut by 20%
(conf_mult = 0.8) and reports whether each scheme's E[PnL]/capital-efficiency ranking changes.

Run:  PYTHONUTF8=1 python backtest/experiments/exp_sizing_two_axis.py
      (optional: --n-paths 50000 --seed 20260712)

Output: printed report (assumption table, scheme comparison at baseline + haircut, ranking
stability check, ai-power-grid node breakdown) and a CSV snapshot of the scheme-comparison
metrics at backtest/results/_sizing_two_axis_metrics.csv for reproducibility.
"""
from __future__ import annotations

import argparse
import copy
import csv
import importlib.util
import math
import os
import sys

import numpy as np

# ---------------------------------------------------------------------------
# Load thesis/sizing.py directly by file path (thesis/ is not a package -- no __init__.py --
# and this script does not need any other repo-root import). Loading the REAL module, rather
# than reimplementing its cap/scale-down logic by hand, is what guarantees Scheme A reproduces
# sizing.py's numbers with 0% error (the acceptance bar was "<1%").
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SIZING_PATH = os.path.join(REPO_ROOT, "thesis", "sizing.py")
RESULTS_DIR = os.path.join(REPO_ROOT, "backtest", "results")

_spec = importlib.util.spec_from_file_location("ws5_sizing", SIZING_PATH)
ws5_sizing = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ws5_sizing)  # type: ignore[union-attr]

# ---------------------------------------------------------------------------
# Constants shared by all 4 schemes
# ---------------------------------------------------------------------------
BUDGET = 41_000.0
TOTAL_DEPLOYMENT_CAP = 0.50 * BUDGET          # $20,500 -- matches live PRELIMINARY 50% cap
KELLY_PER_THEME_CAP = 0.25 * TOTAL_DEPLOYMENT_CAP   # $5,125 -- ASSUMPTION, see results doc
OPTION_STYLE_FIXED_STAKE = 1_000.0            # $1,000 flat per binary theme in Scheme B -- ASSUMPTION
TOP_K = 5
N_PATHS_DEFAULT = 50_000
SEED_DEFAULT = 20260712

# ---------------------------------------------------------------------------
# ai-power-grid node mixture (per-node magnitude_tier already in themes.yaml, added
# 2026-07-12; sizing.py itself does not use it -- theme-granular). weight = ticker count
# (ETF-only legs count as weight 1). magnitude_mid / downside translate the yaml's qualitative
# magnitude_tier string into point-estimate numbers using the SAME rubric as every other theme
# (late/priced 1.5-2x/-50%, mid 2-3x/-35%..-50%, early/cheap 3-5x/-35%, event-binary
# 5-10x/-80% with halved success prob).
# ---------------------------------------------------------------------------
NODES_AI_POWER_GRID = [
    dict(name="grid-hardware", weight=7, magnitude_mid=2.5, downside=-0.50, binary=False),
    dict(name="power-semis-mature", weight=4, magnitude_mid=2.5, downside=-0.50, binary=False),
    dict(name="pre-earnings-optionality", weight=3, magnitude_mid=7.5, downside=-0.80, binary=True),
    dict(name="uranium-fuel", weight=1, magnitude_mid=4.0, downside=-0.35, binary=False),
    dict(name="ipp-utilities", weight=1, magnitude_mid=2.0, downside=-0.35, binary=False),
]


def _node_weights(nodes):
    w = np.array([nd["weight"] for nd in nodes], dtype=float)
    return w / w.sum()


def _blended(nodes, field):
    w = np.array([nd["weight"] for nd in nodes], dtype=float)
    v = np.array([nd[field] for nd in nodes], dtype=float)
    return float((w * v).sum() / w.sum())


AI_POWER_GRID_BLENDED_MAGNITUDE = _blended(NODES_AI_POWER_GRID, "magnitude_mid")   # ~3.5
AI_POWER_GRID_BLENDED_DOWNSIDE = _blended(NODES_AI_POWER_GRID, "downside")         # informational only

# ---------------------------------------------------------------------------
# Per-theme magnitude/downside ASSUMPTIONS (NOT measurements). Derived from cycle_stage +
# themes.yaml notes per the task's rubric:
#   late/priced-in   -> 1.5-2x upside,  -50% downside (unless noted otherwise)
#   mid              -> 2-3x upside,    -35% downside
#   early/cheap      -> 3-5x upside,    -35% downside (USAC, FSLR named explicitly)
#   event-binary     -> 5-10x upside,   -80% downside, success prob HALVED
# ---------------------------------------------------------------------------
THEME_ASSUMPTIONS = {
    "memory-supercycle": dict(
        category="late_priced", magnitude_mid=2.0, downside=-0.45, binary=False,
        rationale="late cycle_stage (MU capex 2.66x top signal, most-discussed AI-capex proxy) "
                   "but LTA/SCA take-or-pay contracts explicitly cushion the downside per the "
                   "theme note -> high end of the late/priced magnitude band, downside eased "
                   "from -50% to -45% for the same documented reason."),
    "photonics-optical": dict(
        category="late_priced", magnitude_mid=1.5, downside=-0.50, binary=False,
        rationale="MOST crowded cluster in the registry (58% bull sentiment) + moat names "
                   "(COHR/LITE/FN) at 75-98th ttm_pe percentile -> low end of the late/priced "
                   "band, full -50% downside, no mitigating factor noted."),
    "ai-power-grid": dict(
        category="late_priced_node_mixture", magnitude_mid=AI_POWER_GRID_BLENDED_MAGNITUDE,
        downside=AI_POWER_GRID_BLENDED_DOWNSIDE, binary=False,
        rationale="theme-level point estimate is a ticker-count-weighted blend across the 5 "
                   "nodes' own magnitude_tier (grid-hardware 2-3x, power-semis-mature 2-3x, "
                   "pre-earnings-optionality 5-10x-binary, uranium-fuel 3-5x, ipp-utilities 2x) "
                   "used ONLY for schemes B/C/D allocation math; the Monte Carlo RETURN "
                   "simulation samples a dominant node per path instead (richer, see "
                   "NODES_AI_POWER_GRID) -- WOLF's actual Chapter 11 filing is an ex-post "
                   "confirmation the pre-earnings-optionality node's 'binary' label is real."),
    "advanced-packaging": dict(
        category="late_priced", magnitude_mid=1.5, downside=-0.50, binary=False,
        rationale="all 5 discovery-radar proxies (TTMI/MKSI/KLAC/AMKR/ASX) at 90-100th ttm_pe "
                   "percentile -> low end of the late/priced band, full -50% downside."),
    "space-satellite": dict(
        category="event_binary", magnitude_mid=7.5, downside=-0.80, binary=True,
        rationale="theme's own verdict explicitly says express via option/event framing, small "
                   "size, strict kill discipline; ASTS 377x P/S, RKLB 94x P/S, many pre-revenue "
                   "names -> event-binary band, success probability halved per task rule."),
    "rare-earth-materials": dict(
        category="event_binary", magnitude_mid=7.5, downside=-0.80, binary=True,
        rationale="verdict is literally named 'real-chokepoint-thin-evidence-event-binary'; "
                   "binary 2026-11 US-China truce-expiry catalyst, MP already at 92nd ttm_pe "
                   "percentile -> event-binary band, success probability halved."),
    "tpu-custom-silicon": dict(
        category="mid", magnitude_mid=2.5, downside=-0.35, binary=False,
        rationale="mid cycle_stage, chain at 75-87th ttm_pe percentile, single Tier-2 source "
                   "(100% bull, thin diversity) -> mid-band magnitude, standard mid downside."),
    "oil-gas-energy": dict(
        category="late_priced", magnitude_mid=1.5, downside=-0.40, binary=False,
        rationale="verdict 'thin-split-watch' -- explicitly heterogeneous (oil-macro neutral + "
                   "gas-power bull, 'not one thesis') -> late/priced magnitude band, downside "
                   "eased slightly from -50% to -40% because the split framing already implies "
                   "a smaller committed bet size in practice, not a single sharp thesis to kill."),
    "semicap-equipment": dict(
        category="late_priced", magnitude_mid=1.5, downside=-0.50, binary=False,
        rationale="THINnest evidence base in the registry (1 neutral report, 0% bull); AEHR "
                   "fwd PE ~615x, +856% 1yr, price above all sell-side targets -> low end of "
                   "the late/priced band, full -50% downside."),
    "aerospace-specialty-alloys": dict(
        category="late_priced", magnitude_mid=1.5, downside=-0.50, binary=False,
        rationale="ATI/CRS both at 98th ttm_pe percentile (~61-62x); sourced only from "
                   "transcript-discovery-radar (tier 3), no deep ROIC/TAM research done yet -> "
                   "late/priced band, full -50% downside."),
    "euv-lithography-monopoly": dict(
        category="late_priced", magnitude_mid=1.5, downside=-0.50, binary=False,
        rationale="ASML at 98th ttm_pe percentile (~60x), explicitly the 'most priced-in of "
                   "all' with zero undiscovered premium (most widely-discussed semi monopoly "
                   "story) -> low end of the late/priced band, full -50% downside."),
    "us-solar-manufacturing": dict(
        category="early_cheap", magnitude_mid=4.0, downside=-0.35, binary=False,
        rationale="explicitly named in the task rubric (FSLR); ttm_pe only 22nd percentile "
                   "(~14.7x) despite mid cycle_stage -- the cheapest of the 6 new "
                   "discovery-radar themes, 7 consecutive years of 'sold out' language "
                   "confirmed in transcripts -> early/cheap band."),
    "gas-compression-equipment": dict(
        category="early_cheap", magnitude_mid=4.5, downside=-0.35, binary=False,
        rationale="explicitly named in the task rubric (USAC); ttm_pe 2nd percentile "
                   "(~27.1x) -- the single most extreme cheapness of all 15 active themes / 40 "
                   "discovery-radar candidates screened -> high end of the early/cheap band."),
    "specialty-siding-pricing-power": dict(
        category="mid", magnitude_mid=2.0, downside=-0.35, binary=False,
        rationale="lowest confidence of all 15 themes (0.20); whole-company ttm_pe 95th "
                   "percentile is explicitly flagged as a blended/dirty read (mixes weak OSB "
                   "commodity segment with strong Siding segment) -> mid band, low end, given "
                   "the acknowledged measurement noise."),
    "glp1-biologics-packaging": dict(
        category="mid", magnitude_mid=2.5, downside=-0.35, binary=False,
        rationale="ttm_pe 71st percentile (moderate); shortest track record of all 15 themes "
                   "(4 quarters vs. USAC's 13 years / ATI's 19 years) -> mid band."),
}


def p_success_for(slug: str, confidence: dict, conf_mult: float) -> float:
    c = confidence[slug] * conf_mult
    a = THEME_ASSUMPTIONS[slug]
    return 0.5 * c if a["binary"] else c


# ---------------------------------------------------------------------------
# Monte Carlo return sampling (3-state: kill / half-win / full-win)
# ---------------------------------------------------------------------------
def state_returns(u: np.ndarray, p_success: float, magnitude_mid: float, downside: float) -> np.ndarray:
    p_fail = 1.0 - p_success
    p_half = 0.5 * p_success
    full_r = magnitude_mid - 1.0
    half_r = full_r * 0.5
    thresh_fail = p_fail
    thresh_half = p_fail + p_half
    return np.where(u < thresh_fail, downside, np.where(u < thresh_half, half_r, full_r))


def ai_power_grid_returns(node_idx: np.ndarray, sub_u: np.ndarray, base_confidence: float,
                           conf_mult: float, n_paths: int) -> np.ndarray:
    returns = np.empty(n_paths)
    for i, nd in enumerate(NODES_AI_POWER_GRID):
        mask = node_idx == i
        if not mask.any():
            continue
        p = base_confidence * conf_mult
        if nd["binary"]:
            p = 0.5 * p
        returns[mask] = state_returns(sub_u[mask], p, nd["magnitude_mid"], nd["downside"])
    return returns


def build_all_returns(confidence: dict, conf_mult: float, slugs: list, u_by_slug: dict,
                       node_idx: np.ndarray, sub_u: np.ndarray, n_paths: int) -> dict:
    returns = {}
    for s in slugs:
        if s == "ai-power-grid":
            returns[s] = ai_power_grid_returns(node_idx, sub_u, confidence[s], conf_mult, n_paths)
        else:
            p = p_success_for(s, confidence, conf_mult)
            a = THEME_ASSUMPTIONS[s]
            returns[s] = state_returns(u_by_slug[s], p, a["magnitude_mid"], a["downside"])
    return returns


# ---------------------------------------------------------------------------
# Scheme A: status quo -- import the REAL sizing.py logic, do not reimplement it.
# ---------------------------------------------------------------------------
def scheme_A_alloc(themes: dict, status: str, circuit_breaker: bool, conf_mult: float) -> dict:
    if conf_mult == 1.0:
        rows, *_ = ws5_sizing.build_table(themes, status, circuit_breaker, BUDGET)
        return {r["slug"]: r["final"] for r in rows}
    themes_scaled = copy.deepcopy(themes)
    for slug, t in themes_scaled.items():
        if t.get("status", "active") == "active":
            t["confidence"] = float(t.get("confidence") or 0.0) * conf_mult
    rows, *_ = ws5_sizing.build_table(themes_scaled, status, circuit_breaker, BUDGET)
    return {r["slug"]: r["final"] for r in rows}


# ---------------------------------------------------------------------------
# Scheme B: confidence x log2(magnitude) multiplier; binary themes get a fixed small stake.
# ---------------------------------------------------------------------------
def scheme_B_alloc(confidence: dict, conf_mult: float) -> dict:
    binary_slugs = [s for s, a in THEME_ASSUMPTIONS.items() if a["binary"]]
    normal_slugs = [s for s in THEME_ASSUMPTIONS if s not in binary_slugs]
    fixed_total = OPTION_STYLE_FIXED_STAKE * len(binary_slugs)
    remaining_cap = TOTAL_DEPLOYMENT_CAP - fixed_total
    scores = {}
    for s in normal_slugs:
        c = confidence[s] * conf_mult
        mag = THEME_ASSUMPTIONS[s]["magnitude_mid"]
        scores[s] = c * math.log2(mag)
    total_score = sum(scores.values())
    alloc = {s: scores[s] / total_score * remaining_cap for s in normal_slugs}
    for s in binary_slugs:
        alloc[s] = OPTION_STYLE_FIXED_STAKE
    return alloc


# ---------------------------------------------------------------------------
# Scheme C: Top-K=5 concentration, ranked by confidence * magnitude_mid (raw, not log).
# ---------------------------------------------------------------------------
def scheme_C_alloc(confidence: dict, conf_mult: float, k: int = TOP_K):
    scores = {}
    for s, a in THEME_ASSUMPTIONS.items():
        c = confidence[s] * conf_mult
        scores[s] = c * a["magnitude_mid"]
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    top = ranked[:k]
    top_total_score = sum(v for _, v in top)
    alloc = {s: 0.0 for s in THEME_ASSUMPTIONS}
    for s, v in top:
        alloc[s] = v / top_total_score * TOTAL_DEPLOYMENT_CAP
    return alloc, [s for s, _ in top]


# ---------------------------------------------------------------------------
# Scheme D: Kelly-lite. f* = (p*b - q)/b, simple/literal formula per task spec (assumes total
# loss on failure -- does NOT use the partial downside_pct assumption; see caveats in results
# doc). Negative Kelly -> $0. Each theme capped at 25% of the deployment cap ($5,125), then the
# whole vector scaled DOWN (never up) if it exceeds the $20,500 total cap.
# ---------------------------------------------------------------------------
def scheme_D_alloc(confidence: dict, conf_mult: float) -> dict:
    raw = {}
    for s, a in THEME_ASSUMPTIONS.items():
        c = confidence[s] * conf_mult
        p = 0.5 * c if a["binary"] else c
        b = a["magnitude_mid"] - 1.0
        q = 1.0 - p
        f_star = (p * b - q) / b
        f_star = max(f_star, 0.0)
        dollars = min(f_star * BUDGET, KELLY_PER_THEME_CAP)
        raw[s] = dollars
    total = sum(raw.values())
    if total > TOTAL_DEPLOYMENT_CAP:
        factor = TOTAL_DEPLOYMENT_CAP / total
        raw = {s: v * factor for s, v in raw.items()}
    return raw


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def pnl_for_alloc(alloc: dict, slugs: list, returns: dict, n_paths: int) -> np.ndarray:
    pnl = np.zeros(n_paths)
    for s in slugs:
        v = alloc.get(s, 0.0)
        if v:
            pnl += v * returns[s]
    return pnl


def summarize(name: str, alloc: dict, slugs: list, returns: dict, n_paths: int) -> dict:
    pnl = pnl_for_alloc(alloc, slugs, returns, n_paths)
    deployed = sum(alloc.values())
    funded = sum(1 for v in alloc.values() if v > 1e-6)
    max_share = (max(alloc.values()) / deployed * 100.0) if deployed > 0 else 0.0
    mean_pnl = float(pnl.mean())
    median_pnl = float(np.median(pnl))
    p5 = float(np.percentile(pnl, 5))
    p95 = float(np.percentile(pnl, 95))
    loss_thresh = -0.30 * deployed
    p_big_loss = float((pnl < loss_thresh).mean()) if deployed > 0 else float("nan")
    cap_eff = mean_pnl / deployed if deployed > 0 else float("nan")
    return dict(name=name, deployed=deployed, funded=funded, max_share=max_share,
                mean=mean_pnl, median=median_pnl, p5=p5, p95=p95,
                p_loss30=p_big_loss, cap_eff=cap_eff)


def print_assumptions_table(slugs: list, confidence: dict):
    header = (f"{'theme':<32}{'conf':>6}{'category':>22}{'mag_mid':>9}{'downside':>10}{'binary':>8}")
    print(header)
    print("-" * len(header))
    for s in slugs:
        a = THEME_ASSUMPTIONS[s]
        print(f"{s:<32}{confidence[s]:>6.2f}{a['category']:>22}{a['magnitude_mid']:>9.2f}"
              f"{a['downside']:>10.2%}{str(a['binary']):>8}")


def print_scheme_table(results: list):
    header = (f"{'scheme':<24}{'deployed':>11}{'funded':>7}{'max_shr%':>9}{'E[PnL]':>10}"
              f"{'median':>10}{'P5':>10}{'P95':>10}{'P(loss>30%)':>13}{'cap_eff':>9}")
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['name']:<24}{r['deployed']:>11,.0f}{r['funded']:>7}{r['max_share']:>9.1f}"
              f"{r['mean']:>10,.0f}{r['median']:>10,.0f}{r['p5']:>10,.0f}{r['p95']:>10,.0f}"
              f"{r['p_loss30'] * 100:>12.1f}%{r['cap_eff'] * 100:>8.1f}%")


def ranking(results: list, key: str) -> list:
    return [r["name"] for r in sorted(results, key=lambda r: -r[key])]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-paths", type=int, default=N_PATHS_DEFAULT)
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT)
    args = ap.parse_args()
    n_paths = args.n_paths

    print("=" * 100)
    print("exp_sizing_two_axis.py -- DECISION ANALYSIS (assumed payoffs), NOT A BACKTEST")
    print("=" * 100)

    themes = ws5_sizing.load_themes()
    judge = ws5_sizing.load_judge()
    status = judge.get("status", "PRELIMINARY")
    circuit_breaker = bool(judge.get("circuit_breaker", False)) or status == "FAIL"

    active = {s: t for s, t in themes.items() if t.get("status", "active") == "active"}
    slugs = sorted(active.keys())
    confidence = {s: float(active[s].get("confidence") or 0.0) for s in slugs}

    missing = [s for s in slugs if s not in THEME_ASSUMPTIONS]
    if missing:
        raise SystemExit(f"THEME_ASSUMPTIONS missing entries for active themes: {missing}")

    print(f"\nactive themes: {len(slugs)}   judge status: {status}   circuit_breaker: {circuit_breaker}")
    print(f"budget: ${BUDGET:,.0f}   shared total deployment cap (all 4 schemes): "
          f"${TOTAL_DEPLOYMENT_CAP:,.0f}   n_paths: {n_paths:,}   seed: {args.seed}")

    print("\n--- per-theme magnitude/downside ASSUMPTIONS (see docstring + results doc for full "
          "rationale) ---")
    print_assumptions_table(slugs, confidence)
    print(f"\nai-power-grid node mixture (weights = ticker count, ETF-only legs = weight 1):")
    for nd in NODES_AI_POWER_GRID:
        print(f"  {nd['name']:<28} weight={nd['weight']:>2}  magnitude_mid={nd['magnitude_mid']:.2f}"
              f"  downside={nd['downside']:.0%}  binary={nd['binary']}")
    print(f"  -> blended magnitude_mid used for B/C/D allocation math: "
          f"{AI_POWER_GRID_BLENDED_MAGNITUDE:.3f}")

    # --- Scheme A reference: the REAL sizing.py function, not a reimplementation ---
    rows, cut_log, total_cap, total_factor = ws5_sizing.build_table(themes, status, circuit_breaker, BUDGET)
    scheme_A_baseline = {r["slug"]: r["final"] for r in rows}
    print(f"\nscheme A reproduced via thesis.sizing.build_table() directly (imported, not "
          f"reimplemented) -> 0% error by construction (acceptance bar was <1%).")
    print(f"scheme A total deployed: ${sum(scheme_A_baseline.values()):,.2f}  "
          f"(status={status} total cap ${total_cap:,.0f}, scale factor x{total_factor:.4f})")

    rng = np.random.default_rng(args.seed)
    u_by_slug = {s: rng.random(n_paths) for s in slugs if s != "ai-power-grid"}
    node_idx = rng.choice(len(NODES_AI_POWER_GRID), size=n_paths, p=_node_weights(NODES_AI_POWER_GRID))
    sub_u = rng.random(n_paths)
    # NOTE: u_by_slug / node_idx / sub_u are drawn ONCE and reused for BOTH the baseline and the
    # 20%-confidence-haircut sensitivity scenario below (common random numbers) -- only the
    # probability thresholds shift between scenarios, not the underlying randomness, so the
    # ranking-stability check isn't confounded by fresh sampling noise.

    csv_rows = []

    def run_scenario(conf_mult: float, label: str):
        alloc_A = scheme_A_alloc(themes, status, circuit_breaker, conf_mult) if conf_mult != 1.0 else scheme_A_baseline
        alloc_B = scheme_B_alloc(confidence, conf_mult)
        alloc_C, top5 = scheme_C_alloc(confidence, conf_mult)
        alloc_D = scheme_D_alloc(confidence, conf_mult)
        returns = build_all_returns(confidence, conf_mult, slugs, u_by_slug, node_idx, sub_u, n_paths)

        results = []
        for name, alloc in [("A_status_quo", alloc_A), ("B_conf_x_magnitude", alloc_B),
                             ("C_top5_concentration", alloc_C), ("D_kelly_lite", alloc_D)]:
            r = summarize(name, alloc, slugs, returns, n_paths)
            r["scenario"] = label
            results.append(r)
            csv_rows.append(r)

        print(f"\n--- scenario: {label} (confidence x{conf_mult}) ---")
        print_scheme_table(results)
        print(f"scheme C top-{TOP_K} membership: {top5}")
        return results

    baseline_results = run_scenario(1.0, "baseline")
    haircut_results = run_scenario(0.8, "sensitivity_conf_x0.8_cold_start_haircut")

    print("\n--- ranking stability check (baseline vs. 20%-confidence-haircut sensitivity) ---")
    print("ranking by E[PnL],  baseline:", ranking(baseline_results, "mean"))
    print("ranking by E[PnL],  haircut :", ranking(haircut_results, "mean"))
    print("ranking by cap_eff, baseline:", ranking(baseline_results, "cap_eff"))
    print("ranking by cap_eff, haircut :", ranking(haircut_results, "cap_eff"))
    same_pnl_rank = ranking(baseline_results, "mean") == ranking(haircut_results, "mean")
    same_eff_rank = ranking(baseline_results, "cap_eff") == ranking(haircut_results, "cap_eff")
    print(f"E[PnL] ranking unchanged under haircut: {same_pnl_rank}")
    print(f"capital-efficiency ranking unchanged under haircut: {same_eff_rank}")

    # --- persist CSV snapshot for reproducibility (repo convention: backtest/results/_*.csv) ---
    os.makedirs(RESULTS_DIR, exist_ok=True)
    csv_path = os.path.join(RESULTS_DIR, "_sizing_two_axis_metrics.csv")
    fieldnames = ["scenario", "name", "deployed", "funded", "max_share", "mean", "median",
                  "p5", "p95", "p_loss30", "cap_eff"]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in csv_rows:
            w.writerow({k: r[k] for k in fieldnames})
    print(f"\nmetrics CSV written: {csv_path}")
    print("\ndone.")


if __name__ == "__main__":
    main()
