# -*- coding: utf-8 -*-
"""KARST-160 第四步:迷因過濾器五條規則 + 組合,量誤殺率與捕捉率。
規則在名單上設計,即樣本內;本檔只作提案,不產生及格。照 RULES.md 第六節。
"""
import itertools
import json
import os

import numpy as np
import pandas as pd

ROOT = r"C:\projects\Karst"
BASE = os.path.join(ROOT, "experiments", "2026-09-02-tenbagger-scan")
OUT = os.path.join(BASE, "out")
DATA = os.path.join(BASE, "data")
P_EXIST = os.path.join(ROOT, "experiments", "2026-09-02-timing-sweep", "data", "daily_close.parquet")
P_NEW = os.path.join(ROOT, "experiments", "2026-09-02-narrative-layers-v2", "data", "new_close.parquet")
P_PANEL = os.path.join(ROOT, "experiments", "2026-09-02-panel-scale-fix", "out", "panel_monthly_v2.parquet")
P_SPLIT = os.path.join(ROOT, "experiments", "2026-09-02-fourpiece-test", "data", "splits.parquet")
CONTAMINATED = {"CPWR", "EP", "PARA"}

RULES = {
    "R1_股數增發": "前 12 個月攤薄股數增加 > 10%",
    "R2_無營業額而市值高": "無 TTM 營業額,或 市值 ÷ TTM 營業額 > 50 倍",
    "R3_燒錢靠增發": "TTM 經營現金流 < 0,而且前 12 個月股數增加 > 5%",
    "R4_已經跑掉": "過去 12 個月股價升幅 > 200%",
    "R5_上市未滿兩年": "首個有價日至今不足 24 個月",
}


def split_factor(tickers, month_ends, splits):
    f = np.ones(len(tickers))
    for i, (t, m) in enumerate(zip(tickers, month_ends)):
        g = splits.get(t)
        if g is None:
            continue
        f[i] = float(np.prod([r for d, r in g if d > m])) if len(g) else 1.0
    return f


def load_splits(path, exclude=()):
    sp = pd.read_parquet(path)
    sp["report_date"] = pd.to_datetime(sp["report_date"])
    out = {}
    for s, g in sp.groupby("symbol"):
        if s in exclude:
            continue
        out[s] = list(zip(g["report_date"].to_numpy(), g["ratio"].to_numpy()))
    return out


def price_features(px):
    """逐月底:12 個月價格升幅、上市月數。"""
    idx = px.index
    s = pd.Series(idx, index=idx)
    me = pd.DatetimeIndex(sorted(s.groupby([idx.year, idx.month]).max().values))
    m = px.reindex(me)
    ret12 = m / m.shift(12) - 1
    age = pd.DataFrame(index=me, columns=px.columns, dtype=float)
    for t in px.columns:
        fv = px[t].first_valid_index()
        age[t] = np.where(me >= fv, (me - fv).days / 30.44, np.nan) if fv is not None else np.nan
    return m, ret12, age


def build_cells(px, panel, splits, tickers):
    m, ret12, age = price_features(px[tickers])
    long = []
    for t in tickers:
        d = pd.DataFrame({"month_end": m.index, "close": m[t].values,
                          "ret12": ret12[t].values, "age_m": age[t].values})
        d["ticker"] = t
        long.append(d)
    L = pd.concat(long, ignore_index=True).dropna(subset=["close"])
    P = panel.copy()
    P = P.sort_values(["ticker", "month_end"])
    g = P.groupby("ticker", sort=False)
    P["sf"] = split_factor(P["ticker"].to_numpy(), P["month_end"].to_numpy(), splits)
    P["shares_adj"] = P["diluted_shares"] * P["sf"]
    P.loc[P.ticker.isin(CONTAMINATED), "shares_adj"] = np.nan
    P["shares_chg_12m"] = P["shares_adj"] / g["shares_adj"].shift(12) - 1
    C = L.merge(P[["ticker", "month_end", "shares_adj", "shares_chg_12m",
                   "revenue_ttm", "cfo_ttm"]], on=["ticker", "month_end"], how="left")
    C["mcap"] = C["close"] * C["shares_adj"]
    C["ps"] = C["mcap"] / C["revenue_ttm"].where(C["revenue_ttm"] > 0)
    return C


