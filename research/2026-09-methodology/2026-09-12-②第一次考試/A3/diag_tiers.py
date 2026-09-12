# -*- coding: utf-8 -*-
"""診斷:宇宙內事件按「入池可能性」分層,數一數每層還欠多少全文(只讀)。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE.parent / "A" / "edgar_cache"
SPAC = r"(?:acquisition (?:corp|co|company|holdings|inc)|blank check|\bSPAC\b|acquisition holdings)"


def main() -> None:
    ev = pd.read_parquet(CACHE / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    pm = pd.read_parquet(CACHE / "price_metrics.parquet")
    to = pd.read_parquet(CACHE / "turnover60.parquet")[["accessionNumber", "turnover_mean_60d"]]
    df = ev.merge(pm, on="accessionNumber", how="left").merge(to, on="accessionNumber",
                                                              how="left")
    df["sic4"] = df["sic"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(4)
    df["year"] = pd.to_datetime(df["reaction_date"], errors="coerce").dt.year
    inu = ((df["px_status"].fillna("x") == "")
           & (df["turnover_mean_60d"] >= 10_000_000.0)
           & df["listed_lt_12m"].fillna(1).eq(0)
           & (df["sic4"] != "6770")
           & (~df["name"].str.contains(SPAC, regex=True, na=False))
           & (df["has_1_01"].fillna(0) == 0))
    u = df[inu].copy()
    have = {f.split("__")[0] for f in os.listdir(DOCS) if f.endswith("__EX991.txt.gz")}
    u["an"] = u["accessionNumber"].str.replace("-", "", regex=False)
    u["has_text"] = u["an"].isin(have)
    print("宇宙內(暫定):%d;已有全文 %d;欠 %d" % (len(u), u["has_text"].sum(),
                                             (~u["has_text"]).sum()))
    u["pct"] = u.groupby("year")["rel_spy"].rank(pct=True)
    tiers = [
        ("T1 rel_sic2>0 且 rel_spy≥年P75", (u["rel_sic2"] > 0) & (u["pct"] >= 0.75)),
        ("T2 rel_sic2>0 且 rel_spy≥年P50", (u["rel_sic2"] > 0) & (u["pct"] >= 0.50)),
        ("T3 rel_sic2>0 且 rel_spy≥年P25", (u["rel_sic2"] > 0) & (u["pct"] >= 0.25)),
        ("T4 rel_sic2>0", u["rel_sic2"] > 0),
        ("T5 全部宇宙內", pd.Series(True, index=u.index)),
    ]
    prev = pd.Series(False, index=u.index)
    for name, m in tiers:
        cum = m | prev
        print("  %-32s 累計 %6d;其中欠全文 %6d" % (
            name, int(cum.sum()), int((cum & ~u["has_text"]).sum())))
        prev = cum
    print("逐年欠全文:", u[~u["has_text"]].groupby("year").size().to_dict())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
