# -*- coding: utf-8 -*-
"""KARST-172 步驟一:對宇宙全體實體抓 EDGAR companyfacts,gzip 存入單一快取。

落點(D-134 單一快取):
  data/sec/companyfacts/CIK##########.json.gz
  data/sec/companyfacts/manifest.csv
      cik, entity_id, fetchedAt, fetchedBy, bytes, sha256, status, http_code

status:
  ok      —— 拿到 JSON 而且 facts 區塊非空
  empty   —— 拿到 JSON 但 facts 區塊空白,或者只有 dei(外國申報人多數是這一格)
  fail    —— 拿不到(404 / 重試耗盡)

抓之前先讀 manifest:已有而且 status = ok 的跳過,不重抓。
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import pathlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd

from sec_client import FORBIDDEN_COUNT, get

REPO = pathlib.Path(r"C:\projects\Karst")
CACHE = REPO / "data" / "sec" / "companyfacts"
MANIFEST = CACHE / "manifest.csv"
TICKET = "KARST-172"
COLS = ["cik", "entity_id", "fetchedAt", "fetchedBy", "bytes", "sha256",
        "status", "http_code"]


def load_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    df = pd.read_csv(MANIFEST, dtype=str)
    return {r["cik"]: dict(r) for _, r in df.iterrows()}


def write_manifest(done: dict[str, dict]) -> None:
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for k in sorted(done):
            w.writerow({c: done[k].get(c, "") for c in COLS})


def classify(raw: bytes) -> str:
    try:
        doc = json.loads(raw)
    except Exception:  # noqa: BLE001
        return "empty"
    facts = doc.get("facts") or {}
    useful = {k: v for k, v in facts.items() if k != "dei" and v}
    return "ok" if useful else "empty"


def rescan_disk(done: dict[str, dict]) -> dict[str, dict]:
    """由硬碟上已存在的 .json.gz 補回 manifest 沒有寫到的那批(中斷續跑用)。"""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for p in CACHE.glob("CIK*.json.gz"):
        cik = p.stem.replace("CIK", "").replace(".json", "")
        if done.get(cik, {}).get("status") in ("ok", "empty"):
            continue
        raw = gzip.open(p, "rb").read()
        done[cik] = dict(cik=cik, entity_id=cik, fetchedAt=now, fetchedBy=TICKET,
                         bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                         status=classify(raw), http_code=200)
    return done


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ent = pd.read_parquet(REPO / "data" / "universe" / "entities.parquet")
    ciks = sorted(ent["entity_id"].unique())
    done = rescan_disk(load_manifest())
    todo = [c for c in ciks if done.get(c, {}).get("status") not in ("ok", "empty")]
    print(f"實體 {len(ciks)} 個,已有的 {len(ciks) - len(todo)} 個,要抓 {len(todo)} 個",
          flush=True)

    t0 = time.time()
    counts = {"ok": 0, "empty": 0, "fail": 0}
    lock = threading.Lock()
    progress = [0]

    def one(cik: str) -> None:
        raw, err, code = get(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if raw is None:
            rec = dict(cik=cik, entity_id=cik, fetchedAt=now, fetchedBy=TICKET,
                       bytes=0, sha256="", status="fail", http_code=code)
        else:
            status = classify(raw)
            with gzip.open(CACHE / f"CIK{cik}.json.gz", "wb", compresslevel=6) as f:
                f.write(raw)
            rec = dict(cik=cik, entity_id=cik, fetchedAt=now, fetchedBy=TICKET,
                       bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                       status=status, http_code=code or 200)
        with lock:
            counts[rec["status"]] += 1
            done[cik] = rec
            progress[0] += 1
            i = progress[0]
            if i % 200 == 0 or i == len(todo):
                write_manifest(done)
                el = time.time() - t0
                print(f"  {i}/{len(todo)} ok={counts['ok']} empty={counts['empty']} "
                      f"fail={counts['fail']} 403={FORBIDDEN_COUNT[0]} {el / 60:.1f} 分",
                      flush=True)

    # 全域節流器在 sec_client 裡,無論幾多條執行緒都是每秒 8 個請求以下。
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(one, todo))

    write_manifest(done)
    total = sum(p.stat().st_size for p in CACHE.glob("*.json.gz"))
    summary = dict(entities=len(ciks), fetched=len(todo), counts=counts,
                   forbidden_403=FORBIDDEN_COUNT[0],
                   gz_bytes_on_disk=total,
                   raw_bytes_total=int(sum(int(v.get("bytes") or 0) for v in done.values())),
                   minutes=round((time.time() - t0) / 60, 1))
    (pathlib.Path(__file__).parent / "out" / "fetch_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
