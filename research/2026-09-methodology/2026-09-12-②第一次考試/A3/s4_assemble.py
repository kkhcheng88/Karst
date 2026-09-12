# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2)第四步:合併事件、價格、XBRL、成交額、併購閘,算宇宙旗標。

與 `A2/s4_assemble.py` 之別(執行口徑 v1.2 第 5 項 (c)):
  ①併購閘**改規則**:同日 8-K 含 Item 2.01,或含 Item 1.01 **且該 8-K 正文**含
    merger / acquisition / agreement and plan of merger / acquire;
    僅 Item 1.01 而正文無併購字眼者**不剔**。舊閘(任何 Item 1.01 即剔)誤剔數另記。
      - Item 2.01:8-K 自身 items 或同日其他 8-K(由 `s4b_merger_scan.py` 掃 submissions)
      - 1.01 正文:由 `s5_fetch_text.py` 抓 primaryDocument 後,`s4c_merger_text.py` 判字眼
  ②母體含 2014(只供暖身窗口,`in_pool_window==False` 不入池);
  ③門檻改為逐事件滾動窗口(由 `s4a_thresholds.py` 另算,本支不算逐年門檻);
  ④宇宙旗標不把「疑更早公開」「訊號季收入未在稿內」「歷史季度未於 T1 前申報」
    「分析口徑不適用」等 v1.2 新閘算進去(它們在 s6/s7 由入口層處理,本支只出母體)。

輸入 cache/events_raw、price_metrics、xbrl_metrics、turnover60、merger_scan;
輸出 cache/population_base.parquet。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from buckets import bucket_of

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
MIN_DOLLAR_VOL = 10_000_000.0      # v1.1:成交額門檻 1,000 萬美元

SPAC_NAME = re.compile(r"(?:acquisition (?:corp|co|company|holdings|inc)|blank check|"
                       r"\bSPAC\b|acquisition holdings)", re.I)
MERGER_WORDS = re.compile(r"(?i)\b(?:merger|acquisition|agreement and plan of merger|acquire)")


