"""KARST-145 reading step: apply the frozen CRITERIA sec.6 rules mechanically.

Nothing here is a judgement call -- the plateau / lone-peak definitions were
committed (49b0a70) before any cell was computed. This script only executes them.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

MAIN = "pick_cagr_15"        # CRITERIA sec.4.8: the self-picked sleeve is the verdict number

# --- adjacency, verbatim from CRITERIA sec.6.1 -----------------------------
ENTRY_FAMILIES = {"dd": ["dd_5", "dd_10", "dd_15"], "rsi": ["rsi2d_lt10", "rsi2w_lt10"]}
ENTRY_ISOLATED = ["golden_cross"]
EXIT_FAMILIES = {"trail": ["trail_10", "trail_20"], "time": ["time_3m", "time_6m"]}
EXIT_ISOLATED = ["rsi2d_gt90", "death_cross", "drop_out"]
K_ADJ = {6: [10], 10: [6, 15], 15: [10]}
N_ADJ = {3: [5], 5: [3]}


def entry_sets():
    """All E with |E|>=2 whose members are pairwise adjacent / same family."""
    out = []
    for fam, members in ENTRY_FAMILIES.items():
        for r in range(2, len(members) + 1):
            for combo in itertools.combinations(members, r):
                out.append((fam, list(combo)))
    return out


def exit_sets():
    out = []
    for fam, members in EXIT_FAMILIES.items():
        for r in range(2, len(members) + 1):
            for combo in itertools.combinations(members, r):
                out.append((fam, list(combo)))
    return out


def neighbours(row, index):
    """Cells one step away along exactly one axis, same proxy."""
    out = []
    fam_of_entry = {m: f for f, ms in ENTRY_FAMILIES.items() for m in ms}
    fam_of_exit = {m: f for f, ms in EXIT_FAMILIES.items() for m in ms}

    if row.entry in fam_of_entry:
        for m in ENTRY_FAMILIES[fam_of_entry[row.entry]]:
            if m != row.entry:
                out.append((row.proxy, m, row.exit, row.top_n, row.k))
    if row.exit in fam_of_exit:
        for m in EXIT_FAMILIES[fam_of_exit[row.exit]]:
            if m != row.exit:
                out.append((row.proxy, row.entry, m, row.top_n, row.k))
    for kk in K_ADJ[row.k]:
        out.append((row.proxy, row.entry, row.exit, row.top_n, kk))
    for nn in N_ADJ[row.top_n]:
        out.append((row.proxy, row.entry, row.exit, nn, row.k))
    return [index[key] for key in out if key in index]


def main():
    df = pd.read_csv(OUT / "sweep.csv")
    spy = float(df["spy_cagr"].iloc[0])
    xlk = float(df["xlk_cagr"].iloc[0])
    index = {(r.proxy, r.entry, r.exit, r.top_n, r.k): r.Index for r in df.itertuples()}

    df["beats_spy"] = df[MAIN] > spy
    df["beats_xlk"] = df[MAIN] > xlk
    df["beats_both"] = df["beats_spy"] & df["beats_xlk"]

    rep = {
        "n_cells": int(len(df)),
        "spy_cagr": spy, "xlk_cagr": xlk,
        "main_metric": MAIN,
        "cells_beating_spy": int(df["beats_spy"].sum()),
        "cells_beating_xlk": int(df["beats_xlk"].sum()),
        "cells_beating_both": int(df["beats_both"].sum()),
        "cells_beating_rand_p95": int(df["beats_rand"].sum()),
        "cells_beating_pool_ew": int((df["vs_pool"] > 0).sum()),
        "main_cagr_min": float(df[MAIN].min()),
        "main_cagr_median": float(df[MAIN].median()),
        "main_cagr_max": float(df[MAIN].max()),
    }

    # ---- plateau search, per proxy and pooled ----------------------------
    def plateau_scan(sub, need_xlk):
        hits = []
        for efam, E in entry_sets():
            for xfam, X in exit_sets():
                blk = sub[sub["entry"].isin(E) & sub["exit"].isin(X)]
                need = len(E) * len(X) * 6
                if len(blk) != need:
                    continue
                ok = blk["beats_both"].all() if need_xlk else blk["beats_spy"].all()
                if ok:
                    hits.append({
                        "entry_family": efam, "entries": E,
                        "exit_family": xfam, "exits": X,
                        "n_cells": need,
                        "min_main": float(blk[MAIN].min()),
                        "median_main": float(blk[MAIN].median()),
                        "median_vs_spy": float(blk["vs_spy"].median()),
                        "median_vs_xlk": float(blk["vs_xlk"].median()),
                    })
        return hits

    rep["plateaus"] = {}
    for proxy in sorted(df["proxy"].unique()):
        sub = df[df["proxy"] == proxy]
        rep["plateaus"][proxy] = {
            "strict_beats_spy_and_xlk": plateau_scan(sub, True),
            "loose_beats_spy_only": plateau_scan(sub, False),
        }

    # near-miss diagnostics: for every candidate block, how many of its cells pass
    near = []
    for proxy in sorted(df["proxy"].unique()):
        sub = df[df["proxy"] == proxy]
        for efam, E in entry_sets():
            for xfam, X in exit_sets():
                blk = sub[sub["entry"].isin(E) & sub["exit"].isin(X)]
                if not len(blk):
                    continue
                near.append({
                    "proxy": proxy, "entries": "+".join(E), "exits": "+".join(X),
                    "n": int(len(blk)),
                    "pass_spy": int(blk["beats_spy"].sum()),
                    "pass_both": int(blk["beats_both"].sum()),
                    "median_main": round(float(blk[MAIN].median()), 2),
                    "min_main": round(float(blk[MAIN].min()), 2),
                    "max_main": round(float(blk[MAIN].max()), 2),
                })
    rep["block_pass_counts"] = sorted(near, key=lambda d: -d["pass_both"])

    # ---- lone-peak check on the best cell (CRITERIA sec.6.1) -------------
    best_i = int(df[MAIN].idxmax())
    best = df.loc[best_i]
    nb = neighbours(df.loc[best_i], index)
    nb_vals = df.loc[nb, MAIN]
    rep["best_cell"] = {
        "proxy": best["proxy"], "entry": best["entry"], "exit": best["exit"],
        "top_n": int(best["top_n"]), "k": int(best["k"]),
        "pick_cagr_15": float(best[MAIN]),
        "port_cagr_15": float(best["port_cagr_15"]),
        "vs_spy": float(best["vs_spy"]), "vs_xlk": float(best["vs_xlk"]),
        "turnover_ann": float(best["turnover_ann"]),
        "maxdd_pick": float(best["maxdd_pick"]),
        "rand_p95": float(best["rand_p95"]),
        "n_neighbours": len(nb),
        "neighbour_median": float(nb_vals.median()) if len(nb) else None,
        "neighbour_min": float(nb_vals.min()) if len(nb) else None,
        "neighbour_max": float(nb_vals.max()) if len(nb) else None,
        "neighbour_median_beats_spy": bool(nb_vals.median() > spy) if len(nb) else None,
        "neighbour_median_beats_xlk": bool(nb_vals.median() > xlk) if len(nb) else None,
    }
    best_by_proxy = {}
    for proxy in sorted(df["proxy"].unique()):
        sub = df[df["proxy"] == proxy]
        bi = int(sub[MAIN].idxmax())
        nbp = neighbours(df.loc[bi], index)
        v = df.loc[nbp, MAIN]
        best_by_proxy[proxy] = {
            "entry": df.loc[bi, "entry"], "exit": df.loc[bi, "exit"],
            "top_n": int(df.loc[bi, "top_n"]), "k": int(df.loc[bi, "k"]),
            "pick_cagr_15": float(df.loc[bi, MAIN]),
            "vs_spy": float(df.loc[bi, "vs_spy"]), "vs_xlk": float(df.loc[bi, "vs_xlk"]),
            "neighbour_median": float(v.median()) if len(nbp) else None,
        }
    rep["best_by_proxy"] = best_by_proxy

    # ---- verdict (CRITERIA sec.6.2, three permitted sentences) ----------
    any_strict = any(p["strict_beats_spy_and_xlk"] for p in rep["plateaus"].values())
    any_loose = any(p["loose_beats_spy_only"] for p in rep["plateaus"].values())
    bc = rep["best_cell"]
    if any_strict:
        verdict = "A_plateau_strict"
    elif any_loose:
        verdict = "A_plateau_loose_spy_only"
    elif bc["vs_spy"] > 0 and bc["vs_xlk"] > 0 and not (
            bc["neighbour_median_beats_spy"] and bc["neighbour_median_beats_xlk"]):
        verdict = "B_lone_peak_untrustworthy"
    else:
        verdict = "C_no_plateau"
    rep["verdict"] = verdict

    # ---- axis marginals, for describing the terrain ---------------------
    rep["marginals"] = {}
    for ax in ["entry", "exit", "top_n", "k", "proxy"]:
        g = df.groupby(ax)
        rep["marginals"][ax] = {
            str(kk): {"median_main": round(float(v[MAIN].median()), 2),
                      "max_main": round(float(v[MAIN].max()), 2),
                      "median_turnover": round(float(v["turnover_ann"].median()), 2),
                      "median_slots": round(float(v["avg_slots_filled"].median()), 2),
                      "pct_days_empty": round(float(v["pct_days_empty"].median()), 1),
                      "n_beat_spy": int(v["beats_spy"].sum()),
                      "n": int(len(v))}
            for kk, v in g
        }

    # portfolio (with SPY filler) view, reported alongside per the ticket
    rep["with_filler"] = {
        "cells_beating_spy": int((df["port_vs_spy"] > 0).sum()),
        "cells_beating_xlk": int((df["port_vs_xlk"] > 0).sum()),
        "median_port_cagr_15": round(float(df["port_cagr_15"].median()), 2),
        "max_port_cagr_15": round(float(df["port_cagr_15"].max()), 2),
    }
    rep["cost_sensitivity"] = {
        f"{bp}bps": {"median_pick": round(float(df[f"pick_cagr_{bp}"].median()), 2),
                     "max_pick": round(float(df[f"pick_cagr_{bp}"].max()), 2),
                     "n_beat_spy": int((df[f"pick_cagr_{bp}"] > spy).sum())}
        for bp in [0, 15, 25, 50]
    }

    (OUT / "analysis.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
    df.to_csv(OUT / "sweep_flagged.csv", index=False, encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items()
                      if k not in ("block_pass_counts", "marginals")},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
