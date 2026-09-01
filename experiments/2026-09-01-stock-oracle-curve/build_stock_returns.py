"""KARST-139 第一步:砌個股層月度含息回報面板。

輸入(倉內現成,不新開數據線):
  experiments/2026-09-02-multiples-oracle-scan/data/constituent_panel.parquet
      587 隻標普成分股、九個板塊、1998-12 至 2026-08 逐月月底收市價,
      帶點對點成員資格(joined_on / left_on)。收市價已調整拆股,未含股息。
  defeatbeta stock_dividend_events  逐次派息(金額同樣已按拆股調整,已核實)
  experiments/2026-08-31-fear-greed/prices_daily.parquet  SPY 與九隻板塊 ETF 已含息日價

輸出 data/ (大檔,不入 git):
  stock_monthly.parquet   symbol, month_end, etf, close, div, ret(含息月度回報)
  bench_monthly.parquet   month_end, SPY 與九隻板塊 ETF 的含息月度回報

口徑:
  含息月度回報 r(m) = (close(m) + 該月除息金額) / close(m-1) - 1
  除息金額用 stock_dividend_events 的 amount,已按拆股調整到與收市價同一基準
  (核實:AAPL 2013 年季度派息表值 0.09,實際 2.65,比例 1/28 = 1/(7×4),
   正好是 2014 年 7:1 與 2020 年 4:1 兩次拆股的乘積)。
"""
from __future__ import annotations

import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)
REPO = HERE.parent.parent

PANEL = REPO / "experiments" / "2026-09-02-multiples-oracle-scan" / "data" / "constituent_panel.parquet"
ETF_PX = REPO / "experiments" / "2026-08-31-fear-greed" / "prices_daily.parquet"


def main() -> None:
    panel = pd.read_parquet(PANEL, columns=["symbol", "month_end", "close", "etf",
                                            "joined_on", "left_on"])
    # 面板本身已按成員資格過濾;清走 7 條越界殘留
    panel = panel[(panel["month_end"] >= panel["joined_on"])
                  & (panel["month_end"] < panel["left_on"])].copy()
    panel = panel.sort_values(["symbol", "month_end"]).reset_index(drop=True)
    syms = sorted(panel["symbol"].unique().tolist())
    print(f"面板 {len(panel)} 列, {len(syms)} 隻, "
          f"{panel['month_end'].min().date()} 至 {panel['month_end'].max().date()}")

    # ---- 派息 ----
    from defeatbeta_api.client.duckdb_client import get_duckdb_client
    from defeatbeta_api.client.hugging_face_client import HuggingFaceClient

    cli = get_duckdb_client()
    hf = HuggingFaceClient()
    u_div = hf.get_url_path("stock_dividend_events")
    in_list = ",".join("'" + s.replace("'", "''") + "'" for s in syms)
    div = cli.query(
        f"SELECT symbol, CAST(report_date AS DATE) AS d, amount "
        f"FROM '{u_div}' WHERE symbol IN ({in_list})"
    )
    div["d"] = pd.to_datetime(div["d"])
    div = div.dropna(subset=["amount"])
    div["month_end"] = div["d"] + pd.offsets.MonthEnd(0)
    dm = div.groupby(["symbol", "month_end"], as_index=False)["amount"].sum()
    dm = dm.rename(columns={"amount": "div"})
    print(f"派息事件 {len(div)} 宗, {div['symbol'].nunique()} 隻; 聚合後 {len(dm)} 個股月")

    m = panel.merge(dm, on=["symbol", "month_end"], how="left")
    m["div"] = m["div"].fillna(0.0)

    # ---- 含息月度回報 ----
    g = m.groupby("symbol", sort=False)
    m["prev_close"] = g["close"].shift(1)
    m["prev_me"] = g["month_end"].shift(1)
    # 只承認連續月(上一個月底就是對上一格),中間有斷層的不計回報
    expected_prev = m["month_end"] - pd.offsets.MonthEnd(1)
    ok = m["prev_me"].eq(expected_prev) & m["prev_close"].gt(0)
    m["ret"] = ((m["close"] + m["div"]) / m["prev_close"] - 1.0).where(ok)
    m["ret_px"] = (m["close"] / m["prev_close"] - 1.0).where(ok)

    out = m[["symbol", "month_end", "etf", "close", "div", "ret", "ret_px"]]
    out.to_parquet(OUT / "stock_monthly.parquet", index=False)
    n_ok = out["ret"].notna().sum()
    print(f"個股月度回報 {n_ok} 格可用 (全部 {len(out)} 格)")
    print("極端值核對 (含息回報最高/最低五格):")
    print(out.nlargest(5, "ret")[["symbol", "month_end", "ret"]].to_string(index=False))
    print(out.nsmallest(5, "ret")[["symbol", "month_end", "ret"]].to_string(index=False))

    # ---- 基準:SPY 與九隻板塊 ETF(已含息日價 → 月底)----
    px = pd.read_parquet(ETF_PX)
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values(["ticker", "date"])
    px["month_end"] = px["date"] + pd.offsets.MonthEnd(0)
    last = px.groupby(["ticker", "month_end"], as_index=False).last()
    b = last.pivot(index="month_end", columns="ticker", values="close").sort_index()
    bret = b.pct_change()
    bret.to_parquet(OUT / "bench_monthly.parquet")
    print(f"基準 {list(b.columns)}; {b.index.min().date()} 至 {b.index.max().date()}")

    # 交叉核對:SPY 與 XLK 年化,應對得上 KARST-113 (8.64% / 10.16%)
    idx = bret.index[(bret.index >= "1999-01-31") & (bret.index <= "2026-08-31")]
    for t in ["SPY", "XLK"]:
        if t in bret.columns:
            r = bret.loc[idx, t].dropna()
            yrs = len(r) / 12.0
            cagr = (1.0 + r).prod() ** (1.0 / yrs) - 1.0
            print(f"核對 {t}: {len(r)} 個月, 年化 {cagr * 100:.2f}%")


if __name__ == "__main__":
    main()
