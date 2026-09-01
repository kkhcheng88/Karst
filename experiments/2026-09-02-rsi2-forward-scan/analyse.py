"""KARST-137 判讀:照 CRITERIA.md 第七節事前寫死的讀法,產平原/孤峰表與分段表。

輸出:plateau.csv、best_cells.csv、analysis_out.txt
不落任何及格宣稱(協議第七節第 7 條)。
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
PAN = HERE / "panorama.csv"

FAM = ["window", "arm", "direction", "bar", "rsi_kind", "style"]
PLATEAU_POS_SHARE = 0.60      # CRITERIA 第七節

lines: list[str] = []


def out(*a) -> None:
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)


def neighbours(row: pd.Series, fam: pd.DataFrame) -> float:
    """最強格鄰域的最低超額(甲式 N±1;乙式門檻各上下一檔)。"""
    if row["style"] == "甲":
        nb = fam[(fam["H"] == row["H"]) & (fam["N"].sub(row["N"]).abs() == 1)]
    else:
        es = sorted(fam["E"].dropna().unique())
        xs = sorted(fam["X"].dropna().unique())
        def step(v, arr):
            i = arr.index(v)
            return [arr[j] for j in (i - 1, i + 1) if 0 <= j < len(arr)]
        nb = fam[(fam["H"] == row["H"])
                 & (((fam["E"].isin(step(row["E"], es))) & (fam["X"] == row["X"]))
                    | ((fam["X"].isin(step(row["X"], xs))) & (fam["E"] == row["E"])))]
    return float(nb["exc_spy"].min()) if len(nb) else np.nan


def main() -> None:
    p = pd.read_csv(PAN)
    cells = p[p["style"] != "基線"].copy()
    base = p[p["style"] == "基線"]

    out("== 基線 ==")
    out(base[["window", "bar", "params", "n_periods", "years", "cagr_pct",
              "maxdd_pct"]].to_string(index=False))

    rows, best = [], []
    for key, fam in cells.groupby(FAM):
        fam = fam.dropna(subset=["exc_spy"])
        if fam.empty:
            continue
        b = fam.loc[fam["exc_spy"].idxmax()]
        rec = dict(zip(FAM, key))
        rec.update(
            n_cells=len(fam),
            best_params=b["params"], best_exc_spy=b["exc_spy"], best_t_spy=b["t_spy"],
            nb_med=float(fam["n_periods"].median()),
            fam_med_exc=round(float(fam["exc_spy"].median()), 4),
            fam_p10_exc=round(float(fam["exc_spy"].quantile(0.10)), 4),
            pct_positive=round(float((fam["exc_spy"] > 0).mean()), 4),
            pct_t_gt2=round(float((fam["t_spy"] > 2).mean()), 4),
            med_pre13=round(float(fam["exc_spy_pre13"].median()), 4),
            med_post13=round(float(fam["exc_spy_post13"].median()), 4),
            pct_pos_pre13=round(float((fam["exc_spy_pre13"] > 0).mean()), 4),
            pct_pos_post13=round(float((fam["exc_spy_post13"] > 0).mean()), 4),
            med_h1=round(float(fam["exc_spy_h1"].median()), 4),
            med_h2=round(float(fam["exc_spy_h2"].median()), 4),
            nbr_min_exc=round(neighbours(b, fam), 4),
        )
        rec["verdict"] = (
            "平原" if (rec["fam_med_exc"] > 0
                       and rec["pct_positive"] >= PLATEAU_POS_SHARE
                       and rec["nbr_min_exc"] == rec["nbr_min_exc"]
                       and rec["nbr_min_exc"] > 0)
            else ("孤峰" if rec["best_exc_spy"] > 0 else "無峰"))
        rows.append(rec)
        best.append(dict(zip(FAM, key)) | {
            "params": b["params"], "cagr_pct": b["cagr_pct"],
            "exc_spy": b["exc_spy"], "t_spy": b["t_spy"],
            "exc_ew9": b["exc_ew9"], "t_ew9": b["t_ew9"],
            "exc_spy_pre13": b["exc_spy_pre13"], "exc_spy_post13": b["exc_spy_post13"],
            "exc_spy_h1": b["exc_spy_h1"], "exc_spy_h2": b["exc_spy_h2"],
            "ann_turnover": b["ann_turnover"], "pct_in_mkt": b["pct_in_mkt"]})

    pl = pd.DataFrame(rows).sort_values(["window", "arm", "direction", "bar",
                                         "rsi_kind", "style"])
    pl.to_csv(HERE / "plateau.csv", index=False, encoding="utf-8-sig")
    bc = pd.DataFrame(best).sort_values("exc_spy", ascending=False)
    bc.to_csv(HERE / "best_cells.csv", index=False, encoding="utf-8-sig")

    out("\n== 逐族平原/孤峰判讀(主窗,主方向 買便宜)==")
    m = pl[(pl["window"] == "主窗") & (pl["direction"] == "買便宜")]
    out(m[["arm", "bar", "rsi_kind", "style", "best_params", "best_exc_spy",
           "best_t_spy", "fam_med_exc", "pct_positive", "nbr_min_exc",
           "med_post13", "pct_pos_post13", "verdict"]].to_string(index=False))

    out("\n== 逐族(主窗,鏡像方向 買貴)==")
    mi = pl[(pl["window"] == "主窗") & (pl["direction"] == "買貴")]
    out(mi[["arm", "bar", "rsi_kind", "style", "best_params", "best_exc_spy",
            "best_t_spy", "fam_med_exc", "pct_positive", "med_post13",
            "verdict"]].to_string(index=False))

    out("\n== ey_lag 全期(不同窗,不可與前瞻臂直接相比)==")
    fp = pl[pl["window"] == "ey_lag全期"]
    out(fp[["arm", "direction", "bar", "rsi_kind", "style", "best_params",
            "best_exc_spy", "best_t_spy", "fam_med_exc", "pct_positive",
            "med_post13", "verdict"]].to_string(index=False))

    out("\n== 每(臂×方向×bar×式)最強格,主窗,按超額排 ==")
    top = bc[bc["window"] == "主窗"]
    out(top[["arm", "direction", "bar", "style", "params", "cagr_pct", "exc_spy",
             "t_spy", "exc_spy_pre13", "exc_spy_post13"]].head(25)
        .to_string(index=False))

    out("\n== 核心問題:2013 前後,主窗主方向逐臂族內中位數 ==")
    g = (m.groupby("arm")
           .agg(族數=("verdict", "count"),
                平原數=("verdict", lambda s: int((s == "平原").sum())),
                全期中位=("fam_med_exc", "median"),
                前段中位=("med_pre13", "median"),
                後段中位=("med_post13", "median"),
                後段正格比中位=("pct_pos_post13", "median"),
                最強格超額=("best_exc_spy", "max")))
    out(g.to_string(float_format="%.3f"))

    out("\n== 同一問題,鏡像方向 ==")
    gi = (mi.groupby("arm")
            .agg(族數=("verdict", "count"),
                 平原數=("verdict", lambda s: int((s == "平原").sum())),
                 全期中位=("fam_med_exc", "median"),
                 前段中位=("med_pre13", "median"),
                 後段中位=("med_post13", "median"),
                 最強格超額=("best_exc_spy", "max")))
    out(gi.to_string(float_format="%.3f"))

    (HERE / "analysis_out.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
