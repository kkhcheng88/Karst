"""thesis/concentration.py — meta_factor concentration report (Phase-3 WS3 backlog #3,
docs/2026-07-08_phase3_ws3_lifecycle.md §4).

Spec §4 hard rule (enforced at the SIZING layer, WS5 -- not here): themes sharing a meta_factor
must not jointly deploy more than 50% of satellite capital. This script does NOT have deployment
$ yet (sizing.py is WS5, not built) -- it stands in with a PROXY: each theme's `confidence` from
themes.yaml as a weight, split evenly across a theme's meta_factors so weights sum to 1 total (a
theme tagged with 2 meta_factors contributes half its confidence to each). This is a **placeholder**
so the 6/9-themes-tagged-ai-capex concentration is visible NOW, before WS5 ships real $ sizing --
read the numbers as "share of confidence-weighted theme count", not "share of capital".

Run: python thesis/concentration.py
"""
import os
from collections import defaultdict

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
THEMES_PATH = os.path.join(ROOT, "themes.yaml")
BUDGET_CAP_PCT = 50.0   # spec §4: same meta_factor combined deployment <= 50% of satellite capital


def load_themes():
    with open(THEMES_PATH, encoding="utf-8") as fh:
        return (yaml.safe_load(fh) or {}).get("themes", {}) or {}


def compute(themes, include_status=("active", "watch")):
    """Aggregate confidence-proxy weight by meta_factor.

    Returns (rows, total_weight, theme_count_by_factor, excluded) where rows is a list of
    dicts {meta_factor, n_themes, weight, pct} sorted by pct desc.
    """
    factor_weight = defaultdict(float)
    factor_themes = defaultdict(list)
    total_weight = 0.0
    excluded = []
    for slug, t in themes.items():
        status = t.get("status", "active")
        if status not in include_status:
            excluded.append((slug, status))
            continue
        conf = t.get("confidence")
        mfs = t.get("meta_factors") or []
        if conf is None or not mfs:
            continue
        conf = float(conf)
        share = conf / len(mfs)   # split evenly across a theme's tagged meta_factors
        for mf in mfs:
            factor_weight[mf] += share
            factor_themes[mf].append(slug)
        total_weight += conf

    rows = []
    for mf, w in factor_weight.items():
        pct = (w / total_weight * 100.0) if total_weight else 0.0
        rows.append({
            "meta_factor": mf,
            "n_themes": len(factor_themes[mf]),
            "themes": factor_themes[mf],
            "weight": w,
            "pct": pct,
        })
    rows.sort(key=lambda r: r["pct"], reverse=True)
    return rows, total_weight, excluded


def run():
    themes = load_themes()
    rows, total_weight, excluded = compute(themes)

    print("\n=== thesis concentration report (meta_factor x confidence-proxy weight) ===")
    print("NOTE: deployment $ does not exist yet (sizing.py is WS5, not built). This uses each")
    print("theme's `confidence` from themes.yaml as a PROXY weight (split evenly across a theme's")
    print("meta_factors). Read as relative concentration risk, NOT actual capital allocation.\n")

    if excluded:
        print(f"excluded (status not active/watch): {len(excluded)}")
        for slug, status in excluded:
            print(f"  {slug}: status={status}")
        print()

    print(f"{'meta_factor':<20}{'n_themes':>10}{'weight':>10}{'share %':>10}  themes")
    print("-" * 90)
    for r in rows:
        print(f"{r['meta_factor']:<20}{r['n_themes']:>10}{r['weight']:>10.3f}{r['pct']:>9.1f}%  "
              f"{', '.join(r['themes'])}")

    print(f"\ntotal confidence-weight across {sum(r['n_themes'] for r in rows)} theme-tags: "
          f"{total_weight:.3f}")

    if rows:
        top = rows[0]
        print(f"\nLARGEST meta_factor by theme-count and weighted share: '{top['meta_factor']}' "
              f"({top['n_themes']} themes, {top['pct']:.1f}% of confidence-weight)")

    print(f"\nBUDGET CHECK (spec Sec4 cap: {BUDGET_CAP_PCT:.0f}% of satellite capital per meta_factor "
          f"-- enforced by WS5 sizing.py once it exists; this is an early-warning proxy only):")
    breaches = [r for r in rows if r["pct"] > BUDGET_CAP_PCT]
    if breaches:
        for r in breaches:
            print(f"  EXCESS WARNING: '{r['meta_factor']}' at {r['pct']:.1f}% > {BUDGET_CAP_PCT:.0f}% "
                  f"cap ({r['n_themes']} themes: {', '.join(r['themes'])})")
    else:
        print(f"  none over {BUDGET_CAP_PCT:.0f}% (proxy-weight basis) -- but see note below: this is "
              f"theme-count/confidence, not real $; WS5 sizing may still concentrate differently.")

    print("\n(Deployment $ pending WS5 sizing.py -- this report is a confidence-proxy stand-in so the "
          "ai-capex concentration is visible NOW, before real sizing exists.)")


if __name__ == "__main__":
    run()
