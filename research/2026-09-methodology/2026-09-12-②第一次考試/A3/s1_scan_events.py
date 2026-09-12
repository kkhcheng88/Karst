# -*- coding: utf-8 -*-
"""KARST-226 票 A″(執行口徑 v1.2)第一步:掃本地 SEC submissions,取 8-K Item 2.02 事件。

與 `A/s1_scan_events.py` 之別**只有一項**:申報窗口起點由 2015-01-01 提前到 **2014-01-01**
(執行口徑 v1.2 第 1 項:2014 的事件只作反應門檻的暖身窗口,不入池,故 `in_pool_window`
欄記 False)。

只讀 `data/sec/submissions/`;輸出 `A3/cache/events_raw.parquet`。

口徑:
  - form == "8-K",items 逐項拆開後含 "2.02"
  - T0 = acceptanceDateTime(UTC,ISO);另存 ET 時間與是否在 16:00 後
  - 8-K/A 另計,不入母體
  - `in_pool_window` = filingDate ≥ 2015-01-01(2014 只供窗口)

**已知限制(照 A 的紀錄)**:本地 submissions 的 `recent` 塊只覆蓋每家公司最近約 1000 宗
申報,較早年份住在 data.sec.gov 分片檔而本地無快取,故早期高頻申報公司會漏。
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
SUB = ROOT / "data" / "sec" / "submissions"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
ET = ZoneInfo("America/New_York")

WIN_START, WIN_END = "2014-01-01", "2025-06-30"
POOL_START = "2015-01-01"

COLS = ["cik", "name", "sic", "entityType", "category",
        "form", "filingDate", "acceptanceDateTime",
        "t0_et", "t0_after16", "t0_weekend", "reportDate",
        "items", "has_1_01", "accessionNumber", "primaryDocument",
        "primaryDocDescription"]


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    n_files = n_bad = 0
    n_8ka = 0
    for fp in sorted(SUB.glob("CIK*.json")):
        n_files += 1
        try:
            with open(fp, encoding="utf-8") as f:
                d = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            n_bad += 1
            continue
        r = d.get("filings", {}).get("recent", {})
        forms = r.get("form", [])
        dates = r.get("filingDate", [])
        items_l = r.get("items", [])
        accs = r.get("acceptanceDateTime", [])
        rep = r.get("reportDate", [])
        an = r.get("accessionNumber", [])
        pdocs = r.get("primaryDocument", [])
        pdesc = r.get("primaryDocDescription", [])
        cik = d.get("cik", "")
        for i in range(len(forms)):
            fd = dates[i] if i < len(dates) else ""
            if not (WIN_START <= fd <= WIN_END):
                continue
            form = forms[i]
            if form not in ("8-K", "8-K/A"):
                continue
            it = items_l[i] if i < len(items_l) else ""
            toks = [x.strip() for x in it.split(",")] if it else []
            if "2.02" not in toks:
                continue
            if form == "8-K/A":
                n_8ka += 1
                continue
            acc_dt = accs[i] if i < len(accs) else ""
            et_str, after16, non_trading = "", "", ""
            if acc_dt:
                try:
                    t = dt.datetime.fromisoformat(acc_dt.replace("Z", "+00:00")).astimezone(ET)
                    et_str = t.strftime("%Y-%m-%dT%H:%M:%S")
                    after16 = int(t.hour > 16 or (t.hour == 16 and (t.minute > 0 or t.second > 0)))
                    non_trading = int(t.weekday() >= 5)
                except ValueError:
                    pass
            rows.append(dict(
                cik=cik, name=d.get("name", ""), sic=str(d.get("sic", "") or ""),
                entityType=d.get("entityType", ""), category=d.get("category", ""),
                form=form, filingDate=fd, acceptanceDateTime=acc_dt,
                t0_et=et_str, t0_after16=after16, t0_weekend=non_trading,
                reportDate=rep[i] if i < len(rep) else "",
                items=it, has_1_01=int("1.01" in toks),
                accessionNumber=an[i] if i < len(an) else "",
                primaryDocument=pdocs[i] if i < len(pdocs) else "",
                primaryDocDescription=pdesc[i] if i < len(pdesc) else "",
            ))
        if n_files % 2000 == 0:
            print("  ...掃過 %d 個快取檔,%d 宗事件" % (n_files, len(rows)), flush=True)

    df = pd.DataFrame(rows, columns=COLS)
    df["in_pool_window"] = (df["filingDate"] >= POOL_START).astype(int)
    df.to_parquet(CACHE / "events_raw.parquet", index=False)
    print("submissions 快取檔:%d(壞檔 %d)" % (n_files, n_bad))
    print("8-K Item 2.02 事件(dedup 前):%d;8-K/A 同項另有 %d 宗,不入母體" % (len(df), n_8ka))
    print("逐年:", df.groupby(df["filingDate"].str[:4]).size().to_dict())
    print("2015 起(入池窗口):%d;2014(只供窗口):%d" % (
        int(df["in_pool_window"].sum()), int((df["in_pool_window"] == 0).sum())))
    print("有 acceptanceDateTime 者:%d;缺者:%d" % (
        (df["acceptanceDateTime"] != "").sum(), (df["acceptanceDateTime"] == "").sum()))
    print("→", CACHE / "events_raw.parquet")


if __name__ == "__main__":
    main()
