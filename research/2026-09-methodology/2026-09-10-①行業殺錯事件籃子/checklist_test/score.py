# -*- coding: utf-8 -*-
"""KARST-204 評分隊:把判斷隊的四級判斷對上 KARST-199 的十二個月超額,量分辨力。
只讀,不改任何既有輸出。輸出三張表到 out/。
統計:scipy.stats.spearmanr。
"""
import glob
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "out")
MEMBERS = os.path.join(os.path.dirname(BASE), "out", "basket_members.csv")

GRADES = ["高度適用", "部分適用", "大致不適用", "資料不足"]
ORD = {"高度適用": 3, "部分適用": 2, "大致不適用": 1}
MIN_N = 8  # 少於此家數不下結論


def load():
    judged = pd.concat(
        [pd.read_csv(f) for f in sorted(glob.glob(os.path.join(OUT, "判-E*.csv")))],
        ignore_index=True,
    )
    mem = pd.read_csv(MEMBERS)
    mem.columns = [c.lstrip("﻿") for c in mem.columns]
    mem = mem[mem["basket_kind"] == "新聞點名"]
    keep = [
        "event_id", "ticker", "f_shock_rel_drop",
        "T_12m_excess", "T_12m_status", "N_12m_excess", "N_12m_status",
    ]
    df = judged.merge(mem[keep], on=["event_id", "ticker"], how="left")
    a7 = pd.read_csv(os.path.join(OUT, "a7_gate.csv"))
    a7c = ["event_id", "ticker", "a7_strict_cut", "a7_proxy_cut_0pp", "a7_proxy_cut_10pp"]
    df = df.merge(a7[a7c], on=["event_id", "ticker"], how="left")
    # 只用「已成熟」的成績
    for a in ("T", "N"):
        ok = df[f"{a}_12m_status"].astype(str).str.strip() == "已成熟"
        df[f"{a}_y"] = np.where(ok, df[f"{a}_12m_excess"], np.nan)
    df["grade_ord"] = df["step5_grade"].map(ORD)
    return df


def desc(s):
    s = pd.Series(s).dropna()
    n = len(s)
    if n == 0:
        return dict(家數=0, 中位=np.nan, 平均=np.nan, 勝率=np.nan, 四分位距=np.nan, 註=" 無成熟樣本")
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    return dict(
        家數=n,
        中位=round(float(s.median()), 4),
        平均=round(float(s.mean()), 4),
        勝率=round(float((s > 0).mean()), 4),
        四分位距=round(float(q3 - q1), 4),
        註="家數過細,不下結論" if n < MIN_N else "",
    )


def table1(df, tag=""):
    rows = []
    for anchor in ("T", "N"):
        for g in GRADES:
            sub = df[df["step5_grade"] == g]
            r = dict(樣本=tag or "全樣本", 錨=anchor, 適用度=g, 判定家數=len(sub))
            r.update(desc(sub[f"{anchor}_y"]))
            rows.append(r)
        r = dict(樣本=tag or "全樣本", 錨=anchor, 適用度="__合計__", 判定家數=len(df))
        r.update(desc(df[f"{anchor}_y"]))
        rows.append(r)
    return pd.DataFrame(rows)


def decentre(df, anchor):
    """事件內去中心化:逐宗事件減去該宗籃子(有成熟成績者)的中位數。"""
    y = df[f"{anchor}_y"]
    med = y.groupby(df["event_id"]).transform("median")
    return y - med


def spear(x, y, label, anchor, mode, tag):
    m = pd.notna(x) & pd.notna(y)
    n = int(m.sum())
    if n < 3:
        return dict(樣本=tag, 錨=anchor, 版本=mode, 欄=label, 家數=n,
                    Spearman=np.nan, p值=np.nan, 註="家數過細,不下結論")
    rho, p = spearmanr(np.asarray(x)[m.values], np.asarray(y)[m.values])
    return dict(樣本=tag, 錨=anchor, 版本=mode, 欄=label, 家數=n,
                Spearman=round(float(rho), 4), p值=round(float(p), 4),
                註="家數過細,不下結論" if n < MIN_N else "")


def hi_lo(df, ycol, anchor, mode, tag):
    hi = df.loc[df["step5_grade"] == "高度適用", ycol].dropna()
    lo = df.loc[df["step5_grade"] == "大致不適用", ycol].dropna()
    return dict(
        樣本=tag, 錨=anchor, 版本=mode,
        高度適用家數=len(hi), 大致不適用家數=len(lo),
        高度適用中位=round(float(hi.median()), 4) if len(hi) else np.nan,
        大致不適用中位=round(float(lo.median()), 4) if len(lo) else np.nan,
        中位差_低減高=round(float(lo.median() - hi.median()), 4) if len(hi) and len(lo) else np.nan,
        平均差_低減高=round(float(lo.mean() - hi.mean()), 4) if len(hi) and len(lo) else np.nan,
        註="家數過細,不下結論" if min(len(hi), len(lo)) < MIN_N else "",
    )


