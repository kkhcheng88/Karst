# -*- coding: utf-8 -*-
"""KARST-154 事後診斷 —— 不改凍結判準,只拆解「優勢住在哪裡」。

這一節在看過主結果之後加寫,依 D-131 第 3 條(追加事後診斷,不改凍結判準)的做法,
其性質只能削弱結論不能加強結論:分半、剔走兩次大熊、優勢集中度、D-131 年化上限。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import run_test as R

OUT = R.OUT


def main() -> None:
    d = R.load()
    track = d["spy"]
    track = track[(track.index >= R.WIN_START) & (track.index <= R.WIN_END)]
    rf = d["rf"]
    sig_dates, months = R.signal_dates(track)

    votes, narrow = R.build_votes(d, months, R.BASE)
    e_A = R.composite_exposure(votes, narrow, R.BASE["theta"], "A")
    e_01 = pd.Series(np.where(e_A == 0.0, 0.0, 1.0), index=months)

    pos_A = R.daily_position(e_A, sig_dates, months, track.index)
    pos_01 = R.daily_position(e_01, sig_dates, months, track.index)
    r_A = R.levered_returns(track, rf, pos_A)
    r_01 = R.levered_returns(track, rf, pos_01)

    out = {}

    # ---------- 1. 分半 ----------
    halves = {
        "1990-2007": (pd.Timestamp("1990-01-01"), pd.Timestamp("2007-12-31")),
        "2008-2026": (pd.Timestamp("2008-01-01"), pd.Timestamp("2026-09-01")),
        "1990-1999": (pd.Timestamp("1990-01-01"), pd.Timestamp("1999-12-31")),
        "2000-2009": (pd.Timestamp("2000-01-01"), pd.Timestamp("2009-12-31")),
        "2010-2026": (pd.Timestamp("2010-01-01"), pd.Timestamp("2026-09-01")),
    }
    sub = {}
    for name, (a, b) in halves.items():
        m = (track.index >= a) & (track.index <= b)
        sub[name] = dict(
            bh=R.metrics(track[m], rf),
            rule01=R.metrics(r_01[(r_01.index >= a) & (r_01.index <= b)], rf,
                             pos_01[(pos_01.index >= a) & (pos_01.index <= b)]),
            ruleA=R.metrics(r_A[(r_A.index >= a) & (r_A.index <= b)], rf,
                            pos_A[(pos_A.index >= a) & (pos_A.index <= b)]),
        )
    out["split"] = sub

    # ---------- 2. 剔走兩次跌穿 -35% 的熊市 ----------
    drop = ((track.index >= "2000-09-01") & (track.index <= "2003-06-30")) | \
           ((track.index >= "2007-10-01") & (track.index <= "2009-12-31"))
    keep = ~drop
    out["ex_two_bears"] = dict(
        bh=R.metrics(track[keep], rf),
        rule01=R.metrics(r_01[keep[: len(r_01)]] if len(r_01) == len(track) else r_01[r_01.index.isin(track.index[keep])], rf),
        ruleA=R.metrics(r_A[r_A.index.isin(track.index[keep])], rf),
        note="剔走 2000-09..2003-06 與 2007-10..2009-12 兩段(接駁回報序列,非真實可交易路徑)",
    )

    # ---------- 3. 逐年超額 ----------
    yr = pd.DataFrame({
        "bh": (1 + track).groupby(track.index.year).prod() - 1,
        "rule01": (1 + r_01).groupby(r_01.index.year).prod() - 1,
        "ruleA": (1 + r_A).groupby(r_A.index.year).prod() - 1,
    })
    yr["excess01_pp"] = (yr["rule01"] - yr["bh"]) * 100
    yr["excessA_pp"] = (yr["ruleA"] - yr["bh"]) * 100
    yr.round(4).to_csv(OUT / "yearly.csv")
    top = yr.reindex(yr["excess01_pp"].abs().sort_values(ascending=False).index).head(8)
    out["top_years_by_abs_excess"] = {
        str(i): dict(bh_pct=round(r.bh * 100, 1), rule01_pct=round(r.rule01 * 100, 1),
                     excess01_pp=round(r.excess01_pp, 1))
        for i, r in top.iterrows()
    }
    n_pos = int((yr["excess01_pp"] > 0).sum())
    out["excess_year_count"] = dict(positive=n_pos, total=int(len(yr)),
                                    median_pp=round(float(yr["excess01_pp"].median()), 2))

    # ---------- 4. D-131 年化上限 ----------
    rf_avg = float(rf.reindex(track.index).ffill().mean())
    def ceiling(sh):
        return rf_avg + sh ** 2 / 2
    m01 = R.metrics(r_01, rf, pos_01)
    mA = R.metrics(r_A, rf, pos_A)
    mbh = R.metrics(track, rf)
    out["d131"] = dict(
        rf_avg=round(rf_avg * 100, 2),
        ceiling_bh=round(ceiling(mbh["sharpe"]) * 100, 1),
        ceiling_rule01=round(ceiling(m01["sharpe"]) * 100, 1),
        ceiling_ruleA=round(ceiling(mA["sharpe"]) * 100, 1),
        sharpe_needed_for_30pct=round(float(np.sqrt(2 * (0.30 - rf_avg))), 3),
    )

    # ---------- 5. 訊號的「太遲」量度:0x 首日相對高位/低位 ----------
    events = R.bear_events(track)
    tim = []
    p = pos_01.ffill()
    for ev in events:
        seg = p[(p.index >= ev["peak"]) & (p.index <= ev["end"])]
        z = seg[seg == 0.0]
        first_zero = z.index[0] if len(z) else None
        pre = p[(p.index >= ev["peak"] - pd.Timedelta(days=400)) & (p.index < ev["peak"])]
        prez = pre[pre == 0.0]
        tim.append(dict(
            peak=str(ev["peak"].date()), trough=str(ev["trough"].date()),
            depth_pct=round(ev["depth"] * 100, 1),
            first_zero=str(first_zero.date()) if first_zero is not None else "全程未減注",
            months_after_peak=round((first_zero - ev["peak"]).days / 30.44, 1) if first_zero is not None else None,
            months_before_trough=round((ev["trough"] - first_zero).days / 30.44, 1) if first_zero is not None else None,
            zero_before_peak=bool(len(prez) and pre.iloc[-1] == 0.0),
        ))
    out["timing_vs_events"] = tim

    (OUT / "diagnostics.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str),
                                          encoding="utf-8")

    print("=== 分半 ===")
    for k, v in sub.items():
        print(f"{k:10s} B&H {v['bh']['cagr']*100:6.2f}%  規則0/1 {v['rule01']['cagr']*100:6.2f}% "
              f"(差 {(v['rule01']['cagr']-v['bh']['cagr'])*100:+5.2f}pp)  "
              f"規則A {v['ruleA']['cagr']*100:6.2f}% (差 {(v['ruleA']['cagr']-v['bh']['cagr'])*100:+5.2f}pp)")
    print("\n=== 剔走兩次大熊 ===")
    ex = out["ex_two_bears"]
    print(f"B&H {ex['bh']['cagr']*100:.2f}%  規則0/1 {ex['rule01']['cagr']*100:.2f}%  規則A {ex['ruleA']['cagr']*100:.2f}%")
    print("\n=== 逐年超額(絕對值最大 8 年) ===")
    for y, v in out["top_years_by_abs_excess"].items():
        print(f"  {y}: 大市 {v['bh_pct']:+6.1f}%  規則 {v['rule01_pct']:+6.1f}%  超額 {v['excess01_pp']:+6.1f}pp")
    print(f"\n超額為正年數 {n_pos}/{len(yr)},中位超額 {out['excess_year_count']['median_pp']}pp")
    print("\n=== D-131 上限 ===", out["d131"])
    print("\n=== 減注時點 vs 熊市 ===")
    for t in tim:
        print("  ", t)


if __name__ == "__main__":
    main()
