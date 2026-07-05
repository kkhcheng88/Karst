# Insider cluster-buy + factor-family re-validation (offline reproduction) — 2026-07-04

Reproduces and **saves** two previously off-book claims (cited in ARCHITECTURE/HANDOFF but never
written to `results/`): the insider 21d edge and the four-family long-only "hold the leaders" result.
Env: sandbox Python 3.10 + scipy 1.15.3, **fully offline** (SEC bulk download 403-blocked here;
defeatbeta/yfinance unavailable). Look-ahead-safe throughout.

## Data-integrity findings (act on these)
1. **Path bug (⚠️ committed script broken).** The 2026-07-03 reorg moved experiments into
   `backtest/experiments/` but left `.insider_data/` in `backtest/`. `exp_insider_validate._DATA`
   (and `exp_family_validate._DATA/_PXC`) resolve relative to `__file__`, so they now point at a
   non-existent `backtest/experiments/.insider_data` → the script silently falls back to
   **re-downloading from SEC** (blocked → 403). Reproduced here by overriding `_DATA` to
   `backtest/.insider_data`. Fix the committed scripts (repoint `_DATA`) before the weekly cron.
2. **Small-cap price cache is dead.** `px_defeatbeta.pkl` (136 MB, 1743 keys incl. SPY) has
   **0 non-None values** — every defeatbeta price is None. `px_cache.pkl` has only 369/1742.
   Only `sp500_px.pkl` (505 S&P names + SPY; 500 real daily Series, 1995–2026) is usable offline.
3. **Consequence:** the insider event universe (1742 mostly small/mid-cap tickers) could only be
   priced for the **110 names that are current S&P-500 members** → 189 matured events (vs the
   original full-universe run). The stronger small-cap insider edge cannot be reproduced offline.

## Insider cluster-buy event study — S&P-500-priced subset, 2022q1–2025q2
Signal: open-market P-buys (10b5-1 excluded), cluster = ≥2 distinct insiders + ≥$500k within ~21d;
entry = Form-4 FILING date; forward **excess** return vs SPY. n = 189 events (large-cap subset only).

| horizon | n | mean % | median % | hit>0 | t |
|---|---|---|---|---|---|
| 21d | 189 | +2.32 | +1.94 | 59% | **2.30** |
| 63d | 189 | +4.29 | +2.40 | 55% | **2.91** |
| 126d | 189 | +3.47 | −0.16 | 50% | 1.71 |

Portfolio (40 monthly cohorts): 21d Sharpe 1.27 (hit 70%), 63d 0.74, 126d 0.16.
**Deflated Sharpe (63d, vs 3 horizon variants) = 0.791** (< 0.95).

Read: a real short-horizon edge even on large-caps (21d t2.3, 63d t2.9); 126d median turns negative
→ short-term catalyst, not durable — same SHAPE as the original finding but weaker (original
full-universe 21d t≈5.12, which included the small-cap names now unpriceable). DSR 0.791 < 0.95 →
does **not** clear multiple-testing on this subset. Costless, equal-weight, current-S&P survivorship.

## Factor families — cross-section, S&P-500 universe, 1995–2026 (368 monthly rebalances, 152,936 name-months)
Cross-sectional Spearman IC (signal vs forward return):

| family | 21d IC (t) | 63d IC (t) |
|---|---|---|
| momentum (12-1) | +0.011 (1.06) | +0.014 (1.49) |
| mean-rev (RSI-2) | **+0.037 (5.97)** | +0.025 (4.25) |
| RS-short (63d) | −0.011 (−1.25) | −0.013 (−1.56) |
| RS-med (126d) | −0.004 (−0.41) | −0.001 (−0.11) |
| low-vol (63d) | −0.036 (−2.85) | −0.061 (−4.98) |

Long-only, hold **top-quintile** by signal, equal-weight monthly, vs SPY buy&hold (full sample):

| family | basket CAGR | SPY CAGR | excess | basket × | SPY × |
|---|---|---|---|---|---|
| momentum (12-1) | 19.9% | 9.9% | +9.9% | 251.7× | 18.0× |
| mean-rev (RSI-2) | 22.5% | 9.9% | **+12.5%** | 487.1× | 18.0× |
| RS-short (63d) | 18.3% | 9.6% | +8.6% | 149.7× | 15.6× |
| RS-med (126d) | 19.9% | 9.6% | +10.2% | 221.9× | 15.6× |
| low-vol (63d) | 8.4% | 9.9% | −1.5% | 11.8× | 18.0× |

Best long-short = mean-rev(RSI-2)/21d, Sharpe 1.01, **DSR vs 10 variants = 0.908** (< 0.95).

Read: **reproduces the +12.5% RSI-2 long-only claim** and the momentum/RS "hold the leaders beat
SPY" result; low-vol loses. BUT: **current-S&P survivorship** (top-quintile is picked from *today's*
members, so dead names are pre-excluded), equal-weight, costless. In the market-neutral IC/long-short
lens only RSI-2 mean-reversion is individually significant (t≈6); momentum/RS are weak/negative
long-short — the long-only edge lives in the top quintile, not a neutral spread. (NB the script's own
banner mislabels the universe "insider-active (small-cap tilt)"; here it is actually the S&P-500 cache.)

## Verdict + what would reach "high"
- **Insider:** now SAVED + reproducible → off "unverified", but only MODEST (large-cap subset;
  21d t2.3 / 63d t2.9; DSR 0.79 < 0.95). To reach HIGH: price the full small/mid-cap event universe
  (needs a working, delisting-retaining price source) + trading costs + a defined multiple-testing set.
- **Families:** +12.5% (and the momentum/RS excesses) SAVED + reproduced, but **survivorship-inflated**.
  To reach HIGH: point-in-time S&P membership (remove survivorship) + costs. Until then: "leaders beat
  the index, with a survivorship tailwind of unknown size."

## Reproduce
Offline drivers override `_DATA` → `backtest/.insider_data` and price from `sp500_px.pkl`
(insider patched to price from the S&P cache). The committed scripts need: (a) `_DATA` repointed,
(b) a live price source for the small-cap universe. scipy required for DSR.
