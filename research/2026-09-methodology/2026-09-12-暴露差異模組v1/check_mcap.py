# -*- coding: utf-8 -*-
"""KARST-218 市值複核:面板 `mcap_usd` 欄對拆股／多類股公司不可靠,本檔獨立重算。

**缺陷本體(已核)**:`basket_core.PanelFeatures` 用「覆蓋頁股數 × 衝擊起日價」算市值,而該價是
**還原價**(`adj_close`,除息還原),覆蓋頁股數又是**申報日當日**的數。兩者不同步,於是:
  - NVDA:FY2024 10-K 覆蓋頁 25 億股是**拆股前**,而 2024-08-01 的價是**拆股後**,相乘少算十倍(2024-06-10 生效)。
  - JPM:覆蓋頁股數(30–40 億股)冇問題,但用的是除息還原價(2011-08-05 還原價遠低於當日真實收市價),市值少算。
本檔改用價格庫裡的**未還原收市價 `close`** 乘**申報覆蓋頁股數**,逐家重算,並把兩個數並列。

輸出 `out/mcap_check.csv`。本檔只讀價格庫與 `docs/` 申報全文,不寫任何既有目錄。
"""
from __future__ import annotations

import csv
import glob
import os
import re

import pandas as pd

ROOT = "C:/projects/Karst"
HERE = os.path.join(ROOT, "research", "2026-09-methodology", "2026-09-12-暴露差異模組v1")
DOCS = os.path.join(HERE, "docs")

SHOCK = {"E17": "2011-08-05", "E18": "2024-08-01", "E19": "2021-11-24", "E20": "2022-05-17"}
PICKS = {
    "E17": ["JPM", "STT", "CME", "MET"],
    "E18": ["NVDA", "MU", "TXN", "ASML"],
    "E19": ["CCL", "DAL", "MAR", "BKNG"],
    "E20": ["WMT", "TGT", "TJX", "DG"],
}
# 申報覆蓋頁股數(單位:股)。出處 = 該家 10-K／10-Q／20-F 覆蓋頁,括號寫申報日。
SHARES = {
    ("E17", "JPM"): (3973684787, "10-Q 覆蓋頁 2011-04-30(accn 0000950123-11-045948)"),
    ("E17", "STT"): (504038676, "10-Q 覆蓋頁 2011-04-29(accn 0001193125-11-131166)"),
    # CME:覆蓋頁 66,847 千股(2011-02-25)是**拆股前**,而價格庫 2011-08-05 的 `close`=53.88 是**拆股後**
    # 基準(序列無跳空,即已追溯調整);兩者相乘會少算五倍。CME 的 5 拆 1 在衝擊日(2011-08-05)**之後**才發生,
    # 依提示詞硬界線(事後文件不得引用),本票**不自行套用事後的拆股倍數**,故本家市值標 `查不到`。
    ("E17", "CME"): (None, "覆蓋頁 66,847 千股(2011-02-25);價格庫為拆股後基準,事後拆股不得引用 → 查不到"),
    ("E17", "MET"): (986585463, "10-K 覆蓋頁 2011-02-25(accn 0000950123-11-018077)"),
    ("E18", "NVDA"): (2500000000 * 10, "10-K 覆蓋頁 2024-02-16 為 25 億股(拆股前)× 10(2024-06-10 生效的 1 拆 10;10-Q Note 15 載 2024-05-22 宣布)"),
    ("E18", "MU"): (1098000000, "10-K 資產負債表 1,098 百萬股(單位百萬;accn 0000723125-23-000054)"),
    ("E18", "TXN"): (913045963, "10-Q 覆蓋頁 2024-07-16(accn 0000097476-24-000030)"),
    ("E18", "ASML"): (393421721, "20-F 覆蓋頁 FY2023 年底(accn 0000937966-24-000008)"),
    ("E19", "MAR"): (324414150, "10-K 覆蓋頁 2021-02-10 之 Class A(accn 0001628280-21-002433)"),
    # BKNG:覆蓋頁 4,096 萬股(2021-02)對價格庫 2021-11-24 的 `close`=92.92,相乘得 38 億美元,
    # 與同期真實市值相差約廿五倍;序列本身無跳空,故差異不是本票可解釋的拆股,屬價格庫水平問題 → 查不到。
    ("E19", "BKNG"): (None, "覆蓋頁 4,096 萬股(2021-02);與價格庫水平相差約 25 倍 → 查不到"),
    ("E20", "WMT"): (2751779629, "10-K 覆蓋頁 2022-03-16(accn 0000104169-22-000012)"),
    ("E20", "TGT"): (462418075, "10-K 覆蓋頁 2022-03-03(accn 0000027419-22-000007)"),
    ("E20", "TJX"): (1192878394, "10-Q 覆蓋頁 2021-11-19(accn 0000109198-21-000030)"),
    ("E20", "DG"): (228868368, "10-K 覆蓋頁(accn 0001558370-22-003921)"),
}


def main() -> None:
    frames = []
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "prices", "daily", "part_*.parquet"))):
        frames.append(pd.read_parquet(p, columns=["entity_id", "date", "close", "adj_close", "series_role"]))
    px = pd.concat(frames, ignore_index=True)
    px = px[px["series_role"] == "primary"]
    px["date"] = pd.to_datetime(px["date"])

    ent = pd.read_parquet(os.path.join(ROOT, "data", "universe", "entities.parquet"),
                          columns=["entity_id", "primary_ticker"])
    t2e = dict(zip(ent["primary_ticker"], ent["entity_id"]))

    with open(os.path.join(HERE, "out", "basket_members_new.csv"), encoding="utf-8-sig") as f:
        rows = {(r["event_id"], r["ticker"]): r
                for r in csv.DictReader(f) if r["basket_kind"] == "新聞點名"}

    out = []
    for ev, ts in PICKS.items():
        d = pd.Timestamp(SHOCK[ev])
        for t in ts:
            r = rows.get((ev, t))
            if r is None:
                print("跳過(不在籃子)", ev, t)
                continue
            e = r["entity_id"]
            g = px[px["entity_id"] == e].sort_values("date")
            g = g[g["date"] <= d]
            if not len(g):
                print("跳過(無價)", ev, t)
                continue
            close = float(g["close"].iloc[-1])
            adj = float(g["adj_close"].iloc[-1])
            sh = SHARES.get((ev, t), (None, ""))
            mcap = close * sh[0] if sh[0] else None
            rev = float(r["ttm_revenue"]) if r.get("ttm_revenue") else None
            eq = float(r["equity"]) if r.get("equity") else None
            panel = float(r["mcap_usd"]) if r.get("mcap_usd") else None
            out.append(dict(
                event_id=ev, ticker=t, date=g["date"].iloc[-1].date(),
                close=close, adj_close=adj,
                shares=sh[0], shares_source=sh[1],
                mcap_recomputed=mcap,
                ps_recomputed=(mcap / rev) if (mcap and rev) else None,
                pb_recomputed=(mcap / eq) if (mcap and eq) else None,
                mcap_panel=panel,
                ps_panel=float(r["f_ps"]) if r.get("f_ps") else None))
            print(ev, t, "close=%.2f adj=%.2f 重算市值=%s 面板市值=%s" % (
                close, adj, f"{mcap/1e9:.1f}B" if mcap else "查不到",
                f"{panel/1e9:.1f}B" if panel else "查不到"))

    with open(os.path.join(HERE, "out", "mcap_check.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)


if __name__ == "__main__":
    main()
