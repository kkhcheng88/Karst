# -*- coding: utf-8 -*-
"""KARST-177 step 3b: fetch the shards listed in out/missing_shards.csv from
EDGAR (https://data.sec.gov/submissions/<name>), <=10 req/s, fair-access
User-Agent, into data/sec/submissions/pages/. Checks manifest before each
fetch (idempotent re-run). On 403, backs off and retries with a capped
attempt count -- never spins forever. Failures go to out/failed.csv.
"""
from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO = Path(r"C:\projects\Karst")
CANON = REPO / "data" / "sec" / "submissions"
PAGES = CANON / "pages"
MANIFEST = CANON / "manifest.jsonl"
OUT = Path(__file__).resolve().parent / "out"

UA = "Casy Limited kaho.career@gmail.com"
FETCHED_BY = "KARST-177"
RATE = 8.0  # req/s, under the 10/s ceiling (matches KARST-167/174 precedent)
MAX_ATTEMPTS = 5
BASE_BACKOFF = 5.0  # seconds, doubles each 403 retry


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_manifest(rec: dict) -> None:
    with open(MANIFEST, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> None:
    with open(OUT / "missing_shards.csv", "r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    print(f"to fetch: {len(rows)}", flush=True)

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})

    ok, already, failed = 0, 0, []
    t0 = time.time()
    interval = 1.0 / RATE
    for i, row in enumerate(rows, 1):
        name = row["name"]
        dst = PAGES / name
        if dst.exists() and dst.stat().st_size > 0:
            already += 1
            continue
        url = f"https://data.sec.gov/submissions/{name}"
        attempt = 0
        backoff = BASE_BACKOFF
        success = False
        last_err = None
        while attempt < MAX_ATTEMPTS and not success:
            attempt += 1
            t_req = time.time()
            try:
                resp = session.get(url, timeout=60)
            except Exception as exc:  # noqa: BLE001
                last_err = f"exception: {exc}"
                time.sleep(backoff)
                backoff *= 2
                continue
            if resp.status_code == 200:
                raw = resp.content
                try:
                    json.loads(raw.decode("utf-8"))
                except Exception as exc:  # noqa: BLE001
                    last_err = f"bad json: {exc}"
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                dst.write_bytes(raw)
                import hashlib
                sha = hashlib.sha256(raw).hexdigest()
                append_manifest({
                    "cik": row["cik"], "file": name, "kind": "page",
                    "page": name.split("-submissions-")[-1].split(".")[0],
                    "bytes": len(raw), "sha256": sha,
                    "fetchedAt": now_iso(), "fetchedBy": FETCHED_BY,
                    "source": "fetched", "url": url,
                })
                success = True
                ok += 1
            elif resp.status_code == 403:
                last_err = "http403"
                time.sleep(backoff)
                backoff *= 2
            elif resp.status_code == 404:
                last_err = "http404"
                break  # not retryable
            else:
                last_err = f"http{resp.status_code}"
                time.sleep(backoff)
                backoff *= 2
            # rate limit pacing
            elapsed = time.time() - t_req
            if elapsed < interval:
                time.sleep(interval - elapsed)
        if not success:
            failed.append({"name": name, "cik": row["cik"], "error": last_err})
        if i % 200 == 0:
            print(f"  {i}/{len(rows)}  ok={ok} already={already} failed={len(failed)}  "
                  f"{time.time()-t0:.0f}s", flush=True)

    with open(OUT / "failed.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["name", "cik", "error"])
        w.writeheader()
        for r in failed:
            w.writerow(r)

    summary = {
        "requested": len(rows), "fetched_ok": ok, "already_present": already,
        "failed": len(failed), "seconds": round(time.time() - t0, 1),
    }
    with open(OUT / "fetch_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
