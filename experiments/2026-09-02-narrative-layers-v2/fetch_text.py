"""KARST-157 步驟 2:新增公司的 10-K 全文入共用快取,再切出 Item 1(衍生物)。

D-134 原料唯一快取:
  · 全文只入 C:\\projects\\Karst\\data\\sec\\10k_text\\<TICKER>_<accession>.txt.gz,
    連同同目錄 manifest.jsonl(逐行 append,不整檔重寫——KARST-153 隊同時在寫)。
  · 抓之前先查 manifest,已有該 accession 就讀快取,不再打 EDGAR。
  · 本票目錄只存衍生物:data/item1/<TICKER>_<切片日>.txt.gz(切節後的 Item 1)。

574 家那批的 Item 1 直接讀 KARST-152 的衍生物,不重抓(見 CRITERIA.md 第 3 節)。

EDGAR:User-Agent `Casy Limited kaho.career@gmail.com`,全域 ≤8 req/s,重試上限 3。
可續跑。Run: PYTHONUTF8=1 python fetch_text.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from lxml import html as LH

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
DATA = HERE / "data"
ITEM1 = DATA / "item1"
SUBS = DATA / "submissions"
for d in (OUT, ITEM1, SUBS):
    d.mkdir(parents=True, exist_ok=True)

# D-134 共用原料快取(倉根 data/ 已被 .gitignore 擋住)
CACHE = REPO / "data" / "sec" / "10k_text"
CACHE.mkdir(parents=True, exist_ok=True)
MANIFEST = CACHE / "manifest.jsonl"

TICKERS_JSON = REPO / "experiments" / "2026-09-02-narrative-layers" / "data" / "company_tickers_sec.json"

SLICES = ["2015-06-30", "2019-06-30", "2023-06-30"]
MAX_STALE_DAYS = 500

UA = "Casy Limited kaho.career@gmail.com"
HEADERS = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
RATE = 8.0
MAX_RETRIES = 3
WORKERS = 6

_local = threading.local()
_rate_lock = threading.Lock()
_next_slot = [0.0]
_manifest_lock = threading.Lock()


def _session() -> requests.Session:
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update(HEADERS)
        _local.s = s
    return s


def _throttle() -> None:
    with _rate_lock:
        now = time.monotonic()
        slot = max(now, _next_slot[0])
        _next_slot[0] = slot + 1.0 / RATE
    wait = slot - time.monotonic()
    if wait > 0:
        time.sleep(wait)


def get(url: str) -> requests.Response:
    last = None
    for attempt in range(MAX_RETRIES):
        _throttle()
        try:
            r = _session().get(url, timeout=60)
            r.raise_for_status()
            return r
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"{url}: {last}")


# ---------------- 共用快取 ----------------

def read_manifest() -> dict[str, dict]:
    """accession -> record。逐行讀,壞行跳過(別隊可能同時在 append)。"""
    out: dict[str, dict] = {}
    if not MANIFEST.exists():
        return out
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        acc = rec.get("accession")
        if acc:
            out[acc] = rec
    return out


def append_manifest(rec: dict) -> None:
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    with _manifest_lock:
        with open(MANIFEST, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()


def cache_path(ticker: str, accession: str) -> Path:
    return CACHE / f"{ticker}_{accession}.txt.gz"


# ---------------- EDGAR ----------------

def load_cik_map() -> tuple[dict[str, str], dict[str, str]]:
    data = json.loads(TICKERS_JSON.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    titles: dict[str, str] = {}
    for _key, row in data.items():
        t = row["ticker"].upper()
        if t in out:
            continue
        out[t] = str(row["cik_str"]).zfill(10)
        titles[t] = row.get("title", "")
    return out, titles


def filings_10k(cik: str) -> list[tuple[str, str, str, str]]:
    cache = SUBS / f"{cik}.json"
    if cache.exists():
        return [tuple(r) for r in json.loads(cache.read_text(encoding="utf-8"))]
    sub = get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
    blocks = [sub["filings"]["recent"]]
    for extra in sub["filings"].get("files", []):
        blocks.append(get(f"https://data.sec.gov/submissions/{extra['name']}").json())
    rows: list[tuple[str, str, str, str]] = []
    for b in blocks:
        for form, acc, doc, rdate, fdate in zip(
            b["form"], b["accessionNumber"], b["primaryDocument"],
            b["reportDate"], b["filingDate"],
        ):
            if form != "10-K" or not fdate or not doc:
                continue
            rows.append((fdate, rdate, acc.replace("-", ""), doc))
    rows.sort()
    cache.write_text(json.dumps(rows), encoding="utf-8")
    return rows


# ---------------- 切節(與 KARST-152 逐字相同) ----------------

ITEM1_START = re.compile(r"item\s*1\s*[.\-:\u2013\u2014]?\s*business", re.I)
ITEM1A_END = re.compile(r"item\s*1a\s*[.\-:\u2013\u2014]?\s*risk\s*factors", re.I)
ITEM2_END = re.compile(r"item\s*2\s*[.\-:\u2013\u2014]?\s*propert", re.I)
MIN_SPAN = 3000
MIN_TEXT = 2000
_WS = re.compile(r"[ \t\r\n\u00a0]+")


def extract_item1(text: str) -> tuple[str, str]:
    starts = [m.start() for m in ITEM1_START.finditer(text)]
    if not starts:
        return "", "NO-ITEM1-MARKER"
    for end_re, label in ((ITEM1A_END, "Item1..Item1A"), (ITEM2_END, "Item1..Item2")):
        ends = [m.start() for m in end_re.finditer(text)]
        spans = []
        for s in starts:
            e = [x for x in ends if x > s + MIN_SPAN]
            if e:
                spans.append((s, e[0]))
        ok = [sp for sp in spans if sp[1] - sp[0] >= MIN_SPAN]
        if ok:
            s, e = min(ok, key=lambda sp: sp[1] - sp[0])
            return text[s:e], f"{label} (min-span of {len(spans)} cands)"
    return "", "NO-VALID-SPAN"


def clean_html(raw: bytes) -> str:
    doc = LH.fromstring(raw)
    for bad in doc.xpath("//script|//style"):
        bad.getparent().remove(bad)
    return _WS.sub(" ", " ".join(doc.itertext()))


# ---------------- 主流程 ----------------

def do_job(job: dict, have: dict[str, dict]) -> tuple[str, dict]:
    ticker, sl, acc = job["ticker"], job["slice"], job["accession"]
    key = f"{ticker}|{sl}"
    cpath = cache_path(ticker, acc)

    if acc in have and cpath.exists():
        full = gzip.decompress(cpath.read_bytes()).decode("utf-8")
        src = "cache"
    else:
        try:
            raw = get(job["url"]).content
        except Exception as exc:  # noqa: BLE001
            return key, {"ok": False, "why": f"fetch: {exc}"[:180], "url": job["url"]}
        try:
            full = clean_html(raw)
        except Exception as exc:  # noqa: BLE001
            return key, {"ok": False, "why": f"parse: {exc}"[:180], "url": job["url"]}
        blob = full.encode("utf-8")
        cpath.write_bytes(gzip.compress(blob))
        append_manifest({
            "ticker": ticker, "cik": job["cik"], "accession": acc, "form": "10-K",
            "filingDate": job["filingDate"], "reportDate": job["reportDate"],
            "primaryDoc": job["doc"], "url": job["url"],
            "path": f"{ticker}_{acc}.txt.gz", "chars": len(full),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "by": "KARST-157",
        })
        src = "edgar"

    item1, how = extract_item1(full)
    if len(item1) < MIN_TEXT:
        return key, {"ok": False, "why": f"extract failed: {how} ({len(item1)} chars)",
                     "accession": acc, "filingDate": job["filingDate"], "source": src}
    (ITEM1 / f"{ticker}_{sl}.txt.gz").write_bytes(gzip.compress(item1.encode("utf-8")))
    return key, {"ok": True, "cik": job["cik"], "accession": acc,
                 "filingDate": job["filingDate"], "reportDate": job["reportDate"],
                 "chars": len(item1), "extract": how, "source": src, "url": job["url"]}


def main() -> int:
    uni = json.loads((OUT / "universe_v2.json").read_text(encoding="utf-8"))
    price_meta_path = OUT / "new_price_meta.json"
    price_meta = json.loads(price_meta_path.read_text(encoding="utf-8")) if price_meta_path.exists() else {}
    drop = set(price_meta.get("non_equity_dropped", [])) | set(price_meta.get("price_missing", []))
    new = [t for t in uni["new_tickers"] if t not in drop]
    print(f"new tickers with prices: {len(new)}", flush=True)

    cikmap, titles = load_cik_map()
    have = read_manifest()
    print(f"shared cache manifest: {len(have)} accessions already", flush=True)

    mpath = OUT / "text_manifest_new.json"
    manifest: dict[str, dict] = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}

    filings: dict[str, list] = {}
    zero: list[str] = []
    no_cik: list[str] = []

    def idx_job(t: str):
        cik = cikmap.get(t)
        if not cik:
            return t, None, "no CIK"
        try:
            return t, filings_10k(cik), None
        except Exception as exc:  # noqa: BLE001
            return t, None, f"submissions: {exc}"[:180]

    with ThreadPoolExecutor(WORKERS) as ex:
        for n, fut in enumerate(as_completed([ex.submit(idx_job, t) for t in new]), 1):
            t, rows, err = fut.result()
            if err or rows is None:
                (no_cik if err == "no CIK" else zero).append(f"{t}: {err}")
                for sl in SLICES:
                    manifest[f"{t}|{sl}"] = {"ok": False, "why": err or "no filings"}
                continue
            if not rows:
                zero.append(f"{t} (CIK {cikmap.get(t)}, {titles.get(t, '')}): no 10-K")
                for sl in SLICES:
                    manifest[f"{t}|{sl}"] = {"ok": False, "why": "CIK has no 10-K filings"}
                continue
            filings[t] = rows
            if n % 40 == 0:
                print(f"  indexes {n}/{len(new)}", flush=True)

    jobs = []
    for t, rows in filings.items():
        cik = cikmap[t]
        for sl in SLICES:
            key = f"{t}|{sl}"
            dest = ITEM1 / f"{t}_{sl}.txt.gz"
            if manifest.get(key, {}).get("ok") and dest.exists():
                continue
            cut = pd.Timestamp(sl)
            cands = [r for r in rows if pd.Timestamp(r[0]) <= cut]
            if not cands:
                manifest[key] = {"ok": False, "why": "no 10-K filed before slice"}
                continue
            fdate, rdate, acc, doc = max(cands, key=lambda r: r[0])
            stale = (cut - pd.Timestamp(fdate)).days
            if stale > MAX_STALE_DAYS:
                manifest[key] = {"ok": False, "why": f"stale {stale}d (filed {fdate})"}
                continue
            jobs.append({"ticker": t, "slice": sl, "cik": cik, "accession": acc,
                         "doc": doc, "filingDate": fdate, "reportDate": rdate,
                         "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"})

    print(f"documents to process: {len(jobs)}", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = [ex.submit(do_job, j, have) for j in jobs]
        for n, fut in enumerate(as_completed(futs), 1):
            key, rec = fut.result()
            manifest[key] = rec
            if n % 40 == 0:
                mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
                rate = n / max(time.time() - t0, 0.01)
                print(f"  docs {n}/{len(jobs)} ({rate:.1f}/s)", flush=True)

    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "text_missing_new.json").write_text(
        json.dumps({"no_cik": no_cik, "zero_or_error": zero}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    for sl in SLICES:
        ok = sum(1 for k, v in manifest.items() if k.endswith(sl) and v.get("ok"))
        print(f"slice {sl}: {ok}/{len(new)} new texts")
    print(f"no CIK: {len(no_cik)}; zero/err: {len(zero)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
