# -*- coding: utf-8 -*-
"""KARST-187 ①錯殺注基準率表:事件表建構。

事件定義(可觀察,不含「錯殺」這個判斷):
  某日收市價相對 SPY 過去 60 個交易日跌幅 >= 25%(總回報口徑,兩邊都用 adj_close);
  同一公司 120 個交易日內只計首次觸發。

觸發日當時「已公布」的最近季度須過兩閘:
  負債閘 A(N2):現金 - 總債務 >= 0
  負債閘 B:總債務 / 過去四季經營現金流 <= 3
  現金流閘:過去四季經營現金流 > 0
  市值閘:股數(觸發日前最近一次封面頁) x 觸發日收市價 >= 5 億美元

知情時點是硬約束:面板每一格用的 `<欄>_filed` 與列層 `filed_date` 全部必須 <= 觸發日,
腳本內有斷言,違反即拋錯(見 assert_knowledge_time)。

輸出:out/events.csv、out/build_stats.json、out/gate_funnel.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

PRICES = ROOT / "data" / "prices" / "daily"
PANEL = ROOT / "data" / "panel" / "quarterly_v3.parquet"
ENTITIES = ROOT / "data" / "universe" / "entities.parquet"
SPY_CSV = ROOT / "data" / "prices" / "spy_daily.csv"

LOOKBACK = 60          # 觸發窗:60 個交易日
DROP_THRESHOLD = -0.25  # 相對 SPY 跌幅門檻
COOLDOWN = 120         # 同一公司再次觸發的最短間隔(交易日)
MIN_HISTORY = 250      # 觸發日之前至少要有 250 根日線(250 日線要算得出)
MAX_GAP_DAYS = 120     # 60 根日線之間的日曆天數上限,超過即當資料斷層不計
MIN_MCAP = 500e6
IND_KILL_THRESHOLD = -0.15  # 同業中位跌幅門檻
MIN_PEERS = 5
SEARCH_WINDOW = 126    # 尋找「跌勢衰竭」「買方回來」的最長等待(交易日)
EXHAUST_DAYS = 10      # 連續 10 個交易日不再創新低
HORIZONS = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}
PANEL_STALE_DAYS = 400  # 面板季度距觸發日的最長容忍
TTM_SPAN_DAYS = 450     # 四季 TTM 的期末跨度上限


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------- 讀價格
def load_prices() -> pd.DataFrame:
    parts = sorted(PRICES.glob("part_*.parquet"))
    cols = ["entity_id", "date", "close", "adj_close", "low", "volume", "series_role"]
    frames = []
    for p in parts:
        d = pd.read_parquet(p, columns=cols)
        d = d[d["series_role"] == "primary"].drop(columns=["series_role"])
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    for c in ("close", "adj_close", "low", "volume"):
        df[c] = df[c].astype("float32")
    df = df.dropna(subset=["adj_close", "close"])
    df = df[(df["adj_close"] > 0) & (df["close"] > 0)]
    df = df.sort_values(["entity_id", "date"], kind="stable").reset_index(drop=True)
    return df


def main() -> None:
    stats: dict[str, object] = {}

    log("[1/7] 讀 SPY")
    spy = pd.read_csv(SPY_CSV, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    spy = spy[["date", "adj_close"]].rename(columns={"adj_close": "spy_adj"})
    spy_dates = spy["date"].to_numpy()
    spy_adj = spy["spy_adj"].to_numpy(dtype="float64")
    stats["spy_first"] = str(spy["date"].iloc[0].date())
    stats["spy_last"] = str(spy["date"].iloc[-1].date())

    log("[2/7] 讀日線價格庫(只取 series_role=primary)")
    px = load_prices()
    stats["price_rows_primary"] = int(len(px))
    stats["price_entities"] = int(px["entity_id"].nunique())
    px = px.merge(spy, on="date", how="inner")   # 只留 SPY 有報價的交易日
    px = px.sort_values(["entity_id", "date"], kind="stable").reset_index(drop=True)
    stats["price_rows_on_spy_calendar"] = int(len(px))
    stats["price_last_date"] = str(px["date"].max().date())

    # 每一列在該實體序列內的位置
    g = px.groupby("entity_id", sort=False)
    px["idx"] = g.cumcount()
    px["n_rows"] = g["date"].transform("size")

    # 全域 rolling / shift 再按 idx 作廢跨實體的那幾列(資料已按實體+日期排好)
    rel = px["adj_close"].astype("float64") / px["spy_adj"]
    px["rel60"] = (rel / rel.shift(LOOKBACK) - 1.0).astype("float32")
    px["ret60_abs"] = (px["adj_close"].astype("float64") / px["adj_close"].astype("float64").shift(LOOKBACK) - 1.0).astype("float32")
    gap = (px["date"] - px["date"].shift(LOOKBACK)).dt.days
    bad = px["idx"] < LOOKBACK
    px.loc[bad, ["rel60", "ret60_abs"]] = np.nan
    gap[bad] = np.nan
    px["gap60"] = gap

    a = px["adj_close"].astype("float64")
    for w in (50, 200, 250):
        m = a.rolling(w).mean()
        m[px["idx"] < (w - 1)] = np.nan
        px[f"sma{w}"] = m.astype("float32")

    log("[3/7] 讀實體表,算行業中位跌幅")
    ent = pd.read_parquet(ENTITIES, columns=["entity_id", "name", "primary_ticker", "sic",
                                             "sic_description", "is_foreign_filer",
                                             "filing_status", "approx_mcap_usd"])
    ent["sic2"] = ent["sic"].astype("string").str.zfill(4).str[:2]
    ent.loc[ent["sic"].isna() | (ent["sic"].astype("string") == ""), "sic2"] = pd.NA
    px = px.merge(ent[["entity_id", "sic2"]], on="entity_id", how="left")

    ind = (px.dropna(subset=["rel60", "sic2"])
             .groupby(["date", "sic2"], observed=True)
             .agg(ind_med_rel=("rel60", "median"),
                  ind_med_abs=("ret60_abs", "median"),
                  ind_n=("rel60", "size"))
             .reset_index())
    stats["industry_median_cells"] = int(len(ind))

    log("[4/7] 掃觸發")
    cand = px[(px["rel60"] <= DROP_THRESHOLD)
              & (px["idx"] >= MIN_HISTORY)
              & (px["gap60"] <= MAX_GAP_DAYS)].copy()
    stats["raw_candidate_rows"] = int(len(cand))

    # 每個實體的 numpy 陣列(供事件層逐筆計算)
    ent_slices: dict[str, tuple[int, int]] = {}
    eid = px["entity_id"].to_numpy()
    start = 0
    for i in range(1, len(eid) + 1):
        if i == len(eid) or eid[i] != eid[start]:
            ent_slices[eid[start]] = (start, i)
            start = i

    dates_all = px["date"].to_numpy()
    adj_all = px["adj_close"].to_numpy(dtype="float64")
    close_all = px["close"].to_numpy(dtype="float64")
    low_all = px["low"].to_numpy(dtype="float64")
    vol_all = px["volume"].to_numpy(dtype="float64")
    sma50_all = px["sma50"].to_numpy(dtype="float64")
    sma200_all = px["sma200"].to_numpy(dtype="float64")
    sma250_all = px["sma250"].to_numpy(dtype="float64")
    spy_pos_all = np.searchsorted(spy_dates, dates_all)

    # 觸發:同一公司 120 個交易日(以大市日曆計)內只計首觸發
    triggers = []
    for e, sub in cand.groupby("entity_id", sort=False):
        pos = sub.index.to_numpy()
        last_spy = -10**9
        for p in pos:
            sp = spy_pos_all[p]
            if sp - last_spy < COOLDOWN:
                continue
            last_spy = sp
            triggers.append(p)
    triggers = np.array(sorted(triggers), dtype="int64")
    stats["triggers_after_cooldown"] = int(len(triggers))

    log(f"      原始觸發列 {stats['raw_candidate_rows']:,} → 冷卻後 {len(triggers):,}")

    log("[5/7] 讀面板 v3(知情時點欄位)")
    pcols = ["entity_id", "period_end", "filed_date", "currency",
             "cash_and_equivalents", "cash_and_equivalents_filed",
             "total_debt", "total_debt_filed",
             "operating_cash_flow", "operating_cash_flow_filed", "operating_cash_flow_period",
             "shares_outstanding", "shares_outstanding_filed"]
    pan = pd.read_parquet(PANEL, columns=pcols)
    pan = pan.dropna(subset=["period_end"])
    pan = pan[(pan["period_end"] >= pd.Timestamp("1990-01-01")) &
              (pan["period_end"] <= pd.Timestamp("2026-12-31"))]
    pan = pan.sort_values(["entity_id", "period_end"], kind="stable").reset_index(drop=True)

    pan_slices: dict[str, tuple[int, int]] = {}
    peid = pan["entity_id"].to_numpy()
    s = 0
    for i in range(1, len(peid) + 1):
        if i == len(peid) or peid[i] != peid[s]:
            pan_slices[peid[s]] = (s, i)
            s = i

    p_pe = pan["period_end"].to_numpy()
    p_fd = pan["filed_date"].to_numpy()
    p_cash = pan["cash_and_equivalents"].to_numpy(dtype="float64")
    p_cash_f = pan["cash_and_equivalents_filed"].to_numpy()
    p_td = pan["total_debt"].to_numpy(dtype="float64")
    p_td_f = pan["total_debt_filed"].to_numpy()
    p_ocf = pan["operating_cash_flow"].to_numpy(dtype="float64")
    p_ocf_f = pan["operating_cash_flow_filed"].to_numpy()
    p_ocf_p = pan["operating_cash_flow_period"].astype("string").fillna("").to_numpy()
    p_sh = pan["shares_outstanding"].to_numpy(dtype="float64")
    p_sh_f = pan["shares_outstanding_filed"].to_numpy()
    p_cur = pan["currency"].astype("string").fillna("").to_numpy()

    def assert_knowledge_time(label: str, filed, trig) -> None:
        """硬斷言:任何用到的面板格,公布日必須 <= 觸發日。"""
        if filed is None or np.isnat(filed):
            raise AssertionError(f"知情時點違規:{label} 沒有公布日")
        if filed > trig:
            raise AssertionError(f"知情時點違規:{label} 公布日 {filed} 晚於觸發日 {trig}")

    SPAN_DAYS = {"Q": 90, "H": 180, "9M": 270, "FY": 365}

    def ttm_ocf(idxs: np.ndarray, q: int, t) -> tuple[float, str]:
        """滾動四季經營現金流。

        面板的現金流是「本財年至今累計」(Q=3個月、H=6個月、9M=9個月、FY=全年),
        所以不可以把四個季度相加。四條路,由最貼市到最舊:
          FY_latest —— 最近一個已公布季度本身就是財年末,該格即是滾動四季
          YTD_diff  —— 本期累計 + 上一財年全年 − 去年同期累計
          4Q        —— 該公司真的逐季報三個月數(少數),四個 Q 相加
          FY_stale  —— 以上都湊不出,用最近一份已公布年報的全年數(最多舊 500 日)
        """
        ok = idxs[(~np.isnan(p_ocf[idxs]))]
        if len(ok) == 0:
            return np.nan, ""
        ok = np.array([k for k in ok if (not np.isnat(p_ocf_f[k])) and (p_ocf_f[k] <= t)], dtype="int64")
        if len(ok) == 0:
            return np.nan, ""
        span_q = p_ocf_p[q] if (q in set(ok.tolist())) else ""

        # 1) 最近一格就是財年末
        if span_q == "FY":
            return float(p_ocf[q]), "FY_latest"

        # 2) YTD 差分
        if span_q in ("Q", "H", "9M"):
            pe_q = p_pe[q]
            fy = ok[p_ocf_p[ok] == "FY"]
            fy = fy[p_pe[fy] < pe_q]
            prv = ok[(p_ocf_p[ok] == span_q) & (p_pe[ok] < pe_q)]
            if len(fy) and len(prv):
                f = fy[-1]
                lag_fy = (pe_q - p_pe[f]).astype("timedelta64[D]").astype(int)
                cand = prv[np.abs((pe_q - p_pe[prv]).astype("timedelta64[D]").astype(int) - 365) <= 45]
                if len(cand) and abs(lag_fy - SPAN_DAYS[span_q]) <= 45:
                    v = float(p_ocf[q]) + float(p_ocf[f]) - float(p_ocf[cand[-1]])
                    return v, "YTD_diff"

        # 3) 四個真正的三個月季度
        qq = ok[p_ocf_p[ok] == "Q"]
        if len(qq) >= 4:
            last4 = qq[-4:]
            span = (p_pe[last4[-1]] - p_pe[last4[0]]).astype("timedelta64[D]").astype(int)
            if span <= TTM_SPAN_DAYS:
                return float(np.sum(p_ocf[last4])), "4Q"

        # 4) 最近一份年報
        fy = ok[p_ocf_p[ok] == "FY"]
        if len(fy):
            f = fy[-1]
            if (t - p_pe[f]).astype("timedelta64[D]").astype(int) <= 500:
                return float(p_ocf[f]), "FY_stale"
        return np.nan, ""

    log("[6/7] 逐事件套閘 + 分格 + 前瞻回報")
    ent_meta = ent.set_index("entity_id")
    rows = []
    funnel = {"觸發(冷卻後)": len(triggers)}
    n_no_panel = n_stale = n_no_cash = n_no_td = n_no_ocf = n_no_shares = 0

    for p in triggers:
        e = eid[p]
        t = dates_all[p]
        lo, hi = ent_slices[e]
        sl = pan_slices.get(e)
        if sl is None:
            n_no_panel += 1
            continue
        ps, pe_ = sl
        # --- 已公布的季度(列層 filed_date <= 觸發日)
        mask = (p_fd[ps:pe_] <= t) & (p_pe[ps:pe_] <= t)
        idxs = np.nonzero(mask)[0] + ps
        if len(idxs) == 0:
            n_no_panel += 1
            continue
        q = idxs[-1]                      # 最近一個已公布季度
        assert_knowledge_time("列層 filed_date", p_fd[q], t)
        age_days = (t - p_pe[q]).astype("timedelta64[D]").astype(int)
        if age_days > PANEL_STALE_DAYS:
            n_stale += 1
            continue

        # --- 現金與總債務(必須同一季,且該格公布日 <= 觸發日)
        cash = p_cash[q]
        td = p_td[q]
        if np.isnan(cash) or np.isnat(p_cash_f[q]) or p_cash_f[q] > t:
            n_no_cash += 1
            continue
        assert_knowledge_time("cash_and_equivalents_filed", p_cash_f[q], t)
        has_td = (not np.isnan(td)) and (not np.isnat(p_td_f[q])) and (p_td_f[q] <= t)
        if has_td:
            assert_knowledge_time("total_debt_filed", p_td_f[q], t)

        # --- TTM 經營現金流
        ttm, ttm_method = ttm_ocf(idxs, q, t)
        if np.isnan(ttm):
            n_no_ocf += 1
            continue

        # --- 股數(觸發日前最近一次封面頁,400 日內)
        shq = idxs[(~np.isnan(p_sh[idxs]))]
        shq = shq[[(not np.isnat(p_sh_f[k])) and (p_sh_f[k] <= t) for k in shq]] if len(shq) else shq
        if len(shq) == 0:
            n_no_shares += 1
            continue
        k = shq[-1]
        assert_knowledge_time("shares_outstanding_filed", p_sh_f[k], t)
        sh_age = (t - p_sh_f[k]).astype("timedelta64[D]").astype(int)
        if sh_age > PANEL_STALE_DAYS:
            n_no_shares += 1
            continue
        shares = float(p_sh[k])
        mcap = shares * close_all[p]
        # 拆股基準不一致的警示:價格庫的 close 已拆股調整到今日基準,封面頁股數是當時基準。
        # 觸發日之後若發生拆股或反向拆股,兩者的基準就對不上,市值會被放大或縮小。
        sh_hist = np.nonzero(~np.isnan(p_sh[ps:pe_]))[0] + ps
        split_suspect = False
        if len(sh_hist) > 1:
            kp = int(np.searchsorted(sh_hist, k))
            seq = p_sh[sh_hist[kp:]]
            if len(seq) > 1:
                rat = seq[1:] / seq[:-1]
                rat = rat[np.isfinite(rat)]
                if len(rat) and (np.any(rat <= 0.5) or np.any(rat >= 1.8)):
                    split_suspect = True

        # --- 三閘
        gate_debt_n2 = bool(has_td and (cash - td) >= 0)
        gate_debt_ratio = bool(has_td and ttm > 0 and (td / ttm) <= 3.0)
        gate_cf = bool(ttm > 0)
        gate_mcap = bool(mcap >= MIN_MCAP)

        # --- 行業殺 / 個別殺
        sic2 = ent_meta["sic2"].get(e, pd.NA)
        rows.append(dict(
            entity_id=e, trigger_pos=int(p), trigger_date=pd.Timestamp(t),
            sic2=sic2, cash=cash, total_debt=td if has_td else np.nan,
            has_total_debt=has_td, ttm_ocf=ttm, ttm_method=ttm_method,
            shares=shares, mcap=mcap, split_basis_suspect=split_suspect,
            panel_period_end=pd.Timestamp(p_pe[q]), panel_filed=pd.Timestamp(p_fd[q]),
            panel_age_days=age_days, currency=p_cur[q],
            gate_debt_n2=gate_debt_n2, gate_debt_ratio=gate_debt_ratio,
            gate_cf=gate_cf, gate_mcap=gate_mcap,
        ))

    ev = pd.DataFrame(rows)
    funnel["有已公布季度(且不過期)"] = int(len(ev))
    stats["reject_no_panel"] = n_no_panel
    stats["reject_stale_panel"] = n_stale
    stats["reject_no_cash"] = n_no_cash
    stats["reject_no_ttm_ocf"] = n_no_ocf
    stats["reject_no_shares"] = n_no_shares

    if ev.empty:
        raise SystemExit("沒有事件,檢查上游")

    # 行業中位
    ev = ev.merge(ind, left_on=["trigger_date", "sic2"], right_on=["date", "sic2"], how="left")
    ev = ev.drop(columns=["date"])
    ev["industry_kill"] = np.where(
        (ev["ind_n"] >= MIN_PEERS) & (ev["ind_med_rel"] <= IND_KILL_THRESHOLD), "行業殺",
        np.where(ev["ind_n"] >= MIN_PEERS, "個別殺", "行業不明"))
    ev["industry_kill_abs"] = np.where(
        (ev["ind_n"] >= MIN_PEERS) & (ev["ind_med_abs"] <= IND_KILL_THRESHOLD), "行業殺",
        np.where(ev["ind_n"] >= MIN_PEERS, "個別殺", "行業不明"))

    # 200/250 日線位置
    tp = ev["trigger_pos"].to_numpy()
    for w, arr in ((200, sma200_all), (250, sma250_all)):
        ratio = adj_all[tp] / arr[tp] - 1.0
        ev[f"px_vs_sma{w}"] = ratio
        ev[f"pos_sma{w}"] = np.where(np.isnan(ratio), "資料不足",
                             np.where(ratio > 0, "線之上",
                             np.where(ratio >= -0.10, "線下 10% 內", "線下逾 10%")))
    ev["rel60"] = px["rel60"].to_numpy()[tp]
    ev["dollar_vol_60d"] = [float(np.median(close_all[max(x - 59, 0):x + 1] * vol_all[max(x - 59, 0):x + 1])) for x in tp]

    log("[7/7] 三格進場點 + 前瞻回報")
    last_global_date = dates_all.max()
    out_rows = []
    for r in ev.itertuples(index=False):
        p = r.trigger_pos
        e = r.entity_id
        lo, hi = ent_slices[e]
        rec = r._asdict()
        rec["entity_last_date"] = pd.Timestamp(dates_all[hi - 1])

        # 訊號日 → 進場日 = 訊號日之後一個交易日的收市(可成交時點)
        signals = {}
        signals["A_觸發日即買"] = p
        # B:跌勢衰竭——觸發後連續 10 個交易日不再創新低
        run_min = adj_all[p]
        last_low = p
        sig_b = None
        for j in range(p + 1, min(p + 1 + SEARCH_WINDOW, hi)):
            if adj_all[j] < run_min:
                run_min = adj_all[j]
                last_low = j
            elif j - last_low >= EXHAUST_DAYS:
                sig_b = j
                break
        signals["B_跌勢衰竭"] = sig_b
        # C:買方回來——重上 50 日線
        sig_c = None
        for j in range(p + 1, min(p + 1 + SEARCH_WINDOW, hi)):
            if not np.isnan(sma50_all[j]) and adj_all[j] > sma50_all[j]:
                sig_c = j
                break
        signals["C_買方回來"] = sig_c

        for gname, sig in signals.items():
            key = gname.split("_")[0]
            if sig is None or sig + 1 >= hi:
                rec[f"entry_{key}_date"] = pd.NaT
                rec[f"entry_{key}_lag"] = np.nan
                for hn in HORIZONS:
                    rec[f"{key}_{hn}_excess"] = np.nan
                    rec[f"{key}_{hn}_mdd"] = np.nan
                    rec[f"{key}_{hn}_touch33"] = np.nan
                    rec[f"{key}_{hn}_status"] = "無進場點" if sig is None else "資料不足"
                continue
            en = sig + 1
            rec[f"entry_{key}_date"] = pd.Timestamp(dates_all[en])
            rec[f"entry_{key}_lag"] = int(en - p)
            en_spy = spy_pos_all[en]
            base = adj_all[en]
            base_spy = spy_adj[en_spy]
            for hn, hh in HORIZONS.items():
                tgt = en_spy + hh
                if tgt >= len(spy_dates):
                    rec[f"{key}_{hn}_excess"] = np.nan
                    rec[f"{key}_{hn}_mdd"] = np.nan
                    rec[f"{key}_{hn}_touch33"] = np.nan
                    rec[f"{key}_{hn}_status"] = "未成熟"
                    continue
                tgt_date = spy_dates[tgt]
                seg = dates_all[en:hi]
                k = np.searchsorted(seg, tgt_date, side="right") - 1
                if k < 0:
                    rec[f"{key}_{hn}_excess"] = np.nan
                    rec[f"{key}_{hn}_mdd"] = np.nan
                    rec[f"{key}_{hn}_touch33"] = np.nan
                    rec[f"{key}_{hn}_status"] = "資料不足"
                    continue
                ex_i = en + k
                gap_to_target = (tgt_date - dates_all[ex_i]).astype("timedelta64[D]").astype(int)
                if gap_to_target > 10:
                    status = "未成熟" if (last_global_date - dates_all[hi - 1]).astype("timedelta64[D]").astype(int) <= 10 else "資料提早結束"
                    rec[f"{key}_{hn}_excess"] = np.nan
                    rec[f"{key}_{hn}_mdd"] = np.nan
                    rec[f"{key}_{hn}_touch33"] = np.nan
                    rec[f"{key}_{hn}_status"] = status
                    continue
                stock_ret = adj_all[ex_i] / base - 1.0
                spy_ret = spy_adj[spy_pos_all[ex_i]] / base_spy - 1.0
                rec[f"{key}_{hn}_excess"] = (1 + stock_ret) / (1 + spy_ret) - 1.0
                seg_lo = low_all[en:ex_i + 1] * (adj_all[en:ex_i + 1] / close_all[en:ex_i + 1])
                mdd = float(np.min(seg_lo)) / base - 1.0
                rec[f"{key}_{hn}_mdd"] = mdd
                rec[f"{key}_{hn}_touch33"] = bool(mdd <= -0.33)
                rec[f"{key}_{hn}_status"] = "已成熟"
        out_rows.append(rec)

    res = pd.DataFrame(out_rows)
    res = res.merge(ent[["entity_id", "name", "primary_ticker", "sic_description",
                         "is_foreign_filer"]], on="entity_id", how="left")
    res["trigger_year"] = res["trigger_date"].dt.year
    res["trigger_ym"] = res["trigger_date"].dt.strftime("%Y-%m")
    res["cluster"] = res["trigger_ym"] + "|" + res["sic2"].astype("string").fillna("NA")
    res["period_split"] = np.where(res["trigger_year"] >= 2022, "2022 後(驗證年份)", "2009-2021(建表年份)")

    res.to_csv(OUT / "events.csv", index=False, encoding="utf-8-sig")

    funnel_rows = [
        ("原始觸發列(未冷卻)", stats["raw_candidate_rows"]),
        ("觸發(120 日冷卻後)", int(len(triggers))),
        ("剔:面板無已公布季度", n_no_panel),
        ("剔:最近季度距觸發日逾 400 日", n_stale),
        ("剔:現金格缺", n_no_cash),
        ("剔:四季經營現金流湊不齊", n_no_ocf),
        ("剔:封面頁股數缺或過期", n_no_shares),
        ("進入事件表", int(len(res))),
        ("其中 過現金流閘", int(res["gate_cf"].sum())),
        ("其中 過負債閘 A(N2 淨現金 >= 0)", int(res["gate_debt_n2"].sum())),
        ("其中 過負債閘 B(總債務/四季經營現金流 <= 3)", int(res["gate_debt_ratio"].sum())),
        ("其中 過市值閘(>= 5 億美元)", int(res["gate_mcap"].sum())),
        ("合格事件(A 版:N2 + 現金流 + 市值)",
         int((res["gate_debt_n2"] & res["gate_cf"] & res["gate_mcap"]).sum())),
        ("合格事件(B 版:債務比 + 現金流 + 市值)",
         int((res["gate_debt_ratio"] & res["gate_cf"] & res["gate_mcap"]).sum())),
    ]
    pd.DataFrame(funnel_rows, columns=["步驟", "數目"]).to_csv(
        OUT / "gate_funnel.csv", index=False, encoding="utf-8-sig")

    stats["events_rows"] = int(len(res))
    stats["qualified_A"] = int((res["gate_debt_n2"] & res["gate_cf"] & res["gate_mcap"]).sum())
    stats["qualified_B"] = int((res["gate_debt_ratio"] & res["gate_cf"] & res["gate_mcap"]).sum())
    stats["first_trigger"] = str(res["trigger_date"].min().date())
    stats["last_trigger"] = str(res["trigger_date"].max().date())
    with open(OUT / "build_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    log(json.dumps(stats, ensure_ascii=False, indent=2))
    for k, v in funnel_rows:
        log(f"  {k}: {v:,}")


if __name__ == "__main__":
    main()
