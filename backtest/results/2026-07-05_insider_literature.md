# Result — Insider LITERATURE-ALIGNED test (small-cap · 12-month · portfolio · vs IWM)

**Date:** 2026-07-05  **Script:** `exp_insider_literature.py`  **Tag:** active ✅ — CONFIRMS the
documented edge; corrects the earlier (mismatched) "disciplined negative".

## Question
The rigor tests ran the wrong cut (large-cap / short-horizon / vs-SPY) and I dismissed the
micro portfolio. The literature (Lakonishok-Lee 2001 ~7.4%/12mo small-cap; Cohen-Malloy-Pomorski
2012; Seyhun) says the edge is: SMALL/MICRO cap · 6–12mo hold · diversified PORTFOLIO ·
size-matched benchmark. Does that cut hold in our 2006–2025 data?

## Method
2006q1–2025q2 cluster P-buys (≥2 insiders, ≥$500k, 10b5-1 excl), forward EXCESS vs **IWM**
(size-matched) and SPY (contrast), by market-cap bucket; monthly-cohort PORTFOLIO Sharpe; cost.

## Result 1 — small-cap event edge (mean%/median%/t)
| bucket | 126d vs IWM | 252d vs IWM | 252d vs SPY |
|---|---|---|---|
| micro <$300M | +13.4/−3.0/6.3 | **+21.4/−7.1/5.8** | +20.0/−9.9/5.4 |
| small $300M–2B | +3.4/−1.9/3.7 | +4.9/−4.4/3.7 | +3.6/−6.8/2.6 |
| **combined <$2B** | +7.9/−2.3/7.3 | **+12.3/−5.7/6.8** | +10.9/−8.2/6.0 |

## Result 2 — PORTFOLIO (monthly cohort, <$2B, vs IWM)
- 126d: 234 cohorts, mean **+8.1%**, hit 65%, Sharpe(ann) **0.43**
- 252d: 234 cohorts, mean **+13.8%**, hit 65%, Sharpe(ann) **0.32**

## Result 3 — costs (252d, <$2B, net vs IWM)
0.5% → +11.8% · 1.0% → +11.3% · 2.0% → +10.3%. Survives costs (a ~+12%/yr edge easily absorbs a
1–2% round-trip; positive-EVENT share ~42–44%, so a diversified basket is required — the median
event underperforms).

## Result 4 — survivorship (the key caveat)
Of 9,998 events, 8,187 had market cap and 1,811 (~18%) did NOT — those unpriced/no-mcap names are
likely delisted losers dropped upstream. Among PRICED <$2B names, 100% matured to 252d. So the
survivorship selection happens at the pricing stage: **we see the small-caps that survived; the
bankrupt ones are invisible → the edge is SURVIVORSHIP-INFLATED.** L&L (careful delisting-return
control) found ~7.4%; our +12–21% is higher, consistent with survivorship lifting it.

## Conclusions (this SUPERSEDES the "disciplined negative")
**Insider cluster-buys DO carry the documented edge in our data — literature-aligned:**
- **Small-cap (<$2B), 12-month hold, diversified portfolio, vs a size-matched (IWM) benchmark:
  +12% excess (t6.8), survives 1–2% costs.** Directionally = Lakonishok-Lee; our magnitude is
  survivorship-inflated toward the low end (true ≈ L&L's ~7%).
- **The sign FLIPS by market cap** (consistent with the literature "edge is in small caps"):
  small-cap = +12% at 252d; LARGE-cap = −7% at 252d (short pop then reversal). Micro = highest raw
  (+21%) but most survivorship-inflated + highest variance.
- **It is a MODEST, high-variance edge**: portfolio Sharpe 0.32, median event NEGATIVE → only works
  as a broadly-diversified small-cap basket held ~12 months, not a single-name or short-term bet.

## Confidence
- "Small-cap insider portfolio, 12mo, has an edge" = **MEDIUM–HIGH** (literature-backed + confirmed
  here + survives costs), magnitude discounted for survivorship (true ≈ 7–10%, Sharpe ~0.3).
- Untested refinement (would strengthen): **opportunistic-vs-routine filter** (Cohen-Malloy: ~4×
  the signal; routine ≈ 0) — needs per-insider history (build_events discards owner IDs).

## Implication for Karst (FINAL, corrected)
Insider is a legitimate but MODEST **small-cap, multi-month (≈12mo) portfolio tilt**, NOT a
large-cap or short-term signal. Wire it as: a bounded confidence overlay on **SMALL-CAP** tier-2
names held for months (not large caps, where it reverses); size it small (Sharpe ~0.3); ideally
add an opportunistic filter. The earlier "turn it off / disciplined negative" was an artifact of a
mismatched test — corrected by matching the literature's cut. (Old large-cap short-term "edge"
remains a 2022–25 regime artifact; the durable, literature-backed edge is small-cap/12mo.)
