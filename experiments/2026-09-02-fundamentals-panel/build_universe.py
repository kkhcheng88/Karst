# -*- coding: utf-8 -*-
"""KARST-146 step 1: build the download universe (S&P 500 historical members)
and resolve every ticker to a SEC CIK.

Sources, in resolution priority order:
  1. karst/data/universes/sp500_ticker_anchors.csv  - hand-verified ticker->CIK
     anchors with validity windows (KARST-083). Highest trust.
  2. data/sec/company_tickers.json                  - SEC's CURRENT ticker->CIK
     map. Only valid for still-listed names; a recycled ticker points at
     whoever holds it today, so it is used ONLY when the anchor file is silent
     AND the member never left the index (left_on is blank).
  3. data/sec/cik-lookup-data.txt                   - SEC's full company-name ->
     CIK dump. Matched on the historical display_name. Lower trust: used only
     when 1 and 2 fail, and only on an exact normalised name match.

Anything still unresolved is written out by name so a human can see it.

Run:  PYTHONUTF8=1 python build_universe.py
"""
from __future__ import annotations

import json
import pathlib
import re

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

HIST = REPO / "karst" / "data" / "universes" / "sp500_historical.csv"
ANCHORS = REPO / "karst" / "data" / "universes" / "sp500_ticker_anchors.csv"
CT_JSON = REPO / "data" / "sec" / "company_tickers.json"
CIK_LOOKUP = REPO / "data" / "sec" / "cik-lookup-data.txt"


def norm_name(s: str) -> str:
    """Normalise a company name for matching against the SEC name dump."""
    if not isinstance(s, str):
        return ""
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(
        r"\b(INC|INCORPORATED|CORP|CORPORATION|CO|COMPANY|LTD|LIMITED|PLC|LP|"
        r"LLC|HOLDINGS|HOLDING|GROUP|THE|CLASS|A|B|C)\b",
        " ",
        s,
    )
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    hist = pd.read_csv(HIST, dtype=str).fillna("")
    # One row per ticker: earliest join, latest leave (blank leave = still in).
    grp = hist.groupby("ticker", as_index=False).agg(
        display_name=("display_name", lambda s: next((x for x in s if x), "")),
        joined_on=("joined_on", "min"),
        left_on=("left_on", lambda s: "" if any(x == "" for x in s) else max(s)),
    )

    anchors = pd.read_csv(ANCHORS, dtype=str).fillna("")
    # If a ticker has several anchor windows, keep the one covering the latest
    # membership period; ties broken by the longest window.
    anchors = anchors.sort_values(["ticker", "valid_from"])
    anchor_map: dict[str, list[dict]] = {}
    for _, r in anchors.iterrows():
        anchor_map.setdefault(r["ticker"], []).append(r.to_dict())

    ct = json.loads(CT_JSON.read_text(encoding="utf-8"))
    # company_tickers.json ships either as {"0": {...}} or as {TICKER: CIK}.
    cur_map: dict[str, str] = {}
    if isinstance(ct, dict):
        vals = list(ct.values())
        if vals and isinstance(vals[0], dict):
            for v in vals:
                cur_map[str(v["ticker"]).upper()] = str(v["cik_str"]).zfill(10)
        else:
            for k, v in ct.items():
                cur_map[str(k).upper()] = str(v).zfill(10)

    # SEC full name dump: "NAME:CIK:" one per line, many names per CIK.
    name_map: dict[str, set[str]] = {}
    with CIK_LOOKUP.open("r", encoding="latin-1") as fh:
        for line in fh:
            parts = line.strip().split(":")
            if len(parts) < 2 or not parts[1]:
                continue
            nm = norm_name(parts[0])
            if nm:
                name_map.setdefault(nm, set()).add(parts[1].zfill(10))

    rows = []
    for _, r in grp.iterrows():
        t, nm, jo, lo = r.ticker, r.display_name, r.joined_on, r.left_on
        cik, src, note = "", "", ""
        cands = anchor_map.get(t, [])
        if cands:
            # Prefer an anchor whose window overlaps this member's period.
            pick = None
            for c in cands:
                if c.get("cik"):
                    vf, vt = c.get("valid_from", ""), c.get("valid_to", "")
                    if (not lo or not vf or vf <= lo) and (not vt or not jo or vt >= jo):
                        pick = c
                        break
            if pick is None:
                pick = next((c for c in cands if c.get("cik")), None)
            if pick:
                cik, src = str(pick["cik"]).zfill(10), "anchors"
                note = pick.get("verdict", "")
        if not cik and not lo and t in cur_map:
            cik, src = cur_map[t], "sec_current_ticker_map"
            note = "still an index member, SEC current map is safe"
        if not cik and nm:
            hits = name_map.get(norm_name(nm), set())
            if len(hits) == 1:
                cik, src = next(iter(hits)), "sec_name_dump_exact"
                note = f"matched on display_name '{nm}'"
            elif len(hits) > 1:
                note = f"name '{nm}' matched {len(hits)} CIKs - ambiguous, skipped"
            else:
                note = f"name '{nm}' not found in SEC name dump"
        if not cik and not nm:
            note = "no display_name recorded; ticker not in anchors nor current map"
        rows.append(dict(ticker=t, display_name=nm, joined_on=jo, left_on=lo,
                         delisted_or_removed=bool(lo), cik=cik,
                         cik_source=src, cik_note=note))

    uni = pd.DataFrame(rows).sort_values("ticker")
    uni.to_csv(OUT / "universe_cik.csv", index=False, encoding="utf-8")
    miss = uni[uni.cik == ""]
    miss.to_csv(OUT / "cik_missing.csv", index=False, encoding="utf-8")

    print(f"universe tickers          : {len(uni)}")
    print(f"still in index            : {(~uni.delisted_or_removed).sum()}")
    print(f"removed / delisted        : {uni.delisted_or_removed.sum()}")
    print(f"CIK resolved              : {(uni.cik != '').sum()}")
    print(f"CIK unresolved            : {len(miss)}")
    print("\nby source:")
    print(uni[uni.cik != ""].cik_source.value_counts().to_string())
    print(f"\nunique CIKs               : {uni[uni.cik != ''].cik.nunique()}")


if __name__ == "__main__":
    main()
