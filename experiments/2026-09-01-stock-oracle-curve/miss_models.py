"""KARST-139 補充:兩個「揀唔中嗰陣揀咗啲乜」的替代模型。

主曲線(模型甲)假設「揀唔中就在全宇宙隨機揀」。這個假設決定整條曲線的高度,
而現實錨顯示它太寬鬆——兩條笨規則的命中率都高過名義打和線,實際回報仍然輸。
所以另跑兩個模型把這一格量清楚:

  模型乙「完美過濾器、排名退化」:揀唔中時在同月神諭 27 池(扣走神諭六隻)裡揀。
      答的問題:假設第一層名單完美,第二層排名要幾準先加得到價值。
  模型丙「現實式揀錯」:揀唔中時揀 12-1 動能規則當月會揀的名(該規則的 27 池)。
      答的問題:一條真規則錯的時候會錯成點,把這種錯法放進曲線,門檻會升幾多。

輸出 out/miss_models.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from oracle_curve import (DATA, FINE_GRID, HOLD_M, MIN_MEMBERS, OUT, SIDE_BP_MAIN,
                          TOP_N, apply_cost, build_months, cagr, cagr_rows, load)

N_PATHS = 800
RUNGS = [1.00, 0.90, 0.80, 0.70, 0.60, 0.50, 0.0]


def rule_pool(m: pd.DataFrame, months, sig: pd.DataFrame) -> dict:
    """一條規則當月會出的 27 池(照架構:行內頭 3)。"""
    etf_of = m.drop_duplicates("symbol").set_index("symbol")["etf"]
    out = {}
    for mo in months:
        me = mo["month_end"]
        if me not in sig.index:
            continue
        s = sig.loc[me].dropna()
        g = m[m["month_end"] == me]
        s = s[s.index.isin(g["symbol"])]
        if len(s) < HOLD_M:
            continue
        d = pd.DataFrame({"sym": s.index, "sig": s.to_numpy()})
        d["etf"] = d["sym"].map(etf_of)
        cnt = g.groupby("etf").size()
        d = d[d["etf"].map(cnt).ge(MIN_MEMBERS)]
        pool = d.sort_values("sig", ascending=False).groupby("etf").head(TOP_N)
        out[me] = pool["sym"].tolist()
    return out


def sim(months, miss_arrays, a: float, n_paths: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    T = len(months)
    gross = np.empty((n_paths, T))
    for j, mo in enumerate(months):
        hold = mo["hold_ret"]
        k = len(hold)
        non = miss_arrays[j]
        if a >= 1.0 or len(non) == 0:
            gross[:, j] = hold.mean()
            continue
        hits = rng.random((n_paths, k)) < a
        idx = rng.integers(0, len(non), size=(n_paths, k))
        gross[:, j] = np.where(hits, hold[None, :], non[idx]).mean(axis=1)
    return apply_cost(gross, SIDE_BP_MAIN)


def breakeven(frame: pd.DataFrame, target: float) -> float | None:
    x, y = frame["a"].to_numpy(), frame["med"].to_numpy()
    for i in range(1, len(x)):
        if (y[i - 1] - target) * (y[i] - target) <= 0 and y[i] != y[i - 1]:
            return float(x[i - 1] + (target - y[i - 1]) * (x[i] - x[i - 1])
                         / (y[i] - y[i - 1]))
    return None


def main() -> None:
    m, _, _ = load("main")
    months = build_months(m)
    dice = HOLD_M / float(np.mean([x["n_univ"] for x in months]))
    prev = json.load(open(OUT / "summary.json", encoding="utf-8"))
    benches = prev["benches"]

    piv = m.pivot_table(index="month_end", columns="symbol", values="ret").sort_index()
    sig_mom = (1.0 + piv).shift(2).rolling(11).apply(np.prod, raw=True) - 1.0
    mom_pool = rule_pool(m, months, sig_mom)

    ret_by_month = {mo["month_end"]: m[m["month_end"] == mo["month_end"]]
                    .set_index("symbol")["ret"] for mo in months}

    # 模型乙:揀唔中時在神諭 27 池(扣走神諭六隻)裡揀
    miss_B = []
    for mo in months:
        r = ret_by_month[mo["month_end"]]
        g = m[m["month_end"] == mo["month_end"]]
        pool = []
        for etf, gs in g.groupby("etf"):
            if len(gs) < MIN_MEMBERS:
                continue
            pool.append(gs.nlargest(min(TOP_N, len(gs)), "ret"))
        pool = pd.concat(pool)
        arr = pool[~pool["symbol"].isin(mo["hold_syms"])]["ret"].to_numpy()
        miss_B.append(arr)

    # 模型丙:揀唔中時揀動能規則當月的 27 池(扣走神諭六隻)
    miss_C = []
    for mo in months:
        me = mo["month_end"]
        syms = [s for s in mom_pool.get(me, []) if s not in mo["hold_syms"]]
        arr = ret_by_month[me].reindex(syms).dropna().to_numpy()
        miss_C.append(arr if len(arr) else mo["non_or"])
    n_fallback = sum(1 for mo, a_ in zip(months, miss_C)
                     if len(a_) == len(mo["non_or"]))

    res = {"dice_acc%": round(dice * 100, 3), "months": len(months),
           "模型丙用回全宇宙的月數": n_fallback}
    for name, miss in (("乙 完美過濾器排名退化", miss_B), ("丙 現實式揀錯", miss_C)):
        ladder, grid = [], []
        for a in RUNGS:
            cs = cagr_rows(sim(months, miss, a, N_PATHS, 20260904)) * 100
            ladder.append({"準繩度": a, "p5": round(float(np.percentile(cs, 5)), 2),
                           "中位": round(float(np.median(cs)), 2),
                           "p95": round(float(np.percentile(cs, 95)), 2)})
        for a in FINE_GRID:
            cs = cagr_rows(sim(months, miss, a, N_PATHS, 20260905)) * 100
            grid.append({"a": a, "med": float(np.median(cs))})
        gf = pd.DataFrame(grid)
        be = {}
        for bn, tgt in benches.items():
            v = breakeven(gf, tgt)
            be[bn] = {"打和準繩度%": round(v * 100, 3) if v else None,
                      "擲骰倍數": round(v / dice, 2) if v else None}
        res[name] = {"梯級": ladder, "打和": be}
        print(name)
        print(pd.DataFrame(ladder).to_string(index=False))
        print(json.dumps(be, ensure_ascii=False, indent=1))
        gf.to_csv(OUT / f"grid_{name.split()[0]}.csv", index=False, encoding="utf-8-sig")

    (OUT / "miss_models.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("已寫入", OUT / "miss_models.json")


if __name__ == "__main__":
    main()
