# Rotation challenge — the 7%→155%→327% gap is a frequency mirage, not a missed factor

2026-07-01. `backtest/experiments/exp_rotation_challenge.py`. User's challenge: such a huge gap between
causal (~7%) and oracle (155-327%) must hide a missed KEY FACTOR (even at overfitting risk).
Answered with two tests. Window 2002-2026 (IEF starts 2002), total-return, 5bp/unit turnover.

## (1) Oracle top-3 CAGR COLLAPSES as the holding period grows
| hold | oracle top-3 CAGR |
|---|---|
| weekly | 151.5% |
| monthly | 65.8% |
| quarterly | 38.0% |
| yearly | 23.5% |
| SPY (ref) | 11.2% |

The "missed factor" the user sensed = SWITCHING FREQUENCY itself. The 151% weekly number
evaporates to 23.5% at yearly holding → the huge weekly figure is overwhelmingly a high-frequency
perfect-switching artifact (compounding of perfect noise-timing), NOT a persistent systematic
factor you could design toward. The meaningful "skill ceiling" is perfect ANNUAL sector selection
(~23.5%, ~2× SPY) — real, but see (2): no causal signal captures it.

## (2) Best-documented TAA (dual momentum + bond fallback) still loses on return
| strategy | CAGR | Sharpe | MaxDD |
|---|---|---|---|
| SPY | 11.2% | 0.71 | −54.6% |
| EW 9 sectors | 11.0% | 0.72 | −52.5% |
| DualMom-26 + IEF fallback (monthly) | **7.4%** | 0.57 | **−34.2%** |

Deliberately tried the strongest known candidate factor (Antonacci dual momentum with a Treasury
safe-haven — the "even at overfitting risk" attempt). It LOSES to SPY/EW on return (7.4 vs 11.2)
and only cuts drawdown (−34% vs −55%). Risk control, again.

## Answer to the challenge
No missed CAPTURABLE quant factor. The 7%→155%→327% gap decomposes as:
- most of it = high-frequency perfect-switching (oracle collapses 151%→23% as holding extends);
- the residual real skill ceiling (perfect annual sector selection ~23%) exists but is captured
  by NO causal signal we tested (momentum, dual momentum, valuation all land at/below EW).

The factor the user sensed is real — but it is NOT a quant factor; it is qualitative SELECTION
SKILL (thesis/foresight), and it has more room at the STOCK/THEME level (higher dispersion) than
at the sector level. That is Phase 3, and it is inherently un-backtestable (forward-tracked).

Confirmed positive: rotation DOES have a legitimate role — DEFENSE / drawdown control (the bond
fallback cut MaxDD from −55% to −34%). So in the composition engine: quant = risk/drawdown
control, thesis = return generation.

## Files
New: `backtest/experiments/exp_rotation_challenge.py`. Closes the sector-rotation / composition arc
(oracle ceiling → causal capture → this decomposition). 7 studies now converge: every quant
layer is risk control; the return edge, if any, is qualitative → Phase 3.
