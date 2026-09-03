# -*- coding: utf-8 -*-
"""KARST-173:淨現金比率——十倍股 t0 對小型股宇宙 v1 同年 1 月 1 日(逐年加權)。

判準見 CRITERIA.md 第五、七、九節。零新抓,唯讀。
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import common as C

YEARS = list(range(2010, 2027))


def flags(df: pd.DataFrame) -> pd.DataFrame:
    """向量化版的 CRITERIA 第五節 N1 / N2。"""
    cash = df["cash_and_equivalents"]
    sti = df["short_term_investments"].fillna(0.0)
    liab = df["liabilities"]
    ltd = df["lt_debt"]
    std = df["st_debt"].fillna(0.0)
    n1 = pd.Series(pd.NA, index=df.index, dtype="boolean")
    ok1 = cash.notna() & liab.notna()
    n1[ok1] = (cash[ok1] + sti[ok1] - liab[ok1]) > 0
    n2 = pd.Series(pd.NA, index=df.index, dtype="boolean")
    ok2 = cash.notna() & ltd.notna()
    n2[ok2] = (cash[ok2] - (ltd[ok2] + std[ok2])) > 0
    return pd.DataFrame({"n1": n1, "n2": n2})


def main() -> None:
    v1 = pd.read_csv(C.UNIVERSE / "universe_smallcap_v1.csv", dtype={"entity_id": str})
    ids = set(v1["entity_id"].str.zfill(10))
    p = C.panel()
    p = p[p["entity_id"].isin(ids)].sort_values(["filed_date", "entity_id"])

    rows = []
    for y in YEARS:
        cut = pd.Timestamp(f"{y}-01-01")
        left = pd.DataFrame({"entity_id": sorted(ids), "when": cut}).sort_values("when")
        m = pd.merge_asof(left, p, left_on="when", right_on="filed_date",
                          by="entity_id", direction="backward")
        m = m[m["filed_date"].notna()]
        f = flags(m)
        rows.append(dict(
            年份=y, 有面板家數=int(len(m)),
            n1可算=int(f["n1"].notna().sum()),
            n1為正=int(f["n1"].fillna(False).sum()),
            n1比率=round(float(f["n1"].dropna().mean()), 4) if f["n1"].notna().any() else None,
            n2可算=int(f["n2"].notna().sum()),
            n2為正=int(f["n2"].fillna(False).sum()),
            n2比率=round(float(f["n2"].dropna().mean()), 4) if f["n2"].notna().any() else None))
    uni = pd.DataFrame(rows)
    uni.to_csv(C.OUT / "netcash_universe_by_year.csv", index=False, encoding="utf-8")
    print("=== 小型股宇宙 v1 逐年(每年 1 月 1 日,時點正確)===")
    print(uni.to_string(index=False))

    tb = pd.read_csv(C.OUT / "tenbagger_t0_v3.csv")
    tb["t0_year"] = pd.to_datetime(tb["t0"]).dt.year
    out = {"universe_by_year": rows, "tenbagger": {}, "verdict": {}}
    for k in ("n1", "n2"):
        sub = tb[tb[k].notna()]
        w = sub["t0_year"].value_counts()
        uni_i = uni.set_index("年份")
        num = den = 0.0
        for y, cnt in w.items():
            r = uni_i.loc[y, f"{k}比率"] if y in uni_i.index else None
            if r is None or pd.isna(r):
                continue
            num += float(r) * int(cnt)
            den += int(cnt)
        tb_rate = float(sub[k].astype(bool).mean()) if len(sub) else None
        uni_rate = num / den if den else None
        diff = (tb_rate - uni_rate) if (tb_rate is not None and uni_rate is not None) else None
        if len(sub) < 50:
            verdict = "量不出(十倍股可算家數 < 50)"
        elif diff is not None and abs(diff) >= 0.05:
            verdict = "存在(" + ("十倍股較常見" if diff > 0 else "十倍股較少見") + ")"
        else:
            verdict = "不存在(差 < 5 個百分點)"
        out["tenbagger"][k] = {
            "可算家數": int(len(sub)), "為正家數": int(sub[k].astype(bool).sum()),
            "比率": round(tb_rate, 4) if tb_rate is not None else None,
            "對照組(逐年加權)": round(uni_rate, 4) if uni_rate is not None else None,
            "差(百分點)": round(diff * 100, 2) if diff is not None else None,
            "t0年份權重": {int(a): int(b) for a, b in w.items()}}
        out["verdict"][k] = verdict
    (C.OUT / "netcash_compare.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"tenbagger": out["tenbagger"], "verdict": out["verdict"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
