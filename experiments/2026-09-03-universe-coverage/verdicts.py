# -*- coding: utf-8 -*-
"""KARST-173:四數與判詞總表(讀前面幾支腳本的結果,不重算原料)。

判準見 CRITERIA.md 第七、九節。
"""
from __future__ import annotations

import json

import pandas as pd

import common as C


def verdict(n_a: int, n_b: int, diff: float | None) -> str:
    if n_a < 50 or n_b < 50:
        return f"量不出(可算家數 {n_a} / {n_b},未達 50)"
    if diff is None:
        return "量不出(算不出差)"
    if abs(diff) >= 0.05:
        return "存在(" + ("十倍股較高" if diff > 0 else "十倍股較低") + ")"
    return "不存在(差 < 5 個百分點)"


def main() -> None:
    tb = pd.read_csv(C.OUT / "tenbagger_t0_v3.csv")
    tb["t0_year"] = pd.to_datetime(tb["t0"]).dt.year
    by_year = pd.read_csv(C.OUT / "base_rate_by_year.csv").set_index("年份")
    nc = json.loads((C.OUT / "netcash_compare.json").read_text(encoding="utf-8"))
    base = json.loads((C.OUT / "base_rate_summary.json").read_text(encoding="utf-8"))

    out: dict = {"四數": {}, "判詞": {}}

    # ① 覆蓋
    m = tb["mcap"]
    out["四數"]["① 覆蓋"] = {
        "十倍股名單": int(len(tb)),
        "接得回實體": int(tb["entity_id"].notna().sum()),
        "價格庫在 t0 有價": int(tb["t0_close"].notna().sum()),
        "面板在 t0 有列": int(tb["has_panel_at_t0"].fillna(False).sum()),
        "算得出市值": int(m.notna().sum()),
        "算得出 N1 淨現金": int(tb["n1"].notna().sum()),
        "算得出 N2 淨現金": int(tb["n2"].notna().sum()),
    }

    # ② 起步市值
    q = m.dropna()
    out["四數"]["② 起步市值(美元)"] = {
        "家數": int(len(q)),
        "中位": round(float(q.median()), 1),
        "四分一位": round(float(q.quantile(0.25)), 1),
        "四分三位": round(float(q.quantile(0.75)), 1),
        "低於 50 億的比例": round(float((q < 5e9).mean()), 4),
        "低於 3 億的比例": round(float((q < 3e8).mean()), 4),
    }

    # ③ 淨現金
    out["四數"]["③ 淨現金比率"] = nc["tenbagger"]
    out["判詞"]["③ N1(現金+短投−總負債 > 0)"] = nc["verdict"]["n1"]
    out["判詞"]["③ N2(現金−長短期債 > 0)"] = nc["verdict"]["n2"]

    # ④ >50% 回撤
    dd = tb[tb["drawdown_new"].notna()].copy()
    tb_rate = float((dd["drawdown_new"] <= -0.5).mean())
    inrange = dd[dd["t0_year"].between(2010, 2021)]
    w = inrange["t0_year"].value_counts()
    num = den = 0.0
    for y, cnt in w.items():
        if y in by_year.index:
            num += float(by_year.loc[y, "回撤逾五成比率"]) * int(cnt)
            den += int(cnt)
    uni_w = num / den if den else None
    diff = tb_rate - uni_w if uni_w is not None else None
    out["四數"]["④ 五年窗內 >50% 回撤"] = {
        "十倍股可算家數": int(len(dd)),
        "十倍股比率": round(tb_rate, 4),
        "對照組(逐年加權,2010–2021 那批 t0)": round(uni_w, 4) if uni_w else None,
        "對照組(全期加權)": base["回撤逾五成_全期加權"],
        "用於加權的十倍股家數": int(den),
        "差(百分點)": round(diff * 100, 2) if diff is not None else None,
    }
    out["判詞"]["④ >50% 回撤"] = verdict(int(len(dd)), int(base["cells_with_shares"]), diff)
    out["判詞"]["④ 附註"] = ("t0 是事後揀出的最佳起點,回撤低是揀出來的結果,"
                          "不是可用的過濾器;這個判詞只描述名單,不可當訊號")

    # 宇宙覆蓋率(對 KARST-162)
    summ = json.loads((C.OUT / "tenbagger_t0_summary.json").read_text(encoding="utf-8"))
    out["宇宙覆蓋率"] = summ["coverage"]
    n_known = summ["n_mcap_known"]
    u2 = summ["coverage"]["U2 全美小型股(<50億)"]
    lo, hi = u2["覆蓋率下限(未知當作不在)"], u2["覆蓋率上限(未知當作在)"]
    out["判詞"]["① 小型股宇宙撈得到十倍股"] = (
        f"量不出(算得出市值只有 {n_known} 家,U2 覆蓋率下限 {lo}、上限 {hi},"
        f"上下限相差 {round((hi - lo) * 100, 1)} 個百分點)"
        if (hi - lo) >= 0.10 else f"存在(U2 覆蓋率 {lo}–{hi})")

    # 基礎率
    out["基礎率(倖存者口徑)"] = {
        "宇宙": base["universe"], "年份": base["years"],
        "格數(有價有股數)": base["cells_with_shares"],
        "涉及實體": base["entities_touched"],
        "五年十倍率(逐年加權)": base["十倍率_全期加權"],
        "五年窗內 >50% 回撤率(逐年加權)": base["回撤逾五成_全期加權"],
        "逐年": base["by_year"],
    }
    (C.OUT / "verdicts.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
