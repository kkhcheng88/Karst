# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2)第二步:接日線,算 T0/反應日/反應報酬/宇宙門檻/上市月齡。

與 `A/s2_price_metrics.py` 之別(執行口徑 v1.2 第 1、2 項):
  ①母體含 2014(只作暖身窗口);
  ②T0 加入 **EX-99.1 稿頭日期**(`cache/dateline.parquet`,由 `s2b_dateline.py` 產生):
    稿頭日期 < 申報日 → 視作稿頭日收市後公開,反應日 = 稿頭日**次一交易日**;
    否則沿用 8-K 受理時間規則。`t0_source` 記「8-K」或「稿頭」。
    稿頭日期缺者一律沿用 8-K 規則(記 `dateline_used=False`,執行紀錄報覆蓋率)。
  ③新增 `prior_day_abs_ret`:反應日前一交易日的**絕對報酬**;> 8% 標
    `suspect_earlier_release=1`(由下游剔出池,記數)。
  ④新增標籤用價格狀態(v1.2 第 6 項;只記狀態,不作閘):`ma200`、`above_200dma`、
    `rs6`(反應日前 21 至 147 個交易日的相對 SPY 報酬,即跳過最近一個月)。

只讀 `data/prices/`、`data/universe/`、`cache/events_raw.parquet`、`cache/dateline.parquet`;
輸出 `cache/price_metrics.parquet`。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
PRICES = ROOT / "data" / "prices" / "daily"
SPY_CSV = ROOT / "data" / "prices" / "spy_daily.csv"
ENT = ROOT / "data" / "universe" / "entities.parquet"

