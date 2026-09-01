"""KARST-143 核實:KARST-140 價值臂的 −7.90% 是不是純粹來自「當月分數配當月回報」。

同一條管線,同一批月份與宇宙,只改對齊:
  (a) 同月對齊 = KARST-140 run.py 的實際做法(分數 t → 回報 t)
  (b) 正確對齊 = KARST-140 PLAN 第三節寫的做法(分數 t → 回報 t+1)
若 (a) 重現得到 140 報告的數,即證實差異純粹來自對齊。
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

import run as R

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"


def main() -> None:
    mon, _ = R.load_monthly()
    sector = dict(zip(mon["symbol"], mon["etf"]))
    ret_piv = mon.pivot_table(index="month_end", columns="symbol",
                              values="ret").sort_index()
    same = R.long_form(ret_piv, "ret_next")            # 分數 t → 回報 t
    nextm = R.long_form(ret_piv.shift(-1), "ret_next")  # 分數 t → 回報 t+1

    fwd = pd.read_parquet(R.FWD / "data" / "member_forward.parquet")
    fwd = fwd[(fwd["month_end"] >= fwd["joined_on"]) & (fwd["month_end"] < fwd["left_on"])]
    fwd = fwd[fwd["mcap"] > 0].copy()
    fwd["ey_fwd1"] = fwd["earn_fwd1"] / fwd["mcap"]
    sc = fwd[["symbol", "month_end", "ey_fwd1"]].dropna()

    mom_same = (1.0 + ret_piv).shift(2).rolling(11).apply(np.prod, raw=True) - 1.0
    mom_next = (1.0 + ret_piv).shift(1).rolling(11).apply(np.prod, raw=True) - 1.0
    keys = set(zip(sc["symbol"], sc["month_end"]))

    def sub(piv):
        L = R.long_form(piv, "mom")
        return L[[(s, m) in keys for s, m in zip(L["symbol"], L["month_end"])]]

    out = {}
    for tag, score, col, asc, rets in (
        ("價值_同月對齊(140原做法)", sc, "ey_fwd1", False, same),
        ("價值_正確對齊(t→t+1)", sc, "ey_fwd1", False, nextm),
        ("動能_140原做法(shift2,同月回報)", sub(mom_same), "mom", False, same),
        ("動能_正確對齊(shift1,t+1回報)", sub(mom_next), "mom", False, nextm),
    ):
        ms = R.build(score, col, asc, sector, rets)
        g = np.array([x["hold_ret"] for x in ms])
        t = np.array([x["turnover"] for x in ms])
        idx = pd.DatetimeIndex([x["month_end"] for x in ms])
        out[tag] = {
            "樣本期": f"{idx[0].date()} 至 {idx[-1].date()}",
            "月數": len(g),
            "月度標準差%": round(float(np.std(g, ddof=1)) * 100, 3),
            "算術年化%": round(R.arith_ann(g) * 100, 2),
            "幾何年化(零成本)%": round(R.cagr(g) * 100, 2),
            "絕對波動拖累pp": round((R.arith_ann(g) - R.cagr(g)) * 100, 2),
            "淨年化@15bp%": round(R.cagr(R.apply_cost(g, 15.0, t)) * 100, 2),
            "平均換手率%": round(float(np.mean(t)) * 100, 1),
        }
    (OUT / "verify_align.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
