# -*- coding: utf-8 -*-
"""KARST-192 第(二)(三)步:總回報口徑量度 + 前二十大贏家逐筆機械核查。

(二) 總回報口徑
  價格庫 README 第一節:`close` = 拆股調整、**未除息**;`adj_close` = 拆股 + 除息。
  SPY README 第二節:同一口徑。build_events.py 兩邊都用 adj_close(第 103、467-469 行),
  所以個股與大市**同是總回報口徑**。本步用資料實證這一句,並量出「若一邊用價格口徑」
  會差幾多:對每個合格 12 個月事件同時算
      TR 超額   = (adj_close 比率) / (SPY adj_close 比率) - 1        <- 現用
      價格超額 = (close 比率)     / (SPY close 比率)     - 1
  兩者之差就是「個股股息率 - SPY 股息率」在該持有年的實現值。

(三) 前二十大贏家逐筆核
  逐筆重算超額、量拆股/反向拆股(股數變動與價格庫 ticker 變動)、量單日跳動、
  查代號時段是否覆蓋觸發日(代號重用污染的機械代理)。

輸出:out/recon_total_return_recon.csv、out/recon_total_return_summary_recon.json、
      out/recon_top_winners_checked_recon.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyarrow.compute as pc

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_tables as MT            # noqa: E402
import make_tables_gatefix as MTG   # noqa: E402

OUT = HERE / "out"
PRICES = ROOT / "data" / "prices" / "daily"
SPY_CSV = ROOT / "data" / "prices" / "spy_daily.csv"
TICKER_PERIODS = ROOT / "data" / "universe" / "ticker_periods.parquet"
PANEL = ROOT / "data" / "panel" / "quarterly_v3.parquet"

H12 = 252


def qualifying_events() -> pd.DataFrame:
    """六個版本任何一個收貨、資料可信、12 個月觸發日即買已成熟的事件(去重)。"""
    lb, _ = MT.load_long()
    lg, _ = MTG.load_long_gatefix()
    frames = []
    for long, vers, tag in ((lb, ("過閘A", "過閘A2", "過閘B"), "events.csv(正本)"),
                            (lg, ("過閘A", "過閘A2", "過閘B"), "events_gatefix.csv")):
        q = long[(long["進場格"] == MT.ENTRIES["A"]) & (long["期"] == "12m")
                 & long["資料可信"]].copy()
        q["任一版本收貨"] = q[list(vers)].any(axis=1)
        q = q[q["任一版本收貨"]]
        q["事件表"] = tag
        frames.append(q)
    ev = pd.concat(frames, ignore_index=True)
    ev = ev.drop_duplicates(subset=["entity_id", "trigger_date"], keep="first")
    return ev


def load_px(entity_ids: set[str]) -> pd.DataFrame:
    parts = sorted(PRICES.glob("part_*.parquet"))
    ids = pa_ids = list(entity_ids)
    frames = []
    for p in parts:
        t = pq.read_table(p, columns=["entity_id", "ticker", "date", "close",
                                      "adj_close", "series_role"])
        m = pc.and_(pc.is_in(t["entity_id"], value_set=__import__("pyarrow").array(ids)),
                    pc.equal(t["series_role"], "primary"))
        t = t.filter(m)
        if t.num_rows:
            frames.append(t.to_pandas())
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["entity_id", "date"], kind="stable").reset_index(drop=True)


def main() -> None:
    ev = qualifying_events()
    print(f"待核事件 {len(ev):,},涉及實體 {ev['entity_id'].nunique():,}")

    spy = pd.read_csv(SPY_CSV, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    spy_dates = spy["date"].to_numpy()
    spy_adj = spy["adj_close"].to_numpy(dtype="float64")
    spy_close = spy["close"].to_numpy(dtype="float64")

    px = load_px(set(ev["entity_id"]))
    print(f"價格列 {len(px):,}")

    idx = {}
    eid = px["entity_id"].to_numpy()
    s = 0
    for i in range(1, len(eid) + 1):
        if i == len(eid) or eid[i] != eid[s]:
            idx[eid[s]] = (s, i)
            s = i
    p_date = px["date"].to_numpy()
    p_close = px["close"].to_numpy(dtype="float64")
    p_adj = px["adj_close"].to_numpy(dtype="float64")
    p_tkr = px["ticker"].astype("string").to_numpy()

    rows = []
    for r in ev.itertuples(index=False):
        e = r.entity_id
        if e not in idx:
            continue
        lo, hi = idx[e]
        entry_d = pd.Timestamp(r.entry_A_date) if pd.notna(r.entry_A_date) else None
        if entry_d is None:
            continue
        seg_d = p_date[lo:hi]
        k_en = int(np.searchsorted(seg_d, np.datetime64(entry_d)))
        if k_en >= len(seg_d) or seg_d[k_en] != np.datetime64(entry_d):
            continue
        en = lo + k_en
        sp_en = int(np.searchsorted(spy_dates, np.datetime64(entry_d)))
        tgt = sp_en + H12
        if tgt >= len(spy_dates):
            continue
        tgt_date = spy_dates[tgt]
        k_ex = int(np.searchsorted(seg_d, tgt_date, side="right")) - 1
        if k_ex < 0:
            continue
        ex_i = lo + k_ex
        if (tgt_date - p_date[ex_i]).astype("timedelta64[D]").astype(int) > 10:
            continue
        sp_ex = int(np.searchsorted(spy_dates, p_date[ex_i]))

        st_tr = p_adj[ex_i] / p_adj[en] - 1.0
        sp_tr = spy_adj[sp_ex] / spy_adj[sp_en] - 1.0
        st_pr = p_close[ex_i] / p_close[en] - 1.0
        sp_pr = spy_close[sp_ex] / spy_close[sp_en] - 1.0
        exc_tr = (1 + st_tr) / (1 + sp_tr) - 1.0
        exc_pr = (1 + st_pr) / (1 + sp_pr) - 1.0

        win = slice(en, ex_i + 1)
        adj_w = p_adj[win]
        step = adj_w[1:] / adj_w[:-1] - 1.0 if len(adj_w) > 1 else np.array([0.0])
        tkr_w = pd.unique(p_tkr[win])

        rows.append(dict(
            entity_id=e, primary_ticker=r.primary_ticker, name=r.name,
            trigger_date=pd.Timestamp(r.trigger_date), entry_date=entry_d,
            exit_date=pd.Timestamp(p_date[ex_i]),
            entry_close=p_close[en], entry_adj=p_adj[en],
            exit_close=p_close[ex_i], exit_adj=p_adj[ex_i],
            股票總回報=st_tr, 大市總回報=sp_tr, 股票價格回報=st_pr, 大市價格回報=sp_pr,
            超額_總回報口徑=exc_tr, 超額_價格口徑=exc_pr,
            口徑差=exc_tr - exc_pr,
            存檔超額=float(r.超額),
            重算對照差=exc_tr - float(r.超額),
            股票除息因子=(p_adj[ex_i] / p_close[ex_i]) / (p_adj[en] / p_close[en]) - 1.0,
            大市除息因子=(spy_adj[sp_ex] / spy_close[sp_ex]) / (spy_adj[sp_en] / spy_close[sp_en]) - 1.0,
            窗內最大單日升=float(np.max(step)), 窗內最大單日跌=float(np.min(step)),
            窗內交易日=int(ex_i - en + 1),
            窗內代號=("|".join([str(x) for x in tkr_w])), 窗內代號數=int(len(tkr_w)),
        ))

    tr = pd.DataFrame(rows)
    tr.to_csv(OUT / "recon_total_return_recon.csv", index=False, encoding="utf-8-sig")

    summ = {
        "重算事件數": int(len(tr)),
        "重算 vs events.csv 最大絕對差": float(tr["重算對照差"].abs().max()),
        "TR 口徑平均超額": float(tr["超額_總回報口徑"].mean()),
        "價格口徑平均超額": float(tr["超額_價格口徑"].mean()),
        "口徑差 平均(個百分點)": float(tr["口徑差"].mean() * 100),
        "口徑差 中位(個百分點)": float(tr["口徑差"].median() * 100),
        "口徑差 p5(個百分點)": float(tr["口徑差"].quantile(0.05) * 100),
        "口徑差 p95(個百分點)": float(tr["口徑差"].quantile(0.95) * 100),
        "個股一年除息因子 中位(%)": float(tr["股票除息因子"].median() * 100),
        "個股一年除息因子 平均(%)": float(tr["股票除息因子"].mean() * 100),
        "個股零股息事件比例": float((tr["股票除息因子"].abs() < 1e-6).mean()),
        "SPY 一年除息因子 中位(%)": float(tr["大市除息因子"].median() * 100),
        "SPY 一年除息因子 平均(%)": float(tr["大市除息因子"].mean() * 100),
        "SPY 全期(2010-2026)年化股息率(%)": None,
    }
    m0 = int(np.searchsorted(spy_dates, np.datetime64("2010-01-04")))
    yrs = (spy_dates[-1] - spy_dates[m0]).astype("timedelta64[D]").astype(int) / 365.25
    tr_tot = spy_adj[-1] / spy_adj[m0]
    pr_tot = spy_close[-1] / spy_close[m0]
    summ["SPY 全期(2010-2026)年化股息率(%)"] = float(((tr_tot / pr_tot) ** (1 / yrs) - 1) * 100)
    summ["SPY 全期總回報年化(%)"] = float((tr_tot ** (1 / yrs) - 1) * 100)
    summ["SPY 全期價格年化(%)"] = float((pr_tot ** (1 / yrs) - 1) * 100)
    with open(OUT / "recon_total_return_summary_recon.json", "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=2)
    print(json.dumps(summ, ensure_ascii=False, indent=2))

    # ---- 前二十大贏家併入逐筆診斷
    tw = pd.read_csv(OUT / "recon_top_winners_recon.csv", encoding="utf-8-sig",
                     dtype={"entity_id": str}, parse_dates=["trigger_date"])
    tp = pd.read_parquet(TICKER_PERIODS)
    tp["valid_from"] = pd.to_datetime(tp["valid_from"])
    tp["valid_to"] = pd.to_datetime(tp["valid_to"])
    tp_by_tkr = tp.groupby("ticker")["entity_id"].nunique()
    tp_idx = tp.set_index(["entity_id", "ticker"])

    pan = pd.read_parquet(PANEL, columns=["entity_id", "period_end", "filed_date",
                                          "shares_outstanding"])
    pan["period_end"] = pd.to_datetime(pan["period_end"])

    chk = tw.merge(tr.drop(columns=["primary_ticker", "name"]),
                   on=["entity_id", "trigger_date"], how="left")

    def enrich(r):
        e, t = r["entity_id"], pd.Timestamp(r["trigger_date"])
        out = {}
        tk = r.get("primary_ticker")
        out["代號可對應實體數"] = int(tp_by_tkr.get(tk, 0))
        try:
            row = tp_idx.loc[(e, tk)]
            vf = row["valid_from"] if not isinstance(row, pd.DataFrame) else row["valid_from"].min()
            vt = row["valid_to"] if not isinstance(row, pd.DataFrame) else row["valid_to"].max()
            out["代號時段起"] = vf
            out["代號時段止"] = vt
            out["觸發日在代號時段內"] = bool(pd.notna(vf) and vf <= t and (pd.isna(vt) or vt >= t))
        except KeyError:
            out["代號時段起"] = pd.NaT
            out["代號時段止"] = pd.NaT
            out["觸發日在代號時段內"] = False
        sub = pan[(pan["entity_id"] == e)]
        a = sub[(sub["period_end"] <= t)].sort_values("period_end")
        b = sub[(sub["period_end"] > t) & (sub["period_end"] <= t + pd.Timedelta(days=400))].sort_values("period_end")
        sa = a["shares_outstanding"].dropna()
        sb = b["shares_outstanding"].dropna()
        out["觸發前股數"] = float(sa.iloc[-1]) if len(sa) else np.nan
        out["一年後股數"] = float(sb.iloc[-1]) if len(sb) else np.nan
        out["股數比"] = (out["一年後股數"] / out["觸發前股數"]
                        if len(sa) and len(sb) and out["觸發前股數"] else np.nan)
        return pd.Series(out)

    chk = pd.concat([chk, chk.apply(enrich, axis=1)], axis=1)
    chk["疑似拆股(股數比<=0.5 或 >=1.8)"] = chk["股數比"].apply(
        lambda x: bool(pd.notna(x) and (x <= 0.5 or x >= 1.8)))
    chk["疑似單日異常(升>=80% 或 跌<=-50%)"] = (
        (chk["窗內最大單日升"] >= 0.8) | (chk["窗內最大單日跌"] <= -0.5))
    chk["窗內換過代號"] = chk["窗內代號數"].fillna(0) > 1
    chk.to_csv(OUT / "recon_top_winners_checked_recon.csv", index=False, encoding="utf-8-sig")

    flags = ["疑似拆股(股數比<=0.5 或 >=1.8)", "疑似單日異常(升>=80% 或 跌<=-50%)",
             "窗內換過代號", "觸發日在代號時段內"]
    print(chk.groupby("版本")[flags].sum().to_string())
    print("重算對照差 最大:", float(chk["重算對照差"].abs().max()))


if __name__ == "__main__":
    main()
