# -*- coding: utf-8 -*-
"""KARST-192 第(三)步輔助:前二十大贏家的價格路徑摘要(供逐筆人手/子隊核查)。

每個入榜事件出:觸發前 3 個月起至一年後出場日的月末收市價、期內三大單日升幅與其日期、
觸發日與出場日的原始 close / adj_close。**不作判斷**,只把逐筆事實攤出來。

輸出:out/recon_winner_paths_recon.csv(月末路徑)、out/recon_winner_jumps_recon.csv(單日跳動)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
PRICES = ROOT / "data" / "prices" / "daily"


def main() -> None:
    chk = pd.read_csv(OUT / "recon_top_winners_checked_recon.csv", encoding="utf-8-sig",
                      dtype={"entity_id": str},
                      parse_dates=["trigger_date", "entry_date", "exit_date"])
    u = chk.drop_duplicates(subset=["entity_id", "trigger_date"]).copy()
    ids = sorted(set(u["entity_id"]))

    frames = []
    for p in sorted(PRICES.glob("part_*.parquet")):
        t = pq.read_table(p, columns=["entity_id", "ticker", "date", "close",
                                      "adj_close", "volume", "series_role"])
        m = pc.and_(pc.is_in(t["entity_id"], value_set=pa.array(ids)),
                    pc.equal(t["series_role"], "primary"))
        t = t.filter(m)
        if t.num_rows:
            frames.append(t.to_pandas())
    px = pd.concat(frames, ignore_index=True)
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values(["entity_id", "date"], kind="stable").reset_index(drop=True)

    paths, jumps = [], []
    for r in u.itertuples(index=False):
        e = r.entity_id
        t0 = pd.Timestamp(r.trigger_date) - pd.Timedelta(days=95)
        t1 = pd.Timestamp(r.exit_date)
        s = px[(px["entity_id"] == e) & (px["date"] >= t0) & (px["date"] <= t1)].copy()
        if s.empty:
            continue
        s["ym"] = s["date"].dt.to_period("M")
        me = s.groupby("ym").tail(1)
        for q in me.itertuples(index=False):
            paths.append(dict(entity_id=e, ticker=r.primary_ticker,
                              trigger_date=r.trigger_date, 月=str(q.ym),
                              日=q.date.date(), close=q.close, adj_close=q.adj_close,
                              成交股數=q.volume, 該列代號=q.ticker))
        w = s[(s["date"] >= pd.Timestamp(r.entry_date)) & (s["date"] <= t1)].copy()
        w["日變動"] = w["adj_close"].pct_change()
        top = w.nlargest(3, "日變動")
        bot = w.nsmallest(2, "日變動")
        for q in pd.concat([top, bot]).itertuples(index=False):
            jumps.append(dict(entity_id=e, ticker=r.primary_ticker,
                              trigger_date=r.trigger_date, 日=q.date.date(),
                              日變動=q.日變動, close=q.close, adj_close=q.adj_close,
                              成交股數=q.volume))

    pd.DataFrame(paths).to_csv(OUT / "recon_winner_paths_recon.csv", index=False,
                               encoding="utf-8-sig")
    j = pd.DataFrame(jumps).sort_values(["ticker", "日變動"], ascending=[True, False])
    j.to_csv(OUT / "recon_winner_jumps_recon.csv", index=False, encoding="utf-8-sig")
    print(f"路徑列 {len(paths):,},跳動列 {len(j):,}")
    print(j[j["日變動"].abs() >= 0.45].to_string(index=False))


if __name__ == "__main__":
    main()
