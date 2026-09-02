# -*- coding: utf-8 -*-
"""KARST-166 第一步:補面板 v2 缺的三欄(短期債務、商譽、無形資產)。

照 CRITERIA.md 第二節。知情時點機器直接 import KARST-146 的 build_panel.py
(first_versions / pick_tag / period_type),不自寫一套,確保與面板一字不差。

原料只讀 experiments/2026-09-02-fundamentals-panel/data/secfacts/(KARST-146 已抓),
不新抓 EDGAR、不另存副本(D-134)。

輸出:out/panel_extra_v1.parquet(ticker, month_end, st_debt, goodwill, intangibles)
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
from collections import defaultdict

import pandas as pd

ROOT = pathlib.Path(r"C:\projects\Karst")
PANEL_DIR = ROOT / "experiments" / "2026-09-02-fundamentals-panel"
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(PANEL_DIR))
import build_panel as bp  # noqa: E402  知情時點機器,原封不動

CACHE = PANEL_DIR / "data" / "secfacts"

# 每個「族」各自獨立取值。st_debt 的兩族相加(短期借款與一年內到期長債是兩件事)。
FAMILIES: dict[str, list[str]] = {
    "st_borrow": ["ShortTermBorrowings", "OtherShortTermBorrowings",
                  "ShorttermBorrowings"],
    "lt_debt_current": ["LongTermDebtCurrent",
                        "CurrentPortionOfLongtermBorrowings"],
    "goodwill": ["Goodwill"],
    "intangibles": ["IntangibleAssetsNetExcludingGoodwill",
                    "FiniteLivedIntangibleAssetsNet",
                    "IntangibleAssetsOtherThanGoodwill"],
}


def extract(facts: dict) -> dict[str, list[dict]]:
    obs: dict[str, list[dict]] = {f: [] for f in FAMILIES}
    blocks = facts.get("facts", {})
    for scope in ("us-gaap", "ifrs-full"):
        blk = blocks.get(scope, {})
        if not blk:
            continue
        for field, taglist in FAMILIES.items():
            for prio, tag in enumerate(taglist):
                units = blk.get(tag, {}).get("units", {})
                for unit, points in units.items():
                    if unit not in bp.OK_UNITS_MONEY:
                        continue
                    for pt in points:
                        form = pt.get("form")
                        if form not in bp.FORMS_PRIMARY and form not in bp.FORMS_AMEND:
                            continue
                        ptype = bp.period_type(pt.get("start"), pt.get("end"))
                        if ptype != "instant":       # 全部是存量欄
                            continue
                        filed = pt.get("filed")
                        if not filed or pt.get("val") is None:
                            continue
                        obs[field].append(dict(
                            tag=tag, prio=prio, start=pt.get("start"),
                            end=pt["end"], filed=filed, val=float(pt["val"]),
                            ptype=ptype, amended=form in bp.FORMS_AMEND))
    return obs


def value_at(series: list[dict], ms: str):
    """面板 RULES 第一、二、五節:filed ≤ ms 之中 end 最近者,同 end 取首版。"""
    cands = [r for r in series if r["filed"] <= ms]
    tag = bp.pick_tag(cands)
    if tag is None:
        return None
    same = [c for c in cands if c["tag"] == tag]
    latest_end = max(c["end"] for c in same)
    best = min([c for c in same if c["end"] == latest_end], key=lambda c: c["filed"])
    return best["val"]


def main() -> None:
    uni = pd.read_csv(PANEL_DIR / "out" / "universe_cik.csv", dtype=str).fillna("")
    have = uni[uni.cik != ""].copy()
    months = bp.month_ends(bp.PANEL_START, bp.PANEL_END)
    print(f"{len(have)} tickers, {len(months)} month ends", flush=True)

    frames, missing = [], []
    t0 = time.time()
    for i, (_, r) in enumerate(have.iterrows(), 1):
        p = CACHE / f"CIK{r.cik}.json"
        if not p.exists() or p.stat().st_size == 0:
            missing.append(r.ticker)
            continue
        facts = json.loads(p.read_text(encoding="utf-8"))
        obs = extract(facts)
        series = {f: bp.first_versions(v) for f, v in obs.items()}
        allfiled = [x["filed"] for v in series.values() for x in v]
        if not allfiled:
            continue
        lo, hi = min(allfiled), max(allfiled)
        hi6 = (pd.Timestamp(hi) + pd.DateOffset(months=6)).strftime("%Y-%m-%d")
        rows = []
        for m in months:
            ms = m.strftime("%Y-%m-%d")
            if ms < lo or ms > hi6:
                continue
            sb = value_at(series["st_borrow"], ms)
            lc = value_at(series["lt_debt_current"], ms)
            st = None if (sb is None and lc is None) else (sb or 0.0) + (lc or 0.0)
            rows.append({
                "ticker": r.ticker, "month_end": m,
                "st_debt": st,
                "st_debt_parts": int(sb is not None) + int(lc is not None),
                "goodwill": value_at(series["goodwill"], ms),
                "intangibles": value_at(series["intangibles"], ms),
            })
        if rows:
            frames.append(pd.DataFrame(rows))
        if i % 150 == 0:
            print(f"  {i}/{len(have)}  {time.time() - t0:.0f}s", flush=True)

    extra = pd.concat(frames, ignore_index=True)
    extra = extra.sort_values(["ticker", "month_end"]).reset_index(drop=True)
    extra.to_parquet(OUT / "panel_extra_v1.parquet", index=False)

    meta = {
        "source": "experiments/2026-09-02-fundamentals-panel/data/secfacts (KARST-146 已抓,只讀)",
        "new_fetches": 0,
        "rows": int(len(extra)),
        "tickers": int(extra.ticker.nunique()),
        "tickers_without_facts_file": missing,
        "coverage": {c: round(float(extra[c].notna().mean()), 4)
                     for c in ("st_debt", "goodwill", "intangibles")},
        "st_debt_two_parts_share": round(float((extra.st_debt_parts == 2).mean()), 4),
    }
    (OUT / "panel_extra_meta.json").write_text(
        json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(meta["coverage"], ensure_ascii=False), flush=True)
    print(f"rows {len(extra):,} tickers {extra.ticker.nunique()}", flush=True)


if __name__ == "__main__":
    main()
