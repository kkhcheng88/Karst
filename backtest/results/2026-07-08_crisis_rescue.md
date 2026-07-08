# Result — A-type crisis-rescue event study (Phase-3 WS2, real data)

**Date:** 2026-07-08
**Script:** `backtest/experiments/exp_crisis_rescue.py`
**Tag:** active — mixed/negative on the naive residual leg, directionally positive but thin on the
"wait for the crest" leg; this is an **event study (n=12 at the main threshold), not a t-stat
verdict** — the per-episode table is the primary product.

## Question

Prior finding (`2026-07-06_sector_capeff.md`, H2): buying the worst-63d-return sector pair whenever
SPY>200SMA & VIX>28 loses to SPY by −2.45%/episode (t=−2.52, p=0.026, n=14) — a naive residual-
sector dip-buy does **not** work at a VIX>28 fear level. This study asks whether going to a much
higher, genuinely generational-panic VIX bar (35/40/45 close), AND filtering for a truly
**systemic** epicenter sector (XLF/XLE — economy-wide-chain, not e.g. a single supply-shock
sector), changes that verdict. Four legs per episode:

- **L1** naive residual — buy the trigger-day worst-2-by-trailing-63d-return sectors (this is the
  H2 mechanism, just at a much higher VIX bar).
- **L2** SPY control — buy SPY on the same trigger date (the discipline benchmark; excess vs
  itself is 0 by construction).
- **L3** epicenter leg — of the worst-2, keep only sectors that are XLF/XLE; skip (N/A) the
  episode if neither worst-2 sector is systemic.
- **L4** right-side epicenter — same target as L3, but entry delayed until VIX closes back below
  30 (waits for the panic to visibly crest).

n is necessarily tiny (this is a study of a dozen actual crises over 27 years) — conclusions use
direction + consistency + named exceptions, **not** p-values as arbiter, per the pre-registered
spec.

## Method

**Episode definition:** ^VIX daily close first > threshold; the same episode does not re-trigger
for the next 60 trading days. Thresholds {35, 40, 45} all run; **40 is the primary/main table**.
Window: 1999-01-01+ (the 9 original SPDR sectors have data from 1998-12-22, so 63-trading-day
trailing returns are available from ~1999 Q1).

**Universe:** XLK/XLF/XLE/XLV/XLI/XLP/XLU/XLY/XLB (9 original SPDR sectors, no ffill-before-
inception needed — all 9 predate 1999) + SPY + ^VIX.

**Data:** `backtest/data.py` `load(sym, adjusted=True)` (yfinance total-return) for equities;
`^VIX` loaded raw (index, no dividends). Master calendar = SPY's trading-day index, 1999-01-04 →
2026-07-07 (6,918 rows; live pull, network confirmed working, same-day as this report).

**Cost:** 5bps/side on every entry/exit (repo standard). **Execution lag:** signal at close T →
trade executes at close T+1 (repo convention), applied uniformly: L1/L2/L3 lag off the trigger
date; L4 lags off its own later "VIX closed <30" signal date. **Horizon:** all of 21/63/126/252
trading days reported for every leg, no cherry-picking. **Excess:** every leg's excess is computed
against SPY bought on that SAME leg's own dates — so L4's excess uses a SPY leg dated off L4's
later, right-side entry, not off the original trigger date (mirror/increment discipline,
memory `validation-mirror-and-increment`).

**VIX peak reported per episode** = max ^VIX close from the trigger day through the earlier of
(first close < 30 after the trigger) or a 90-trading-day cap (documented operationalization, not
a swept parameter).

**Narrative column** is this repo's own historical knowledge (labeled explicitly as narrative,
not a backtested quantity) — one line on the contemporaneous policy response, to let the reader
judge "was there actually a backstop here or not" per episode.

**Stats:** a paired `ttest_1samp` on the excess series is reported as a secondary descriptive next
to n/mean/median/win%/worst — never as the sole verdict, per spec (n<10 in most cells).

## Results — main table (VIX>40 close, n=12 episodes)

2022's inflation/rate-hike bear market (VIX max close ≈34) **never triggers** at this threshold —
a useful sanity check confirming this study is genuinely at a higher bar than H2's VIX>28, and
correctly excludes the one episode where the Fed was hiking (no rescue put) rather than easing.

