# Result — Real options-chain spot-check vs LEAP pricing model

**Date:** 2026-07-09  **Script:** `backtest/experiments/exp_chain_spotcheck.py`  **Tag:** 🟡 confirms base case, does NOT close crash-vega risk

## Question
Core v2 prices the 1y LEAP with `IV_1y = m * (VIX_or_VXN/100)`, m ∈ {0.85 base, 1.00, 1.15}
(`backtest/experiments/exp_leap_real_sweep.py`). The 2026-07-06 adversarial addendum flagged
that a constant multiplier maps a 30d VIX spike 1:1 into the 1y tenor during crashes, which is
wrong (term structure inverts — 1y moves far less than 30d in a crash). This spot-check asks
the narrower, answerable question: **in TODAY's calm market, is the constant-m base level even
approximately right, and does the flat-vol assumption miss skew at the deep-ITM deltas used by
the "steady" LEAP variant (0.70Δ)?**

## Method
- yfinance live `option_chain()` snapshot, SPY (vs ^VIX) and QQQ (vs ^VXN), pulled 2026-07-09
  ~00:03 UTC.
- Provenance: SPY spot **$745.40**, QQQ spot **$711.44**, VIX **16.90** (46.8 %ile of trailing
  252d), VXN **27.86** (87.7 %ile of trailing 252d).
- LEAP expiry: nearest standard monthly in the 330–420d window → **2027-06-30** for both
  (T = 356 calendar days) — this is a June-2027 expiry, i.e. ~1y out, matching the core-v2 tenor.
- Delta computed per-strike from the CHAIN's own `impliedVolatility` via BSM
  (`backtest/bsm.py:call_delta`), q = trailing-12m gross dividend yield (SPY 1.01%, QQQ 0.43%),
  r = 4.5% (T-bill proxy, only affects d1/d2 marginally).
- Short-call check: SPY nearest ~21DTE expiry (2026-07-31, T=22d), nearest-to-0.30Δ call.
- IV rank: VIX/VXN 252-trading-day percentile of the current level.
- Raw JSON dump: `backtest/experiments/_chain_spotcheck_raw.json` (not committed data, provenance
  only — regenerate via the script for a fresh pull).

## Results — 1|LEAP delta model vs real chain (expiry 2027-06-30, ~356 DTE)

### SPY (spot $745.40, VIX=16.90, q=1.01%)
| strike | delta | real IV | model m=0.85 | model m=1.00 | model m=1.15 | diff vs m=1.15 | implied m (real/VIX) |
|---|---|---|---|---|---|---|---|
| 745 (ATM) | 0.60 | 23.1% | 14.4% | 16.9% | 19.4% | **+3.7pp** | 1.37 |
| 780 (0.50Δ) | 0.51 | 20.6% | 14.4% | 16.9% | 19.4% | **+1.2pp** | 1.22 |
| 689 (0.70Δ) | 0.70 | 27.5% | 14.4% | 16.9% | 19.4% | **+8.1pp** | 1.63 |
| 610 (0.80Δ) | 0.80 | 33.5% | 14.4% | 16.9% | 19.4% | **+14.0pp** | 1.98 |

### QQQ (spot $711.44, VXN=27.86, q=0.43%)
| strike | delta | real IV | model m=0.85 | model m=1.00 | model m=1.15 | diff vs m=1.15 | implied m (real/VXN) |
|---|---|---|---|---|---|---|---|
| 710 (ATM) | 0.61 | 31.8% | 23.7% | 27.9% | 32.0% | −0.2pp | 1.14 |
| 770 (0.50Δ) | 0.50 | 29.5% | 23.7% | 27.9% | 32.0% | −2.6pp | 1.06 |
| 650 (0.70Δ) | 0.71 | 35.1% | 23.7% | 27.9% | 32.0% | **+3.1pp** | 1.26 |
| 575 (0.80Δ) | 0.80 | 39.9% | 23.7% | 27.9% | 32.0% | **+7.9pp** | 1.43 |

## Skew check
**Confirmed, and monotonic on both underlyings.** As strike falls (deeper ITM call / higher
delta), real IV rises steadily — SPY 20.6% (0.50Δ) → 27.5% (0.70Δ) → 33.5% (0.80Δ); QQQ 29.5% →
35.1% → 39.9%. This is the standard equity index skew (low-strike puts bid up, and by put-call
parity the low-strike calls inherit the same implied vol) showing up cleanly at 1y tenor.

**Implication for delta choice:** the model's flat-vol assumption (one IV for the whole chain)
is roughly OK at 0.50Δ but **increasingly wrong the deeper ITM you go**. At 0.70Δ ("穩" variant)
the real entry cost implies m≈1.6 (SPY) / 1.3 (QQQ) — already above the top of the current grid
(1.15). At 0.80Δ it's m≈2.0 (SPY) / 1.4 (QQQ). So the deep-ITM LEAP legs are more expensive to
enter than the sandbox credits them for, on TOP of the crash-vega underestimate already flagged
in the adversarial addendum — the two errors compound in the same direction (both understate
deep-ITM cost/risk). This is a second, independent reason (skew, not just term-structure) to
prefer the 0.50Δ flagship over 0.70/0.80Δ, or to add a skew adjustment if 0.70Δ is kept.

