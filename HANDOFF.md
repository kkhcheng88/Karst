# Karst — Session Handoff (2026-07-03)

> ⚠️ **已被 `STATUS.md` 取代為入口(2026-07-06)。** 本檔僅保留為 2026-07-03 當日詳細記錄。
> **注意:finding #2「Credit (HYG/LQD) > VIX」已於 2026-07-05 被推翻** —— credit 做風險軸失敗、剔除,改用
> 「VIX × 趨勢(200SMA)」2D(見 `results/2026-07-05_market_regime_2d.md`)。其餘 findings(資本效率 / alpha=T1+T2
> 拆解等)仍有效,已濃縮入 `.agents/KARS_MEMORY.md` §10。現行入口 = `STATUS.md`;交棒 = `docs/2026-07-06_fable_brief.md`。

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
   **⚠️ 已作廢 2026-07-05,見 STATUS.md:199-201** — credit 測完剔除(regime 反覆、對 VIX 無增量),
   改用「VIX × 趨勢(200SMA)」2D regime(`results/2026-07-05_market_regime_2d.md`,已 live)。
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

## Addendum (2026-07-03, same day) — top-10-days coverage + exposure-normalized alpha
User asked two follow-ups on finding #8: (1) does the overlay fall into the classic
"miss the market's top 10 days, miss your year" trap? (2) does alpha survive once you
correct for average exposure (relever to match B&H's beta)? Reconstructed the overlay
(capstone run was inline/unsaved) as a saved, re-runnable experiment:
`backtest/experiments/exp_topdays_exposure.py` → `backtest/results/2026-07-03_topdays_exposure.md`.
Also pulled real CNN Fear&Greed history to `reference/fear_greed/` (gitignored,
regenerable via `github.com/whit3rabbit/fear-greed-data`).

9. **Does NOT miss the top-10 days — structurally the opposite.** 9–10/10 of each asset's
   best single days (2011–2026) are violent rallies INSIDE crashes (2020-03 COVID,
   2018-12-26, 2011-08 debt-ceiling, 2025-04-09 tariff shock) — exactly when VIX-fear
   triggers fire. An overweight-on-fear (1.3x) variant captures 125–128% of B&H's
   top-10-day return sum; a no-leverage variant still captures ~97–100%.
10. **Relevering to B&H's average exposure does NOT unlock hidden alpha.** Scaling the
    SAME signal timing to avg exposure=1.0: alpha stays negative everywhere, never flips
    positive. For a flat-baseline MR variant (avg exposure ~0.14), relevering implies
    ~7x leverage in fear windows → alpha gets MASSIVELY worse (−17% to −19%/yr) via
    vol drag, not better. **Mechanism: relevering rescales the same timing decisions by
    a constant — it amplifies whatever's already there, it can't create skill that isn't
    in the entry/exit timing.** Sharpens (doesn't overturn) finding #8's do-not-deploy call.
    **Refined same day** (`exp_mr_roundtrip.py`, `exp_exposure_sweep.py` — user's
    methodological correction: B&H exposure=1.0 is trivial/by-construction; ours must be
    CALCULATED from real entry+exit rules, not assumed/targeted): entry=findings #5
    (VIX>30 or RSI2<10&VIX>25), exit=findings #6/#7 (RSI2>90 or F&G>80) → **calculated**
    avg exposure converges to **~14%** on all 3 assets regardless of exit rule (entry
    rarity dominates). Cross-checked relevering across every exposure level actually
    tested today (0.12→1.00, 3 independent constructions): **alpha never flips positive
    at any level** — robust to the exposure-assumption question. Open gap: none of these
    reconstructions reproduce finding #8's stated beta≈0.7 (rebuilds land at ~0.14 or
    ~1.0, not in between) — the original capstone's exact blend is unrecoverable
    (unsaved); doesn't change the Q2 conclusion, but the literal 0.7 figure is unverified.
    **Refined again same day** (`exp_mr_split_rules.py` — split combined entry/exit into
    2 independent rules): **RSI2 alone is the workhorse** (85-120 trades, ~39% calculated
    exposure, the most-powered cut tested today) — alpha still negative but weak/
    insignificant (t=-0.6 to -1.1). **VIX+F&G alone is rare/fragile** (only 4-6 trades in
    15yr — its more-negative, more-"significant" alpha (t to -2.1) is likely 1-2 episodes
    dominating, not trustworthy). Combining doesn't cancel/dilute here (unlike finding #3's
    VIX/F&G blend pattern) — sits between or even beats either alone on 2/3 assets, but
    never positive. Best-powered cut (RSI2 alone) still shows no alpha.
