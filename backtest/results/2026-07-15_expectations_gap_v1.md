# Expectations-Gap Valuation v1 — 2026-07-15

Script: `thesis/valuation.py` (`python thesis/valuation.py --run`). Production version of `backtest/experiments/exp_expectations_gap_v0.py` (2026-07-12 one-off run, kept as historical record). Spec: `docs/2026-07-12_valuation_expectations_gap_spec.md`.

## What this is (and isn't)

Mauboussin-style **expectations investing**, not Graham deep-value: the question is "how much future growth/performance is the current price already paying for," not "is this stock cheap in absolute terms." The headline number, **P_base@14x ("supercycle-free coverage")**, asks: if every one of these supercycle theses (AI/memory/space/rare-earth/etc.) never plays out and each business just prints its own **normalized, mid-cycle** operating earnings forever, what fraction of today's Enterprise Value does that boring baseline already justify? P_base >= 0.8 = the supercycle is basically a free option on top of a fairly-covered EV. P_base < 0.4 = most of the EV is a bet that the supercycle actually happens.

## Method (v1)

```
revenue_term = min(TTM revenue, 3yr median revenue)      <- v1's ONLY change vs v0
3yr median revenue = median(quarterly revenue, most recent min(12,available) qtrs) x 4
E_norm      = median(quarterly Operating Income / Total Revenue) x revenue_term
NOPAT_norm  = E_norm x (1 - 0.21)
EV          = market_cap + net_debt   (net_debt = Total Debt - Cash&STI, latest quarter)
P_base      = NOPAT_norm x 14 / EV     (also reported @ 10x / 18x)
g_implied   = ((EV x 1.10^5) / (14 x NOPAT_norm)) ^ (1/5) - 1
```

**v0 -> v1 change (the only one):** v0 used raw TTM revenue in E_norm, which v0's own caveats flagged as inflated for any name whose TTM revenue sits at a cycle peak (worked example: MU). v1 takes the CONSERVATIVE of TTM vs. a 3-year median revenue -- at a cycle peak the lower 3yr-median wins (damped); at a trough or flat history TTM wins unchanged. v1 can only be equal to or MORE conservative than v0, never less.

Classification: P_base>=0.8 "supercycle 白送" / 0.4-0.8 "買緊部分希望" / <0.4 "大部分係希望" / E_norm<=0 "N/A-binary (option framing)".

Universe: top 2 expressive tickers per active theme, read LIVE from `thesis/themes.yaml` (not a hardcoded snapshot) + 4 WATCH-only names (KALU, MCHP, AVT, PTEN).

## Summary

- 28/28 tickers computed successfully (0 failed -- see below).
- Classification split (of 28 OK): **14 大部分係希望** (mostly hope), 6 買緊部分希望 (partial hope), 1 supercycle 白送 (free lunch), 7 N/A-binary (option framing).
- 0 ticker(s) used the yfinance fallback (none -- defeatbeta covered all).
- 3 ticker(s) have <12 quarters of margin data (SNDK(10q), ASTS(10q), USAR(2q)).
- 22 ticker(s) had the v1 cycle-peak damp actually BIND (3yr-median revenue < TTM revenue, so v1's revenue term is lower than v0's would be): MU, SNDK, COHR, LITE, GEV, BE, AMKR, ASX, RKLB, ASTS, MP, AVGO, TSM, XOM, ATI, CRS, ASML, FSLR, USAC, WST, KALU, AVT.

## Theme-level rollup (15 active themes)

A theme's reading = the BEST P_base@14x among its expressive tickers (generous reading: if even the best-covered expression of the theme is mostly hope, the theme is). "N/A-binary" only when ALL the theme's computed tickers have E_norm <= 0.

| Theme | Best ticker | P_base@14x | Theme classification |
|---|---|---:|---|
| specialty-siding-pricing-power | LPX | 0.73x | 買緊部分希望 |
| oil-gas-energy | XOM | 0.68x | 買緊部分希望 |
| us-solar-manufacturing | FSLR | 0.66x | 買緊部分希望 |
| gas-compression-equipment | USAC | 0.47x | 買緊部分希望 |
| advanced-packaging | AMKR | 0.34x | 大部分係希望 |
| glp1-biologics-packaging | WST | 0.29x | 大部分係希望 |
| tpu-custom-silicon | TSM | 0.25x | 大部分係希望 |
| aerospace-specialty-alloys | ATI | 0.24x | 大部分係希望 |
| euv-lithography-monopoly | ASML | 0.18x | 大部分係希望 |
| photonics-optical | COHR | 0.09x | 大部分係希望 |
| memory-supercycle | MU | 0.08x | 大部分係希望 |
| ai-power-grid | GEV | 0.01x | 大部分係希望 |
| semicap-equipment | AEHR | -0.01x | N/A-binary (option framing) |
| space-satellite | RKLB | -0.05x | N/A-binary (option framing) |
| rare-earth-materials | MP | -0.16x | N/A-binary (option framing) |

