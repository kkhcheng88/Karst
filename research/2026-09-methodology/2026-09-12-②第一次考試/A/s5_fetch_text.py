# -*- coding: utf-8 -*-
"""KARST-222 票 A 第五步:抓觸發那份 8-K 的 EX-99.1 全文(判指引上調正則用)。

抓取次序(執行口徑 v1 第二節第 1 點的許可次序,寫入執行紀錄):
  先按價格門檻(當年第 90 百分位,即入口池的門檻,相對 SPY 且相對同業為正)縮到強勢反應
  子集,只對這個子集抓文本;母體其餘列的指引欄標「未評」。第 95/第 80 百分位的數目與
  門檻值只需價格欄,不涉文本(見 s10_export.py 的 thresholds.md)。

每宗最多兩個請求:① EDGAR 申報索引頁 {acc}-index.html ② 該檔全文。
  索引頁解析不到 EX-99.1 才多抓一個 index.json 作退路。
原文落 `A/edgar_cache/`(.gitignore 已擋 `research/2026-09-methodology/*/*/edgar_cache/`),不入庫。

用法:python s5_fetch_text.py <年份|all> [每批上限]
"""
from __future__ import annotations

import gzip
import html
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE / "edgar_cache"
UA = {"User-Agent": "Karst research kaho@example.com"}
N_WORKERS = 4
RATE_PER_SEC = 6.0          # SEC 名義上限 10/秒;實測 9.5/秒 會被 429 封,退到一半
_lock = threading.Lock()
_last = [0.0]


def _throttle() -> None:
    with _lock:
        now = time.time()
        wait = _last[0] + 1.0 / RATE_PER_SEC - now
        if wait > 0:
            time.sleep(wait)
            now = _last[0] + 1.0 / RATE_PER_SEC
        _last[0] = now


def _get(url: str, timeout: int = 60) -> bytes:
    for attempt in range(4):
        _throttle()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 503):
                # SEC 一旦回 429 會封一段時間;短退避無用,要等分鐘級
                time.sleep((30.0, 90.0, 180.0, 240.0)[attempt])
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("retries exhausted: %s" % url)


def strip_html(raw: bytes) -> str:
    t = raw.decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?is)<br\s*/?>", "\n", t)
    t = re.sub(r"(?is)</(p|div|tr|h[1-6]|li)>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t


def fetch_one(row) -> dict:
    acc = row.accessionNumber
    cik = row.cik
    acc_nodash = acc.replace("-", "")
    out = {"accessionNumber": acc, "cik": cik, "status": "", "ex991_files": "",
           "ex991_path": "", "n_docs": 0, "other_items_text": ""}
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s" % (int(cik), acc_nodash)
    names: list[str] = []

    # 已經有全文者不必再問 EDGAR,省一個請求
    done = DOCS / ("%s__EX991.txt.gz" % acc_nodash)
    if done.exists():
        try:
            out["chars"] = len(gzip.open(done, "rt", encoding="utf-8").read())
            out["ex991_path"] = done.name
            out["ex991_files"] = "已快取"
            out["status"] = "ok"
            return out
        except OSError:
            pass

    # 以申報索引頁的 SEC 文件類型欄認 EX-99.1(檔名各式各樣,不可靠)
    doc_type, doc_name = "", ""
    try:
        page = _get(base + "/" + acc + "-index.html", timeout=60).decode("utf-8", "ignore")
        cands = []
        for tr in re.findall(r"(?is)<tr.*?</tr>", page):
            href = re.search(r'href="([^"]+)"', tr)
            if not href:
                continue
            tds = re.findall(r"(?is)<td[^>]*>\s*([^<]*?)\s*</td>", tr)
            types = [t for t in tds if re.match(r"(?i)^EX-?9", t)]
            if types:
                cands.append((types[0].upper(), href.group(1)))
        ex1 = [c for c in cands if c[0].replace(" ", "") == "EX-99.1"]
        pick = ex1[0] if ex1 else (cands[0] if cands else None)
        if pick:
            doc_type, doc_name = pick[0], pick[1].rsplit("/", 1)[-1]
    except Exception:  # noqa: BLE001
        pass

    if not doc_name:                      # 退路:用 index.json 檔名猜
        try:
            idx = json.loads(_get(base + "/index.json"))
            names = [it.get("name") or "" for it in idx.get("directory", {}).get("item", [])]
            out["n_docs"] = len(names)
        except Exception as e:  # noqa: BLE001
            out["status"] = "索引抓取失敗:%s" % type(e).__name__
            return out
        ex = [n for n in names if re.search(r"(?i)(ex|exhibit)[-_]?99", n)]
        if ex:
            ex.sort(key=lambda n: (0 if re.search(r"(?i)99[._-]?1", n)
                                   else 1 if not re.search(r"(?i)99[._-]?[2-9]", n) else 2, n))
            doc_name, doc_type = ex[0], "猜測(索引頁解析失敗)"
    if not doc_name:
        out["status"] = "該申報無 EX-99 附件"
        out["ex991_files"] = "|".join(s for s in names if s.lower().endswith((".htm", ".html", ".txt")))
        return out
    out["ex991_files"] = "%s | %s" % (doc_type, doc_name)

    p = DOCS / ("%s__%s.txt.gz" % (acc_nodash, doc_name))
    try:
        if p.exists():
            txt = gzip.open(p, "rt", encoding="utf-8").read()
        else:
            raw = _get(base + "/" + doc_name, timeout=120)
            txt = strip_html(raw)
            with gzip.open(p, "wt", encoding="utf-8") as f:
                f.write(txt)
    except Exception as e:  # noqa: BLE001
        out["status"] = "附件抓取失敗:%s:%s" % (doc_name, type(e).__name__)
        return out
    path = DOCS / ("%s__EX991.txt.gz" % acc_nodash)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(txt)
    out["ex991_path"] = path.name
    out["status"] = "ok"
    out["chars"] = len(txt)
    return out


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10 ** 9
    DOCS.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(CACHE / "population_base.parquet")
    sel = df[(df["in_universe"] == 1) & (df["pass_p90"] == 1)].copy()
    if arg != "all":
        sel = sel[sel["year"].astype(str) == arg]
    log = CACHE / "fetch_log.jsonl"
    already: set[str] = set()
    if log.exists():
        for line in open(log, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("status") == "ok":
                already.add(r["accessionNumber"])
    sel = sel[~sel["accessionNumber"].isin(already)]
    sel = sel.sort_values("accessionNumber").head(limit)
    print("本年要抓:%d 宗(已抓成功者略過)" % len(sel), flush=True)
    rows = list(sel.itertuples(index=False))
    done = 0
    ok = 0
    from collections import Counter
    stat = Counter()
    # 逐宗落 log(被中途叫停都不失進度)
    with open(log, "a", encoding="utf-8") as f, \
            ThreadPoolExecutor(max_workers=N_WORKERS) as ex:
        for r in ex.map(fetch_one, rows):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            done += 1
            ok += int(r["status"] == "ok")
            stat[r["status"].split(":")[0]] += 1
            if done % 200 == 0:
                print("  ...%d/%d" % (done, len(rows)), flush=True)
    print("成功:%d/%d" % (ok, len(rows)))
    print("狀態:", stat.most_common(6))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
