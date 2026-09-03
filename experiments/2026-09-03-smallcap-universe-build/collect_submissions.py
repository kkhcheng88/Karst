"""KARST-167 步驟一:把 8,001 個 CIK 的申報索引收進單一快取 data/sec/submissions/。

規矩(D-134 原料唯一快取):
- 抓之前先查快取與 manifest,已有不重抓。
- 倉內其他實驗目錄早已抓過的完整 submissions 檔,先複製入單一快取再算,省 EDGAR 請求。
- EDGAR 每秒不超過 10 個請求;本腳本設 8 個/秒的令牌桶。
- User-Agent 必須是 Casy Limited kaho.career@gmail.com。

只寫 data/sec/submissions/ 與同目錄 manifest.jsonl,不寫任何其他地方。
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

REPO = r"C:\projects\Karst"
CACHE = os.path.join(REPO, "data", "sec", "submissions")
MANIFEST = os.path.join(CACHE, "manifest.jsonl")
TICKERS = os.path.join(REPO, "data", "sec", "company_tickers.json")
UA = "Casy Limited kaho.career@gmail.com"
RATE = 8.0  # 每秒請求上限,低於 EDGAR 的 10
WORKERS = 6
NAME_RE = re.compile(r"^(?:CIK)?(\d{10})\.json$")

_lock = threading.Lock()
_manifest_lock = threading.Lock()
_next_slot = [time.monotonic()]


def throttle() -> None:
    with _lock:
        now = time.monotonic()
        slot = max(now, _next_slot[0])
        _next_slot[0] = slot + 1.0 / RATE
    delay = slot - time.monotonic()
    if delay > 0:
        time.sleep(delay)


def cache_path(cik: str) -> str:
    return os.path.join(CACHE, f"CIK{cik}.json")


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest_ciks() -> set[str]:
    got: set[str] = set()
    if not os.path.exists(MANIFEST):
        return got
    with open(MANIFEST, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                got.add(json.loads(line)["cik"])
            except Exception:
                continue
    return got


def append_manifest(row: dict) -> None:
    with _manifest_lock:
        with open(MANIFEST, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def is_full_submission(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
    except Exception:
        return False
    return isinstance(obj, dict) and "filings" in obj and "cik" in obj


def describe(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        obj = json.load(fh)
    return {
        "name": obj.get("name"),
        "entityType": obj.get("entityType"),
        "sic": obj.get("sic"),
        "tickers": obj.get("tickers"),
        "exchanges": obj.get("exchanges"),
    }


def manifest_row(cik: str, path: str, source: str) -> dict:
    info = describe(path)
    return {
        "cik": cik,
        "file": os.path.basename(path),
        "name": info["name"],
        "entityType": info["entityType"],
        "sic": info["sic"],
        "tickers": info["tickers"],
        "exchanges": info["exchanges"],
        "url": f"https://data.sec.gov/submissions/CIK{cik}.json",
        "bytes": os.path.getsize(path),
        "sha256": sha256_of(path),
        "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetchedBy": "KARST-167 universe-167",
        "source": source,
    }


def fetch(cik: str, session: requests.Session) -> tuple[str, str]:
    path = cache_path(cik)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    for attempt in range(4):
        throttle()
        try:
            resp = session.get(url, timeout=30)
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                return cik, f"error:{type(exc).__name__}"
            time.sleep(1.5 * (attempt + 1))
            continue
        if resp.status_code == 200:
            tmp = path + ".part"
            with open(tmp, "wb") as fh:
                fh.write(resp.content)
            if not is_full_submission(tmp):
                os.remove(tmp)
                return cik, "bad_payload"
            os.replace(tmp, path)
            append_manifest(manifest_row(cik, path, "edgar"))
            return cik, "fetched"
        if resp.status_code == 404:
            return cik, "http404"
        if resp.status_code in (403, 429, 503):
            time.sleep(2.0 * (attempt + 1))
            continue
        return cik, f"http{resp.status_code}"
    return cik, "retries_exhausted"


def main() -> int:
    os.makedirs(CACHE, exist_ok=True)
    with open(TICKERS, "r", encoding="utf-8") as fh:
        tmap = json.load(fh)
    ciks = sorted(set(tmap.values()))
    print(f"tickers={len(tmap)} unique_cik={len(ciks)}", flush=True)

    # 1) 先把單一快取裡已有的檔登記入 manifest(倉內 119 份從來未登記過)
    in_manifest = load_manifest_ciks()
    registered = 0
    for path in glob.glob(os.path.join(CACHE, "*.json")):
        m = NAME_RE.match(os.path.basename(path))
        if not m or m.group(1) in in_manifest:
            continue
        if not is_full_submission(path):
            continue
        append_manifest(manifest_row(m.group(1), path, "pre-existing"))
        in_manifest.add(m.group(1))
        registered += 1
    print(f"registered_pre_existing={registered}", flush=True)

    have = {m.group(1) for p in glob.glob(os.path.join(CACHE, "*.json"))
            if (m := NAME_RE.match(os.path.basename(p)))}

    # 2) 由其他實驗目錄複製已抓過的完整檔(位元複製,不解碼內容)
    copied = 0
    for src_dir in sorted(glob.glob(os.path.join(REPO, "experiments", "*", "data", "submissions"))):
        for path in glob.glob(os.path.join(src_dir, "*.json")):
            m = NAME_RE.match(os.path.basename(path))
            if not m:
                continue
            cik = m.group(1)
            if cik in have or cik not in set(ciks):
                continue
            if not is_full_submission(path):
                continue
            dest = cache_path(cik)
            shutil.copyfile(path, dest)
            append_manifest(manifest_row(cik, dest, f"reused:{os.path.relpath(src_dir, REPO)}"))
            have.add(cik)
            copied += 1
    print(f"copied_from_experiments={copied}", flush=True)

    todo = [c for c in ciks if c not in have]
    print(f"cached={len(ciks) - len(todo)} to_fetch={len(todo)}", flush=True)
    est = len(todo) / RATE / 60.0
    print(f"estimated_minutes={est:.1f}", flush=True)

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})

    counts: dict[str, int] = {}
    done = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for cik, status in pool.map(lambda c: fetch(c, session), todo):
            counts[status] = counts.get(status, 0) + 1
            done += 1
            if done % 250 == 0:
                rate = done / max(time.time() - started, 1e-9)
                print(f"progress {done}/{len(todo)} {rate:.1f}/s {counts}", flush=True)

    print(f"done={done} counts={counts}", flush=True)
    print(f"elapsed_minutes={(time.time() - started) / 60:.1f}", flush=True)
    with open(os.path.join(REPO, "experiments", "2026-09-03-smallcap-universe-build",
                           "out", "collect_submissions_summary.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "unique_cik": len(ciks),
            "registered_pre_existing": registered,
            "copied_from_experiments": copied,
            "fetch_attempted": len(todo),
            "counts": counts,
            "elapsed_minutes": round((time.time() - started) / 60, 2),
            "rate_limit_per_sec": RATE,
            "user_agent": UA,
        }, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
