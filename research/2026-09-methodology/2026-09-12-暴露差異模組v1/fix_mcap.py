# -*- coding: utf-8 -*-
"""KARST-219 共用層市值欄 `basket_core.PanelFeatures.mcap_usd` 修復。

## 根因(兩條錯疊在一起,都在同一個乘法)

`basket_core.PanelFeatures.at(entity, t, px_close)` 用

    mcap_usd = px_close x shares_outstanding

而:

(1) **股價那一邊是除息還原價。** 呼叫端(`build_baskets.py` / `build_new_events.py`)
    傳進去的 `px_close` 取自 `build_wide()` 的寬表,而該寬表由 **`adj_close`** 建成
    (`basket_core.py:69`)。`adj_close` = 拆股調整 **再加股息調整**,所以高息股的價格
    被歷史派息一路壓低:JPM 2011-08-05 真實收市 37.60,`adj_close` 只有 25.11(−33%)。
    → 高息股市值低估約三成。

(2) **股數那一邊沒有拆股調整。** `shares_outstanding` 是 `dei:EntityCommonStockShares
    Outstanding`(申報封面頁,單位 shares),永遠是「申報當日那一版」的實數,價格庫卻
    已把整條 `close` 序列重述到今日股數基準(yfinance `Close`,`auto_adjust=False`)。
    兩邊基準不同:申報日之後發生的拆股,一邊調整了、另一邊沒有。
    → NVDA 2024-08-01 用 2024-05-29 申報的 24.6 億股(2024-06-10 一拆十之前),
    配拆股後的 109.21,相乘 2,682 億美元;真實約 2.7 萬億,低估十倍。

## 修法

    mcap_usd = close(t) x shares_outstanding(ref) x Π(拆股比率,拆股日 > ref)

`ref` = 該股數那一筆的申報日(`shares_outstanding_filed`),即股數所屬的股數基準日。

兩個要點:
  - 改用 **`close`**(拆股調整、不除息還原),不碰 `adj_close`。
  - 乘回 `ref` 之後所有拆股比率,把「今日基準的價」還原成「ref 那一版的價」,
    與 ref 那一版的股數同一基準,相乘才是真銀碼。
    (拆股本身不改變市值,故此式對 ref 落在拆股前後都成立。)

拆股比率取自 yfinance `Ticker.splits` —— 與價格庫同一來源
(`data/prices/daily` 的 `source` 欄 = `yfinance(auto_adjust=False, actions=False)`),
即價格庫所用的調整因子正是這一張表,乘回去才對得準。yfinance 的 `splits` 除了真拆股,
亦收錄被當作拆股處理的分拆(如 T 2022-04-11 WBD 分拆 1.324、SPG 2014-05-29 1.063),
這正是價格庫已扣掉的部分,必須一併乘回。結果快取於 `mcap修正/splits_used.csv`。

**`data/` 內沒有拆股表**(2026-09-12 glob 過 data/ 全樹,無任何 split 相關檔),
故拆股表來源如實記為 yfinance,不是本地檔。

單元驗證:高息股(T/ED/SPG/JPM/MET/STT)與 NVDA,修前修後對 yfinance 同日市值。
歷史預測(股價重述)一律以後見之明記住:本檔只做算術修復,不改任何既有輸出檔本身,
修正版另存 `mcap修正/*_mcap修正.csv`。

用法:
    PYTHONUTF8=1 python fix_mcap.py
"""
from __future__ import annotations

import csv
import glob
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

ROOT = "C:/projects/Karst"
HERE = os.path.join(ROOT, "research", "2026-09-methodology", "2026-09-12-暴露差異模組v1")
OUT = os.path.join(HERE, "mcap修正")
CACHE = os.path.join(OUT, "splits_used.csv")
FETCH_DAY = "2026-09-12"

