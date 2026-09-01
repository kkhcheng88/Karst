# -*- coding: utf-8 -*-
"""KARST-146 step 4: download SEC companyfacts for every resolved CIK.

One JSON per CIK into data/secfacts/. The whole data/ directory is gitignored.
Resumable: an existing non-empty file is skipped, so the script can be re-run
after an interruption.

Run:  PYTHONUTF8=1 python download_facts.py
"""
from __future__ import annotations

import json
import pathlib
import time

import pandas as pd

from sec_client import get

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
CACHE = HERE / "data" / "secfacts"
CACHE.mkdir(parents=True, exist_ok=True)


def main() -> None:
    uni = pd.read_csv(OUT / "universe_cik.csv", dtype=str).fillna("")
    ciks = sorted(uni[uni.cik != ""].cik.unique())
    print(f"{len(ciks)} unique CIKs to fetch", flush=True)

    log, t0 = [], time.time()
    done = skipped = failed = 0
    for i, cik in enumerate(ciks, 1):
        p = CACHE / f"CIK{cik}.json"
        if p.exists() and p.stat().st_size > 0:
            skipped += 1
            continue
        raw, err = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
        if raw is None:
            failed += 1
            log.append(dict(cik=cik, status="failed", detail=err))
            continue
        p.write_bytes(raw)
        done += 1
        log.append(dict(cik=cik, status="ok", bytes=len(raw)))
        if i % 50 == 0:
            el = time.time() - t0
            print(f"{i}/{len(ciks)}  ok={done} skip={skipped} fail={failed} "
                  f"{el:.0f}s", flush=True)

    pd.DataFrame(log).to_csv(OUT / "download_log.csv", index=False,
                             encoding="utf-8")
    total = sum(f.stat().st_size for f in CACHE.glob("*.json"))
    summary = dict(unique_ciks=len(ciks), downloaded=done, already_present=skipped,
                   failed=failed, bytes_on_disk=total,
                   seconds=round(time.time() - t0, 1))
    (OUT / "download_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print("DONE", summary, flush=True)


if __name__ == "__main__":
    main()