PX_FROM = "2013-06-01"   # 2014-01 事件要回看 60 個交易日,2015-01 事件的 252 日窗口要回看一年
MIN_DOLLAR_VOL = 3_000_000.0
VOL_WINDOW = 60
PRIOR_ABS_RET_CUT = 0.08
MA_LONG = 200          # 長期均線
RS6_LOOKBACK = 126     # 六個月
RS6_SKIP = 21          # 跳過最近一個月


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)

    # ---- SPY 交易日曆與報酬(唯一權威)
    spy = pd.read_csv(SPY_CSV, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    spy["spy_ret"] = spy["adj_close"].pct_change()
    spy_dates = spy["date"].values.astype("datetime64[D]")
    spy_map = dict(zip(spy_dates, spy["spy_ret"].values))
    spy_adj = spy["adj_close"].to_numpy(dtype="float64")

    # ---- 主日線(逐檔讀,不一次入記憶體)
    frames = []
    for p in sorted(PRICES.glob("part_*.parquet")):
        d = pd.read_parquet(p, columns=["entity_id", "date", "adj_close", "open", "close",
                                        "volume", "series_role"])
        d["date"] = pd.to_datetime(d["date"])
        d = d[(d["series_role"] == "primary") & (d["date"] >= PX_FROM)]
        frames.append(d[["entity_id", "date", "adj_close", "open", "close", "volume"]])
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

    dates_arr: dict[str, np.ndarray] = {}
    adj_arr: dict[str, np.ndarray] = {}
    dvol_arr: dict[str, np.ndarray] = {}
    open_arr: dict[str, np.ndarray] = {}
    close_arr: dict[str, np.ndarray] = {}
    for eid, g in px.groupby("entity_id", sort=False):
        dates_arr[eid] = g["date"].values.astype("datetime64[D]")
        adj_arr[eid] = g["adj_close"].to_numpy(dtype="float64")
        dvol_arr[eid] = g["dvol"].to_numpy(dtype="float64")
        open_arr[eid] = g["open"].to_numpy(dtype="float64")
        close_arr[eid] = g["close"].to_numpy(dtype="float64")
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

    # ---- 稿頭日期(v1.2 新增)
    dl_path = CACHE / "dateline.parquet"
    dl_map: dict[str, str] = {}
    if dl_path.exists():
        dl = pd.read_parquet(dl_path)
        dl = dl[dl["dateline"].fillna("") != ""]
        dl_map = dict(zip(dl["accessionNumber"], dl["dateline"]))
    print("有稿頭日期的事件:%d" % len(dl_map), flush=True)

    # ---- 逐事件
    ev = pd.read_parquet(CACHE / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    print("事件(去重後):%d" % len(ev), flush=True)

    t0 = pd.to_datetime(ev["t0_et"], format="%Y-%m-%dT%H:%M:%S", errors="coerce")
    t0_date = t0.dt.normalize().values.astype("datetime64[D]")
    t0_mins = (t0.dt.hour * 60 + t0.dt.minute).to_numpy(dtype="float64")   # 美東分鐘數
    after16 = ev["t0_after16"].to_numpy(dtype=int)
    PRE_930 = 9 * 60 + 30
    AT_1600 = 16 * 60

    out = []
    for k in range(len(ev)):
        eid = ev["cik"].iat[k]
        acc = ev["accessionNumber"].iat[k]
        fd = ev["filingDate"].iat[k]
        if eid not in dates_arr or np.isnat(t0_date[k]):
            out.append(dict(accessionNumber=acc, cik=eid, px_status="無日線或無 T0 時間",
                            reaction_date="", reaction_date_8k="", t0_source="8-K",
                            release_timing="", dateline_used=False, dateline="",
                            prev_date="", t2_date="", ret=None, rel_spy=None, rel_sic2=None,
                            prior_day_abs_ret=None, suspect_earlier_release=0,
                            dvol_med_60=None, gate_volume=None, first_px_date="",
                            listed_months=None, listed_lt_12m=None))
            continue
        dd = t0_date[k]
        pos = np.searchsorted(spy_dates, dd, side="left")
        same_day = pos < len(spy_dates) and spy_dates[pos] == dd
        if same_day and after16[k] == 0:
            react8 = dd
        else:
            np_ = pos + 1 if same_day else pos
            react8 = spy_dates[np_] if np_ < len(spy_dates) else np.datetime64("NaT")

        # ---- 首次公開時間(v1.2 第 2 項 + 補二)
        #   稿頭日期 < 申報日 → 稿頭日收市後公開,反應日 = 稿頭日次一交易日
        #   稿頭日期 = 申報日 → 按 8-K 受理時間(美東):<09:30 盤前當日;≥16:00 盤後次日;
        #                        09:30–16:00 → 開市跳空判:≥ 收市變動一半且同向 → 盤前(推斷);
        #                        否則盤中(intraday,不入池)
        #   無稿頭日期 → 沿用 8-K 受理時間,09:30–16:00 者標 undetermined
        dl = dl_map.get(acc, "")
        used = False
        timing = ""
        react = react8
        tm = t0_mins[k]
        if dl and dl < str(fd):
            npd = np.datetime64(dl, "D")
            p2 = int(np.searchsorted(spy_dates, npd, side="right"))
            if p2 < len(spy_dates):
                react = spy_dates[p2]
                used = True
                timing = "prior_day_after_close"
            else:
                timing = "prior_day_after_close(日線外)"
        elif dl and dl == str(fd):
            used = True
            if tm < PRE_930:
                timing = "pre_market"
                react = dd if same_day else react8
            elif tm >= AT_1600:
                timing = "after_close"
                react = react8
            else:
                # 開市跳空判(用未還原開市價對上一交易日未還原收市價)
                gap = dayret = None
                da, op, cl = dates_arr[eid], open_arr[eid], close_arr[eid]
                jd = int(np.searchsorted(da, dd, side="right")) - 1
                if jd >= 1 and da[jd] == dd:
                    pc = cl[jd - 1]
                    if pc and pc > 0 and not np.isnan(pc):
                        if not np.isnan(op[jd]):
                            gap = op[jd] / pc - 1.0
                        if not np.isnan(cl[jd]):
                            dayret = cl[jd] / pc - 1.0
                if (gap is not None and dayret is not None and dayret != 0.0
                        and abs(gap) >= 0.5 * abs(dayret) and (gap > 0) == (dayret > 0)):
                    timing = "pre_market_inferred"
                    react = dd
                else:
                    timing = "intraday"
                    react = dd
        else:
            # 無稿頭日期(無文本):沿用 8-K 受理時間;09:30–16:00 者無法分辨 → undetermined
            if tm < PRE_930:
                timing, react = "pre_market_8k", (dd if same_day else react8)
            elif tm >= AT_1600:
                timing, react = "after_close_8k", react8
            else:
                timing, react = "undetermined", react8
        t0src = "稿頭" if used else "8-K"

        if np.isnat(react):
            out.append(dict(accessionNumber=acc, cik=eid, px_status="T0 晚於日線覆蓋",
                            reaction_date="", reaction_date_8k="", t0_source=t0src,
                            release_timing=timing, dateline_used=used, dateline=dl,
                            prev_date="", t2_date="", ret=None, rel_spy=None, rel_sic2=None,
                            prior_day_abs_ret=None, suspect_earlier_release=0,
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
        prior_abs = None
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
                # 反應日前一交易日的絕對報酬(該公司自己序列)
                if j >= 1:
                    prior_abs = float(abs(ad[j] / ad[j - 1] - 1.0))

        gate = None
        med = None
        if i >= VOL_WINDOW:
            w = dv[i - VOL_WINDOW:i]
            med = float(np.nanmean(w)) if len(w) else None
            if med is not None:
                gate = int(med >= MIN_DOLLAR_VOL)

        # ---- 價格狀態(v1.2 第 6 項標籤;只記狀態,不作閘)
        ma200 = None
        if i + 1 >= MA_LONG:
            w200 = ad[i - MA_LONG + 1:i + 1]
            if len(w200) == MA_LONG and not np.isnan(w200).any():
                ma200 = float(w200.mean())
        above200 = int(ad[i] > ma200) if (ma200 is not None and ma200 > 0) else None
        rs6 = None
        k1 = i - RS6_SKIP
        k0 = k1 - RS6_LOOKBACK
        if k0 >= 0:
            q0 = int(np.searchsorted(spy_dates, da[k0]))
            q1s = int(np.searchsorted(spy_dates, da[k1]))
            if (q0 < len(spy_dates) and q1s < len(spy_dates)
                    and spy_dates[q0] == da[k0] and spy_dates[q1s] == da[k1]
                    and ad[k0] > 0 and spy_adj[q0] > 0):
                sr6 = float(spy_adj[q1s] / spy_adj[q0] - 1.0)
                rs6 = float(ad[k1] / ad[k0] - 1.0) - sr6

        fs = first_seen.get(eid)
        listed = None
        lt12 = None
        if fs is not None:
            listed = round((react.astype("datetime64[D]") - fs) / np.timedelta64(1, "D") / 30.4375, 2)
            lt12 = int(listed < 12.0)

        out.append(dict(accessionNumber=acc, cik=eid, px_status=status,
                        reaction_date=str(react),
                        reaction_date_8k="" if np.isnat(react8) else str(react8),
                        t0_source=t0src, release_timing=timing,
                        dateline_used=used, dateline=dl,
                        prev_date="" if np.isnat(prev) else str(prev),
                        t2_date="" if np.isnat(t2) else str(t2),
                        ret=ret, rel_spy=rel_spy, rel_sic2=rel_sic2,
                        prior_day_abs_ret=prior_abs,
                        suspect_earlier_release=int(prior_abs is not None
                                                    and prior_abs > PRIOR_ABS_RET_CUT),
                        dvol_med_60=med, gate_volume=gate,
                        ma200=ma200, above_200dma=above200, rs6=rs6,
                        first_px_date="" if fs is None else str(fs),
                        listed_months=listed, listed_lt_12m=lt12))
        if (k + 1) % 20000 == 0:
            print("  ...%d/%d" % (k + 1, len(ev)), flush=True)

    pm = pd.DataFrame(out)
    pm.to_parquet(CACHE / "price_metrics.parquet", index=False)
    n_shift = int(((pm["dateline_used"]) & (pm["reaction_date"] != pm["reaction_date_8k"])).sum())
    print("接得上日線:%d / %d" % ((pm["px_status"] == "").sum(), len(pm)))
    print("用稿頭日改反應日者:%d(其中反應日真的變了 %d)" % (
        int(pm["dateline_used"].sum()), n_shift))
    print("宇宙門檻過:%d;未過:%d;視窗不足:%d" % (
        (pm["gate_volume"] == 1).sum(), (pm["gate_volume"] == 0).sum(),
        pm["gate_volume"].isna().sum()))
    print("上市不足十二個月:%d;疑更早公開(前一日|報酬|>8%%):%d" % (
        (pm["listed_lt_12m"] == 1).sum(), int(pm["suspect_earlier_release"].sum())))
    print("release_timing 分佈:", pm["release_timing"].value_counts(dropna=False).to_dict())
    print("px_status 分佈:", pm["px_status"].value_counts().to_dict())
    print("→", CACHE / "price_metrics.parquet")


if __name__ == "__main__":
    main()
