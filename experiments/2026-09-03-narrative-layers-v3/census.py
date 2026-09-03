# -*- coding: utf-8 -*-
"""KARST-170 覆蓋率普查(判準凍結之前跑,只數家數與檔案,零回報、零相關)。

目的:知道 v2.2 表在每個切片有幾多成員入得到數、有無文本,好把判準寫得實在。
本腳本**不掂任何價格回報、任何相關係數**——只讀價格面板的欄名。

跑法: set PYTHONUTF8=1 && python census.py
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

CHAIN = REPO / "experiments" / "2026-09-02-chain-layers" / "chain_membership_v2_2.csv"
PX_OLD = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
PX_NEW = REPO / "experiments" / "2026-09-02-narrative-layers-v2" / "data" / "new_close.parquet"
ITEM1_V1 = REPO / "experiments" / "2026-09-02-narrative-layers" / "data" / "item1"
ITEM1_V2 = REPO / "experiments" / "2026-09-02-narrative-layers-v2" / "data" / "item1"
MANIFEST = REPO / "data" / "sec" / "10k_text" / "manifest.jsonl"

SLICES = ["2023-06-30", "2025-06-30"]
MAX_STALE_DAYS = 500
MIN_ROSTER = 5


def read_chain():
    with io.open(CHAIN, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def approx(row):
    return "近似" in (row.get("valid_from_basis") or "")


def rows_in_effect(rows, T):
    cut = pd.Timestamp(T)
    out = []
    for r in rows:
        vf, vt = r["valid_from"].strip(), r["valid_to"].strip()
        if not vf:
            continue
        vfd = pd.Timestamp(vf)
        if vt:
            vtd = pd.Timestamp(vt)
            if vtd < vfd or vtd < cut:
                continue
        if vfd > cut:
            continue
        # 近似 valid_from 的成員只入 2023-01-01 以後的切片
        if approx(r) and cut < pd.Timestamp("2023-01-01"):
            continue
        out.append(r)
    return out


def main():
    rows = read_chain()
    roster = {}
    for r in rows:
        roster.setdefault(r["theme"], set()).add(r["ticker"])
    big = {t for t, s in roster.items() if len(s) >= MIN_ROSTER}
    small = sorted(set(roster) - big)

    px_cols = set(pd.read_parquet(PX_OLD).columns) | set(pd.read_parquet(PX_NEW).columns)

    # 年報快取索引
    man = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        man.setdefault(rec["ticker"], []).append((rec["filingDate"], rec["accession"]))

    rep = {"n_rows": len(rows), "n_themes": len(roster),
           "n_companies": len(set(r["ticker"] for r in rows)),
           "themes_lt5": small, "n_themes_lt5": len(small),
           "n_themes_ge5": len(big), "slices": {}}

    for T in SLICES:
        eff = [r for r in rows_in_effect(rows, T) if r["theme"] in big]
        tks = sorted({r["ticker"] for r in eff})
        themes = sorted({r["theme"] for r in eff})
        with_px = [t for t in tks if t in px_cols]
        item1_have = []
        for t in tks:
            if (ITEM1_V1 / f"{t}_{T}.txt.gz").exists() or (ITEM1_V2 / f"{t}_{T}.txt.gz").exists():
                item1_have.append(t)
        cut = pd.Timestamp(T)
        cache_ok = []
        for t in tks:
            cands = [f for f, a in man.get(t, []) if pd.Timestamp(f) <= cut]
            if cands and (cut - pd.Timestamp(max(cands))).days <= MAX_STALE_DAYS:
                cache_ok.append(t)
        # 逐鏈:有價格的成員數
        per_theme = {}
        for th in themes:
            mem = sorted({r["ticker"] for r in eff if r["theme"] == th})
            per_theme[th] = {"roster": len(mem),
                             "with_price": len([t for t in mem if t in px_cols])}
        rep["slices"][T] = {
            "n_rows_in_effect": len(eff), "n_themes_in_effect": len(themes),
            "n_companies": len(tks), "n_with_price": len(with_px),
            "n_item1_derivative": len(item1_have),
            "n_cache_10k_within_500d": len(cache_ok),
            "n_price_and_cache": len([t for t in with_px if t in cache_ok]),
            "themes_with_ge2_priced": len([t for t, v in per_theme.items() if v["with_price"] >= 2]),
            "themes_with_ge3_priced": len([t for t, v in per_theme.items() if v["with_price"] >= 3]),
            "per_theme": per_theme,
            "missing_price": sorted(set(tks) - set(with_px)),
        }
        print(f"[{T}] rows={len(eff)} themes={len(themes)} cos={len(tks)} "
              f"price={len(with_px)} item1={len(item1_have)} cache10k={len(cache_ok)} "
              f"price&cache={rep['slices'][T]['n_price_and_cache']}")

    (OUT / "census.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print("themes <5 roster:", len(small))
    print("written -> out/census.json")


if __name__ == "__main__":
    raise SystemExit(main())
