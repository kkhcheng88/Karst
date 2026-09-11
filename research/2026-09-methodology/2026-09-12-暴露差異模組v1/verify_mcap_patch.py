# -*- coding: utf-8 -*-
"""KARST-221 驗收:basket_core.py 改碼後,市值是否等於 KARST-219 已驗證的參考實作。

核三層:
  A. 生產者碼(改後 `basket_core.PanelFeatures.at()`)逐行對 `fix_mcap.py` 的修正值
     —— 199 全 4374 行,相對誤差須為零。
  B. 生產者碼對 `單元驗證——市值修正.csv` 的 `mcap_after`(修後值)逐宗 —— 須為零。
  C. 單元驗證個案再用 **SPY 日曆**的 t0(即 `build_baskets.py` 實際呼叫的方式)重算一次
     —— 與 fix_mcap 用的 `shock_start` 口徑相比,落在交易日者須一致。

用法:PYTHONUTF8=1 python verify_mcap_patch.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
ROOT = Path(r"C:\projects\Karst")
D199 = ROOT / "research" / "2026-09-methodology" / "2026-09-10-①行業殺錯事件籃子"
sys.path.insert(0, str(D199))

import basket_core as bc  # noqa: E402

REF = HERE / "mcap修正"


def rel(new, old):
    if new is None or old is None or not np.isfinite(new) or not np.isfinite(old) or old == 0:
        return np.nan
    return new / old - 1.0


def lean_raw_close(needed) -> dict:
    """只載入用得到的 entity,語意與 basket_core.raw_close_by_entity 相同。

    為甚麼不用原函式:整個價格庫 20,647,659 行 × 16 份 parquet,連 entity_id 字串
    一併入 pandas 要 ~5GB(實測單份 330MB × 16),本機可用記憶體不足 —— 上一個做
    這張票的工人正因此被中止。此處逐份用 arrow 過濾,組出來的 dict 形狀與
    `{entity_id: DataFrame(date, close)}`(按日期排序、未 dropna)一致。
    """
    keys = pa.array(sorted({e for e in needed if isinstance(e, str)}))
    acc: dict = {}
    for p in sorted(bc.PRICES.glob("part_*.parquet")):
        t = pq.read_table(p, columns=["entity_id", "date", "close", "series_role"])
        t = t.filter(pc.equal(t["series_role"], "primary"))
        t = t.filter(pc.is_in(t["entity_id"], value_set=keys))
        if not t.num_rows:
            continue
        d = t.select(["entity_id", "date", "close"]).to_pandas()
        d["date"] = pd.to_datetime(d["date"])
        for e, g in d.groupby("entity_id", sort=False):
            acc.setdefault(e, []).append(g[["date", "close"]])
    out = {}
    for e, gs in acc.items():
        out[e] = pd.concat(gs, ignore_index=True).sort_values("date", kind="stable").reset_index(drop=True)
    return out


def lean_calendar(spy: pd.DataFrame) -> pd.DatetimeIndex:
    """等同 build_wide 的日曆:價格庫裡 close/adj_close 皆為正的主序列日期 ∩ SPY 交易日。

    逐份只讀四個欄,避免 pivot 出 entity × 日期的寬表(那一步才是記憶體殺手)。
    """
    dates = set()
    for p in sorted(bc.PRICES.glob("part_*.parquet")):
        t = pq.read_table(p, columns=["date", "close", "adj_close", "series_role"])
        t = t.filter(pc.equal(t["series_role"], "primary"))
        t = t.filter(pc.and_(pc.greater(t["close"], 0), pc.greater(t["adj_close"], 0)))
        dates.update(pd.DatetimeIndex(pd.to_datetime(t["date"].to_pandas())).unique())
    return pd.DatetimeIndex(sorted(dates & set(spy["date"])))


def main() -> None:
    # entity_id 是補零的 CIK 字串;pandas 會靜靜轉成整數,int-lookup 一律對不上
    mem = pd.read_csv(D199 / "out" / "basket_members.csv", low_memory=False, dtype={"entity_id": str})
    ev = pd.read_csv(D199 / "out" / "event_list.csv")
    fix = pd.read_csv(REF / "basket_members_mcap修正.csv", low_memory=False, dtype={"entity_id": str})
    ki = ["event_id", "basket_kind", "entity_id"]

    # 兩份逐行對齊(同一次 build,同樣次序)
    same_key = (mem[ki].astype(str).agg("|".join, axis=1).tolist()
                == fix[ki].astype(str).agg("|".join, axis=1).tolist())
    print("A 逐行鍵對齊:", same_key, "| 行數", len(mem), len(fix))
    assert same_key, "199 原檔與修正檔逐行鍵不對齊,不能逐行比"

    shock = dict(zip(ev["event_id"], pd.to_datetime(ev["shock_start"])))
    pf = bc.PanelFeatures()

    # 日曆(build_baskets 的做法:衝擊起日對齊到 SPY 交易日)
    spy_df = bc.load_spy()
    cal = lean_calendar(spy_df)
    print("日曆:價格庫×SPY 交易日 %d 日;SPY 本身 %d 日" % (len(cal), len(spy_df)))

    # 未除息還原收市價快取(只載入本檔用得到的 entity:A 用 basket_members,B/C 用單元驗證代號)
    uni = pd.read_csv(REF / "單元驗證——市值修正.csv")
    ent = pd.read_parquet(ROOT / "data" / "universe" / "entities.parquet",
                          columns=["entity_id", "primary_ticker"])
    tk2e = dict(zip(ent["primary_ticker"], ent["entity_id"]))
    need = set(mem["entity_id"].dropna().astype(str))
    need |= {tk2e[t] for t in uni["ticker"].astype(str) if t in tk2e}
    bc._RAW_CLOSE = lean_raw_close(need)
    print("價格快取:entity 數 %d(需要 %d)" % (len(bc._RAW_CLOSE), len(need)))

    rows = []
    for i, r in enumerate(mem.itertuples(index=False)):
        e = r.entity_id
        if pd.isna(e):
            rows.append((np.nan, np.nan, "", ""))
            continue
        t_shock = shock.get(r.event_id)
        i0 = int(cal.searchsorted(t_shock, side="left"))
        t_cal = cal[i0] if i0 < len(cal) else t_shock
        a = pf.at(e, t_shock, None, bc.raw_close_asof(e, t_shock))
        b = pf.at(e, t_cal, None, bc.raw_close_asof(e, t_cal))
        rows.append((a.get("mcap_usd", np.nan), b.get("mcap_usd", np.nan),
                     a.get("mcap_status", "") + "/" + a.get("feat_status", ""),
                     b.get("mcap_status", "")))

    got = pd.DataFrame(rows, columns=["mcap_shock", "mcap_cal", "st_shock", "st_cal"])
    ref = pd.to_numeric(fix["mcap_usd"], errors="coerce")
    err_shock = [rel(n, o) for n, o in zip(got["mcap_shock"], ref)]
    err_cal = [rel(n, o) for n, o in zip(got["mcap_cal"], ref)]
    se1 = pd.Series(err_shock, dtype="float64")
    se2 = pd.Series(err_cal, dtype="float64")
    e1 = se1.abs().max()
    e2 = se2.abs().max()
    n_off = int((se1.fillna(0) != 0).sum())
    nan_both = int(((got["mcap_shock"].isna()) & (ref.isna())).sum())
    print("A 逐行 vs fix_mcap:shock_start 口徑最大絕對相對誤差 = %r;日曆 t0 口徑 = %r" % (e1, e2))
    print("A 兩邊都有值而行差非零的行數 = %d(其餘逐行完全相同)" % n_off)
    print("A 兩邊同時 NaN 的行數 = %d / %d" % (nan_both, len(mem)))
    print("A 有值行數:生產者 %d,參考 %d" % (int(got["mcap_shock"].notna().sum()), int(ref.notna().sum())))
    print("A mcap_status 分佈:", got["st_shock"].value_counts().to_dict())
    print("A 非交易日衝擊起日的事件數 =",
          int((pd.to_datetime(ev["shock_start"]).values != cal[cal.searchsorted(
              pd.to_datetime(ev["shock_start"]), side="left")].values).sum()))

    # B/C 單元驗證個案(uni / tk2e 已在上方為價格快取載入)
    print("\nB/C 單元驗證個案(生產者碼重算;參考值在該檔存為四捨五入後整數)")
    print("  %-5s %-11s %-16s %-16s %-16s %-9s %-9s" %
          ("ticker", "date", "生產者(shock)", "生產者(日曆t0)", "參考 mcap_after", "差B(元)", "差C(元)"))
    worst_b = worst_c = 0.0
    for r in uni.itertuples(index=False):
        e = tk2e.get(r.ticker)
        t = pd.Timestamp(r.date)
        i0 = int(cal.searchsorted(t, side="left"))
        t_cal = cal[i0] if i0 < len(cal) else t
        a = pf.at(e, t, None, bc.raw_close_asof(e, t)) if e else {"mcap_usd": np.nan}
        c = pf.at(e, t_cal, None, bc.raw_close_asof(e, t_cal)) if e else {"mcap_usd": np.nan}
        refv = float(r.mcap_after) if pd.notna(r.mcap_after) else np.nan
        db = abs(round(a["mcap_usd"]) - refv) if np.isfinite(a["mcap_usd"]) and np.isfinite(refv) else np.nan
        dc = abs(round(c["mcap_usd"]) - refv) if np.isfinite(c["mcap_usd"]) and np.isfinite(refv) else np.nan
        if np.isfinite(db):
            worst_b = max(worst_b, db)
        if np.isfinite(dc):
            worst_c = max(worst_c, dc)
        print("  %-5s %-11s %-16.6g %-16.6g %-16.6g %-9s %-9s" %
              (r.ticker, r.date, a["mcap_usd"], c["mcap_usd"], refv,
               "" if not np.isfinite(db) else "%d" % db,
               "" if not np.isfinite(dc) else "%d" % dc))
    print("B 最大絕對差 = %r 元;C 最大絕對差 = %r 元(與參考值同一精度即 0)" % (worst_b, worst_c))

    # A 層:兩條算式逐行相同,只會差浮點最後一位(乘的次序不同),故以 1e-12 為界;
    # 另記「參考有值而生產者無值」的行數 —— fix_mcap 在面板過期時仍用 yfinance 股數補,
    # 生產者碼照票面第二條「缺股數即標查不到」留 NaN,這是口徑不同不是算錯。
    a_nan_only = int((got["mcap_shock"].isna() & ref.notna()).sum())
    ok_a = (not np.isfinite(e1) or e1 <= 1e-12) and (not np.isfinite(e2) or e2 <= 1e-12)
    ok_bc = worst_b == 0 and worst_c == 0
    print("\nA 層最大相對誤差 shock 口徑 %.2e / 日曆口徑 %.2e(<=1e-12 即浮點最後一位,視為零)= %s"
          % (e1, e2, ok_a))
    print("A 層參考有值而生產者留 NaN 的行數 = %d(面板過期時 fix_mcap 用外補股數,生產者碼照票面留空)"
          % a_nan_only)
    print("B/C 層單元驗證個案逐宗誤差為零 =", ok_bc)
    print("\n判定:修法與 KARST-219 參考實作一致(市值算式逐行相同、單元個案零誤差)= %s"
          % (ok_a and ok_bc))


if __name__ == "__main__":
    main()
