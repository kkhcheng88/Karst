"""Stage 1 (top level) — GICS sector-rotation map (option 2a, the DEFENSE / regime lens).

11 SPDR sector ETFs ranked by RS vs SPY, with the regime reads that actually matter for
rotation (raw return correlations are dominated by market beta, so we don't lean on them
here): leadership breadth (narrow = fragile / late-cycle), cyclical-vs-defensive tilt
(risk-on/off), and whether tech is confirming leadership.

ETF-PRICE mode: broad sectors have long clean history, so the ETF price IS the sector --
no holdings basket needed (that's only for young thematics like DRAM, see sector.py).

Caveat: RS uses RAW (price-return) closes -- high-yield sectors (XLU/XLP/XLRE, ~3%/yr) are
slightly understated over longer windows; for the short RS windows here it is minor, but
any multi-month sector BACKTEST must switch to total-return (dividend-adjusted) prices.
"""
from __future__ import annotations

import numpy as np

from signals import sma

from .dataio import load
from .schemas import SectorRotation

# The 11 SPDR (State Street) GICS sectors.
SPDR = [("XLK", "Tech"), ("XLC", "Comm"), ("XLY", "Discr"), ("XLI", "Indus"), ("XLF", "Fin"),
        ("XLB", "Materl"), ("XLE", "Energy"), ("XLV", "Health"), ("XLP", "Staples"),
        ("XLU", "Util"), ("XLRE", "RealEst")]
CYCLICAL = {"XLK", "XLC", "XLY", "XLI", "XLF", "XLB", "XLE"}   # risk-on (XLC growth-dominated)
DEFENSIVE = {"XLV", "XLP", "XLU", "XLRE"}                      # risk-off ballast


def _rs(c, spy, win):
    if len(c) <= win or len(spy) <= win:
        return float("nan")
    return float((c.iloc[-1] / c.iloc[-1 - win]) / (spy.iloc[-1] / spy.iloc[-1 - win]))


def _temp(rs63, above50, roc20):
    pts = (1 if rs63 == rs63 and rs63 > 1.05 else 0) + (1 if above50 else 0) + (1 if roc20 > 0 else 0)
    return "Cold" if pts == 0 else "Hot" if pts == 3 else "Warm"


def build_rotation() -> SectorRotation | None:
    spy = load("SPY")["close"]
    rows = []
    for etf, name in SPDR:
        try:
            c = load(etf)["close"]
        except Exception:
            continue
        rs63, rs21 = _rs(c, spy, 63), _rs(c, spy, 21)
        if rs63 != rs63:
            continue
        above200 = bool(c.iloc[-1] > sma(c, 200).iloc[-1]) if len(c) >= 200 else False
        above50 = bool(c.iloc[-1] > sma(c, 50).iloc[-1]) if len(c) >= 50 else False
        roc20 = float(c.iloc[-1] / c.iloc[-1 - 20] - 1) if len(c) > 20 else float("nan")
        rows.append({"etf": etf, "name": name, "rs63": round(rs63, 3),
                     "rs21": round(rs21, 3) if rs21 == rs21 else None, "above200": above200,
                     "temp": _temp(rs63, above50, roc20),
                     "group": "cyc" if etf in CYCLICAL else "def"})
    if not rows:
        return None
    rows.sort(key=lambda r: -r["rs63"])

    asof = str(load("SPY").index[-1].date())
    n_beating = sum(1 for r in rows if r["rs63"] > 1)
    cyc = [r["rs63"] for r in rows if r["group"] == "cyc"]
    dfn = [r["rs63"] for r in rows if r["group"] == "def"]
    cyc_rs = float(np.mean(cyc)) if cyc else float("nan")
    def_rs = float(np.mean(dfn)) if dfn else float("nan")
    tilt = "risk-on (cyclicals lead)" if cyc_rs >= def_rs else "risk-off (defensives lead)"
    breadth = "narrow" if n_beating <= 3 else "broad" if n_beating >= 6 else "mixed"
    tech_leading = any(r["etf"] == "XLK" and r["rs63"] > 1 for r in rows)

    leaders = ", ".join(f"{r['name']}({r['rs63']})" for r in rows[:3])
    laggards = ", ".join(f"{r['name']}({r['rs63']})" for r in rows[-2:])
    drivers = (f"tilt {tilt} | breadth {breadth} ({n_beating}/11 beat SPY) | "
               f"cyc {cyc_rs:.2f} vs def {def_rs:.2f} | tech {'leading' if tech_leading else 'NOT leading'} | "
               f"top: {leaders} | bottom: {laggards}")

    caveats = []
    if breadth == "narrow":
        caveats.append(f"narrow leadership ({n_beating}/11 beat SPY) -- fragile / late-cycle, less to rotate into")
    if not tech_leading:
        caveats.append("tech (XLK) NOT beating SPY -- the offense thesis (tech value-chains) is unconfirmed; favour defense/diversification")
    if tilt.startswith("risk-off"):
        caveats.append("defensives leading -- risk-off rotation underway")

    return SectorRotation(asof=asof, rows=rows, n_beating=n_beating, breadth=breadth, tilt=tilt,
                          cyc_rs=round(cyc_rs, 3), def_rs=round(def_rs, 3), tech_leading=tech_leading,
                          drivers=drivers, caveats=caveats)
