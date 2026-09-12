# -*- coding: utf-8 -*-
"""KARST-226 票 A″(執行口徑 v1.2)第十二步:輸出三份交付檔。

  - `population.csv` —— 全母體逐宗欄位(含排除理由),T2 開盤屬 T1 後價格欄,不入抽樣前。
  - `entry_pool.csv` —— 入口池逐宗(= `entry_pool` 旗標為 1 者)。
  - `thresholds.md` —— **描述統計**(v1.2 第 3 項):門檻逐事件算,故逐年報窗口與門檻分佈,
    不再是一年一個門檻。
  - `.gitignore` —— cache/、edgar_cache/、__pycache__/、population.csv。

與 A2 版之別:v1.2 的入口池定義(前視門檻、稿頭日期 T0、稿內收入、適用性 F、併購閘、
七個標籤欄)直接讀 `entry_pool` 旗標;排除理由改列 v1.2 的六類新增理由;thresholds.md 改寫。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import pxlib

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

ORDER = ["accessionNumber", "cik", "name", "ticker", "form", "sic", "sic2", "bucket",
         "fiscal_quarter", "reportDate", "filingDate", "acceptanceDateTime", "t0_et",
         "t0_after16", "t0_weekend", "t0_source", "release_timing", "dateline_used",
         "dateline", "reaction_date", "t1_close_adj", "prev_date", "t1_prev_close_adj",
         "t2_date", "t2_open_adj",
         "ret_reaction", "spy_ret_same_day", "rel_spy", "rel_sic2", "prior_day_abs_ret",
         "dvol_med_60", "turnover_mean_60d", "turnover_median_60d", "n_window",
         "gate_volume", "first_px_date", "listed_months", "ma200", "above_200dma", "rs6",
         "signal_q_end", "signal_q_days_before_filing", "rev_g0", "rev_g0_text",
         "rev_prev_q_yoy", "accel_pp", "accel_pp_text", "accel_hit", "accel_text_hit",
         "rev_signal_text", "rev_signal_xbrl", "signal_rev_in_text",
         "guide_rev_raise", "guidance_raise_eps_only", "guide_any", "guide_n_sent",
         # 第 4 項指引解析器逐句結果(每宗取收入那一條;見 main() 的取法說明)
         "guidance_n_records", "guidance_metric", "guidance_period", "guidance_old_lo",
         "guidance_old_hi", "guidance_new_lo", "guidance_new_hi", "guidance_mid_change",
         "guidance_raise_flag", "guidance_old_missing", "guidance_eps_only",
         "xbrl_status", "rev_tag_used", "n_consec_q", "hist_quarters_public_by_t1",
         "hist_src_latest_filed", "prev4_yoy_mean", "improvement_type",
         "g0_negative", "rev_ttm", "both_signals", "rs6_top20", "rel_sic2_ge5",
         "accel_2q", "surprise_c2",
         "excl_no_price", "excl_volume", "excl_listed_lt_12m", "excl_spac",
         "excl_merger_2_01", "excl_merger_1_01", "excl_merger_1_01_old",
         "excl_going_concern", "excl_no_text", "excl_intraday", "excl_earlier_release",
         "excl_hist_not_public", "excl_applicability", "excl_financial_sic",
         "applicability_reason", "suspect_earlier_release", "merger_text_pending",
         "text_stage_checked",
         "exclusion_reason", "in_universe", "in_pool_window",
         "thr_win_days", "thr_n", "thr_p90", "thr_p95", "thr_p80", "thr_insufficient",
         "pass_p90", "pass_p95", "pass_p80", "entry_pool",
         "repeat_company_flag", "adr_flag", "covid_window", "year"]

REASON = [("excl_no_price", "無日線"), ("excl_volume", "60 日平均成交額不足 1,000 萬"),
          ("excl_listed_lt_12m", "上市未滿 12 個月"), ("excl_spac", "SPAC"),
          ("excl_merger_2_01", "同日 8-K Item 2.01(處置/併購)"),
          ("excl_merger_1_01", "同日 8-K Item 1.01 且正文有併購字眼"),
          ("excl_going_concern", "持續經營疑慮"),
          ("excl_financial_sic", "金融業(SIC 60–64、67)不適用"),
          ("excl_applicability", "適用性 F 不通過"),
          ("excl_hist_not_public", "歷史季度未於 T1 前公開"),
          ("excl_earlier_release", "疑更早公開(前一日絕對報酬 > 8%)"),
          ("excl_intraday", "業績稿盤中發布"),
          ("excl_no_text", "稿內找不到訊號季收入")]


def load_px(entity_filter: set) -> dict:
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
        for i in np.nonzero(inv == k)[0]:
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

    # 「稿內找不到訊號季收入」只在候選(過門檻且同業正)身上真的檢過;其餘事件的欄位是
    # 「未檢」而不是「檢過不合格」,故另設 text_stage_checked 欄,理由字串只對候選顯示。
    df["text_stage_checked"] = (
        (df["in_universe"] == 1) & (df["in_pool_window"]) & (df["pass_thr"] == True)  # noqa: E712
    ).astype(int)
    reasons = []
    for _, r in df.iterrows():
        rs = [lab for col, lab in REASON
              if ((r[col] == 1) or (col == "excl_going_concern" and r[col] == "有"))
              and not (col == "excl_no_text" and r["text_stage_checked"] == 0)]
        if r["excl_going_concern"] == "未核":
            rs.append("持續經營疑慮(未核)")
        if r["thr_insufficient"] == 1:
            rs.append("門檻資料不足")
        reasons.append(";".join(rs))
    df["exclusion_reason"] = reasons

    # ---- 第 4 項:指引解析器結果,每宗附一組欄(驗收條件二點名)----------
    # 同一宗可有多條指引句(全池 6,454 條、1,0xx 宗)。本附表每宗只放**收入**那一條:
    # 入池只認收入指引上調,故只有收入那條對入池有作用;同一宗有多條收入句者,先取
    # raise_flag=True 的,否則取文檔次序第一條。**此取法規格未寫明,執行紀錄已登記。**
    gcols = ["metric", "period", "old_lo", "old_hi", "new_lo", "new_hi", "mid_change",
             "raise_flag", "old_missing"]
    gmap: dict[str, dict] = {}
    nrec: dict[str, int] = {}
    gpath = CACHE / "guidance_parsed.jsonl"
    if gpath.exists():
        for line in gpath.open(encoding="utf-8"):
            r = json.loads(line)
            a = r["accessionNumber"]
            nrec[a] = nrec.get(a, 0) + 1
            if r["metric"] != "revenue":
                continue
            cur = gmap.get(a)
            if cur is None or (r["raise_flag"] and not cur["raise_flag"]):
                gmap[a] = r
    df["guidance_n_records"] = df["accessionNumber"].map(nrec).fillna(0).astype(int)
    for c in gcols:
        df["guidance_" + c] = df["accessionNumber"].map(
            lambda a, c=c: (gmap.get(a) or {}).get(c))
    df["guidance_eps_only"] = df["guidance_raise_eps_only"]

    # signal_rev_in_text 在 CSV 寫成 真 / 容差內差值 / 假(驗收條件的三個值):
    #   真 = 稿內數字與 XBRL 首報值同(相對差 ≤ 1e-6);
    #   容差內差值 = 稿內找到但不同(仍在 0.5% 匹配容差內,例稿寫 17.4 十億、XBRL 17.36 十億);
    #   假 = 稿內找不到(不入池)。
    tx = pd.to_numeric(df["rev_signal_text"], errors="coerce")
    xb = pd.to_numeric(df["rev_signal_xbrl"], errors="coerce")
    lab = pd.Series("假", index=df.index)
    hit = df["signal_rev_in_text"].astype(bool)
    lab[hit] = "容差內差值"
    lab[hit & tx.notna() & xb.notna() & (xb != 0) & ((tx / xb - 1).abs() <= 1e-6)] = "真"
    df["signal_rev_in_text"] = lab

    df = df.reindex(columns=[c for c in ORDER if c in df.columns])
    df.to_csv(HERE / "population.csv", index=False, encoding="utf-8-sig")
    print("population.csv:%d 列 × %d 欄" % df.shape)
    print("  稿內訊號季收入:%s" % df["signal_rev_in_text"].value_counts().to_dict())
    print("  宇宙內 %d;排除分佈:%s" % (
        df["in_universe"].sum(),
        {lab: int((df[col] == 1).sum()) for col, lab in REASON
         if col != "excl_going_concern"}))

    ep = df[df["entry_pool"] == 1].copy()
    ep.to_csv(HERE / "entry_pool.csv", index=False, encoding="utf-8-sig")
    print("entry_pool.csv:%d 列;逐年 %s" % (
        len(ep), ep["year"].astype(str).value_counts().sort_index().to_dict()))

    # ---- thresholds.md(v1.2:描述統計)
    th_all = json.loads((CACHE / "thresholds.json").read_text(encoding="utf-8"))
    th = th_all.get("by_year", th_all)
    w = pd.read_parquet(CACHE / "thresholds_window.parquet")
    L = []
    add = L.append
    add("# ②第一次考試 · 票 A″(執行口徑 v1.2)逐年門檻描述統計(thresholds.md)")
    add("")
    add("**v1.2 第 3 項:門檻改成逐事件算,不再是「一年一個門檻」。**每宗事件用自己的")
    add("**反應日之前過去 252 個交易日**窗口,取窗內「宇宙內合格業績事件」相對 SPY 反應")
    add("的第 90 百分位;窗內事件 < 300 宗則改用過去 504 個交易日;仍不足標「門檻資料不足」")
    add("不入池。母體掃描起點 2014-01-01 只作暖身(2014 事件只入窗、不入池)。")
    add("")
    add("本表因此只報**分佈**:同一年的每宗事件,門檻值與窗口大小都不同。")
    add("")
    add("| 年 | 宇宙內事件數 | 窗口事件數(中位/最小) | 改用 504 日 | 門檻資料不足 |"
        " 第90百分位門檻(中位/最小/最大) | 過門檻事件數 | 入口池 |")
    add("|---|---|---|---|---|---|---|---|")
    wy = w.assign(y=w["accessionNumber"].map(
        df.set_index("accessionNumber")["year"].astype(str)))
    for y in sorted(th):
        t = th[y]
        c90 = int(((df["year"].astype(str) == y) & (df["pass_p90"] == 1)).sum())
        ne = int((ep["year"].astype(str) == y).sum())
        g = wy[wy["y"] == y]
        add("| %s | %d | %.0f/%.0f | %d | %d | %.4f/%.4f/%.4f | %d | %d |"
            % (y, t["n_events"], g["thr_n"].median(), g["thr_n"].min(),
               int((g["thr_win_days"] == 504).sum()), int(g["thr_insufficient"].sum()),
               t["p90_median"], t["p90_min"], t["p90_max"], c90, ne))
    add("")
    add("合計:宇宙內 %d;過門檻 %d;入口池 %d(池另要求稿內收入、非盤中、歷史季度已公開、"
        "適用性 F、非金融業等條件)。"
        % (df["in_universe"].sum(), int((df["pass_p90"] == 1).sum()), len(ep)))
    add("")
    add("窗內事件少於 300 宗者改用 504 日窗;本次建池**沒有**任何一宗需要改用 504 日"
        "(全部窗都有 300 宗以上)。2014 為暖身年,窗內事件不足"
        "(門檻資料不足 %d 宗),該年不入池。" % th.get("2014", {}).get("insufficient", 0))
    add("")
    add("窗口內事件數(全部事件,`thr_n` 欄):中位 %.0f、最小 %.0f、最大 %.0f;"
        "改用 504 日窗口的事件 %d 宗;門檻資料不足 %d 宗。"
        % (w["thr_n"].median(), w["thr_n"].min(), w["thr_n"].max(),
           int((w["thr_win_days"] == 504).sum()), int(w["thr_insufficient"].sum())))
    add("")
    a2 = HERE.parent / "A2" / "thresholds.md"
    add("對照:A2(v1.1,成交額門檻 1,000 萬、宇宙與入口池另建)的宇宙內事件數與同年門檻見")
    add("`../A2/thresholds.md`;**兩版門檻定義不同(同年 vs 前 252 日),數字不可直接比**。")
    (HERE / "thresholds.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("thresholds.md 完成")

    (HERE / ".gitignore").write_text(
        "cache/\nedgar_cache/\n__pycache__/\npopulation.csv\n", encoding="utf-8")

    # population.csv 本身 100 MB 以上,照 A/A2 的做法另存 .gz 入庫(.csv 在 .gitignore)
    import gzip
    import shutil
    with (HERE / "population.csv").open("rb") as fi, \
            gzip.open(HERE / "population.csv.gz", "wb", compresslevel=6) as fo:
        shutil.copyfileobj(fi, fo)
    print("population.csv.gz:%.1f MB" % ((HERE / "population.csv.gz").stat().st_size / 1e6))
    print("→", HERE)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
