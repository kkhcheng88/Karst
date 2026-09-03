# -*- coding: utf-8 -*-
"""KARST-172 步驟三:面板 v3 的覆蓋率體檢,加對面板 v2 抽 30 家對帳。唯讀(只寫 out/)。"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
V3 = REPO / "data" / "panel" / "quarterly_v3.parquet"
V2 = REPO / "experiments" / "2026-09-02-panel-scale-fix" / "out" / "panel_monthly_v2.parquet"

CORE = ["cash_and_equivalents", "total_debt", "revenue", "shares_outstanding"]
ALL_FIELDS = ["shares_outstanding", "cash_and_equivalents", "short_term_investments",
              "lt_debt", "st_debt", "total_debt", "liabilities", "assets", "equity",
              "revenue", "operating_cash_flow", "net_income"]
# v2 欄名 -> v3 欄名
PAIRS = {"cash": "cash_and_equivalents", "lt_debt": "lt_debt", "revenue": "revenue",
         "net_income": "net_income", "assets": "assets", "equity": "equity",
         "liabilities": "liabilities", "cfo": "operating_cash_flow"}


def coverage(panel: pd.DataFrame, ent: pd.DataFrame) -> dict:
    real = panel[panel["period_end"].notna()]
    latest = real.sort_values("period_end").groupby("entity_id").tail(1)
    out: dict = {}
    out["panel_rows"] = int(len(panel))
    out["real_rows"] = int(len(real))
    out["entities_total"] = int(panel["entity_id"].nunique())
    out["entities_with_rows"] = int(real["entity_id"].nunique())
    out["facts_status"] = panel.groupby("entity_id")["facts_status"].first(
    ).value_counts().to_dict()

    out["field_coverage_all_rows"] = {
        f: round(float(real[f].notna().mean()), 4) for f in ALL_FIELDS}
    out["field_coverage_latest_row"] = {
        f: round(float(latest[f].notna().mean()), 4) for f in ALL_FIELDS}
    out["entities_with_field_ever"] = {
        f: int(real.loc[real[f].notna(), "entity_id"].nunique()) for f in ALL_FIELDS}
    core_ok = latest[CORE].notna().all(axis=1)
    out["core_four"] = CORE
    out["entities_core_four_complete_latest"] = int(core_ok.sum())
    out["entities_core_four_complete_pct"] = round(
        float(core_ok.sum()) / out["entities_total"], 4)

    # 按市值分層
    tiers = ent[["entity_id", "approx_mcap_usd", "is_foreign_filer"]].copy()
    def tier(v):
        if pd.isna(v):
            return "無市值"
        if v < 5e8:
            return "<5 億"
        if v < 5e9:
            return "5-50 億"
        return ">50 億"
    tiers["tier"] = tiers["approx_mcap_usd"].map(tier)
    j = latest.merge(tiers, on="entity_id", how="right")
    rows = []
    for t, g in j.groupby("tier"):
        rec = {"tier": t, "entities": int(len(g))}
        for f in ALL_FIELDS:
            rec[f] = round(float(g[f].notna().mean()), 4)
        rec["core_four"] = round(float(g[CORE].notna().all(axis=1).mean()), 4)
        rows.append(rec)
    tier_df = pd.DataFrame(rows)
    tier_df.to_csv(OUT / "coverage_by_mcap_tier.csv", index=False, encoding="utf-8")
    out["by_tier"] = rows

    # 外國申報人
    fpi = j[j["is_foreign_filer"] == True]  # noqa: E712
    dom = j[j["is_foreign_filer"] == False]  # noqa: E712
    out["foreign_filer"] = {
        "entities": int(len(fpi)),
        "core_four": round(float(fpi[CORE].notna().all(axis=1).mean()), 4),
        "fields": {f: round(float(fpi[f].notna().mean()), 4) for f in ALL_FIELDS},
    }
    out["domestic_filer"] = {
        "entities": int(len(dom)),
        "core_four": round(float(dom[CORE].notna().all(axis=1).mean()), 4),
        "fields": {f: round(float(dom[f].notna().mean()), 4) for f in ALL_FIELDS},
    }
    out["missing_reason_counts"] = {
        f: real[f"{f}_missing_reason"].value_counts().to_dict()
        for f in ALL_FIELDS if f"{f}_missing_reason" in real.columns}
    out["shares_scale_suspect_rows"] = int(panel["shares_scale_suspect"].sum())
    out["shares_scale_suspect_entities"] = int(
        panel.loc[panel["shares_scale_suspect"], "entity_id"].nunique())
    out["restated_share"] = {
        f: round(float(real[f"{f}_was_restated"].fillna(False).mean()), 4)
        for f in ALL_FIELDS if f"{f}_was_restated" in real.columns}
    return out


def reconcile(panel: pd.DataFrame) -> dict:
    v2 = pd.read_parquet(V2)
    v2["entity_id"] = v2["cik"].astype(str).str.zfill(10)
    common = sorted(set(v2["entity_id"]) & set(panel["entity_id"]))
    step = max(1, len(common) // 30)
    sample = common[::step][:30]

    v3 = panel[panel["entity_id"].isin(sample) & panel["period_end"].notna()]
    v3idx = {(r.entity_id, pd.Timestamp(r.period_end)): r for r in v3.itertuples()}

    rows = []
    for v2f, v3f in PAIRS.items():
        endcol = f"{v2f}_end"
        if endcol not in v2.columns:
            continue
        sub = v2[v2["entity_id"].isin(sample) & v2[v2f].notna() & v2[endcol].notna()]
        sub = sub.drop_duplicates(subset=["entity_id", endcol])
        n = same = diff = absent = 0
        worst = []
        for r in sub.itertuples():
            key = (getattr(r, "entity_id"), pd.Timestamp(getattr(r, endcol)))
            hit = v3idx.get(key)
            n += 1
            if hit is None:
                absent += 1
                continue
            a = getattr(r, v2f)
            b = getattr(hit, v3f)
            if b is None or pd.isna(b):
                absent += 1
                continue
            if a == 0 and b == 0:
                same += 1
                continue
            rel = abs(a - b) / max(abs(a), abs(b), 1.0)
            if rel < 1e-6:
                same += 1
            else:
                diff += 1
                worst.append((rel, r.entity_id, str(key[1].date()), v2f, a, b))
        worst.sort(reverse=True)
        rows.append(dict(field_v2=v2f, field_v3=v3f, compared=n, identical=same,
                         different=diff, absent_in_v3=absent,
                         identical_pct=round(same / n, 4) if n else None,
                         worst=worst[:3]))
    pd.DataFrame([{k: v for k, v in r.items() if k != "worst"} for r in rows]).to_csv(
        OUT / "reconcile_v2_v3.csv", index=False, encoding="utf-8")
    return {"sample_entities": sample, "by_field": rows}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    panel = pd.read_parquet(V3)
    ent = pd.read_parquet(REPO / "data" / "universe" / "entities.parquet")
    rep = {"coverage": coverage(panel, ent), "reconcile": reconcile(panel)}
    (OUT / "coverage_report.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    c = rep["coverage"]
    print(json.dumps({k: c[k] for k in
                      ["panel_rows", "real_rows", "entities_total", "entities_with_rows",
                       "facts_status", "entities_core_four_complete_latest",
                       "entities_core_four_complete_pct", "field_coverage_latest_row",
                       "shares_scale_suspect_rows", "shares_scale_suspect_entities"]},
                     ensure_ascii=False, indent=2))
    print("--- 分層 ---")
    print(pd.DataFrame(c["by_tier"])[["tier", "entities", "core_four",
                                      "cash_and_equivalents", "total_debt",
                                      "revenue", "shares_outstanding"]].to_string())
    print("--- 對帳 ---")
    for r in rep["reconcile"]["by_field"]:
        print(r["field_v2"], "比較", r["compared"], "一樣", r["identical"],
              "不同", r["different"], "v3 無此格", r["absent_in_v3"])


if __name__ == "__main__":
    main()
