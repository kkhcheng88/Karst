"""Market-cap getter for cap-weighting sector baskets.

yfinance fast_info.market_cap — light + fast (~0.5-1.3s), unlike the heavy .info.
Cached per run. Returns None on any failure so callers fall back to equal-weight
(the coherence metric, not the weighting, is what guards single-name dominance).
"""
from __future__ import annotations

import contextlib
import io
from functools import lru_cache

import yfinance as yf


@lru_cache(maxsize=128)
def market_cap(symbol: str) -> float | None:
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            mc = getattr(yf.Ticker(symbol).fast_info, "market_cap", None)
        if mc and mc > 0:
            return float(mc)
    except Exception:
        pass
    return None
