# -*- coding: utf-8 -*-
"""KARST-209 步驟三與五:對照、漏接排名、總覽。

輸入:`籃子表.csv`(步驟二,口徑與 KARST-200 逐欄相同)與 `收費模式.csv`(步驟四)。
輸出:
- `籃子表.csv` / `籃子表.md` 補上「收費模式」一欄(原欄不動)
- `差異表.md`——35 家內 / 外、反向缺口、漏接前 20(附市值與收費模式)
- `總覽——①SaaS籃子重定義.md`——交回主腦的一頁
"""
import csv

import pandas as pd

OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①SaaS籃子重定義"
K200 = "C:/projects/Karst/research/2026-09-methodology/2026-09-10-①SaaS事件前瞻登記"
KEYS = ["收費模式", "收費證據"]


def main():
    df = pd.read_csv(f"{OUT}/籃子表.csv", encoding="utf-8-sig")
    fee = pd.read_csv(f"{OUT}/收費模式.csv", encoding="utf-8-sig")
    fmap = dict(zip(fee["代號"], fee["收費模式"]))
    ev = dict(zip(fee["代號"], fee["證據句"].fillna("")))
    note = dict(zip(fee["代號"], fee["備註"].fillna("")))
    df["收費模式"] = df["代號"].map(fmap).fillna("查不到")
    df["收費證據"] = df["代號"].map(ev).fillna("")
    df["收費備註"] = df["代號"].map(note).fillna("")
    df.sort_values("急性窗相對大市低點%", inplace=True)
    df.to_csv(f"{OUT}/籃子表.csv", index=False, encoding="utf-8-sig")

    old = pd.read_csv(f"{K200}/basket_members.csv")
    old35 = list(dict.fromkeys(old["ticker"].astype(str)))
    inn = df[df["在200的35家內"] == "是"]
    out = df[df["在200的35家內"] == "否"]
    back = [t for t in old35 if t not in set(df["代號"])]

    a = df["急性窗相對大市低點%"]
    bins = [(0, -10), (-10, -20), (-20, -30), (-30, -40), (-40, -1e9)]
    dist = [(f"{lo}% 至 {hi}%", int(((a <= lo) & (a > hi)).sum())) for lo, hi in bins]

    md = ["# KARST-209 差異表——IGV+CIBR 新籃子 對 KARST-200 的 35 家\n"]
    md.append(f"- 新籃子 **{len(df)} 家**(IGV 106 + CIBR 42 去重);"
              f"在 200 的 35 家之內 **{len(inn)} 家**、之外 **{len(out)} 家**\n")
    md.append(f"- **反向缺口**(在 35 家、不在 IGV+CIBR)共 **{len(back)} 家**:"
              f"{'、'.join(back)}\n")
    md.append("- 口徑與 KARST-200 相同:基準日 2026-01-12、急性期 01-13 至 02-27、"
              "價格日 2026-09-08、相對大市 = 個股 ÷ SPY 基準日歸一\n")

    md.append("\n## 一、漏接前 20(不在 35 家內,按急性窗相對大市跌幅排序)\n")
    md.append("| # | 代號 | 公司 | ETF | 急性窗相對大市% | 全期相對大市% | 回補比例% | 現價 | 市值(十億美元) | 收費模式 |\n")
    md.append("|---|---|---|---|---|---|---|---|---|---|\n")
    top = out.head(20)
    for i, (_, r) in enumerate(top.iterrows(), 1):
        cap = "" if pd.isna(r["市值(十億美元)"]) else f"{r['市值(十億美元)']:,.1f}"
        md.append(f"| {i} | {r['代號']} | {str(r['公司'])[:26]} | {r['ETF']} | "
                  f"{r['急性窗相對大市低點%']} | {r['全期相對大市低點%']} | "
                  f"{'' if pd.isna(r['回補比例%']) else r['回補比例%']} | {r['現價']} | "
                  f"{cap} | {r['收費模式']} |\n")

    md.append("\n## 二、35 家之內的對照(兩表同尺)\n")
    md.append("| 代號 | 急性窗相對大市% | 全期相對大市% | 回補比例% | 收費模式 |\n|---|---|---|---|---|\n")
    for _, r in inn.iterrows():
        md.append(f"| {r['代號']} | {r['急性窗相對大市低點%']} | {r['全期相對大市低點%']} | "
                  f"{'' if pd.isna(r['回補比例%']) else r['回補比例%']} | {r['收費模式']} |\n")

    with open(f"{OUT}/差異表.md", "w", encoding="utf-8") as f:
        f.write("".join(md))

    # 建議並排十家:規則寫死,方便覆核——35 家外、收費模式屬軟件收費
    # (剔「查不到」與「其他」,後者含廣告/遊戲/政府服務,不是①SaaS 那條線)、有市值,
    # 取跌得最深的十家。剔走的次選另列,免主腦以為只看過十家。
    pool = out[(out["收費模式"] != "查不到") & (out["收費模式"] != "其他")
               & out["市值(十億美元)"].notna()]
    cand = pool.head(10)
    skipped = out[(out["收費模式"] == "其他") & out["市值(十億美元)"].notna()].head(3)
    print("剔走的『其他』前幾名(非軟件收費):",
          [(r["代號"], r["急性窗相對大市低點%"]) for _, r in skipped.iterrows()])
    print("家數", len(df), "| 35內", len(inn), "| 35外", len(out), "| 反向缺口", len(back))
    print("跌幅分佈", dist)
    print("收費模式分佈(全籃):", df["收費模式"].value_counts().to_dict())
    print("收費模式分佈(35內):", inn["收費模式"].value_counts().to_dict())
    print("收費模式分佈(35外):", out["收費模式"].value_counts().to_dict())
    print("\n建議並排十家:")
    for _, r in cand.iterrows():
        print(f"  {r['代號']:6s} {r['急性窗相對大市低點%']:6.1f}% "
              f"全期{r['全期相對大市低點%']:6.1f}% 回補"
              f"{r['回補比例%'] if not pd.isna(r['回補比例%']) else float('nan'):6.1f}% "
              f"{r['市值(十億美元)']:8.1f}B {r['收費模式']}")
    cand[["代號", "公司", "ETF", "急性窗相對大市低點%", "全期相對大市低點%",
          "回補比例%", "現價", "市值(十億美元)", "收費模式", "收費證據"]
         ].to_csv(f"{OUT}/建議並排十家.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