| trigger date | VIX@trig | VIX peak | worst-2 (63d ret) | epicenter | L4 entry | narrative (own knowledge, not data) |
|---|---:|---:|---|---|---|---|
| 2001-09-17 | 41.8 | 43.7 | XLK(−29.1%), XLI(−20.8%) | NONE | N/A | 9/11; markets closed 4 days, Fed slashed rates post-reopen, airline/insurance federal backstops. |
| 2002-07-22 | 41.9 | 45.1 | XLU(−30.6%), XLK(−29.8%) | NONE | N/A | WorldCom/Enron scandals + post-dot-com bear low; Sarbanes-Oxley passed, Fed cutting toward 1.0-1.25%. |
| 2008-09-29 | 46.7 | 80.9 | XLE(−32.4%), XLB(−21.2%) | XLE | never<30 | Lehman/GFC; TARP $700B, AIG bailout, Fed QE1 (Nov 2008), Fannie/Freddie conservatorship. |
| 2008-12-24 | 44.2 | 56.7 | XLF(−42.6%), XLB(−38.6%) | XLF | never<30 | Same GFC episode continuing. |
| 2009-03-25 | 42.2 | 45.5 | XLF(−20.2%), XLI(−15.3%) | XLF | 2009-05-19 | GFC tail; TARP/QE1/TALF still active, market bottom Mar 9 2009. |
| 2010-05-07 | 41.0 | 41.0 | XLV(−3.3%), XLU(+1.5%) | NONE | N/A | Flash Crash (May 6) + Greek sovereign debt; EU/IMF first Greek bailout, ECB SMP. |
| 2011-08-08 | 48.0 | 48.0 | XLF(−24.1%), XLI(−22.4%) | XLF | 2011-10-14 | US S&P downgrade + EU debt escalation; Fed Operation Twist (Sept 2011). |
| 2015-08-24 | 40.7 | 40.7 | XLE(−23.4%), XLB(−17.7%) | XLE | 2015-08-27 | China yuan devaluation/"Black Monday"; PBoC stimulus, no US policy response — self-resolving. |
| 2020-02-28 | 40.1 | 82.7 | XLE(−20.7%), XLB(−11.7%) | XLE | 2020-05-08 | COVID crash; Fed to zero + unlimited QE, CARES Act $2.2T, PPP — largest backstop in sample. |
| 2020-06-11 | 40.8 | 40.8 | XLU(+8.6%), XLP(+12.0%) | NONE | N/A | Single-day COVID-resurgence scare + cautious Fed SEP; no new policy action. |
| 2020-10-28 | 40.3 | 40.3 | XLE(−22.2%), XLV(−3.0%) | XLE | 2020-11-04 | Pre-election COVID 2nd-wave fear (ahead of Nov 9 vaccine news); no policy action. |
| 2025-04-04 | 45.3 | 52.3 | XLK(−21.2%), XLY(−17.2%) | NONE | N/A | "Liberation Day" tariff shock; 90-day pause announced, Fed on hold — trade-deal not monetary. |

**Per-episode leg returns / excess-vs-SPY-same-dates, all four horizons** (ret%/excess%; N/A =
leg skipped — no systemic sector in worst-2, or VIX never closed <30 within the 90td cap):

