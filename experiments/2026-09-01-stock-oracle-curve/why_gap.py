"""KARST-139 補充二:拆解「曲線預測 15%、真規則只跑到 8.7%」那道缺口。

兩個候選成因:
  甲 揀嘢質素:規則揀的六隻,平均回報本身就低過同池隨機抽六隻(算術平均之差)
  乙 集中度:規則六隻同一種曝險、一齊升一齊跌,波動拖累食走複利
      (算術平均相同但幾何平均差得遠)
分辨法:同時報算術月均與幾何年化,以及月度標準差。

另外量:神諭揀中那批股票在同月宇宙裡的市值百分位——如果神諭系統性揀最細那批,
15 個基點滑點就唔夠,上限係買唔到的。

輸出 out/why_gap.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from oracle_curve import (DATA, HOLD_M, MIN_MEMBERS, OUT, SIDE_BP_MAIN, TOP_N,
                          apply_cost, build_months, cagr, load)


def main() -> None:
    m, _, _ = load("main")
    months = build_months(m)
    piv = m.pivot_table(index="month_end", columns="symbol", values="ret").sort_index()
    sig_mom = (1.0 + piv).shift(2).rolling(11).apply(np.prod, raw=True) - 1.0
    sig_prev = piv.shift(1)
    etf_of = m.drop_duplicates("symbol").set_index("symbol")["etf"]

    res = {}
    rng = np.random.default_rng(20260906)
    for nm, sig in (("買上月頭六名", sig_prev), ("12-1 動能頭六名", sig_mom)):
        rr, pool_ew, rand6, hit = [], [], [], []
        for mo in months:
            me = mo["month_end"]
            if me not in sig.index:
                continue
            g = m[m["month_end"] == me]
            s = sig.loc[me].dropna()
            s = s[s.index.isin(g["symbol"])]
            if len(s) < HOLD_M:
                continue
            d = pd.DataFrame({"sym": s.index, "sig": s.to_numpy()})
            d["etf"] = d["sym"].map(etf_of)
            cnt = g.groupby("etf").size()
            d = d[d["etf"].map(cnt).ge(MIN_MEMBERS)]
            pool = d.sort_values("sig", ascending=False).groupby("etf").head(TOP_N)
            pick = pool.nlargest(HOLD_M, "sig")["sym"].tolist()
            if len(pick) < HOLD_M:
                continue
            rmap = g.set_index("symbol")["ret"]
            pr = rmap.reindex(pool["sym"]).dropna()
            rr.append(float(rmap.reindex(pick).mean()))
            pool_ew.append(float(pr.mean()))
            rand6.append(float(pr.sample(HOLD_M, random_state=int(rng.integers(1e9))).mean()))
            hit.append(len(set(pick) & set(mo["hold_syms"])) / HOLD_M)
        a = np.array(rr); b = np.array(pool_ew); c = np.array(rand6)
        an = apply_cost(a, SIDE_BP_MAIN); cn = apply_cost(c, SIDE_BP_MAIN)
        res[nm] = {
            "月數": len(a), "命中率%": round(float(np.mean(hit)) * 100, 3),
            "規則六隻 算術月均%": round(float(a.mean()) * 100, 3),
            "同池 27 隻等權 算術月均%": round(float(b.mean()) * 100, 3),
            "同池隨機六隻 算術月均%": round(float(c.mean()) * 100, 3),
            "規則六隻 月度標準差%": round(float(a.std(ddof=1)) * 100, 2),
            "同池隨機六隻 月度標準差%": round(float(c.std(ddof=1)) * 100, 2),
            "同池 27 隻 月度標準差%": round(float(b.std(ddof=1)) * 100, 2),
            "規則六隻 年化%": round(cagr(an) * 100, 2),
            "同池隨機六隻 年化%": round(cagr(cn) * 100, 2),
            "同池 27 隻等權 年化%": round(cagr(apply_cost(b, SIDE_BP_MAIN)) * 100, 2),
        }
        print(nm, json.dumps(res[nm], ensure_ascii=False))

    # ---- 神諭揀中那批的市值位置 ----
    panel = pd.read_parquet(
        DATA.parent.parent / "2026-09-02-multiples-oracle-scan" / "data"
        / "constituent_panel.parquet", columns=["symbol", "month_end", "mcap"])
    mc = panel.set_index(["symbol", "month_end"])["mcap"]
    pct_u, pct_s, sizes = [], [], []
    for mo in months:
        me = mo["month_end"]
        g = m[m["month_end"] == me].copy()
        g["mcap"] = [mc.get((s, me), np.nan) for s in g["symbol"]]
        g = g.dropna(subset=["mcap"])
        if len(g) < 50:
            continue
        g["pu"] = g["mcap"].rank(pct=True)
        g["ps"] = g.groupby("etf")["mcap"].rank(pct=True)
        sel = g[g["symbol"].isin(mo["hold_syms"])]
        pct_u.extend(sel["pu"].tolist())
        pct_s.extend(sel["ps"].tolist())
        sizes.extend((sel["mcap"] / 1e9).tolist())
    res["神諭持倉市值位置"] = {
        "格數": len(pct_u),
        "全宇宙市值百分位 中位": round(float(np.median(pct_u)) * 100, 1),
        "全宇宙市值百分位 平均": round(float(np.mean(pct_u)) * 100, 1),
        "行內市值百分位 中位": round(float(np.median(pct_s)) * 100, 1),
        "市值中位(十億美元)": round(float(np.median(sizes)), 2),
        "市值第一四分位(十億美元)": round(float(np.percentile(sizes, 25)), 2),
        "落在全宇宙市值最細三成的比例%": round(float(np.mean(np.array(pct_u) < 0.3)) * 100, 1),
    }
    print(json.dumps(res["神諭持倉市值位置"], ensure_ascii=False, indent=1))

    (OUT / "why_gap.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                      encoding="utf-8")


if __name__ == "__main__":
    main()
