# -*- coding: utf-8 -*-
"""KARST-148 analysis: differences against all four benchmarks, and the
CRITERIA sec.9 verdict computed mechanically from the frozen rules.
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"

BENCH = {"SPY": "基準:SPY含息", "XLK": "基準:XLK含息", "POOL": "基準:同池等權"}


def main() -> None:
    arms = pd.read_csv(OUT / "arms.csv")
    band = json.loads((OUT / "random_band.json").read_text(encoding="utf-8"))

    rows = []
    for period, g in arms.groupby("period"):
        ref = {k: g[g["arm"] == v]["cagr_15"].iloc[0] for k, v in BENCH.items()}
        b = band[period]
        for _, r in g.iterrows():
            rows.append({
                "arm": r["arm"], "period": period,
                "cagr_15": r["cagr_15"], "mdd_15": r["mdd_15"],
                "turnover_yr": r["turnover_yr"],
                "vs_SPY_pp": (r["cagr_15"] - ref["SPY"]) * 100,
                "vs_XLK_pp": (r["cagr_15"] - ref["XLK"]) * 100,
                "vs_pool_pp": (r["cagr_15"] - ref["POOL"]) * 100,
                "vs_rand_p50_pp": (r["cagr_15"] - b["p50"]) * 100,
                "rand_p5": b["p5"], "rand_p95": b["p95"],
                "above_rand_p95": bool(r["cagr_15"] > b["p95"]),
            })
    vs = pd.DataFrame(rows)
    vs.round(4).to_csv(OUT / "vs_benchmarks.csv", index=False, encoding="utf-8")

    # ---- CRITERIA sec.9 verdict, applied mechanically
    nb = pd.read_csv(OUT / "neighbourhood.csv")
    full = nb[nb["period"] == "全期"]
    later = nb[nb["period"] == "乙期(2013起)"]
    spy_f = arms[(arms["arm"] == BENCH["SPY"]) & (arms["period"] == "全期")]["cagr_15"].iloc[0]
    xlk_f = arms[(arms["arm"] == BENCH["XLK"]) & (arms["period"] == "全期")]["cagr_15"].iloc[0]
    spy_b = arms[(arms["arm"] == BENCH["SPY"]) & (arms["period"] == "乙期(2013起)")]["cagr_15"].iloc[0]
    xlk_b = arms[(arms["arm"] == BENCH["XLK"]) & (arms["period"] == "乙期(2013起)")]["cagr_15"].iloc[0]

    main_f = full[(full["n"] == 3) & (full["drop_pct"] == 0.20)]["cagr_15"].iloc[0]
    main_b = later[(later["n"] == 3) & (later["drop_pct"] == 0.20)]["cagr_15"].iloc[0]
    med_f = float(full["cagr_15"].median())

    strict = int(((full["cagr_15"] >= spy_f) & (full["cagr_15"] >= xlk_f)).sum())
    loose = int((full["cagr_15"] >= spy_f).sum())

    verdict = {
        "window": "2010-03-01 .. 2026-08-31",
        "beat_xlk_gate": {
            "main_cell_full_ge_XLK": bool(main_f >= xlk_f),
            "grid_median_full_ge_XLK": bool(med_f >= xlk_f),
            "main_cell_2013_ge_XLK": bool(main_b >= xlk_b),
            "all_three": bool(main_f >= xlk_f and med_f >= xlk_f and main_b >= xlk_b),
        },
        "grid": {
            "main_cell_cagr_15": round(float(main_f), 5),
            "median_cagr_15": round(med_f, 5),
            "min_cagr_15": round(float(full["cagr_15"].min()), 5),
            "max_cagr_15": round(float(full["cagr_15"].max()), 5),
            "cells_beating_SPY_and_XLK": strict,
            "cells_beating_SPY": loose,
        },
        "benchmarks": {"SPY_full": round(float(spy_f), 5), "XLK_full": round(float(xlk_f), 5),
                       "SPY_2013": round(float(spy_b), 5), "XLK_2013": round(float(xlk_b), 5)},
        "plateau_strict": strict >= 6,
        "plateau_loose": loose >= 6,
        "lone_peak": bool(float(full["cagr_15"].max()) >= spy_f
                          and float(full["cagr_15"].max()) >= xlk_f),
        "composite_inside_luck_band": bool(band["全期"]["p5"] <= main_f <= band["全期"]["p95"]),
        "conclusion": None,
    }
    if verdict["plateau_strict"] or verdict["plateau_loose"]:
        verdict["conclusion"] = "甲:有平原"
    elif verdict["lone_peak"]:
        verdict["conclusion"] = "乙:有孤峰但不可信"
    else:
        verdict["conclusion"] = "丙:無平原"

    (OUT / "verdict.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2),
                                      encoding="utf-8")

    # fold the preparation-step results into meta.json (acceptance criterion 1)
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    meta["prep_liabilities"] = json.loads((OUT / "prep_liabilities.json").read_text(encoding="utf-8"))
    meta["prep_cik"] = json.loads((OUT / "prep_cik.json").read_text(encoding="utf-8"))
    meta["leak_check"] = json.loads((OUT / "leak_check.json").read_text(encoding="utf-8"))
    meta["verdict"] = verdict
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                   encoding="utf-8")

    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    print(vs[vs["period"] == "全期"].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