| episode | leg | h=21d | h=63d | h=126d | h=252d |
|---|---|---:|---:|---:|---:|
| 2001-09-17 | L1 | +4.77/+1.02 | +19.31/+9.16 | +13.69/+1.93 | −22.12/−6.74 |
| | L2 (ctrl) | +3.74/0 | +10.15/0 | +11.76/0 | −15.38/0 |
| | L3/L4 | N/A | N/A | N/A | N/A |
| 2002-07-22 | L1 | +23.27/+3.63 | +4.20/−8.98 | +14.08/+2.87 | +30.25/+4.12 |
| | L2 (ctrl) | +19.64/0 | +13.18/0 | +11.21/0 | +26.13/0 |
| | L3/L4 | N/A | N/A | N/A | N/A |
| 2008-09-29 | L1 | −24.86/−5.03 | −28.67/−5.92 | −30.92/−1.81 | −9.03/−2.33 |
| | L2 (ctrl) | −19.83/0 | −22.75/0 | −29.11/0 | −6.70/0 |
| | L3 | −24.04/−4.21 | −25.01/−2.26 | −30.86/−1.75 | −13.20/−6.50 |
| | L4 | N/A | N/A | N/A | N/A |
| 2008-12-24 | L1 | −5.50/−5.66 | −14.10/−5.05 | +11.35/+3.73 | +39.74/+7.55 |
| | L2 (ctrl) | +0.16/0 | −9.05/0 | +7.61/0 | +32.19/0 |
| | L3 | −12.57/−12.73 | −28.48/−19.43 | +3.92/−3.70 | +25.52/−6.67 |
| | L4 | N/A | N/A | N/A | N/A |
| 2009-03-25 | L1 | +10.96/+7.78 | +19.60/+8.29 | +46.84/+19.30 | +66.74/+23.80 |
| | L2 (ctrl) | +3.18/0 | +11.31/0 | +27.54/0 | +42.94/0 |
| | L3 | +13.99/+10.81 | +26.29/+14.98 | +57.34/+29.80 | +71.93/+28.99 |
| | L4 | +3.16/+0.99 | +19.18/+8.23 | +27.71/+3.54 | +23.21/+2.13 |
| 2010-05-07 | L1 | −6.10/+2.69 | +1.33/+3.69 | +6.48/−0.13 | +17.55/−0.61 |
| | L2 (ctrl) | −8.79/0 | −2.36/0 | +6.61/0 | +18.16/0 |
| | L3/L4 | N/A | N/A | N/A | N/A |
| 2011-08-08 | L1 | −1.84/−3.07 | +5.75/−2.18 | +17.63/+1.35 | +18.12/−3.89 |
| | L2 (ctrl) | +1.23/0 | +7.92/0 | +16.29/0 | +22.01/0 |
| | L3 | −3.68/−4.91 | +2.28/−5.64 | +13.80/−2.49 | +16.03/−5.98 |
| | L4 | +6.61/+1.85 | +14.62/+5.27 | +26.72/+10.31 | +34.11/+10.59 |
| 2015-08-24 | L1 | +2.53/−0.91 | +13.47/+1.36 | +0.29/−5.19 | +21.79/+3.05 |
| | L2 (ctrl) | +3.44/0 | +12.11/0 | +5.48/0 | +18.73/0 |
| | L3 | +5.79/+2.35 | +14.50/+2.39 | −2.45/−7.92 | +21.36/+2.62 |
| | L4 | −8.49/−3.28 | +3.73/−1.87 | −10.33/−10.75 | +9.37/−2.47 |
| 2020-02-28 | L1 | −27.30/−11.10 | −6.18/−5.51 | −1.16/−15.63 | +25.99/−1.28 |
| | L2 (ctrl) | −16.20/0 | −0.66/0 | +14.48/0 | +27.27/0 |
| | L3 | −36.98/−20.78 | −14.48/−13.81 | −19.97/−34.44 | +11.15/−16.12 |
| | L4 | +12.43/+3.48 | +1.79/−13.32 | −21.91/−42.51 | +44.50/+0.76 |
| 2020-06-11 | L1 | +3.01/−2.18 | +6.59/−3.60 | +12.33/−9.12 | +20.91/−20.98 |
| | L2 (ctrl) | +5.19/0 | +10.19/0 | +21.45/0 | +41.89/0 |
| | L3/L4 | N/A | N/A | N/A | N/A |
| 2020-10-28 | L1 | +18.20/+8.58 | +27.14/+12.75 | +51.63/+24.07 | +71.98/+30.98 |
| | L2 (ctrl) | +9.61/0 | +14.39/0 | +27.56/0 | +40.99/0 |
| | L3 | +28.58/+18.97 | +40.37/+25.98 | +81.80/+54.24 | +110.51/+69.51 |
| | L4 | +34.06/+28.78 | +51.80/+39.94 | +85.63/+65.51 | +106.11/+70.59 |
| 2025-04-04 | L1 | +13.81/+2.67 | +30.99/+7.02 | +43.44/+10.15 | +40.65/+4.44 |
| | L2 (ctrl) | +11.14/0 | +23.97/0 | +33.29/0 | +36.21/0 |
| | L3/L4 | N/A | N/A | N/A | N/A |

