"""Universe loader — reads the watchlist YAML into typed entries."""
from __future__ import annotations

import os

import yaml

from .schemas import UniverseEntry

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "universe.yaml")
_THEMES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "thesis", "themes.yaml")

TIER1 = {"SPY", "QQQ", "SPMO"}  # the only names that may route to the options toolkit


def _resolve_thesis_baskets(sectors: dict):
    """For any sector declaring `thesis: <slug>`, pull its basket tickers from thesis/themes.yaml
    (the SINGLE source of truth -> no universe/themes drift). The benchmark_etf is excluded from the
    basket (it is a cross-check long, not a constituent). Silently leaves the sector unresolved if the
    themes file / slug is missing (falls back to any explicit `tickers`)."""
    need = {c["thesis"] for c in sectors.values() if isinstance(c, dict) and c.get("thesis")}
    if not need:
        return
    try:
        themes = (yaml.safe_load(open(_THEMES_PATH, encoding="utf-8")) or {}).get("themes", {}) or {}
    except Exception:
        return
    for cfg in sectors.values():
        slug = isinstance(cfg, dict) and cfg.get("thesis")
        if not slug or slug not in themes:
            continue
        bench = cfg.get("benchmark_etf")
        cfg["tickers"] = [t for t in (themes[slug].get("tickers") or []) if t != bench]


def load_universe(path: str = DEFAULT_PATH):
    """Return (sectors_cfg: dict, entries: list[UniverseEntry])."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    sectors = raw.get("sectors") or {}
    _resolve_thesis_baskets(sectors)
    entries = []
    for t in raw.get("tickers") or []:
        tier = t["tier"]
        # Hard guard: a misconfigured 'options' tier on a non-TIER1 name is downgraded to long.
        if tier == "options" and t["ticker"] not in TIER1:
            tier = "long"
        entries.append(UniverseEntry(
            ticker=t["ticker"], tier=tier,
            sector=t.get("sector", "MARKET"), iv_proxy=t.get("iv_proxy"),
        ))
    return sectors, entries


def expand_with_sectors(sectors_cfg: dict, entries: list):
    """Append tier-2 Long entries for each sector. Two kinds:

    A) EXPLICIT ticker list (`tickers:`) -- a cross-sectional value chain that no single ETF
       represents (photonics, AI-power, ...). Each named US stock is an actionable long; an
       optional `benchmark_etf` is added as a sector-level long for cross-check only.
    B) HOLDINGS ETF (`holdings_etf:`) -- a GICS-representable sector (e.g. Memory/DRAM). The ETF
       itself + its US-listed holdings become longs; foreign holdings stay context (temperature only).

    First-seen wins (a ticker shared by two chains lands in the sector listed first).
    """
    from .holdings import holdings as _holdings

    have = {e.ticker for e in entries}
    out = list(entries)
    for key, cfg in (sectors_cfg or {}).items():
        if cfg.get("tickers"):                                   # A) explicit chain
            bench = cfg.get("benchmark_etf")
            if bench and bench not in have:
                out.append(UniverseEntry(ticker=bench, tier="long", sector=key))
                have.add(bench)
            for tk in cfg["tickers"]:
                if tk not in have:
                    out.append(UniverseEntry(ticker=tk, tier="long", sector=key))
                    have.add(tk)
            continue
        etf = cfg.get("holdings_etf")                            # B) holdings ETF
        if not etf:
            continue
        if etf not in have:
            out.append(UniverseEntry(ticker=etf, tier="long", sector=key))
            have.add(etf)
        for m in _holdings(etf):
            if m["is_us"] and m["ticker"] not in have:
                out.append(UniverseEntry(ticker=m["ticker"], tier="long", sector=key))
                have.add(m["ticker"])
    return out
