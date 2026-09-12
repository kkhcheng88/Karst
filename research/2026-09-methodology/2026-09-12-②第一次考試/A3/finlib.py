# -*- coding: utf-8 -*-
"""KARST-222 票 A 共用:由 `data/sec/companyfacts` 取單季與累計財務數列(首報值)。

只讀,不改任何既有檔。供 s8(對照預測)與 s9(取證包)共用。
口徑與 `research/2026-09-methodology/2026-09-12-暴露差異模組v1/part3_operating.py` 一致,
分別是這裡一律取**首報值**(同一 (start,end) 取 filed 最早那份),重述不用。
"""
from __future__ import annotations

import gzip
import json
from datetime import date
from pathlib import Path

ROOT = Path(r"C:\projects\Karst")
CF = ROOT / "data" / "sec" / "companyfacts"

REV_TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
            "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax",
            "SalesRevenueGoodsNet", "RegulatedAndUnregulatedOperatingRevenue"]
GP_TAGS = ["GrossProfit"]
OI_TAGS = ["OperatingIncomeLoss"]
OCF_TAGS = ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]


def load_facts(cik: str) -> dict | None:
    p = CF / ("CIK%s.json.gz" % cik)
    if not p.exists():
        return None
    try:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, EOFError):
        return None


def unit_rows(facts: dict, tag: str, want: str = "USD") -> list[dict]:
    node = facts.get("facts", {}).get("us-gaap", {}).get(tag)
    if not node:
        return []
    out = []
    for unit, rows in node.get("units", {}).items():
        if unit == want:
            out += rows
    return out


def _first_report(rows: list[dict], lo: int, hi: int) -> dict:
    """(start,end) → filed 最早那份的值;回傳 {(start,end): (val, filed)}。"""
    best: dict[tuple[str, str], tuple[float, str]] = {}
    for r in rows:
        st, en, v = r.get("start"), r.get("end"), r.get("val")
        if st is None or en is None or v is None:
            continue
        try:
            d = (date.fromisoformat(en) - date.fromisoformat(st)).days
        except ValueError:
            continue
        if not (lo <= d <= hi):
            continue
        k = (st, en)
        f = r.get("filed", "")
        if k not in best or f < best[k][1]:
            best[k] = (float(v), f)
    return best


def _year_end_quarters(facts: dict, tags: list[str]) -> dict[str, tuple[float, str]]:
    """年報期末那一季的單季值 = 年報(340–380 日) − 同一開始日的 9 個月累計(255–285 日)。

    A3 新增(票 A″ 第 3 步已用同一條):2021 年後多數公司不再於 facts 報 80–100 日的
    第四季 duration,只報年報與季度累計;不補這一季,季末事件的取證包數列會整條空。
    回傳 {期末日: (值, filed)};filed 取兩者較晚,代表這條數最早可被公眾看到的時間。
    """
    out: dict[str, tuple[float, str]] = {}
    for t in tags:
        ytd9: dict[str, tuple[float, str, str]] = {}
        for (st, en), (v, f) in _first_report(unit_rows(facts, t), 255, 285).items():
            ytd9.setdefault(st, (v, f, en))
        for (st, en), (v, f) in _first_report(unit_rows(facts, t), 340, 380).items():
            if en in out:
                continue
            hit = ytd9.get(st)
            if hit is None:
                continue
            v9, f9, end9 = hit
            try:
                gap = (date.fromisoformat(en) - date.fromisoformat(end9)).days
            except ValueError:
                continue
            if not (60 <= gap <= 130) or v - v9 <= 0:
                continue
            out[en] = (v - v9, max(f, f9))
    return out


def quarterly(facts: dict, tags: list[str], lo: int = 80, hi: int = 100,
              derive_fy: bool = False) -> dict[str, float]:
    """期末日 → 首報單季值;同一期末多個 tag 按 tags 次序取先者。

    `derive_fy=True` 時,補上 facts 未直報的年報期末季(見 `_year_end_quarters`)。
    """
    out: dict[str, float] = {}
    for t in tags:
        for (st, en), (v, _f) in _first_report(unit_rows(facts, t), lo, hi).items():
            out.setdefault(en, v)
    if derive_fy:
        for en, (v, _f) in _year_end_quarters(facts, tags).items():
            out.setdefault(en, v)
    return out


def quarterly_filed(facts: dict, tags: list[str]) -> dict[str, tuple[float, str]]:
    """同 `quarterly(derive_fy=True)`,但連 filed 一併回傳(期末日 → (值, 最早 filed))。"""
    out: dict[str, tuple[float, str]] = {}
    for t in tags:
        for (st, en), (v, f) in _first_report(unit_rows(facts, t), 80, 100).items():
            if en not in out or f < out[en][1]:
                out[en] = (v, f)
    for en, (v, f) in _year_end_quarters(facts, tags).items():
        if en not in out:
            out[en] = (v, f)
    return out


def cumulative(facts: dict, tags: list[str], lo: int = 80, hi: int = 400) -> list[tuple]:
    """所有 (start,end) 的累計值,首報;回傳 [(start,end,val)] 按期長排。"""
    seen: dict[tuple[str, str], tuple[float, str]] = {}
    for t in tags:
        for k, (v, f) in _first_report(unit_rows(facts, t), lo, hi).items():
            if k not in seen or f < seen[k][1]:
                seen[k] = (v, f)
    return sorted([(k[0], k[1], v) for k, (v, _f) in seen.items()],
                  key=lambda x: (x[1], x[0]))


def quarterize_cumulative(cum: list[tuple]) -> dict[str, float]:
    """累計值相減得單季(現金流量表只報累計)。同一起日序列內相減。"""
    by_start: dict[str, list[tuple]] = {}
    for st, en, v in cum:
        by_start.setdefault(st, []).append((en, v))
    out: dict[str, float] = {}
    for st, rows in by_start.items():
        rows.sort()
        prev = None
        for en, v in rows:
            out[en] = v if prev is None else v - prev
            prev = v
    return out


def yoy(series: dict[str, float], end: str) -> float | None:
    e = date.fromisoformat(end)
    cands = sorted((abs((e - date.fromisoformat(k)).days - 365), k)
                   for k in series if 340 <= (e - date.fromisoformat(k)).days <= 390)
    if not cands:
        return None
    base = series[cands[0][1]]
    return None if base == 0 else series[end] / base - 1.0


def bundle(cik: str) -> dict:
    """一次取齊一家的季度損益、單季經營現金流、累計收入與年報期末。"""
    facts = load_facts(cik)
    if facts is None:
        return {"ok": False, "note": "無 companyfacts 快取"}
    rev_q = quarterly(facts, REV_TAGS, derive_fy=True)
    return {
        "ok": True, "note": "",
        "rev_q": rev_q,
        "rev_q_filed": quarterly_filed(facts, REV_TAGS),
        "rev_q_direct": tuple(quarterly(facts, REV_TAGS).keys()),
        "gp_q": quarterly(facts, GP_TAGS, derive_fy=True),
        "oi_q": quarterly(facts, OI_TAGS, derive_fy=True),
        "ocf_q": quarterize_cumulative(cumulative(facts, OCF_TAGS)),
        "rev_cum": cumulative(facts, REV_TAGS),
        "rev_annual": [(s, e, v) for s, e, v in cumulative(facts, REV_TAGS, 330, 400)],
    }
