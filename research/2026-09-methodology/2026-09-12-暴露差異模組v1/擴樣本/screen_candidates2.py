# -*- coding: utf-8 -*-
"""KARST-220 先導篩選第二輪:補財務事件(經營條件真的變)的候選。"""
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
    dict(cid="C11", name="2023-09 UAW 罷工殺汽車與零件商",
         shock="2023-09-14", end="2023-10-30",
         tickers=["F", "GM", "STLA", "APTV", "LEA", "BWA", "MGA", "ADNT", "DAN",
                  "ALV", "GNTX", "MOD", "THRM"]),
    dict(cid="C12", name="2022-10 對華晶片出口管制新規殺半導體與設備",
         shock="2022-10-06", end="2022-10-28",
         tickers=["AMAT", "LRCX", "KLAC", "ASML", "TER", "ONTO", "ACLS", "UCTT",
                  "AEIS", "MKSI", "ENTG", "NVDA", "AMD", "MU", "FORM", "COHU"]),
    dict(cid="C13", name="2021-03 Archegos 爆倉殺投行",
         shock="2021-03-25", end="2021-04-16",
         tickers=["CS", "UBS", "DB", "MS", "GS", "JPM", "NMR", "MUFG", "SMFG",
                  "BCS", "HSBC", "ING"]),
    dict(cid="C14", name="2015-09 柴油門殺車廠與零件",
         shock="2015-09-17", end="2015-10-02",
         tickers=["F", "GM", "TM", "HMC", "BWA", "ALV", "GNTX", "LEA", "MGA",
                  "TEN", "SMP", "MOD"]),
    dict(cid="C15", name="2018-12 加息恐慌殺雲軟件增長股",
         shock="2018-09-28", end="2018-12-24",
         tickers=["CRM", "NOW", "WDAY", "ADBE", "VEEV", "TWLO", "ZS", "OKTA",
                  "SPLK", "NTNX", "AYX", "MDB", "PANW", "TEAM"]),
    dict(cid="C17", name="2023-10 長息急升殺 REITs",
         shock="2023-07-28", end="2023-10-19",
         tickers=["SPG", "O", "VNO", "BXP", "ARE", "PLD", "SLG", "KIM", "REG",
                  "AVB", "EQR", "ESS", "MAA", "NNN", "WPC"]),
    dict(cid="C19", name="2020-06 疫情二次爆發殺航空郵輪(對照)",
         shock="2020-06-08", end="2020-06-30",
         tickers=["AAL", "DAL", "UAL", "LUV", "CCL", "RCL", "NCLH", "MAR", "HLT", "BKNG"]),
    dict(cid="C20", name="2022-04 上海封城殺汽車供應鏈",
         shock="2022-03-31", end="2022-05-12",
         tickers=["F", "GM", "TSLA", "NIO", "APTV", "LEA", "BWA", "MGA", "ADNT",
                  "DAN", "ALV", "GNTX"]),
]


def main() -> None:
    spy_df = load_spy()
    px = load_prices()
    cal, wide, spy = build_wide(px, spy_df)
    cal = pd.DatetimeIndex(cal)
    rows = []
    for c in CAND:
        i0 = int(cal.searchsorted(pd.Timestamp(c["shock"]), side="left"))
        if i0 >= len(cal):
            print(c["cid"], "起日超出日曆")
            continue
        t0 = cal[i0]
        i_end = int(min(cal.searchsorted(pd.Timestamp(c["end"]), side="right") - 1, len(cal) - 1))
        hi = int(min(i_end + 21, len(cal) - 1))
        res = resolve_tickers(c["tickers"], t0)
        good = res[res["resolve_status"] == "已解析"]["entity_id"].tolist()
        members = [e for e in good if e in wide.columns and np.isfinite(wide[e].iloc[i0])]
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
                         n_named=len(c["tickers"]), n_usable=len(members),
                         n_lost=len(c["tickers"]) - len(members)))
    df = pd.DataFrame(rows).sort_values("basket_rel_dd")
    print(df.to_string(index=False))
    df.to_csv(Path(__file__).resolve().parent / "out" / "screen_candidates2.csv",
              index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
