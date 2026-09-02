# -*- coding: utf-8 -*-
"""KARST-148 preparation step (b): one more hour on the 126 unresolved tickers.

D-125 decision 3 / CRITERIA sec.11.2. KARST-146 already tried the current ticker
map and a full-text search restricted to 10-K/10-Q cover pages. The new angle
here is simply a wider net: drop the form filter, so 8-K press releases and proxy
statements -- which printed the trading symbol long before the 2019 cover-page
rule -- can identify the filer too.

The acceptance gate stays exactly as strict as KARST-146's (>= 3 hits, >= 60%
share, and the candidate CIK's own filing window must cover the membership
window). Guessing a ticker wrong means back-testing another company's accounts.

Nothing under experiments/2026-09-02-fundamentals-panel/ is written to.
Hard wall clock: 60 minutes.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys
import time
import urllib.parse

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
PANEL_DIR = REPO / "experiments" / "2026-09-02-fundamentals-panel"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

sys.path.insert(0, str(PANEL_DIR))
from sec_client import get  # noqa: E402
from resolve_cik_extra import filing_window, submissions  # noqa: E402

MIN_HITS = 3
MIN_SHARE = 0.60
TIME_BUDGET_SEC = 60 * 60


def fts_ciks(ticker: str, start: str, end: str) -> list[str]:
    """Full-text search, no form filter (the widened net)."""
    q = urllib.parse.urlencode({"q": f'"{ticker}"', "dateRange": "custom",
                                "startdt": start, "enddt": end})
    raw, _ = get(f"https://efts.sec.gov/LATEST/search-index?{q}")
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
    uni = pd.read_csv(PANEL_DIR / "out" / "universe_cik.csv", dtype=str).fillna("")
    ly = pd.to_numeric(uni.left_on.str.slice(0, 4), errors="coerce")
    todo = uni[(uni.cik == "") & (uni.left_on != "") & (ly >= 2010)].copy()
    print(f"still-missing XBRL-era tickers: {len(todo)}", flush=True)

    t0 = time.monotonic()
    accepted, rejected, skipped = [], [], []
    for i, (_, r) in enumerate(todo.iterrows(), 1):
        if time.monotonic() - t0 > TIME_BUDGET_SEC:
            skipped = todo.iloc[i - 1:][["ticker", "joined_on", "left_on"]].to_dict("records")
            print(f"time budget reached at {i - 1}/{len(todo)}", flush=True)
            break
        t, jo, lo = r.ticker, r.joined_on, r.left_on
        start = max(jo, "2001-01-01")
        if start >= lo:
            rejected.append(dict(ticker=t, joined_on=jo, left_on=lo,
                                 reason="成分期完全早於全文檢索的 2001 年起始點"))
            continue
        ciks = fts_ciks(t, start, lo)
        if not ciks:
            rejected.append(dict(ticker=t, joined_on=jo, left_on=lo,
                                 reason="放寬到全部表格後,成分期內仍無任何申報印有此代號"))
            continue
        cnt = collections.Counter(ciks)
        top, n = cnt.most_common(1)[0]
        share = n / len(ciks)
        if n < MIN_HITS or share < MIN_SHARE:
            runner = cnt.most_common(2)[1] if len(cnt) > 1 else ("", 0)
            rejected.append(dict(ticker=t, joined_on=jo, left_on=lo,
                                 reason=f"檢索結果分散,最高票 {top} 只佔 {n}/{len(ciks)} "
                                        f"({share:.0%}),次高 {runner[0]} {runner[1]} 票"))
            continue
        sub, err = submissions(top)
        if sub is None:
            rejected.append(dict(ticker=t, joined_on=jo, left_on=lo,
                                 reason=f"候選 {top} 的申報索引取不到({err})"))
            continue
        first, last = filing_window(sub)
        name = sub.get("name", "")
        if not (first and first <= lo and (not last or last >= jo)):
            rejected.append(dict(ticker=t, joined_on=jo, left_on=lo,
                                 reason=f"候選 {top}({name})申報期 {first}~{last} 不覆蓋成分期"))
            continue
        accepted.append(dict(ticker=t, cik=top, name=name, joined_on=jo, left_on=lo,
                             evidence=f"放寬表格全文檢索:成分期 {jo}~{lo} 內 {n}/{len(ciks)} "
                                      f"份申報印有代號 {t},全屬 {top}({name});"
                                      f"該 CIK 申報期 {first}~{last} 覆蓋成分期"))
        if i % 20 == 0:
            print(f"  {i}/{len(todo)} ... accepted {len(accepted)} "
                  f"({time.monotonic() - t0:.0f}s)", flush=True)

    pd.DataFrame(accepted).to_csv(OUT / "prep_cik_recovered.csv", index=False, encoding="utf-8")
    still = pd.DataFrame(rejected + skipped)
    still.to_csv(OUT / "prep_cik_still_missing.csv", index=False, encoding="utf-8")
    meta = {
        "attempted": int(len(todo)),
        "recovered": int(len(accepted)),
        "still_missing": int(len(still)),
        "skipped_for_time": int(len(skipped)),
        "elapsed_sec": round(time.monotonic() - t0, 1),
        "gate": {"min_hits": MIN_HITS, "min_share": MIN_SHARE,
                 "filing_window_must_cover_membership": True},
        "note": ("補到的公司一樣沒有價格,入不了回測宇宙,只作記錄;"
                 "KARST-146 的 out/ 一個檔都沒有改。"),
    }
    (OUT / "prep_cik.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