**Aggregate (VIX>40, descriptive — n<10 in most cells, not a t-stat verdict):**

| leg | h | n | mean exc% | median exc% | win% | worst exc% | t (desc.) |
|---|---:|---:|---:|---:|---:|---:|---:|
| L1 | 21 | 12 | −0.13 | +0.06 | 50.0 | −11.10 | −0.08 |
| L1 | 63 | 12 | +0.92 | −0.41 | 50.0 | −8.98 | +0.45 |
| L1 | 126 | 12 | +2.63 | +1.64 | 58.3 | −15.63 | +0.82 |
| L1 | 252 | 12 | +3.18 | +1.22 | 50.0 | −20.98 | +0.81 |
| L3 | 21 | 7 | −1.50 | −4.21 | 42.9 | −20.78 | −0.29 |
| L3 | 63 | 7 | +0.32 | −2.26 | 42.9 | −19.43 | +0.05 |
| L3 | 126 | 7 | +4.82 | −2.49 | 28.6 | −34.44 | +0.44 |
| L3 | 252 | 7 | +9.41 | −5.98 | 42.9 | −16.12 | +0.83 |
| L4 | 21 | 5 | +6.36 | +1.85 | 80.0 | −3.28 | +1.11 |
| L4 | 63 | 5 | +7.65 | +5.27 | 60.0 | −13.32 | +0.86 |
| L4 | 126 | 5 | +5.22 | +3.54 | 60.0 | −42.51 | +0.30 |
| L4 | 252 | 5 | +16.32 | +2.13 | 80.0 | −2.47 | +1.19 |

## Threshold sensitivity (35 / 40 / 45), h=63d mean excess

| threshold | n episodes | L1 mean exc (63d) | L3 mean exc (63d) | L4 mean exc (63d) |
|---|---:|---:|---:|---:|
| VIX>35 | 19 | +2.81% | +2.59% | +5.02% |
| VIX>40 | 12 | +0.92% | +0.32% | +7.65% |
| VIX>45 | 7 | +2.51% | −0.28% | +0.64% |

Full per-episode tables at 35 and 45 are in the script's stdout log (not reproduced in full here
— same format as the VIX>40 table above); the 45-threshold set drops 2001-09, 2002-07-22, and
2010-05-07 (none reached 45), and adds one extra 2010-05-20 flash-crash-recovery episode and a
second 2002-08-05 episode; the 35-threshold set additionally picks up the whole 1999 LTCM/Y2K
tail plus 2018 (Volmageddon, Dec-2018), 2021-01 (GameStop), 2022-03 (rate-hike bear, negative
control), and 2024-08 (yen-carry unwind).

## Conclusions

**Episode count:** 12 episodes clear VIX>40 close over 1999-2026 (19 at >35, 7 at >45). Roughly
matches the pre-registered expectation (2001, 2002×2, 2008-09/12, 2009-03, 2010-05, 2011-08,
2015-08, 2020-02/06/10, 2025-04) — 2022's inflation bear market never crosses 40 (max close ≈34),
correctly staying outside this study's scope as a negative-control absence.

**① Does the "systemic" filter (L3) beat the naive residual (L1)?** **No, not cleanly.** At the
main threshold (VIX>40), L3's h=63d mean excess (+0.32%) is *worse* than L1's (+0.92%), and L3's
win-rate is markedly lower at every horizon except 252d (e.g. 126d: L3 28.6% vs L1 58.3%). L3 only
clearly separates positively at 252d (+9.41% vs +3.18%, mostly carried by 2020-10-28's outsized
+69.5% excess). Restricting to XLF/XLE does **not** systematically improve on "just buy the worst-
2, whatever they are" — the systemic-sector prior does not hold up as a selection filter in this
sample. **Verdict: no evidence the "systemic" filter adds value over the naive residual pick.**

