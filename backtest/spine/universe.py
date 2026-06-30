"""Universe loader — reads the watchlist YAML into typed entries."""
from __future__ import annotations

import os

import yaml

from .schemas import UniverseEntry

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "universe.yaml")

TIER1 = {"SPY", "QQQ", "SPMO"}  # the only names that may route to the options toolkit


def load_universe(path: str = DEFAULT_PATH):
    """Return (sectors_cfg: dict, entries: list[UniverseEntry])."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    sectors = raw.get("sectors") or {}
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
    """Append tier-2 Long entries derived from each sector's holdings ETF:
       - the ETF itself (a sector-level Long expressing the WHOLE sector, incl. foreign leaders)
       - each US-listed holding (the actionable single-name longs).
    Foreign holdings stay context-only (used in the sector temperature, not scanned as rows).
    """
    from .holdings import holdings as _holdings

    have = {e.ticker for e in entries}
    out = list(entries)
    for key, cfg in (sectors_cfg or {}).items():
        etf = cfg.get("holdings_etf")
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