**Theme-level split (15 themes): 8 大部分係希望, 4 買緊部分希望, 3 N/A-binary (option framing).**

## Full table (sorted by P_base@14x, descending)

| Theme | Ticker | EBIT margin (median) | E_norm | Revenue basis | P_base@14x | P@10x | P@18x | g_implied(5y) | Classification | #Q | Source |
|---|---|---:|---:|---|---:|---:|---:|---:|---|---:|---|
| WATCH | **AVT** | 3.3% | $758.0M | 3yr median (damped; TTM was 8% above 3yr median) | 0.84x | 0.60x | 1.07x | 14.0% | supercycle 白送 | 14 | defeatbeta |
| specialty-siding-pricing-power | **LPX** | 14.1% | $361.5M | TTM (already <= 3yr median; no damping needed) | 0.73x | 0.52x | 0.94x | 17.2% | 買緊部分希望 | 13 | defeatbeta |
| oil-gas-energy | **XOM** | 12.1% | $39.48B | 3yr median (damped; TTM was 0% above 3yr median) | 0.68x | 0.49x | 0.88x | 18.8% | 買緊部分希望 | 16 | defeatbeta |
| us-solar-manufacturing | **FSLR** | 31.5% | $1.30B | 3yr median (damped; TTM was 32% above 3yr median) | 0.66x | 0.47x | 0.84x | 19.7% | 買緊部分希望 | 14 | defeatbeta |
| oil-gas-energy | **CVX** | 11.2% | $20.75B | TTM (already <= 3yr median; no damping needed) | 0.57x | 0.41x | 0.73x | 23.1% | 買緊部分希望 | 16 | defeatbeta |
| gas-compression-equipment | **USAC** | 30.1% | $292.5M | 3yr median (damped; TTM was 12% above 3yr median) | 0.47x | 0.33x | 0.60x | 28.0% | 買緊部分希望 | 16 | defeatbeta |
| WATCH | **KALU** | 4.6% | $141.3M | 3yr median (damped; TTM was 19% above 3yr median) | 0.43x | 0.30x | 0.55x | 30.5% | 買緊部分希望 | 13 | defeatbeta |
| advanced-packaging | **AMKR** | 8.0% | $530.9M | 3yr median (damped; TTM was 7% above 3yr median) | 0.34x | 0.25x | 0.44x | 36.2% | 大部分係希望 | 14 | defeatbeta |
| glp1-biologics-packaging | **WST** | 22.2% | $663.9M | 3yr median (damped; TTM was 8% above 3yr median) | 0.29x | 0.21x | 0.38x | 40.6% | 大部分係希望 | 15 | defeatbeta |
| tpu-custom-silicon | **TSM** | 48.8% | $48.47B | 3yr median (damped; TTM was 28% above 3yr median) | 0.25x | 0.18x | 0.33x | 44.6% | 大部分係希望 | 14 | defeatbeta (TWD→USD @0.0311) |
| aerospace-specialty-alloys | **ATI** | 13.2% | $585.3M | 3yr median (damped; TTM was 3% above 3yr median) | 0.24x | 0.17x | 0.31x | 46.7% | 大部分係希望 | 13 | defeatbeta |
| euv-lithography-monopoly | **ASML** | 32.8% | $11.26B | 3yr median (damped; TTM was 12% above 3yr median) | 0.18x | 0.13x | 0.24x | 54.4% | 大部分係希望 | 13 | defeatbeta (EUR→USD @1.1442) |
| aerospace-specialty-alloys | **CRS** | 16.3% | $475.3M | 3yr median (damped; TTM was 4% above 3yr median) | 0.18x | 0.13x | 0.23x | 54.9% | 大部分係希望 | 13 | defeatbeta |
| WATCH | **MCHP** | 17.1% | $804.4M | TTM (already <= 3yr median; no damping needed) | 0.17x | 0.12x | 0.22x | 56.9% | 大部分係希望 | 13 | defeatbeta |
| advanced-packaging | **ASX** | 7.4% | $1.42B | 3yr median (damped; TTM was 9% above 3yr median) | 0.17x | 0.12x | 0.22x | 57.0% | 大部分係希望 | 15 | defeatbeta (TWD→USD @0.0311) |
| WATCH | **PTEN** | 1.3% | $61.7M | TTM (already <= 3yr median; no damping needed) | 0.15x | 0.10x | 0.19x | 61.6% | 大部分係希望 | 13 | defeatbeta |
| tpu-custom-silicon | **AVGO** | 42.3% | $24.51B | 3yr median (damped; TTM was 30% above 3yr median) | 0.14x | 0.10x | 0.18x | 62.3% | 大部分係希望 | 14 | defeatbeta |
| photonics-optical | **COHR** | 9.5% | $527.6M | 3yr median (damped; TTM was 19% above 3yr median) | 0.09x | 0.07x | 0.12x | 76.4% | 大部分係希望 | 13 | defeatbeta |
| memory-supercycle | **MU** | 23.3% | $7.82B | 3yr median (damped; TTM was 169% above 3yr median) | 0.08x | 0.06x | 0.10x | 82.6% | 大部分係希望 | 13 | defeatbeta |
| memory-supercycle | **SNDK** | 9.1% | $683.4M | 3yr median (damped; TTM was 75% above 3yr median) | 0.03x | 0.02x | 0.04x | 122.6% | 大部分係希望 | 10 | defeatbeta |
| ai-power-grid | **GEV** | 1.0% | $348.1M | 3yr median (damped; TTM was 9% above 3yr median) | 0.01x | 0.01x | 0.02x | 159.1% | 大部分係希望 | 13 | defeatbeta |
| ai-power-grid | **BE** | -4.4% | -$66.4M | 3yr median (damped; TTM was 62% above 3yr median) | -0.01x | -0.01x | -0.01x | N/A | N/A-binary (option framing) | 14 | defeatbeta |
| semicap-equipment | **AEHR** | -6.1% | -$2.8M | TTM (already <= 3yr median; no damping needed) | -0.01x | -0.01x | -0.02x | N/A | N/A-binary (option framing) | 13 | defeatbeta |
| photonics-optical | **LITE** | -13.4% | -$207.5M | 3yr median (damped; TTM was 61% above 3yr median) | -0.04x | -0.03x | -0.05x | N/A | N/A-binary (option framing) | 14 | defeatbeta |
| space-satellite | **RKLB** | -47.4% | -$216.8M | 3yr median (damped; TTM was 48% above 3yr median) | -0.05x | -0.04x | -0.07x | N/A | N/A-binary (option framing) | 14 | defeatbeta |
| space-satellite | **ASTS** | -4510.2% | -$180.4M | 3yr median (damped; TTM was 2023% above 3yr median) | -0.10x | -0.07x | -0.13x | N/A | N/A-binary (option framing) | 10 | defeatbeta |
| rare-earth-materials | **MP** | -55.6% | -$123.3M | 3yr median (damped; TTM was 15% above 3yr median) | -0.16x | -0.12x | -0.21x | N/A | N/A-binary (option framing) | 13 | defeatbeta |
| rare-earth-materials | **USAR** | -1114.9% | -$81.8M | TTM (3yr median unavailable -- too few revenue-window quarters) | -0.39x | -0.28x | -0.50x | N/A | N/A-binary (option framing) | 2 | defeatbeta |

