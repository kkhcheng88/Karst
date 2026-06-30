"""Stage 1 — sector/subsector temperature, computed from the ETF's real holdings (option B).

Faithful to the actual sector: e.g. Memory is led by SK Hynix/Samsung (foreign), not the
US trio. Currency cancels (RS/ROC are unitless ratios). Two-level RS:
  rs_vs_market  = basket vs SPY     (sector vs whole market)
  rs_vs_parent  = basket vs SEMI    (intra-sector rotation -> leader/laggard, feeds INV-5)
Plus breadth/coherence to catch a Warm reading that is really one name carrying the basket.

Temperature here is Layer-1 (price) ONLY; Compass capital-flow / narrative overlays are Phase 2.
"""
from __future__ import annotations

import numpy as np

from signals import sma

from .dataio import load
from .holdings import holdings
from .schemas import SectorContext

_WIN = 20  # RS / ROC window


def _ratio(s, win=_WIN):
    if s is None or len(s) <= win:
        return float("nan")
    return float(s.iloc[-1] / s.iloc[-1 - win])


def _above50(s):
    if s is None or len(s) < 50:
        return None
    return bool(s.iloc[-1] > s.rolling(50).mean().iloc[-1])


def _parent_ratio(proxies):
    rs = [_ratio(load(p)["close"]) for p in proxies]
    rs = [r for r in rs if r == r]
    return float(np.mean(rs)) if rs else float("nan")


def build_sector_context(key: str, cfg: dict):
    etf = cfg.get("holdings_etf")
    members = holdings(etf) if etf else []
    if not members:
        return None

    parent = cfg.get("parent")
    proxies = cfg.get("parent_proxy") or []
    spy_r = _ratio(load("SPY")["close"])
    parent_r = _parent_ratio(proxies) if proxies else float("nan")

    rows = []
    for m in members:
        try:
            s = load(m["ticker"], min_rows=21)["close"]
        except Exception:
            continue
        r20 = _ratio(s)
        if r20 != r20:
            continue
        rows.append({**m, "ratio20": r20, "roc20": r20 - 1, "above50": _above50(s)})
    if not rows:
        return None

    tot = sum(r["weight"] for r in rows) or 1.0
    for r in rows:
        r["w"] = r["weight"] / tot

    basket_ratio = sum(r["w"] * r["ratio20"] for r in rows)
    roc20 = basket_ratio - 1
    rs_vs_market = basket_ratio / spy_r if spy_r == spy_r else float("nan")
    rs_vs_parent = basket_ratio / parent_r if parent_r == parent_r else float("nan")
    parent_rs_vs_market = parent_r / spy_r if (parent_r == parent_r and spy_r == spy_r) else float("nan")

    above = [r["above50"] for r in rows if r["above50"] is not None]
    breadth = float(np.mean([1.0 if a else 0.0 for a in above])) if above else float("nan")
    disp = float(np.std([r["roc20"] for r in rows])) if len(rows) > 1 else 0.0

    contribs = {r["ticker"]: r["w"] * r["roc20"] for r in rows}
    total_c = sum(contribs.values())
    if total_c > 0:
        leader = max(contribs, key=contribs.get)
        leader_share = contribs[leader] / total_c
    else:
        leader = max(rows, key=lambda r: r["w"])["ticker"]
        leader_share = float("nan")
    leader_is_us = next((r["is_us"] for r in rows if r["ticker"] == leader), True)

    rs_pt = 1 if (rs_vs_market == rs_vs_market and rs_vs_market > 1.05) else 0
    br_pt = 1 if (breadth == breadth and breadth >= 0.5) else 0
    roc_pt = 1 if roc20 > 0 else 0
    layer1 = rs_pt + br_pt + roc_pt
    temperature = "Cold" if layer1 == 0 else "Hot" if layer1 == 3 else "Warm"
    warm = 1 if temperature in ("Warm", "Hot") else 0

    if leader_share == leader_share and (leader_share >= 0.6 or (breadth == breadth and breadth <= 0.34)):
        coherence = "leader-carried"
    elif leader_share == leader_share and breadth == breadth and breadth >= 0.66 and leader_share < 0.6:
        coherence = "broad"
    else:
        coherence = "mixed"

    for r in rows:
        r["rs_vs_parent"] = r["ratio20"] / parent_r if parent_r == parent_r else float("nan")
    ranked = sorted(rows, key=lambda r: r["rs_vs_parent"] if r["rs_vs_parent"] == r["rs_vs_parent"] else -1,
                    reverse=True)
    # INV-5 laggard is judged among the ACTIONABLE (US-listed) members only -- a non-tradeable
    # foreign leader is context, never an actionable "laggard". `rank` is the full-basket RS rank.
    us_rank_of = {r["ticker"]: i for i, r in enumerate([r for r in ranked if r["is_us"]], 1)}
    n_us = len(us_rank_of)
    member_rank = {}
    for i, r in enumerate(ranked, 1):
        rvp = r["rs_vs_parent"]
        us_rank = us_rank_of.get(r["ticker"])
        member_rank[r["ticker"]] = {
            "rank": i, "us_rank": us_rank, "n_us": n_us,
            "rs_vs_parent": round(rvp, 3) if rvp == rvp else None, "is_us": r["is_us"],
            "is_laggard": bool(r["is_us"] and us_rank and us_rank > 2),
            "weight": round(r["w"], 3), "name": r["name"], "roc20": round(r["roc20"], 3),
        }

    caveats = []
    if coherence == "leader-carried":
        tail = f" ({leader_share:.0%})" if leader_share == leader_share else ""
        caveats.append(f"narrow strength: {leader} carrying the sector{tail} -- chase leader only (INV-5)")
    if not leader_is_us:
        caveats.append(f"sector leader {leader} is not US-listed -- express via {etf} ETF, or the strongest US name")
    if any(not r["is_us"] for r in rows):
        caveats.append("foreign holdings (KR/JP) measured on their own sessions; currency cancels in RS/ROC, offset minor")

    pn = parent or "parent"
    drivers = (f"{temperature} (L1 {layer1}/3) | RS vs mkt {rs_vs_market:.2f}, vs {pn} {rs_vs_parent:.2f} | "
               f"{pn} vs mkt {parent_rs_vs_market:.2f} | ROC20 {roc20 * 100:+.1f}% | "
               f"breadth {breadth * 100:.0f}%>50DMA | coherence {coherence} (leader {leader})")

    def _r(x):
        return round(x, 3) if x == x else float("nan")

    return SectorContext(
        sector=key, parent=parent, members=[r["ticker"] for r in rows], weight_mode="etf",
        rs_vs_market=_r(rs_vs_market), rs_vs_parent=_r(rs_vs_parent), parent_rs_vs_market=_r(parent_rs_vs_market),
        roc20=round(roc20, 4), layer1_score=layer1, temperature=temperature, warm=warm,
        breadth_above50=_r(breadth), roc_dispersion=round(disp, 4), leader=leader,
        leader_share=_r(leader_share), coherence=coherence, member_rank=member_rank,
        drivers=drivers, caveats=caveats,
    )


def build_all(sectors_cfg: dict) -> dict:
    out = {}
    for key, cfg in (sectors_cfg or {}).items():
        try:
            ctx = build_sector_context(key, cfg)
        except Exception:
            ctx = None
        if ctx is not None:
            out[key] = ctx
    return out
