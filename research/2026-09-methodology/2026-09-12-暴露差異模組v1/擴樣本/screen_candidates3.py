# -*- coding: utf-8 -*-
"""先導篩選第三輪:補未覆蓋行業(醫療保險/分銷、能源、公用)。"""
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
    dict(cid="C21", name="2018-01 亞馬遜-巴郡-JPM 健保合資殺健保與藥品分銷",
         shock="2018-01-29", end="2018-02-28",
         tickers=["UNH", "ANTM", "CI", "HUM", "CVS", "ESRX", "MCK", "ABC", "CAH",
                  "MOH", "CNC", "WCG", "HSIC", "PDCO"]),
    dict(cid="C22", name="2019-04 全民醫保提案恐慌殺健保股",
         shock="2019-04-15", end="2019-05-31",
         tickers=["UNH", "ANTM", "CI", "HUM", "CVS", "MOH", "CNC", "WCG", "MCK",
                  "ABC", "CAH", "HCA", "UHS", "THC", "CYH"]),
    dict(cid="C23", name="2018-08 藥品分銷商被控助長鴉片危機",
         shock="2018-08-09", end="2018-08-31",
         tickers=["MCK", "ABC", "CAH", "JNJ", "TEVA", "ENDP", "MNK", "AMRX"]),
    dict(cid="C24", name="2021-09 中國恒大違約恐慌殺在美中概與銀行",
         shock="2021-09-17", end="2021-10-06",
         tickers=["BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "TME", "EDU",
                  "TAL", "FUTU", "TIGR", "JPM", "BAC", "C", "GS"]),
    dict(cid="C25", name="2019-08 中美關稅升級殺零售與工業",
         shock="2019-07-31", end="2019-08-30",
         tickers=["AAPL", "NKE", "SBUX", "HD", "LOW", "TGT", "WMT", "CAT", "DE",
                  "HON", "MMM", "EMR", "ETN", "BA", "GE"]),
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
    df.to_csv(Path(__file__).resolve().parent / "out" / "screen_candidates3.csv",
              index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
