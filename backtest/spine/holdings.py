"""ETF holdings — define a sector basket from what an ETF actually holds.

yfinance `funds_data.top_holdings` gives the TOP holdings (<=10) + weights. We:
  - drop non-equity sleeves (cash / money-market, e.g. DRAM's FGXXX 14.9%),
  - tag US vs foreign by ticker suffix (000660.KS / 285A.T = foreign, MU = US),
  - renormalize weights over the remaining equities.

Foreign names are KEPT for the temperature (RS/ROC are unitless ratios, so currency
cancels; only the trading-session offset remains, minor over 20d). Only US names are
tier-2 ACTIONABLE longs; foreign leaders are context (and tradable in aggregate via
the ETF itself). Full holdings beyond top-10 need the issuer CSV / SEC N-PORT (later).
"""
from __future__ import annotations

import contextlib
import io
from functools import lru_cache

import yfinance as yf

_CASH_HINTS = ("oblig", "money market", "government", "treasury", "cash", "liquidity", "repo")

# Fallback if funds_data is unavailable (yfinance occasionally flaky). DRAM as of 2026-06.
_FALLBACK = {
    "DRAM": [("000660.KS", 0.247, "SK Hynix Inc"), ("005930.KS", 0.163, "Samsung Electronics Co Ltd"),
             ("285A.T", 0.066, "Kioxia Holdings Corp"), ("SNDK", 0.051, "SanDisk Corp"),
             ("MU", 0.048, "Micron Technology Inc"), ("STX", 0.042, "Seagate Technology Holdings PLC")],
}


def _is_cash(name: str) -> bool:
    n = (name or "").lower()
    return any(h in n for h in _CASH_HINTS)


def is_us_listed(ticker: str) -> bool:
    return "." not in ticker  # foreign tickers carry an exchange suffix (.KS / .T / ...)


@lru_cache(maxsize=32)
def holdings(etf: str):
    """Return [{ticker, weight (renormalized over equities), name, is_us}], heaviest first."""
    rows = None
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            th = yf.Ticker(etf).funds_data.top_holdings
        rows = [(str(ix), float(r["Holding Percent"]), str(r["Name"])) for ix, r in th.iterrows()]
    except Exception:
        rows = None
    if not rows:
        rows = _FALLBACK.get(etf)
    if not rows:
        return []
    eq = [(t, w, n) for (t, w, n) in rows if not _is_cash(n)]
    tot = sum(w for _, w, _ in eq) or 1.0
    out = [{"ticker": t, "weight": w / tot, "name": n, "is_us": is_us_listed(t)} for (t, w, n) in eq]
    return sorted(out, key=lambda d: -d["weight"])
