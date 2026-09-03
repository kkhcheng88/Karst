# -*- coding: utf-8 -*-
"""KARST-173:A-045 查證——近似市值與時點正確市值劃出來的 50 億線,名單差幾多。

判準見 CRITERIA.md 第十節。零新抓,唯讀。
"""
from __future__ import annotations

import json

import pandas as pd

import common as C

ASOF = pd.Timestamp("2026-09-02")
LINE = 5e9


def main() -> None:
    ent = pd.read_parquet(C.UNIVERSE / "entities.parquet")
    v1 = pd.read_csv(C.UNIVERSE / "universe_smallcap_v1.csv", dtype={"entity_id": str})
    v1_ids = set(v1["entity_id"].str.zfill(10))

    # v1 的非市值資格:剔 SIC 6221 信託型 ETP,三家人手保留照 RULES 第九節
    keep = set(v1_ids)
    pool = ent[(ent["sic"].astype(str) != "6221") | ent["entity_id"].isin(keep)]
    pool_ids = set(pool["entity_id"])
    print(f"候選池:{len(pool_ids)}(entities 全表 {len(ent)})")

    # 甲:近似市值(封面股數 × 2026-09-02 現價),即 v1 用的那一套
    a_mcap = dict(zip(ent["entity_id"], ent["approx_mcap_usd"]))

    # 乙:時點正確股數(面板 v3,filed <= 2026-09-02)× 價格庫同日 close
    p = C.panel()
    p = p[p["shares_outstanding"].notna() & (p["filed_date"] <= ASOF)]
    pit_shares = p.groupby("entity_id")["shares_outstanding"].last()
    px = C.load_prices(entity_ids=pool_ids, since="2026-08-01",
                       cols=("entity_id", "ticker", "date", "close", "series_role"))
    px = px[px["date"] <= ASOF].sort_values("date")
    last_px = px.groupby("entity_id").last()

    rows = []
    for e in sorted(pool_ids):
        am = a_mcap.get(e)
        sh = pit_shares.get(e)
        pr = last_px["close"].get(e)
        bm = float(sh) * float(pr) if (sh is not None and pd.notna(sh)
                                       and pr is not None and pd.notna(pr)) else None
        rows.append(dict(entity_id=e,
                         approx_mcap=float(am) if pd.notna(am) else None,
                         pit_mcap=bm,
                         in_v1=e in v1_ids))
    d = pd.DataFrame(rows)
    both = d[d["approx_mcap"].notna() & d["pit_mcap"].notna()].copy()
    both["甲"] = both["approx_mcap"] < LINE
    both["乙"] = both["pit_mcap"] < LINE
    A = set(both.loc[both["甲"], "entity_id"])
    B = set(both.loc[both["乙"], "entity_id"])
    sym = A ^ B
    uni = A | B
    ratio = len(sym) / len(uni) if uni else None

    both["rel"] = ((both["pit_mcap"] - both["approx_mcap"]).abs()
                   / both[["pit_mcap", "approx_mcap"]].abs().max(axis=1))
    res = {
        "asof": ASOF.date().isoformat(),
        "line_usd": LINE,
        "pool": len(pool_ids),
        "both_computable": int(len(both)),
        "甲_家數(近似市值 < 50 億)": len(A),
        "乙_家數(時點正確市值 < 50 億)": len(B),
        "對稱差": len(sym),
        "聯集": len(uni),
        "對稱差比例": round(ratio, 4) if ratio is not None else None,
        "市值相對差_中位": round(float(both["rel"].median()), 4),
        "市值相對差_九十分位": round(float(both["rel"].quantile(0.9)), 4),
        "相對差 > 10% 的家數": int((both["rel"] > 0.10).sum()),
    }
    if len(both) < 4000:
        res["判"] = "unverified(量不出:可算家數 < 4,000)"
    elif ratio is not None and ratio <= 0.10:
        res["判"] = "holds(對稱差 <= 10%)"
    else:
        res["判"] = "refuted(對稱差 > 10%)"

    both.sort_values("rel", ascending=False).head(30).to_csv(
        C.OUT / "a045_worst.csv", index=False, encoding="utf-8")
    both.to_csv(C.OUT / "a045_pairs.csv", index=False, encoding="utf-8")
    (C.OUT / "a045_summary.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
