"""Stage 0 — the market gate.

Computed from price/vol ETFs + index VIX (all free, all backtestable):
  trend   = SPY > 200SMA            (the single most robust tool — layer2 §1; reuse regime.classify)
  vol     = ^VIX bands + iv_rank    (risk-appetite A/B/C/D — Compass regime_matrix outer layer)
  breadth = IWM > 200SMA            (small-cap participation; SPY-up/IWM-down = late-cycle warning)
  term    = ^VIX / ^VIX3M           (>1 backwardation = near-term stress; the one free fragility add)
  momo    = RS(SPMO / SPY) 63d      (momentum FACTOR in favor or not — SPMO is a factor, not market)

gate (0/1) = SPY above its 200SMA (eligible for new long/risk). The label adds texture:
  gate=1 clean    -> risk_on
  gate=1 fragile  -> risk_on_fragile   (uptrend but breadth/term/momentum warns)
  gate=0 calm     -> wait
  gate=0 high-IV  -> defend            (the scorecard CASH regime)

Flow/positioning overlays (dealer gamma walls, CTA scores, Fear&Greed) are deliberately
NOT here — paid / not-free-backtestable; they enter as tagged overlays in a later phase.
"""
from __future__ import annotations

import pandas as pd

import regime

from .dataio import load
from .schemas import MarketContext


def _risk_appetite(vix_last: float) -> str:
    if vix_last >= 25:
        return "A"   # extreme panic
    if vix_last >= 20:
        return "B"   # recovery
    if vix_last >= 15:
        return "C"   # normal
    return "D"       # extreme greed


def _above_200sma(symbol: str) -> bool | None:
    df = load(symbol)
    s = df["close"]
    if len(s) < 200:
        return None
    return bool(s.iloc[-1] > s.rolling(200).mean().iloc[-1])


def _rs_63d(num: str, den: str, win: int = 63) -> float:
    a, b = load(num)["close"], load(den)["close"]
    if len(a) <= win or len(b) <= win:
        return float("nan")
    return float((a.iloc[-1] / a.iloc[-1 - win]) / (b.iloc[-1] / b.iloc[-1 - win]))


def build_market_context() -> MarketContext:
    spy = load("SPY")[["high", "low", "close"]]
    vix = load("^VIX", min_rows=50)["close"]
    df = spy.join(vix.rename("vix"), how="inner").dropna()
    f = regime.classify(df, df["vix"]).dropna()
    last = f.iloc[-1]
    asof = str(last.name.date())

    vix_last = float(df["vix"].loc[last.name])
    appetite = _risk_appetite(vix_last)
    ivr = float(last["iv_rank"])
    spy_above = bool(last["dist"] > 0)
    spy_dist = float(last["dist"])

    # VIX term structure (free fragility signal)
    try:
        vix3m = float(load("^VIX3M", min_rows=50)["close"].iloc[-1])
        term = vix_last / vix3m if vix3m else float("nan")
    except Exception:
        term = float("nan")
    term_backwardation = bool(term == term and term > 1.0)  # term==term filters NaN

    iwm_above = _above_200sma("IWM")
    breadth_divergence = bool(spy_above and iwm_above is False)

    rs = _rs_63d("SPMO", "SPY")
    momentum_on = bool(rs == rs and rs > 1.0)

    high_iv = bool(ivr > 0.70 or vix_last >= 25)
    fragile = bool(breadth_divergence or term_backwardation or not momentum_on)
    gate = 1 if spy_above else 0
    if gate:
        gate_label = "risk_on_fragile" if fragile else "risk_on"
    else:
        gate_label = "defend" if high_iv else "wait"

    caveats = []
    if breadth_divergence:
        caveats.append("SPY uptrend but IWM (small-cap) < 200SMA — narrow breadth, late-cycle warning")
    if term_backwardation:
        caveats.append(f"VIX term backwardation ({term:.2f}>1) — near-term stress")
    if rs == rs and not momentum_on:
        caveats.append(f"momentum factor SPMO lagging SPY (RS {rs:.2f}) — defensive rotation")
    if not spy_above and high_iv:
        caveats.append("SPY < 200SMA + high IV — defend/reduce (downturns can bounce: flags risk, not certain loss)")

    drivers = (
        f"SPY {'above' if spy_above else 'below'} 200SMA ({spy_dist * 100:+.1f}%) | "
        f"VIX {vix_last:.1f} (rank {ivr * 100:.0f}%, {appetite}) | term {term:.2f} | "
        f"IWM {'+' if iwm_above else '-' if iwm_above is False else '?'} | "
        f"SPMO-RS {rs:.2f} {'on' if momentum_on else 'off'} | ADX {last['adx']:.0f} | "
        f"regime {last['regime']}"
    )

    return MarketContext(
        asof=asof, risk_appetite=appetite, vix=round(vix_last, 2), vix_iv_rank=round(ivr, 3),
        vix_term=round(term, 3) if term == term else float("nan"),
        spy_above_200sma=spy_above, spy_dist=round(spy_dist, 4), spy_adx=round(float(last["adx"]), 1),
        spy_regime=str(last["regime"]), iwm_above_200sma=bool(iwm_above) if iwm_above is not None else False,
        breadth_divergence=breadth_divergence, momentum_on=momentum_on,
        gate=gate, gate_label=gate_label, drivers=drivers, caveats=caveats,
    )