def apply_rules(C):
    R = pd.DataFrame(index=C.index)
    R["R1_股數增發"] = np.where(C.shares_chg_12m.notna(), C.shares_chg_12m > 0.10, np.nan)
    no_rev = C.revenue_ttm.notna() & (C.revenue_ttm <= 0)
    hi_ps = C.ps.notna() & (C.ps > 50)
    ok2 = C.mcap.notna() & C.revenue_ttm.notna()
    R["R2_無營業額而市值高"] = np.where(ok2, (no_rev | hi_ps), np.nan)
    ok3 = C.cfo_ttm.notna() & C.shares_chg_12m.notna()
    R["R3_燒錢靠增發"] = np.where(ok3, (C.cfo_ttm < 0) & (C.shares_chg_12m > 0.05), np.nan)
    R["R4_已經跑掉"] = np.where(C.ret12.notna(), C.ret12 > 2.0, np.nan)
    R["R5_上市未滿兩年"] = np.where(C.age_m.notna(), C.age_m < 24, np.nan)
    return R


def rate(mask, fired):
    ok = fired.notna() & mask
    n = int(ok.sum())
    return (round(float(fired[ok].astype(float).mean()), 4) if n else None), n


def main():
    px = pd.read_parquet(P_EXIST).join(pd.read_parquet(P_NEW), how="outer").sort_index()
    pan = pd.read_parquet(P_PANEL, columns=["ticker", "month_end", "diluted_shares",
                                            "revenue_ttm", "cfo_ttm"])
    sp = load_splits(P_SPLIT, exclude=CONTAMINATED)
    wm = pd.read_parquet(os.path.join(OUT, "window_multiples.parquet"))
    wm5 = wm[wm.horizon == "5y"][["ticker", "t0", "multiple"]]
    uni = sorted(set(wm5.ticker.unique()) & set(px.columns))

    U = build_cells(px, pan, sp, uni)
    U = U.merge(wm5.rename(columns={"t0": "month_end"}), on=["ticker", "month_end"], how="inner")
    U["is10x"] = U.multiple >= 10
    RU = apply_rules(U)
    U.to_parquet(os.path.join(OUT, "filter_cells_universe.parquet"), index=False)

    # ---- 反例 ----
    cpx = pd.read_parquet(os.path.join(DATA, "counterexample_close.parquet"))
    cpan = pd.read_parquet(os.path.join(DATA, "counterexample_panel.parquet"))
    csp = load_splits(os.path.join(DATA, "counterexample_splits.parquet"))
    ctk = list(cpx.columns)
    Cc = build_cells(cpx, cpan, csp, ctk)
    # 峰前窗:首月至歷史最高收市那個月(買在這段之內,之後都要蝕逾八成)
    peak_m = {t: cpx[t].idxmax() for t in ctk}
    Cc["is_prepeak"] = [r.month_end <= peak_m[r.ticker] for r in Cc.itertuples()]
    # 主捕捉窗:峰前 12 個月(狂熱期,買在這一段之後跌逾八成);全峰前只作對照
    Cc["is_mania"] = [(r.month_end <= peak_m[r.ticker]) and
                      (r.month_end >= peak_m[r.ticker] - pd.DateOffset(months=12))
                      for r in Cc.itertuples()]
    RC = apply_rules(Cc)
    Cc.to_parquet(os.path.join(OUT, "filter_cells_counterexamples.parquet"), index=False)

    # ---- 逐條規則 ----
    rows = []
    tenx = U.is10x
    mania = Cc.is_mania
    pre = Cc.is_prepeak
    best = U[U.is10x].loc[U[U.is10x].groupby("ticker")["multiple"].idxmax()]
    for r in RULES:
        fk, n_fk = rate(tenx, RU[r])
        cap, n_cap = rate(mania, RC[r])
        cap_all, n_cap_all = rate(pre, RC[r])
        bf = RU.loc[best.index, r]
        fk_name = round(float(bf.dropna().astype(float).mean()), 4) if bf.notna().any() else None
        capn = []
        for t, g in Cc[mania].groupby("ticker"):
            v = RC.loc[g.index, r].dropna().astype(float)
            if len(v):
                capn.append(v.mean() >= 0.5)
        rows.append({
            "rule": r, "定義": RULES[r],
            "誤殺率_格級": fk, "十倍格數": n_fk,
            "誤殺率_名單級_最佳t0": fk_name,
            "十倍家數_有欄位": int(bf.notna().sum()),
            "捕捉率_狂熱期": cap, "狂熱期格數": n_cap,
            "捕捉率_全峰前": cap_all, "全峰前格數": n_cap_all,
            "捕捉家數_過半月份": int(sum(capn)), "反例家數_有欄位": len(capn),
        })
    tab = pd.DataFrame(rows)
    tab.to_csv(os.path.join(OUT, "meme_filter_rules.csv"), index=False, encoding="utf-8-sig")
    print(tab.to_string(index=False))

    # ---- 組合(任何一條中即剔)----
    combos = []
    names = list(RULES)
    for k in range(1, 6):
        for c in itertools.combinations(names, k):
            # 共同分母:只算五條成分規則全部算得出的格,免得不同組合各用各的分母
            fu = RU[list(c)].astype(float)
            fc = RC[list(c)].astype(float)
            fire_u = fu.max(axis=1).where(fu.notna().all(axis=1))
            fire_c = fc.max(axis=1).where(fc.notna().all(axis=1))
            # 實務版:算得出哪條就用哪條(至少一條算得出即作數),缺欄位不當放行
            pu = fu.max(axis=1).where(fu.notna().any(axis=1))
            pc = fc.max(axis=1).where(fc.notna().any(axis=1))
            fk, n_fk = rate(tenx, fire_u)
            cap, n_cap = rate(mania, fire_c)
            cap_all, n_cap_all = rate(pre, fire_c)
            pfk, n_pfk = rate(tenx, pu)
            pcap, n_pcap = rate(mania, pc)
            capn, pcapn = [], []
            for t, g in Cc[mania].groupby("ticker"):
                v = fire_c.loc[g.index].dropna()
                if len(v):
                    capn.append(v.mean() >= 0.5)
                v2 = pc.loc[g.index].dropna()
                if len(v2):
                    pcapn.append(v2.mean() >= 0.5)
            combos.append({"combo": "+".join(c), "k": k,
                           "誤殺率": fk, "捕捉率_狂熱期": cap, "捕捉率_全峰前": cap_all,
                           "捕捉家數": int(sum(capn)), "反例家數": len(capn),
                           "淨值_捕捉減誤殺": (round(cap - fk, 4) if (cap is not None and fk is not None) else None),
                           "十倍格數": n_fk, "狂熱期格數": n_cap, "全峰前格數": n_cap_all,
                           "實務_誤殺率": pfk, "實務_捕捉率": pcap,
                           "實務_捕捉家數": int(sum(pcapn)), "實務_反例家數": len(pcapn),
                           "實務_淨值": (round(pcap - pfk, 4) if (pcap is not None and pfk is not None) else None),
                           "實務_十倍格數": n_pfk, "實務_狂熱期格數": n_pcap})
    cb = pd.DataFrame(combos).sort_values("淨值_捕捉減誤殺", ascending=False)
    cb.to_csv(os.path.join(OUT, "meme_filter_combos.csv"), index=False, encoding="utf-8-sig")
    print()
    print(cb.head(12).to_string(index=False))

    json.dump({"universe_cells": int(len(U)), "tenx_cells": int(tenx.sum()),
               "counterexample_names": ctk,
               "counterexample_peak_month": {t: str(pd.Timestamp(v).date()) for t, v in peak_m.items()},
               "counterexample_prepeak_cells": int(pre.sum()), "counterexample_mania_cells": int(mania.sum())},
              open(os.path.join(OUT, "meme_filter_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