## Base-m calibration (today, calm market)
- **At 0.50Δ (the flagship LEAP strike), m=1.15 is the closest grid point for SPY** (real
  20.6% vs model 19.4%, only +1.2pp low) but the true implied multiplier is 1.22, i.e. slightly
  above even the top of the grid.
- **For QQQ at 0.50Δ, m=1.00 fits better than m=1.15** (real 29.5% vs m=1.00's 27.9%, +1.6pp;
  vs m=1.15's 32.0%, −2.6pp — m=1.15 overshoots). Implied multiplier 1.06.
- At ATM, SPY needs m≈1.37 (well above grid) while QQQ needs m≈1.14 (within grid) — the two
  underlyings do NOT share one calibration; QQQ's VXN-to-1y-IV ratio is closer to 1:1 than SPY's
  VIX-to-1y-IV ratio, likely because VXN (30d NDX vol) already sits structurally higher/flatter
  vs its own term structure than VIX does vs SPX's.
- **Base case m=0.85 is too low for both underlyings at every delta tested today** — it
  underestimates real 1y IV by 6–19pp depending on delta/underlying. m=1.00–1.15 is a much
  better base-level fit at ATM/0.50Δ; nothing in the current grid is adequate at 0.70Δ+.

## Results — 2|Short call 0.30Δ/21DTE (SPY)
Expiry 2026-07-31 (T=22d), strike 760, delta 0.292 (≈0.30Δ target), IV 12.5%.

| bid | ask | mid | spread | spread as % of mid |
|---|---|---|---|---|
| $3.86 | $3.90 | $3.88 | $0.04 | **1.03%** |

Backtest assumes 0.5%/side = ~1.0% round trip. Real one-way spread-as-%-of-mid is **1.03%**,
i.e. **roughly matches** the assumption (not materially wider) — SPY is the most liquid single
underlying in the market, so this is close to a best case; the assumption is not obviously
optimistic here, but this single snapshot doesn't cover regime-dependent widening (spreads blow
out in fast markets, which is exactly when the assumption matters most and this spot-check
cannot see).

## Results — 3|IV rank today
| index | now | 252d min | 252d max | percentile rank |
|---|---|---|---|---|
| VIX (SPY) | 16.90 | 13.47 | 31.05 | **46.8%** (mid-range) |
| VXN (QQQ) | 27.86 | 16.73 | 33.54 | **87.7%** (near top of range) |

Per `2026-06-30_regime_and_iv.md`, low IV rank (0–25%) is the best premium-selling zone (91.2%
WR / PF 1.58 for spreads; also best for naked CSP). **SPY is mid-rank (46.8%) — not the best
zone, but not the worst (mid 25–50 was the weakest bucket for spreads in 56/57, though naked CSP
was still positive there).** Selling premium on SPY today is a middling, not compelling, entry
by this lens. **QQQ is near the top of its 252d range (87.7%)** — the 56/57 spread data showed
the very-high bucket (75–100%) still profitable (90.7% WR, small sample) and naked CSP also
positive there, so a QQQ short call/CSP is not disqualified by IV rank, but it's a different
regime (elevated vol, likely downtrend/turbulence per the regime finding that high IV co-moves
with downtrends) — worth flagging that QQQ vol being near a 252d high is itself informative
about current market character, separate from the pricing question.

## Conclusions
1. **Base m for the flagship 0.50Δ LEAP**: m=1.00–1.15 fits today's calm-market chain
   reasonably (within ~1–3pp on both underlyings); m=0.85 is too low everywhere tested.
2. **Skew is real and monotonic**: deep-ITM (0.70–0.80Δ) real IV is 3–14pp above what even
   m=1.15 predicts — a second, independent underestimate of deep-ITM LEAP cost beyond the
   already-flagged crash-vega/term-structure error. Reinforces preferring 0.50Δ over 0.70/0.80Δ
   in the "steady" variant, or requires an explicit skew adjustment if 0.70Δ stays.
3. **Short-call spread cost**: real 1.03% vs assumed ~1.0% round trip — matches, not a hidden
   cost gap, for SPY specifically (most liquid case; not tested for stress conditions).
4. **IV rank today**: SPY mid-rank (46.8%, unremarkable for premium selling), QQQ near top of
   range (87.7%, elevated but not historically disqualifying per 56/57 data).

## Caveats / open risk (explicit boundary)
- **This spot-check validates only TODAY's (calm-market) IV level.** It cannot validate
  crash-time term structure — Yahoo/yfinance exposes only the current chain, not a historical
  implied-vol surface, so there is no free-data way to backtest how m should behave when VIX
  spikes. **The adversarial addendum's core finding (constant-m maps 30d spikes 1:1 into 1y,
  which is wrong in a crash) is CONFIRMED as still-open — this result neither closes nor
  worsens that risk.** It only recalibrates the base (calm-market) level and adds the skew
  finding as a second, distinct source of deep-ITM underestimation.
- Single snapshot, single day — no averaging across recent days/expiries; a follow-up could
  re-pull on a few different days to see how stable the implied-m and skew numbers are.
- q (dividend yield) uses trailing-12m gross yield; does not model potential dividend changes
  over the 1y LEAP life.
