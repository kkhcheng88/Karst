"""KARST-136 第三步:兩條序列的相關、分歧期、覆蓋率彙總——建置報告的數表來源。

輸出:
  corr_summary.csv     逐序列:水平相關、變動相關、平均前瞻溢價
  divergence.csv       分歧期(前瞻與後顧方向相反的月份)逐段
  coverage_by_year.csv 由 build_sector_yields.py 產出,這裡只印摘要
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
Y = HERE / "sector_yields.csv"


def main() -> None:
    d = pd.read_csv(Y, parse_dates=["month_end"])
    d = d.sort_values(["series", "month_end"])

    rows = []
    for s, g in d.groupby("series"):
        g = g.set_index("month_end")
        both = g.dropna(subset=["ey_lag", "ey_fwd"])
        b1 = g.dropna(subset=["ey_lag", "ey_fwd1"])
        bh = g.dropna(subset=["ey_fwd", "ey_fwd_hp"])
        dl = g["ey_lag"].diff()
        df_ = g["ey_fwd"].diff()
        dd = pd.concat([dl, df_], axis=1).dropna()
        rec = {
            "series": s,
            "n_both": len(both),
            "start_fwd": g["ey_fwd"].first_valid_index(),
            "end_fwd": g["ey_fwd"].last_valid_index(),
            "corr_level": both["ey_lag"].corr(both["ey_fwd"]) if len(both) > 2 else np.nan,
            "corr_diff": dd.iloc[:, 0].corr(dd.iloc[:, 1]) if len(dd) > 2 else np.nan,
            "corr_fwd_fwd1": (b1["ey_fwd"].corr(b1["ey_fwd1"])
                              if len(b1) > 2 else np.nan),
            "corr_fwd_hp": bh["ey_fwd"].corr(bh["ey_fwd_hp"]) if len(bh) > 2 else np.nan,
            "mean_ey_lag": both["ey_lag"].mean(),
            "mean_ey_fwd": both["ey_fwd"].mean(),
            "mean_premium_pp": (both["ey_fwd"] - both["ey_lag"]).mean() * 100,
            "pct_fwd_above_lag": float((both["ey_fwd"] > both["ey_lag"]).mean()),
            "cov_fwd_med": g["cov_fwd"].median(),
            "lowprec_med": g["lowprec_mcap_share"].median(),
        }
        rows.append(rec)
    cs = pd.DataFrame(rows)
    cs.to_csv(HERE / "corr_summary.csv", index=False, encoding="utf-8")
    print("== 兩條序列的關係(逐序列)==")
    print(cs[["series", "n_both", "corr_level", "corr_diff", "corr_fwd_fwd1",
              "corr_fwd_hp", "mean_ey_lag", "mean_ey_fwd", "mean_premium_pp",
              "pct_fwd_above_lag"]].to_string(index=False, float_format="%.3f"))

    # ---- 分歧期:兩條序列月變動方向相反,且連續 3 個月以上 ----
    seg = []
    for s, g in d.groupby("series"):
        g = g.set_index("month_end")
        dl = g["ey_lag"].diff()
        df_ = g["ey_fwd"].diff()
        opp = ((dl * df_) < 0)
        opp = opp.where(dl.notna() & df_.notna())
        run_start, run_len = None, 0
        for t, v in opp.items():
            if v is True:
                if run_start is None:
                    run_start = t
                run_len += 1
            else:
                if run_start is not None and run_len >= 3:
                    seg.append({"series": s, "start": run_start, "end": prev,
                                "months": run_len,
                                "d_lag_pp": (g.loc[prev, "ey_lag"]
                                             - g.loc[run_start, "ey_lag"]) * 100,
                                "d_fwd_pp": (g.loc[prev, "ey_fwd"]
                                             - g.loc[run_start, "ey_fwd"]) * 100})
                run_start, run_len = None, 0
            prev = t
        if run_start is not None and run_len >= 3:
            seg.append({"series": s, "start": run_start, "end": prev,
                        "months": run_len,
                        "d_lag_pp": (g.loc[prev, "ey_lag"]
                                     - g.loc[run_start, "ey_lag"]) * 100,
                        "d_fwd_pp": (g.loc[prev, "ey_fwd"]
                                     - g.loc[run_start, "ey_fwd"]) * 100})
    sg = pd.DataFrame(seg).sort_values(["months"], ascending=False)
    sg.to_csv(HERE / "divergence.csv", index=False, encoding="utf-8")
    print(f"\n== 分歧期(月變動方向相反且連續 ≥3 個月),合共 {len(sg)} 段;最長十段 ==")
    if len(sg):
        print(sg.head(10).to_string(index=False, float_format="%.2f"))

    # ---- 覆蓋率逐年(印摘要)----
    cov = pd.read_csv(HERE / "coverage_by_year.csv")
    piv = cov.pivot(index="year", columns="series", values="cov_fwd_med")
    print("\n== 逐板塊逐年 cov_fwd 中位(市值覆蓋)==")
    print((piv * 100).round(1).to_string())
    lp = cov.pivot(index="year", columns="series", values="lowprec_med")
    print("\n== 逐板塊逐年低精度成員佔市值中位(%)==")
    print((lp * 100).round(1).to_string())

    # ---- 負盈利救回的格 ----
    mult = pd.read_csv(HERE.parent / "2026-09-02-multiples-oracle-scan"
                       / "sector_multiples.csv", parse_dates=["month_end"])
    m = d[["month_end", "series", "ey_lag"]].merge(
        mult[["month_end", "series", "pe_lag"]], on=["month_end", "series"])
    bad = m[(m["pe_lag"].isna()) | (m["pe_lag"] <= 0)]
    print(f"\n== pe_lag 未定義而 ey_lag 有值的格:{len(bad)} 格 ==")
    print(bad.groupby("series").agg(格數=("month_end", "count"),
                                    最早=("month_end", "min"),
                                    最遲=("month_end", "max")).to_string())


if __name__ == "__main__":
    main()
