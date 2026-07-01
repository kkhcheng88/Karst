# Reward vs ranking skill — the user was right; retract "mirage". The game = find IC ≥ 0.05

2026-07-01. `exp_weekly_trigger.py` + `exp_skill_curve.py`. The user challenged the "oracle
collapse = frequency mirage" dismissal (it's circular — of course more frequent perfect
decisions compound higher) with the real point: because dispersion is enormous, you don't need
to pick THE best — 2nd/3rd best is still huge — so the question is whether we can rank even
slightly better than random. Correct. I retract "mirage."

## (A) Payoff by exact rank (perfect foresight of the k-th best sector each week)
| rank | CAGR |
|---|---|
| 1 (best) | 327% |
| 2 | 141% |
| 3 | 76% |
| 4 | 37% |
| 5 (median) | 8.7% ≈ SPY |
| 6–9 | negative → −73% |

2nd best = 16× SPY, 3rd = 9×. You do NOT need #1 — just to sit systematically in the top few.

## (B) Reward vs ranking skill (IC) — steeply convex
Degrade the perfect ranking with noise to a target IC, pick top-3, net of 5bp/unit turnover:
| target IC | realized IC | CAGR net |
|---|---|---|
| 0.00 | 0.00 | 5.5% |
| 0.02 | 0.02 | 7.3% |
| **0.05** | 0.05 | **10.3% (beats SPY)** |
| **0.10** | 0.10 | **15.6% (~2× SPY)** |
| 0.20 | 0.21 | 27% |
| 0.30 | 0.31 | 39% |
| 1.00 | 1.00 | 155% (oracle) |

IC 0.05 (almost nothing) already beats SPY net; IC 0.10 doubles it. The reward for ranking skill
is huge and convex — the user's point, confirmed.

## (Trigger IC) — the measured skill of quant features is ~0
`exp_weekly_trigger.py` cross-sectional IC vs next-week sector return: REV-1w 0.013 (t 1.1),
REV-4w 0.009, MOM-26w 0.005, RSI2 −0.001, LOW-VOL −0.009. All ~0, none significant. A causal
reversal rotation is 11.3% gross but 7.6% net (turnover 68/yr eats it).

## The reframe (replaces "quant = risk, thesis = return")
The problem is NOT "no reward" — reward is enormous. It's that every quant feature tested ranks
next-week sectors with ~0 IC. So the whole game becomes a single falsifiable question:

  **Is there ANY signal (quant or qualitative) that ranks sectors/themes with forward IC ≥ ~0.05?**

- Quant features: measured IC ~0 → fail.
- Untested candidate: qualitative info (news / catalysts / fundamentals / bottleneck) that quant
  features miss. This is Phase 3 — and it now has a MEASURABLE success bar: does thesis-driven
  ranking achieve forward IC ≥ ~0.05? Forward-trackable, falsifiable.

## Honest temper (don't overswing)
IC 0.05–0.10 is a HARD bar — pro quants get 0.02–0.05 with vast breadth + infrastructure; a lone
operator ranking 9 sectors weekly at IC 0.1 is ambitious. We have ZERO evidence any accessible
signal clears 0.05. But the convex payoff justifies the hunt, qualitative info is the one untested
edge, and lower frequency (monthly) lets a modest IC survive costs better. Net: the arc's
conclusion isn't "quant is useless" — it's "the entire edge reduces to finding a ranking signal
with forward IC ≥ ~0.05, and that's the falsifiable target Phase 3 must hit."

## Factor sweep — the "just map all factors (Qlib) + SVD" idea, done with discipline
`exp_factor_sweep.py`. Instead of hand-testing 4 factors, swept 28 across the Alpha158 families
(momentum 1-52w, reversal, MA-ratio, volatility, RSI, range-position, volume, skew/kurt, 52w-high
distance), vectorized, forward IC vs next-week sector return, with Bonferroni correction (the
narrow 9-sector cross-section DEMANDS it).
```
survive Bonferroni (|t|>3.12): 0/28
strongest: mom52 (12m momentum) IC 0.033, t 2.7  -- only |t|>2, fails correction, and < 0.05 bar
composite (mean-z of 28): IC 0.004 (t 0.4)   -- combining ~0-IC factors stays ~0
1st PC (SVD):            IC -0.002 (t -0.2)   -- SVD finds variance, NOT prediction
```
Confirms the three caveats: (1) narrow cross-section makes real factors HARDER to find, spurious
ones easier — 0 survive; (2) Qlib's factors are all price/volume, the same source at IC~0 — more
of them = more overfit chances, no new information; (3) SVD is the wrong tool for discovery (PC1
IC ~0; variance ≠ prediction). Only flicker: 12-month momentum (the most robust academic factor),
but sub-threshold, sub-0.05, and uncapturable net of cost at this breadth.

## Definitive close of the quant door
Price/volume factors have forward IC ~0 on weekly sectors, no matter how many or how combined.
The missing ingredient is a NEW INFORMATION SOURCE, not more factor engineering. Combined with
the reward-vs-skill curve (IC 0.05 beats SPY, 0.10 doubles it), the whole system reduces to one
falsifiable target: find a signal with forward IC ≥ ~0.05. The only untested source is qualitative
(news/catalysts/fundamentals/bottleneck) = Phase 3 — now with a measurable, forward-trackable bar.

## Files
New: `backtest/exp_weekly_trigger.py` (cross-sectional IC of candidate factors + causal reversal),
`backtest/exp_skill_curve.py` (payoff-by-rank + reward-vs-skill curve),
`backtest/exp_factor_sweep.py` (28-factor Alpha158-style sweep + Bonferroni + composite/SVD).
