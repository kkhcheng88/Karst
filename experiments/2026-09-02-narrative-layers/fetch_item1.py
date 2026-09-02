"""KARST-152 步驟 1:按申報日定格抓 10-K 的 Item 1 Business。

零偷看:每個切片只取 filingDate <= 切片日的最新一份 10-K,且距切片日不超過 500 日。
切節規則見 CRITERIA.md 第 3 節(承接 bottleneck-scan-prototype/fetch_mdna.py 的做法,
彎引號與「夠長之中最短」那兩個坑已在原型驗過)。

單線程跑 1722 份太慢(實測約 3 小時),故用 6 條線 + 全域速率閘(≤8 req/s,
證監會上限 10 req/s),HTML 用 lxml itertext 取文(每個文字節點之間補一個空格,
避免跨標籤黐字),比 BeautifulSoup get_text 快數倍。

原始文本落 data/(gitignore 擋住)。可續跑。
Run: PYTHONUTF8=1 python fetch_item1.py
"""
from __future__ import annotations

import gzip
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
from lxml import html as LH

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TEXTS = DATA / "item1"
TEXTS.mkdir(parents=True, exist_ok=True)
SUBS = DATA / "submissions"
SUBS.mkdir(parents=True, exist_ok=True)
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

PARQUET = Path(r"C:\projects\Karst\experiments\2026-09-02-timing-sweep\data\daily_close.parquet")
# 倉內 data/sec/company_tickers.json 是舊快取,且與證監會現行檔一樣有一個坑:
# 重組成控股公司的代碼(例如 XOM 現指向 ExxonMobil Holdings Corp,CIK 2115436)
# 會指去一個沒有歷史 10-K 的新實體。故此本票自己下載一份現行檔,並把「0 份 10-K」
# 的代碼列入缺失名單(不自動猜替代 CIK,猜錯會把別家公司的文本掛在這個代碼上)。
TICKERS_JSON = HERE / "data" / "company_tickers_sec.json"
ETFS = {"SPY", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"}

SLICES = ["2015-06-30", "2019-06-30", "2023-06-30"]
MAX_STALE_DAYS = 500

UA = "Casy Limited kaho.career@gmail.com"
HEADERS = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
RATE = 8.0            # req/s 全域上限(證監會容許 10)
MAX_RETRIES = 3       # 重試上限寫死
WORKERS = 6

_local = threading.local()
_rate_lock = threading.Lock()
_next_slot = [0.0]


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


def load_cik_map() -> tuple[dict[str, str], dict[str, str]]:
    """Return (ticker -> cik, ticker -> title). 同一代碼多次出現取第一次。"""
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
    """Return [(filingDate, reportDate, accession_nodash, primaryDoc)] for all 10-Ks."""
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


ITEM1_START = re.compile(r"item\s*1\s*[.\-:\u2013\u2014]?\s*business", re.I)
ITEM1A_END = re.compile(r"item\s*1a\s*[.\-:\u2013\u2014]?\s*risk\s*factors", re.I)
ITEM2_END = re.compile(r"item\s*2\s*[.\-:\u2013\u2014]?\s*propert", re.I)

MIN_SPAN = 3000
MIN_TEXT = 2000


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


_WS = re.compile(r"[ \t\r\n\u00a0]+")


def clean_html(raw: bytes) -> str:
    doc = LH.fromstring(raw)
    for bad in doc.xpath("//script|//style"):
        bad.getparent().remove(bad)
    text = " ".join(doc.itertext())
    return _WS.sub(" ", text)


def do_job(job: tuple[str, str, str, str, str, str]) -> tuple[str, dict]:
    ticker, sl, url, cik, fdate, rdate = job
    key = f"{ticker}|{sl}"
    try:
        raw = get(url).content
    except Exception as exc:  # noqa: BLE001
        return key, {"ok": False, "why": f"fetch: {exc}"[:180], "url": url}
    try:
        text = clean_html(raw)
    except Exception as exc:  # noqa: BLE001
        return key, {"ok": False, "why": f"parse: {exc}"[:180], "url": url}
    item1, how = extract_item1(text)
    if len(item1) < MIN_TEXT:
        return key, {"ok": False, "why": f"extract failed: {how} ({len(item1)} chars)",
                     "filingDate": fdate, "url": url}
    (TEXTS / f"{ticker}_{sl}.txt.gz").write_bytes(gzip.compress(item1.encode("utf-8")))
    return key, {"ok": True, "cik": cik, "filingDate": fdate, "reportDate": rdate,
                 "chars": len(item1), "extract": how, "url": url}


def main() -> int:
    df = pd.read_parquet(PARQUET)
    tickers = sorted(c for c in df.columns if c not in ETFS)
    cikmap, titles = load_cik_map()

    manifest_path = OUT / "text_manifest.json"
    manifest: dict[str, dict] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # ---- 第一步:取每家公司的 10-K 清單(可續跑,已快取者不再打 EDGAR) ----
    print(f"universe {len(tickers)} tickers; fetching filing indexes...", flush=True)
    filings: dict[str, list] = {}
    zero_filers: list[str] = []

    def idx_job(t: str):
        cik = cikmap.get(t)
        if not cik:
            return t, None, "no CIK"
        try:
            return t, filings_10k(cik), None
        except Exception as exc:  # noqa: BLE001
            return t, None, f"submissions: {exc}"[:180]

    with ThreadPoolExecutor(WORKERS) as ex:
        for n, fut in enumerate(as_completed([ex.submit(idx_job, t) for t in tickers]), 1):
            t, rows, err = fut.result()
            if err or rows is None:
                for sl in SLICES:
                    manifest[f"{t}|{sl}"] = {"ok": False, "why": err or "no filings"}
                continue
            if not rows:
                zero_filers.append(f"{t} (CIK {cikmap.get(t)}, {titles.get(t, '')})")
                for sl in SLICES:
                    manifest[f"{t}|{sl}"] = {"ok": False, "why": "CIK has no 10-K filings"}
                continue
            filings[t] = rows
            if n % 100 == 0:
                print(f"  indexes {n}/{len(tickers)}", flush=True)

    # ---- 第二步:按切片挑定格的那一份,抓文並切節 ----
    jobs = []
    for t, rows in filings.items():
        cik = cikmap[t]
        for sl in SLICES:
            key = f"{t}|{sl}"
            dest = TEXTS / f"{t}_{sl}.txt.gz"
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
            if dest.exists():
                manifest[key] = {"ok": True, "cik": cik, "filingDate": fdate,
                                 "reportDate": rdate, "extract": "cached",
                                 "chars": len(gzip.decompress(dest.read_bytes()))}
                continue
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
            jobs.append((t, sl, url, cik, fdate, rdate))

    print(f"documents to fetch: {len(jobs)}", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = [ex.submit(do_job, j) for j in jobs]
        for n, fut in enumerate(as_completed(futs), 1):
            key, rec = fut.result()
            manifest[key] = rec
            if n % 50 == 0:
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
                rate = n / (time.time() - t0)
                print(f"  docs {n}/{len(jobs)} ({rate:.1f}/s, eta "
                      f"{(len(jobs) - n) / max(rate, 0.01) / 60:.0f} min)", flush=True)

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    for sl in SLICES:
        ok = sum(1 for k, v in manifest.items() if k.endswith(sl) and v.get("ok"))
        print(f"slice {sl}: {ok}/{len(tickers)} texts")
    print(f"zero-10K tickers ({len(zero_filers)}): {zero_filers}")
    (OUT / "zero_filers.json").write_text(
        json.dumps(zero_filers, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
