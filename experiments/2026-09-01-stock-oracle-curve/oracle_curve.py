"""KARST-139 主引擎:個股層退化神諭曲線。

架構(照 KARST-138 方案書 / D-112):
  九個板塊 → 每板塊行內取神諭頭 3(事後全知:該板塊下一個月回報最高那 3 隻)
  → 合資格池約 27 隻 → 再全知揀頭 6 → 等權 → 月度換馬。
  每組最少 8 隻成員才出人(方案書對齊項 #2 示例值)。

退化定義(先寫死):
  準繩度 a = 每一個持倉格「拿到神諭那隻」的機會。命中 → 該格就是神諭那隻;
  唔命中 → 在同月「非神諭六隻」的合資格宇宙裡等機會隨機抽一隻。
  a = 0 即純隨機揀六隻。
  擲骰等價準繩度 = 6 / 當月合資格隻數(約 1.8%),用來換算「入場費係擲骰幾多倍」,
  與 KARST-113 板塊版(擲骰 11.1%、打和 14.85%、即 1.34 倍)並排。

成本:每邊 15 個基點(手續費 5 + 滑點 10),敏感度 0 / 25 / 50。
  月度全換馬 → 每月成本 = 換手率 × 2 × 每邊費率。

口徑:月底收市價對月底收市價(個股面板只有月底價,沒有次日開市價)。
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

TOP_N = 3          # 每板塊行內頭 N
HOLD_M = 6         # 最終持倉
MIN_MEMBERS = 8    # 一個板塊當月少過這麼多隻有數據,該月不出人
SIDE_BP_MAIN = 15.0
SIDE_BP_GRID = [0.0, 15.0, 25.0, 50.0]
N_PATHS_RUNG = 2000
N_PATHS_GRID = 800
RUNGS = [1.00, 0.90, 0.80, 0.70, 0.60, 0.50, 0.0]
FINE_GRID = sorted(set(
    [0.0, 0.002, 0.005, 0.0075] +
    [round(x, 4) for x in np.arange(0.01, 0.101, 0.005)] +
    [round(x, 3) for x in np.arange(0.11, 0.31, 0.01)] +
    [round(x, 2) for x in np.arange(0.35, 1.001, 0.05)]
))


# ---------------------------------------------------------------- 載入與清洗
def load(screen: str):
    """數據完整性篩選(判準先寫死,再看結果)。

    「無解釋的爆炸日」= 該股月內出現 ≥ ±100% 的單日變動,而該月及前後一個月
    都沒有拆股紀錄。真實個股單日翻倍極罕見,這種格幾乎一定是價格序列出錯。

    screen:
      'main'   ①一隻股票若果有 ≥3 個無解釋爆炸月 → 判為序列系統性損壞,整隻剔走;
               ②其餘的無解釋爆炸月,逐格剔走
      'none'   完全不剔(用來量髒數據把上限抬高了幾多)
      'strict' 在 main 之上,再剔走任何 |月度回報| > 100% 的格
               (連真實的危機後爆升都剔埋,刻意偏保守)
    """
    m = pd.read_parquet(DATA / "stock_monthly.parquet")
    m = m[m["ret"].notna()].copy()
    dropped_syms: list[str] = []
    dropped_cells = 0

    if screen in ("main", "strict"):
        dm = pd.read_parquet(DATA / "day_moves.parquet")
        sp = pd.read_parquet(DATA / "splits.parquet")
        explained = set()
        for s, me in zip(sp["symbol"], sp["month_end"]):
            for k in (-1, 0, 1):
                explained.add((s, me + pd.offsets.MonthEnd(k) if k else me))
        bad = dm[dm["max_abs_day"] >= 1.0]
        bad = [(s, me) for s, me in zip(bad["symbol"], bad["month_end"])
               if (s, me) not in explained]
        cnt = pd.Series([s for s, _ in bad]).value_counts()
        dropped_syms = sorted(cnt[cnt >= 3].index.tolist())
        m = m[~m["symbol"].isin(dropped_syms)].copy()
        cells = {(s, me) for s, me in bad if s not in dropped_syms}
        n0 = len(m)
        m = m[[(s, me) not in cells for s, me in zip(m["symbol"], m["month_end"])]].copy()
        dropped_cells = n0 - len(m)

    if screen == "strict":
        n0 = len(m)
        m = m[m["ret"].abs() <= 1.0].copy()
        dropped_cells += n0 - len(m)

    return m, dropped_syms, dropped_cells


def build_months(m: pd.DataFrame):
    """逐個持有月砌出:神諭六隻、27 池、宇宙等權、非神諭宇宙。"""
    months = []
    for me, g in m.groupby("month_end", sort=True):
        pool = []
        for etf, gs in g.groupby("etf", sort=False):
            if len(gs) < MIN_MEMBERS:
                continue
            pool.append(gs.nlargest(min(TOP_N, len(gs)), "ret"))
        if not pool:
            continue
        pool = pd.concat(pool)
        hold = pool.nlargest(min(HOLD_M, len(pool)), "ret")
        hold_syms = set(hold["symbol"])
        non_or = g[~g["symbol"].isin(hold_syms)]["ret"].to_numpy()
        months.append({
            "month_end": me,
            "n_univ": len(g),
            "n_pool": len(pool),
            "hold_ret": hold["ret"].to_numpy(),
            "hold_syms": tuple(hold["symbol"]),
            "pool_ew": float(pool["ret"].mean()),
            "univ_ew": float(g["ret"].mean()),
            "non_or": non_or,
        })
    return months


# ---------------------------------------------------------------- 成績計算
def cagr(net: np.ndarray) -> float:
    yrs = net.shape[-1] / 12.0
    return float(np.prod(1.0 + net) ** (1.0 / yrs) - 1.0)


def cagr_rows(net: np.ndarray) -> np.ndarray:
    yrs = net.shape[1] / 12.0
    return np.prod(1.0 + net, axis=1) ** (1.0 / yrs) - 1.0


def maxdd(net: np.ndarray) -> float:
    eq = np.cumprod(1.0 + net)
    return float((eq / np.maximum.accumulate(eq) - 1.0).min())


def apply_cost(gross: np.ndarray, side_bp: float, turnover: float = 1.0) -> np.ndarray:
    c = turnover * 2.0 * side_bp / 10000.0
    return (1.0 + gross) * (1.0 - c) - 1.0


# ---------------------------------------------------------------- 模擬
def simulate(months, a: float, n_paths: int, side_bp: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    T = len(months)
    gross = np.empty((n_paths, T))
    for j, mo in enumerate(months):
        hold = mo["hold_ret"]
        k = len(hold)
        non = mo["non_or"]
        if a >= 1.0:
            gross[:, j] = hold.mean()
            continue
        hits = rng.random((n_paths, k)) < a
        idx = rng.integers(0, len(non), size=(n_paths, k))
        gross[:, j] = np.where(hits, hold[None, :], non[idx]).mean(axis=1)
    return apply_cost(gross, side_bp)


def main() -> None:
    report: dict = {}

    for screen in ("main", "none", "strict"):
        m, dsyms, dcells = load(screen)
        months = build_months(m)
        T = len(months)
        me0, me1 = months[0]["month_end"], months[-1]["month_end"]
        info = {
            "screen": screen, "months": T, "years": round(T / 12.0, 2),
            "from": str(me0.date()), "to": str(me1.date()),
            "dropped_symbols": dsyms, "dropped_cells": dcells,
            "n_symbols": int(m["symbol"].nunique()),
            "avg_univ": round(float(np.mean([x["n_univ"] for x in months])), 1),
            "avg_pool": round(float(np.mean([x["n_pool"] for x in months])), 1),
        }
        oracle_gross = np.array([x["hold_ret"].mean() for x in months])
        pool_ew = np.array([x["pool_ew"] for x in months])
        univ_ew = np.array([x["univ_ew"] for x in months])
        # 神諭換手率(相鄰兩個月持倉重疊)
        ov = [len(set(months[i]["hold_syms"]) & set(months[i - 1]["hold_syms"]))
              for i in range(1, T)]
        info["oracle_overlap_avg"] = round(float(np.mean(ov)), 3)
        info["oracle_turnover"] = round(1.0 - float(np.mean(ov)) / HOLD_M, 4)
        info["dice_acc"] = round(HOLD_M / float(np.mean([x["n_univ"] for x in months])), 5)

        o_net = apply_cost(oracle_gross, SIDE_BP_MAIN)
        info["oracle_cagr"] = round(cagr(o_net) * 100, 2)
        info["oracle_maxdd"] = round(maxdd(o_net) * 100, 1)
        info["pool_ew_cagr"] = round(cagr(apply_cost(pool_ew, SIDE_BP_MAIN)) * 100, 2)
        info["univ_ew_cagr"] = round(cagr(univ_ew) * 100, 2)
        info["oracle_cagr_by_cost"] = {
            str(int(b)): round(cagr(apply_cost(oracle_gross, b)) * 100, 2)
            for b in SIDE_BP_GRID}
        report[screen] = info
        print(json.dumps(info, ensure_ascii=False, indent=1))

        if screen == "main":
            MAIN = (m, months, oracle_gross, pool_ew, univ_ew, info)

    m, months, oracle_gross, pool_ew, univ_ew, info = MAIN
    T = len(months)
    idx = pd.DatetimeIndex([x["month_end"] for x in months])

    # ------------------------------------------------ 基準
    bench = pd.read_parquet(DATA / "bench_monthly.parquet")
    b = bench.reindex(idx)
    spy = b["SPY"].to_numpy()
    benches = {"SPY 含息": round(cagr(spy) * 100, 2)}
    etf_cagr = {c: round(cagr(b[c].to_numpy()) * 100, 2)
                for c in b.columns if c != "SPY"}
    best_etf = max(etf_cagr, key=etf_cagr.get)
    benches[f"最強單一板塊 ETF({best_etf})"] = etf_cagr[best_etf]

    # 最強單一個股(全期在冊、逐月有回報)
    piv = m.pivot_table(index="month_end", columns="symbol", values="ret")
    piv = piv.reindex(idx)
    full = piv.columns[piv.notna().all()]
    stock_cagr = {c: cagr(piv[c].to_numpy()) for c in full}
    best_stock = max(stock_cagr, key=stock_cagr.get) if len(stock_cagr) else None
    top_stocks = sorted(stock_cagr.items(), key=lambda kv: -kv[1])[:10]
    benches["同池等權(27 池,已扣成本)"] = info["pool_ew_cagr"]
    benches["全宇宙等權(無成本)"] = info["univ_ew_cagr"]
    if best_stock:
        benches[f"最強單一個股({best_stock},全期在冊)"] = round(stock_cagr[best_stock] * 100, 2)

    print("\n基準:", json.dumps(benches, ensure_ascii=False, indent=1))
    print("全期在冊隻數", len(full), "首十:",
          [(s, round(v * 100, 2)) for s, v in top_stocks])
    print("逐隻板塊 ETF:", etf_cagr)

    # ------------------------------------------------ 梯級表
    rows = []
    for a in RUNGS:
        net = simulate(months, a, N_PATHS_RUNG, SIDE_BP_MAIN, seed=20260901)
        cs = cagr_rows(net) * 100
        rows.append({
            "準繩度": a, "p5": round(float(np.percentile(cs, 5)), 2),
            "中位": round(float(np.median(cs)), 2),
            "p95": round(float(np.percentile(cs, 95)), 2),
            "贏SPY機會": round(float((cs > benches["SPY 含息"]).mean()) * 100, 1),
            "贏最強ETF機會": round(float((cs > etf_cagr[best_etf]).mean()) * 100, 1),
            "贏最強個股機會": round(float((cs > stock_cagr[best_stock] * 100).mean()) * 100, 1),
            "贏同池等權機會": round(float((cs > info["pool_ew_cagr"]).mean()) * 100, 1),
        })
    ladder = pd.DataFrame(rows)
    ladder.to_csv(OUT / "ladder.csv", index=False, encoding="utf-8-sig")
    print("\n梯級表\n", ladder.to_string(index=False))

    # ------------------------------------------------ 細網格 + 打和點
    grid_rows = []
    for a in FINE_GRID:
        net = simulate(months, a, N_PATHS_GRID, SIDE_BP_MAIN, seed=20260902)
        cs = cagr_rows(net) * 100
        grid_rows.append({"a": a, "p5": float(np.percentile(cs, 5)),
                          "med": float(np.median(cs)),
                          "p95": float(np.percentile(cs, 95)),
                          "p25": float(np.percentile(cs, 25))})
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(OUT / "grid.csv", index=False, encoding="utf-8-sig")

    def breakeven(col: str, target: float, frame: pd.DataFrame | None = None) -> float | None:
        f = grid if frame is None else frame
        x, y = f["a"].to_numpy(), f[col].to_numpy()
        for i in range(1, len(x)):
            if (y[i - 1] - target) * (y[i] - target) <= 0 and y[i] != y[i - 1]:
                return float(x[i - 1] + (target - y[i - 1]) * (x[i] - x[i - 1])
                             / (y[i] - y[i - 1]))
        return None

    dice = info["dice_acc"]
    be = {}
    for name, tgt in benches.items():
        v = breakeven("med", tgt)
        be[name] = {"打和準繩度%": round(v * 100, 3) if v else None,
                    "擲骰倍數": round(v / dice, 2) if v else None,
                    "基準年化%": tgt}
    be["_擲骰準繩度%"] = round(dice * 100, 3)
    # 四分三把握
    be34 = {n: (lambda v: round(v * 100, 3) if v else None)(breakeven("p25", t))
            for n, t in benches.items()}
    print("\n打和準繩度:", json.dumps(be, ensure_ascii=False, indent=1))
    print("四分三把握贏到的準繩度%:", json.dumps(be34, ensure_ascii=False, indent=1))

    # ------------------------------------------------ 成本敏感度(打和點)
    cost_be = {}
    for bp in SIDE_BP_GRID:
        g2 = []
        for a in FINE_GRID:
            net = simulate(months, a, 400, bp, seed=20260903)
            g2.append({"a": a, "med": float(np.median(cagr_rows(net) * 100))})
        g2 = pd.DataFrame(g2)
        cost_be[str(int(bp))] = {
            n: (lambda v: round(v * 100, 3) if v else None)(breakeven("med", t, g2))
            for n, t in benches.items()}
    print("\n成本敏感度(每邊基點 → 打和準繩度%):",
          json.dumps(cost_be, ensure_ascii=False, indent=1))

    # ------------------------------------------------ 種子穩定性
    seeds = {}
    for sd in (11, 22, 33):
        g3 = []
        for a in FINE_GRID:
            net = simulate(months, a, 800, SIDE_BP_MAIN, seed=sd)
            g3.append({"a": a, "med": float(np.median(cagr_rows(net) * 100))})
        g3 = pd.DataFrame(g3)
        seeds[sd] = {n: (lambda v: round(v * 100, 3) if v else None)(breakeven("med", t, g3))
                     for n, t in benches.items()}
    print("\n三個種子的打和點%:", json.dumps(seeds, ensure_ascii=False, indent=1))

    # ------------------------------------------------ 現實錨:兩條事先寫死的笨規則
    # 目的只有一個:核對曲線是不是太樂觀(照 KARST-113 做法)。
    # 兩條規則都不含任何參數搜尋、不含任何擬合,揀完就報,不再試第三條。
    piv_all = m.pivot_table(index="month_end", columns="symbol", values="ret").sort_index()
    lp = (1.0 + piv_all)
    sig_prev = piv_all.shift(1)                                   # 甲:上月回報
    sig_mom = lp.shift(2).rolling(11).apply(np.prod, raw=True) - 1  # 乙:12-1 動能
    etf_of = m.drop_duplicates("symbol").set_index("symbol")["etf"]
    anchors = {}
    for nm, sig in (("買上月頭六名", sig_prev), ("12-1 動能頭六名", sig_mom)):
        rr, hit = [], []
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
            pick = pool.nlargest(HOLD_M, "sig")["sym"].tolist()
            if len(pick) < HOLD_M:
                continue
            rmap = g.set_index("symbol")["ret"]
            rr.append(float(rmap.reindex(pick).mean()))
            hit.append(len(set(pick) & set(mo["hold_syms"])) / HOLD_M)
        net = apply_cost(np.array(rr), SIDE_BP_MAIN)
        acc = float(np.mean(hit))
        pred = float(np.interp(acc, grid["a"], grid["med"]))
        anchors[nm] = {"月數": len(rr), "實際命中率%": round(acc * 100, 3),
                       "係擲骰幾多倍": round(acc / dice, 2),
                       "實際年化%": round(cagr(net) * 100, 2),
                       "曲線在該命中率的中位預測%": round(pred, 2),
                       "最大跌幅%": round(maxdd(net) * 100, 1)}
    print("\n現實錨:", json.dumps(anchors, ensure_ascii=False, indent=1))

    summary = {"anchors": anchors, "info": report, "benches": benches, "etf_cagr": etf_cagr,
               "top_stocks": [(s, round(v * 100, 2)) for s, v in top_stocks],
               "n_full_period_stocks": int(len(full)),
               "breakeven": be, "breakeven_p25": be34,
               "cost_breakeven": cost_be, "seed_breakeven": seeds}
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n已寫入", OUT)


if __name__ == "__main__":
    main()