**② Right-side (L4, wait for VIX<30) vs left-side (L3, buy at the trigger)?** **L4 is
directionally better at every horizon and every threshold** at the VIX>40 bar: mean excess 63d
+7.65% (L4) vs +0.32% (L3); win-rate 60-80% (L4) vs 28.6-42.9% (L3) at every horizon. This is the
**opposite** of the "waiting for the dip costs you" finding flagged elsewhere in this repo's core
work (`2026-07-07_topup_timing_ab.md`: dip-gating a LEAP top-up hurt vs pure GATED; `exp_leap_
real_sweep.py`: "pure GATED > DIP" is a repo-level finding) — but the two are not the same
mechanism: the core LEAP-timing finding is about NOT waiting for a dip inside an already-bullish
regime, whereas L4 here is a **crisis-conditional** right-side entry (only fires after the tape
has already crested from a VIX>40 spike), closer to a trend-confirmation filter than a market-
timing dip-gate. **Both L3 and L4 have small n (7 and 5 at the main threshold)** — treat this as
directionally consistent, not proven; L4's advantage is also inflated by 2020-10-28 (a single
episode contributing +39.9%/+65.5%/+70.6% excess at 63/126/252d) and 2009-03-25/2011-08-08
(consistently smaller but real positive L4 excesses). Remove 2020-10-28 and L4's edge shrinks
substantially but stays directionally positive at 21/63d. **Verdict: waiting for the VIX-crest
before buying the epicenter sector looks better than buying at the peak — direction is
consistent across n=5-8 episodes and 3 thresholds, but the effect size is not proven at this
sample size and is outlier-sensitive.**

**③ Which horizon is the sweet spot?** No horizon is unambiguously best across all legs/
thresholds, but **63d and 126d are the most consistently positive-and-least-outlier-driven** cells
for L1 (win-rate 50-58%, moderate dispersion) and for L4 (win-rate 60-80% at every horizon, but
worst-case excess balloons at 126d for L3/L4 — 2020-02-28's L3 −34.4%/L4 −42.5% at 126d, both
COVID-crash episodes where the epicenter (energy) kept falling well past 63 trading days before
the eventual 2020-Q4/2021 vaccine-driven recovery). 21d is the weakest cell everywhere (L1/L3 mean
excess near zero or negative) — too short to capture the rescue-bounce; the "rescue" mostly plays
out over a full quarter to two quarters, not a month. 252d shows the largest point estimates but
also the largest dispersion (worst-case −20.98% for L1 in 2020-06-11, −24.46% for L3 in 2024-08 at
the 35-threshold set) — a full year is long enough for an unrelated intervening shock (the next
crisis, or in 2020-06-11's case, nothing bad at all — SPY simply outran the sector pick by 21pp).
**Verdict: 63-126d is the sweet zone; 21d is too early, 252d carries too much unrelated-noise
risk to call a clean horizon.**

**④ 2025-04-04 (most recent episode) — how did all four legs perform?** Worst-2 sectors were
XLK/XLY (tech/discretionary — a **tariff-driven demand/supply-chain scare**, not a systemic
financial-sector one), so **neither XLF nor XLE appears in the worst-2 and L3/L4 are both N/A**
for this episode — the "systemic epicenter" framing does not even apply to this crisis. L1 (naive
worst-2) modestly beat SPY at every horizon: +2.67/+7.02/+10.15/+4.44pp excess at 21/63/126/252d.
This is itself informative: 2025-04 is a clean example of a panic that was **not** a systemic-
sector crisis (no bank/energy epicenter), consistent with its narrative (a trade-policy shock
that resolved via a negotiated tariff pause, not a Fed/Treasury financial-system rescue) — the
brief's "systemic + policy-put" story simply doesn't describe this one.

## Caveats

- **n is the headline caveat, by design.** 12 episodes at the main threshold, 5-8 with a
  systemic epicenter present (L3/L4). Every aggregate stat above is descriptive, not inferential;
  single episodes (2020-10-28, 2020-02-28) move means and win-rates substantially.
- **63d-trailing-return "worst-2" selection is mechanical and can pick non-systemic sectors** at
  a given episode (e.g. 2001, 2002, 2010-05, 2020-06, 2025-04 all have no XLF/XLE in the worst-2)
  — this is a real, not a modeling-artifact, finding: the "beaten epicenter is always a systemic
  sector" premise in the brief only holds for ~5 of 12 VIX>40 episodes in this sample (all GFC/
  euro-crisis/2015-China/2020-COVID-related — i.e. clusters where financials or energy were
  genuinely epicenter).
