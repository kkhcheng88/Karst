# -*- coding: utf-8 -*-
"""KARST-220:核價格庫的拆股還原因子(只印衝擊日或之前 + 全序列的單日跳幅,不觸及任何結果欄)。

背景:價格庫 `source` 欄自報 `yfinance(auto_adjust=False, actions=False)`,即 `close` 是
Yahoo 的 Close 欄 —— Yahoo 會把**歷史價格按後來的拆股還原**,所以 `close` 是
「已按衝擊日之後所有拆股還原」的價,不是當日真實成交價。
`adj_close` 再額外還原股息。

本腳本做的事:
1. 逐隻印衝擊前一交易日(界線前最後一個收市)的 close / adj_close;
2. 掃 2010-01-01 之後全序列的單日對數變動,印最大三個絕對值 —— 若某隻在已知拆股日
   **沒有**出現接近該拆股比例的單日跳幅,即證明該序列已被還原;
3. 印出已知拆股日前後的 close,供人工核對。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent

# (ticker, 衝擊前一交易日, 已知其後拆股日, 拆股比例)
CASES = [
    ("COIN", "2022-06-10", None, 1.0),
    ("MSTR", "2022-06-10", "2024-08-08", 10.0),
    ("RIOT", "2022-06-10", None, 1.0),
    ("HOOD", "2022-06-10", None, 1.0),
    ("AMAT", "2022-10-06", None, 1.0),
    ("ASML", "2022-10-06", None, 1.0),
    ("NVDA", "2022-10-06", "2024-06-10", 10.0),
    ("MU", "2022-10-06", None, 1.0),
    ("F", "2023-09-14", None, 1.0),
    ("GM", "2023-09-14", None, 1.0),
    ("APTV", "2023-09-14", None, 1.0),
    ("MGA", "2023-09-14", None, 1.0),
    ("VNO", "2023-09-19", None, 1.0),
    ("SPG", "2023-09-19", None, 1.0),
    ("O", "2023-09-19", None, 1.0),
    ("PLD", "2023-09-19", None, 1.0),
    ("UNH", "2018-01-29", None, 1.0),
    ("CVS", "2018-01-29", None, 1.0),
    ("MCK", "2018-01-29", None, 1.0),
    ("CNC", "2018-01-29", None, 1.0),
]


def main() -> None:
    import glob

    frames = [pd.read_parquet(f, columns=["entity_id", "ticker", "date", "close", "adj_close"])
              for f in sorted(glob.glob(str(ROOT / "data" / "prices" / "daily" / "part_*.parquet")))]
    px = pd.concat(frames, ignore_index=True)
    px["date"] = pd.to_datetime(px["date"])
    px = px.drop_duplicates(subset=["ticker", "date"], keep="last")

    print(f"{'ticker':7s}{'衝擊前收市':>12s}{'adj_close':>12s}{'其後拆股':>10s}{'因子':>6s}  最大三個單日跳幅")
    for tk, cut, split_date, factor in CASES:
        s = px[px["ticker"] == tk].sort_values("date")
        s = s[s["date"] >= "2010-01-01"]
        if s.empty:
            print(f"{tk:7s} 無資料")
            continue
        row = s[s["date"] <= pd.Timestamp(cut)].tail(1)
        c = float(row["close"].iloc[0])
        a = float(row["adj_close"].iloc[0])
        d0 = str(row["date"].iloc[0].date())
        lr = (s["close"] / s["close"].shift(1)).apply(lambda x: abs(x - 1) if pd.notna(x) else 0)
        top = lr.nlargest(3)
        tops = "  ".join(
            f"{str(s.loc[i, 'date'].date())} {lr.loc[i]:.1%}" for i in top.index
        )
        print(f"{tk:7s}{c:>12.2f}{a:>12.2f}{str(split_date or '-'):>10s}{factor:>6.1f}  {tops}  [衝擊日 {d0}]")
        if split_date:
            w = s[(s["date"] >= pd.Timestamp(split_date) - pd.Timedelta(days=6))
                  & (s["date"] <= pd.Timestamp(split_date) + pd.Timedelta(days=4))]
            print("       拆股日前後 close: " + "  ".join(
                f"{str(r.date.date())}={r.close:.2f}" for r in w.itertuples()))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
