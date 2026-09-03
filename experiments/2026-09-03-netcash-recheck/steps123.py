# -*- coding: utf-8 -*-
"""KARST-176 第①②③步:舊格上的三個隔離(判準第三節)。

①舊宇宙 728 + 面板 v2 + 舊口徑(停手線:逐年加權 AUC 0.648 ± 0.02)
②同一批格,只把帳目換成面板 v3(另出②附:連股數也換 v3)
③同一批格、面板 v2,只把樣本收窄到小型股名單 v1 的成員

輸出 out/:
  cells_old.parquet     舊格連三步的 S1
  steps123.csv          四數表
  steps123_by_year.csv  逐年 AUC 明細
  step3_match.json      代號接實體的命中情況
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import common176 as K

STOP_LO, STOP_HI = 0.628, 0.668     # 0.648 ± 0.02


def match_entities(cells: pd.DataFrame) -> pd.DataFrame:
    """判準第三節③:代號 + t0 落在時段內;多段命中用同實體別名閘挑一。"""
    tp = pd.read_parquet(K.UNIVERSE / "ticker_periods.parquet")
    tp["valid_from"] = pd.to_datetime(tp["valid_from"], errors="coerce")
    tp["valid_to"] = pd.to_datetime(tp["valid_to"], errors="coerce")
    man = pd.read_csv(K.PRICE_DIR / "manifest.csv", dtype={"entity_id": str})
    man["entity_id"] = man["entity_id"].str.zfill(10)
    rows = {(r.entity_id, r.ticker): (r.rows if pd.notna(r.rows) else 0)
            for r in man.itertuples()}

    by_tk = {tk: g for tk, g in tp.groupby("ticker")}
    eids, reasons = [], []
    cache: dict[tuple, tuple] = {}
    for tk, t0 in zip(cells["ticker"].to_numpy(), cells["t0"].to_numpy()):
        key = (tk, t0)
        if key in cache:
            e, r = cache[key]
        else:
            g = by_tk.get(tk)
            if g is None:
                e, r = None, "代號表無此代號"
            else:
                t0s = pd.Timestamp(t0)
                hit = g[(g["valid_from"] <= t0s)
                        & (g["valid_to"].isna() | (g["valid_to"] >= t0s))]
                if hit.empty:
                    e, r = None, "時段不覆蓋 t0"
                elif len(hit) == 1:
                    e, r = str(hit.iloc[0]["entity_id"]), "唯一"
                else:
                    h = hit.assign(
                        _o=hit["valid_to"].isna().astype(int),
                        _r=[rows.get((x, tk), 0) for x in hit["entity_id"]])
                    h = h.sort_values(["_o", "_r", "entity_id"],
                                      ascending=[False, False, True])
                    e, r = str(h.iloc[0]["entity_id"]), "別名閘挑一"
            cache[key] = (e, r)
        eids.append(e)
        reasons.append(r)
    cells["eid_tp"] = eids
    cells["eid_reason"] = reasons
    return cells


def main() -> None:
    c, _ = K.old_cells()
    print(f"舊格:{len(c):,} 格、十倍格 {int(c.is10x.sum())}、代號 {c.ticker.nunique()}")

    # ---------------- ① 基準 ------------------------------------------------
    c["s1_step1_pre"] = (c["cash"] - c["total_debt_orig"]) / c["mcap"]
    c["s1_step1"] = (c["cash"] - c["total_debt_filled"]) / c["mcap"]

    r1_pre, y1_pre = K.four_numbers(c, "s1_step1_pre", "①舊宇宙+面板v2(補前,即 KARST-166 原口徑)")
    print(f"① 補前逐年加權 AUC = {r1_pre['AUC_year_weighted']}(停手線 {STOP_LO}–{STOP_HI})")
    a1 = r1_pre["AUC_year_weighted"]
    if a1 is None or not (STOP_LO <= a1 <= STOP_HI):
        (K.OUT / "STOP.json").write_text(json.dumps(
            {"停手": True, "第一步逐年加權AUC": a1, "目標": "0.648 ± 0.02"},
            ensure_ascii=False, indent=1), encoding="utf-8")
        raise SystemExit(f"停手:第一步重現不到 KARST-166 的 0.648(量到 {a1})")
    r1, y1 = K.four_numbers(c, "s1_step1", "①舊宇宙+面板v2(補後)")

    # ---------------- ② 只換面板 v3 ----------------------------------------
    p3 = K.panel_v3()
    v3 = K.asof_v3(c, p3, when="t0", key="entity_id")
    c = pd.concat([c.reset_index(drop=True), v3], axis=1)
    usd = c["v3_currency"].eq("USD")
    c["s1_step2_pre"] = np.where(usd, (c["v3_cash_and_equivalents"] - c["v3_total_debt_orig"]) / c["mcap"], np.nan)
    c["s1_step2"] = np.where(usd, (c["v3_cash_and_equivalents"] - c["v3_total_debt_filled"]) / c["mcap"], np.nan)
    c["s1_step2_nocur"] = (c["v3_cash_and_equivalents"] - c["v3_total_debt_filled"]) / c["mcap"]

    # ②附:連市值分母的股數也換成面板 v3(申報原值 × t0 之後累積拆股因子)
    sp = pd.read_parquet(K.SPLITS)
    sp["report_date"] = pd.to_datetime(sp["report_date"], errors="coerce")
    fac = np.ones(len(c))
    tk = c["ticker"].to_numpy()
    t0v = c["t0"].to_numpy()
    for sym, g in sp.groupby("symbol"):
        if sym in K.CONTAMINATED:
            continue
        m = tk == sym
        if not m.any():
            continue
        f = np.ones(m.sum())
        for d, r in zip(g["report_date"].to_numpy(), g["ratio"].to_numpy()):
            f *= np.where(t0v[m] < d, r, 1.0)
        fac[m] = f
    c["mcap_v3"] = c["close"] * c["v3_shares_outstanding"] * fac
    c.loc[c.ticker.isin(K.CONTAMINATED), "mcap_v3"] = np.nan
    c["s1_step2b"] = np.where(
        usd, (c["v3_cash_and_equivalents"] - c["v3_total_debt_filled"]) / c["mcap_v3"], np.nan)

    r2_pre, y2_pre = K.four_numbers(c, "s1_step2_pre", "②只換面板v3(補前)")
    r2, y2 = K.four_numbers(c, "s1_step2", "②只換面板v3(補後)")
    r2n, _ = K.four_numbers(c, "s1_step2_nocur", "②附A 不設美元限制(對照)")
    r2b, _ = K.four_numbers(c, "s1_step2b", "②附B 連股數也換 v3(對照)")

    # ---------------- ③ 只換宇宙 -------------------------------------------
    c = match_entities(c)
    v1 = pd.read_csv(K.UNIVERSE / "universe_smallcap_v1.csv", dtype={"entity_id": str})
    ids = set(v1["entity_id"].str.zfill(10))
    c["in_smallcap"] = c["eid_tp"].isin(ids)
    sub = c[c["in_smallcap"]].copy()
    r3_pre, y3_pre = K.four_numbers(sub, "s1_step1_pre", "③只換宇宙為小型股名單v1(補前)")
    r3, y3 = K.four_numbers(sub, "s1_step1", "③只換宇宙為小型股名單v1(補後)")

    # 交叉核對:用面板 v2 自帶的 cik 判成員身份
    c["in_smallcap_cik"] = c["cik"].isin(ids)
    match = {
        "接得回實體的格": int(c["eid_tp"].notna().sum()),
        "接不回的格": int(c["eid_tp"].isna().sum()),
        "接不回原因": c.loc[c["eid_tp"].isna(), "eid_reason"].value_counts().to_dict(),
        "屬小型股名單v1的格(代號時段表接法)": int(c["in_smallcap"].sum()),
        "屬小型股名單v1的十倍格": int(c.loc[c["in_smallcap"], "is10x"].sum()),
        "屬小型股名單v1的公司數": int(c.loc[c["in_smallcap"], "ticker"].nunique()),
        "交叉核對(面板v2 cik 接法)的格": int(c["in_smallcap_cik"].sum()),
        "兩種接法不一致的格": int((c["in_smallcap"] != c["in_smallcap_cik"]).sum()),
    }
    (K.OUT / "step3_match.json").write_text(
        json.dumps(match, ensure_ascii=False, indent=1), encoding="utf-8")

    rows = [r1_pre, r1, r2_pre, r2, r2n, r2b, r3_pre, r3]
    tab = pd.DataFrame(rows)
    tab.to_csv(K.OUT / "steps123.csv", index=False, encoding="utf-8-sig")
    yr = []
    for name, per in [("①補前", y1_pre), ("①補後", y1), ("②補前", y2_pre),
                      ("②補後", y2), ("③補前", y3_pre), ("③補後", y3)]:
        for yy, a, n, k1 in per:
            yr.append(dict(step=name, year=yy, AUC=round(a, 4), n_cells=n, n_10x=k1))
    pd.DataFrame(yr).to_csv(K.OUT / "steps123_by_year.csv", index=False,
                            encoding="utf-8-sig")

    keep = ["ticker", "cik", "eid_tp", "t0", "year", "multiple", "is10x", "mcap",
            "mcap_v3", "cash", "total_debt_orig", "total_debt_filled",
            "v3_cash_and_equivalents", "v3_total_debt_orig", "v3_total_debt_filled",
            "v3_currency", "in_smallcap", "s1_step1_pre", "s1_step1",
            "s1_step2_pre", "s1_step2", "s1_step2b"]
    c[keep].to_parquet(K.OUT / "cells_old.parquet", index=False, compression="zstd")

    print(tab[["step", "n_cells", "n_10x", "AUC_full", "AUC_year_weighted",
               "verdict", "netcash_pos_10x", "netcash_pos_all",
               "false_kill_10x"]].to_string(index=False))
    print()
    print(json.dumps(match, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
