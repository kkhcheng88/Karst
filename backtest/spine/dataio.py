"""Per-run cached data loader.

`data.load` hits the network (defeatbeta/yfinance). A single scan touches some
symbols more than once (SPY/SPMO/^VIX feed both the gate and tier-1 expression),
so cache per process. Callers must treat returned frames as READ-ONLY (the cache
hands back the same object) — slice/join to derive, never mutate in place.
"""
from __future__ import annotations

from functools import lru_cache

import data as _data


@lru_cache(maxsize=64)
def load(symbol: str, min_rows: int = 100):
    return _data.load(symbol, min_rows=min_rows)