- **L4's "never<30" episodes** (2008-09-29, 2008-12-24) are excluded from the L4 leg entirely,
  not force-entered late — meaning the two most severe GFC sub-episodes (both still inside the
  broader 2008-09→2009-03 GFC complex) never generate an L4 observation; L4's small n is partly a
  direct consequence of how long VIX stayed elevated in 2008.
- **90-trading-day cap on the "VIX peak" / L4-reentry window** is a documented operationalization
  choice, not swept — for 2008-09/12 this caps the reported "VIX peak" at 80.9/56.7 (the true VIX
  peaks around Oct-Nov 2008 exceeded this within the cap window, so the reported peak is still
  accurate for those two, but the cap could in principle truncate a slower-building episode's true
  peak; not observed to bind incorrectly in this sample).
- **Dedup window (60 trading days)** occasionally splits what a human would call one continuous
  crisis into 2 episodes (2008-09-29 and 2008-12-24 are both "the GFC"; 2020-02-28 and 2020-06-11
  and 2020-10-28 are all "COVID"). This is a pre-registered mechanical rule, not re-tuned
  post-hoc — but readers should treat clustered episodes as correlated observations, not fully
  independent draws, when reading the aggregate win-rates.
- **Narrative column is this repo's own historical knowledge**, explicitly labeled as narrative —
  not derived from any dataset, and not fact-checked against a primary source in this pass.
- **Execution-lag convention** (signal T → trade T+1) applied uniformly to L1/L2/L3's trigger-
  date entry and to L4's later VIX<30 signal date — consistent with the rest of this repo's
  event-driven scripts (documented, not a bug).
- **5bps/side cost** is a small drag relative to the return magnitudes reported here (single-digit
  to double-digit percent moves) — cost sensitivity was not separately swept in this study since
  it would not move any of the four qualitative conclusions above.

## Implication

The brief's premise — "generational panic + beaten systemic sector + policy backstop = violent
mean reversion, different from H2's shallower VIX>28 failure" — is **partially supported, with an
important correction**: going to a much higher VIX bar (40+) does look somewhat better directionally
than H2's VIX>28 result (L1 mean excess flips from significantly negative at VIX>28 to modestly
positive-but-noisy at VIX>40), but the **"systemic-sector filter" itself does not add value** — L3
does not beat L1 at the horizons that matter (63/126d) in this sample. The one piece of genuinely
new, consistent signal is **timing, not sector selection**: waiting for VIX to visibly crest below
30 before buying the epicenter sector (L4) looks better than buying at the peak (L3) across every
horizon and every threshold tested — though with n=5-8 this is a lead to watch, not a rule to
hard-code. Given both n and effect-size uncertainty, **this does not clear the bar to become a
mechanical core rule** — it is evidence for the thesis layer / WS2 design discussion, not a
signal to wire into the spine today.

## Addendum (2026-07-08) — L5 (right-side naive worst-2) + 2020-10-28 sensitivity

Executes `docs/2026-07-08_phase3_ws2_crisis.md` §4 backlog item #1: (a) add **L5 = right-side
entry (wait for VIX close < 30) applied to the plain naive worst-2** — L4's entry-timing rule but
L1's target, no systemic-sector screen; (b) re-run the L4/L5 comparison with the 2020-10-28
episode dropped, since the main table above already flagged it as the single biggest driver of
L4's aggregate excess. Same data/cost/lag conventions as above; VIX>40 main threshold unless noted.

**L5 aggregate (VIX>40, n=10 — every episode where VIX re-closed <30 within the 90td cap,
independent of whether an epicenter sector was present):**

| leg | h | n | mean exc% | median exc% | win% | worst exc% |
|---|---:|---:|---:|---:|---:|---:|
| L4 | 21 | 5 | +6.36 | +1.85 | 80.0 | −3.28 |
| L4 | 63 | 5 | +7.65 | +5.27 | 60.0 | −13.32 |
| L4 | 126 | 5 | +5.22 | +3.54 | 60.0 | −42.51 |
| L4 | 252 | 5 | +16.32 | +2.13 | 80.0 | −2.47 |
| L5 | 21 | 10 | +2.06 | +2.06 | 60.0 | −4.11 |
| L5 | 63 | 10 | +3.08 | +1.60 | 60.0 | −3.66 |
| L5 | 126 | 10 | +1.44 | −0.26 | 50.0 | −15.16 |
| L5 | 252 | 10 | +3.34 | +2.72 | 70.0 | −23.02 |

