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

Run: python thesis/sizing.py [--budget 41000] [--force-status PRELIMINARY|PASS|FAIL]
"""
from __future__ import annotations

import argparse
import json
import os

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
THEMES_PATH = os.path.join(ROOT, "themes.yaml")
IC_REPORT_PATH = os.path.join(ROOT, "ic_report.json")

DEFAULT_BUDGET = 41_000.0
MF_CAP_PCT = 0.50          # WS3 Sec4: same meta_factor <= 50% of satellite budget
PRELIM_TOTAL_CAP_PCT = 0.50
FAIL_TOTAL_CAP_PCT = 0.25
PRELIM_CONF_MULT = 20_000.0
PRELIM_PER_THEME_CAP = 15_000.0


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


def apply_meta_factor_cut(themes, values, budget):
    """Scale down themes sharing an over-budget meta_factor. Mutates a copy of `values`
    (dict slug -> $) and returns (new_values, cut_log) where cut_log lists which
    meta_factor groups were reduced and by what factor."""
    mf_budget_cap = MF_CAP_PCT * budget
    cur = dict(values)
    cut_log = []

    # group slugs by meta_factor
    groups = {}
    for slug, t in themes.items():
        for mf in (t.get("meta_factors") or []):
            groups.setdefault(mf, []).append(slug)

    for mf, slugs in groups.items():
        group_sum = sum(cur[s] for s in slugs)
        if group_sum > mf_budget_cap and group_sum > 0:
            factor = mf_budget_cap / group_sum
            for s in slugs:
                cur[s] *= factor
            cut_log.append((mf, slugs, group_sum, mf_budget_cap, factor))
    return cur, cut_log


def apply_total_cap(values, budget, status):
    """Final scale-down so total deployment respects the status's overall satellite cap."""
    if status == "PRELIMINARY":
        total_cap = PRELIM_TOTAL_CAP_PCT * budget
    elif status == "PASS":
        total_cap = budget
    elif status == "FAIL":
        total_cap = FAIL_TOTAL_CAP_PCT * budget
    else:
        raise ValueError(f"unknown judge status: {status!r}")

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

    conc_reduced, cut_log = apply_meta_factor_cut(active, raw, budget)
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


def run():
    ap = argparse.ArgumentParser(description="Phase-3 WS5 sizing report (display-only).")
    ap.add_argument("--budget", type=float, default=DEFAULT_BUDGET,
                     help=f"satellite budget in $ (default {DEFAULT_BUDGET:.0f})")
    ap.add_argument("--force-status", choices=["PRELIMINARY", "PASS", "FAIL"], default=None,
                     help="override judge status read from ic_report.json (for fixture testing)")
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
          f"{MF_CAP_PCT * 100:.0f}% of budget = ${MF_CAP_PCT * budget:,.0f}):")
    if cut_log:
        for mf, slugs, group_sum, cap, factor in cut_log:
            print(f"  '{mf}': raw ${group_sum:,.0f} > cap ${cap:,.0f} -> scaled x{factor:.4f} "
                  f"({len(slugs)} themes: {', '.join(slugs)})")
    else:
        print("  none over cap.")

    print("\nfootnotes:")
    print("  - Type-A crisis sleeve <=10% of satellite budget is a SEPARATE budget (WS5 Sec1.5),"
          " not shown in this table (no Type-A themes currently in registry -- all 9 are Type B).")
    print("  - Small-cap pure-play position inside a theme <= 1/3 of that theme's final $ "
          "(WS5 Sec1.3), and must carry its own kill_condition. Not itemized per-ticker here.")
    print()


if __name__ == "__main__":
    run()
