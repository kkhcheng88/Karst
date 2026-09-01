# -*- coding: utf-8 -*-
"""Why are tickers CIK-less, and does it actually cost us any XBRL data?

XBRL companyfacts only exist for filings from roughly 2009 (large accelerated
filers) through 2011 (everyone else). A member that left the index before then
has no machine-readable accounts at the SEC whatever its CIK is, so an
unresolved CIK for such a name costs nothing.
"""
import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
uni = pd.read_csv(HERE / "out" / "universe_cik.csv", dtype=str).fillna("")
uni["left_year"] = uni.left_on.str.slice(0, 4)
uni["resolved"] = uni.cik != ""

miss = uni[~uni.resolved]
print(f"total {len(uni)} | resolved {uni.resolved.sum()} | missing {len(miss)}")
print("\nmissing, by the year they left the index:")
bins = pd.cut(pd.to_numeric(miss.left_year, errors="coerce"),
              [1990, 2000, 2005, 2009, 2012, 2015, 2020, 2030],
              labels=["<=2000", "2001-05", "2006-09", "2010-12",
                      "2013-15", "2016-20", "2021+"])
print(bins.value_counts().sort_index().to_string())

print("\nXBRL-era relevance (left the index in 2010 or later):")
m_x = miss[pd.to_numeric(miss.left_year, errors="coerce") >= 2010]
print(f"  missing CIK AND left 2010+ : {len(m_x)}  <- the real recoverable gap")
print(f"  missing CIK, left pre-2010 : {len(miss) - len(m_x)}  <- no XBRL exists anyway")
m_x[["ticker", "joined_on", "left_on"]].to_csv(
    HERE / "out" / "cik_missing_xbrl_era.csv", index=False, encoding="utf-8")
print("\nthose names:")
print(", ".join(sorted(m_x.ticker)))

res = uni[uni.resolved]
print("\nresolved set:")
print(f"  still in index : {(res.left_on == '').sum()}")
print(f"  left the index : {(res.left_on != '').sum()}")
print(f"  of which left 2010+ : "
      f"{(pd.to_numeric(res.left_year, errors='coerce') >= 2010).sum()}")
