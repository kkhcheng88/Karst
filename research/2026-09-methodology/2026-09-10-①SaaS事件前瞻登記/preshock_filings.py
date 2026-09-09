# -*- coding: utf-8 -*-
"""KARST-200:替籃子每家列出「衝擊日之前」最後幾份申報,供判斷層取證。

硬界線 CUTOFF = 2026-01-29(首個衝擊日)。只列 filingDate < CUTOFF 的申報,
所以拿到的一定是衝擊當日已經公開的資料——這是本票「只准用衝擊日前已公開的資料」
那一條的機械保證,不靠人手自律。

來源:data/sec/submissions/CIK##########.json 本地快取;快取缺就記 missing,
      由取證的人打 EDGAR。
"""
import json
import sys

import pandas as pd

CUTOFF = "2026-01-29"
SUB = "C:/projects/Karst/data/sec/submissions/CIK{cik}.json"
OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-10-①SaaS事件前瞻登記"


def recent(cik):
    try:
        with open(SUB.format(cik=cik), encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return None
    r = d.get("filings", {}).get("recent", {})
    if not r:
        return None
    df = pd.DataFrame({k: r[k] for k in
                       ("form", "filingDate", "reportDate", "accessionNumber", "primaryDocument")
                       if k in r})
    return df


def main(tickers):
    ent = pd.read_parquet("C:/projects/Karst/data/universe/entities.parquet")
    lines = []
    for t in tickers:
        row = ent[ent.primary_ticker == t]
        if row.empty:
            lines.append(f"## {t}\n\n- 宇宙表無此代號(外國申報人或未收錄),取證請直接打 EDGAR 全文搜尋。\n")
            continue
        cik = str(row.entity_id.iloc[0])
        name = row.name.iloc[0] if "name" in row else ""
        df = recent(cik)
        lines.append(f"## {t} — {row['name'].iloc[0]}(CIK {cik})\n")
        if df is None:
            lines.append("- 本地快取無 submissions,請打 EDGAR。\n")
            continue
        pre = df[df.filingDate < CUTOFF]
        for form in ("10-K", "20-F", "10-Q", "8-K", "DEF 14A"):
            sel = pre[pre.form == form].head(2 if form in ("10-Q", "8-K") else 1)
            for _, s in sel.iterrows():
                acc = s.accessionNumber.replace("-", "")
                url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/"
                       f"{s.primaryDocument}")
                lines.append(f"- {s.form} 申報日 {s.filingDate} 期末 {s.reportDate} — {url}")
        lines.append("")
    with open(f"{OUT}/衝擊前申報索引.md", "w", encoding="utf-8") as f:
        f.write(f"# 衝擊前申報索引(硬界線:申報日 < {CUTOFF})\n\n"
                "只列衝擊日之前已公開的申報。判斷層取證只准用這裡的文件"
                "(或同樣早於界線的逐字稿、存檔定價頁)。\n\n")
        f.write("\n".join(lines))
    print(f"寫好 {len(tickers)} 家")


if __name__ == "__main__":
    main([t.strip() for t in sys.argv[1].split(",")])
