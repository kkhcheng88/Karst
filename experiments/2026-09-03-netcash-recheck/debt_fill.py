# -*- coding: utf-8 -*-
"""KARST-176 第一件事:面板 v3 總債務缺失分層表與補算前後覆蓋率(判準第四節)。

輸出 out/:
  debt_fill_by_tier_latest.csv   按市值分層(每家最新一期)
  debt_fill_by_tier_allrows.csv  按市值分層(全部面板列)
  debt_fill_summary.json         補前 / 補後覆蓋率
"""
from __future__ import annotations

import json

import pandas as pd

import common176 as K

TIERS = [(">50 億", 5e9, None), ("5-50 億", 5e8, 5e9),
         ("<5 億", None, 5e8), ("無市值", None, None)]


def tier_of(v):
    if v != v or v is None:
        return "無市值"
    if v > 5e9:
        return ">50 億"
    if v >= 5e8:
        return "5-50 億"
    return "<5 億"


def build(p: pd.DataFrame, ent: pd.DataFrame, unit: str) -> pd.DataFrame:
    j = p.merge(ent[["entity_id", "approx_mcap_usd"]], on="entity_id", how="left")
    j["tier"] = j["approx_mcap_usd"].map(tier_of)
    rows = []
    for t in [">50 億", "5-50 億", "<5 億", "無市值", "全體"]:
        g = j if t == "全體" else j[j.tier == t]
        if not len(g):
            continue
        n = len(g)
        n_orig = int(g["total_debt_orig"].notna().sum())
        n_fill = int((g["debt_fill_tag"] == "filled_st_only").sum())
        n_absent = int((g["debt_fill_tag"] == "tag_absent").sum())
        rows.append({
            "層": t, "口徑": unit, "總數": n,
            "有總債務(補前)": n_orig,
            "補前覆蓋率": round(n_orig / n, 4),
            "缺總債務": n - n_orig,
            "可補(只有短期借款)": n_fill,
            "補不到(兩個標籤都無)": n_absent,
            "有總債務(補後)": n_orig + n_fill,
            "補後覆蓋率": round((n_orig + n_fill) / n, 4),
            "覆蓋率提升(百分點)": round((n_fill / n) * 100, 2),
        })
    return pd.DataFrame(rows)


def main() -> None:
    p = K.panel_v3()
    ent = pd.read_parquet(K.UNIVERSE / "entities.parquet",
                          columns=["entity_id", "approx_mcap_usd"])

    # 每家最新一期(照 KARST-172 第三節的做法:以 period_end 最後一列計)
    latest = (p.sort_values(["entity_id", "period_end", "filed_date"])
              .groupby("entity_id", as_index=False).tail(1))
    t_latest = build(latest, ent, "每家最新一期")
    t_all = build(p, ent, "全部面板列")
    t_latest.to_csv(K.OUT / "debt_fill_by_tier_latest.csv", index=False,
                    encoding="utf-8-sig")
    t_all.to_csv(K.OUT / "debt_fill_by_tier_allrows.csv", index=False,
                 encoding="utf-8-sig")

    v1 = pd.read_csv(K.UNIVERSE / "universe_smallcap_v1.csv", dtype={"entity_id": str})
    ids = set(v1["entity_id"].str.zfill(10))
    sub = latest[latest.entity_id.isin(ids)]
    n = len(sub)
    summary = {
        "面板列數": int(len(p)),
        "實體數": int(p.entity_id.nunique()),
        "最新一期_補前覆蓋率": round(float(latest["total_debt_orig"].notna().mean()), 4),
        "最新一期_補後覆蓋率": round(float(latest["total_debt_filled"].notna().mean()), 4),
        "全部列_補前覆蓋率": round(float(p["total_debt_orig"].notna().mean()), 4),
        "全部列_補後覆蓋率": round(float(p["total_debt_filled"].notna().mean()), 4),
        "小型股名單v1_最新一期_家數": int(n),
        "小型股名單v1_補前覆蓋率": round(float(sub["total_debt_orig"].notna().mean()), 4) if n else None,
        "小型股名單v1_補後覆蓋率": round(float(sub["total_debt_filled"].notna().mean()), 4) if n else None,
        "租賃負債": "面板 v3 無此欄,原料層無標籤,一律補不到(tag_absent)",
    }
    (K.OUT / "debt_fill_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(t_latest.to_string(index=False))
    print()
    print(t_all.to_string(index=False))
    print()
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