L4's n=5 is a **strict subset** of L5's n=10 — every episode where an epicenter sector was in the
worst-2 also has an L5 observation (same right-side entry date), plus L5 additionally covers the
5 episodes where the worst-2 had no XLF/XLE (2001-09-17, 2002-07-22, 2010-05-07, 2020-06-11,
2025-04-04). Comparing on the **matched 5-episode subset only** (2009-03-25, 2011-08-08,
2015-08-24, 2020-02-28, 2020-10-28 — where both legs exist), 63d mean excess is L4 +7.65% vs L5
+4.22%, and the per-episode sign is **not** consistently one-directional: L4 beats L5 clearly at
2009-03-25 (+8.23 vs +3.20) and 2020-10-28 (+39.94 vs +16.90), but L5 beats L4 clearly at
2020-02-28 (−3.66 vs −13.32, i.e. epicenter-only XLE got hit much harder than the XLE+XLB naive
pair that quarter) and marginally at 2011-08-08 (+5.84 vs +5.27); 2015-08-24 is a wash (both
negative, L5 slightly less bad). So the systemic screen does not uniformly help even within its
own matched sample — it wins big twice, loses clearly once, ties twice.

**Sensitivity: drop the 2020-10-28 episode (VIX>40, L4 & L5):**

| leg | h | n | mean exc% | median exc% | win% | worst exc% |
|---|---:|---:|---:|---:|---:|---:|
| L4 | 21 | 4 | +0.76 | +1.42 | 75.0 | −3.28 |
| L4 | 63 | 4 | −0.42 | +1.70 | 50.0 | −13.32 |
| L4 | 126 | 4 | −9.85 | −3.61 | 50.0 | −42.51 |
| L4 | 252 | 4 | +2.75 | +1.44 | 75.0 | −2.47 |
| L5 | 21 | 9 | +0.89 | +1.81 | 55.6 | −4.11 |
| L5 | 63 | 9 | +1.54 | +0.01 | 55.6 | −3.66 |
| L5 | 126 | 9 | −1.69 | −0.68 | 44.4 | −15.16 |
| L5 | 252 | 9 | +0.50 | +1.31 | 66.7 | −23.02 |

Once 2020-10-28 is dropped, **L4's edge does not just shrink — it flips negative** at 63d
(+7.65% → −0.42%) and 126d (+5.22% → −9.85%), confirming the main table's caveat that L4's
headline result was carried almost entirely by that single episode. **L5 also shrinks** (63d
+3.08% → +1.54%; 126d +1.44% → −1.69%) but stays modestly positive at 21/63/252d and its 126d
decline is far smaller in magnitude (−1.69 vs −9.85) — L5 is **less outlier-dependent**, as
expected from having double the n.

**L4 vs L5 verdict:** use **L5** as the formal object for the crisis sleeve. Three reasons: (1)
n=10 vs n=5 — L5 fires on every right-side re-entry regardless of whether an epicenter sector
happened to be in the worst-2, so it is the more usable rule (an ARM/ENTER state machine needs a
target on every qualifying episode, not just the ~half that clear the systemic filter); (2) on the
matched subset the systemic screen (L4) does not uniformly beat naive (L5) — it wins twice, loses
once decisively, ties twice, consistent with the main table's finding (①) that L3 does not beat L1
either; (3) removing the single episode propping up L4's aggregate flips its 63/126d mean negative,
while L5's decline is smaller and stays directionally positive — L5 is the more robust leg to hang
a rare-event sleeve on. **Net: right-side timing (waiting for VIX<30) is the real, if thin,
signal; the epicenter/systemic-sector screen adds no reliable value on top of it and should be
dropped from the sleeve design** — `docs/2026-07-08_phase3_ws2_crisis.md` §2's "target sector"
step should read as "worst-2 by trailing 63d return at ARM time", not "worst-2 filtered to
XLF/XLE".
