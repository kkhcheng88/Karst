"""Premarket overlay for core-v2 + satellite watchlist (docs/2026-07-07_core_playbook.md).

Two daily runs (user design, 2026-07-09):
  POST-CLOSE (~5am HKT, after US close): playbook_readout.py -- closed-form next-close TRIGGER
    prices from the last close (dip/accumulate, sell-covered-call, 200SMA gate). Uses CLOSE.
  PREMARKET  (~1h before US open, ~20:30 HKT): THIS script -- fetches LIVE premarket prices and
    overlays them on those trigger levels: distance to each line + a chase-warning when an
    accumulate name gaps up. Uses PREMARKET price IN ADDITION to the close-based triggers.

Read-only, no orders. Premarket price = yfinance prepost 1m last bar (fallback fast_info).

    python backtest/premarket_check.py                 # default watchlist (core + accumulate set)
    python backtest/premarket_check.py MU LITE GEV      # custom tickers
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.playbook_readout import trigger_nums

# core gates + the current ACCUMULATE/constraint-confirmed satellite names (edit as verdicts move;
# theme_signal.py prints today's ACCUMULATE/BUY-ZONE set -- keep this in sync or pass args).
DEFAULT = ["SPY", "QQQ", "MU", "LITE", "GEV", "COHR", "ON", "AVGO"]


def fetch_premarket(sym):
    """Live premarket (or latest) price: yfinance prepost 1m last bar, fallback fast_info."""
    import yfinance as yf
    tk = yf.Ticker(sym)
    try:
        h = tk.history(period="1d", interval="1m", prepost=True)
        if len(h):
            return float(h["Close"].iloc[-1])
    except Exception:
        pass
    try:
        return float(tk.fast_info["lastPrice"])
    except Exception:
        return None


def verdict(pre, n):
    """One-line actionable read of premarket vs the post-close trigger levels."""
    gap = pre / n["last"] - 1
    if n["dip"] and pre <= n["dip"]:
        return "DIP TRIGGER HIT -> accumulate zone (RSI-2<10 level)"
    if n["sell"] and pre >= n["sell"]:
        return "SELL-CALL TRIGGER HIT -> RSI-2>90 (sell covered call)"
    if n["gate"] == "ON" and pre < n["cross"]:
        return "premarket below 200SMA -> LEAP-gate-flip WATCH"
    if gap >= 0.03:
        return f"gap +{gap*100:.1f}% -> CHASING; don't market-buy, wait / limit lower"
    if gap <= -0.03:
        return f"gap {gap*100:.1f}% -> weakness, moving toward accumulate"
    return "in range -- no trigger (hold / scale on weakness)"


def main(watchlist):
    print(f"==== PREMARKET CHECK {datetime.now():%Y-%m-%d %H:%M} "
          f"(live premarket vs post-close closed-form triggers) ====")
    for sym in watchlist:
        n = trigger_nums(sym)
        if n is None:
            print(f"{sym:6} triggers unavailable"); continue
        pre = fetch_premarket(sym)
        if pre is None:
            print(f"{sym:6} premarket unavailable (last close={n['last']:.2f})"); continue
        gap = (pre / n["last"] - 1) * 100
        dip_s = f"dip {n['dip']:.2f} [{(n['dip']/pre-1)*100:+.1f}%]" if n["dip"] else "dip n/a"
        sell_s = f"sell {n['sell']:.2f} [{(n['sell']/pre-1)*100:+.1f}%]" if n["sell"] else "sell n/a"
        print(f"{sym:6} close {n['last']:.2f} -> PREMKT {pre:.2f} ({gap:+.1f}%) | {dip_s} | {sell_s} "
              f"| 200SMA {n['cross']:.2f} gate {n['gate']}")
        print(f"       -> {verdict(pre, n)}")
    print("(dip/sell [%] = move from premarket to hit that trigger; triggers are CLOSE-based, "
          "premarket is an early read -- confirm at the close.)")


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