## Solvency 閘讀數(槓桿/利息覆蓋)

判決:`backtest/results/2026-07-15_solvency_gate_probe.md`(GO-as-gate 條件版)—— solvency 差單獨冇跑輸料,但「pe 平(自身歷史分位 ≤20)∧ solvency 爆」126d excess -14.9%(vs pe_low alone -2.9%);「solvency 爆但唔平」反而 +3.9%,證明無條件 gate 會錯殺(USAC 動機案例:淨負債 \$2.98B、睇落全場最平但槓桿股權切片)。所以呢度**只讀數同旗標**,唔喺 valuation 呢層做否決——真正「只對 pe-cheap 買入候選降級」嘅邏輯喺 `thesis/dashboard_render.py` 嘅 `pick_ticker`(揀 ticker 嗰步)先做。閾值:NetDebt/EBITDA > 4x 或 EBITDA≤0,OR EBIT/利息支出 < 2x。金融股(銀行/保險)跳過,對佢哋呢兩條比率無意義。

**11 隻名槓桿或利息覆蓋爆錶**(睇落平未必真係平,可能係槓桿假象——業務語言:「睇落平但槓桿爆錶」):

| Ticker | 主題 | NetDebt/EBITDA | EBIT/利息覆蓋 |
|---|---|---:|---:|
| **AEHR** | semicap-equipment | EBITDA≤0 | n/a |
| **ASTS** | space-satellite | EBITDA≤0 | -10.55x |
| **ASX** | advanced-packaging | 32.98x | 8.22x |
| **AVT** | WATCH | 4.32x | 2.30x |
| **BE** | ai-power-grid | 4.06x | 1.26x |
| **MCHP** | WATCH | 4.49x | 2.27x |
| **MP** | rare-earth-materials | -25.02x | -2.09x |
| **PTEN** | WATCH | 1.08x | -0.90x |
| **RKLB** | space-satellite | EBITDA≤0 | -7.39x |
| **USAC** | gas-compression-equipment | 4.75x | 1.72x |
| **USAR** | rare-earth-materials | EBITDA≤0 | -648.63x |

