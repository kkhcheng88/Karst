# Result — RSI-2 buy-the-dip: capital efficiency, exit=exposure dial, VIX three-zone

**Date:** 2026-07-05  **Window:** 2016-01-01 → present (standard window going forward)
**Scripts:** `exp_rsi2_universe.py` (entry×exit grid + two-halves), `exp_rsi2_vix_regime.py`
(VIX-regime conditional Sharpe), `exp_rsi2_vix_zones.py` (trade-level, entry-VIX three-zone)
**Tag:** active — mechanism HIGH confidence, magnitudes regime-dependent (not a stable index alpha)

## Question
Re-settle RSI-2 (Connors buy-the-dip) on the recent 10y across instrument types, measured by
CAPITAL EFFICIENCY (not Jensen alpha, which under-states a mostly-flat sleeve). Is the edge
stable (two-halves), and is it driven by the VIX regime?

## Method
Long/flat, entry RSI2<{5,10}, exit RSI2>{70,80,90,95}, look-ahead-safe, 1bp/side (fine for a
limit-order swing trader on liquid names — no slippage assumed), raw close, cash 0 while flat.
Universes: 大盤指數 SPY/QQQ/SPMO · 細價股 IWM/IJR · 11 SPDR 板塊ETF (replaces a hand-picked
large-cap grab-bag — cleaner, no survivorship, is a level Karst uses) · Mag7 single stocks
(idiosyncratic dispersion probe; survivorship-aware). Metrics: **Deployed CAGR** (annualised
return over in-market days only = return on deployed capital), **Cond. Sharpe** (in-market
days), Exposure, Total PnL (idle=0), vs B&H CAGR/MaxDD/Sharpe. Idle-cash return and portfolio
sizing are deferred to the portfolio layer by design.

## Result 1 — capital efficient across the board (deployed return >> B&H)
2016+, entry<10, exit>80 (representative):
| 組別 | 部署回報 | 條件Sharpe | B&H CAGR | B&H Sharpe |
|---|---|---|---|---|
| 大盤指數 | 32% | 1.16 | 17.1% | 0.88 |
| 細價股 | 21% | 0.83 | 10.0% | 0.53 |
| 板塊ETF | 14% | 0.63 | 9.7% | 0.54 |
| Mag7單股 | 46% | 1.09 | 30.9% | 0.88 |
Deployed return and conditional Sharpe beat B&H everywhere; total PnL LAGS B&H (idle cash 70%);
the gap scales with the underlying's up-drift (tiny on small-caps, huge on Mag7). → capital
efficient ≠ beats B&H on wealth; that is the portfolio-layer (idle-cash) question.

## Result 2 — exit threshold = the exposure dial
Loosening exit >70→>95 raises exposure (~20%→~55%) and total wealth toward B&H, but on high-
up-drift assets (index/sectors/Mag7) total PnL is capped BELOW B&H regardless (can't out-hold
the drift with ~half in cash), so tight exit (>70) dominates there (highest deployed return +
Sharpe + lowest DD, same wealth). Small caps are the one place the dial genuinely raises wealth
(>95: total 8.9% > B&H 8.2%, lower DD). Entry<5 vs <10: <5 = deeper dips = higher deployed
return at lower exposure; <10 = more exposure, lower peak. Both entry & exit are efficiency/
exposure dials. Sector dispersion: high-beta cyclicals (XLK/XLF/XLC/XLY) mean-revert best;
defensives (XLU/XLRE/XLP) worst (shallow dips, nothing to catch).

## Result 3 — two-halves (2016-20 vs 2021-26): REGIME-DEPENDENT
Same fixed rule, conditional Sharpe (前/後), exit>70: 大盤 0.53/2.48 · 細價 −0.09/1.37 ·
板塊 0.30/1.18 · Mag7 1.27/1.60. The edge is weak-to-negative in the calm 2016-19 half and
strong in the choppy 2021-26 half — EXCEPT Mag7 (volatile single stocks work in both halves).
Tight settings (entry<5/exit>70) are the MOST regime-fragile; loose settings (entry<10/exit>95)
on liquid indices are the MOST regime-robust (~1.0 both halves) at a lower peak.
**Retraction:** the earlier "small-caps are the sweet spot" was H2-flattered — small caps
LOST money (Sharpe −0.79) buying dips in the calm 2016-20 half.

## Result 4 — VIX three-zone (trade-level, classified by entry-day VIX; RSI2 exit kept)
Pooled trades across all 23 names, avg per-trade return / win% (entry<10):
| 入場VIX | >70 | >80 | >90 | >95 |
|---|---|---|---|---|
| 低VIX <18 | +0.6/68% | +0.8/70% | +1.1/73% | +1.7/75% |
| 中VIX 18-28 | +0.2/65% | +0.2/65% | +0.8/67% | +1.7/70% |
| **極端VIX >28** | +1.0/72% | +2.4/78% | +3.6/81% | **+5.3/88%** |
- Per-trade return RISES with a looser exit in EVERY zone (holding captures more reversion).
- **Extreme VIX (>28, capitulation) + loose exit (>90/95) is the jackpot: +4–5%/trade, ~88%
  win, ~2–3wk hold** — reconciles with the separate VIX>40 → +8.7% fwd-63d capitulation finding.
