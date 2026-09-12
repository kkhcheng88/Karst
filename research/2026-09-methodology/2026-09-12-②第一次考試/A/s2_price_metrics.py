# -*- coding: utf-8 -*-
"""KARST-222 票 A 第二步:接日線,算三時點、反應報酬、宇宙門檻、上市月齡。

只讀 `data/prices/`、`data/universe/`;輸出 `A/cache/price_metrics.parquet`。

口徑:
  - 主日線 = series_role == "primary"(與 scan_forced_selling.py / basket_core.py 同)。
  - 交易日曆 = SPY 有報價的日期(唯一權威)。
  - 反應日: T0(美東)當日為交易日且時間 ≤ 16:00 → 當日;否則 T0 之後首個交易日。
  - 反應報酬 = 反應日 adj_close 對「反應日前最後一個交易日」adj_close − 1。
  - 相對 SPY = 個股反應報酬 − SPY 同日報酬;相對同業 = 個股反應報酬
    − 同日同 SIC 兩位數全部有報價公司的報酬中位數。
  - 宇宙門檻 = 反應日前 60 個交易日(不含反應日)的 close×volume 日均 ≥ 300 萬美元。
  - 上市月齡 = 反應日 − 該公司在整個日線庫的首個報價日(不分 primary/alias)。
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
PRICES = ROOT / "data" / "prices" / "daily"
SPY_CSV = ROOT / "data" / "prices" / "spy_daily.csv"
ENT = ROOT / "data" / "universe" / "entities.parquet"

PX_FROM = "2013-06-01"   # 2015-01-01 事件要回看 60 個交易日
MIN_DOLLAR_VOL = 3_000_000.0
VOL_WINDOW = 60


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)

    # ---- SPY 交易日曆與報酬
    spy = pd.read_csv(SPY_CSV, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    spy["spy_ret"] = spy["adj_close"].pct_change()
    spy_dates = spy["date"].values.astype("datetime64[D]")
    spy_map = dict(zip(spy_dates, spy["spy_ret"].values))

    # ---- 主日線
    frames = []
    for p in sorted(PRICES.glob("part_*.parquet")):
        d = pd.read_parquet(p, columns=["entity_id", "date", "adj_close", "close",
                                        "volume", "series_role"])
        d["date"] = pd.to_datetime(d["date"])
        d = d[(d["series_role"] == "primary") & (d["date"] >= PX_FROM)]
        frames.append(d[["entity_id", "date", "adj_close", "close", "volume"]])
    px = pd.concat(frames, ignore_index=True)
    del frames
    print("窗口內主日線列數:%d,公司數:%d" % (len(px), px["entity_id"].nunique()), flush=True)
    px = px.dropna(subset=["adj_close"]).sort_values(["entity_id", "date"], kind="stable")
    px = px.reset_index(drop=True)

    ent = pd.read_parquet(ENT, columns=["entity_id", "sic"])
    ent["sic2"] = ent["sic"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(4).str[:2]
    px = px.merge(ent[["entity_id", "sic2"]], on="entity_id", how="left")
    px["sic2"] = px["sic2"].fillna("")
    px["ret"] = px.groupby("entity_id", sort=False)["adj_close"].pct_change()
    px["dvol"] = px["close"] * px["volume"]

    sic2_med = (px[px["sic2"] != ""].groupby(["date", "sic2"])["ret"].median()
                .rename("sic2_ret_med").reset_index())
    print("同日同 SIC2 中位數列數:%d" % len(sic2_med), flush=True)
    sic2_med_map = {(d, s): float(v) for d, s, v in
                    zip(sic2_med["date"].values.astype("datetime64[D]"),
                        sic2_med["sic2"].values, sic2_med["sic2_ret_med"].values)
                    if pd.notna(v)}
    sic2_of = dict(zip(ent["entity_id"], ent["sic2"]))

    # ---- 每公司陣列
    dates_arr: dict[str, np.ndarray] = {}
    adj_arr: dict[str, np.ndarray] = {}
    dvol_arr: dict[str, np.ndarray] = {}
    for eid, g in px.groupby("entity_id", sort=False):
        dates_arr[eid] = g["date"].values.astype("datetime64[D]")
        adj_arr[eid] = g["adj_close"].to_numpy(dtype="float64")
        dvol_arr[eid] = g["dvol"].to_numpy(dtype="float64")
    del px

    # ---- 上市月齡:整個日線庫首個報價日(不分 series_role)
    first_seen: dict[str, np.datetime64] = {}
    for p in sorted(PRICES.glob("part_*.parquet")):
        d = pd.read_parquet(p, columns=["entity_id", "date"])
        s = d.groupby("entity_id")["date"].min()
        for eid, v in s.items():
            v = np.datetime64(v, "D")
            if eid not in first_seen or v < first_seen[eid]:
                first_seen[eid] = v
        del d

    # ---- 逐事件
    ev = pd.read_parquet(CACHE / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    print("事件(去重後):%d" % len(ev), flush=True)

    t0 = pd.to_datetime(ev["t0_et"], format="%Y-%m-%dT%H:%M:%S", errors="coerce")
    t0_date = t0.dt.normalize().values.astype("datetime64[D]")
    after16 = ev["t0_after16"].to_numpy(dtype=int)

    out = []
    for k in range(len(ev)):
        eid = ev["cik"].iat[k]
        acc = ev["accessionNumber"].iat[k]
        if eid not in dates_arr or np.isnat(t0_date[k]):
            out.append(dict(accessionNumber=acc, cik=eid, px_status="無日線或無 T0 時間",
                            reaction_date="",
                            prev_date="", t2_date="", ret=None, rel_spy=None, rel_sic2=None,
                            dvol_med_60=None, gate_volume=None, first_px_date="",
                            listed_months=None, listed_lt_12m=None))
            continue
        dd = t0_date[k]
        # 反應日:T0 美東日若為交易日且不遲於 16:00 → 同一日;否則下一個交易日
        pos = np.searchsorted(spy_dates, dd, side="left")
        same_day = pos < len(spy_dates) and spy_dates[pos] == dd
        if same_day and after16[k] == 0:
            react = dd
        else:
            np_ = pos + 1 if same_day else pos
            react = spy_dates[np_] if np_ < len(spy_dates) else np.datetime64("NaT")
        if np.isnat(react):
            out.append(dict(accessionNumber=acc, cik=eid, px_status="T0 晚於日線覆蓋",
                            reaction_date="",
                            prev_date="", t2_date="", ret=None, rel_spy=None, rel_sic2=None,
                            dvol_med_60=None, gate_volume=None, first_px_date="",
                            listed_months=None, listed_lt_12m=None))
            continue
        rpos = int(np.searchsorted(spy_dates, react))
        prev = spy_dates[rpos - 1] if rpos >= 1 else np.datetime64("NaT")
        t2 = spy_dates[rpos + 1] if rpos + 1 < len(spy_dates) else np.datetime64("NaT")

        da, ad, dv = dates_arr[eid], adj_arr[eid], dvol_arr[eid]
        i = int(np.searchsorted(da, react, side="right")) - 1
        status = ""
        ret = rel_spy = rel_sic2 = None
        if i < 0 or da[i] != react:
            status = "反應日無該公司報價"
        elif np.isnat(prev):
            status = "反應日前無交易日"
        else:
            j = int(np.searchsorted(da, prev, side="right")) - 1
            if j < 0:
                status = "反應日前無該公司報價"
            else:
                ret = float(ad[i] / ad[j] - 1.0)
                sr = spy_map.get(react)
                if sr is not None and not (isinstance(sr, float) and np.isnan(sr)):
                    rel_spy = ret - float(sr)
                m = sic2_med_map.get((react, sic2_of.get(eid, "")))
                if m is not None:
                    rel_sic2 = ret - m

        # 宇宙門檻:反應日前 60 個交易日(不含反應日)
        gate = None
        med = None
        if i >= VOL_WINDOW:
            w = dv[i - VOL_WINDOW:i]
            med = float(np.nanmean(w)) if len(w) else None
            if med is not None:
                gate = int(med >= MIN_DOLLAR_VOL)
        fs = first_seen.get(eid)
        listed = None
        lt12 = None
        if fs is not None:
            listed = round((react.astype("datetime64[D]") - fs) / np.timedelta64(1, "D") / 30.4375, 2)
            lt12 = int(listed < 12.0)

        out.append(dict(accessionNumber=acc, cik=eid, px_status=status,
                        reaction_date=str(react),
                        prev_date="" if np.isnat(prev) else str(prev),
                        t2_date="" if np.isnat(t2) else str(t2),
                        ret=ret, rel_spy=rel_spy, rel_sic2=rel_sic2,
                        dvol_med_60=med, gate_volume=gate,
                        first_px_date="" if fs is None else str(fs),
                        listed_months=listed, listed_lt_12m=lt12))
        if (k + 1) % 20000 == 0:
            print("  ...%d/%d" % (k + 1, len(ev)), flush=True)

    pm = pd.DataFrame(out)
    pm.to_parquet(CACHE / "price_metrics.parquet", index=False)
    print("接得上日線:%d / %d" % ((pm["px_status"] == "").sum(), len(pm)))
    print("宇宙門檻過:%d;未過:%d;視窗不足:%d" % (
        (pm["gate_volume"] == 1).sum(), (pm["gate_volume"] == 0).sum(),
        pm["gate_volume"].isna().sum()))
    print("上市不足十二個月:%d" % (pm["listed_lt_12m"] == 1).sum())
    print("px_status 分佈:", pm["px_status"].value_counts().to_dict())
    print("→", CACHE / "price_metrics.parquet")


if __name__ == "__main__":
    main()
