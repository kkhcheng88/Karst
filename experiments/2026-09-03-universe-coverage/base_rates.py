# -*- coding: utf-8 -*-
"""KARST-173:小型股宇宙 v1 的倖存者口徑基礎率(每年十倍率、五年窗內 >50% 回撤率)。

判準見 CRITERIA.md 第八節。零新抓,全部原料唯讀。
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import common as C

YEARS = list(range(2010, 2022))
TOL_DAYS = 10          # Jan 1 前後 5 個交易日,以曆日 10 天近似
FIVE_Y = pd.DateOffset(years=5)


def main() -> None:
    C.OUT.mkdir(exist_ok=True)
    v1 = pd.read_csv(C.UNIVERSE / "universe_smallcap_v1.csv", dtype={"entity_id": str})
    ids = set(v1["entity_id"].str.zfill(10))
    print(f"小型股宇宙 v1:{len(ids)} 個實體")

    px = C.load_prices(entity_ids=ids, since="2009-06-01",
                       cols=("entity_id", "ticker", "date", "adj_close", "series_role"))
    print(f"價格列:{len(px):,},實體:{px['entity_id'].nunique()}")

    p = C.panel()
    p = p[p["entity_id"].isin(ids) & p["shares_outstanding"].notna()]
    first_shares = p.groupby("entity_id")["filed_date"].min()
    print(f"面板有股數的實體:{len(first_shares)}")

    rows = []
    for (eid, tk), s in px.groupby(["entity_id", "ticker"], sort=False):
        s = s.sort_values("date")
        d = s["date"].to_numpy()
        a = s["adj_close"].to_numpy(dtype=float)
        role = s["series_role"].iloc[0]
        n = len(d)
        fs = first_shares.get(eid)
        for y in YEARS:
            t0 = pd.Timestamp(f"{y}-01-01")
            i = int(np.searchsorted(d, np.datetime64(t0), side="left"))
            if i >= n or (pd.Timestamp(d[i]) - t0).days > TOL_DAYS:
                continue
            if not np.isfinite(a[i]) or a[i] <= 0:
                continue
            end = t0 + FIVE_Y
            j = int(np.searchsorted(d, np.datetime64(end), side="right"))
            if j - i < 2:
                continue
            w = a[i + 1:j]
            w = w[np.isfinite(w)]
            if not len(w):
                continue
            rows.append(dict(
                entity_id=eid, ticker=tk, series_role=role, year=y,
                t0_date=pd.Timestamp(d[i]).date().isoformat(),
                t0_price=float(a[i]),
                mult=float(w.max() / a[i]),
                dd=float(w.min() / a[i] - 1),
                last_date=pd.Timestamp(d[j - 1]).date().isoformat(),
                window_covered_days=int((pd.Timestamp(d[j - 1]) - t0).days),
                has_shares=bool(fs is not None and fs <= t0)))

    cells = pd.DataFrame(rows)
    # 同一實體同一年若有多條代號序列:主序列優先,再取列數最多那條
    cells["_p"] = (cells["series_role"] == "primary").astype(int)
    cells["_len"] = cells["window_covered_days"]
    cells = (cells.sort_values(["entity_id", "year", "_p", "_len"],
                               ascending=[True, True, False, False])
             .drop_duplicates(subset=["entity_id", "year"]).drop(columns=["_p", "_len"]))
    cells["is10x"] = cells["mult"] >= 10.0
    cells["dd50"] = cells["dd"] <= -0.50
    cells["full_window"] = cells["window_covered_days"] >= 1795   # 5 年 − 30 日
    cells.to_parquet(C.OUT / "base_rate_cells.parquet", index=False, compression="zstd")

    qual = cells[cells["has_shares"]]
    by_year = []
    for y, g in qual.groupby("year"):
        by_year.append(dict(
            年份=int(y), 分母=int(len(g)),
            十倍家數=int(g["is10x"].sum()),
            十倍率=round(float(g["is10x"].mean()), 4),
            回撤逾五成家數=int(g["dd50"].sum()),
            回撤逾五成比率=round(float(g["dd50"].mean()), 4),
            窗完整比例=round(float(g["full_window"].mean()), 4)))
    by_year_df = pd.DataFrame(by_year)
    by_year_df.to_csv(C.OUT / "base_rate_by_year.csv", index=False, encoding="utf-8")

    # 不設「有股數」條件的對照(只要有價):看那個條件砍走幾多
    by_year_px = []
    for y, g in cells.groupby("year"):
        by_year_px.append(dict(年份=int(y), 分母=int(len(g)),
                               十倍率=round(float(g["is10x"].mean()), 4),
                               回撤逾五成比率=round(float(g["dd50"].mean()), 4)))
    pd.DataFrame(by_year_px).to_csv(C.OUT / "base_rate_by_year_price_only.csv",
                                    index=False, encoding="utf-8")

    tot = int(by_year_df["分母"].sum())
    summary = {
        "universe": "universe_smallcap_v1(3,117 家)",
        "caliber": "倖存者口徑(D-152/D-157):宇宙全部是今日仍在申報的公司",
        "years": [YEARS[0], YEARS[-1]],
        "cells_total": int(len(cells)),
        "cells_with_shares": tot,
        "entities_touched": int(qual["entity_id"].nunique()),
        "十倍率_全期加權": round(float((by_year_df["十倍家數"].sum() / tot)), 4) if tot else None,
        "回撤逾五成_全期加權": round(
            float(by_year_df["回撤逾五成家數"].sum() / tot), 4) if tot else None,
        "by_year": by_year,
        "窗不完整格數": int((~cells["full_window"]).sum()),
    }
    (C.OUT / "base_rate_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(by_year_df.to_string(index=False))
    print(json.dumps({k: v for k, v in summary.items() if k != "by_year"},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
