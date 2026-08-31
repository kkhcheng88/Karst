"""KARST-133 第一步:砌板塊層倍數序列(逐月),三種盈利對齊。

輸出 data/sector_multiples.parquet(大檔,不入 git)。

口徑(報告第三節有完整說明):
  板塊倍數(m) = Σ_i 市值_i(m) / Σ_i 盈利_i(m)
              = Σ_i (收市價_i × 股數_i) / Σ_i (每股盈利_i × 股數_i)
  這是指數式聚合(總和比總和),蝕錢成員照計入分母——刻意不採
  富途那種「剔走蝕錢成員」的算法(D-089 已判該算法不可用)。

三種盈利對齊:
  oracle_fwd  神諭·完美預測 :用 m + 12 個月那一季的滾動十二個月每股盈利
  oracle_now  神諭·盈利即知 :用 report_date ≤ m 的最近一季(零公布滯後)
  real_lag    現實·公布後才知:用 report_date + 60 日 ≤ m 的最近一季

成分:本倉 karst/data/universes/sp500_historical.csv(帶上市/除名日期,
      名單本身無倖存者偏差);板塊分類取 defeatbeta stock_profile.sector
      (今日分類回溯 = 分類前視,報告已明文交代)。
"""
from __future__ import annotations

import pathlib

import pandas as pd

from defeatbeta_api.client.duckdb_client import get_duckdb_client
from defeatbeta_api.client.hugging_face_client import HuggingFaceClient

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)
REPO = HERE.parent.parent

# 九隻 SPDR ← Yahoo sector(回報面板只有這九隻,XLRE/XLC 無價格數據不做)
SECTOR_MAP = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Basic Materials": "XLB",
    "Utilities": "XLU",
}

START = "1998-12-01"
END = "2026-08-31"
MIN_MEMBERS = 8          # 一個板塊當月少過這麼多隻有數據,該格判為缺
PUBLISH_LAG_DAYS = 60    # 現實版:財季結束後 60 日才當公布


