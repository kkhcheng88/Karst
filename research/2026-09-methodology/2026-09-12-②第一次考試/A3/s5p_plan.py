# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2):定出要抓 EX-99.1 全文的事件清單(→ cache/fetch_plan.json)。

為何不是「宇宙內全部事件」:宇宙內 51,889 宗,3 請求/秒要抓四小時以上;而文本只用於
三處 —— 稿頭日期、稿內訊號季收入、指引句 —— 這三處**只影響入口池**,而入口池只從
「宇宙內 ∧ 反應 ≥ 逐事件窗口第 90 百分位 ∧ 相對同業為正」之中來。故抓取集 =
該子集 **加安全邊際**(門檻 −0.008、同業 −0.008),蓋住併購閘套用後門檻的最大移動
(實測最大 0.0029,見執行紀錄),加邊際後 2.7 倍。

已快取者不列入。輸出 `cache/fetch_plan.json`(accessionNumber 陣列)。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE.parent / "A" / "edgar_cache"

MARGIN = 0.008


def main() -> None:
    df = pd.read_parquet(CACHE / "population_base.parquet")
    th = pd.read_parquet(CACHE / "thresholds_window.parquet")
    df = df.merge(th, on="accessionNumber", how="left")

    names = set(os.listdir(DOCS))
    df["accnd"] = df["accessionNumber"].str.replace("-", "")
    df["has_txt"] = df["accnd"].map(lambda a: ("%s__EX991.txt.gz" % a) in names)

    u = df[(df["in_universe"] == 1) & df["in_pool_window"]
           & (df["thr_insufficient"] == 0)]
    m = ((u["rel_spy"] >= u["thr_p90"] - MARGIN) & (u["rel_sic2"] > -MARGIN))
    f = u[m]
    need = f[~f["has_txt"]]["accessionNumber"].tolist()

    (CACHE / "fetch_plan.json").write_text(json.dumps(need), encoding="utf-8")
    print("宇宙內(pool 窗):%d" % len(u))
    print("抓取集(第 90 百分位 −%.3f、同業 > −%.3f):%d;已有文本 %d;待抓 %d"
          % (MARGIN, MARGIN, len(f), int(f["has_txt"].sum()), len(need)))
    print("→", CACHE / "fetch_plan.json")


if __name__ == "__main__":
    main()
