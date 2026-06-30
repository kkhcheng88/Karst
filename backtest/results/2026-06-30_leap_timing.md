# Result — Does a deep-ITM LEAP need timing? (PROVISIONAL — magnitudes not bankable)

**Date:** 2026-06-30  **Script:** `backtest/exp_leap_timing.py`  **Tag:** 🟡 provisional

## Question
RSI-2 showed underlying TA timing = drawdown control, not alpha — and on SHARES that
trade-off isn't worth it. Hypothesis: for a LEVERAGED, finite-life LEAP, drawdown
control is essential (a deep drop is ~terminal on leverage; you can't just hold).
So the 200SMA right-side gate that HURT the share strategy should HELP the LEAP.

## Method
Continuously-held deep-ITM (0.80Δ) long call, BSM-priced daily with VIX/VXN as IV,
roll at ~63 trading days, fractional contracts (capital-normalized NAV), r=3%,
q=1.3%/0.6%, cost 7bps/side. always-in vs gated (hold only when price>SMA200) vs B&H.

## Results

| Underlying | Variant | CAGR | Sharpe | MaxDD | x |
|---|---|---|---|---|---|
| SPY | LEAP always | 13.65% | 0.53 | **−99.9%** | 44 |
| SPY | **LEAP 200SMA-gated** | **34.0%** | **0.88** | −70.1% | 5763 |
| SPY | B&H shares | 8.17% | 0.50 | −56.5% | 10 |
| QQQ | LEAP always | 20.70% | 0.64 | **−99.3%** | 102 |
| QQQ | **LEAP 200SMA-gated** | **44.7%** | **0.98** | −69.0% | 8782 |
| QQQ | B&H shares | 12.66% | 0.64 | −53.6% | 19 |

## Conclusion (qualitative — robust)
✅ **The 200SMA right-side gate that HURT the share strategy dramatically HELPS the
LEAP** — ~2× CAGR, higher Sharpe, and MaxDD from −99.9% (ruin) to −70%. Always-in
leveraged LEAP = ruin (wiped out in 2002/2008/2020). **Leveraged, finite-life
positions need the right-side regime gate as ruin-avoidance.** (= INV-6, confirmed.)

## Why the MAGNITUDES are NOT bankable
1. VIX (30-day IV) used to price 1-year options — crude, biases vega.
2. 7 bps cost is far too low for rolling LEAPs (real ~0.5–2%/round-trip); the gate
   whipsaws around SMA200 → real costs would gut returns.
3. Single favorable US-bull path; no capacity / financing / assignment / liquidity.
4. Same-bar gate execution (mild look-ahead vs the next-bar RSI experiment).

## The real story
Even GATED, MaxDD ≈ −70%. "Timing helps" ≠ "safe". A leveraged LEAP is near-unhostable
through its drawdowns — **size small**.

## Next (to make it bankable)
Realistic LEAP costs (0.5–1%/round-trip), next-bar gate execution, IV term-structure
haircut (use ~0.8×VIX for 1yr tenor), and multi-path / parameter robustness.
