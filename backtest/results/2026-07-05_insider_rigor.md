# Result — Insider 21d edge: rigor (is it a penny/small-cap/tail illusion?)

**Date:** 2026-07-05  **Scripts:** `exp_insider_validate.py` (full-universe reproduction),
`exp_insider_rigor.py` (buckets/trim/cost/weight)  **Tag:** active — the audit's #1 "fragile"
finding, now properly characterized. Reproduces, but the headline strength is NOT tradeable.

## Question
The full-universe insider 21d event-study (mean +2.01%, t 5.12) beat the large-cap subset
(t 2.3). Audit flag: is the strength a small-cap / illiquidity / tail-driven illusion? (Also:
the original t≈5.12 was unreproducible on a dead price cache — now refilled.)

## Method
SEC bulk Form 345, 2022q1–2025q2. Cluster open-market P-buys (≥2 insiders, ≥$500k, 10b5-1
excluded), entry = filing date, forward EXCESS vs SPY. Prices via defeatbeta (delisted retained).
Rigor: split the SAME 21d events by price level, realized vol, trimmed mean, cost, weighting.

## Result 0 — reproduction (audit #1 resolved)
Full universe now reproduces: 21d n=2867 mean **+2.01% t=5.12**; 63d +0.66% t=0.95; 126d
−1.54% t=−1.45 (edge is 21d-only, negative by 126d). Cache refilled, path bug fixed → the
previously "unreproducible" number is confirmed. BUT (below) it is not a tradeable edge.

## Result 1 — the strength is concentrated in PENNY stocks (2726 events, +2.36% t5.84)
| price bucket | n | mean% | median% | t |
|---|---|---|---|---|
| **<$5 (penny)** | 506 | **+8.01** | +2.76 | 5.31 |
| $5–20 | 1160 | +1.09 | −0.41 | 2.29 |
| >$20 | 1060 | +1.07 | +0.27 | 2.02 |
The +2.36% aggregate is carried by the <$5 bucket (+8%). Tradeable (>$5) names: only **+1.1%,
t≈2.0–2.3** — matching the large-cap subset the audit flagged.

## Result 2 — no edge in low-vol (large/stable) names; it's the wild names
Realized-vol terciles: 低 +0.22% (t 0.69, ≈0) · 中 +3.12% (t 4.78) · 高 +3.75% (t 3.87).
Liquid, low-vol large caps show NO insider edge.

## Result 3 — tail-driven (a few penny rockets)
Trimmed mean: raw +2.36% → trim 5% **+1.03%** → trim 10% +0.74%. Median +0.14%, hit 51%
(coin-flip on direction). Most events barely move; the mean is a handful of huge winners.

## Result 4 — costs
Flat costs survivable (0.3→1.0% → net +2.06→+1.36%), but a price-scaled spread (penny names
wide) cuts it to **+1.11%**, and real penny spreads are wider still. Positive-event share ≈47–51%.

## Result 5 — weighting
1/vol-weight (down-weight wild names) cuts +2.36% → **+1.38%**. (Price-weight returned a
nonsensical −32% — a broken aggregation, price is not a valid return weight; ignore. The
price-BUCKET split is the clean version.)

