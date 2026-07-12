"""thesis/sizing.py — Phase-3 WS5 sizing report (docs/2026-07-08_phase3_ws5_expression.md
Sec1-2, backlog #1).

Pure DISPLAY tool. Reads themes.yaml (active themes) + ic_report.json (judge status /
circuit_breaker) + a satellite budget parameter, and prints a target-$ table per theme. It
does NOT write to any registry / state file.

Rules (spec Sec1-2):
  PRELIMINARY : per-theme raw cap = min(confidence * $20k, $15k); total satellite
                deployment capped at 50% of budget.
  PASS        : total deployment = 100% of budget; per-theme = confidence * budget / sum(conf).
  FAIL (circuit_breaker: true): total deployment capped at 25% of budget, "new-position
                freeze" (only-decrease is an external/session-level discipline this
                stateless script cannot enforce -- it is flagged in the output).

Concentration cut (WS3 Sec4): themes sharing a meta_factor may not jointly deploy more
than 50% of the satellite budget. Applied AFTER the per-theme raw cap, BEFORE the final
total-budget scale-down, so the printed column order is:
    raw cap -> concentration-reduced -> final target $

meta_factor cap basis fix (2026-07-13, docs/2026-07-08_phase3_ws5_expression.md Sec8 known
refinement): the cap is now 50% of the STATUS's actual total deployment cap (e.g. 50% of the
PRELIMINARY 50%-of-budget pool = 25% of budget), not 50% of the raw nominal budget -- the old
basis let a meta_factor end up at ~56% of what was ACTUALLY deployed during PRELIMINARY,
because the group cut and the total-cap cut both referenced the same $41k figure independently.

v2 shadow (2026-07-13, docs/2026-07-12_fable_investment_logic_review.md P0-1): a SEPARATE,
side-by-side conf x magnitude two-axis formula, run with --v2-shadow. Does not replace v1 --
v1's $ table is still the operative one; v2 is logged for comparison only (shadow A/B ledger,
Fable review's explicit validation plan: two quarters of parallel paper record before either
formula is trusted to move real capital). See build_table_v2() docstring for the exact rule.

Run: python thesis/sizing.py [--budget 41000] [--force-status PRELIMINARY|PASS|FAIL] [--v2-shadow]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
THEMES_PATH = os.path.join(ROOT, "themes.yaml")
IC_REPORT_PATH = os.path.join(ROOT, "ic_report.json")

DEFAULT_BUDGET = 41_000.0
MF_CAP_PCT = 0.50          # WS3 Sec4: same meta_factor <= 50% of the ACTUAL deployment cap
PRELIM_TOTAL_CAP_PCT = 0.50
FAIL_TOTAL_CAP_PCT = 0.25
PRELIM_CONF_MULT = 20_000.0
PRELIM_PER_THEME_CAP = 15_000.0

# --- v2 shadow constants (P0-1 spec) ---
V2_MAGNITUDE_CONF_GATE = 0.25   # below this, magnitude bonus suppressed (score = conf alone,
                                 # not conf * log2(magnitude)) -- a low-confidence thesis
                                 # shouldn't rank up just because its (unverified) magnitude
                                 # assumption is large
V2_DEFAULT_MAGNITUDE_MID = 2.0  # placeholder for themes with no per-node magnifier rubric run
                                 # yet (14/15 themes as of 2026-07-13 -- only ai-power-grid has
                                 # nodes: with real magnitude_tier data). Matches the modal
                                 # "late_priced" category (1.5-2.0x) from the 2026-07-12 decision
                                 # analysis's own ad-hoc table, used here only as an honest
                                 # documented default, not a re-derived measurement.
V2_TOP_K = 6                    # deploy only top 5-7 by score (spec's stated range, midpoint)
V2_MIN_POSITION = 4_000.0       # below this, position -> $0 (stays watch); "one affordable
                                 # LEAP / one meaningful equity position" per the spec
V2_BINARY_MICRO_POSITION = 1_000.0  # event-binary themes: fixed micro-position, excluded from
                                     # the score ranking entirely (option/event framing)


def load_themes():
    with open(THEMES_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("themes", {}) or {}


def load_judge():
    with open(IC_REPORT_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def raw_cap(status, conf, budget, sum_conf_pass):
    """Per-theme raw cap before any concentration cut, per judge status."""
    if status == "PRELIMINARY":
        return min(conf * PRELIM_CONF_MULT, PRELIM_PER_THEME_CAP)
    if status == "PASS":
        if sum_conf_pass <= 0:
            return 0.0
        return conf * budget / sum_conf_pass
    if status == "FAIL":
        # FAIL: "only decrease, never increase" is a session-level discipline this
        # stateless script can't track (no prior-target state). We size as if PRELIMINARY
        # rules still apply for the raw cap, then let the 25% total cap do the real work.
        return min(conf * PRELIM_CONF_MULT, PRELIM_PER_THEME_CAP)
    raise ValueError(f"unknown judge status: {status!r}")


def total_cap_for_status(status, budget):
    """The status's overall satellite deployment cap in $. Single source of truth -- used both
    by apply_total_cap() and as the meta_factor cap BASIS (2026-07-13 fix, WS5 Sec8: the
    meta_factor 50% cap must be 50% of what can actually be deployed, not 50% of the raw
    nominal budget, otherwise a group's real share of the deployed pool can exceed the
    intended 50% -- see build_table()'s call site for the concrete before/after)."""
    if status == "PRELIMINARY":
        return PRELIM_TOTAL_CAP_PCT * budget
    if status == "PASS":
        return budget
    if status == "FAIL":
        return FAIL_TOTAL_CAP_PCT * budget
    raise ValueError(f"unknown judge status: {status!r}")


def apply_meta_factor_cut(themes, values, cap_basis):
    """Scale down themes sharing an over-cap meta_factor. `cap_basis` is the $ amount that
    MF_CAP_PCT is taken AGAINST -- pass total_cap_for_status(...)'s return value, not the raw
    budget (2026-07-13 fix; see total_cap_for_status docstring). Mutates a copy of `values`
    (dict slug -> $) and returns (new_values, cut_log) where cut_log lists which
    meta_factor groups were reduced and by what factor."""
    mf_cap = MF_CAP_PCT * cap_basis
    cur = dict(values)
    cut_log = []

    # group slugs by meta_factor
    groups = {}
    for slug, t in themes.items():
        for mf in (t.get("meta_factors") or []):
            groups.setdefault(mf, []).append(slug)

    for mf, slugs in groups.items():
        group_sum = sum(cur[s] for s in slugs)
        if group_sum > mf_cap and group_sum > 0:
            factor = mf_cap / group_sum
            for s in slugs:
                cur[s] *= factor
            cut_log.append((mf, slugs, group_sum, mf_cap, factor))
    return cur, cut_log


def apply_total_cap(values, budget, status):
    """Final scale-down so total deployment respects the status's overall satellite cap."""
    total_cap = total_cap_for_status(status, budget)
    total = sum(values.values())
    if total <= total_cap or total <= 0:
        return dict(values), total_cap, 1.0
    factor = total_cap / total
    return {k: v * factor for k, v in values.items()}, total_cap, factor


def build_table(themes, judge_status, circuit_breaker, budget):
    active = {slug: t for slug, t in themes.items() if t.get("status", "active") == "active"}

    sum_conf_pass = sum(float(t.get("confidence") or 0.0) for t in active.values())

    raw = {}
    for slug, t in active.items():
        conf = float(t.get("confidence") or 0.0)
        raw[slug] = raw_cap(judge_status, conf, budget, sum_conf_pass)

    total_cap = total_cap_for_status(judge_status, budget)
    conc_reduced, cut_log = apply_meta_factor_cut(active, raw, total_cap)
    final, total_cap, total_factor = apply_total_cap(conc_reduced, budget, judge_status)

    rows = []
    for slug, t in sorted(active.items(), key=lambda kv: -float(kv[1].get("confidence") or 0.0)):
        conf = float(t.get("confidence") or 0.0)
        mfs = ",".join(t.get("meta_factors") or [])
        rows.append({
            "slug": slug,
            "confidence": conf,
            "meta_factors": mfs,
            "raw_cap": raw[slug],
            "conc_reduced": conc_reduced[slug],
            "final": final[slug],
        })
    return rows, cut_log, total_cap, total_factor


# ============================================================================
# v2 SHADOW (2026-07-13) -- docs/2026-07-12_fable_investment_logic_review.md P0-1.
# Does NOT replace anything above. Purely an additional, side-by-side computation for the
# shadow A/B paper ledger (two quarters, per the review's validation plan) before either
# formula is trusted with real capital.
# ============================================================================

_MAG_TIER_RE = re.compile(r"(\d+(?:\.\d+)?)-?(\d+(?:\.\d+)?)?x")


def parse_magnitude_tier(tier_str):
    """'2-3x' -> 2.5, '5-10x-binary' -> 7.5, '3-5x-durable' -> 4.0, '2x' -> 2.0.
    Returns None if the string doesn't match the expected shape (fails loud upstream via the
    None check in theme_magnitude_mid, not silently)."""
    if not tier_str:
        return None
    m = _MAG_TIER_RE.match(str(tier_str))
    if not m:
        return None
    lo = float(m.group(1))
    hi = float(m.group(2)) if m.group(2) else lo
    return (lo + hi) / 2.0


def theme_magnitude_mid(theme):
    """Ticker-count-weighted blend of node-level magnitude_tier (same method the 2026-07-12
    decision analysis used for ai-power-grid). Returns (mid, source): source='nodes' if real
    per-node magnifier data exists, 'default' if this theme hasn't had the per-node rubric run
    yet (as of 2026-07-13, that's 14/15 themes -- P2 backlog item to extend it) and we fall
    back to V2_DEFAULT_MAGNITUDE_MID. Never silently invents a number attributed to real data."""
    nodes = theme.get("nodes")
    if not nodes:
        return V2_DEFAULT_MAGNITUDE_MID, "default"
    total_w, total = 0, 0.0
    for n in nodes:
        mid = parse_magnitude_tier(n.get("magnitude_tier"))
        if mid is None:
            continue
        w = max(len(n.get("tickers") or []), 1)  # ETF-only legs (tickers: []) still weight 1
        total += mid * w
        total_w += w
    if total_w == 0:
        return V2_DEFAULT_MAGNITUDE_MID, "default"
    return total / total_w, "nodes"


def is_event_binary(theme):
    """Data-driven proxy for 'event-binary' (option/event framing, not score-ranked): themes.yaml
    cycle_stage == 'event-driven'. Note this is NARROWER than the 2026-07-12 decision analysis's
    own ad-hoc classification (which also flagged space-satellite, an 'early' cycle_stage theme,
    via a self-described "自訂assumption" not backed by a themes.yaml field) -- deliberately using
    only the real, reproducible field here rather than hard-coding a ticker list."""
    return theme.get("cycle_stage") == "event-driven"


def build_table_v2(themes, judge_status, budget):
    """Shadow v2 sizing: score = conf * log2(magnitude_mid), with the magnitude bonus
    suppressed (score = conf alone) below V2_MAGNITUDE_CONF_GATE so an unverified large
    magnitude assumption can't rank up a low-confidence thesis. Deploy only the top V2_TOP_K by
    score, each position floored at V2_MIN_POSITION (else $0, stays watch -- not redistributed
    to neighbors). Event-binary themes get a fixed V2_BINARY_MICRO_POSITION, excluded from
    ranking entirely. Concentration cut applied AFTER selection (the v1 reversal-bug fix,
    applied here too) using the same total_cap_for_status basis as v1.

    Returns (rows, binary_rows, cut_log, total_cap) -- rows sorted by final $ descending."""
    active = {slug: t for slug, t in themes.items() if t.get("status", "active") == "active"}
    binary_slugs = {slug for slug, t in active.items() if is_event_binary(t)}
    scoreable = {slug: t for slug, t in active.items() if slug not in binary_slugs}

    scored = []
    for slug, t in scoreable.items():
        conf = float(t.get("confidence") or 0.0)
        mag_mid, mag_source = theme_magnitude_mid(t)
        if conf >= V2_MAGNITUDE_CONF_GATE:
            score = conf * math.log2(mag_mid)
        else:
            score = conf  # magnitude bonus suppressed -- score = confidence alone
        scored.append({"slug": slug, "confidence": conf, "magnitude_mid": mag_mid,
                        "magnitude_source": mag_source, "score": score})
    scored.sort(key=lambda r: -r["score"])
    top_k = [r for r in scored[:V2_TOP_K] if r["score"] > 0]

    total_cap = total_cap_for_status(judge_status, budget)
    score_sum = sum(r["score"] for r in top_k)
    raw = {slug: 0.0 for slug in scoreable}  # every scoreable theme needs an entry -- apply_
                                              # meta_factor_cut groups by the FULL theme dict,
                                              # not just top_k, so a non-selected group-mate
                                              # would KeyError otherwise
    for r in top_k:
        raw[r["slug"]] = (r["score"] / score_sum * total_cap) if score_sum > 0 else 0.0
    # $ floor: below it -> $0, stays watch. NOT redistributed (conservative: a name that
    # doesn't clear the floor doesn't donate its slot to inflate its neighbors' size).
    for slug in list(raw):
        if raw[slug] < V2_MIN_POSITION:
            raw[slug] = 0.0

    conc_reduced, cut_log = apply_meta_factor_cut(scoreable, raw, total_cap)
    top_k_slugs = {r["slug"] for r in top_k if raw.get(r["slug"], 0.0) > 0}

    rows = []
    for r in scored:
        selected = r["slug"] in top_k_slugs
        final = conc_reduced.get(r["slug"], 0.0)
        rows.append({**r, "selected": selected, "final": final})
    rows.sort(key=lambda r: -r["final"])

    binary_rows = [{"slug": s, "confidence": float(active[s].get("confidence") or 0.0),
                     "final": V2_BINARY_MICRO_POSITION} for s in sorted(binary_slugs)]
    return rows, binary_rows, cut_log, total_cap


def run():
    ap = argparse.ArgumentParser(description="Phase-3 WS5 sizing report (display-only).")
    ap.add_argument("--budget", type=float, default=DEFAULT_BUDGET,
                     help=f"satellite budget in $ (default {DEFAULT_BUDGET:.0f})")
    ap.add_argument("--force-status", choices=["PRELIMINARY", "PASS", "FAIL"], default=None,
                     help="override judge status read from ic_report.json (for fixture testing)")
    ap.add_argument("--v2-shadow", action="store_true",
                     help="also print the v2 shadow sizing (conf x magnitude, P0-1) side by "
                          "side with the operative v1 table -- v1 remains the real output")
    args = ap.parse_args()

    themes = load_themes()
    judge = load_judge()

    status = args.force_status or judge.get("status", "PRELIMINARY")
    circuit_breaker = bool(judge.get("circuit_breaker", False)) or status == "FAIL"
    if args.force_status == "FAIL":
        circuit_breaker = True

    budget = args.budget
    rows, cut_log, total_cap, total_factor = build_table(themes, status, circuit_breaker, budget)

    print("\n=== thesis sizing report (WS5) ===")
    print(f"judge status: {status}"
          f"{'  [FORCED for fixture test]' if args.force_status else ''}"
          f"  circuit_breaker={circuit_breaker}")
    print(f"satellite budget: ${budget:,.0f}")
    if status == "FAIL" or circuit_breaker:
        print("*** NEW-POSITION FREEZE (熔斷): only decrease, never increase vs current "
              "holdings -- this script cannot see current holdings, so treat 'final' below "
              "as an UPPER BOUND, not a target to size UP to. Wait for session review. ***")

    header = f"{'theme':<24}{'conf':>7}{'meta_factor':>14}{'raw_cap':>12}{'conc_reduced':>14}{'final_$':>12}"
    print("\n" + header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['slug']:<24}{r['confidence']:>7.2f}{r['meta_factors']:>14}"
              f"{r['raw_cap']:>12,.0f}{r['conc_reduced']:>14,.0f}{r['final']:>12,.0f}")

    total_raw = sum(r["raw_cap"] for r in rows)
    total_conc = sum(r["conc_reduced"] for r in rows)
    total_final = sum(r["final"] for r in rows)
    print("-" * len(header))
    print(f"{'TOTAL':<24}{'':>7}{'':>14}{total_raw:>12,.0f}{total_conc:>14,.0f}{total_final:>12,.0f}")
    print(f"\ntotal deployment cap for status={status}: ${total_cap:,.0f} "
          f"({total_cap / budget * 100:.0f}% of budget)")
    if total_factor < 1.0:
        print(f"final total-cap scale-down applied: x{total_factor:.4f} "
              f"(conc-reduced total ${total_conc:,.0f} > cap ${total_cap:,.0f})")
    else:
        print("no final total-cap scale-down needed (conc-reduced total already within cap)")

    print("\nmeta_factor concentration cuts (WS3 Sec4, cap "
          f"{MF_CAP_PCT * 100:.0f}% of the ${total_cap:,.0f} actual deployment cap = "
          f"${MF_CAP_PCT * total_cap:,.0f}; basis fixed 2026-07-13, was 50% of raw budget):")
    if cut_log:
        for mf, slugs, group_sum, cap, factor in cut_log:
            print(f"  '{mf}': raw ${group_sum:,.0f} > cap ${cap:,.0f} -> scaled x{factor:.4f} "
                  f"({len(slugs)} themes: {', '.join(slugs)})")
    else:
        print("  none over cap.")

    if args.v2_shadow:
        v2_rows, v2_binary, v2_cut_log, v2_total_cap = build_table_v2(themes, status, budget)
        print("\n=== v2 SHADOW (conf x magnitude, P0-1) -- NOT operative, comparison only ===")
        print(f"deployment cap: ${v2_total_cap:,.0f} ({v2_total_cap / budget * 100:.0f}% of "
              f"budget)  |  top-{V2_TOP_K}, ${V2_MIN_POSITION:,.0f} floor, "
              f"magnitude gate @ conf>={V2_MAGNITUDE_CONF_GATE}")
        v2_header = (f"{'theme':<24}{'conf':>7}{'mag_mid':>9}{'mag_src':>9}{'score':>8}"
                     f"{'sel':>5}{'final_$':>10}{'v1_final_$':>12}{'v1_rank_delta':>14}")
        print("\n" + v2_header)
        print("-" * len(v2_header))
        v1_final_by_slug = {r["slug"]: r["final"] for r in rows}
        v1_rank_by_slug = {r["slug"]: i + 1 for i, r in enumerate(
            sorted(rows, key=lambda r: -r["final"]))}
        v2_rank_by_slug = {r["slug"]: i + 1 for i, r in enumerate(v2_rows)}
        for r in v2_rows:
            v1_final = v1_final_by_slug.get(r["slug"], 0.0)
            delta = v1_rank_by_slug.get(r["slug"], len(rows)) - v2_rank_by_slug[r["slug"]]
            print(f"{r['slug']:<24}{r['confidence']:>7.2f}{r['magnitude_mid']:>9.2f}"
                  f"{r['magnitude_source']:>9}{r['score']:>8.3f}"
                  f"{'Y' if r['selected'] else '-':>5}{r['final']:>10,.0f}"
                  f"{v1_final:>12,.0f}{delta:>+14d}")
        if v2_binary:
            print("\nevent-binary (fixed micro-position, excluded from ranking):")
            for r in v2_binary:
                print(f"  {r['slug']:<24}conf={r['confidence']:.2f}  final=${r['final']:,.0f}")
        v2_total = sum(r["final"] for r in v2_rows) + sum(r["final"] for r in v2_binary)
        print(f"\nv2 total deployed: ${v2_total:,.0f}  (v1 total: ${total_final:,.0f})")
        if v2_total < 0.6 * v2_total_cap:
            print(f"  (v2 under-deploys its own cap here NOT from a bug: with most themes "
                  f"sharing the same default magnitude, their scores bunch too close together "
                  f"for any one of them to individually clear the ${V2_MIN_POSITION:,.0f} "
                  f"floor once a real-magnitude theme (ai-power-grid) pulls ahead in the same "
                  f"top-K -- extending the per-node magnifier rubric to more themes (magnifier "
                  f"backlog P2 #12) would differentiate scores enough to change this)")
        if v2_cut_log:
            print("v2 meta_factor cuts:")
            for mf, slugs, group_sum, cap, factor in v2_cut_log:
                print(f"  '{mf}': raw ${group_sum:,.0f} > cap ${cap:,.0f} -> scaled x{factor:.4f} "
                      f"({len(slugs)} themes: {', '.join(slugs)})")
        n_default_mag = sum(1 for r in v2_rows if r["magnitude_source"] == "default")
        if n_default_mag:
            print(f"\n({n_default_mag}/{len(v2_rows)} scoreable themes used the "
                  f"${V2_DEFAULT_MAGNITUDE_MID:.1f}x DEFAULT magnitude placeholder -- no "
                  f"per-node magnifier rubric run yet for them, see magnifier P2 backlog #12)")

    print("\nfootnotes:")
    print("  - Type-A crisis sleeve <=10% of satellite budget is a SEPARATE budget (WS5 Sec1.5),"
          " not shown in this table (no Type-A themes currently in registry -- all 9 are Type B).")
    print("  - Small-cap pure-play position inside a theme <= 1/3 of that theme's final $ "
          "(WS5 Sec1.3), and must carry its own kill_condition. Not itemized per-ticker here.")
    print()


if __name__ == "__main__":
    run()
