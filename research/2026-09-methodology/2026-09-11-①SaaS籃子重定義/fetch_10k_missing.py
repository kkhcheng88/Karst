# -*- coding: utf-8 -*-
"""KARST-209 步驟四之前置:補齊本籃缺的 10-K 全文快取。

倉內 `data/sec/10k_text/` 是申報全文的唯一快取(D-134,原料唯一快取),
本籃 131 家之中只有 53 家有快取。缺的先查 `data/sec/submissions/`(已快取的申報索引,
不必再問 EDGAR),找出衝擊基準日 2026-01-12 或之前最近一份 10-K,
再抓全文寫入同一個快取並補 manifest——**不另存第二份副本**。

選件規則:優先 filingDate <= 2026-01-12(衝擊前已公開,與 KARST-200 的盲判界線一致);
該日之前沒有 10-K 的,取之後最近一份並在 manifest 標 `post_shock = true`。
"""
import gzip
import hashlib
import json
import os
import time

import pandas as pd
import requests

OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①SaaS籃子重定義"
CACHE = "C:/projects/Karst/data/sec/10k_text"
SUBS = "C:/projects/Karst/data/sec/submissions"
MANIFEST = f"{CACHE}/manifest.jsonl"
BOUNDARY = "2026-01-12"
UA = {"User-Agent": "Karst Research (KARST-209) research@karst.local"}


def load_manifest():
    return [json.loads(l) for l in open(MANIFEST, encoding="utf-8") if l.strip()]


def latest_10k(cik):
    """由已快取的 submissions 索引找 10-K。回 (accession, filingDate, primaryDoc)。"""
    p = f"{SUBS}/CIK{cik}.json"
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    r = d.get("filings", {}).get("recent", {})
    forms, dates = r.get("form", []), r.get("filingDate", [])
    accs, docs = r.get("accessionNumber", []), r.get("primaryDocument", [])
    hits = [(dates[i], accs[i], docs[i]) for i in range(len(forms))
            if forms[i] == "10-K" and i < len(accs) and docs[i]]
    if not hits:
        return None
    pre = [h for h in hits if h[0] <= BOUNDARY]
    pick = max(pre) if pre else max(hits)
    return {"filingDate": pick[0], "accession": pick[1],
            "primaryDoc": pick[2], "post_shock": not pre}


def main():
    cons = pd.read_csv(f"{OUT}/constituents.csv")
    ent = pd.read_parquet("C:/projects/Karst/data/universe/entities.parquet")
    cik_of = dict(zip(ent.primary_ticker.astype(str), ent.entity_id.astype(str)))
    have = {m["ticker"] for m in load_manifest()}
    todo = [t for t in cons.ticker if t not in have]
    print(f"本籃 {len(cons)} 家;已有快取 {len(cons)-len(todo)};待補 {len(todo)}")

    new_rows, skipped, failed = [], [], []
    for t in todo:
        cik = cik_of.get(t)
        if not cik:
            skipped.append((t, "不在宇宙表,無 CIK(多為外地上市/ETF 成分的外國股)"))
            continue
        pick = latest_10k(cik)
        if not pick:
            skipped.append((t, "submissions 索引內無 10-K(外國私人發行人多交 20-F)"))
            continue
        acc_nodash = pick["accession"].replace("-", "")
        url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
               f"{acc_nodash}/{pick['primaryDoc']}")
        dest = f"{CACHE}/{t}_{acc_nodash}.txt.gz"
        if os.path.exists(dest):
            skipped.append((t, "檔案已在快取"))
            continue
        try:
            r = requests.get(url, headers=UA, timeout=60)
            if r.status_code != 200:
                failed.append((t, f"HTTP {r.status_code}"))
                time.sleep(0.2)
                continue
            raw = r.content
            body = raw.decode("utf-8", errors="replace")
            with gzip.open(dest, "wb") as f:
                f.write(body.encode("utf-8"))
            new_rows.append({
                "ticker": t, "cik": cik, "accession": pick["accession"], "form": "10-K",
                "filingDate": pick["filingDate"], "reportDate": None, "url": url,
                "chars": len(body),
                "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                "fetchedBy": "KARST-209", "primaryDoc": pick["primaryDoc"],
                "post_shock": pick["post_shock"],
            })
            print(f"  OK {t} {pick['filingDate']}{' (衝擊後)' if pick['post_shock'] else ''}")
        except Exception as e:
            failed.append((t, str(e)[:80]))
        time.sleep(0.15)          # EDGAR 上限 10 req/s

    if new_rows:
        with open(MANIFEST, "a", encoding="utf-8") as f:
            for r in new_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(f"{OUT}/10k_補抓紀錄.md", "w", encoding="utf-8") as f:
        f.write("# KARST-209 10-K 全文補抓(寫入倉內唯一快取 data/sec/10k_text/)\n\n")
        f.write(f"- 規則:優先 filingDate ≤ {BOUNDARY};之前無 10-K 者取之後最近一份並標 `post_shock`\n")
        f.write(f"- 新抓 **{len(new_rows)}** 份、跳過 **{len(skipped)}**、失敗 **{len(failed)}**\n\n")
        f.write("## 新抓\n\n| 代號 | 申報日 | 衝擊後 | 字數 |\n|---|---|---|---|\n")
        for r in new_rows:
            f.write(f"| {r['ticker']} | {r['filingDate']} | "
                    f"{'是' if r['post_shock'] else '否'} | {r['chars']:,} |\n")
        f.write("\n## 跳過(連原因;這些家在本票標「查不到」)\n\n| 代號 | 原因 |\n|---|---|\n")
        for t, why in skipped:
            f.write(f"| {t} | {why} |\n")
        if failed:
            f.write("\n## 失敗\n\n| 代號 | 原因 |\n|---|---|\n")
            for t, why in failed:
                f.write(f"| {t} | {why} |\n")
    print(f"\n新抓 {len(new_rows)}、跳過 {len(skipped)}、失敗 {len(failed)}")


if __name__ == "__main__":
    main()