## Result 6 — by MARKET CAP (price was misleading) — `exp_insider_mktcap.py`
Price is a poor size proxy (a $3 stock can be large, a $500 stock small). Using defeatbeta
point-in-time market cap (daily close × latest quarterly shares), 2499 events:
| market-cap bucket | n | mean% | median% | hit | t |
|---|---|---|---|---|---|
| micro <$300M | 844 | +4.05 | +0.56 | 51% | 4.03 |
| small $300M–2B | 906 | +1.44 | −0.65 | 48% | 2.47 |
| mid $2B–10B | 514 | +0.70 | +0.14 | 51% | 1.18 |
| **large >$10B** | 235 | **+2.07** | **+1.86** | **56%** | 2.44 |
**U-shape, and the large-cap edge is the CLEAN one:** >$10B shows +2.07% with a POSITIVE
median (+1.86%) and 56% hit — i.e. the *typical* large-cap insider buy rises, NOT a few tail
rockets (contrast micro's +4% mean / +0.56% median = tail-driven). The price test HID this:
price>$20 (+1.07%) was diluted by high-priced small companies; <$5 names have a median mcap of
$134M (true micro, so price≈mcap at the bottom but diverges at the top). **The user's call to
use market cap changed the conclusion — the tradeable edge lives in LARGE caps, not the penny
names.** (Mild tension with the vol split — low-vol showed ≈0 — suggests the large-cap edge may
sit in the higher-vol large-growth names, not stable utilities.)

## Conclusions (settle, REVISED by market cap)
**Insider cluster-buy 21d edge has a deployable slice — in LARGE caps.** micro <$300M = +4% but
tail-driven & untradeable (penny/illiquid); mid $2–10B = ≈0 (t1.18); **large >$10B = +2.07%,
median +1.86%, hit 56%, t2.44 — clean and tradeable.** The full-universe t=5.12 headline is a
micro-cap tail effect; the real, usable edge is the modest-but-clean large-cap one. 21d-only
(negative by 126d), short 2022–2025 sample (one regime), equal-weight, costless-baseline, not
point-in-time-survivorship-cleaned.

## Confidence
- "Insider buys → a strong universe-wide edge" = **NO** — the headline strength is untradeable
  micro-cap tail winners.
- **"Large-cap (>$10B) insider buys carry a clean, tradeable +2% 21d edge" = MEDIUM–HIGH**
  (positive median, 56% hit; but n=235, one regime, costless, no DSR).

## Result 7 — full horizon profile (5d → 252d) × market cap — `exp_insider_horizons.py`
mean%/median%/t (excess vs SPY):
| horizon | all | micro<$300M | large>$10B |
|---|---|---|---|
| 5d | +3.10/+1.3/11.1 | +5.29/+2.0/7.6 | +1.49/+1.4/4.0 |
| 10d | +3.02/+1.0/9.1 | +5.14/+1.6/6.3 | +1.85/+0.7/3.2 |
| 21d | +2.01/−0.1/5.1 | +4.05/+0.6/4.0 | +2.07/+1.9/2.4 |
| 42d | +0.75/−2.0/1.4 | +3.57/−2.1/2.6 | **+2.97/+1.2/2.3** |
| 63d | +0.66/−3.1/0.9 | +4.49/−4.2/2.5 | +1.83/+0.0/1.5 |
| 126d | −1.54/−8.9/−1.4 | +4.57/−11.9/1.6 | −1.89/−3.9/−1.2 |
| 189d | −1.81/−12.8/−1.1 | +6.89/−17.0/1.4 | −2.93/−4.4/−1.4 |
| 252d | **−5.03/−18.1/−2.1** | +2.96/−23.7/0.4 | **−7.16/−7.4/−3.2** |
Findings: (1) **edge is STRONGEST at the shortest TF (5–10d, +3%, t≈9–11)**, decaying
monotonically — 21d is already past peak. (2) **It is a short-term POP that REVERSES** — all
buckets turn negative by 126–252d (all −5%, t−2.1). Refutes the "insiders know long-term value"
thesis for this signal. (3) **Large-cap = clean (mean≈median) and tradeable +1.5–3% over 5–42d,
then −7% by 252d (t−3.2); micro = pure lottery** (mean tail-carried +3–7% while MEDIAN craters
to −23.7% at 252d — most micro names lose ~24%/yr, a few moonshot).

## Implication for Karst (REVISED again by the horizon profile)
**Insider is a SHORT-TERM (5–42d) entry-timing signal on LARGE caps — NOT a multi-month
confidence overlay.** Critically, insider-buy names UNDERPERFORM over the tier-2 holding horizon
(126–252d: large −7%, t−3.2), so a positive ±30% confidence overlay HELD for months is
WRONG-SIGNED against its own holding period. Correct wiring:
- **large-cap (>$10B) cluster-buy → a short (≤~1 month) ENTRY-TIMING nudge, exit within weeks**;
- **never a long-held size/confidence multiplier** (it reverses hard); **micro/mid caps OFF**
  (lottery / no edge).
Supersedes the current ±30% held-overlay design. To reach "high": point-in-time universe, real
costs, DSR, multi-regime sample.

## Result 8 — EXTENDED to 2006 (multi-regime) — KILLS the large-cap edge — `exp_insider_extended.py`
SEC bulk 2006q1+ (verified), defeatbeta prices+mcap to 1994. 18,751 cluster events / 6,766
tickers; 9,997 priced. Full-sample horizon (mean%/median%/t):
| hor | all | micro | large>$10B |
|---|---|---|---|
| 5d | +2.08/+0.8/16.4 | +3.96/+1.2/12.1 | +0.48/+0.5/**2.4** |
| 21d | +2.10/+0.3/10.6 | +4.21/+0.7/8.1 | **+0.40/−0.1/1.1** |
| 126d | +3.44/−3.7/5.1 | +12.54/−4.8/5.9 | −1.71/−1.3/−2.1 |
| 252d | +4.73/−8.4/4.3 | +19.98/−9.9/5.4 | −3.76/−4.3/−3.2 |
Large-cap 21d collapses from +2.07% (2022–25) to **+0.40%, t=1.1 (INSIGNIFICANT)** over 20y,
and is negative long-term. Large-cap 21d edge BY YEAR: strong ONLY in 2009 (+2.9), 2022 (+1.7),
2024 (+3.5), 2025 (+3.5); **weak/zero/NEGATIVE across 2006–2021 including the crises (2008 GFC
−1.1, 2018, 2020 −0.3).** The aggregate strong t is the micro-cap lottery tail (252d mean +20%
while median −9.9%). **The deployable large-cap edge is NOT regime-robust — it is a 2022–2025
(+2009 recovery) phenomenon with no pre-2022 track record.**

## Conclusions (FINAL — disciplined negative)
**Insider cluster-buys have NO robust, deployable edge.** Layer by layer: the headline t=5.12 is
a micro-cap **lottery tail** (median negative, untradeable); the "clean large-cap edge" is
**2022–25-specific** (full-sample 21d +0.40%, t=1.1 insignificant); and **every bucket reverses
long-term** (large −3.8% at 252d, t−3.2). Recent 4 years worked in large caps, but with no
pre-2022 track record across 15 years and multiple crises, it cannot be trusted as durable.

## Confidence (final)
- "Insider buys → a deployable edge" = **NO (low)** — micro is a lottery; large-cap is
  2022–25-specific & insignificant over 20y; all buckets reverse long-term.
- "Insider does NOT durably predict outperformance / reverses long-term" = **HIGH** (20 years,
  multi-regime, across market cap).

## Implication for Karst (FINAL)
**Turn the insider ±30% overlay OFF (or ≤±5% explicitly flagged "2022–25-contingent, no long-run
track record").** It is not "apply to large caps" — that was a recent-regime artifact the
multi-regime test refuted. Insider joins the disciplined-negative pile (like the rotation/ML
factor arc): a plausible signal that does not survive proper testing (market cap + horizon +
multi-regime). The only robustly-true insider fact is the LONG-TERM REVERSAL (don't hold
insider-buy names for months).

## ⚠️ CORRECTION (2026-07-05, after literature review — the "disciplined negative" was too strong)
User invoked the academic literature (Lakonishok-Lee 2001; Cohen-Malloy-Pomorski 2012; Seyhun;
Jeng-Metrick-Zeckhauser), which robustly documents an insider-BUY edge: **~7.4% abnormal / 12
MONTHS, concentrated in SMALL/MICRO caps, as a diversified PORTFOLIO, amplified by cluster /
C-suite / OPPORTUNISTIC (non-routine) trades; routine trades ≈ 0.** Reconciling, **this test
was mismatched to how the edge actually works, and I dismissed the right cut:**
1. **The literature edge is in SMALL/MICRO caps, NOT large.** Our "large-cap no edge" is
   CONSISTENT with the literature (large-cap markets efficient) — not a refutation of insider.
2. **The edge is a 12-MONTH PORTFOLIO.** Our own micro-cap 252d **mean was +19.98% vs SPY
   (t=5.4)** — I dismissed it as "lottery" on the negative median, but an equal-weight portfolio
   captures exactly that mean (which is what L&L measure). Our data actually HINTS at the
   small-cap portfolio edge; the dismissal was wrong.
3. **Wrong benchmark:** excess-vs-SPY penalises small caps (L&L stressed size-matched
   benchmarking); should be vs IWM/IJR.
4. **No opportunistic-vs-routine filter** (Cohen-Malloy's key refinement — routine dilutes to 0).
**Revised status: insider is NOT settled as a negative.** The short-horizon (5-21d) / large-cap /
vs-SPY cuts we ran show no edge (consistent with the literature), but the LITERATURE-ALIGNED cut
(small-cap, 12-month, portfolio, size-matched, opportunistic-filtered) is UNTESTED here and
plausible. Caveat: our micro +20% is survivorship-suspect + costless + wrong-benchmark → likely
inflated vs the literature's ~7.4%. → proper re-test in `2026-07-05_insider_literature.md`.
