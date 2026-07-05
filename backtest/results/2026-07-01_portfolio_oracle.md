# Weekly sector-rotation CEILING (oracle) — huge, but a noise mirage

2026-07-01. `backtest/experiments/exp_portfolio_oracle.py`. Corrects the single-asset framing error (a
signal need not beat B&H-this-asset; the question is COMPOSITION — where a finite pool goes).
Bounds the opportunity with a perfect-foresight oracle: each week allocate by that week's
realized sector returns. Gap(oracle − SPY) = the MOST weekly sector rotation could add.
9 core SPDR sectors, total-return, weekly, 1999–2026, cost 5bp/unit turnover.

## Result
| strategy | CAGR | Sharpe | MaxDD | CAGR_net |
|---|---|---|---|---|
| SPY (do nothing) | 8.6% | 0.56 | −54.6% | — |
| EW 9 sectors | 9.2% | 0.60 | −52.5% | 9.2% |
| ORACLE top-1 | 327% | 6.74 | −18.5% | **309%** |
| ORACLE top-3 | 164% | 5.35 | −22% | **155%** |
| ORACLE top-3 +cash | 205% | 7.29 | **0%** | **196%** |
| WORST top-1 (floor) | −73% | — | −100% | −74% |

## Interpretation — high ceiling ≠ capturable edge
- The ceiling is astronomical (net +301 / +146 / +187 pp/yr vs SPY). Weekly sector DISPERSION
  is enormous (best +327% vs worst −73%). The user's intuition — composition has far more room
  than single-asset timing — is right about the dispersion.
- BUT a huge WEEKLY oracle ceiling is EXPECTED and is mostly a NOISE MIRAGE: the more often you
  rebalance, the higher the oracle (you exploit more noise). "Next week's best sector" is largely
  random. High ceiling is NOT evidence of a reachable edge — it's the value of perfect
  noise-trading.
- The truly informative number: the NO-SKILL baseline (EW 9.2%) barely beats SPY (8.6%) → the
  FREE composition premium (diversification/rebalance) is only ~+0.6pp/yr. Everything above that
  requires PREDICTIVE SKILL on weekly sector returns — and our evidence for that is thin (RS mild
  persistence, valuation = sector-dependent tilt, RSI-2 = risk-control).
- Decomposition: top-3+cash (196%) − top-3 (155%) ≈ +40pp from perfect cash-timing; the rest is
  sector selection. So selection >> timing (~4:1), both uncapturable at this level.

## Honest reframe (balances the earlier concession)
- Right: composition is the correct frame; dispersion is real and large — not "single-asset has
  no alpha so there's nothing."
- But: the free composition premium is tiny (EW vs SPY +0.6pp); the rest needs weekly predictive
  skill, which is the hard part. A high oracle ceiling does NOT mean rotation is where the edge is.
- The decisive test is NOT the ceiling — it's where a CAUSAL rotation (RS momentum + valuation
  tilt + trend gate, no foresight) lands between EW (9.2%) and the oracle. Prior: near EW, maybe
  a modest beat, NOT near the ceiling.

## Next
Build the causal weekly rotation (real signals, look-ahead-safe) and measure its net-of-cost,
through-regime result vs SPY / EW — the actual test of "does composition beat buy-and-hold".

## Files
New: `backtest/experiments/exp_portfolio_oracle.py`.
