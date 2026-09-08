# -*- coding: utf-8 -*-
"""KARST-194:加不加閘對照——同一批觸發,按三閘過不過分五組,量閘買到什麼、割掉什麼。

不重建事件。只讀 out/events_gatefix.csv(KARST-191 負債閘補算後的事件表)重分組。
統計方法(簇 bootstrap、樣本 < 30 只報樣本數、未成熟樣本不計入)直接匯入
make_tables.py 的 boot_ci(),不另寫一份。
集中度(前 1% / 前 5% 佔總超額比例、剔走後平均)沿用 recon_caliber.py 的算法。

分組(負債閘用 gatefix 版):
  1 過三閘            三閘全過(= 現行①池)
  2 只不過負債閘      現金流、市值過,負債不過
  3 只不過現金流閘    負債、市值過,現金流不過
  4 只不過市值閘      負債、現金流過,市值不過(另按 1 億分細)
  5 不過兩閘          剛好兩閘不過(補完組,五組定義的餘數,細分三種組合另表)
  6 三閘全不過        三閘皆不過
  0 全部觸發不分閘    總對照

負債閘三態:過 / 不過 / 資料不足。主口徑「可判」把資料不足排除出五組(單獨一行報);
另出 A(資料不足當不過)與 A2(資料不足當過閘)兩個敏感度口徑。

流動性口徑:①池原本除了三閘還加一條「近 60 日中位成交金額 >= 300 萬美元」。
它不是三閘之一,但實質是第四道閘,所以獨立成一個口徑維度:
  含流動性閘(與①池可比) / 不含流動性閘(只剔拆股基準可疑)

輸出:out/gate_groups_gatecost.csv、out/gate_marginal_gatecost.csv、
out/top_winners_gatecost.csv、out/gate_summary_gatecost.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_tables as MT  # noqa: E402  沿用 boot_ci / MIN_CELL / LIQ_MIN

OUT = HERE / "out"
HORIZONS = MT.HORIZONS
MIN_CELL = MT.MIN_CELL
LIQ_MIN = MT.LIQ_MIN
MCAP_GATE = 500e6
MCAP_SMALL = 100e6

GROUP_ORDER = [
    "0 全部觸發(不分閘)",
    "1 過三閘(現行①池)",
    "2 只不過負債閘",
    "3 只不過現金流閘",
    "4 只不過市值閘",
    "4a 只不過市值閘(1 億至 5 億)",
    "4b 只不過市值閘(低於 1 億)",
    "5 不過兩閘(補完)",
    "6 三閘全不過",
    "9 負債閘資料不足(不納入五組)",
]


def load_events() -> pd.DataFrame:
    ev = pd.read_csv(OUT / "events_gatefix.csv", encoding="utf-8-sig",
                     parse_dates=["trigger_date"], dtype={"entity_id": "string"})
    ev["entity_id"] = ev["entity_id"].str.zfill(10)
    ev["負債閘可判"] = ~ev["資料不足_債務閘"].astype(bool)
    ev["過負債閘"] = ev["gate_debt_n2_gatefix"].astype(bool)
    ev["過現金流閘"] = ev["gate_cf"].astype(bool)
    ev["過市值閘"] = ev["gate_mcap"].astype(bool)
    ev["過流動性閘"] = ev["dollar_vol_60d"] >= LIQ_MIN
    ev["資料底線"] = ~ev["split_basis_suspect"].astype(bool)
    return ev


def assign_group(ev: pd.DataFrame, debt_caliber: str) -> pd.Series:
    """按口徑決定負債閘的布林值,再判五組。回傳組名 Series。"""
    if debt_caliber == "可判":
        debt = ev["過負債閘"]
        undet = ~ev["負債閘可判"]
    elif debt_caliber == "A(資料不足當不過)":
        debt = ev["過負債閘"]          # gatefix 版本身已把資料不足判 False
        undet = pd.Series(False, index=ev.index)
    elif debt_caliber == "A2(資料不足當過閘)":
        debt = ev["過負債閘"] | (~ev["負債閘可判"])
        undet = pd.Series(False, index=ev.index)
    else:
        raise ValueError(debt_caliber)

    cf, mc = ev["過現金流閘"], ev["過市值閘"]
    nfail = (~debt).astype(int) + (~cf).astype(int) + (~mc).astype(int)
    g = pd.Series("", index=ev.index, dtype=object)
    g[nfail == 0] = "1 過三閘(現行①池)"
    g[(nfail == 1) & (~debt)] = "2 只不過負債閘"
    g[(nfail == 1) & (~cf)] = "3 只不過現金流閘"
    g[(nfail == 1) & (~mc)] = "4 只不過市值閘"
    g[nfail == 2] = "5 不過兩閘(補完)"
    g[nfail == 3] = "6 三閘全不過"
    g[undet] = "9 負債閘資料不足(不納入五組)"
    return g


def cell(sub: pd.DataFrame, h: str, do_boot: bool) -> dict:
    st = sub[f"A_{h}_status"]
    mature = sub[st == "已成熟"]
    row = {
        "樣本N": int(len(mature)),
        "未成熟": int((st == "未成熟").sum()),
        "其他不可判": int((~st.isin(["已成熟", "未成熟"])).sum()),
        "公司數": int(mature["entity_id"].nunique()),
    }
    n = len(mature)
    if n == 0:
        return row
    ex = mature[f"A_{h}_excess"].to_numpy(dtype=float)
    mdd = mature[f"A_{h}_mdd"].to_numpy(dtype=float)
    row["中位期內最大跌幅"] = float(np.median(mdd))
    row["觸及負33比例"] = float(np.mean(mature[f"A_{h}_touch33"].astype(bool).to_numpy()))
    row["觸及負80比例"] = float(np.mean(mdd <= -0.80))
    row["觸及負50比例"] = float(np.mean(mdd <= -0.50))
    row["最大單筆超額"] = float(np.max(ex))
    if n < MIN_CELL:
        row["可信度"] = "低(樣本不足,只報樣本數)"
        return row
    row["可信度"] = "高" if n >= 100 else "中"
    win = (ex > 0).astype(float)
    row["勝率"] = float(win.mean())
    row["中位超額"] = float(np.median(ex))
    row["平均超額"] = float(np.mean(ex))
    row["p25超額"] = float(np.percentile(ex, 25))
    row["p75超額"] = float(np.percentile(ex, 75))
    w, l = ex[ex > 0], ex[ex <= 0]
    row["平均盈虧比"] = float(np.mean(w) / abs(np.mean(l))) if len(w) and len(l) else np.nan
    row["中位盈虧比"] = float(np.median(w) / abs(np.median(l))) if len(w) and len(l) else np.nan
    # 集中度:沿用 recon_caliber.py
    ex_sorted = np.sort(ex)
    k1 = max(1, int(np.ceil(n * 0.01)))
    k5 = max(1, int(np.ceil(n * 0.05)))
    tot = float(np.sum(ex))
    row["前1%事件數"] = k1
    row["前1%佔總超額比例"] = float(np.sum(ex_sorted[-k1:]) / tot) if tot != 0 else np.nan
    row["前5%事件數"] = k5
    row["前5%佔總超額比例"] = float(np.sum(ex_sorted[-k5:]) / tot) if tot != 0 else np.nan
    row["剔走前1%後平均"] = float(np.mean(ex_sorted[:-k1]))
    row["剔走前5%後平均"] = float(np.mean(ex_sorted[:-k5]))
    row["簇數"] = int(mature["cluster"].nunique())
    row["2020年觸發佔比"] = float((mature["trigger_year"] == 2020).mean())
    if do_boot:
        lo, hi, mlo, mhi = MT.boot_ci(win, mature["cluster"].to_numpy(), ex)
        row["勝率下限"], row["勝率上限"] = lo, hi
        row["平均超額下限"], row["平均超額上限"] = mlo, mhi
    return row


def build_group_tables(ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for liq_label, liq_mask in (("含流動性閘(與①池可比)", ev["過流動性閘"]),
                                ("不含流動性閘", pd.Series(True, index=ev.index))):
        for debt_caliber in ("可判", "A(資料不足當不過)", "A2(資料不足當過閘)"):
            base = ev[ev["資料底線"] & liq_mask].copy()
            base["組"] = assign_group(base, debt_caliber)
            主 = (liq_label.startswith("含") and debt_caliber == "可判")
            for yr_label, ymask in (("全期 2010-2026", pd.Series(True, index=base.index)),
                                    ("建表年份 2010-2021", base["trigger_year"] <= 2021),
                                    ("驗證年份 2022-2026", base["trigger_year"] >= 2022)):
                seg = base[ymask]
                for gname in GROUP_ORDER:
                    if gname == "0 全部觸發(不分閘)":
                        sub = seg
                    elif gname == "4a 只不過市值閘(1 億至 5 億)":
                        sub = seg[(seg["組"] == "4 只不過市值閘") &
                                  (seg["mcap"] >= MCAP_SMALL)]
                    elif gname == "4b 只不過市值閘(低於 1 億)":
                        sub = seg[(seg["組"] == "4 只不過市值閘") &
                                  (seg["mcap"] < MCAP_SMALL)]
                    else:
                        sub = seg[seg["組"] == gname]
                    if len(sub) == 0:
                        continue
                    for h in HORIZONS:
                        rec = {"流動性口徑": liq_label, "負債閘口徑": debt_caliber,
                               "年份段": yr_label, "組": gname, "期": h, "主口徑": 主}
                        rec.update(cell(sub, h, do_boot=主))
                        rows.append(rec)
    out = pd.DataFrame(rows)
    out["期"] = pd.Categorical(out["期"], categories=HORIZONS, ordered=True)
    out["組"] = pd.Categorical(out["組"], categories=GROUP_ORDER, ordered=True)
    return out.sort_values(["流動性口徑", "負債閘口徑", "年份段", "組", "期"])


def build_two_gate_detail(ev: pd.DataFrame) -> pd.DataFrame:
    """『不過兩閘』細分三種組合(主口徑,12 個月)。"""
    base = ev[ev["資料底線"] & ev["過流動性閘"]].copy()
    base["組"] = assign_group(base, "可判")
    seg = base[base["組"] == "5 不過兩閘(補完)"]
    rows = []
    combos = {
        "不過 負債+現金流(市值過)": (~seg["過負債閘"]) & (~seg["過現金流閘"]) & seg["過市值閘"],
        "不過 負債+市值(現金流過)": (~seg["過負債閘"]) & seg["過現金流閘"] & (~seg["過市值閘"]),
        "不過 現金流+市值(負債過)": seg["過負債閘"] & (~seg["過現金流閘"]) & (~seg["過市值閘"]),
    }
    for name, m in combos.items():
        sub = seg[m]
        if len(sub) == 0:
            continue
        for h in HORIZONS:
            rec = {"組合": name, "期": h}
            rec.update(cell(sub, h, do_boot=False))
            rows.append(rec)
    return pd.DataFrame(rows)


def build_marginal(ev: pd.DataFrame) -> pd.DataFrame:
    """逐閘邊際:其他兩閘固定為『皆過』時,這道閘過 vs 不過(12 個月,主口徑)。
    另出『不設條件』版:全體可判事件,單看這道閘過 vs 不過。"""
    base = ev[ev["資料底線"] & ev["過流動性閘"] & ev["負債閘可判"]].copy()
    gates = {"負債閘": "過負債閘", "現金流閘": "過現金流閘", "市值閘": "過市值閘"}
    rows = []
    for gname, gcol in gates.items():
        others = [c for c in gates.values() if c != gcol]
        cond_mask = base[others[0]] & base[others[1]]
        for cond_label, mask in (("其他兩閘皆過", cond_mask),
                                 ("不設條件(全體可判)", pd.Series(True, index=base.index))):
            seg = base[mask]
            for pass_label, sub in ((f"過{gname}", seg[seg[gcol]]),
                                    (f"不過{gname}", seg[~seg[gcol]])):
                if len(sub) == 0:
                    continue
                for h in HORIZONS:
                    rec = {"閘": gname, "條件": cond_label, "格": pass_label, "期": h}
                    rec.update(cell(sub, h, do_boot=(cond_label == "其他兩閘皆過" and h == "12m")))
                    rows.append(rec)
    return pd.DataFrame(rows)


def build_top_winners(ev: pd.DataFrame, n_top: int = 50) -> tuple[pd.DataFrame, dict]:
    """全體觸發十二個月超額前 N 筆(只剔拆股基準可疑,不設流動性閘),逐筆標去向。"""
    base = ev[ev["資料底線"] & (ev["A_12m_status"] == "已成熟")].copy()
    base["組_可判"] = assign_group(base, "可判")
    base["負債閘狀態"] = np.where(~base["負債閘可判"], "資料不足",
                                  np.where(base["過負債閘"], "過", "不過"))
    top = base.nlargest(n_top, "A_12m_excess").copy()
    cols = ["primary_ticker", "name", "trigger_date", "A_12m_excess", "A_12m_mdd",
            "mcap", "cash", "total_debt_gatefix", "total_debt_source_gatefix",
            "ttm_ocf", "dollar_vol_60d", "過現金流閘", "過市值閘", "負債閘狀態",
            "過流動性閘", "組_可判", "industry_kill", "pos_sma200", "trigger_year",
            "is_foreign_filer", "sic_description"]
    top = top[cols].rename(columns={
        "primary_ticker": "代號", "name": "公司", "trigger_date": "觸發日",
        "A_12m_excess": "十二個月超額", "A_12m_mdd": "期內最大跌幅", "mcap": "觸發日市值",
        "cash": "現金", "total_debt_gatefix": "總債務(gatefix)",
        "total_debt_source_gatefix": "債務來源", "ttm_ocf": "滾動四季經營現金流",
        "dollar_vol_60d": "近60日中位成交金額", "組_可判": "落組",
        "industry_kill": "軸一", "pos_sma200": "軸二", "trigger_year": "觸發年",
        "is_foreign_filer": "外國申報人", "sic_description": "SIC 行業"})

    tot = len(top)
    summ: dict = {"全體已成熟事件(剔拆股基準可疑)": int(len(base)), "取前N": tot}
    summ["前50過三閘比例"] = float((top["落組"] == "1 過三閘(現行①池)").mean())
    summ["前50過三閘數"] = int((top["落組"] == "1 過三閘(現行①池)").sum())
    summ["前50各組分佈"] = {k: int(v) for k, v in top["落組"].value_counts().items()}
    for gname, col, ok in (("現金流閘", "過現金流閘", True), ("市值閘", "過市值閘", True)):
        summ[f"前50不過{gname}數"] = int((~top[col]).sum())
    summ["前50負債閘不過數"] = int((top["負債閘狀態"] == "不過").sum())
    summ["前50負債閘資料不足數"] = int((top["負債閘狀態"] == "資料不足").sum())
    summ["前50負債閘過數"] = int((top["負債閘狀態"] == "過").sum())
    summ["前50不過流動性閘數"] = int((~top["過流動性閘"]).sum())
    # 「被哪道閘剔走最多」:在不過三閘的前 50 筆之中,逐閘計數(可重複)
    lost = top[top["落組"] != "1 過三閘(現行①池)"]
    summ["前50被剔走數"] = int(len(lost))
    summ["被剔走者逐閘計數(可重複)"] = {
        "現金流閘": int((~lost["過現金流閘"]).sum()),
        "市值閘": int((~lost["過市值閘"]).sum()),
        "負債閘(不過)": int((lost["負債閘狀態"] == "不過").sum()),
        "負債閘(資料不足)": int((lost["負債閘狀態"] == "資料不足").sum()),
    }
    summ["被剔走者唯一致命閘計數"] = {
        k: int(v) for k, v in lost["落組"].value_counts().items()}
    # 同一件事,加了流動性閘之後
    base_liq = base[base["過流動性閘"]]
    top_liq = base_liq.nlargest(n_top, "A_12m_excess")
    summ["含流動性閘版前50過三閘比例"] = float(
        (assign_group(top_liq, "可判") == "1 過三閘(現行①池)").mean())
    # 極端贏家門檻對照:全體 vs 過三閘組的右尾
    for label, sub in (("全體", base), ("過三閘", base[base["組_可判"] == "1 過三閘(現行①池)"])):
        ex = sub["A_12m_excess"].to_numpy(dtype=float)
        summ[f"{label}_樣本"] = int(len(ex))
        summ[f"{label}_超額>=+100%比例"] = float(np.mean(ex >= 1.0))
        summ[f"{label}_超額>=+300%比例"] = float(np.mean(ex >= 3.0))
        summ[f"{label}_最大超額"] = float(np.max(ex))
    return top, summ


def build_drop_one_gate(ev: pd.DataFrame) -> pd.DataFrame:
    """拆掉其中一道閘之後,合併池的平均超額與保命指標怎樣變(12 個月,主口徑)。
    基準池 = 過三閘 + 流動性閘;逐道閘把『只不過這道閘』那組併回去。"""
    base = ev[ev["資料底線"] & ev["過流動性閘"] & ev["負債閘可判"] &
              (ev["A_12m_status"] == "已成熟")].copy()
    base["組"] = assign_group(base, "可判")
    pool0 = base[base["組"] == "1 過三閘(現行①池)"]

    def stat(sub, label):
        ex = sub["A_12m_excess"].to_numpy(dtype=float)
        mdd = sub["A_12m_mdd"].to_numpy(dtype=float)
        ex_s = np.sort(ex)
        k1 = max(1, int(np.ceil(len(ex) * 0.01)))
        return {"池": label, "樣本N": len(ex), "勝率": float(np.mean(ex > 0)),
                "中位超額": float(np.median(ex)), "平均超額": float(np.mean(ex)),
                "剔走前1%後平均": float(np.mean(ex_s[:-k1])),
                "觸及負33比例": float(np.mean(mdd <= -0.33)),
                "觸及負80比例": float(np.mean(mdd <= -0.80)),
                "中位期內最大跌幅": float(np.median(mdd))}

    rows = [stat(pool0, "基準:過三閘 + 流動性閘")]
    for gname, grp in (("市值閘", "4 只不過市值閘"), ("負債閘", "2 只不過負債閘"),
                       ("現金流閘", "3 只不過現金流閘")):
        add = base[base["組"] == grp]
        merged = pd.concat([pool0, add])
        r = stat(merged, f"拆掉{gname}(併回「只不過{gname}」組)")
        r["併回事件數"] = len(add)
        r["平均超額變動(百分點)"] = (r["平均超額"] - rows[0]["平均超額"]) * 100
        r["觸及負80變動(百分點)"] = (r["觸及負80比例"] - rows[0]["觸及負80比例"]) * 100
        r["觸及負33變動(百分點)"] = (r["觸及負33比例"] - rows[0]["觸及負33比例"]) * 100
        rows.append(r)
    return pd.DataFrame(rows)


def build_survivorship_breakeven(ev: pd.DataFrame) -> pd.DataFrame:
    """倖存者破口:每組要有幾多比例的事件『缺席而且全損』,平均才會歸零 /
    才會跌回過三閘組的水平。缺席事件一律當超額 −100%(即 −1.0)。"""
    base = ev[ev["資料底線"] & ev["過流動性閘"] &
              (ev["A_12m_status"] == "已成熟")].copy()
    base["組"] = assign_group(base, "可判")
    ref = base[base["組"] == "1 過三閘(現行①池)"]["A_12m_excess"].astype(float).mean()
    rows = []
    for gname in GROUP_ORDER:
        if gname == "0 全部觸發(不分閘)":
            sub = base
        elif gname.startswith("4a"):
            sub = base[(base["組"] == "4 只不過市值閘") & (base["mcap"] >= MCAP_SMALL)]
        elif gname.startswith("4b"):
            sub = base[(base["組"] == "4 只不過市值閘") & (base["mcap"] < MCAP_SMALL)]
        else:
            sub = base[base["組"] == gname]
        n = len(sub)
        if n < MIN_CELL:
            continue
        mu = float(sub["A_12m_excess"].astype(float).mean())

        def need(target):
            # (n*mu - m) / (n + m) = target  ->  m = n*(mu - target) / (1 + target)
            if mu <= target:
                return np.nan
            m = n * (mu - target) / (1.0 + target)
            return float(m / (n + m))

        rows.append({"組": gname, "樣本N": n, "平均超額": mu,
                     "缺席全損多少比例才歸零": need(0.0),
                     "缺席全損多少比例才跌回過三閘水平": need(ref) if gname != "1 過三閘(現行①池)" else np.nan})
    return pd.DataFrame(rows)


def build_tradability(ev: pd.DataFrame) -> dict:
    """極端贏家可不可以真的買到:按近 60 日中位成交金額分層。"""
    base = ev[ev["資料底線"] & (ev["A_12m_status"] == "已成熟")].copy()
    ex = base["A_12m_excess"].astype(float)
    dv = base["dollar_vol_60d"].astype(float)
    out: dict = {}
    bins = [(0, 1e5, "低於 10 萬"), (1e5, 1e6, "10 萬至 100 萬"),
            (1e6, 3e6, "100 萬至 300 萬"), (3e6, np.inf, "300 萬或以上(過流動性閘)")]
    for thr, label in ((1.0, "超額>=+100%"), (3.0, "超額>=+300%"), (10.0, "超額>=+1000%")):
        m = ex >= thr
        d = {"事件數": int(m.sum())}
        for lo, hi, bl in bins:
            d[bl] = int(((dv >= lo) & (dv < hi) & m).sum())
        d["過流動性閘比例"] = float((dv[m] >= LIQ_MIN).mean()) if m.sum() else np.nan
        d["成交金額中位"] = float(np.median(dv[m])) if m.sum() else np.nan
        out[label] = d
    d = {"事件數": int(len(base))}
    for lo, hi, bl in bins:
        d[bl] = int(((dv >= lo) & (dv < hi)).sum())
    d["過流動性閘比例"] = float((dv >= LIQ_MIN).mean())
    d["成交金額中位"] = float(np.median(dv))
    out["全體已成熟事件"] = d
    return out


def known_case_check(ev: pd.DataFrame) -> list[dict]:
    """派工列的三筆個案,逐筆核落組。"""
    want = [("AXTI", "2025-05-07"), ("BE", "2024-10-11"), ("BE", "2025-04-21")]
    base = ev.copy()
    base["組_可判"] = assign_group(base, "可判")
    out = []
    for tk, d in want:
        m = base[(base["primary_ticker"] == tk) & (base["trigger_date"] == pd.Timestamp(d))]
        if len(m) == 0:
            out.append({"代號": tk, "觸發日": d, "結果": "事件表無此筆"})
            continue
        r = m.iloc[0]
        out.append({
            "代號": tk, "觸發日": d,
            "十二個月超額": float(r["A_12m_excess"]),
            "市值": float(r["mcap"]), "現金": float(r["cash"]),
            "總債務(gatefix)": (None if pd.isna(r["total_debt_gatefix"])
                                else float(r["total_debt_gatefix"])),
            "滾動四季經營現金流": float(r["ttm_ocf"]),
            "過現金流閘": bool(r["過現金流閘"]), "過市值閘": bool(r["過市值閘"]),
            "過負債閘": bool(r["過負債閘"]), "負債閘可判": bool(r["負債閘可判"]),
            "近60日中位成交金額": float(r["dollar_vol_60d"]),
            "過流動性閘": bool(r["過流動性閘"]),
            "落組": str(r["組_可判"]),
        })
    return out


def main() -> None:
    ev = load_events()
    info: dict = {
        "事件表列數": int(len(ev)),
        "資料底線(剔拆股基準可疑)後": int(ev["資料底線"].sum()),
        "再加流動性閘後": int((ev["資料底線"] & ev["過流動性閘"]).sum()),
        "負債閘資料不足": int((~ev["負債閘可判"]).sum()),
    }

    groups = build_group_tables(ev)
    groups.to_csv(OUT / "gate_groups_gatecost.csv", index=False, encoding="utf-8-sig")

    two = build_two_gate_detail(ev)
    two.to_csv(OUT / "gate_two_fail_detail_gatecost.csv", index=False, encoding="utf-8-sig")

    marg = build_marginal(ev)
    marg.to_csv(OUT / "gate_marginal_gatecost.csv", index=False, encoding="utf-8-sig")

    top, summ = build_top_winners(ev)
    top.to_csv(OUT / "top_winners_gatecost.csv", index=False, encoding="utf-8-sig")
    top_liq, summ_liq = build_top_winners(ev[ev["過流動性閘"]])
    top_liq.to_csv(OUT / "top_winners_liquid_gatecost.csv", index=False, encoding="utf-8-sig")

    drop1 = build_drop_one_gate(ev)
    drop1.to_csv(OUT / "gate_drop_one_gatecost.csv", index=False, encoding="utf-8-sig")
    surv = build_survivorship_breakeven(ev)
    surv.to_csv(OUT / "gate_survivorship_breakeven_gatecost.csv", index=False, encoding="utf-8-sig")

    info["極端贏家"] = summ
    info["極端贏家(只計過流動性閘者)"] = summ_liq
    info["極端贏家可成交性"] = build_tradability(ev)
    info["拆掉一道閘"] = drop1.to_dict("records")
    info["倖存者破口"] = surv.to_dict("records")
    info["已知個案核對"] = known_case_check(ev)
    # 主口徑五組的組別計數(全期)
    base = ev[ev["資料底線"] & ev["過流動性閘"]].copy()
    base["組"] = assign_group(base, "可判")
    info["主口徑各組事件數"] = {k: int(v) for k, v in base["組"].value_counts().items()}
    info["主口徑各組公司數"] = {k: int(v) for k, v in
                                base.groupby("組", observed=True)["entity_id"].nunique().items()}

    with open(OUT / "gate_summary_gatecost.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2, default=str)

    print(json.dumps(info, ensure_ascii=False, indent=2, default=str))
    main_tbl = groups[groups["主口徑"] & (groups["年份段"] == "全期 2010-2026") &
                      (groups["期"] == "12m")]
    cols = ["組", "樣本N", "勝率", "勝率下限", "勝率上限", "中位超額", "平均超額",
            "平均盈虧比", "中位盈虧比", "前1%佔總超額比例", "剔走前1%後平均",
            "觸及負33比例", "觸及負80比例", "中位期內最大跌幅"]
    print(main_tbl[cols].to_string(index=False))


if __name__ == "__main__":
    main()