11. **CAPITAL-EFFICIENCY lens — user was right, per-exposure it IS efficient**
    (`exp_capital_efficiency.py`). User's objection: comparing a mostly-flat strategy's
    calendar CAGR vs always-up B&H is unfair; correct measure = PnL% / exposure (return on
    DEPLOYED capital), a CAPITAL-adjusted question distinct from Jensen α's RISK/beta one.
    Result (robust, both rules, all 3 assets): the timing deploys into **above-average days**
    (mean-daily-invested 1.3–3.1x B&H) at a **conditional Sharpe that BEATS B&H** (1.0–1.7 vs
    0.86–0.99); PnL/Exp 20–55%, deployed-capital-annualized 24–74% vs B&H 14–20%. Jensen α
    stays ~0/slightly-neg (insignificant) ONLY because β (0.45–0.67) >> exposure (0.14–0.39)
    — it enters high-vol days, so CAPM charges a high beta. **Per-time-capital = efficient;
    per-systematic-risk = neutral; both true.** The earlier relevered-CAGR framing (finding
    #10) was a MISLEADING way to show per-exposure perf — geometric releverage applies ~7x
    leverage to 33–37%-vol windows, so its −12% is vol-drag, not skill. **Revised takeaway:**
    NOT a SPY-replacement (flat 86% in an uptrend → wealth lags; can't naively lever — drag),
    but a genuinely useful **dry-powder DEPLOYMENT timer** (deploy idle cash into fear, earn a
    high rate on deployed capital). Strengthens finding #8's "risk knob" read: the beta it
    keeps is concentrated into the market's best-paid windows, not just reduced.
12. **WHY it can't be index alpha — exact decomposition** (`exp_alpha_decomp.py`). User:
    "good timing → +alpha only works for SPY if exposure high enough / leveraged / traded
    instrument ≠ SPY." Confirmed via exact identity for long/flat strat=pos·mkt vs same mkt:
    **α = Cov(pos,mkt) [T1 timing] + (exposure−β)·mean_mkt [T2 structural drag]**. Result
    (all 6 cuts): **T1 is POSITIVE (+2.2% to +6.2%/yr)** — timing genuinely anticipates
    above-avg days; **T2 is negative (−4% to −6.6%/yr)** because β (0.45–0.67) ≫ exposure
    (0.14–0.39) — buy-the-dip forces entry into high-VARIANCE days, inflating β while you sit
    flat through the up-drift. T1+T2 = the small negative α. **Remedies (verified): higher
    exposure via SPY baseline = zero-α dilution (fixes wealth-lag not α); leverage = α→L·α
    sign-preserving (no) + vol-drag; ONLY "traded instrument ≠ benchmark" structurally
    converts +T1 into outperformance.** This is exactly why Karst runs RSI-2/fear timing as an
    entry-timing field on individual names + option structures (VRP), NOT SPY-in/out —
    `exp_family_validate.py` already showed RSI-2 long-only top-quintile of broad universe
    beats SPY +12.5% CAGR (same T1, right instrument). User re-derived the architecture's
    rationale from the alpha algebra alone.

## Addendum 2 (2026-07-03) — 全系統審查 + roadmap(三份文件)
應用戶要求做了投資框架/方法論全審查(3 個唯讀 agent 抽取 spine/web/thesis 實作事實
+ 獨立驗收 agent 抽查 10 條 file:line 主張全 PASS):
- `docs/2026-07-03_strategy_methodology_review.md` — P0 級發現:**insider conf_eff
  算了但從未接回分數**(expression.py:66 用原始 th.unit)、**credit 軸/兩軸背離
  已驗證卻完全缺席**、**校準迴路是斷的**(log_predictions 從未寫入、outcome 回填
  程式碼不存在)、IC≥0.05 只是文字非程式。+ 反建議清單(別再挖的坑)。
- `docs/2026-07-03_dashboard_decision_experience.md` — 決策條/翻轉警示/兩軸主視覺/
  乾火藥計時器/證據連結;含逐面板實作錨點(file:line)。
- `docs/ROADMAP_AGENTIC.md` — Phase A(修接線)→ B(閉迴路:價格庫+paper ledger)
  → C(agent 運維)→ D(校準+IC 裁決=分水嶺)。「全自動」邊界釘死:決策管線
  自動,下單/新 thesis 採納/制度變更留人工。最先動手:A1(校準資料流,每天不修
  就流失資料)+ B1(價格庫)可並行。

## Open decisions / next steps
- [ ] (optional) Leveraged-on-fearful-dips variant (RSI2<10 & VIX>25 → 1.3–1.5×) — the only
      untested path that MIGHT beat B&H, at higher tail risk.
- [x] ~~(design) If wanted: rebuild the 大盤 panel as TWO axes (趨勢 gate / 風險情緒) + a
      divergence read (finding #1). Risk axis = credit + VIX + safe-haven + true-breadth
      (% S&P >200MA) — built ourselves, NOT scraping CNN.~~
      **⚠️ 已作廢 2026-07-05,見 STATUS.md:199-201** — credit 剔除;2D regime(VIX × 200SMA)已 live
      (`spine/context.py`),唔再需要 credit/safe-haven/true-breadth 呢條 TODO。
- [ ] Keep the dashboard; do NOT productionize a regime-timing alpha signal (finding #8).

## Where to pick up
- Dashboard: `python web/app.py` → http://localhost:8000 (a server may still be running on
  :8000 from the session).
- All of today's backtests were run inline (heredoc) — not saved as files. Conclusions live
  in this doc + memory (`regime-and-fear-greed-findings`, `karst-dashboard`).
