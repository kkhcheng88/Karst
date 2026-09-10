# -*- coding: utf-8 -*-
"""KARST-204 收尾:逐格統計與「資料不足」組剖析。只讀 `判-E*.csv`,另寫兩張新表。

為什麼另開一支而不用 score.py:score.py 已驗證可重現,不動它。
本檔答兩條票上明文要的問題:
  1. 八步之中,哪幾格常答「查不到」——逐格標籤分佈與查不到率(表四)。
  2. 「資料不足」那一組成績最好,是否因為它們是小公司——按適用度分組看市值與成交額(表五)。
步四六格(e1–e6)的方向寫在自由文字,不可機械讀;故分辨力只在總表
(表二:適用度序數、證據等級、脆弱條數、查不到條數)量,本檔不另造方向。
"""
import glob
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "out")
MEMBERS = os.path.join(os.path.dirname(BASE), "out", "basket_members.csv")

# 步四六格 + 步三佔比 + 步六判詞;欄名 → 顯示名
CELLS = [
    ("step3_label", "步三 受衝擊收入佔比"),
    ("e1_label", "步四-1 客戶集中度"),
    ("e2_label", "步四-2 合約年期"),
    ("e3_label", "步四-3 經常性收入"),
    ("e4_label", "步四-4 定價方式"),
    ("e5_label", "步四-5 可替代性"),
    ("e6_label", "步四-6 管理層應對"),
]
TAGS = ["已核", "推算", "判斷", "查不到"]
GRADES = ["高度適用", "部分適用", "大致不適用", "資料不足"]


def tag_of(v):
    """把帶括號的標籤(例:已核(上限 10%))歸回四個主標籤。"""
    s = str(v).strip()
    for t in TAGS:
        if s.startswith(t):
            return t
    return "其他"


def cell_table(df):
    rows = []
    for col, name in CELLS:
        t = df[col].map(tag_of)
        r = dict(格=name, 判定家數=len(df))
        for tag in TAGS:
            r[f"{tag}家數"] = int((t == tag).sum())
            r[f"{tag}率"] = round(float((t == tag).mean()), 4)
        rows.append(r)
    # 步六判詞另計:推算不足＝這一格答不到
    v = df["step6_verdict"].astype(str)
    r = dict(格="步六 價格影響判詞", 判定家數=len(df))
    for tag in TAGS:
        r[f"{tag}家數"] = int((v == "推算不足").sum()) if tag == "查不到" else 0
        r[f"{tag}率"] = round(float((v == "推算不足").mean()), 4) if tag == "查不到" else 0.0
    rows.append(r)
    return pd.DataFrame(rows)


def grade_profile(df):
    rows = []
    for g in GRADES:
        s = df[df["step5_grade"] == g]
        for anchor in ("T", "N"):
            y = s[f"{anchor}_y"].dropna()
            rows.append(dict(
                適用度=g, 錨=anchor, 家數=len(s),
                市值中位_百萬美元=round(float(s["mcap_usd"].median()) / 1e6, 1)
                if s["mcap_usd"].notna().any() else np.nan,
                市值_有值家數=int(s["mcap_usd"].notna().sum()),
                日均成交額中位_百萬美元=round(float(s["dollar_vol_60d"].median()) / 1e6, 2)
                if s["dollar_vol_60d"].notna().any() else np.nan,
                查不到格數中位=float(s["n_missing"].median()),
                十二個月中位=round(float(y.median()), 4) if len(y) else np.nan,
            ))
    return pd.DataFrame(rows)


def main():
    judged = pd.concat(
        [pd.read_csv(f) for f in sorted(glob.glob(os.path.join(OUT, "判-E*.csv")))],
        ignore_index=True,
    )
    mem = pd.read_csv(MEMBERS)
    mem.columns = [c.lstrip("﻿") for c in mem.columns]
    mem = mem[mem["basket_kind"] == "新聞點名"]
    df = judged.merge(
        mem[["event_id", "ticker", "mcap_usd", "dollar_vol_60d",
             "T_12m_excess", "T_12m_status", "N_12m_excess", "N_12m_status"]],
        on=["event_id", "ticker"], how="left")
    for a in ("T", "N"):
        ok = df[f"{a}_12m_status"].astype(str).str.strip() == "已成熟"
        df[f"{a}_y"] = np.where(ok, df[f"{a}_12m_excess"], np.nan)

    t4 = cell_table(df)
    t4.to_csv(os.path.join(OUT, "表四_逐格查不到.csv"), index=False, encoding="utf-8-sig")

    t5 = grade_profile(df)
    t5.to_csv(os.path.join(OUT, "表五_適用度組市場特徵.csv"), index=False, encoding="utf-8-sig")

    # 「資料不足」是不是集中在某幾宗事件
    t6 = (df.assign(是否資料不足=(df["step5_grade"] == "資料不足"))
            .groupby("event_id")
            .agg(家數=("ticker", "size"), 資料不足家數=("是否資料不足", "sum")))
    t6["資料不足佔比"] = (t6["資料不足家數"] / t6["家數"]).round(3)
    t6.to_csv(os.path.join(OUT, "表六_資料不足逐宗分佈.csv"), encoding="utf-8-sig")

    # 事件內去中心後,各級還剩多少差距(分辨力是單邊還是雙邊)
    rows = []
    for a in ("T", "N"):
        dec = df[f"{a}_y"] - df[f"{a}_y"].groupby(df["event_id"]).transform("median")
        df[f"{a}_dec"] = dec
        for g in GRADES:
            s = df.loc[df["step5_grade"] == g, f"{a}_dec"].dropna()
            rows.append(dict(錨=a, 適用度=g, 家數=len(s),
                             去中心中位=round(float(s.median()), 4),
                             去中心平均=round(float(s.mean()), 4),
                             勝率=round(float((s > 0).mean()), 4)))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "表七_去中心後各級成績.csv"),
                              index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 260)
    pd.set_option("display.max_columns", 40)
    print("== 表四 逐格標籤 ==");  print(t4.to_string(index=False))
    print("\n== 表五 適用度組市場特徵 ==");  print(t5.to_string(index=False))
    print("\n== 表六 資料不足逐宗 ==");  print(t6.to_string())
    print("\n大小關係:查不到格數 vs 市值(有值者) 的 Spearman")
    sub = df[df["mcap_usd"].notna()]
    from scipy.stats import spearmanr
    if len(sub) >= 3:
        rho, p = spearmanr(sub["n_missing"], sub["mcap_usd"])
        print(f"  n={len(sub)} rho={rho:.4f} p={p:.4f}")


if __name__ == "__main__":
    main()