# 既有輸出檔(只讀不寫)。每張票各自的籃子成員表,都帶同一個有缺陷的 mcap_usd 欄。
SOURCES = [
    ("KARST-199", os.path.join(ROOT, "research", "2026-09-methodology",
                               "2026-09-10-①行業殺錯事件籃子", "out", "basket_members.csv"),
     os.path.join(ROOT, "research", "2026-09-methodology",
                  "2026-09-10-①行業殺錯事件籃子", "out", "event_list.csv")),
    ("KARST-218", os.path.join(HERE, "out", "basket_members_new.csv"),
     os.path.join(HERE, "out", "event_list_new.csv")),
]

# 由 mcap 直接推出來的欄,一律要跟著重算(否則修正版裡仍躺著舊數)
DERIVED = ("f_net_cash_over_mcap", "f_ps", "f_pb", "f_pe", "f_log_mcap")

# 單元驗證個案:(ticker, 事件日, 備註)。NVDA 與 E17 三家是 KARST-218 點名的;
# T/ED/SPG 是 E01 那一宗(縮減恐慌殺債券替代品)的高息股。
CASES = [
    ("NVDA", "2024-08-01", "E18 日圓套息平倉,拆股錯(一拆十之前申報)"),
    ("JPM", "2011-08-05", "E17 美債降級,高息"),
    ("MET", "2011-08-05", "E17 美債降級,高息"),
    ("STT", "2011-08-05", "E17 美債降級,高息"),
    ("T", "2013-05-21", "E01 縮減恐慌,高息"),
    ("ED", "2013-05-21", "E01 縮減恐慌,高息(公用)"),
    ("SPG", "2013-05-21", "E01 縮減恐慌,高息(房託)"),
    ("WMT", "2022-05-17", "E20 通脹殺零售"),
    ("TGT", "2022-05-17", "E20 通脹殺零售"),
]
# yfinance 的股數歷史(get_shares_full)只由 2015-10 左右開始;之前的年份要人手取的
# 一手申報封面頁股數。單元驗證補充:同一批高息股在 2024-08-01(非事件日)對全口徑
# yfinance 參考,把「除息還原價」那一條錯單獨量出來。
SUPPLEMENT_DAY = "2024-08-01"
SUPPLEMENT = ["T", "ED", "SPG", "JPM", "MET", "STT", "NVDA", "WMT", "TGT"]


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------- 拆股表
def _read_cache() -> tuple[dict[str, dict], set]:
    """快取 = 每個 ticker 一列(有拆股就多列),`ok` 欄記是否抓成功。

    回 (ticker -> {日期: 比率}, 已成功抓過的 ticker 集合)。沒有拆股的 ticker
    亦有一列(split_date 空白),否則「查過但沒有拆股」與「未查過」分不開,
    每一次重跑都會再抓一次,又撞一次限流。
    """
    got: dict[str, dict] = {}
    done: set = set()
    if not os.path.exists(CACHE):
        return got, done
    with open(CACHE, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("ok") == "1":
                done.add(r["ticker"])
            if r["split_date"]:
                got.setdefault(r["ticker"], {})[r["split_date"]] = float(r["ratio"])
    return got, done


def _write_cache(got: dict[str, dict], done: set) -> None:
    """整份重寫:查過的 ticker 一列不漏(包括零拆股的那些)。"""
    os.makedirs(OUT, exist_ok=True)
    with open(CACHE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "split_date", "ratio", "ok", "fetched"])
        for tk in sorted(done):
            sp = sorted(got.get(tk, {}).items())
            if not sp:
                w.writerow([tk, "", "", "1", FETCH_DAY])
            for d, r in sp:
                w.writerow([tk, d, r, "1", FETCH_DAY])


