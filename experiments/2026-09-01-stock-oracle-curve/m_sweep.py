"""KARST-139 補充三:持倉隻數 M 的架構敏感度。

為什麼要跑:why_gap.py 顯示真規則輸的原因不是揀得差(12-1 動能的算術月均
1.281% 高過同池的 1.099%),而是六隻同一種曝險一齊波動——月度標準差 7.55%
對同池隨機六隻的 5.40%,複利拖累食光個優勢。M = 6 是方案書的示例值(對齊項
#11),不是定案。所以量一次「M 大一點,那個優勢守不守得住」。

★ 這不是參數搜尋,亦不得當作對齊建議。 報的是整幅面,看的是形狀
(集中度懲罰是不是主因),不是找最高那一格;由這幅面讀出一個「最好的 M」
正正是 D-048/D-049 明文禁止的擬合。

輸出 out/m_sweep.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from oracle_curve import (MIN_MEMBERS, OUT, SIDE_BP_MAIN, apply_cost, build_months,
                          cagr, load, maxdd)

GRID_N = [3, 5]
GRID_M = [6, 10, 15, 20, 30, 45]


def run(m: pd.DataFrame, months, sig: pd.DataFrame, etf_of, top_n: int, hold_m: int):
    rr = []
    for mo in months:
        me = mo["month_end"]
        if me not in sig.index:
            continue
        g = m[m["month_end"] == me]
        s = sig.loc[me].dropna()
        s = s[s.index.isin(g["symbol"])]
        if len(s) < hold_m:
            continue
        d = pd.DataFrame({"sym": s.index, "sig": s.to_numpy()})
        d["etf"] = d["sym"].map(etf_of)
        cnt = g.groupby("etf").size()
        d = d[d["etf"].map(cnt).ge(MIN_MEMBERS)]
        pool = d.sort_values("sig", ascending=False).groupby("etf").head(top_n)
        if len(pool) < hold_m:
            continue
        pick = pool.nlargest(hold_m, "sig")["sym"]
        rmap = g.set_index("symbol")["ret"]
        rr.append(float(rmap.reindex(pick).dropna().mean()))
    if len(rr) < 100:
        return None
    net = apply_cost(np.array(rr), SIDE_BP_MAIN)
    return {"月數": len(rr), "年化%": round(cagr(net) * 100, 2),
            "月度標準差%": round(float(np.std(rr, ddof=1)) * 100, 2),
            "算術月均%": round(float(np.mean(rr)) * 100, 3),
            "最大跌幅%": round(maxdd(net) * 100, 1)}


def oracle_at(m: pd.DataFrame, months, top_n: int, hold_m: int):
    rr = []
    for mo in months:
        g = m[m["month_end"] == mo["month_end"]]
        pool = []
        for etf, gs in g.groupby("etf"):
            if len(gs) < MIN_MEMBERS:
                continue
            pool.append(gs.nlargest(min(top_n, len(gs)), "ret"))
        pool = pd.concat(pool)
        if len(pool) < hold_m:
            continue
        rr.append(float(pool.nlargest(hold_m, "ret")["ret"].mean()))
    net = apply_cost(np.array(rr), SIDE_BP_MAIN)
    return round(cagr(net) * 100, 2)


def main() -> None:
    m, _, _ = load("main")
    months = build_months(m)
    piv = m.pivot_table(index="month_end", columns="symbol", values="ret").sort_index()
    sigs = {"買上月頭六名": piv.shift(1),
            "12-1 動能": (1.0 + piv).shift(2).rolling(11).apply(np.prod, raw=True) - 1.0}
    etf_of = m.drop_duplicates("symbol").set_index("symbol")["etf"]

    rows = []
    for n in GRID_N:
        for mm in GRID_M:
            if mm > 9 * n:
                continue
            row = {"行內頭N": n, "持倉M": mm, "神諭上限年化%": oracle_at(m, months, n, mm)}
            for nm, sg in sigs.items():
                r = run(m, months, sg, etf_of, n, mm)
                if r:
                    row[f"{nm} 年化%"] = r["年化%"]
                    row[f"{nm} 標準差%"] = r["月度標準差%"]
                    row[f"{nm} 算術月均%"] = r["算術月均%"]
                    row[f"{nm} 最大跌幅%"] = r["最大跌幅%"]
            rows.append(row)
            print(row)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "m_sweep.csv", index=False, encoding="utf-8-sig")
    print("\n", df.to_string(index=False))


if __name__ == "__main__":
    main()
