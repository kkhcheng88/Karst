"""KARST-143 診斷:拖累與波動的算式關係、防守力、笨規則拆出股票格。

只讀 run.py 的產出與倉內現成原料。
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
ORACLE = HERE.parent / "2026-09-01-stock-oracle-curve"


def cagr(x):
    return float(np.prod(1.0 + x) ** (12.0 / len(x)) - 1.0)


def arith_ann(x):
    return float((1.0 + np.mean(x)) ** 12 - 1.0)


def main() -> None:
    bench = pd.read_parquet(ORACLE / "data" / "bench_monthly.parquet")
    calm = pd.read_csv(OUT / "monthly_calm.csv", parse_dates=["month_end"])
    dip = pd.read_csv(OUT / "monthly_dip.csv", parse_dates=["month_end"])
    ridx = pd.DatetimeIndex(calm["month_end"]) + pd.offsets.MonthEnd(1)
    spy = bench.reindex(ridx)["SPY"].to_numpy()
    xlk = bench.reindex(ridx)["XLK"].to_numpy()
    six = calm["six_gross"].to_numpy()
    pool = calm["pool_ew"].to_numpy()
    univ = calm["univ_ew"].to_numpy()

    d = {}

    # 1. 拖累 ≈ 方差的一半:逐族核對
    rows = []
    for nm, x, sd in (
        ("平穩六隻", six, None), ("同池27等權", pool, None), ("全宇宙等權", univ, None),
        ("SPY", spy, None), ("XLK", xlk, None),
    ):
        s = float(np.std(x, ddof=1))
        rows.append({
            "組合": nm,
            "月度標準差%": round(s * 100, 3),
            "實際拖累pp": round((arith_ann(x) - cagr(x)) * 100, 2),
            "半方差近似pp": round(s * s * 12 / 2 * 100, 2),
            "幾何年化%": round(cagr(x) * 100, 2),
        })
    d["拖累與波動的算式關係"] = rows

    # 2. 防守力:SPY 最差十分一月份
    k = max(1, len(spy) // 10)
    worst = np.argsort(spy)[:k]
    d["防守力"] = {
        "樣本月數": len(spy),
        "SPY最差十分一月數": int(k),
        "該批月份 SPY 平均%": round(float(np.mean(spy[worst])) * 100, 2),
        "該批月份 平穩六隻 平均%": round(float(np.mean(six[worst])) * 100, 2),
        "該批月份 同池27等權 平均%": round(float(np.mean(pool[worst])) * 100, 2),
        "該批月份 全宇宙等權 平均%": round(float(np.mean(univ[worst])) * 100, 2),
        "該批月份 XLK 平均%": round(float(np.mean(xlk[worst])) * 100, 2),
        "平穩六隻 月度標準差 對 SPY": round(
            float(np.std(six, ddof=1)) / float(np.std(spy, ddof=1)), 3),
        "平穩六隻 幾何年化 ÷ 月度標準差": round(
            cagr(six) / (float(np.std(six, ddof=1)) * np.sqrt(12)), 3),
        "SPY 幾何年化 ÷ 月度標準差": round(
            cagr(spy) / (float(np.std(spy, ddof=1)) * np.sqrt(12)), 3),
        "XLK 幾何年化 ÷ 月度標準差": round(
            cagr(xlk) / (float(np.std(xlk, ddof=1)) * np.sqrt(12)), 3),
    }

    # 3. 笨規則:只計股票格(剔走 SPY 補位格)
    ridx2 = pd.DatetimeIndex(dip["month_end"]) + pd.offsets.MonthEnd(1)
    spy2 = bench.reindex(ridx2)["SPY"].to_numpy()
    n_st = dip["n_stock"].to_numpy()
    g = dip["gross"].to_numpy()
    has = n_st > 0
    # 六格總回報 = (股票格總和 + SPY 格數×SPY回報) / 6 → 反推股票格平均
    stock_only = np.where(has, (g * 6 - (6 - n_st) * spy2) / np.maximum(n_st, 1), np.nan)
    so = stock_only[has]
    sp_h = spy2[has]
    d["笨規則_只計股票格"] = {
        "有股票格的月數": int(has.sum()),
        "股票格平均月回報%": round(float(np.mean(so)) * 100, 4),
        "同期 SPY 平均月回報%": round(float(np.mean(sp_h)) * 100, 4),
        "股票格對 SPY 每月優勢pp": round(float(np.mean(so) - np.mean(sp_h)) * 100, 4),
        "股票格月度標準差%": round(float(np.std(so, ddof=1)) * 100, 3),
        "股票格幾何年化(只計有貨月份)%": round(cagr(so) * 100, 2),
        "同期 SPY 幾何年化%": round(cagr(sp_h) * 100, 2),
    }

    # 4. 笨規則對照:同一批月份,若改為一直揸平穩六隻
    d["笨規則_對照"] = {
        "笨規則幾何年化(零成本)%": round(cagr(g) * 100, 2),
        "同期 平穩六隻 幾何年化%": round(cagr(six[:len(g)]) * 100, 2),
        "同期 SPY 幾何年化%": round(cagr(spy2) * 100, 2),
        "笨規則 月度標準差%": round(float(np.std(g, ddof=1)) * 100, 3),
    }

    # 5. 分期穩健度:平穩六隻對 SPY,逐五年
    seg = []
    yr = pd.DatetimeIndex(calm["month_end"]).year
    for lo in range(2001, 2026, 5):
        m = (yr >= lo) & (yr < lo + 5)
        if m.sum() < 24:
            continue
        seg.append({
            "期間": f"{lo}-{min(lo + 4, 2026)}",
            "月數": int(m.sum()),
            "平穩六隻%": round(cagr(six[m]) * 100, 2),
            "同池27等權%": round(cagr(pool[m]) * 100, 2),
            "SPY%": round(cagr(spy[m]) * 100, 2),
            "XLK%": round(cagr(xlk[m]) * 100, 2),
        })
    d["分期"] = seg

    (OUT / "diag.json").write_text(json.dumps(d, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    print(json.dumps(d, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