## v0 -> v1 classification changes

Baseline: `2026-07-12_expectations_gap_v0.md` (2026-07-12 snapshot). **Caveat: a classification change can reflect BOTH the v1 revenue-conservatism formula change AND ordinary market/price movement between the v0 snapshot date and today** -- the "revenue basis" and "reason" columns below distinguish which applies per ticker (only rows where the 3yr-median damp actually bound are attributable to the formula change).

**1 ticker(s) changed classification bucket:**

| Ticker | v0 classification | v1 classification | v1 revenue basis | Reason |
|---|---|---|---|---|
| FSLR | supercycle 白送 | 買緊部分希望 | 3yr median (damped; TTM was 32% above 3yr median) | revenue term now min(TTM, 3yr median) -- damps cycle-peak E_norm inflation |

## Caveats (read before trusting any number above)

1. **14x is a baseline assumption, not truth.** 10x/18x sensitivities are reported alongside -- treat P_base as a RANGE, not a point.
2. **EBIT margin is not stationary.** median(margin) across history smooths cyclicality but does NOT predict where margin normalizes to next cycle.
3. **v1's revenue-conservatism fix has its own limits.** "3-year median revenue" is median(quarterly revenue) x 4 over whatever is available up to 12 quarters -- for thin-history names (<12 quarters, e.g. recent IPOs) the window isn't really 3 years, and the median itself is noisier the fewer quarters it's drawn from. min(TTM, 3yr median) is a DAMPING heuristic, not a structural forecast of where revenue normalizes.
4. **Net debt is computed manually** (Total Debt − Cash&STI, latest balance-sheet quarter), NOT from defeatbeta's own "Net Debt" row (frequently masked/absent).
5. **"Operating Income," not the "EBIT" row defeatbeta also exposes** -- keeps E_norm anchored to the core, controllable business (v0 caveat, spot-checked on XOM/MU).
6. **Data depth**: defeatbeta's quarterly_income_statement tops out at 16-17 quarter COLUMNS for large/established names (~4yr); some quarters are masked. Below the 12-quarter margin floor: SNDK(10q), ASTS(10q), USAR(2q).
7. **g_implied is undefined (N/A) whenever NOPAT_norm <= 0** -- those names are priced as a binary/optionality outcome, not off a normalized growth rate (hence the separate "N/A-binary" bucket, read qualitatively, not numerically comparable to P_base).
8. **Currency alignment**: non-USD reporters (TSM/ASX in TWD, ASML in EUR) are FX-converted at the SPOT rate on the run date -- a spot conversion of a trailing flow is itself an approximation.
9. **This is a SNAPSHOT** as of the run date -- re-run to check whether the expectations gap has closed or widened. NOT a timing tool: it answers "what's priced in," not "when does it re-rate" (that's cycle_stage + constraint-language's job).
10. **Universe is read live from themes.yaml** -- if a theme's ticker list or the 15-theme registry changes, this report's ticker set and theme count change with it (unlike v0, which was a frozen hardcoded snapshot).
