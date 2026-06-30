# Spine Phase 2a — GICS sector-rotation map (the DEFENSE / regime lens)

2026-07-01. First slice of Phase 2. User chose to settle everything besides Phase 3 first;
2a is the cheap, high-signal piece (reuses the Stage-1 machinery, ETF-only, no overfitting).

## What it is

`spine/rotation.py` ranks the 11 SPDR GICS sectors by RS vs SPY (63d + 21d), with the regime
reads that actually matter (raw return correlations are dominated by market beta, so we do NOT
lean on a correlation matrix here):
- **leadership breadth** — how many of 11 beat SPY (narrow ≤3 = fragile/late-cycle; broad ≥6)
- **cyclical-vs-defensive tilt** — risk-on (cyclicals lead) vs risk-off (defensives lead)
- **tech-leading flag** — XLK beating SPY (the offense thesis confirmation; see below)

ETF-PRICE mode: broad sectors have long clean history, so the ETF price IS the sector (no
holdings basket — that's only for young thematics like DRAM). Shown after the market gate,
before the MEMORY subsector. ETF-only by design — no per-name work in defensive sectors
(the asymmetric-depth rule that controls multiple-testing).

## Design decisions baked in (from the strategy discussion)

- **Two lenses, held separately:** GICS sectors = rotation/regime/DEFENSE (this file). A
  value-chain (AI/Data-Center) cuts ACROSS GICS (Tech→Energy→Materials/InP→Industrials) and is
  the OFFENSE unit — individual names + bottleneck filter — which is Phase 3, NOT here. Do not
  force a value-chain into the GICS box.
- **Tech-leadership is made FALSIFIABLE, not assumed:** the user's thesis is "true bull runs come
  from tech value-chains." To keep that from becoming an unfalsifiable belief (the POET failure
  mode), rotation surfaces a `tech_leading` flag + a caveat when XLK is NOT beating SPY ("offense
  thesis unconfirmed — favour defense"). Defense sectors are funded because tech-leadership can
  fail for YEARS (2000-2010), not because they carry alpha.
- **Honest data caveat:** RS uses RAW (price-return) closes; high-yield sectors (XLU/XLP/XLRE)
  are slightly understated. Minor for short RS windows; any multi-month sector backtest (2b) MUST
  switch to total-return (dividend-adjusted) prices.

## Verified read (2026-06-30) — the lens earns its keep

`tilt risk-on (cyclicals lead, barely 0.94 vs 0.89) | breadth NARROW (2/11 beat SPY) | tech leading`
- Only **Tech (1.26)** and **Industrials (1.00)** beat SPY over 63d → narrow-leadership caveat
  fired (fragile / late-cycle, little to rotate into).
- RS63 vs RS21 reveals incipient rotation: Tech's 3-month lead is FADING on 1-month (RS21 1.01),
  while Industrials/Health/Fin RS21 (1.05-1.08) are accelerating. Leadership may be broadening
  off tech — a signal the single-window RS would hide.

This pairs with the narrow-breadth / overbought market read: risk-on but fragile, tech-led but
decelerating — consistent with the "wait, don't chase" posture the rest of the scan shows.

## Files
New: `spine/rotation.py`; `SectorRotation` in `schemas.py`. Changed: `orchestrator.py` (build +
ROTATION block + JSON `rotation` key).

## Next in Phase 2 (still besides Phase 3)
- **2b sector character:** measure trend-persistence at the RIGHT horizon (%>200SMA + drawdown +
  trend-efficiency, ACROSS regimes incl. 2022/2020/2018), and BACKTEST buy-dip-hold vs
  buy-dip-sell-bounce per sector (total-return, vs B&H, through the deflated-Sharpe/walk-forward
  gate). Output: a trend/chop tag per sector that modulates the Phase-4 EXIT.
- **2c rotation dynamics:** average pairwise correlation LEVEL (regime), anti-correlated axes
  (growth↔value, cyclical↔defensive), RS-leadership change — computed on RS / beta-residuals.
Then Phase 3 (thesis seam = value-chain + bottleneck = where alpha enters).