def main() -> None:
    cli = get_duckdb_client()
    hf = HuggingFaceClient()
    u_profile = hf.get_url_path("stock_profile")
    u_eps = hf.get_url_path("stock_tailing_eps")
    u_px = hf.get_url_path("stock_prices")
    u_sh = hf.get_url_path("stock_shares_outstanding")

    # ---- 成分名單(帶生效期,無倖存者偏差)----
    mem = pd.read_csv(REPO / "karst" / "data" / "universes" / "sp500_historical.csv")
    mem["joined_on"] = pd.to_datetime(mem["joined_on"])
    mem["left_on"] = pd.to_datetime(mem["left_on"]).fillna(pd.Timestamp("2100-01-01"))
    tickers = sorted(mem["ticker"].dropna().unique().tolist())
    print(f"標普成分段數 {len(mem)}, 相異代號 {len(tickers)}")
    in_list = ",".join("'" + t.replace("'", "''") + "'" for t in tickers)

    # ---- 板塊分類 ----
    prof = cli.query(
        f"SELECT symbol, sector FROM '{u_profile}' WHERE symbol IN ({in_list})"
    )
    prof = prof.dropna(subset=["sector"]).drop_duplicates("symbol")
    prof["etf"] = prof["sector"].map(SECTOR_MAP)
    prof = prof.dropna(subset=["etf"])
    print(f"取得板塊分類 {len(prof)} 隻;分佈:\n{prof['etf'].value_counts().to_string()}")

    # ---- 月底價格(每個代號每月最後一個交易日的收市價)----
    px = cli.query(f"""
        SELECT symbol, month_end, close FROM (
          SELECT symbol,
                 date_trunc('month', CAST(report_date AS DATE)) AS mth,
                 CAST(report_date AS DATE) AS d, close,
                 row_number() OVER (PARTITION BY symbol,
                     date_trunc('month', CAST(report_date AS DATE))
                     ORDER BY CAST(report_date AS DATE) DESC) AS rn,
                 last_day(CAST(report_date AS DATE)) AS month_end
          FROM '{u_px}'
          WHERE symbol IN ({in_list})
            AND CAST(report_date AS DATE) BETWEEN DATE '{START}' AND DATE '{END}'
        ) WHERE rn = 1
    """)
    px["month_end"] = pd.to_datetime(px["month_end"])
    print(f"月底價格 {len(px)} 列, {px['symbol'].nunique()} 隻")

    # ---- 股數(季度申報,取 ≤ 月底的最近一筆)----
    sh = cli.query(
        f"SELECT symbol, CAST(report_date AS DATE) AS d, shares_outstanding "
        f"FROM '{u_sh}' WHERE symbol IN ({in_list})"
    )
    sh["d"] = pd.to_datetime(sh["d"])
    sh = sh.dropna(subset=["shares_outstanding"]).sort_values(["symbol", "d"])
    print(f"股數 {len(sh)} 列, {sh['symbol'].nunique()} 隻")

    # ---- 滾動十二個月每股盈利(季度)----
    eps = cli.query(
        f"SELECT symbol, CAST(report_date AS DATE) AS d, tailing_eps "
        f"FROM '{u_eps}' WHERE symbol IN ({in_list})"
    )
    eps["d"] = pd.to_datetime(eps["d"])
    eps = eps.dropna(subset=["tailing_eps"]).sort_values(["symbol", "d"])
    print(f"滾動每股盈利 {len(eps)} 列, {eps['symbol'].nunique()} 隻, "
          f"最早 {eps['d'].min().date()}")

    months = pd.date_range(START, END, freq="ME")
    panel = px[px["month_end"].isin(months)].copy()
    panel = panel.merge(prof[["symbol", "etf"]], on="symbol", how="inner")

    # 只保留當月確實在標普 500 之內的成分段
    mm = mem[["ticker", "joined_on", "left_on"]].rename(columns={"ticker": "symbol"})
    panel = panel.merge(mm, on="symbol", how="inner")
    panel = panel[(panel["month_end"] >= panel["joined_on"])
                  & (panel["month_end"] <= panel["left_on"])]
    panel = panel.drop_duplicates(["symbol", "month_end"])
    print(f"成分×月 面板 {len(panel)} 列")

    # ---- 逐項 as-of 併入 ----
    panel = panel.sort_values(["symbol", "month_end"])

    def asof(left: pd.DataFrame, right: pd.DataFrame, rcol: str,
             shift_days: int, name: str) -> pd.DataFrame:
        r = right.copy()
        r["key"] = r["d"] + pd.Timedelta(days=shift_days)
        r = r.sort_values(["symbol", "key"]).dropna(subset=["key"])
        out = pd.merge_asof(
            left.sort_values("month_end"), r.sort_values("key"),
            left_on="month_end", right_on="key", by="symbol", direction="backward",
        )
        return out.rename(columns={rcol: name})

    panel = asof(panel, sh, "shares_outstanding", 0, "shares")
    panel = panel.drop(columns=[c for c in ("d", "key") if c in panel.columns])

    panel = asof(panel, eps, "tailing_eps", 0, "eps_now")
    panel = panel.drop(columns=[c for c in ("d", "key") if c in panel.columns])

    panel = asof(panel, eps, "tailing_eps", PUBLISH_LAG_DAYS, "eps_lag")
    panel = panel.drop(columns=[c for c in ("d", "key") if c in panel.columns])

    # 神諭·完美預測:向前望 12 個月 = 把盈利序列日期「提早」12 個月再 as-of
    panel = asof(panel, eps, "tailing_eps", -365, "eps_fwd")
    panel = panel.drop(columns=[c for c in ("d", "key") if c in panel.columns])

    panel["mcap"] = panel["close"] * panel["shares"]
    for a in ("fwd", "now", "lag"):
        panel[f"earn_{a}"] = panel[f"eps_{a}"] * panel["shares"]

    panel.to_parquet(OUT / "constituent_panel.parquet", index=False)
    print(f"逐股面板已落檔 {len(panel)} 列")

    # ---- 聚合成板塊層與大市層 ----
    rows = []
    for etf, g_all in panel.groupby("etf"):
        for me, g in g_all.groupby("month_end"):
            rec = {"month_end": me, "series": etf, "n_members": len(g)}
            ok = g.dropna(subset=["mcap"])
            rec["total_mcap"] = ok["mcap"].sum()
            for a in ("fwd", "now", "lag"):
                gg = g.dropna(subset=["mcap", f"earn_{a}"])
                if len(gg) < MIN_MEMBERS:
                    rec[f"pe_{a}"] = float("nan")
                    rec[f"n_{a}"] = len(gg)
                    continue
                tot_e = gg[f"earn_{a}"].sum()
                tot_m = gg["mcap"].sum()
                rec[f"pe_{a}"] = tot_m / tot_e if tot_e > 0 else float("nan")
                rec[f"n_{a}"] = len(gg)
            rows.append(rec)

    # 大市層(全部標普成分合成一條,做「倍數對大市比值」的分母)
    for me, g in panel.groupby("month_end"):
        rec = {"month_end": me, "series": "MKT", "n_members": len(g)}
        rec["total_mcap"] = g["mcap"].sum()
        for a in ("fwd", "now", "lag"):
            gg = g.dropna(subset=["mcap", f"earn_{a}"])
            tot_e = gg[f"earn_{a}"].sum()
            rec[f"pe_{a}"] = (gg["mcap"].sum() / tot_e) if tot_e > 0 else float("nan")
            rec[f"n_{a}"] = len(gg)
        rows.append(rec)

    out = pd.DataFrame(rows).sort_values(["series", "month_end"])
    out.to_parquet(OUT / "sector_multiples.parquet", index=False)
    out.to_csv(HERE / "sector_multiples.csv", index=False, encoding="utf-8")
    print(f"\n板塊倍數序列已落檔 {len(out)} 列")
    print(out.groupby("series")[["pe_fwd", "pe_now", "pe_lag"]].apply(
        lambda d: d.notna().sum()).to_string())
    print("\n覆蓋起點(每條序列 pe_now 首個有效月):")
    for s, g in out.groupby("series"):
        v = g.dropna(subset=["pe_now"])
        if len(v):
            print(f"  {s}: {v['month_end'].min().date()} .. {v['month_end'].max().date()}"
                  f"  中位成分數 {int(g['n_now'].median())}")


if __name__ == "__main__":
    main()
