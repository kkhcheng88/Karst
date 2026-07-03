# Karst — Session Handoff (2026-07-03)

## What this commit adds
A thin, **read-only web dashboard** for the daily top-down scan (Traditional-Chinese,
multi-panel Eikon/terminal style) + a headless deploy path (Zeabur/Docker).

### New files
- `web/run_scan.py` — COMPUTE: cron target, runs the scan → `web/data/latest.json`
  (+ dated snapshot). Also computes the composite `market_score`.
- `web/market_score.py` — 0–100 **risk-on composite** (5 factors: trend/vol/breadth/
  momentum/term) + Δ1d/1w/1m + 90d sparkline + factor breakdown. From price series.
- `web/render.py` — pure JSON→HTML, panels (大盤=市場+大盤策略合併 / 板塊輪動 / 板塊 /
  tier-2 做多), inline SVG (gauge/sparkline/diverging bars), "如何計算" formula foldouts.
- `web/app.py` — SERVE: Flask, read-only (`/`, `/api/scan`, `/healthz`), token auth,
  optional in-proc daily cron.
- `web/README.md`, `Dockerfile`, `.dockerignore`, `requirements.txt`.
- `backtest/data.py` — `KARST_DATA_SOURCE=defeatbeta` env toggle → defeatbeta-first for
  headless (Yahoo throttles datacenter IPs). Local unset = yfinance-first (unchanged).

### Run
    python web/run_scan.py       # writes web/data/latest.json
    python web/app.py            # http://localhost:8000  (local: no token)
Deploy: Dockerfile bakes KARST_DATA_SOURCE=defeatbeta + in-proc daily cron; set
KARST_TOKEN; mount a volume at /app/web/data. See web/README.md.

## Research arc — what we PROVED today (all backtested, evidence-first)
Question: is "risk regime" the same as bull/bear (200SMA)? Can fear/greed time mean-reversion?

1. **牛熊 (trend, 200SMA) ≠ Risk Regime.** corr(trend-axis, risk-axis)=0.64 → two axes.
   Divergence (bull+risk-off / bear+risk-on) marks late-cycle / bottoming (2018/2020 tops,
   2022 bottom). Dashboard *should* show TWO axes + divergence, not one blended number.
2. **Credit (HYG/LQD) > VIX** for risk regime (matches KC Fed RORO research). Credit was
   the only risk gauge with a positive reversion edge.
3. **VIX is CONTRARIAN** (high VIX in a bear → bounce); F&G-style blending CANCELS the
   signal (opposite polarities) → use confirmation, NOT averaging.
4. **The "triple confirmation" bottom signal FAILED** rigorous test — not significant on
   independent samples (t≈1.2), failed OOS 2021–2026; the apparent edge was 2020-driven.
5. **VIX extremes ARE a robust MR entry** — VIX>30 → +5–6% fwd63, robust across all eras,
   incremental to RSI2; fearful dip (RSI2<10 & VIX>25) → +5.7–6.8% / 85% win. VIX>40 = top 2%.
6. **F&G (real CNN history 2011–2026, github whit3rabbit/fear-greed-data):** fear-entry
   works but VIX beats it. **F&G's real value is the GREED/EXIT side** (F&G>80 → +0.8% fwd63
   vs +3.1% baseline) — where **VIX<15 does NOT work**. So **VIX = fear gauge, F&G = greed
   gauge**, each on its own side; don't average them.
7. **RSI2>90/95 has ~no exit edge** (market stays overbought in a bull); F&G>75–80 is the
   medium-term froth trim. Different jobs: RSI2 = trade-exit (lock the bounce); F&G = de-risk.
8. **CAPSTONE — cost-inclusive equity curves vs B&H (SPY/QQQ/SPMO, 5bps/side):**
   the assembled fear/greed MR-timing strategy **≈ B&H, Jensen α ≈ 0** (SPY +0.1%, QQQ −0.1%,
   SPMO +0.4%). Lower MaxDD (~10pp) but only from lower avg exposure (beta ~0.7), not skill.
   **→ Do NOT deploy as index alpha.** Fear/greed = risk/exposure + conviction knob, NOT a
   systematic alpha engine. (Consistent with keeping RSI-2 timing as a *separate field*.)
   Lesson: a positive conditional forward return ≠ a strategy that beats B&H.

## Open decisions / next steps
- [ ] (optional) Leveraged-on-fearful-dips variant (RSI2<10 & VIX>25 → 1.3–1.5×) — the only
      untested path that MIGHT beat B&H, at higher tail risk.
- [ ] (design) If wanted: rebuild the 大盤 panel as TWO axes (趨勢 gate / 風險情緒) + a
      divergence read (finding #1). Risk axis = credit + VIX + safe-haven + true-breadth
      (% S&P >200MA) — built ourselves, NOT scraping CNN.
- [ ] Keep the dashboard; do NOT productionize a regime-timing alpha signal (finding #8).

## Where to pick up
- Dashboard: `python web/app.py` → http://localhost:8000 (a server may still be running on
  :8000 from the session).
- All of today's backtests were run inline (heredoc) — not saved as files. Conclusions live
  in this doc + memory (`regime-and-fear-greed-findings`, `karst-dashboard`).
