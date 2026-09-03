# -*- coding: utf-8 -*-
"""KARST-146 step 2: mechanically recover CIKs for removed members that the
KARST-083 anchor file never covered.

The anchor file only covers tickers that had price bars inside the 2015+
snapshot window, so 582 removed members carry no CIK. 361 of them left the
index before 2010 and therefore have no XBRL accounts at the SEC at all -
resolving them would buy nothing. The other 221 are worth a real attempt.

Method (the same evidence test KARST-083 used by hand, run mechanically):
  1. Look the ticker up in the SEC's CURRENT ticker->CIK map. A removed
     member's ticker may still be live because someone else recycled it, so a
     hit is a CANDIDATE, never an answer.
  2. Fetch that CIK's submissions history and read its real filing window.
  3. Accept only if the filing window actually covers the membership window:
        first filing <= membership end   (rules out a later re-listing,
                                          e.g. ADT Inc. 2017 vs ADT Corp. 2012)
    AND last  filing >= membership start (rules out a shell that stopped
                                          filing before the member existed).
  4. Everything else is rejected and listed by name. No guessing from memory.

Run:  PYTHONUTF8=1 python resolve_cik_extra.py
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

from sec_client import get

REPO = pathlib.Path(r"C:\projects\Karst")
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
# KARST-174:由票目錄改指單一快取(D-134)。只改路徑,抓取邏輯不變。
# 注意:本檔寫入時不補寫 manifest.jsonl,重跑並新抓之前要先補登記步驟。
CACHE = REPO / "data" / "sec" / "submissions"
CACHE.mkdir(parents=True, exist_ok=True)

XBRL_ERA_START = 2010   # no companyfacts exist for members gone before this


def load_current_map() -> dict[str, str]:
    ct = json.loads((REPO / "data" / "sec" / "company_tickers.json").read_text(
        encoding="utf-8"))
    out: dict[str, str] = {}
    vals = list(ct.values())
    if vals and isinstance(vals[0], dict):
        for v in vals:
            out[str(v["ticker"]).upper()] = str(v["cik_str"]).zfill(10)
    else:
        for k, v in ct.items():
            out[str(k).upper()] = str(v).zfill(10)
    return out


def submissions(cik: str) -> tuple[dict | None, str]:
    p = CACHE / f"CIK{cik}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")), ""
    raw, err = get(f"https://data.sec.gov/submissions/CIK{cik}.json")
    if raw is None:
        return None, err
    p.write_bytes(raw)
    return json.loads(raw.decode("utf-8")), ""


def filing_window(sub: dict) -> tuple[str, str]:
    """(first filing date, last filing date) across the whole history."""
    dates: list[str] = []
    rec = sub.get("filings", {}).get("recent", {}).get("filingDate", [])
    dates.extend(d for d in rec if d)
    for f in sub.get("filings", {}).get("files", []):
        for k in ("filingFrom", "filingTo"):
            if f.get(k):
                dates.append(f[k])
    if not dates:
        return "", ""
    return min(dates), max(dates)


def main() -> None:
    uni = pd.read_csv(OUT / "universe_cik.csv", dtype=str).fillna("")
    cur = load_current_map()

    left_year = pd.to_numeric(uni.left_on.str.slice(0, 4), errors="coerce")
    todo = uni[(uni.cik == "") & (uni.left_on != "")
               & (left_year >= XBRL_ERA_START)]
    print(f"attempting {len(todo)} XBRL-era removed members without a CIK\n")

    fixed, rejected, failures = {}, [], []
    for i, (_, r) in enumerate(todo.iterrows(), 1):
        t, jo, lo = r.ticker, r.joined_on, r.left_on
        cand = cur.get(t)
        if not cand:
            rejected.append(dict(ticker=t, joined_on=jo, left_on=lo,
                                 candidate_cik="", reason="代號今日已無人持有,證監會現行對照表查無此代號"))
            continue
        sub, err = submissions(cand)
        if sub is None:
            failures.append(dict(ticker=t, candidate_cik=cand, error=err))
            continue
        first, last = filing_window(sub)
        name = sub.get("name", "")
        former = "; ".join(f.get("name", "") for f in sub.get("formerNames", []))
        ok = bool(first) and first <= lo and (not last or last >= jo)
        ev = (f"候選 CIK {cand}({name});申報期 {first}~{last};"
              f"成分期 {jo}~{lo}" + (f";曾用名:{former}" if former else ""))
        if ok:
            fixed[t] = (cand, ev)
        else:
            why = ("首份申報晚於成分期結束,是後來另一家公司接用同一代號"
                   if first and first > lo else "申報期與成分期不重疊")
            rejected.append(dict(ticker=t, joined_on=jo, left_on=lo,
                                 candidate_cik=cand, reason=f"{why}。{ev}"))
        if i % 25 == 0:
            print(f"  {i}/{len(todo)} ... accepted so far {len(fixed)}")

    for t, (cik, ev) in fixed.items():
        m = uni.ticker == t
        uni.loc[m, "cik"] = cik
        uni.loc[m, "cik_source"] = "submissions_window_overlap"
        uni.loc[m, "cik_note"] = ev

    uni.to_csv(OUT / "universe_cik.csv", index=False, encoding="utf-8")
    pd.DataFrame(rejected).to_csv(OUT / "cik_rejected.csv", index=False,
                                  encoding="utf-8")
    pd.DataFrame(failures).to_csv(OUT / "cik_fetch_failures.csv", index=False,
                                  encoding="utf-8")
    still = uni[uni.cik == ""]
    still.to_csv(OUT / "cik_missing.csv", index=False, encoding="utf-8")

    print(f"\naccepted        : {len(fixed)}")
    print(f"rejected        : {len(rejected)}")
    print(f"fetch failures  : {len(failures)}")
    print(f"CIK resolved    : {(uni.cik != '').sum()} / {len(uni)}")
    sly = pd.to_numeric(still.left_on.str.slice(0, 4), errors="coerce")
    print(f"still missing   : {len(still)} "
          f"(of which left index 2010+: {(sly >= 2010).sum()})")


if __name__ == "__main__":
    main()
