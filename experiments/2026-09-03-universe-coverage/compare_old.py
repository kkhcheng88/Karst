# -*- coding: utf-8 -*-
"""KARST-173:新舊市值逐項並列(對 KARST-162 的 tenbagger_t0_mcap.csv)。唯讀。"""
from __future__ import annotations

import json

import pandas as pd

import common as C

OLD = (C.REPO / "experiments" / "2026-09-03-smallcap-universe-study" / "out" /
       "tenbagger_t0_mcap.csv")


def main() -> None:
    old = pd.read_csv(OLD)[["ticker", "t0", "mcap", "mcap_src"]].rename(
        columns={"mcap": "mcap_old", "mcap_src": "src_old"})
    new = pd.read_csv(C.OUT / "tenbagger_t0_v3.csv")[
        ["ticker", "t0", "mcap", "mcap_missing_reason", "shares_filed_date"]].rename(
        columns={"mcap": "mcap_new"})
    d = old.merge(new, on=["ticker", "t0"], how="outer")
    d["用了事後股數"] = d["src_old"].fillna("").str.contains("含事後")
    both = d[d["mcap_old"].notna() & d["mcap_new"].notna()].copy()
    both["rel"] = ((both["mcap_new"] - both["mcap_old"]).abs()
                   / both[["mcap_new", "mcap_old"]].abs().max(axis=1))
    res = {
        "舊數可算": int(d["mcap_old"].notna().sum()),
        "新數可算": int(d["mcap_new"].notna().sum()),
        "兩邊都可算": int(len(both)),
        "只有舊數": int((d["mcap_old"].notna() & d["mcap_new"].isna()).sum()),
        "只有新數": int((d["mcap_new"].notna() & d["mcap_old"].isna()).sum()),
        "舊數之中用了事後股數(前視)": int(d["用了事後股數"].sum()),
        "只有舊數那批之中用了事後股數": int(
            (d["用了事後股數"] & d["mcap_old"].notna() & d["mcap_new"].isna()).sum()),
        "同一批公司的中位_舊": round(float(both["mcap_old"].median()), 1),
        "同一批公司的中位_新": round(float(both["mcap_new"].median()), 1),
        "相對差_中位": round(float(both["rel"].median()), 4),
        "相對差 > 10% 的家數": int((both["rel"] > 0.10).sum()),
        "相對差 > 50% 的家數": int((both["rel"] > 0.50).sum()),
        "只有舊數那批的缺因": d.loc[d["mcap_old"].notna() & d["mcap_new"].isna(),
                                "mcap_missing_reason"].value_counts().to_dict(),
    }
    both.sort_values("rel", ascending=False).head(20).to_csv(
        C.OUT / "compare_old_worst.csv", index=False, encoding="utf-8")
    d.to_csv(C.OUT / "compare_old_pairs.csv", index=False, encoding="utf-8")
    (C.OUT / "compare_old_summary.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("\n最大差十家:")
    print(both.sort_values("rel", ascending=False)
          .head(10)[["ticker", "t0", "mcap_old", "mcap_new", "src_old", "rel"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
