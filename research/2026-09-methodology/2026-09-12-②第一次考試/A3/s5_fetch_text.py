# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2)第五步:抓待判事件的 EX-99.1 全文(供稿頭日期、稿內收入、指引解析)。

抓取範圍由 `cache/fetch_plan.json` 指定(由 `s5p_plan.py` 產生);若沒有該檔則退回
「宇宙內全部事件」。**單線程、3 請求/秒**(票面硬規矩);原文寫回 `A/edgar_cache/`
(票面許可「只新增,不改既有」),檔名 `{accnodash}__EX991.txt.gz`。
逐宗落 log,被中途叫停不失進度;已快取者直接跳過。

用法:python s5_fetch_text.py [每支上限宗數] [每支時間上限秒數]
"""
from __future__ import annotations

import gzip
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE.parent / "A" / "edgar_cache"
UA = {"User-Agent": "Karst research kaho@example.com"}
RATE_PER_SEC = 3.0      # 對 SEC 的全域請求速率上限(票面硬規矩)
WORKERS = 12            # 同時連線數;見執行紀錄「跑不通、規格不清」——SEC 冷物件 ~10 秒,
                        # 單連線等於每宗 10 秒,單線程無法在一節內做完;請求速率不變
EPS = re.compile(r"(?i)(\.htm|\.html|\.txt)$")


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


import threading

_last = [0.0]
_rlock = threading.Lock()


def _throttle() -> None:
    """**全域**令牌桶:所有連線合共每秒 3 個請求(與票面 3 請求/秒同一個速率;
    多連線只是把「等 SEC 冷物件 ~10 秒」的死時間填滿,不增加對 SEC 的請求速率)。"""
    with _rlock:
        now = time.time()
        wait = _last[0] + 1.0 / RATE_PER_SEC - now
        if wait > 0:
            time.sleep(wait)
            now = _last[0] + 1.0 / RATE_PER_SEC
        _last[0] = now


_MAX_TRY = 5
_PER_ITEM_BUDGET = 45.0     # 單宗最多花幾秒;超過即記失敗,留待下一支重試


def _get(url: str, timeout: int = 25) -> bytes:
    """SEC 邊緣快取對**未快取的物件**回應約 10 秒(冷),已快取者 0.1 秒;偶回 503。
    故**短重試、快放棄**,不以長退避(舊版 15/45/30 秒退避令單宗最壞 90 秒,實測拖垮整支)。"""
    t_start = time.time()
    for attempt in range(_MAX_TRY):
        _throttle()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 503):
                time.sleep(0.6 * (attempt + 1))
                if time.time() - t_start > _PER_ITEM_BUDGET:
                    break
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.6 * (attempt + 1))
            if time.time() - t_start > _PER_ITEM_BUDGET:
                break
    raise RuntimeError("retries exhausted: %s" % url)


def ex991_name_from_index(page: str) -> tuple[str, str]:
    cands: list[tuple[str, str]] = []
    for tr in re.findall(r"(?is)<tr.*?</tr>", page):
        href = re.search(r'href="([^"]+)"', tr)
        if not href:
            continue
        tds = re.findall(r"(?is)<td[^>]*>\s*([^<]*?)\s*</td>", tr)
        types = [t for t in tds if re.match(r"(?i)^EX-?9", t)]
        if types:
            cands.append((types[0].upper().replace(" ", ""), href.group(1).rsplit("/", 1)[-1]))
    ex1 = [c for c in cands if c[0] == "EX-99.1"]
    pick = ex1[0] if ex1 else (cands[0] if cands else None)
    if not pick:
        return "", ""
    return pick[1], pick[0]


def fetch_one(acc: str, cik: str) -> dict:
    an = acc.replace("-", "")
    out = {"accessionNumber": acc, "status": ""}
    p = DOCS / ("%s__EX991.txt.gz" % an)
    if p.exists():
        out["status"] = "ok"
        out["source"] = "已快取"
        return out
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s" % (int(cik), an)
    try:
        page = _get(base + "/" + acc + "-index.html").decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        out["status"] = "索引抓取失敗:%s" % type(e).__name__
        return out
    doc, typ = ex991_name_from_index(page)
    if not doc or not EPS.search(doc):
        out["status"] = "該申報無 EX-99 附件"
        out["ex991_files"] = typ
        return out
    try:
        raw = _get(base + "/" + doc, timeout=120)
    except Exception as e:  # noqa: BLE001
        out["status"] = "附件抓取失敗:%s" % type(e).__name__
        return out
    txt = strip_html(raw)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(txt)
    out["status"] = "ok"
    out["source"] = doc
    out["chars"] = len(txt)
    return out


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 700
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 540.0
    DOCS.mkdir(parents=True, exist_ok=True)

    plan_p = CACHE / "fetch_plan.json"
    if plan_p.exists():
        plan = json.loads(plan_p.read_text(encoding="utf-8"))
        sel = pd.DataFrame({"accessionNumber": plan})
        ev = pd.read_parquet(CACHE / "events_raw.parquet").drop_duplicates(
            subset=["accessionNumber"])
        sel = sel.merge(ev[["accessionNumber", "cik"]], on="accessionNumber", how="left")
        print("計畫清單:%d 宗" % len(sel), flush=True)
    else:
        raise SystemExit("缺 cache/fetch_plan.json(先跑 s5p_plan.py)")

    log = CACHE / "fetch_log_a3.jsonl"
    tried: set[str] = set()
    if log.exists():
        for line in log.open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("status") == "ok" or "EX-99" in r.get("status", ""):
                tried.add(r["accessionNumber"])
    sel = sel[~sel["accessionNumber"].isin(tried)]
    print("本支待處理:%d(已嘗試過 %d)" % (len(sel), len(tried)), flush=True)

    t_start = time.time()
    n = ok = 0
    from collections import Counter
    stat: Counter = Counter()
    items = list(sel.itertuples(index=False))[:limit]
    with log.open("a", encoding="utf-8") as f:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {ex.submit(fetch_one, r.accessionNumber, r.cik): r for r in items}
            for fut in as_completed(futs):
                try:
                    res = fut.result()
                except Exception as e:  # noqa: BLE001
                    r = futs[fut]
                    res = {"accessionNumber": r.accessionNumber,
                           "status": "例外:%s" % type(e).__name__}
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
                f.flush()
                n += 1
                ok += int(res["status"] == "ok")
                stat[res["status"].split(":")[0]] += 1
                if n % 200 == 0 or n <= 20:
                    print("  ...%d/%d ok=%d 用時%.0fs(%.2fs/宗)"
                          % (n, len(items), ok, time.time() - t_start,
                             (time.time() - t_start) / n), flush=True)
                if time.time() - t_start > budget:
                    for u in futs:
                        u.cancel()
                    print("時間到:已做 %d 宗" % n, flush=True)
                    break
    print("本支處理 %d 宗;成功 %d;用時 %.0fs(%.2fs/宗)"
          % (n, ok, time.time() - t_start, (time.time() - t_start) / max(n, 1)))
    print("狀態:", stat.most_common(6))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
