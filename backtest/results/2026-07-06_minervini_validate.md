# Result — Minervini SEPA/VCP distilled-spec validation (closing 孤兒: exp_minervini_validate.py)

**Date:** 2026-07-06 (rerun; script + verdict existed since ~2026-07-03 but was never filed — the verdict
only ever printed to console, per `backtest/experiments/README.md`'s orphan note).
**Script:** `exp_minervini_validate.py`  **Tag:** active 🟡 (PARTIAL, weak — does not upgrade the
existing negative-leaning verdict from `exp_minervini_breakout.py`)

## Question
Distillation source: `C:/projects/Distillation/knowledge/method/minervini_sepa/minervini_sepa.spec.yaml`.
Does the TECHNICAL core of Minervini's SEPA/VCP method (trend template + RS-rank threshold + breakout
above a 30d pivot on volume expansion, after a volatility CONTRACTION) show positive per-trade excess
vs SPY, look-ahead-safe, long-only, once swept over RS-threshold / stop-width / breakout-volume params
and deflated for multiple testing? Explicitly a first pass on the technical skeleton, not full
Minervini (fundamentals SKIPPED).

## Method (mirror: per-trade excess vs SPY, increment: RS/stop/volume-mult grid, no horizon split)
- Universe: merged cache `backtest/.insider_data/px_defeatbeta.pkl` (6769 keys) +
  `sp500_px.pkl` (505 keys, current-constituent, survivorship-flagged) → **3336 distinct tickers**
  with usable price series (many defeatbeta entries are `None`/unloadable and are dropped in the
  merge). SPY itself spans **1996-01-24 → 2026-07-02** (7659 daily rows) — this is the effective
  backtest window (all signals are gated to when SPY-derived indicators are defined).
- Filter (per stock, once): trend template (150/200 SMA stack, price>50/150/200SMA, 200SMA rising
  21d, off 52w-low ≥30%, within 25% of 52w-high) & ATR-contraction (20d ATR < ATR 40d ago, VCP proxy)
  & breakout (close > prior-30d high, within 5% of it — no chase) & regime (SPY>200SMA at that date).
  **2930 of 3336 tickers (88%) produce ≥1 base signal.**
  RS = trailing-6m return cross-sectional percentile (month-end, ffilled to daily — point-in-time).
- Sweep: RS threshold {70,80,90} × stop {7%,8%,10%} × breakout-volume multiple {1.0×,1.5×} = 18
  param sets. Exit = tight stop OR close<50SMA, else 126-trading-day (≈6mo) max hold. **Costless**
  (script's own assumption, unlike the family's usual 10bps — disclosed here, not fixed).
- No two-halves split in this script (FULL-period pooled only) — does **not** meet the repo's
  2026-07-05 four-bucket/two-halves testing standard; this is an as-is rerun of an existing script,
  not a redesign.

## Results (real run, 2026-07-06 — network/cache-only, no live download needed)
18 param sets swept; **volx=1.0 and volx=1.5 rows are numerically IDENTICAL in every case** — see
Caveats (the volume-confirmation leg cannot discriminate: the cache carries no volume for the
defeatbeta-sourced series, so `volr` defaults to a constant pass-through). Effectively **9 distinct
cells** (RS × stop only). Unique cells below (excess%/exc-t/Sharpe = per-trade excess vs SPY,
its t-stat, and the ann. Sharpe of that excess series):

| RS≥ | stop | trades | win% | avgW% | avgL% | expct% | excess% | exc t | Sharpe |
|---|---|---|---|---|---|---|---|---|---|
| 70 | 7% | 28160 | 33 | 16.8 | -5.6 | 0.90 | 0.90 | 6.48 | 0.12 |
| 70 | 8% | 28000 | 33 | 16.9 | -5.8 | 0.93 | 0.93 | 6.62 | 0.12 |
| 70 | 10% | 27834 | 34 | 17.0 | -5.9 | 0.98 | 0.98 | 6.87 | 0.12 |
| 80 | 7% | 19996 | 32 | 18.7 | -6.1 | 1.11 | 1.11 | 6.02 | 0.13 |
| 80 | 8% | 19872 | 33 | 18.8 | -6.2 | 1.14 | 1.14 | 6.10 | 0.13 |
| 80 | 10% | 19733 | 33 | 18.9 | -6.4 | 1.22 | 1.22 | 6.39 | 0.13 |
| 90 | 7% | 9782 | 31 | 24.1 | -7.1 | 1.76 | 1.76 | 5.21 | 0.16 |
| 90 | 8% | 9702 | 31 | 24.2 | -7.3 | 1.79 | 1.79 | 5.21 | 0.16 |
| **90** | **10%** | **9612** | **32** | **24.3** | **-7.6** | **1.87** | **1.87** | **5.35** | **0.16** |

