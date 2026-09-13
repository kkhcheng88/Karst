# -*- coding: utf-8 -*-
"""KARST-236 修正版取數口徑:`A/finlib.py` 的副本,只改「同一期末多個 tag 誰贏」。

原版 `A/finlib.py` 的 `quarterly()` 逐 tag 走 `REV_TAGS`,以 `out.setdefault(en, v)`
收值 —— **哪個 tag 先命中就贏**,不比申報日。公司改用 ASC 606 之後會用新 tag 重列舊季,
而新 tag 正是 `REV_TAGS` 第一個,於是同一期末較晚申報的重述值蓋過最早申報的舊值(甚至
蓋過 T1 之後才公布的值)。本檔改成:**同一期末跨 tag 取 `filed` 最早那一份,同日再按
tag 次序**;財年末季推算(年報 340–380 日 − 同期 9 個月累計 255–285 日)照舊,但與直接
單季事實一併按 `(filed, tag 次序)` 比。每格附 `first_filed`。

`A/finlib.py` 本體**未改**。本檔與 `A/finlib.py` 的差異只在 `quarterly()` /
`quarterly_filed()` 兩支與新增的 `quarterly_full()`;其餘函式逐字沿用。
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

    照 `A/finlib.py` 原文,未改。回傳 {期末日: (值, filed)},filed 取兩者較晚。
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


def _merge(best: dict, en: str, v: float, f: str, idx: int, fy: bool) -> None:
    """同一期末:比 (filed, tag 次序);只有兩者都相同時才保留先到者。"""
    key = (f or "", idx)
    if en not in best or key < best[en]["key"]:
        best[en] = {"value": v, "first_filed": f, "fy_derived": fy, "key": key}


def quarterly_full(facts: dict, tags: list[str], lo: int = 80, hi: int = 100,
                   derive_fy: bool = False) -> dict[str, dict]:
    """期末日 → {value, first_filed, fy_derived}。

    **同一期末跨 tag 取 `filed` 最早那一份**(同日再按 `tags` 次序);`derive_fy=True`
    時,年報期末季推算值與直接單季事實一併按同一把尺比(推算值 filed 取年報與 9 個月
    累計的較晚者)。
    """
    best: dict[str, dict] = {}
    for idx, t in enumerate(tags):
        for (_st, en), (v, f) in _first_report(unit_rows(facts, t), lo, hi).items():
            _merge(best, en, v, f, idx, False)
    if derive_fy:
        for idx, t in enumerate(tags):
            for en, (v, f) in _year_end_quarters(facts, [t]).items():
                _merge(best, en, v, f, idx, True)
    return best


def quarterly(facts: dict, tags: list[str], lo: int = 80, hi: int = 100,
              derive_fy: bool = False) -> dict[str, float]:
    """期末日 → 修正後首報單季值(跨 tag 比申報日,最早申報者勝)。"""
    return {en: r["value"]
            for en, r in quarterly_full(facts, tags, lo, hi, derive_fy).items()}


def quarterly_filed(facts: dict, tags: list[str], lo: int = 80, hi: int = 100,
                    derive_fy: bool = True) -> dict[str, tuple[float, str]]:
    """同 `quarterly(derive_fy=True)`,連 filed 一併回傳(期末日 → (值, 最早 filed))。"""
    return {en: (r["value"], r["first_filed"])
            for en, r in quarterly_full(facts, tags, lo, hi, derive_fy).items()}


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


def quarterize_cumulative_filed(facts: dict, tags: list[str],
                                lo: int = 80, hi: int = 400) -> dict[str, tuple]:
    """同 `quarterize_cumulative`,但每個點附 `filed`(兩個累計事實取較晚者)。

    與 `A/finlib.py` 的 `quarterize_cumulative(cumulative(...))` 逐點同值 —— 同一組
    (start,end) 取首報、同一起日序列相減;`filed` 只多出來供「來源申報日」用。
    """
    rows: dict[tuple[str, str], tuple[float, str]] = {}
    for t in tags:
        for k, (v, f) in _first_report(unit_rows(facts, t), lo, hi).items():
            if k not in rows or (f and f < rows[k][1]):
                rows[k] = (v, f)
    by_start: dict[str, list] = {}
    for (st, en), (v, f) in rows.items():
        by_start.setdefault(st, []).append((en, v, f))
    out: dict[str, tuple] = {}
    for _st, lst in by_start.items():
        lst.sort()
        prev = None
        for en, v, f in lst:
            out[en] = ((v, f) if prev is None
                       else (v - prev[0], max(f, prev[1])))
            prev = (v, f)
    return out


def rec_full(facts: dict, tags: list[str], derive_fy: bool = True) -> dict[str, dict]:
    """期末日 → {value, first_filed, fy_derived, cum_derived}。

    與 `A3/audit_revenue_integrity.py` 的真值(`series(cross_tag=True)` 為主,
    `quarterize_cumulative` 補缺格)同一條,順序亦同:先跨 tag 最早申報,後補累計差分。
    """
    best = quarterly_full(facts, tags, derive_fy=derive_fy)
    for en, r in best.items():
        r.setdefault("cum_derived", False)
    for en, (v, f) in quarterize_cumulative_filed(facts, tags).items():
        if en in best:
            continue
        best[en] = {"value": v, "first_filed": f, "fy_derived": False,
                    "cum_derived": True}
    return best


def yoy(series: dict[str, float], end: str) -> float | None:
    e = date.fromisoformat(end)
    cands = sorted((abs((e - date.fromisoformat(k)).days - 365), k)
                   for k in series if 340 <= (e - date.fromisoformat(k)).days <= 390)
    if not cands:
        return None
    base = series[cands[0][1]]
    return None if base == 0 else series[end] / base - 1.0


def yoy_end(series: dict[str, float], end: str) -> str | None:
    """`yoy()` 用的去年同季期末日(340–390 日之前、最接近 365 日者)。"""
    e = date.fromisoformat(end)
    cands = sorted((abs((e - date.fromisoformat(k)).days - 365), k)
                   for k in series if 340 <= (e - date.fromisoformat(k)).days <= 390)
    return cands[0][1] if cands else None


def ocf_series(facts: dict) -> dict[str, float]:
    """經營現金流單季:累計差分為主,直接單季事實補缺格(與 KARST-235 核查真值同一條)。"""
    out = dict(quarterize_cumulative(cumulative(facts, OCF_TAGS)))
    for en, (v, _f) in quarterly_filed(facts, OCF_TAGS).items():
        out.setdefault(en, v)
    return out


def bundle(cik: str) -> dict:
    """一次取齊一家的季度損益、單季經營現金流、累計收入與年報期末(修正版口徑)。"""
    facts = load_facts(cik)
    if facts is None:
        return {"ok": False, "note": "無 companyfacts 快取"}
    rev_full = quarterly_full(facts, REV_TAGS, derive_fy=True)
    return {
        "ok": True, "note": "",
        "rev_q": {k: v["value"] for k, v in rev_full.items()},
        "rev_q_filed": {k: (v["value"], v["first_filed"])
                        for k, v in rev_full.items()},
        "rev_q_derived": tuple(k for k, v in rev_full.items() if v["fy_derived"]),
        "gp_full": quarterly_full(facts, GP_TAGS, derive_fy=True),
        "oi_full": quarterly_full(facts, OI_TAGS, derive_fy=True),
        "ocf_q": ocf_series(facts),
        "rev_cum": cumulative(facts, REV_TAGS),
        "rev_annual": [(s, e, v) for s, e, v in cumulative(facts, REV_TAGS, 330, 400)],
    }