def main() -> None:
    ev = pd.read_parquet(CACHE / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    pm = pd.read_parquet(CACHE / "price_metrics.parquet")
    xb = pd.read_parquet(CACHE / "xbrl_metrics.parquet").drop(columns=["cik"])
    to = pd.read_parquet(CACHE / "turnover60.parquet")[
        ["accessionNumber", "turnover_mean_60d", "turnover_median_60d", "n_window"]]
    df = ev.merge(pm.drop(columns=["cik"]), on="accessionNumber",
                  how="left").merge(xb, on="accessionNumber", how="left").merge(
        to, on="accessionNumber", how="left")
    df = df.reset_index(drop=True)
    df["_i"] = df.index
    print("合併後:%d 列" % len(df))

    # 代號
    tp = pd.read_parquet(ROOT / "data" / "universe" / "ticker_periods.parquet")
    ent = pd.read_parquet(ROOT / "data" / "universe" / "entities.parquet",
                          columns=["entity_id", "primary_ticker", "country",
                                   "is_foreign_filer"])
    tp["vf"] = pd.to_datetime(tp["valid_from"], errors="coerce")
    tp["vt"] = pd.to_datetime(tp["valid_to"], errors="coerce")
    j = df[["_i", "cik", "filingDate"]].merge(
        tp[["entity_id", "ticker", "vf", "vt"]], left_on="cik", right_on="entity_id", how="left")
    j["fd"] = pd.to_datetime(j["filingDate"], errors="coerce")
    j = j[(j["vf"].isna() | (j["vf"] <= j["fd"]))
          & (j["vt"].isna() | (j["vt"] >= j["fd"]))]
    j = j.sort_values("vf").drop_duplicates("_i", keep="last")
    tk = df["_i"].map(dict(zip(j["_i"], j["ticker"]))).fillna("")
    prim = dict(zip(ent["entity_id"], ent["primary_ticker"]))
    df["ticker"] = np.where(tk != "", tk, df["cik"].map(prim).fillna(""))

    df["sic"] = df["sic"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(4)
    df["sic2"] = df["sic"].str[:2]
    df["adr_flag"] = df["cik"].map(
        dict(zip(ent["entity_id"],
                 np.where(ent["is_foreign_filer"].fillna(False)
                          | ent["country"].fillna("US").ne("US"), 1, 0)))).fillna(0).astype(int)

    rx = pd.to_datetime(df["reaction_date"], errors="coerce")
    df["covid_window"] = ((rx >= "2020-03-01") & (rx <= "2020-06-30")).astype(int)
    df["year"] = rx.dt.year.astype("Int64")

    df["gate_volume"] = np.where(
        df["turnover_mean_60d"].isna(), np.nan,
        (df["turnover_mean_60d"] >= MIN_DOLLAR_VOL).astype(float))
    df["excl_volume"] = np.where(df["gate_volume"].isna(), 1,
                                 np.where(df["gate_volume"] == 1, 0, 1))
    df["excl_listed_lt_12m"] = df["listed_lt_12m"].fillna(1).astype(int)
    df["excl_spac"] = ((df["sic"] == "6770")
                       | df["name"].str.contains(SPAC_NAME, regex=True, na=False)).astype(int)
    df["excl_no_price"] = np.where(df["px_status"].fillna("") == "", 0, 1)

    # ---- 併購閘(v1.2 第 5 項 (c))
    scan_p = CACHE / "merger_scan.parquet"
    txt_p = CACHE / "merger_text.parquet"
    if not scan_p.exists():
        raise SystemExit("缺 %s:先跑 s4b_merger_scan.py" % scan_p)
    scan = pd.read_parquet(scan_p)
    # 同日(同公司同一申報日)帶 2.01 的 8-K
    d201 = scan[scan["has_2_01"] == 1]
    day201 = set(d201["cik"].astype(str) + "|" + d201["filingDate"].astype(str))
    # 同日帶 1.01 的 8-K(自身或別份)
    d101 = scan[scan["has_1_01"] == 1]
    day101 = {}
    for c, d, a in zip(d101["cik"].astype(str), d101["filingDate"].astype(str),
                       d101["accessionNumber"]):
        day101.setdefault(c + "|" + d, []).append(a)

    key = df["cik"].astype(str) + "|" + df["filingDate"].astype(str)
    # 同日(含自身)任何 8-K 帶 Item 2.01 —— scan 已含母體本身那批 8-K,故不必另判自身
    df["excl_merger_2_01"] = key.isin(day201).astype(int)

    if txt_p.exists():
        mt = pd.read_parquet(txt_p)          # accessionNumber, has_merger_words, chars, status
        mw = dict(zip(mt["accessionNumber"], mt["has_merger_words"]))
        txt_status = dict(zip(mt["accessionNumber"], mt["status"]))
        hit = np.zeros(len(df), dtype=bool)
        pending = np.zeros(len(df), dtype=bool)
        for i, k in enumerate(key.values):
            accs = day101.get(k)
            if not accs:
                continue
            flags = [mw.get(a) for a in accs]
            if any(f is True for f in flags):
                hit[i] = True
            elif any(f is None for f in flags):
                # 有 1.01 但正文未抓到 → 未能判定;保守起見記為未核(不剔),另記數
                if any(txt_status.get(a, "") not in ("ok_no_words", "ok_words")
                       for a in accs):
                    pending[i] = True
        df["excl_merger_1_01"] = hit.astype(int)
        df["merger_text_pending"] = pending.astype(int)
        # 舊閘(v1.1):任何同日 1.01 即剔 —— 只為記誤剔數
        df["excl_merger_1_01_old"] = (df["has_1_01"].fillna(0).astype(int) == 1
                                      ).astype(int) | key.isin(set(day101)).astype(int)
    else:
        # 未抓正文時:保守——暫不剔(留待抓完),但記旗標
        df["excl_merger_1_01"] = 0
        df["merger_text_pending"] = key.isin(set(day101)).astype(int)
        df["excl_merger_1_01_old"] = (df["has_1_01"].fillna(0).astype(int) == 1
                                      ).astype(int) | key.isin(set(day101)).astype(int)

    df["excl_going_concern"] = "未核"
    df["excl_merger"] = ((df["excl_merger_1_01"] == 1) | (df["excl_merger_2_01"] == 1)
                         ).astype(int)

    base_mask = ((df["excl_no_price"] == 0) & (df["excl_volume"] == 0)
                 & (df["excl_listed_lt_12m"] == 0) & (df["excl_spac"] == 0)
                 & (df["excl_merger"] == 0))
    df["in_universe"] = base_mask.astype(int)
    df["in_pool_window"] = df["filingDate"].astype(str) >= "2015-01-01"
    df["in_universe_pool"] = (df["in_universe"] & df["in_pool_window"]).astype(int)

    df["bucket"] = df["sic2"].map(bucket_of)
    n = df.groupby("cik").size()
    df["repeat_company_flag"] = df["cik"].map(n).gt(1).astype(int)

    df.to_parquet(CACHE / "population_base.parquet", index=False)
    print("in_universe:%d;其中入池窗口內(2015+):%d"
          % (df["in_universe"].sum(), df["in_universe_pool"].sum()))
    print("併購閘:2.01 %d;1.01 正文字眼 %d;正文待抓 %d;舊閘(v1.1)剔 %d"
          % (df["excl_merger_2_01"].sum(), df["excl_merger_1_01"].sum(),
             df["merger_text_pending"].sum(), df["excl_merger_1_01_old"].sum()))
    print("→", CACHE / "population_base.parquet")

    summary = {
        "rows": int(len(df)),
        "in_universe": int(df["in_universe"].sum()),
        "in_universe_pool": int(df["in_universe_pool"].sum()),
        "excl_merger_2_01": int(df["excl_merger_2_01"].sum()),
        "excl_merger_1_01_text": int(df["excl_merger_1_01"].sum()),
        "merger_text_pending": int(df["merger_text_pending"].sum()),
        "excl_merger_1_01_old_gate": int(df["excl_merger_1_01_old"].sum()),
        "by_year_universe": {str(int(y)): int(v) for y, v in
                             df[df["in_universe"] == 1].groupby("year").size().items()
                             if not pd.isna(y)},
    }
    (CACHE / "s4_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
