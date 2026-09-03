# -*- coding: utf-8 -*-
"""KARST-155 step 1: build the 8-K Item 4.02 (non-reliance) index.

CRITERIA.md section 5, flag F2. A formal restatement is broadcast - it is the
opposite of a silent revision - so those events must be identifiable and pulled
out of the main arm.

Source: the SEC submissions endpoint. The `filings.recent` block only reaches
back ~1000 filings, so the older `filings.files` shards are fetched too.

SEC fair access: <=10 req/s, identifying User-Agent (sec_client enforces both).

Output:
  data/submissions/CIK*.json      raw cache (not in git)
  out/eightk_402.csv              cik, filing_date, items
  out/eightk_402_fetch.json       fetch stats
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import time

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
PANEL_DIR = REPO / "experiments" / "2026-09-02-fundamentals-panel"
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("sec_client", PANEL_DIR / "sec_client.py")
sec_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sec_client)

# KARST-177:正本已收編歷史分頁檔(data/sec/submissions/pages/),寫入路徑改指正本。
# 主檔(CIK<10>.json)住 data/sec/submissions/ 頂層;分頁檔(CIK<10>-submissions-00N.json)
# 住 data/sec/submissions/pages/。CACHE 只是路徑常數,抓之前先查、查不到才打 EDGAR 的
# load_or_fetch() 邏輯一字未改。
EXISTING = REPO / "data" / "sec" / "submissions"
PAGES_CACHE = EXISTING / "pages"


def load_or_fetch(name: str) -> dict | None:
    """name is like CIK0000004281.json or CIK0000004281-submissions-001.json."""
    is_shard = "-submissions-" in name
    local = (PAGES_CACHE if is_shard else EXISTING) / name
    if local.exists() and local.stat().st_size > 0:
        return json.loads(local.read_text(encoding="utf-8"))
    url = f"https://data.sec.gov/submissions/{name}"
    raw, err = sec_client.get(url)
    if raw is None:
        return None
    local.write_bytes(raw)
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def rows_from_block(cik: str, blk: dict) -> list[dict]:
    forms = blk.get("form", [])
    dates = blk.get("filingDate", [])
    items = blk.get("items", [""] * len(forms))
    out = []
    for i, form in enumerate(forms):
        if not form.startswith("8-K"):
            continue
        it = items[i] if i < len(items) else ""
        if not it:
            continue
        codes = {c.strip() for c in it.split(",")}
        if any(c.startswith("4.02") for c in codes):
            out.append(dict(cik=cik, filing_date=dates[i], form=form, items=it))
    return out


def main() -> None:
    uni = pd.read_csv(PANEL_DIR / "out" / "universe_cik.csv", dtype=str).fillna("")
    have_facts = {p.name[3:-5] for p in (PANEL_DIR / "data" / "secfacts").glob("CIK*.json")}
    ciks = sorted({c for c in uni["cik"] if c} & have_facts)
    print(f"{len(ciks)} CIKs to scan", flush=True)

    rows, failed, shards = [], [], 0
    t0 = time.time()
    for i, cik in enumerate(ciks, 1):
        doc = load_or_fetch(f"CIK{cik}.json")
        if doc is None:
            failed.append(cik)
            continue
        filings = doc.get("filings", {})
        rows += rows_from_block(cik, filings.get("recent", {}))
        for f in filings.get("files", []):
            sub = load_or_fetch(f["name"])
            shards += 1
            if sub is None:
                failed.append(f["name"])
                continue
            rows += rows_from_block(cik, sub)
        if i % 100 == 0:
            print(f"  {i}/{len(ciks)}  {len(rows)} hits  {time.time()-t0:.0f}s",
                  flush=True)

    df = pd.DataFrame(rows).drop_duplicates()
    df.to_csv(OUT / "eightk_402.csv", index=False, encoding="utf-8")
    meta = dict(ciks_scanned=len(ciks), shards_fetched=shards,
                item_402_filings=int(len(df)),
                companies_with_402=int(df.cik.nunique()) if len(df) else 0,
                failed=failed[:50], failed_n=len(failed),
                seconds=round(time.time() - t0, 1))
    (OUT / "eightk_402_fetch.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(meta, indent=2), flush=True)


if __name__ == "__main__":
    sys.exit(main())
