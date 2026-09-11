# -*- coding: utf-8 -*-
"""KARST-220 先導篩選:候選敘事衝擊事件的「形狀」檢查(建籃子之前)。

形狀照 KARST-199/218:一個敘事打一個籃子、**籃子相對大市急跌**。
本腳本只算一件事:候選窗內「新聞點名籃子等權 ÷ SPY」由衝擊起日到最低點的跌幅。
跌幅太小(與大市同步跌)即形狀不合,不採用——理由照 218 的做法寫入總覽,不刪。

用法:python screen_candidates.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
B199 = ROOT / "research" / "2026-09-methodology" / "2026-09-10-①行業殺錯事件籃子"
sys.path.insert(0, str(B199))
from basket_core import build_wide, load_prices, load_spy, resolve_tickers  # noqa: E402

CAND = [
    dict(cid="C1", name="2015-08 人民幣貶值殺奢侈品與汽車",
         shock="2015-08-10", end="2015-08-25",
         tickers=["TIF", "COH", "KORS", "RL", "PVH", "F", "GM", "TM", "HMC",
                  "LVS", "WYNN", "MGM", "JWN", "M", "DKS"]),
    dict(cid="C2", name="2016-06 英國脫歐公投殺歐洲銀行",
         shock="2016-06-23", end="2016-06-27",
         tickers=["BCS", "DB", "HSBC", "UBS", "CS", "ING", "LYG", "NWG", "MFG",
                  "JPM", "BAC", "C", "GS", "MS", "WFC"]),
    dict(cid="C3", name="2021-07 中國監管風暴殺中概股",
         shock="2021-07-01", end="2021-07-30",
         tickers=["BABA", "JD", "PDD", "BIDU", "NTES", "TME", "EDU", "TAL", "GOTU",
                  "NIO", "XPEV", "LI", "FUTU", "TIGR", "VIPS", "YUMC"]),
    dict(cid="C4", name="2022-06 加密崩盤殺加密相關股",
         shock="2022-06-10", end="2022-06-30",
         tickers=["COIN", "MSTR", "MARA", "RIOT", "HUT", "BITF", "CLSK", "HIVE",
                  "BTBT", "WULF", "SQ", "HOOD"]),
    dict(cid="C5", name="2018-12 加息路徑恐慌殺房屋建築商",
         shock="2018-11-30", end="2018-12-24",
         tickers=["DHI", "LEN", "PHM", "NVR", "TOL", "KBH", "MDC", "MTH", "GRBK",
                  "BZH", "CCS", "TMHC", "LGIH", "CVCO"]),
    dict(cid="C6", name="2024-12 對華半導體出口管制新規殺設備商",
         shock="2024-11-29", end="2024-12-18",
         tickers=["AMAT", "LRCX", "KLAC", "ASML", "TER", "ONTO", "ACLS", "UCTT",
                  "AEIS", "MKSI", "ENTG", "FORM", "COHU", "NVMI"]),
    dict(cid="C7", name="2019-08 殖利率倒掛殺銀行",
         shock="2019-08-13", end="2019-08-30",
         tickers=["JPM", "BAC", "C", "WFC", "GS", "MS", "USB", "PNC", "TFC", "RF",
                  "KEY", "HBAN", "ZION", "CFG", "FITB", "MTB", "COF", "SCHW", "BK", "STT"]),
    dict(cid="C8", name="2018-10 貿易戰殺半導體與工業(218 已駁,覆核)",
         shock="2018-10-01", end="2018-10-29",
         tickers=["NVDA", "AMD", "AVGO", "MU", "TXN", "INTC", "QCOM", "AMAT", "LRCX",
                  "KLAC", "CAT", "DE", "HON", "GE", "MMM", "EMR", "ETN"]),
    dict(cid="C9", name="2021-01 GameStop 空頭擠壓殺高空頭股",
         shock="2021-01-26", end="2021-02-01",
         tickers=["GME", "AMC", "KOSS", "BB", "NOK", "EXPR", "SPCE", "PLTR", "TLRY"]),
    dict(cid="C10", name="2020-09 疫苗有效率消息殺居家股",
         shock="2020-11-06", end="2020-11-20",
         tickers=["ZM", "PTON", "NFLX", "DOCU", "ROKU", "PELOTON", "ETSY", "W", "CHWY", "CRWD"]),
]


def main() -> None:
    spy_df = load_spy()
    px = load_prices()
    cal, wide, spy = build_wide(px, spy_df)
    cal = pd.DatetimeIndex(cal)
    print(f"日曆 {cal[0].date()} → {cal[-1].date()},{len(cal):,} 交易日", flush=True)
    rows = []
    for c in CAND:
        t0 = pd.Timestamp(c["shock"])
        i0 = int(cal.searchsorted(t0, side="left"))
        if i0 >= len(cal):
            print(c["cid"], "起日超出日曆")
            continue
        t0 = cal[i0]
        i_end = int(min(cal.searchsorted(pd.Timestamp(c["end"]), side="right") - 1, len(cal) - 1))
        hi = int(min(i_end + 21, len(cal) - 1))
        res = resolve_tickers(c["tickers"], t0)
        good = res[res["resolve_status"] == "已解析"]["entity_id"].tolist()
        members = [e for e in good if e in wide.columns and np.isfinite(wide[e].iloc[i0])]
        lost = len(c["tickers"]) - len(members)
        if len(members) < 3:
            print(c["cid"], "可用成員不足", len(members))
            continue
        seg = wide.loc[:, members].iloc[i0:hi + 1]
        rel = seg.div(seg.iloc[0], axis=1).div(spy.iloc[i0:hi + 1] / spy.iloc[i0], axis=0)
        basket_rel = rel.mean(axis=1, skipna=True)
        i_tr = i0 + int(np.nanargmin(basket_rel.to_numpy()))
        rows.append(dict(cid=c["cid"], name=c["name"], shock_start=cal[i0].date(),
                         window_end=cal[hi].date(), trough=cal[i_tr].date(),
                         basket_rel_dd=round(float(basket_rel.min() - 1), 4),
                         n_named=len(c["tickers"]), n_usable=len(members), n_lost=lost))
    df = pd.DataFrame(rows).sort_values("basket_rel_dd")
    print(df.to_string(index=False))
    df.to_csv(Path(__file__).resolve().parent / "out" / "screen_candidates.csv",
              index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