def ordinalise(df):
    """同場加映各欄編序數。方向皆設為『分數越高 = 清單越覺得敘事成立/證據越硬』。"""
    out = {}
    out["evidence_level"] = df["evidence_level"].map(
        {"低": 1, "中低": 1.5, "中": 2, "中高": 2.5, "高": 3}
    )
    out["n_fragile"] = df["n_fragile"]
    out["n_missing"] = df["n_missing"]
    out["step6_verdict"] = df["step6_verdict"].map(
        {"反應不足": 1, "相稱": 2, "市場反應過度": 3}  # 推算不足 → NaN(答不到)
    )
    return out


def table2(df, tag="全樣本"):
    srows, hrows = [], []
    for anchor in ("T", "N"):
        raw = df[f"{anchor}_y"]
        dec = decentre(df, anchor)
        d2 = df.copy()
        d2[f"{anchor}_dec"] = dec
        for mode, ycol in (("併表", f"{anchor}_y"), ("事件內去中心", f"{anchor}_dec")):
            y = d2[ycol]
            srows.append(spear(df["grade_ord"], y, "step5_grade(適用度序數)", anchor, mode, tag))
            for name, xs in ordinalise(df).items():
                srows.append(spear(xs, y, name, anchor, mode, tag))
            hrows.append(hi_lo(d2, ycol, anchor, mode, tag))
    return pd.DataFrame(srows), pd.DataFrame(hrows)


def main():
    df = load()
    df.to_csv(os.path.join(OUT, "評分_合併明細.csv"), index=False, encoding="utf-8-sig")

    # 表一
    t1 = table1(df)
    t1.to_csv(os.path.join(OUT, "表一_四級成績.csv"), index=False, encoding="utf-8-sig")

    # 表二
    s, h = table2(df)
    s.to_csv(os.path.join(OUT, "表二_秩相關.csv"), index=False, encoding="utf-8-sig")
    h.to_csv(os.path.join(OUT, "表二_最高對最低級.csv"), index=False, encoding="utf-8-sig")

    # 表三:A7 三版
    variants = [
        ("甲 嚴格版", "a7_strict_cut"),
        ("乙 代理版 0pp", "a7_proxy_cut_0pp"),
        ("乙 代理版 10pp", "a7_proxy_cut_10pp"),
    ]
    t3_1, t3_s, t3_h = [], [], []
    cut_counts = []
    for tag, col in variants:
        cut = df[col].astype(str).str.strip().str.lower().isin(["true", "1", "yes"])
        sub = df[~cut].copy()
        cut_counts.append(dict(版本=tag, 被剔家數=int(cut.sum()), 餘下家數=len(sub)))
        t3_1.append(table1(sub, tag))
        ss, hh = table2(sub, tag)
        t3_s.append(ss)
        t3_h.append(hh)
    pd.DataFrame(cut_counts).to_csv(
        os.path.join(OUT, "表三_A7剔除家數.csv"), index=False, encoding="utf-8-sig")
    pd.concat(t3_1).to_csv(
        os.path.join(OUT, "表三_A7三版_四級成績.csv"), index=False, encoding="utf-8-sig")
    core = pd.concat(t3_s)
    core[core["欄"] == "step5_grade(適用度序數)"].to_csv(
        os.path.join(OUT, "表三_A7三版_秩相關.csv"), index=False, encoding="utf-8-sig")
    pd.concat(t3_h).to_csv(
        os.path.join(OUT, "表三_A7三版_最高對最低級.csv"), index=False, encoding="utf-8-sig")

    # 主控台摘要
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print("== 表一 ==");  print(t1.to_string(index=False))
    print("\n== 表二 秩相關 ==");  print(s.to_string(index=False))
    print("\n== 表二 高對低 ==");  print(h.to_string(index=False))
    print("\n== 表三 剔除家數 ==");  print(pd.DataFrame(cut_counts).to_string(index=False))
    print("\n== 表三 秩相關(step5) ==")
    print(core[core["欄"] == "step5_grade(適用度序數)"].to_string(index=False))
    print("\n== 表三 高對低 ==");  print(pd.concat(t3_h).to_string(index=False))
    print("\n== 成熟度 ==")
    for a in ("T", "N"):
        print(a, "成熟", int(df[f"{a}_y"].notna().sum()), "/", len(df),
              df[f"{a}_12m_status"].value_counts(dropna=False).to_dict())
    print("\n== 逐宗事件 ==")
    g = df.groupby("event_id").agg(家數=("ticker", "size"),
                                   T成熟=("T_y", lambda x: x.notna().sum()),
                                   T中位=("T_y", "median"))
    print(g.to_string())


if __name__ == "__main__":
    main()
