# -*- coding: utf-8 -*-
"""KARST-225 票 A′(v1.1):輸出三份交付檔 —— population.csv、entry_pool.csv、thresholds.md。

與 `A/s10_export.py` 之別:①加 `turnover_mean_60d`(門檻用)與 `turnover_median_60d` 兩欄;
②排除理由文字改「60 日平均成交額不足 1,000 萬」;③thresholds.md 加一欄「v1 同年門檻」對照。

**必須在 `picks_before_results.md` 落檔之後才跑**(鎖定次序要求)。
population.csv 內含 T2(反應日之後一個交易日的開盤),屬 T1 之後的價格欄,故不入抽樣前。

population.csv 欄位:
  識別 —— cik / ticker / sic2 / fiscal_quarter / cluster_id / repeat_company_flag /
          adr_flag / covid_window / improvement_type(執行口徑 v1 第一節點名那幾欄)
  時點 —— T0(acceptanceDateTime 與美東時間)、T1(反應日)與 T1 收市、T2 與 T2 開市
  價格 —— 反應報酬、相對 SPY、相對同 SIC2 同日中位、60 日平均/中位成交額
  經營 —— 訊號季、g0、前一季按年、加速(pp)、指引上調正則命中
  排除 —— 逐條排除旗標與合併後的理由欄、宇宙內旗標、三檔百分位旗標
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import pxlib

ROOT = Path(r"C:\projects\Karst")
PRICES = ROOT / "data" / "prices" / "daily"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
PX_FROM = "2013-06-01"

ORDER = ["accessionNumber", "cik", "name", "ticker", "form", "sic", "sic2", "bucket",
         "fiscal_quarter", "reportDate", "filingDate", "acceptanceDateTime", "t0_et",
         "t0_after16", "t0_weekend",
         "reaction_date", "t1_close_adj", "prev_date", "t1_prev_close_adj",
         "t2_date", "t2_open_adj",
         "ret_reaction", "spy_ret_same_day", "rel_spy", "rel_sic2",
         "dvol_med_60", "turnover_mean_60d", "turnover_median_60d", "n_window",
         "gate_volume", "first_px_date", "listed_months",
         "signal_q_end", "signal_q_days_before_filing", "rev_g0", "rev_prev_q_yoy",
         "accel_pp", "accel_hit", "has_text", "guidance_raise", "going_concern_hit",
         "improvement_type",
         "has_1_01", "excl_volume", "excl_listed_lt_12m", "excl_spac", "excl_merger_1_01",
         "excl_going_concern", "excl_no_price", "exclusion_reason", "in_universe",
         "pass_p95", "pass_p90", "pass_p80",
         "repeat_company_flag", "adr_flag", "covid_window", "cluster_id", "year"]

REASON = [("excl_no_price", "無日線"), ("excl_volume", "60 日平均成交額不足 1,000 萬"),
          ("excl_listed_lt_12m", "上市未滿 12 個月"), ("excl_spac", "SPAC"),
          ("excl_merger_1_01", "同日 8-K 有 Item 1.01"),
          ("excl_going_concern", "持續經營疑慮")]


def load_px(entity_filter: set) -> dict:
    """逐檔掃描(pxlib;2,065 萬列一次過讀入會爆記憶體),只留需要的公司。"""
    return pxlib.price_arrays(entity_filter)


def main() -> None:
    df = pd.read_parquet(CACHE / "population_improvement.parquet")
    spy = pd.read_csv(ROOT / "data" / "prices" / "spy_daily.csv", parse_dates=["date"])
    spy = spy.sort_values("date")
    spy["d"] = spy["date"].values.astype("datetime64[D]")
    spy["r"] = spy["adj_close"].pct_change()
    spy_map = dict(zip(spy["d"], spy["r"]))

    px = load_px(set(df["cik"].astype(str).str.zfill(10)))
    print("價格快取:%d 家" % len(px), flush=True)
    n = len(df)
    t1c = np.full(n, np.nan)
    t2o = np.full(n, np.nan)
    pvc = np.full(n, np.nan)
    eids = df["cik"].astype(str).str.zfill(10).to_numpy()
    d1 = pd.to_datetime(df["reaction_date"], errors="coerce")
    d0 = pd.to_datetime(df["prev_date"], errors="coerce")
    d2 = pd.to_datetime(df["t2_date"], errors="coerce")
    d1a = d1.values.astype("datetime64[D]")
    d0a = d0.values.astype("datetime64[D]")
    d2a = d2.values.astype("datetime64[D]")
    uniq, inv = np.unique(eids, return_inverse=True)
    for k, eid in enumerate(uniq):
        ser = px.get(eid)
        if ser is None:
            continue
        dd, ad, cl, op = ser
        idxs = np.nonzero(inv == k)[0]
        for i in idxs:
            j = np.searchsorted(dd, d1a[i])
            if j < len(dd) and dd[j] == d1a[i]:
                t1c[i] = ad[j]
            if not np.isnat(d0a[i]):
                j0 = np.searchsorted(dd, d0a[i])
                if j0 < len(dd) and dd[j0] == d0a[i]:
                    pvc[i] = ad[j0]
            if not np.isnat(d2a[i]):
                j2 = np.searchsorted(dd, d2a[i])
                if j2 < len(dd) and dd[j2] == d2a[i] and cl[j2] > 0:
                    t2o[i] = op[j2] * ad[j2] / cl[j2]

    df["t1_close_adj"] = np.round(t1c, 6)
    df["t1_prev_close_adj"] = np.round(pvc, 6)
    df["t2_open_adj"] = np.round(t2o, 6)
    df["ret_reaction"] = df["ret"].round(6)
    df["spy_ret_same_day"] = df["reaction_date"].map(spy_map).astype(float).round(6)

    reasons = []
    for _, r in df.iterrows():
        rs = [lab for col, lab in REASON
              if (r[col] == 1) or (col == "excl_going_concern" and r[col] == "有")]
        if r["excl_going_concern"] == "未核":
            rs.append("持續經營疑慮(未核)")
        reasons.append(";".join(rs))
    df["exclusion_reason"] = reasons

    df = df.reindex(columns=[c for c in ORDER if c in df.columns])
    df.to_csv(HERE / "population.csv", index=False, encoding="utf-8-sig")
    print("population.csv:%d 列 × %d 欄" % df.shape)
    print("  宇宙內 %d;排除分佈:%s" % (
        df["in_universe"].sum(),
        {lab: int((df[col] == 1).sum()) for col, lab in REASON if col != "excl_going_concern"}))

    # ---- entry_pool.csv(執行口徑 v1 第二節第 2 點)
    ep = df[(df["in_universe"] == 1) & (df["pass_p90"] == 1)
            & (df["improvement_type"].isin(["加速", "指引", "兩者"]))
            & (df["excl_going_concern"] != "有")].copy()
    ep.to_csv(HERE / "entry_pool.csv", index=False, encoding="utf-8-sig")
    print("entry_pool.csv:%d 列;逐年 %s" % (
        len(ep), ep["year"].astype(str).value_counts().sort_index().to_dict()))

    # ---- thresholds.md
    th = json.loads((CACHE / "thresholds.json").read_text(encoding="utf-8"))
    L = []
    add = L.append
    v1th = json.loads((HERE.parent / "A" / "cache" / "thresholds.json").read_text(
        encoding="utf-8"))
    add("# ②第一次考試 · 票 A′(執行口徑 v1.1)逐年門檻與事件數(thresholds.md)")
    add("")
    add("**成交額門檻 = 1,000 萬美元(公布前 60 個交易日算術平均)**,其餘四道閘不變。")
    add("百分位底 = 該年**宇宙內**事件(已過成交額、上市年資、SPAC、同日 8-K Item 1.01 四道")
    add("閘)的相對 SPY 反應報酬 `rel_spy`(缺值不計)。逐年的第 95/90/80 百分位各取一個門檻值。")
    add("「事件數」= 該年宇宙內事件中 `rel_spy ≥ 門檻` **且**相對同業中位反應 `rel_sic2 > 0` 者")
    add("(即執行口徑 v1 第二節第 2 點的價格部分;入口池再要求 `improvement_type ≠ 無`,見下)。")
    add("")
    add("| 年 | 宇宙內事件數 | 第95百分位門檻 | ≥95 事件數 | 第90百分位門檻 | ≥90 事件數 |"
        " 第80百分位門檻 | ≥80 事件數 | 入口池(≥90 且改善非無) |"
        " v1 宇宙內事件數 | v1 第90百分位門檻 |")
    add("|---|---|---|---|---|---|---|---|---|---|---|")
    for y in sorted(th):
        t = th[y]
        c90 = int(((df["year"].astype(str) == y) & (df["pass_p90"] == 1)).sum())
        c95 = int(((df["year"].astype(str) == y) & (df["pass_p95"] == 1)).sum())
        c80 = int(((df["year"].astype(str) == y) & (df["pass_p80"] == 1)).sum())
        ne = int((ep["year"].astype(str) == y).sum())
        v = v1th.get(y, {})
        add("| %s | %d | %.4f | %d | %.4f | %d | %.4f | %d | %d | %s | %s |"
            % (y, t["n"], t["p95"], c95, t["p90"], c90, t["p80"], c80, ne,
               v.get("n", "—"),
               "—" if "p90" not in v else "%.4f" % v["p90"]))
    add("")
    add("合計:宇宙內 %d;≥95 %d;≥90 %d;≥80 %d;入口池 %d。"
        % (df["in_universe"].sum(), df["pass_p95"].sum(), df["pass_p90"].sum(),
           df["pass_p80"].sum(), len(ep)))
    add("")
    add("註:第 95/80 版的數目只作靈敏度參考;執行口徑 v1.1 的入口池定義用第 90 百分位。")
    add("門檻只算相對 SPY,不含相對同業;相對同業 > 0 另作一個條件。")
    add("末兩欄是 v1(成交額門檻 300 萬美元)的同一年數字,取自 `A/thresholds.md` /")
    add("`A/cache/thresholds.json`,只作對照;**每年宇宙內事件數都與 v1 不同**(宇宙已重建)。")
    add("")
    add("v1 逐年宇宙內事件數 / 第90百分位門檻:"
        + "、".join("%s %s/%.4f" % (y, v1th[y]["n"], v1th[y]["p90"]) for y in sorted(v1th)))
    (HERE / "thresholds.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("thresholds.md 完成")
    print("→", HERE)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
