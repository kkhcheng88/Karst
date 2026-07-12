"""thesis/crypto_governance.py -- Phase-3 architecture Sec5 defect #1 fix ("governance covers
only 39% of capital -- crypto's 61% has no kill rule, no ladder in real numbers").

Scope, precisely (read before touching this file):
  1. Operationalize the EXISTING, already-specified UPSIDE recovery ladder for ETH
     (docs/2026-07-08_transition_plan.md Sec7: $2,600 -> sell 25% into core; $3,500 -> sell
     another 25%; $4,338 = cost basis -> keep only the permanent satellite share) as an actual
     checked/alerted rule instead of a paper commitment nobody is watching daily.
  2. Derive an ANALOGOUS ladder for SOL ("SOL 同款一張" -- same-style ladder, per the same doc)
     since only ETH's absolute $ levels were given. Derivation: apply ETH's ladder as FRACTIONS
     OF COST BASIS (2600/4338=59.9%, 3500/4338=80.7%, 4338/4338=100%) to SOL's own cost basis
     ($232) rather than as a ratio to today's price (which would make the derived SOL levels
     depend on which day this was computed -- not stable/pre-registerable). This gives SOL
     rungs at ~$139.0 / ~$187.2 / $232.0. **THESE SOL NUMBERS ARE DERIVED, NOT USER-SPECIFIED
     -- flagged in every output line until the user confirms or overrides them.**
  3. Instrument (WS4-style "裝錶"): track ETH/BTC price ratio as a passive monitoring metric
     (no rule attached -- this is observability, not a trigger).

Explicitly, deliberately OUT of scope -- do not "complete" this by adding it:
  A downside/time-based exit for crypto. docs/2026-07-08_transition_plan.md Sec8 records that
  the user was ASKED about exactly this ("三年未返 $2,600 就檢討" / "ETH/BTC 比率創新低削半" were
  the suggested forms) and explicitly DECLINED, with the transcript recording:
  "用戶知情後維持決定 -> 尊重,方案 B 執行,唔再重提" (user maintained the decision after being
  informed -> respect it, execute plan B, don't raise it again). The 2026-07-08 architecture
  doc's Sec5 defect table (written by a different, later session) suggested a downside/time
  exit as part of "the fix" without apparent awareness of this prior, explicit, recorded
  refusal. This script does NOT add one. If a future session is tempted to "fix" this gap,
  read Sec8 of the transition plan FIRST.

This is a READ-ONLY alert tool. It NEVER places, cancels, or modifies any order -- crypto
sells (like every other trade in this system) are the user's own manual action, on their own
exchange account. This script's only job is to tell them WHEN their own pre-committed plan
says to act, so the decision isn't made in an emotional live moment (the whole point of writing
the ladder down in advance, per the transition plan's own stated rationale).

State: thesis/.raw/crypto_governance_state.json (gitignored) -- tracks which rungs have
already been alerted, so reruns don't re-alert the same crossed rung every day.

Run: python thesis/crypto_governance.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.data import load

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(ROOT, ".raw", "crypto_governance_state.json")

# ETH: user-specified, docs/2026-07-08_transition_plan.md Sec7 (verbatim, do not "round" or
# recompute these against a live price -- they are deliberately fixed in advance).
ETH_COST = 4338.0
ETH_LADDER = [
    (2600.0, "sell 25% into core"),
    (3500.0, "sell another 25%"),
    (ETH_COST, "keep only the permanent satellite share (cost basis reached)"),
]

# SOL: DERIVED (see module docstring) from ETH's ladder as fractions of cost basis, applied to
# SOL's own cost basis. NOT user-specified -- flagged in every printed line.
SOL_COST = 232.0
SOL_LADDER = [(SOL_COST * (lvl / ETH_COST), note) for lvl, note in ETH_LADDER]

BTC_EXEMPT_NOTE = "BTC exempted from any ladder/kill rule (user's own 2026-07-08 decision, ~1% position)"


def _load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"eth_rungs_fired": [], "sol_rungs_fired": []}


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def check_ladder(symbol, price, ladder, fired_key, state, derived):
    new_alerts = []
    fired = set(state.get(fired_key, []))
    for i, (level, note) in enumerate(ladder):
        rung_id = f"{symbol}_{i}"
        if price >= level and rung_id not in fired:
            tag = " [DERIVED, not user-specified -- confirm before treating as final]" if derived else ""
            new_alerts.append(f"{symbol} crossed ${level:,.1f} -> {note}{tag}")
            fired.add(rung_id)
    state[fired_key] = sorted(fired)
    return new_alerts


def run():
    eth = load("ETH-USD")["close"]
    sol = load("SOL-USD")["close"]
    btc = load("BTC-USD")["close"]
    eth_px, sol_px, btc_px = float(eth.iloc[-1]), float(sol.iloc[-1]), float(btc.iloc[-1])
    eth_btc_ratio = eth_px / btc_px

    state = _load_state()
    alerts = []
    alerts += check_ladder("ETH", eth_px, ETH_LADDER, "eth_rungs_fired", state, derived=False)
    alerts += check_ladder("SOL", sol_px, SOL_LADDER, "sol_rungs_fired", state, derived=True)
    _save_state(state)

    print(f"==== crypto governance check {date.today().isoformat()} ====")
    print(f"ETH ${eth_px:,.2f} (cost ${ETH_COST:,.0f}, "
          f"{'above' if eth_px >= ETH_COST else 'below'} cost, "
          f"{(eth_px/ETH_COST-1)*100:+.1f}%)")
    print(f"SOL ${sol_px:,.2f} (cost ${SOL_COST:,.0f}, "
          f"{'above' if sol_px >= SOL_COST else 'below'} cost, "
          f"{(sol_px/SOL_COST-1)*100:+.1f}%)")
    print(f"BTC ${btc_px:,.2f}  |  ETH/BTC ratio (instrumentation only, no rule): {eth_btc_ratio:.5f}")
    print(f"  ({BTC_EXEMPT_NOTE})")
    if alerts:
        print("\n*** LADDER RUNG(S) CROSSED -- this is a READ-ONLY alert, no order was placed ***")
        for a in alerts:
            print(f"  {a}")
    else:
        print("\nno new ladder rungs crossed this run.")
    print("\n(No downside/time exit is implemented for crypto -- deliberate, per the user's "
          "2026-07-08 recorded decision. See module docstring before 'completing' this.)")


if __name__ == "__main__":
    run()
