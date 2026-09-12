# -*- coding: utf-8 -*-
"""KARST-225 票 A′(v1.1)第六步:指引上調正則(讀 s5 抓回來的 EX-99.1 全文)。

與 `A/s6_guidance.py` 之別:①強勢反應子集改用 A2 的宇宙;②原文快取沿用 `A/edgar_cache/`。
正則一字不改。

正則(執行口徑 v1 第一節):raise/raised/raising/increase/increased/increasing 配
guidance/outlook,**並附數字**。做法:找出每個 guidance/outlook 詞的 ±260 字元窗,
窗內同時有上調動詞與數字才算命中;另記 "reaffirm/reiterate/unchanged"(上調以外的
口徑)供覆核,不計入命中。

輸出 `cache/guidance.jsonl`(逐事件命中與摘句)與 `cache/improvement.parquet`
(improvement_type:加速/指引/兩者/無/未評)。
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE.parent / "A" / "edgar_cache"     # 沿用 v1 的原文快取

GUID = re.compile(r"(?i)\b(guidance|outlook)\b")
RAISE = re.compile(r"(?i)\b(raise[ds]?|raising|increase[ds]?|increasing)\b")
HOLD = re.compile(r"(?i)\b(reaffirm\w*|reiterat\w*|maintain\w*|unchanged|no change)\b")
DIGIT = re.compile(r"\d")
WINDOW = 260
GC = re.compile(r"(?i)going\s+concern")


def check_text(txt: str) -> dict:
    hits, holds = [], []
    for m in GUID.finditer(txt):
        a, b = max(0, m.start() - WINDOW), min(len(txt), m.end() + WINDOW)
        w = txt[a:b]
        if RAISE.search(w) and DIGIT.search(w):
            hits.append(re.sub(r"\s+", " ", w).strip()[:300])
        elif HOLD.search(w):
            holds.append(re.sub(r"\s+", " ", w).strip()[:200])
    gcm = GC.search(txt)
    gc_snip = ""
    if gcm:
        gc_snip = re.sub(r"\s+", " ", txt[max(0, gcm.start() - 120):gcm.end() + 120]).strip()
    return {"guidance_raise": int(bool(hits)), "snippets": hits[:3],
            "hold_snippets": holds[:2], "going_concern_hit": int(bool(gcm)),
            "going_concern_snippet": gc_snip[:240]}


def main() -> None:
    df = pd.read_parquet(CACHE / "population_base.parquet")
    sel = df[(df["in_universe"] == 1) & (df["pass_p90"] == 1)]
    out = []
    for r in sel.itertuples(index=False):
        acc_nodash = r.accessionNumber.replace("-", "")
        p = DOCS / ("%s__EX991.txt.gz" % acc_nodash)
        if not p.exists():
            out.append({"accessionNumber": r.accessionNumber, "has_text": 0,
                        "guidance_raise": 0, "snippets": [], "hold_snippets": [],
                        "going_concern_hit": 0, "going_concern_snippet": "", "chars": 0})
            continue
        txt = gzip.open(p, "rt", encoding="utf-8").read()
        c = check_text(txt)
        out.append({"accessionNumber": r.accessionNumber, "has_text": 1,
                    "chars": len(txt), **c})
    g = pd.DataFrame(out)
    with open(CACHE / "guidance.jsonl", "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    df = df.merge(g[["accessionNumber", "has_text", "guidance_raise", "going_concern_hit"]],
                  on="accessionNumber", how="left")
    df["has_text"] = df["has_text"].fillna(0).astype(int)
    df["guidance_raise"] = df["guidance_raise"].fillna(0).astype(int)
    # 持續經營疑慮:抓得文本者以 EX-99.1 全文核(「going concern」字串);其餘標「未核」
    df["going_concern_hit"] = df["going_concern_hit"].fillna(0).astype(int)
    df["excl_going_concern"] = np.where(
        df["has_text"] == 1, np.where(df["going_concern_hit"] == 1, "有", "無"), "未核")
    accel = df["accel_hit"] == 1
    guid = df["guidance_raise"] == 1
    df["improvement_type"] = "未評"
    df.loc[df["has_text"] == 1, "improvement_type"] = "無"
    df.loc[df["has_text"] == 1, "improvement_type"] = (
        df.loc[df["has_text"] == 1].apply(
            lambda r: "兩者" if (r["accel_hit"] == 1 and r["guidance_raise"] == 1)
            else "加速" if r["accel_hit"] == 1
            else "指引" if r["guidance_raise"] == 1 else "無", axis=1))
    df.to_parquet(CACHE / "population_improvement.parquet", index=False)

    inu = df["in_universe"] == 1
    print("抓得文本:%d;有指引上調:%d" % (df["has_text"].sum(), df["guidance_raise"].sum()))
    print("improvement_type(宇宙內):",
          df[inu]["improvement_type"].value_counts().to_dict())
    for pc in ("pass_p90", "pass_p95", "pass_p80"):
        s = df[(df[pc] == 1) & (df["improvement_type"].isin(["加速", "指引", "兩者"]))]
        print("%s 入口(改善非無):%d;其中" % (pc, len(s)),
              s["improvement_type"].value_counts().to_dict())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
