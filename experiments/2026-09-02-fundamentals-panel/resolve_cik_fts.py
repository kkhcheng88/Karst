# -*- coding: utf-8 -*-
"""KARST-146 step 3: last resolution pass for dead tickers, via EDGAR
full-text search.

202 removed members have a ticker that nobody holds today, so the current
ticker map cannot even offer a candidate. Their own filings can: since the
2019 cover-page rule (and voluntarily before it) a 10-K/10-Q cover page prints
the trading symbol, so full-text searching the symbol inside the membership
window surfaces the filer.

That is a heuristic, so it is gated hard and every acceptance carries its
evidence:
  * search restricted to 10-K/10-Q filed inside the membership window;
  * the dominant CIK must hold >= 60% of hits and at least 3 hits;
  * that CIK's submissions filing window must still cover the membership
    window (same test as resolve_cik_extra.py).
Anything short of all three is rejected and listed. Full-text search only
indexes 2001+, and cover pages routinely omitted the symbol before 2019, so a
low hit rate here is expected and is not evidence the company is missing from
the SEC.

Run:  PYTHONUTF8=1 python resolve_cik_fts.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import urllib.parse

import pandas as pd

from resolve_cik_extra import filing_window, submissions
from sec_client import get

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"

MIN_HITS = 3
MIN_SHARE = 0.60


def fts_ciks(ticker: str, start: str, end: str) -> list[str]:
    q = urllib.parse.urlencode({"q": f'"{ticker}"', "forms": "10-K,10-Q",
                                "dateRange": "custom",
                                "startdt": start, "enddt": end})
    raw, err = get(f"https://efts.sec.gov/LATEST/search-index?{q}")
    if raw is None:
        return []
    try:
        d = json.loads(raw)
    except Exception:  # noqa: BLE001
        return []
    ciks = []
    for h in d.get("hits", {}).get("hits", []):
        for c in h.get("_source", {}).get("ciks", []):
            ciks.append(str(c).zfill(10))
    return ciks


def main() -> None:
    uni = pd.read_csv(OUT / "universe_cik.csv", dtype=str).fillna("")
    ly = pd.to_numeric(uni.left_on.str.slice(0, 4), errors="coerce")
    todo = uni[(uni.cik == "") & (uni.left_on != "") & (ly >= 2010)]
    print(f"full-text search pass over {len(todo)} dead tickers\n")

    accepted, rejected = {}, []
    for i, (_, r) in enumerate(todo.iterrows(), 1):
        t, jo, lo = r.ticker, r.joined_on, r.left_on
        start = max(jo, "2001-01-01")
        ciks = fts_ciks(t, start, lo)
        if not ciks:
            rejected.append(dict(ticker=t, joined_on=jo, left_on=lo,
                                 reason="全文檢索在成分期內找不到印有此代號的 10-K/10-Q"))
            continue
        cnt = collections.Counter(ciks)
        top, n = cnt.most_common(1)[0]
        share = n / len(ciks)
        runner = cnt.most_common(2)[1] if len(cnt) > 1 else ("", 0)
        if n < MIN_HITS or share < MIN_SHARE:
            rejected.append(dict(
                ticker=t, joined_on=jo, left_on=lo,
                reason=f"全文檢索結果分散,最高票 {top} 只佔 {n}/{len(ciks)} "
                       f"({share:.0%}),次高 {runner[0]} {runner[1]} 票——不足以認定"))
            continue
        sub, err = submissions(top)
        if sub is None:
            rejected.append(dict(ticker=t, joined_on=jo, left_on=lo,
                                 reason=f"候選 {top} 的申報索引取不到({err})"))
            continue
        first, last = filing_window(sub)
        name = sub.get("name", "")
        if not (first and first <= lo and (not last or last >= jo)):
            rejected.append(dict(
                ticker=t, joined_on=jo, left_on=lo,
                reason=f"候選 {top}({name})申報期 {first}~{last} 不覆蓋成分期 {jo}~{lo}"))
            continue
        accepted[t] = (top, f"全文檢索:成分期 {jo}~{lo} 內 {n}/{len(ciks)} 份 "
                            f"10-K/10-Q 印有代號 {t},全屬 {top}({name});"
                            f"該 CIK 申報期 {first}~{last} 覆蓋成分期")
        if i % 25 == 0:
            print(f"  {i}/{len(todo)} ... accepted so far {len(accepted)}")

    for t, (cik, ev) in accepted.items():
        m = uni.ticker == t
        uni.loc[m, "cik"] = cik
        uni.loc[m, "cik_source"] = "edgar_full_text_search"
        uni.loc[m, "cik_note"] = ev

    uni.to_csv(OUT / "universe_cik.csv", index=False, encoding="utf-8")
    prev = pd.read_csv(OUT / "cik_rejected.csv", dtype=str).fillna("") \
        if (OUT / "cik_rejected.csv").exists() else pd.DataFrame()
    prev = prev[~prev.ticker.isin(list(accepted) + [r["ticker"] for r in rejected])] \
        if len(prev) else prev
    pd.concat([prev, pd.DataFrame(rejected)], ignore_index=True).to_csv(
        OUT / "cik_rejected.csv", index=False, encoding="utf-8")
    still = uni[uni.cik == ""]
    still.to_csv(OUT / "cik_missing.csv", index=False, encoding="utf-8")
    sly = pd.to_numeric(still.left_on.str.slice(0, 4), errors="coerce")

    print(f"\naccepted      : {len(accepted)}")
    print(f"rejected      : {len(rejected)}")
    print(f"CIK resolved  : {(uni.cik != '').sum()} / {len(uni)}")
    print(f"still missing : {len(still)} (left index 2010+: {(sly >= 2010).sum()})")
    print("\nsource mix:")
    print(uni[uni.cik != ""].cik_source.value_counts().to_string())


if __name__ == "__main__":
    main()