- Mid VIX (18-28) is the weakest, esp. at tight exit (+0.2%) = the falling-knife/dead-cat zone.
- **Correction:** an earlier daily-conditional-Sharpe read said "high VIX → exit tight". That
  was a risk-adjustment artifact (volatile hold path → low Sharpe); on per-trade P&L + win-rate,
  extreme-VIX dips reward HOLDING (loose exit). VIX is one-sided downside fear: mid-fear bounces
  are unreliable, but extreme capitulation marks the low and rewards the multi-week recovery hold.

## Conclusions (settle)
RSI-2 = a **capital-efficient but regime-dependent mean-reversion TIMER**, not a stable index
alpha. Its P&L is dominated by ENTRY-VIX regime:
- **Best setup: buy the dip when VIX is EXTREME (>28), hold loose (exit >90/95)** → +4–5%/trade,
  ~88% win (capitulation recovery).
- Mid-VIX (18-28) dips = least attractive (falling knife); low-VIX dips = modest but reliable.
- Deployed capital works far harder than B&H (Sharpe & return), but under-exposure means it
  does NOT beat B&H on wealth on high-drift assets — that is the portfolio/sizing layer's job.
- Volatile single stocks (Mag7) are the most regime-robust instrument; calm broad indices in a
  low-vol bull are the weakest.
Mechanism = HIGH confidence (consistent across 23 names, two halves, VIX zones, and an earlier
independent VIX>40 test). Exact magnitudes = regime-dependent, not a stable number.

## Caveats
- Extreme-VIX zone = 112–285 trades but clustered in ~5–8 capitulation episodes (2018/2020/2022/
  2025) → effective independent N is small; direction matches the independent VIX>40 finding, so
  trustworthy in direction, not as hundreds of independent samples.
- 1bp/side + no slippage (justified: limit-order swing on liquid names, but fill-risk on sharp
  exits is unmodelled). Raw close (B&H understated by dividends). Idle cash 0 (understates total
  return — but total return is the portfolio-layer question, deferred by design).
- In-sample params are STANDARD Connors values (not data-mined) → low overfitting; the two-halves
  + VIX-zone splits ARE the out-of-sample robustness evidence.

## Implication for Karst
Use RSI-2 as a **regime-conditional entry timer**, not an always-on index sleeve:
- Deploy idle cash into **VIX-capitulation dips (VIX>28), hold for the recovery** — the strongest,
  most durable slice.
- On individual (volatile) names it is the most robust; on calm broad indices in low-vol bulls it
  adds little. Keep it a SEPARATE timing field from the structural score (design already does this).

## Result 5 — DECISION MATRIX (category × VIX zone, `exp_rsi2_decision_matrix.py`)
Per-trade return rises monotonically with a looser exit in every cell, so the decision is NOT
mainly the exit — it is WHERE to deploy and how big. Per-trade return @ exit>95 / win% (entry<10):
| 股種 \ VIX | 低VIX <18 | 中VIX 18-28 | 極端VIX >28 |
|---|---|---|---|
| 大盤指數 | +1.5% / 83% | +1.6% / 70% | +4.5% / 100% |
| 細價股 | +0.8% / 69% | +1.6% / 75% | **+8.6% / 93%** |
| 板塊ETF | +1.0% / 71% | +1.4% / 68% | +4.7% / 85% |
| Mag7 | +3.1% / 77% | +2.5% / 71% | +5.1% / 82% |

Rules:
1. **Extreme VIX (capitulation) = jackpot for every category** (loose exit >90/95); small-caps
   spike hardest (+8.6%, 93% win) but the zone is rare.
2. **Mag7 is the only category with juice even in low VIX** (+3.1%) → the all-weather instrument.
3. **Mid VIX (18-28) = the weakest, falling-knife zone** (tight-exit per-trade ≈ 0) → trade small
   or only the strong names; if trading, hold to >95.
4. **Small caps: trade ONLY in the extreme zone**; low/mid VIX has no edge (mid-VIX >70 = −0.2%).
5. **Exit choice depends on capital use:** single instrument (idle cash between dips) → LOOSE exit
   (>90/95) to max each trade; diversified/redeploy-able book → TIGHT exit (>70-80) in low VIX is
   more time-efficient (eff 15-60%/yr), save the loose hold for high VIX.

Efficiency (per-trade ÷ hold × 252): low VIX → tight >70 best; extreme VIX → >80-90 huge (大盤
107% / 細價 146% / Mag7 101% /yr); mid VIX lowest (14-25%). Caveat: extreme-zone cells are 14-98
trades clustered in ~5-8 capitulation episodes — direction robust, exact magnitude not precise;
the efficiency metric assumes redeployment (overstates tight-exit for a single instrument).
