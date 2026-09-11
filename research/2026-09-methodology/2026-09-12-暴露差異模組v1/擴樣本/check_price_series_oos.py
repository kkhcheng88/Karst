# -*- coding: utf-8 -*-
"""KARST-220:核對價格庫的未還原收市價(只印衝擊起日或之前,不觸及任何結果欄)。

用途:Lloyds/Barclays 兩隻英國銀行 ADR 在 2016 上半年的走勢要對得上 20-F 自列的
年結每股價,否則每股換算不能用。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
B199 = ROOT / "research" / "2026-09-methodology" / "2026-09-10-①行業殺錯事件籃子"
sys.path.insert(0, str(B199))
from basket_core import build_wide, load_prices, load_spy, resolve_tickers  # noqa: E402

CUT = pd.Timestamp("2016-06-23")     # 硬界線:只印這日或之前
TICKERS = ["LYG", "BCS", "HSBC", "JPM"]


def main() -> None:
    spy_df = load_spy()
    px = load_prices()
    cal, _, _ = build_wide(px, spy_df)
    cal = pd.DatetimeIndex(cal)
    raw = px.pivot_table(index="date", columns="entity_id", values="close",
                         aggfunc="last").reindex(cal)
    ent = {}
    for t in TICKERS:
        r = resolve_tickers([t], CUT)
        ent[t] = r.iloc[0]["entity_id"] if r.iloc[0]["resolve_status"] == "已解析" else None
    dates = ["2015-12-31", "2016-02-11", "2016-04-29", "2016-06-01", "2016-06-20",
             "2016-06-21", "2016-06-22"]
    print("未還原收市價(原始序列,未做任何還原)")
    print(f"{'date':12s}" + "".join(f"{t:>10s}" for t in TICKERS))
    base = {}
    for d in dates:
        i = int(cal.searchsorted(pd.Timestamp(d), side="right") - 1)
        vals = []
        for t in TICKERS:
            e = ent[t]
            v = float(raw[e].iloc[i]) if (e and e in raw.columns) else float("nan")
            vals.append(v)
            base.setdefault(t, v)
        print(f"{str(cal[i].date()):12s}" + "".join(f"{v:>10.2f}" for v in vals))
    print("\n相對 2015-12-31 的變化")
    print(f"{'date':12s}" + "".join(f"{t:>10s}" for t in TICKERS))
    for d in dates:
        i = int(cal.searchsorted(pd.Timestamp(d), side="right") - 1)
        vals = []
        for t in TICKERS:
            e = ent[t]
            v = float(raw[e].iloc[i]) if (e and e in raw.columns) else float("nan")
            vals.append(v / base[t] - 1 if base[t] else float("nan"))
        print(f"{str(cal[i].date()):12s}" + "".join(f"{v:>9.1%} " for v in vals))
    # 資料點是否連續(有無缺日)
    for t in TICKERS:
        e = ent[t]
        if not e or e not in raw.columns:
            continue
        s = raw[e].loc["2016-01-04":"2016-06-22"]
        print(f"{t}: 2016H1 交易日 {len(s)},非空 {int(s.notna().sum())},首 {s.index[0].date()},尾 {s.index[-1].date()}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
