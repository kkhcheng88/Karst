"""KARST-140:穩陣(價值/質素)族六隻等權組合的集中度懲罰量度。

規格見同目錄 PLAN.md(跑數前已獨立 commit,commit 92eea8a)。
本腳本只讀倉內現成原料,不接任何新數據源,不碰生產庫。
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

ORACLE = HERE.parent / "2026-09-01-stock-oracle-curve"
FWD = HERE.parent / "2026-09-02-forward-yield-build"

TOP_N = 3
HOLD_M = 6
MIN_MEMBERS = 8
SIDE_BP_MAIN = 15.0
SIDE_BP_GRID = [0.0, 15.0, 25.0, 50.0]
N_PATHS = 2000
SEED = 20260902


# ------------------------------------------------------------------ 載入清洗
def load_monthly() -> pd.DataFrame:
    """KARST-139 main 篩,判準原封不動搬過來。"""
    m = pd.read_parquet(ORACLE / "data" / "stock_monthly.parquet")
    m = m[m["ret"].notna()].copy()
    dm = pd.read_parquet(ORACLE / "data" / "day_moves.parquet")
    sp = pd.read_parquet(ORACLE / "data" / "splits.parquet")
    explained = set()
    for s, me in zip(sp["symbol"], sp["month_end"]):
        for k in (-1, 0, 1):
            explained.add((s, me + pd.offsets.MonthEnd(k) if k else me))
    bad = dm[dm["max_abs_day"] >= 1.0]
    bad = [(s, me) for s, me in zip(bad["symbol"], bad["month_end"])
           if (s, me) not in explained]
    cnt = pd.Series([s for s, _ in bad]).value_counts()
    drop_syms = sorted(cnt[cnt >= 3].index.tolist())
    m = m[~m["symbol"].isin(drop_syms)].copy()
    cells = {(s, me) for s, me in bad if s not in drop_syms}
    m = m[[(s, me) not in cells for s, me in zip(m["symbol"], m["month_end"])]].copy()
    return m, drop_syms


def cagr(x: np.ndarray) -> float:
    return float(np.prod(1.0 + x) ** (12.0 / len(x)) - 1.0)


def cagr_rows(x: np.ndarray) -> np.ndarray:
    return np.prod(1.0 + x, axis=1) ** (12.0 / x.shape[1]) - 1.0


def arith_ann(x: np.ndarray) -> float:
    return float((1.0 + np.mean(x)) ** 12 - 1.0)


def maxdd(x: np.ndarray) -> float:
    eq = np.cumprod(1.0 + x)
    return float((eq / np.maximum.accumulate(eq) - 1.0).min())


def apply_cost(gross: np.ndarray, side_bp: float, turnover) -> np.ndarray:
    c = np.asarray(turnover) * 2.0 * side_bp / 10000.0
    return (1.0 + gross) * (1.0 - c) - 1.0


# ------------------------------------------------------------------ 主流程
def build(mon: pd.DataFrame, score: pd.DataFrame, score_col: str):
    """逐月:穩陣六隻、27 池、宇宙。score 帶 symbol/month_end/etf/<score_col>。"""
    sc = score[["symbol", "month_end", "etf", score_col]].dropna()
    j = sc.merge(mon[["symbol", "month_end", "ret"]], on=["symbol", "month_end"])
    months = []
    prev = set()
    for me, g in j.groupby("month_end", sort=True):
        cnt = g.groupby("etf").size()
        g2 = g[g["etf"].map(cnt).ge(MIN_MEMBERS)]
        if g2.empty:
            prev = set()
            continue
        pool = (g2.sort_values(score_col, ascending=False)
                  .groupby("etf", sort=False).head(TOP_N))
        if len(pool) < HOLD_M:
            prev = set()
            continue
        hold = pool.nlargest(HOLD_M, score_col)
        syms = set(hold["symbol"])
        turn = 1.0 if not prev else 1.0 - len(syms & prev) / HOLD_M
        months.append({
            "month_end": me,
            "n_univ": len(g),
            "n_pool": len(pool),
            "hold_ret": float(hold["ret"].mean()),
            "hold_syms": tuple(hold["symbol"]),
            "turnover": turn,
            "pool_ew": float(pool["ret"].mean()),
            "univ_ew": float(g["ret"].mean()),
            "pool_rets": pool["ret"].to_numpy(),
            "univ_rets": g["ret"].to_numpy(),
        })
        prev = syms
    return months


def rand_paths(months, key, rng):
    """每月由 key 指定的池隨機抽六隻等權(有放回抽樣不合理 → 無放回)。"""
    T = len(months)
    out = np.empty((N_PATHS, T))
    for j, mo in enumerate(months):
        r = mo[key]
        n = len(r)
        k = min(HOLD_M, n)
        idx = np.argsort(rng.random((N_PATHS, n)), axis=1)[:, :k]
        out[:, j] = r[idx].mean(axis=1)
    return out


def stats_block(gross: np.ndarray, univ: np.ndarray, turnover) -> dict:
    a_ann = arith_ann(gross)
    g_ann = cagr(gross)
    ua, ug = arith_ann(univ), cagr(univ)
    d = {
        "月數": len(gross),
        "算術月均%": round(float(np.mean(gross)) * 100, 4),
        "月度標準差%": round(float(np.std(gross, ddof=1)) * 100, 3),
        "算術年化%": round(a_ann * 100, 2),
        "幾何年化(零成本)%": round(g_ann * 100, 2),
        "絕對波動拖累pp": round((a_ann - g_ann) * 100, 2),
        "增量拖累(對全宇宙等權)pp": round(((a_ann - g_ann) - (ua - ug)) * 100, 2),
        "最大跌幅%": round(maxdd(gross) * 100, 1),
        "平均換手率%": round(float(np.mean(turnover)) * 100, 1),
    }
    for bp in SIDE_BP_GRID:
        d[f"淨年化@{int(bp)}bp%"] = round(cagr(apply_cost(gross, bp, turnover)) * 100, 2)
    d["淨年化@15bp強制全換%"] = round(cagr(apply_cost(gross, SIDE_BP_MAIN, 1.0)) * 100, 2)
    return d


def main() -> None:
    mon, drop_syms = load_monthly()
    fwd = pd.read_parquet(FWD / "data" / "member_forward.parquet")
    fwd = fwd[(fwd["month_end"] >= fwd["joined_on"]) & (fwd["month_end"] < fwd["left_on"])]
    fwd = fwd[fwd["mcap"] > 0].copy()
    fwd["ey_fwd1"] = fwd["earn_fwd1"] / fwd["mcap"]
    fwd["ey_fwd4"] = fwd["earn_fwd4"] / fwd["mcap"]

    # ---- KARST-139 神諭(全篩後宇宙,定義與 139 一致),用來量準繩度
    oracle_top: dict = {}
    for me, g in mon.groupby("month_end", sort=True):
        pool = []
        for etf, gs in g.groupby("etf", sort=False):
            if len(gs) < MIN_MEMBERS:
                continue
            pool.append(gs.nlargest(min(TOP_N, len(gs)), "ret"))
        if not pool:
            continue
        pool = pd.concat(pool)
        oracle_top[me] = set(pool.nlargest(min(HOLD_M, len(pool)), "ret")["symbol"])

    grid = pd.read_csv(ORACLE / "out" / "grid.csv")
    bench = pd.read_parquet(ORACLE / "data" / "bench_monthly.parquet")

    report: dict = {
        "剔走的股票": drop_syms,
        "口徑": "PLAN.md(commit 92eea8a)",
    }

    for score_col in ("ey_fwd1", "ey_fwd4"):
        months = build(mon, fwd, score_col)
        if not months:
            continue
        idx = pd.DatetimeIndex([x["month_end"] for x in months])
        gross = np.array([x["hold_ret"] for x in months])
        turn = np.array([x["turnover"] for x in months])
        pool_ew = np.array([x["pool_ew"] for x in months])
        univ_ew = np.array([x["univ_ew"] for x in months])

        rng = np.random.default_rng(SEED)
        r_pool = rand_paths(months, "pool_rets", rng)
        r_univ = rand_paths(months, "univ_rets", rng)

        blk = {
            "樣本期": f"{idx[0].date()} 至 {idx[-1].date()}",
            "月數": len(months),
            "年數": round(len(months) / 12.0, 2),
            "每月平均宇宙隻數": round(float(np.mean([x["n_univ"] for x in months])), 1),
            "每月平均池隻數": round(float(np.mean([x["n_pool"] for x in months])), 1),
        }
        blk["穩陣六隻"] = stats_block(gross, univ_ew, turn)
        blk["同池27等權"] = stats_block(pool_ew, univ_ew, 0.0)
        blk["全宇宙等權"] = stats_block(univ_ew, univ_ew, 0.0)

        # 隨機六隻(中位路徑)
        for nm, arr in (("同池隨機六隻", r_pool), ("全宇宙隨機六隻", r_univ)):
            cs = cagr_rows(arr)
            med = int(np.argsort(cs)[len(cs) // 2])
            blk[nm] = {
                "月度標準差%(路徑中位)": round(float(np.median(np.std(arr, axis=1, ddof=1))) * 100, 3),
                "算術月均%(平均)": round(float(np.mean(arr)) * 100, 4),
                "幾何年化%(路徑中位,零成本)": round(float(np.median(cs)) * 100, 2),
                "絕對波動拖累pp(中位路徑)": round(
                    (arith_ann(arr[med]) - cagr(arr[med])) * 100, 2),
                "淨年化@15bp全換%(路徑中位)": round(
                    float(np.median(cagr_rows(apply_cost(arr, SIDE_BP_MAIN, 1.0)))) * 100, 2),
            }

        # 揀股優勢
        blk["揀股優勢"] = {
            "六隻算術月均%": round(float(np.mean(gross)) * 100, 4),
            "同池27等權算術月均%": round(float(np.mean(pool_ew)) * 100, 4),
            "優勢pp每月": round(float(np.mean(gross) - np.mean(pool_ew)) * 100, 4),
            "優勢年化pp": round((arith_ann(gross) - arith_ann(pool_ew)) * 100, 2),
            "同池隨機六隻算術月均%": round(float(np.mean(r_pool)) * 100, 4),
            "對隨機六隻優勢pp每月": round(float(np.mean(gross) - np.mean(r_pool)) * 100, 4),
        }

        # 副 B:139 原式
        blk["副B_139原式pp"] = round(
            (cagr(univ_ew) - float(np.median(cagr_rows(r_univ)))) * 100, 2)

        # 基準(同期重算)
        b = bench.reindex(idx)
        blk["基準"] = {"SPY含息%": round(cagr(b["SPY"].to_numpy()) * 100, 2)}
        for c in b.columns:
            if c != "SPY":
                blk["基準"][c + "%"] = round(cagr(b[c].to_numpy()) * 100, 2)

        # D-116:準繩度與曲線預測
        hits = [len(set(x["hold_syms"]) & oracle_top.get(x["month_end"], set())) / HOLD_M
                for x in months]
        acc = float(np.mean(hits))
        dice = HOLD_M / float(np.mean([x["n_univ"] for x in months]))
        blk["D116"] = {
            "實際準繩度%": round(acc * 100, 3),
            "同期擲骰準繩度%": round(dice * 100, 3),
            "係擲骰幾多倍": round(acc / dice, 2),
            "139曲線在該準繩度的中位預測%": round(
                float(np.interp(acc, grid["a"], grid["med"])), 2),
            "實際淨年化@15bp%": blk["穩陣六隻"]["淨年化@15bp%"],
        }
        blk["D116"]["背離pp"] = round(
            blk["D116"]["實際淨年化@15bp%"] - blk["D116"]["139曲線在該準繩度的中位預測%"], 2)

        # 逐月序列落檔
        pd.DataFrame({
            "month_end": idx, "six_gross": gross, "turnover": turn,
            "pool_ew": pool_ew, "univ_ew": univ_ew,
            "hold": [",".join(x["hold_syms"]) for x in months],
        }).to_csv(OUT / f"monthly_{score_col}.csv", index=False, encoding="utf-8-sig")

        report[score_col] = blk

    # ---- 副 C:動能族(12-1)同期同宇宙重跑
    sc = fwd[["symbol", "month_end", "etf", "ey_fwd1"]].dropna()
    j = sc.merge(mon[["symbol", "month_end", "ret"]], on=["symbol", "month_end"])
    piv = mon.pivot_table(index="month_end", columns="symbol", values="ret").sort_index()
    mom = (1.0 + piv).shift(2).rolling(11).apply(np.prod, raw=True) - 1.0
    mom_long = mom.stack().rename("mom").reset_index()
    mom_long.columns = ["month_end", "symbol", "mom"]
    j2 = j.merge(mom_long, on=["month_end", "symbol"])
    months_m = build(mon, j2.rename(columns={"mom": "score"}), "score")
    if months_m:
        idx = pd.DatetimeIndex([x["month_end"] for x in months_m])
        g_ = np.array([x["hold_ret"] for x in months_m])
        t_ = np.array([x["turnover"] for x in months_m])
        u_ = np.array([x["univ_ew"] for x in months_m])
        p_ = np.array([x["pool_ew"] for x in months_m])
        blk = {"樣本期": f"{idx[0].date()} 至 {idx[-1].date()}", "月數": len(months_m)}
        blk["動能六隻"] = stats_block(g_, u_, t_)
        blk["同池27等權"] = stats_block(p_, u_, 0.0)
        blk["揀股優勢pp每月"] = round(float(np.mean(g_) - np.mean(p_)) * 100, 4)
        hits = [len(set(x["hold_syms"]) & oracle_top.get(x["month_end"], set())) / HOLD_M
                for x in months_m]
        blk["實際準繩度%"] = round(float(np.mean(hits)) * 100, 3)
        report["副C_動能族同期"] = blk

    (OUT / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