def fetch_all_splits(tickers: list[str]) -> dict[str, dict[str, float]]:
    """取 yfinance 拆股記錄;查過的入快取,重跑只補未查過的。

    分塊推進,每塊寫一次快取 —— yfinance 對密集請求會回 YFRateLimitError,一次過
    大批抓會整批失敗並把好數據蓋走;分塊寫入令「抓到幾多入幾多」,重跑只補欠的。
    """
    import time

    got, done = _read_cache()
    todo = [t for t in tickers if t not in done]
    log("拆股快取:%d 個已查(%d 個有拆股紀錄),待查 %d 個"
        % (len(done), sum(1 for v in got.values() if v), len(todo)))
    if not todo:
        return {t: got.get(t, {}) for t in tickers}
    import yfinance as yf

    def one(tk: str):
        try:
            s = yf.Ticker(tk).splits
            return tk, {str(k.date()): float(v) for k, v in s.items()}, None
        except Exception as e:  # noqa: BLE001
            return tk, {}, str(e)

    CHUNK, WORKERS = 100, 6
    still: list = list(todo)
    for round_no, pause in ((1, 0.3), (2, 4.0), (3, 12.0)):
        if not still:
            break
        remain = list(still)
        still = []
        log("  第 %d 輪:%d 個 ticker(每塊 %d、%d 執行緒)"
            % (round_no, len(remain), CHUNK, WORKERS))
        for i in range(0, len(remain), CHUNK):
            blk = remain[i:i + CHUNK]
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                res = list(ex.map(one, blk))
            ok = 0
            for tk, sp, err in res:
                if err:
                    still.append(tk)
                else:
                    done.add(tk)
                    got[tk] = sp
                    ok += 1
            _write_cache(got, done)
            log("    %d/%d 完成(本塊成功 %d)" % (min(i + CHUNK, len(remain)),
                                                len(remain), ok))
            if ok == 0:
                break
            time.sleep(pause)
        if still:
            time.sleep(pause * 3)
    if still:
        log("  ! 三輪之後仍然取不到 %d 個:%s" % (len(still), still[:10]))
    log("  yfinance 共查到 %d/%d 個 ticker" % (len(done & set(tickers)), len(tickers)))
    return {t: got.get(t, {}) for t in tickers}


def split_factor_after(splits: dict[str, float], day: pd.Timestamp) -> tuple[float, list]:
    """day 之後(不含 day)所有拆股比率的乘積,以及用了哪幾筆。"""
    f, used = 1.0, []
    for d, r in sorted(splits.items()):
        if pd.Timestamp(d) > day:
            f *= r
            used.append("%s:%g" % (d, r))
    return f, used


# ----------------------------------------------------------------- 面板 / 價格
def load_prices() -> dict[str, pd.DataFrame]:
    frames = []
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "prices", "daily", "part_*.parquet"))):
        frames.append(pd.read_parquet(p, columns=["entity_id", "date", "close", "series_role"]))
    px = pd.concat(frames, ignore_index=True)
    px = px[px["series_role"] == "primary"]
    px["date"] = pd.to_datetime(px["date"])
    return {e: d.sort_values("date").reset_index(drop=True)
            for e, d in px.groupby("entity_id", sort=False)}


def close_asof(px_by_ent: dict, entity_id: str, t: pd.Timestamp):
    g = px_by_ent.get(entity_id)
    if g is None:
        return None, None
    g = g[g["date"] <= t]
    if not len(g):
        return None, None
    return float(g["close"].iloc[-1]), g["date"].iloc[-1]


def load_panel() -> pd.DataFrame:
    cols = ["entity_id", "period_end", "filed_date", "shares_outstanding",
            "shares_outstanding_filed"]
    pan = pd.read_parquet(os.path.join(ROOT, "data", "panel", "quarterly_v3.parquet"),
                          columns=cols)
    pan["period_end"] = pd.to_datetime(pan["period_end"])
    pan["filed_date"] = pd.to_datetime(pan["filed_date"])
    pan["shares_outstanding_filed"] = pd.to_datetime(pan["shares_outstanding_filed"])
    return pan.sort_values(["entity_id", "period_end"], kind="stable").reset_index(drop=True)