**Best cell (script's own selection rule = max mean excess): RS≥90 / stop 10% / volx 1.0** →
per-trade excess vs SPY **+1.87%**, expectancy **+2.73%**, n=9612 trades, ann. Sharpe(excess) **0.16**.
**Deflated Sharpe: `nan`** (see Caveats — broken by construction, not "inconclusive data").

**Script's own printed verdict:** `>>> PARTIAL: technical core shows positive per-trade excess vs SPY
across the sweep.` (verdict rule: VALIDATED needs excess>0 & Sharpe>0.5 & n≥200; here Sharpe caps at
0.16 → PARTIAL, not VALIDATED.)

## Conclusions
1. **Directionally positive, but weak — matches the "no material alpha" family verdict, doesn't
   upgrade it.** Every cell shows positive average excess (+0.9% to +1.9%/trade) with a low win rate
   (31-34%) and low per-trade Sharpe (0.12-0.16) — a "big-winners-small-losers" profile (avgW
   16.8-24.3% vs avgL −5.6 to −7.6%) typical of trend/breakout systems, but the risk-adjusted quality
   is weak relative to other repo signals (e.g. RS-leader selection Sharpe ≈1+, 20d-breakout timer
   Sharpe 1.3-2.3 — see `2026-07-05_breakout_momentum.md`).
2. **Tighter RS threshold monotonically improves quality** (RS≥70 excess 0.90-0.98%/Sharpe 0.12 →
   RS≥90 excess 1.76-1.87%/Sharpe 0.16, at 1/3 the trade count) — consistent with, and another data
   point for, the repo's separately-validated RS-leader-selection edge
   (`2026-07-05_factor_families_momentum_lowvol_rs.md` §RELATIVE-STRENGTH).
3. **Volume-confirmation leg is INERT in this run** — cannot be tested with the current cache (no
   volume series survives the merge for the bulk of the universe), so this run cannot speak to
   whether real volume confirmation would help (matches the already-registered gap G1 in
   `docs/2026-07-06_gap_conflict_register.md`: "突破 + 成交量確認…唯一可能救 Minervini selection").
4. **Multiple-testing check did not run** (DSR = nan by construction — see Caveats). The "PARTIAL"
   verdict is therefore **unadjusted for the 18-cell (9 distinct) sweep**; take the magnitude with
   that in mind.

## Division of labor vs `exp_minervini_breakout.py` (2026-07-05, filed in `2026-07-05_breakout_momentum.md`)
Both scripts test a Minervini-style trend-template + breakout, but are NOT duplicates:

| | `exp_minervini_validate.py` (this file) | `exp_minervini_breakout.py` (existing) |
|---|---|---|
| Role | "CHECKER" — closest attempt at the full distilled SEPA/VCP spec | SPEC A/B — isolates entry vs risk-layer |
| VCP contraction proxy | **Yes** (ATR-shrink before breakout) | No |
| RS rule | swept threshold {70,80,90} | fixed ≥80 |
| Stop/exit sweep | stop {7,8,10%} × 50SMA / 126d max hold | fixed 8% stop vs FIXED 63d hold (isolates risk layer) |
| Cost | costless | 2bp/trade round-trip |
| Segmentation | pooled, FULL only | 4 market-cap tiers × two-halves |
| Metric | per-trade excess vs SPY + DSR | per-trade %/win%/capital-efficiency%/yr |
| Verdict | **PARTIAL** (weak positive, Sharpe 0.12-0.16) | **negative-leaning**: selection ≈ B&H once tiered (large/mid ≈ B&H, small below, micro well below); risk-layer (stop/trail) cuts returns, doesn't add them |

**They agree directionally** (Minervini-style entries are not a strong standalone edge — small
positive tilt at best, nothing near the repo's validated timer/selection signals) but **disagree in
strength of statement**: this run's un-tiered, un-two-halved pooling plus the RS≥90 result (weakest
sample, strongest cell) leaves open whether the positive tilt concentrates in a cap tier
`exp_minervini_breakout.py` already showed is weak (small/micro). Not reconciled here — flagged as
residual, not chased further (would require re-running with tiers + two-halves, out of scope for
this orphan close-out).

## Caveats
- **Code bug found, not fixed (per task discipline — logic untouched, disclosed here):**
  `run()`'s DSR call (`_dsr(pd.Series([exc_mean] * 12).values, ss, ...)`) passes a **constant
  12-element array** (12 copies of the same mean) as the "returns" argument. `deflated_sharpe_ratio`
  in `backtest/metrics.py` returns `np.nan` whenever `r.std(ddof=1) == 0` (line ~67) — a constant
  array always has zero std, so **this DSR call is `nan` by construction, for any input**. The
  multiple-testing check as coded cannot ever produce a verdict; it is not "this run happened to be
  inconclusive."
- **Volume confirmation is untestable with the current cache** (see Conclusion 3) — `volx` grid is
  decorative in this run.
- **Fundamentals SKIPPED** (price-only SEPA, per docstring) — this is explicitly a technical-core-only
  first pass, not the full method.
- **Costless** — no transaction cost, unlike the family's usual 10bps convention; real edge would be
  smaller net of cost (9600-28000 trades/sweep implies material turnover cost in practice).
- **Survivorship**: merged cache is a defined, not point-in-time, universe (defeatbeta + current
  S&P 500 constituents) — delisted/failed names are underrepresented.
- **No two-halves / no market-cap tiering** in this script — cannot confirm the effect is stable
  across 2016-20 vs 2021+ or across cap buckets (unlike its sibling `exp_minervini_breakout.py`,
  which does both and finds the effect weak/absent once tiered).
- RS percentile computed on pooled-distribution month-end ranks (same approximation noted elsewhere
  in the repo, e.g. `2026-07-05_factor_families_momentum_lowvol_rs.md`).

## Implication for Karst
Does **not** change the existing negative-leaning selection verdict from `exp_minervini_breakout.py`:
Minervini-style entries remain **not a validated standalone edge** worth wiring into the spine. The
one incrementally new, usable observation is the **RS-threshold monotonicity** (tighter RS = better
quality, fewer/costlier-to-fill trades) — already actionable via the separately-validated RS-leader
gating line, not via this spec. Do not re-run this exact script again without adding volume data,
two-halves, and market-cap tiers (or just prefer `exp_minervini_breakout.py`'s better-controlled
design for any future Minervini work).
