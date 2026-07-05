# Result — F&G CROSS-SECTIONAL (Baker-Wurgler): the dimension we missed

**Date:** 2026-07-05  **Script:** `exp_fg_crosssectional.py`  **Tag:** active ✅ — a NEW edge;
found only by cross-checking the literature (Baker-Wurgler) after the market-level F&G test.

## Question
`2026-07-05_fg_vs_vix.md` tested F&G only at MARKET level (SPY fwd). Baker-Wurgler (2006/2007):
sentiment hits HARD-TO-ARBITRAGE stocks (small / young / high-vol / speculative) hardest — high
sentiment → they underperform; low → they outperform. Does F&G predict the speculative-minus-safe
SPREAD in our data? If yes, F&G is a far sharper DE-RISK signal for the speculative sleeve.

## Method
ETF proxies for spec-vs-safe: size = IWM−SPY (small−large); speculation = SPHB−SPLV (S&P High
Beta − Low Vol). CNN F&G (github whit3rabbit), F&G overlap 2011+. Forward 21/63d spread, by F&G zone.

## Result 1 — F&G → forward speculative spread (spec − safe), mean% / t
| spread | 恐懼<25 | 中25-75 | 貪婪>75 | 極端>80 |
|---|---|---|---|---|
| **IWM−SPY (small−large) 63d** | +0.4 / +2.1 | −0.5 / −5.6 | **−1.8 / −6.7** | **−2.7 / −7.0** |
| **SPHB−SPLV (highβ−lowvol) 63d** | **+3.8 / +7.3** | +1.8 / +9.0 | −0.1 / −0.2 | −1.3 / −1.9 |
(21d same direction, weaker.) MONOTONIC and highly significant: high F&G → small/speculative
underperform; low F&G → they outperform strongly. Textbook Baker-Wurgler.

## Result 2 — F&G>80 forward 63d: market vs speculative vs safe
| | F&G>80 | baseline |
|---|---|---|
| SPY (market) | +0.8% | +2.4% |
| QQQ | +3.6% | +3.1% |
| **SPHB (high-beta / speculative)** | **−1.8%** | +3.8% |
| **IWM (small)** | **−2.2%** | +2.2% |
| SPLV (low-vol / safe) | −0.3% | +2.0% |
Market-level F&G>80 is only a mild "reward exhausted" (+0.8%), but SPECULATIVE / SMALL crater
(−1.8% / −2.2%). **F&G de-risk is far sharper for the speculative sleeve than for the market** —
exactly the cross-sectional dimension the market-level test missed.

## Conclusions
**F&G's real power is CROSS-SECTIONAL (Baker-Wurgler), confirmed strongly here:**
- **High F&G (>75-80) → CUT speculative / small-cap / high-beta** (they underperform −1.8 to −2.7%).
- **Low F&G (<25) → ADD speculative / high-beta** — a strong contrarian BUY (+3.8% at 63d, t7.3),
  complementing the VIX-capitulation entry.
- The market-level greed→de-risk (`fg_vs_vix.md`) is the weak shadow of this; the sharp signal is
  the spec-vs-safe TILT.

## Confidence
- Cross-sectional F&G effect = **HIGH direction** (monotonic across zones, t up to ±7, literature-
  backed by Baker-Wurgler + Schmeling). Caveat: overlapping 63d windows inflate t; ETF proxies
  (SPHB/SPLV from 2011); magnitude ≈ a few % per quarter, not a standalone system.

## Implication for Karst
Wire F&G as a **speculative-sleeve exposure modulator**, not just a market flag: F&G high → trim
small-cap / high-beta / speculative tier-2 names; F&G low → add them (contrarian). This is a
cross-sectional TILT, distinct from and sharper than the market-level de-risk. Was missed by
testing only market-level — found via the literature cross-check + the all-categories rule
([[backtest-testing-standard]]).

## ⚠️ RETRACTION (2026-07-05, same day) — proper strategy test REVERSES this — `exp_fg_spec_strategy.py`
The above used ETF proxies (SPHB/SPLV/IWM) in an EVENT STUDY (forward spread by F&G zone), not a
strategy with the capital-efficiency measure. Redone with a BETTER proxy (spec/safe baskets from
INDIVIDUAL stocks sorted on size × vol, 2011–2026) and a REAL F&G-timed strategy:
- **Individual-stock SPEC−SAFE spread REVERSES sign vs the ETFs:** 恐懼<25 **−1.35%**, 貪婪>75
  **+2.44%** (opposite of the ETF result AND of Baker-Wurgler). The individual small+high-vol
  basket behaves like BETA-MOMENTUM (fear→keeps falling, greed→keeps rising), not B-W contrarian.
- **F&G-timed SPEC sleeve HURTS:** hold-spec-when-F&G<X gives deployed CAGR 7–9% / conditional
  Sharpe 0.39–0.47 — WORSE than B&H SPEC (CAGR 11.8% / Sharpe 0.56) at every threshold. Timing the
  speculative sleeve with F&G is capital-INefficient (it exits spec exactly when spec then rises).
**Verdict: the cross-sectional F&G-spec claim is PROXY-DEPENDENT and NOT confirmed; NO deployable
edge.** The two proxies give opposite signs → unproven. My "strongly confirms Baker-Wurgler" was an
over-claim from an ETF event study; the proper (individual-stock + strategy + capital-efficiency)
test does not support it. Only the MARKET-LEVEL greed reward-exhaustion (`fg_vs_vix.md`, F&G>80 →
mild) survives. Caveats on the reversing test: survivorship + insider-biased universe + monthly +
return-clip — so it is not a clean refutation either; net = **the effect is not robustly established
in EITHER direction, and is not deployable.** (Lesson: the new all-categories/real-strategy/
capital-efficiency standard [[backtest-testing-standard]] caught this over-claim on its first use.)