def pick_shares(pan: pd.DataFrame, entity_id: str, t: pd.Timestamp):
    """照抄 `basket_core.PanelFeatures.at()` 的選股數規則(唯讀,不改原邏輯)。

    原規則:在 filed_date <= t 且 period_end <= t 的行之中,取 `period_end` 最大的一行;
    該行的 `shares_outstanding_filed` 距 t 不超過 400 日才採用。
    """
    sub = pan[(pan["entity_id"] == entity_id) & pan["filed_date"].notna()
              & (pan["filed_date"] <= t) & (pan["period_end"] <= t)]
    if not len(sub):
        return None
    shq = sub[sub["shares_outstanding"].notna() & sub["shares_outstanding_filed"].notna()
              & (sub["shares_outstanding_filed"] <= t)]
    if not len(shq):
        return None
    k = shq.iloc[-1]
    if (t - k["shares_outstanding_filed"]).days > 400:
        return None
    return float(k["shares_outstanding"]), k["shares_outstanding_filed"], k["period_end"]


# ------------------------------------------------------------------- 修正一行
def correct(shares: float, ref_day: pd.Timestamp, splits: dict, close: float) -> tuple:
    fac, used = split_factor_after(splits, ref_day)
    return close * fac * shares, fac, used


def num(v):
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def build_corrected(tag: str, src: str, events: str, pan, px_by_ent, splits_all) -> str:
    ev = pd.read_csv(events, encoding="utf-8-sig", dtype=str)
    shock = dict(zip(ev["event_id"], pd.to_datetime(ev["shock_start"])))
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    fields = list(rows[0].keys()) + [
        "mcap_usd_panel_old", "mcap_fix_status", "mcap_fix_ratio",
        "mcap_fix_close", "mcap_fix_shares", "mcap_fix_shares_ref",
        "mcap_fix_split_factor", "mcap_fix_splits"]
    out = []
    n_fix = n_same = 0
    stats = {"無價": 0, "無股數": 0, "無申報事件日": 0}
    for r in rows:
        t = shock.get(r["event_id"])
        old = num(r.get("mcap_usd"))
        new, status, ratio = None, "", None
        close = sh = ref = fac = None
        used: list = []
        if t is None:
            status = "無申報事件日"
            stats[status] += 1
        else:
            close, _d = close_asof(px_by_ent, r["entity_id"], t)
            ps = pick_shares(pan, r["entity_id"], t)
            if close is None:
                status = "無價"
                stats[status] += 1
            elif ps is None:
                status = "無股數"
                stats[status] += 1
            else:
                sh, ref, _pe = ps
                new, fac, used = correct(sh, ref, splits_all.get(r["ticker"], {}), close)
                status = "修正"
                if fac == 1.0 and old and new and abs(new / old - 1) < 1e-6:
                    n_same += 1
                n_fix += 1
        if old and new:
            ratio = new / old
        # 由 mcap 推出來的欄一律重算;其餘原值照抄
        r2 = dict(r)
        for c in DERIVED:
            r2[c] = r.get(c, "")
        if new:
            r2["mcap_usd"] = repr(new)
            n2 = num(r.get("f_net_cash_n2"))
            r2["f_net_cash_over_mcap"] = repr(n2 / new) if (n2 and new > 0) else ""
            rev, eq, ni = num(r.get("ttm_revenue")), num(r.get("equity")), num(r.get("ttm_net_income"))
            r2["f_ps"] = repr(new / rev) if (rev and rev > 0) else ""
            r2["f_pb"] = repr(new / eq) if (eq and eq > 0) else ""
            r2["f_pe"] = repr(new / ni) if (ni and ni > 0) else ""
            r2["f_log_mcap"] = repr(float(np.log(new)))
        r2.update(mcap_usd_panel_old=(r.get("mcap_usd") or ""),
                  mcap_fix_status=status,
                  mcap_fix_ratio=("" if ratio is None else repr(ratio)),
                  mcap_fix_close=("" if close is None else repr(close)),
                  mcap_fix_shares=("" if sh is None else repr(sh)),
                  mcap_fix_shares_ref=("" if ref is None else str(ref.date())),
                  mcap_fix_split_factor=("" if fac is None else repr(fac)),
                  mcap_fix_splits=";".join(used))
        out.append(r2)
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, os.path.basename(src).replace(".csv", "_mcap修正.csv"))
    with open(dst, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    mult = sum(1 for r in out if r["mcap_fix_split_factor"] not in ("", "1.0"))
    log("%s %s → %s(%d 行,修正 %d,拆股因子 != 1 者 %d,無價 %d,無股數 %d)"
        % (tag, os.path.basename(src), os.path.basename(dst), len(out), n_fix, mult,
           stats["無價"], stats["無股數"]))
    return dst


# ---------------------------------------------------------------- 單元驗證表
YF_CACHE = os.path.join(OUT, "yf_參考快取.csv")


def _yf_cache() -> dict:
    out: dict = {}
    if os.path.exists(YF_CACHE):
        with open(YF_CACHE, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                out[(r["kind"], r["ticker"], r["day"])] = r["value"]
    return out


def _yf_cache_put(store: dict, kind: str, ticker: str, day: str, value) -> None:
    store[(kind, ticker, day)] = "" if value is None else repr(value)
    os.makedirs(OUT, exist_ok=True)
    with open(YF_CACHE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kind", "ticker", "day", "value", "fetched"])
        for (k, t, d), v in sorted(store.items()):
            w.writerow([k, t, d, v, FETCH_DAY])


def yf_close(ticker: str, day: str, store: dict):
    """yfinance 該日收市(`auto_adjust=False` 的 `Close`)。"""
    key = ("close", ticker, day)
    if key in store:
        return None if store[key] == "" else eval(store[key])
    val = None
    try:
        import yfinance as yf
        h = yf.Ticker(ticker).history(start=(pd.Timestamp(day) - pd.Timedelta(days=10)).date(),
                                      end=(pd.Timestamp(day) + pd.Timedelta(days=2)).date(),
                                      auto_adjust=False)
        if not h.empty:
            h.index = pd.to_datetime(h.index).tz_localize(None)
            h = h[h.index <= pd.Timestamp(day)]
            if not len(h):
                val = None
            else:
                val = (float(h["Close"].iloc[-1]), str(h.index[-1].date()))
    except Exception:  # noqa: BLE001
        return None          # 抓不到不寫快取,下次再試
    _yf_cache_put(store, "close", ticker, day, val)
    return val


def yf_shares(ticker: str, day: str, store: dict):
    key = ("shares", ticker, day)
    if key in store:
        return None if store[key] == "" else eval(store[key])
    val = None
    try:
        import yfinance as yf
        s = yf.Ticker(ticker).get_shares_full(
            start="2009-01-01", end=(pd.Timestamp(day) + pd.Timedelta(days=400)).date())
        if s is not None and len(s):
            idx = pd.to_datetime(s.index).tz_localize(None)
            prior = s[idx <= pd.Timestamp(day)]
            if len(prior):
                val = float(prior.iloc[-1])
    except Exception:  # noqa: BLE001
        return None
    _yf_cache_put(store, "shares", ticker, day, val)
    return val


def unit_tests(pan, px_by_ent, splits_all) -> str:
    import time
    store = _yf_cache()
    rows = []
    cases = [(tk, d, note, "事件日") for tk, d, note in CASES]
    cases += [(tk, SUPPLEMENT_DAY, "非事件日:全口徑 yfinance 參考單元測", "補充單元測")
              for tk in SUPPLEMENT]
    for tk, day, note, kind in cases:
        t = pd.Timestamp(day)
        e = TICKER2ENT.get(tk)
        close, _d = close_asof(px_by_ent, e, t) if e else (None, None)
        ps = pick_shares(pan, e, t) if e else None
        splits = splits_all.get(tk, {})
        yfc = yf_close(tk, day, store)
        time.sleep(0.8)
        yfs = yf_shares(tk, day, store)
        time.sleep(0.8)
        fac_day, _u = split_factor_after(splits, t)
        # yfinance 同日市值參考:未還原價 x 同日流通股數(股數歷史 2015-10 起)
        ref_mcap = ref_src = None
        if yfc and yfs:
            ref_mcap = yfc[0] * fac_day * yfs
            ref_src = "yfinance 未還原收市 x yfinance 同日流通股數(全外部)"
        elif yfc and ps is not None:
            # yfinance 的股數歷史只由 2015-10 左右開始;更早的日子改用申報封面頁股數,
            # 價格那一邊仍然是 yfinance。股數那一邊不是 yfinance,故另標來源。
            ref_mcap = yfc[0] * fac_day * ps[0]
            ref_src = "yfinance 未還原收市 x 申報封面頁股數(yn 股數歷史自 2015-10 起,該日查不到)"
        old = new = None
        ref_day = None
        if close is not None and ps is not None:
            sh, ref_day, _pe = ps
            new, fac, _used = correct(sh, ref_day, splits, close)
            # 修前重現:除息還原價 x 未調整股數(即 basket_core 的口徑)
            ga = ADJ.get(e)
            if ga is not None:
                ga2 = ga[ga["date"] <= t]
                if len(ga2):
                    old = float(ga2["adj_close"].iloc[-1]) * sh

        def pct(v):
            if ref_mcap is None or not v:
                return ""
            return round(100 * (v / ref_mcap - 1), 1)

        rows.append(dict(
            kind=kind, ticker=tk, date=day,
            close_panel=("" if close is None else round(close, 4)),
            close_yf=("" if not yfc else round(yfc[0], 4)),
            shares_panel=("" if ps is None else int(ps[0])),
            shares_ref=("" if ref_day is None else str(ref_day.date())),
            split_factor=round(fac_day, 6),
            yf_shares=("" if yfs is None else int(yfs)),
            mcap_before=("" if old is None else int(round(old))),
            mcap_after=("" if new is None else int(round(new))),
            mcap_yf_ref=("" if ref_mcap is None else int(round(ref_mcap))),
            err_before_pct=pct(old),
            err_after_pct=pct(new),
            ref_source=(ref_src or "面板無股數(該實體在面板內取不到 dei 封面頁股數)"),
            note=note))
    dst = os.path.join(OUT, "單元驗證——市值修正.csv")
    with open(dst, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log("單元驗證 → %s(%d 行)" % (os.path.basename(dst), len(rows)))
    for r in rows:
        log("  %-5s %s 修前 %s 修後 %s yf %s 誤差 %s→%s%%"
            % (r["ticker"], r["date"], r["mcap_before"], r["mcap_after"], r["mcap_yf_ref"],
               r["err_before_pct"], r["err_after_pct"]))
    return dst


TICKER2ENT: dict = {}
ADJ: dict = {}


def main() -> None:
    global TICKER2ENT, ADJ
    pan = load_panel()
    px_by_ent = load_prices()
    frames = []
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "prices", "daily", "part_*.parquet"))):
        frames.append(pd.read_parquet(p, columns=["entity_id", "date", "adj_close", "series_role"]))
    adj = pd.concat(frames, ignore_index=True)
    adj = adj[adj["series_role"] == "primary"]
    adj["date"] = pd.to_datetime(adj["date"])
    ADJ = {e: d.sort_values("date").reset_index(drop=True) for e, d in adj.groupby("entity_id")}
    ent = pd.read_parquet(os.path.join(ROOT, "data", "universe", "entities.parquet"),
                          columns=["entity_id", "primary_ticker"])
    TICKER2ENT = dict(zip(ent["primary_ticker"], ent["entity_id"]))

    tickers = set()
    for _tag, src, _ev in SOURCES:
        with open(src, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("ticker"):
                    tickers.add(r["ticker"])
    for tk, _d, _n in CASES:
        tickers.add(tk)
    tickers |= set(SUPPLEMENT)
    splits_all = fetch_all_splits(sorted(tickers))

    for tag, src, ev in SOURCES:
        build_corrected(tag, src, ev, pan, px_by_ent, splits_all)
    unit_tests(pan, px_by_ent, splits_all)


if __name__ == "__main__":
    main()
