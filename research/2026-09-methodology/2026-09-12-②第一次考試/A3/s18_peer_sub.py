# -*- coding: utf-8 -*-
"""KARST-232 第七步(根因修復):補抓本地缺的更舊 submissions 分片。

本地 `data/sec/submissions/CIK*.json` 只存 `filings.recent`(上限約 1000 筆);
申報量大的發行人窗口短,年報與前兩份季報會落在 `filings.files` 指到的更舊分片,
而 8,116 個本地檔之中一個分片都沒有。後果兩層:
  (一)KARST-230 點名的被截斷文件(某槽缺第二份季報)——分片裡就有;
  (二)同業年報「查不到」37 家之中大部分——同一根因。

本支按 T1 − 400 日為下限,只補抓到足以覆蓋該日的那一兩塊分片,單線程 3 請求/秒,
寫 `A3/cache/peer_submissions/`(不碰 `data/`),可重複跑。
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
SUB = Path(r"C:\projects\Karst") / "data" / "sec" / "submissions"

NEED_BACK_DAYS = 400


def need_from(t1: str) -> str:
    y, m, d = (int(x) for x in t1.split("-"))
    return (date(y, m, d) - timedelta(days=NEED_BACK_DAYS)).isoformat()


def main() -> None:
    sys.path.insert(0, str(HERE))
    import s15_lib as L

    plan = json.loads((CACHE / "enrich_plan.json").read_text(encoding="utf-8"))
    picks = json.loads((CACHE / "picks_final.json").read_text(encoding="utf-8"))
    meta = pd.read_parquet(CACHE / "population_improvement.parquet").set_index("accessionNumber")

    want: dict[str, str] = {}      # cik -> 下限日
    for f in picks["final"]:
        m = meta.loc[f["acc"]]
        nf = need_from(m["reaction_date"])
        want[m["cik"]] = min(want.get(m["cik"], nf), nf)
    for slot, pv in plan["peers"].items():
        m = meta.loc[[x["acc"] for x in picks["final"] if x["slot"] == slot][0]]
        nf = need_from(m["reaction_date"])
        for pr in pv["peers"]:
            want[pr["entity_id"]] = min(want.get(pr["entity_id"], nf), nf)

    dest = CACHE / "peer_submissions"
    dest.mkdir(parents=True, exist_ok=True)
    log = (CACHE / "sub_fetch_log.jsonl").open("a", encoding="utf-8")
    t0 = time.time()
    n_get = n_skip = n_err = n_files = 0
    for cik, lo in sorted(want.items()):
        p = SUB / ("CIK%s.json" % cik)
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        files = d.get("filings", {}).get("files", [])
        if not files:
            continue
        n_files += 1
        take = []
        for f in files:
            if f["filingTo"] < lo:
                break
            take.append(f)
            if f["filingFrom"] < lo:
                break
        for f in take:
            q = dest / f["name"]
            if q.exists():
                n_skip += 1
                continue
            url = "https://data.sec.gov/submissions/%s" % f["name"]
            try:
                raw = L.http_get(url)
                q.write_bytes(raw)
                n_get += 1
            except Exception as e:                      # noqa: BLE001
                n_err += 1
                log.write(json.dumps(dict(cik=cik, name=f["name"], status=str(e)),
                                     ensure_ascii=False) + "\n")
                log.flush()
                continue
            log.write(json.dumps(dict(cik=cik, name=f["name"], status="ok",
                                      from_=f["filingFrom"], to=f["filingTo"]),
                                 ensure_ascii=False) + "\n")
            log.flush()
            if n_get % 10 == 0:
                print("  ...抓 %d 用時 %.0fs" % (n_get, time.time() - t0), flush=True)
    print("需補分片的發行人 %d;新抓 %d;已快取 %d;失敗 %d;用時 %.0fs"
          % (n_files, n_get, n_skip, n_err, time.time() - t0))
    log.close()
    (CACHE / "sub_fetch_summary.json").write_text(json.dumps(
        dict(issuers=n_files, fetched=n_get, cached=n_skip, failed=n_err),
        ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
