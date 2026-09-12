# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2):抓同日帶 Item 1.01 的 8-K **正文**(併購閘要用字眼判)。

執行口徑 v1.2 第 5 項 (c):僅 Item 1.01 而正文無 merger / acquisition /
agreement and plan of merger / acquire 字眼者**不剔**。故要正文。
抓取範圍:宇宙內(pool 窗)事件當日、帶 Item 1.01 的 8-K(自身或其他),由
`cache/merger_fetch_list.json` 指定。單線程 3 請求/秒;原文入 `A/edgar_cache/`,
檔名 `{accnodash}__8K.txt.gz`。逐宗落 `cache/merger_fetch_log.jsonl`。

用法:python s5b_merger_body.py [每支上限] [秒數上限]
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s5_fetch_text import _get, strip_html, DOCS, CACHE   # noqa: E402


def fetch_one(acc: str, cik: str, prim: str) -> dict:
    an = acc.replace("-", "")
    out = {"accessionNumber": acc, "status": ""}
    p = DOCS / ("%s__8K.txt.gz" % an)
    if p.exists():
        out["status"] = "ok"
        out["source"] = "已快取"
        return out
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s" % (int(cik), an)
    names = []
    if prim:
        names.append(prim.rsplit("/", 1)[-1])
    if not names:
        try:
            page = _get(base + "/" + acc + "-index.html").decode("utf-8", "ignore")
            import re
            for m in re.finditer(r'href="([^"]+\.(?:htm|html|txt))"', page, re.I):
                n = m.group(1).rsplit("/", 1)[-1]
                if not n.lower().startswith(("ex", "r")):
                    names.append(n)
                    break
        except Exception as e:  # noqa: BLE001
            out["status"] = "索引抓取失敗:%s" % type(e).__name__
            return out
    raw = None
    for nm in names:
        try:
            raw = _get(base + "/" + nm, timeout=120)
            break
        except Exception:  # noqa: BLE001
            continue
    if raw is None:
        out["status"] = "正文抓取失敗"
        return out
    txt = strip_html(raw)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(txt)
    out["status"] = "ok"
    out["source"] = names[0]
    out["chars"] = len(txt)
    return out


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 700
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 540.0
    DOCS.mkdir(parents=True, exist_ok=True)

    need = json.loads((CACHE / "merger_fetch_list.json").read_text(encoding="utf-8"))
    scan = pd.read_parquet(CACHE / "merger_scan.parquet")
    meta = dict(zip(scan["accessionNumber"],
                    zip(scan["cik"].astype(str), scan["primaryDocument"].fillna(""))))
    log = CACHE / "merger_fetch_log.jsonl"
    tried: set[str] = set()
    if log.exists():
        for line in log.open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("status") == "ok":
                tried.add(r["accessionNumber"])
    todo = [a for a in need if a not in tried]
    print("清單 %d;已成功 %d;待抓 %d" % (len(need), len(tried), len(todo)), flush=True)

    t0 = time.time()
    n = ok = 0
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from s5_fetch_text import WORKERS
    items = todo[:limit]
    with log.open("a", encoding="utf-8") as f:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {}
            for acc in items:
                cik, prim = meta.get(acc, ("", ""))
                if not cik:
                    f.write(json.dumps({"accessionNumber": acc, "status": "無 cik"},
                                       ensure_ascii=False) + "\n")
                    continue
                futs[ex.submit(fetch_one, acc, cik, prim)] = acc
            for fut in as_completed(futs):
                try:
                    res = fut.result()
                except Exception as e:  # noqa: BLE001
                    res = {"accessionNumber": futs[fut],
                           "status": "例外:%s" % type(e).__name__}
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
                f.flush()
                n += 1
                ok += int(res["status"] == "ok")
                if n % 200 == 0:
                    print("  ...%d/%d ok=%d 用時%.0fs" % (n, len(futs), ok,
                                                          time.time() - t0), flush=True)
                if time.time() - t0 > budget:
                    for u in futs:
                        u.cancel()
                    break
    print("本支處理 %d;成功 %d;用時 %.0fs(%.2fs/宗)"
          % (n, ok, time.time() - t0, (time.time() - t0) / max(n, 1)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
