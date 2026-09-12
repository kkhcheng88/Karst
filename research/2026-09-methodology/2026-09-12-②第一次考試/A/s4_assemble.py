# -*- coding: utf-8 -*-
"""KARST-222 票 A 第四步:合併事件、價格、XBRL,計宇宙/排除旗標與逐年百分位門檻。

輸入 cache/events_raw、price_metrics、xbrl_metrics;輸出 cache/population_base.parquet
與 cache/thresholds.json(逐年 90/95/80 百分位門檻與事件數)。

排除欄(逐欄記狀態):
  - excl_volume        反應日前 60 個交易日日均成交額 < 300 萬美元
  - excl_listed_lt_12m 上市不足十二個月
  - excl_spac          SIC 6770(空白支票)或名稱含 SPAC/Acquisition Corp 等
  - excl_merger_1_01   同日 8-K 含 Item 1.01(併購協議的代理旗標,**需文本覆核**)
  - excl_going_concern 需文本,母體層標「未核」,抽中者在取證包階段核
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

SPAC_NAME = re.compile(r"(?:acquisition (?:corp|co|company|holdings|inc)|blank check|"
                       r"\bSPAC\b|acquisition holdings)", re.I)



def main() -> None:
    ev = pd.read_parquet(CACHE / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    pm = pd.read_parquet(CACHE / "price_metrics.parquet")
    xb = pd.read_parquet(CACHE / "xbrl_metrics.parquet").drop(columns=["cik"])
    df = ev.merge(pm.drop(columns=["cik"]), on="accessionNumber",
                  how="left").merge(xb, on="accessionNumber", how="left")
    df = df.reset_index(drop=True)
    df["_i"] = df.index
    print("合併後:%d 列" % len(df))

    # 代號:優先用事件 cik 對應的 primary/歷史代號
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
    df["cluster_id"] = df["sic2"] + "-" + rx.dt.year.astype("Int64").astype(str) + "Q" + \
        rx.dt.quarter.astype("Int64").astype(str)
    df["year"] = rx.dt.year.astype("Int64")

    df["excl_volume"] = np.where(df["gate_volume"].isna(), 1,
                                 np.where(df["gate_volume"] == 1, 0, 1))
    df["excl_listed_lt_12m"] = df["listed_lt_12m"].fillna(1).astype(int)
    df["excl_spac"] = ((df["sic"] == "6770")
                       | df["name"].str.contains(SPAC_NAME, regex=True, na=False)).astype(int)
    # 同日 8-K Item 1.01:同一份帶 1.01,或同公司同一日另有 8-K 帶 1.01(s4b 補掃)
    md = pd.read_parquet(CACHE / "merger_days.parquet")
    mset = set(md["cik"].astype(str) + "|" + md["filingDate"].astype(str))
    key = df["cik"].astype(str) + "|" + df["filingDate"].astype(str)
    df["excl_merger_1_01"] = ((df["has_1_01"].fillna(0).astype(int) == 1)
                              | key.isin(mset)).astype(int)
    df["excl_going_concern"] = "未核"
    df["excl_no_price"] = np.where(df["px_status"].fillna("") == "", 0, 1)

    base_mask = ((df["excl_no_price"] == 0) & (df["excl_volume"] == 0)
                 & (df["excl_listed_lt_12m"] == 0) & (df["excl_spac"] == 0)
                 & (df["excl_merger_1_01"] == 0))
    df["in_universe"] = base_mask.astype(int)

    # ---- 逐年百分位門檻(以 in_universe 且 rel_spy 有值者為底)
    th: dict[str, dict] = {}
    for y, g in df[df["in_universe"] == 1].groupby("year"):
        v = g["rel_spy"].dropna().to_numpy()
        if not len(v):
            continue
        th[str(int(y))] = {
            "n": int(len(v)),
            "p90": float(np.percentile(v, 90)),
            "p95": float(np.percentile(v, 95)),
            "p80": float(np.percentile(v, 80)),
        }
    (CACHE / "thresholds.json").write_text(json.dumps(th, indent=1, ensure_ascii=False),
                                           encoding="utf-8")
    p90 = df["year"].astype(str).map({k: v["p90"] for k, v in th.items()})
    p95 = df["year"].astype(str).map({k: v["p95"] for k, v in th.items()})
    p80 = df["year"].astype(str).map({k: v["p80"] for k, v in th.items()})
    inu = df["in_universe"] == 1
    df["pass_p90"] = (inu & (df["rel_spy"] >= p90) & (df["rel_sic2"] > 0)).fillna(False).astype(int)
    df["pass_p95"] = (inu & (df["rel_spy"] >= p95) & (df["rel_sic2"] > 0)).fillna(False).astype(int)
    df["pass_p80"] = (inu & (df["rel_spy"] >= p80) & (df["rel_sic2"] > 0)).fillna(False).astype(int)

    df["bucket"] = df["sic2"].map(bucket_of)
    n = df.groupby("cik").size()
    df["repeat_company_flag"] = df["cik"].map(n).gt(1).astype(int)

    df.to_parquet(CACHE / "population_base.parquet", index=False)
    print("in_universe:%d;pass_p90:%d;pass_p95:%d;pass_p80:%d" % (
        df["in_universe"].sum(), df["pass_p90"].sum(), df["pass_p95"].sum(),
        df["pass_p80"].sum()))
    print("accelerated(≥2pp)且在宇宙內:%d;其中 pass_p90:%d" % (
        ((df["accel_hit"] == 1) & (df["in_universe"] == 1)).sum(),
        ((df["accel_hit"] == 1) & (df["pass_p90"] == 1)).sum()))
    print("逐年門檻:", json.dumps({k: {kk: round(vv, 4) if isinstance(vv, float) else vv
                                      for kk, vv in v.items()} for k, v in th.items()},
                                 ensure_ascii=False))
    print("桶分佈(宇宙內):", df[df["in_universe"] == 1]["bucket"].value_counts().to_dict())
    print("→", CACHE / "population_base.parquet")


if __name__ == "__main__":
    main()
