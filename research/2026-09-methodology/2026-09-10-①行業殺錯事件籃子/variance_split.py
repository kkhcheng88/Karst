# -*- coding: utf-8 -*-
"""KARST-199 收尾兩張表。

(甲) 變異拆解:一個成員十二個月超額的差異,有幾多來自「揀中邊一宗事件」,
     有幾多來自「同一個籃子裡面揀邊一家」。這條數直接答用戶那句「一注押一個故事」
     ——如果差異幾乎全部在事件之間,籃內揀股就不值得做,揀事件才值得做。

(乙) 三條問題對照:把在兩種籃子都站得住的特徵砌成三個是非問題,
     逐個事件內比較「三條全中」與「三條全不中」的十二個月超額。
     這是描述性對照表,不是模型,亦不是樣本外成績——同一批資料揀出來又在同一批資料上量。

輸出:out/variance_split.csv、out/three_questions.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from basket_core import OUT, log

COL = "T_12m_excess"


def main() -> None:
    mem = pd.read_csv(OUT / "basket_members.csv", low_memory=False)
    ev = pd.read_csv(OUT / "event_list.csv")
    main_ids = set(ev[ev["in_main_sample"] == True]["event_id"])

    rows = []
    for kind in ("新聞點名", "同SIC全體"):
        d = mem[(mem["basket_kind"] == kind) & mem["event_id"].isin(main_ids) & mem[COL].notna()].copy()
        if kind == "同SIC全體":
            d = d[d["dollar_vol_60d"] >= 1e6]
        if len(d) < 10:
            continue
        grand = d[COL].mean()
        g = d.groupby("event_id")[COL]
        n_i, mu_i = g.size(), g.mean()
        ss_between = float((n_i * (mu_i - grand) ** 2).sum())
        ss_within = float(((d[COL] - d["event_id"].map(mu_i)) ** 2).sum())
        ss_total = ss_between + ss_within
        # 籃內跨度的典型大細
        iqr = d.groupby("event_id")[COL].apply(lambda s: s.quantile(0.75) - s.quantile(0.25))
        rows.append(dict(
            籃子=kind, 事件數=int(d["event_id"].nunique()), 成員數=int(len(d)),
            事件之間佔變異=round(ss_between / ss_total, 4),
            籃內佔變異=round(ss_within / ss_total, 4),
            各事件中位數的中位=round(float(mu_i.median()), 4),
            各事件中位數最低=round(float(mu_i.min()), 4),
            各事件中位數最高=round(float(mu_i.max()), 4),
            籃內四分位距中位=round(float(iqr.median()), 4)))
    vs = pd.DataFrame(rows)
    vs.to_csv(OUT / "variance_split.csv", index=False, encoding="utf-8-sig")
    log(vs.to_string(index=False))

    # ---------------- (乙) 三條問題
    # 三條在兩種籃子都同方向站得住的:賺唔賺到現金、賺唔賺到錢、平唔平(以銷售額計)
    qrows = []
    for kind in ("新聞點名", "同SIC全體"):
        d = mem[(mem["basket_kind"] == kind) & mem["event_id"].isin(main_ids) & mem[COL].notna()].copy()
        if kind == "同SIC全體":
            d = d[d["dollar_vol_60d"] >= 1e6]
        need = ["f_ocf_margin", "f_ni_margin", "f_ps"]
        d = d.dropna(subset=need)
        if len(d) < 20:
            continue
        # 逐個事件之內比較,三條問題各自是「在這個籃子裡排上半」
        for c, q in (("f_ocf_margin", "q1"), ("f_ni_margin", "q2")):
            d[q] = d.groupby("event_id")[c].transform(lambda s: s > s.median()).astype(int)
        d["q3"] = d.groupby("event_id")["f_ps"].transform(lambda s: s < s.median()).astype(int)
        d["score"] = d["q1"] + d["q2"] + d["q3"]
        for sc, g in d.groupby("score"):
            qrows.append(dict(籃子=kind, 三條中幾條=int(sc), n=int(len(g)),
                              事件數=int(g["event_id"].nunique()),
                              中位十二個月超額=round(float(g[COL].median()), 4),
                              平均十二個月超額=round(float(g[COL].mean()), 4),
                              贏家比例=round(float((g[COL] > 0).mean()), 4)))
        base = d[COL]
        qrows.append(dict(籃子=kind, 三條中幾條=-1, n=int(len(base)),
                          事件數=int(d["event_id"].nunique()),
                          中位十二個月超額=round(float(base.median()), 4),
                          平均十二個月超額=round(float(base.mean()), 4),
                          贏家比例=round(float((base > 0).mean()), 4)))
    tq = pd.DataFrame(qrows)
    tq.to_csv(OUT / "three_questions.csv", index=False, encoding="utf-8-sig")
    log("\n三條問題(-1 = 該籃子全體基線):")
    log(tq.to_string(index=False))


if __name__ == "__main__":
    main()
