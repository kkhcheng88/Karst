# -*- coding: utf-8 -*-
"""KARST-220 擴樣本:抓衝擊前申報原文(年報一份、季報最近兩份),落 `擴樣本/docs/`。

照 KARST-218 `fetch_docs.py` 同一口徑。**工人抓的申報原文不入庫(D-134)**:全文只落
`docs/`,倉內 .gitignore 已擋 `research/2026-09-methodology/*/docs/`。本檔不另存副本。

本地 `data/sec/submissions/CIK*.json` 的 `recent` 只覆蓋近年,2016/2018 兩宗的申報住在
分片檔,故一併抓分片。取不到即記錄失敗原因,不冒充成功。
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
DOCS = HERE / "docs"
PKT = HERE / "packets_oos"
SUB = ROOT / "data" / "sec" / "submissions"
UA = {"User-Agent": "Karst research kaho@example.com"}


def _rows_from(block: dict) -> list[dict]:
    out = []
    for i in range(len(block.get("form", []))):
        out.append(dict(form=block["form"][i], filingDate=block["filingDate"][i],
                        reportDate=block["reportDate"][i],
                        accn=block["accessionNumber"][i], doc=block["primaryDocument"][i]))
    return out


def submissions(cik: str) -> dict:
    p = SUB / f"CIK{cik}.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.loads(r.read())


def all_rows(d: dict, cutoff: str) -> list[dict]:
    f = d.get("filings", {})
    rows = _rows_from(f.get("recent", {}))
    for shard in f.get("files", []):
        url = f"https://data.sec.gov/submissions/{shard['name']}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                rows += _rows_from(json.loads(r.read()))
        except Exception as e:  # noqa: BLE001
            print("  分片抓取失敗", shard["name"], type(e).__name__, flush=True)
    return [x for x in rows if x["filingDate"] < cutoff]


def pick_filings(d: dict, cutoff: str) -> list[tuple[str, dict]]:
    rows = all_rows(d, cutoff)
    out = []
    k = [x for x in rows if x["form"] in ("10-K", "20-F", "40-F")]
    if k:
        out.append(("年報", k[0]))
    for j, x in enumerate([x for x in rows if x["form"] in ("10-Q", "6-K")][:2]):
        out.append((f"季報{j}", x))
    return out


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


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    index = []
    for pf in sorted(PKT.glob("E*.json")):
        pack = json.loads(pf.read_text(encoding="utf-8"))
        ev, cutoff = pack["event_id"], pack["shock_start"]
        for c in pack["companies"]:
            if not c.get("picked"):
                continue
            cik, ticker = c["entity_id"], c["ticker"]
            try:
                d = submissions(cik)
                fl = pick_filings(d, cutoff)
            except Exception as e:  # noqa: BLE001
                print("FAIL-INDEX", ev, ticker, type(e).__name__, str(e)[:70], flush=True)
                index.append(dict(event=ev, ticker=ticker, tag="", form="", filingDate="",
                                  accn="", file="", chars=0,
                                  status="申報索引抓取失敗:" + type(e).__name__))
                continue
            if not fl:
                index.append(dict(event=ev, ticker=ticker, tag="", form="", filingDate="",
                                  accn="", file="", chars=0, status="衝擊起日前找不到年報或季報"))
                print("  --", ev, ticker, "無可用申報", flush=True)
            for tag, f in fl:
                acc = f["accn"].replace("-", "")
                fn = DOCS / f"{ev}_{ticker}_{tag}_{acc}.txt"
                if not fn.exists():
                    url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                           f"{acc}/{f['doc']}")
                    try:
                        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                                    timeout=120) as r:
                            txt = strip_html(r.read())
                    except Exception as e:  # noqa: BLE001
                        print("FAIL-DOC", ev, ticker, tag, type(e).__name__, str(e)[:70], flush=True)
                        index.append(dict(event=ev, ticker=ticker, tag=tag, form=f["form"],
                                          filingDate=f["filingDate"], accn=f["accn"], file="",
                                          chars=0, status="全文抓取失敗:" + type(e).__name__))
                        continue
                    fn.write_text(txt, encoding="utf-8")
                    time.sleep(0.4)
                index.append(dict(event=ev, ticker=ticker, tag=tag, form=f["form"],
                                  filingDate=f["filingDate"], reportDate=f["reportDate"],
                                  accn=f["accn"], file=fn.name, chars=fn.stat().st_size,
                                  status="已落 docs/"))
                print("OK", ev, ticker, tag, f["form"], f["filingDate"], fn.stat().st_size, flush=True)
    (HERE / "out" / "docs_index_oos.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for r in index if r["status"] == "已落 docs/")
    print(f"完成:{ok}/{len(index)} 份落 docs/(不入庫)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
