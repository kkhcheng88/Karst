"""KARST-153 步驟 1:抓 10-K 的 Item 7 MD&A 與 Item 1A Risk Factors。

切節規則見 CRITERIA.md 第 3 節(跑數前凍結)。承接
experiments/2026-09-02-bottleneck-scan-prototype/fetch_mdna.py 的做法:
彎引號 U+2019、以及「夠長之中最短」那兩個坑已在原型驗過。

零偷看:每一份年報只用它自己的 filingDate 生效,本步驟不碰任何價格。

原始節文本落 data/(gitignore 擋住)。可續跑。
Run: PYTHONUTF8=1 python fetch_sections.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
import threading
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
from lxml import html as LH

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SEC_DIR = DATA / "sections"
SUBS = DATA / "submissions"
for d in (SEC_DIR, SUBS):
    d.mkdir(parents=True, exist_ok=True)
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

PARQUET = Path(r"C:\projects\Karst\experiments\2026-09-02-timing-sweep\data\daily_close.parquet")

# 數據治理(用戶 2026-09-02 明令,經主 agent 轉達):同一份原料只准有一份副本。
#  - 代號→CIK 對照只讀倉內共用檔,不在本票另存一份。
#  - 每份 10-K 的 clean_html 全文純文本存入倉內共用庫 data/sec/10k_text/,
#    連同 manifest.jsonl;抓之前先查 manifest,已有就讀共用庫,不再打 EDGAR。
#    本票的切節 gz 是衍生物,記錄 accession 指回共用庫那一份。
REPO_SEC = Path(r"C:\projects\Karst\data\sec")
TICKERS_JSON = REPO_SEC / "company_tickers.json"
FULLTEXT = REPO_SEC / "10k_text"
FULLTEXT.mkdir(parents=True, exist_ok=True)
FT_MANIFEST = FULLTEXT / "manifest.jsonl"
_ft_lock = threading.Lock()
_ft_seen: set[str] = set()

ETFS = {"SPY", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"}

FILED_FROM = pd.Timestamp("2008-01-01")
FILED_TO = pd.Timestamp("2026-08-31")

UA = "Casy Limited kaho.career@gmail.com"
HEADERS = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
RATE = 8.0          # req/s 全域上限(證監會容許 10)
MAX_RETRIES = 3     # 重試上限寫死
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
            r = _session().get(url, timeout=120)
            r.raise_for_status()
            return r
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"{url}: {last}")


def load_cik_map() -> tuple[dict[str, str], dict[str, str]]:
    """讀倉內共用對照表。兩種形狀都認:證監會上游的 {"0": {...}} 與倉內的 {TICKER: CIK}。"""
    data = json.loads(TICKERS_JSON.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    titles: dict[str, str] = {}
    for key, row in data.items():
        if isinstance(row, dict):
            t = row["ticker"].upper()
            cik = str(row["cik_str"]).zfill(10)
            title = row.get("title", "")
        else:
            t = str(key).upper()
            cik = str(row).zfill(10)
            title = ""
        if t in out:
            continue
        out[t] = cik
        titles[t] = title
    return out, titles


def load_ft_seen() -> None:
    """開場把共用庫 manifest 讀入記憶,之後每次抓之前先查。"""
    if not FT_MANIFEST.exists():
        return
    with FT_MANIFEST.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                _ft_seen.add(json.loads(line)["accession"])
            except Exception:  # noqa: BLE001
                continue


def fulltext_path(ticker: str, acc: str) -> Path:
    return FULLTEXT / f"{ticker}_{acc}.txt.gz"


def get_fulltext(ticker: str, cik: str, acc: str, doc: str,
                 fdate: str, rdate: str) -> tuple[str, str, bool]:
    """回傳 (全文純文本, url, 是否命中共用庫)。命中就不打 EDGAR。"""
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
    p = fulltext_path(ticker, acc)
    if acc in _ft_seen and p.exists():
        return gzip.decompress(p.read_bytes()).decode("utf-8", "replace"), url, True

    text = clean_html(get(url).content)
    blob = text.encode("utf-8")
    p.write_bytes(gzip.compress(blob))
    rec = {"ticker": ticker, "cik": cik, "accession": acc, "form": "10-K",
           "filingDate": fdate, "reportDate": rdate, "url": url,
           "chars": len(text), "sha256": hashlib.sha256(blob).hexdigest(),
           "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "fetchedBy": "KARST-153"}
    with _ft_lock:
        with FT_MANIFEST.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        _ft_seen.add(acc)
    return text, url, False


def filings_10k(cik: str) -> list[tuple[str, str, str, str]]:
    """[(filingDate, reportDate, accession_nodash, primaryDoc)] for form 10-K only."""
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


# ---------------- 切節(CRITERIA.md 第 3 節,凍結) ----------------
APOS = r"[\'\u2018\u2019\u02bc`]?"
MDNA_START = re.compile(
    rf"item\s*7\s*[.\-:\u2013\u2014]?\s*management{APOS}s\s+discussion", re.I)
MDNA_END = re.compile(
    r"item\s*7a\s*[.\-:\u2013\u2014]?\s*quantitative\s+and\s+qualitative", re.I)
MDNA_MIN = 15000

RISK_START = re.compile(r"item\s*1a\s*[.\-:\u2013\u2014]?\s*risk\s*factors", re.I)
RISK_END_A = re.compile(r"item\s*1b\s*[.\-:\u2013\u2014]?\s*unresolved", re.I)
RISK_END_B = re.compile(r"item\s*2\s*[.\-:\u2013\u2014]?\s*propert", re.I)
RISK_MIN = 5000


def _cut(text: str, start_re, end_res, min_span: int) -> tuple[str, str]:
    """夠長(>= min_span)之中最短的一段。切唔到就當缺失,不做全文 fallback。"""
    starts = [m.start() for m in start_re.finditer(text)]
    if not starts:
        return "", "NO-START-MARKER"
    for end_re in end_res:
        ends = [m.start() for m in end_re.finditer(text)]
        if not ends:
            continue
        spans = []
        for s in starts:
            e = [x for x in ends if x > s + min_span]
            if e:
                spans.append((s, e[0]))
        if spans:
            s, e = min(spans, key=lambda sp: sp[1] - sp[0])
            return text[s:e], f"ok (min-span of {len(spans)} cands)"
    return "", "NO-VALID-SPAN"


def extract_mdna(text: str) -> tuple[str, str]:
    return _cut(text, MDNA_START, (MDNA_END,), MDNA_MIN)


def extract_risk(text: str) -> tuple[str, str]:
    return _cut(text, RISK_START, (RISK_END_A, RISK_END_B), RISK_MIN)


_WS = re.compile(r"[ \t\r\n\u00a0]+")


def clean_html(raw: bytes) -> str:
    doc = LH.fromstring(raw)
    for bad in doc.xpath("//script|//style"):
        bad.getparent().remove(bad)
    return _WS.sub(" ", " ".join(doc.itertext()))


def do_job(job) -> tuple[str, dict]:
    ticker, cik, fdate, rdate, acc, doc = job
    key = f"{ticker}|{acc}"
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
    rec = {"ticker": ticker, "cik": cik, "filingDate": fdate,
           "reportDate": rdate, "acc": acc, "url": url}
    try:
        text, url, cached = get_fulltext(ticker, cik, acc, doc, fdate, rdate)
    except Exception as exc:  # noqa: BLE001
        rec.update(ok=False, why=f"fetch/parse: {exc}"[:180])
        return key, rec
    rec["doc_chars"] = len(text)
    rec["fulltext_cached"] = cached
    got = 0
    for name, fn in (("mdna", extract_mdna), ("risk", extract_risk)):
        body, how = fn(text)
        rec[f"{name}_how"] = how
        rec[f"{name}_chars"] = len(body)
        if body:
            (SEC_DIR / f"{ticker}_{acc}_{name}.txt.gz").write_bytes(
                gzip.compress(body.encode("utf-8")))
            got += 1
    rec["ok"] = got > 0
    if got == 0:
        rec["why"] = "both sections failed"
    return key, rec


def main() -> int:
    df = pd.read_parquet(PARQUET)
    tickers = sorted(c for c in df.columns if c not in ETFS)
    print(f"universe {len(tickers)} tickers", flush=True)
    cikmap, titles = load_cik_map()
    load_ft_seen()
    print(f"shared 10-K full-text cache: {len(_ft_seen)} filings already stored", flush=True)

    manifest_path = OUT / "filing_manifest.json"
    manifest: dict[str, dict] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # ---- 第一步:每家公司的 10-K 清單 ----
    filings: dict[str, list] = {}
    missing: dict[str, str] = {}

    def idx_job(t: str):
        cik = cikmap.get(t)
        if not cik:
            return t, None, "no CIK in SEC company_tickers.json"
        try:
            return t, filings_10k(cik), None
        except Exception as exc:  # noqa: BLE001
            return t, None, f"submissions: {exc}"[:180]

    with ThreadPoolExecutor(WORKERS) as ex:
        for n, fut in enumerate(as_completed([ex.submit(idx_job, t) for t in tickers]), 1):
            t, rows, err = fut.result()
            if err or rows is None:
                missing[t] = err or "no filings"
            elif not rows:
                missing[t] = f"CIK {cikmap.get(t)} has no 10-K filings ({titles.get(t,'')})"
            else:
                filings[t] = rows
            if n % 100 == 0:
                print(f"  indexes {n}/{len(tickers)}", flush=True)
    print(f"indexes done: {len(filings)} with 10-Ks, {len(missing)} missing", flush=True)

    # ---- 第二步:抓文切節 ----
    jobs = []
    for t, rows in filings.items():
        cik = cikmap[t]
        for fdate, rdate, acc, doc in rows:
            fd = pd.Timestamp(fdate)
            if fd < FILED_FROM or fd > FILED_TO:
                continue
            key = f"{t}|{acc}"
            # 切節做完**而且**全文已入共用庫,才算真正完成;否則再跑一轉補上全文。
            if (key in manifest and manifest[key].get("ok")
                    and acc in _ft_seen and fulltext_path(t, acc).exists()):
                continue
            jobs.append((t, cik, fdate, rdate, acc, doc))

    print(f"documents to fetch: {len(jobs)}", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = [ex.submit(do_job, j) for j in jobs]
        for n, fut in enumerate(as_completed(futs), 1):
            try:
                key, rec = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"  !! job crashed: {exc}", flush=True)
                continue
            manifest[key] = rec
            if n % 100 == 0:
                manifest_path.write_text(
                    json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
                rate = n / (time.time() - t0)
                print(f"  docs {n}/{len(jobs)} ({rate:.1f}/s, eta "
                      f"{(len(jobs)-n)/max(rate,0.01)/60:.0f} min)", flush=True)

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (OUT / "missing_tickers.json").write_text(
        json.dumps(missing, ensure_ascii=False, indent=1), encoding="utf-8")

    ok = sum(1 for v in manifest.values() if v.get("ok"))
    cov = sorted({v["ticker"] for v in manifest.values() if v.get("ok")})
    print(f"shared full-text cache now holds {len(_ft_seen)} filings", flush=True)
    print(f"filings with >=1 section: {ok}/{len(manifest)}; tickers covered {len(cov)}/{len(tickers)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
