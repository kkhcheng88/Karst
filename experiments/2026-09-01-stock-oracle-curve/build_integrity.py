"""KARST-139 第二步:數據完整性掃描(事後全知研究的必要前置)。

為什麼一定要做:神諭按「下一期回報最高」揀股,任何一格拆股殘留或者髒價
都會被系統性揀中——上限會被幾格壞數據抬高。所以先量每個股月的最大單日
變動,再與拆股事件表對照。

判準(先寫死,再看結果):
  一個股月若果「該月內出現 ≥ ±50% 的單日變動」而「該月及前後一個月都沒有
  拆股紀錄」,判為數據完整性存疑 → 剔出可選宇宙。
  (真實個股單日 ±50% 極罕見;2008/09 那批真事件多數是連續多日累積,
   單日仍在 ±50% 以內,例如 AIG 2009-08 最大單日 +62.7% 會被剔——
   所以另備一個不剔任何格的口徑做敏感度。)

輸出 data/day_moves.parquet: symbol, month_end, max_abs_day
"""
from __future__ import annotations

import pathlib

import pandas as pd

from defeatbeta_api.client.duckdb_client import get_duckdb_client
from defeatbeta_api.client.hugging_face_client import HuggingFaceClient

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "data"

START, END = "1998-11-01", "2026-08-31"


def main() -> None:
    m = pd.read_parquet(OUT / "stock_monthly.parquet", columns=["symbol"])
    syms = sorted(m["symbol"].unique().tolist())
    in_list = ",".join("'" + s.replace("'", "''") + "'" for s in syms)

    cli = get_duckdb_client()
    hf = HuggingFaceClient()
    u = hf.get_url_path("stock_prices")
    q = f"""
        SELECT symbol, last_day(d) AS month_end,
               max(abs(chg)) AS max_abs_day, count(*) AS n_days
        FROM (
          SELECT symbol, CAST(report_date AS DATE) AS d,
                 close / lag(close) OVER (PARTITION BY symbol
                        ORDER BY CAST(report_date AS DATE)) - 1 AS chg
          FROM '{u}'
          WHERE symbol IN ({in_list})
            AND CAST(report_date AS DATE) BETWEEN DATE '{START}' AND DATE '{END}'
        )
        WHERE chg IS NOT NULL
        GROUP BY 1, 2
    """
    dm = cli.query(q)
    dm["month_end"] = pd.to_datetime(dm["month_end"])
    dm.to_parquet(OUT / "day_moves.parquet", index=False)
    print(f"單日變動聚合 {len(dm)} 個股月, {dm['symbol'].nunique()} 隻")
    for t in (0.5, 0.8, 1.0):
        print(f"  最大單日 ≥ {t:.0%} 的股月: {(dm['max_abs_day'] >= t).sum()}")


if __name__ == "__main__":
    main()
