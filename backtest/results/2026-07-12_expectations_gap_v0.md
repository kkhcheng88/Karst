# Expectations-Gap Valuation v0 — 2026-07-12

Script: `backtest/experiments/exp_expectations_gap_v0.py` (`python backtest/experiments/exp_expectations_gap_v0.py`)

## What this is (and isn't)

Mauboussin-style **expectations investing**, not Graham deep-value: the question is "how much future growth/performance is the current price already paying for," not "is this stock cheap in absolute terms." The headline number, **P_base@14x ("supercycle-free coverage")**, asks: if every one of these supercycle theses (AI/memory/space/rare-earth/etc.) never plays out and each business just prints its own **normalized, mid-cycle** operating earnings forever, what fraction of today's Enterprise Value does that boring baseline already justify? P_base >= 0.8 = the supercycle is basically a free option on top of a fairly-covered EV. P_base < 0.4 = most of the EV is a bet that the supercycle actually happens.

## Method

```
E_norm      = median(quarterly Operating Income / Total Revenue) x TTM revenue
NOPAT_norm  = E_norm x (1 - 0.21)
EV          = market_cap + net_debt   (net_debt = Total Debt - Cash&STI, latest quarter)
P_base      = NOPAT_norm x 14 / EV     (also reported @ 10x / 18x)
g_implied   = ((EV x 1.10^5) / (14 x NOPAT_norm)) ^ (1/5) - 1
```

Classification: P_base>=0.8 "supercycle 白送" / 0.4-0.8 "買緊部分希望" / <0.4 "大部分係希望" / E_norm<=0 "N/A-binary (option framing)".

Universe: top 1-2 expressive tickers per active theme in `thesis/themes.yaml` + 4 WATCH-only names (KALU/MCHP/AVT/PTEN).

## Summary

- 28/28 tickers computed successfully (0 failed -- see below).
- Classification split (of 28 OK): **14 大部分係希望** (mostly hope), 5 買緊部分希望 (partial hope), 2 supercycle 白送 (free lunch), 7 N/A-binary (option framing).
- 0 ticker(s) used the yfinance fallback (none -- defeatbeta covered all).
- 3 ticker(s) have <12 quarters of data (SNDK(10q), ASTS(10q), USAR(2q)).

## Theme-level rollup (15 active themes)

A theme's reading = the BEST P_base@14x among its expressive tickers (generous reading: if even the best-covered expression of the theme is mostly hope, the theme is). "N/A-binary" only when ALL the theme's computed tickers have E_norm <= 0.

| Theme | Best ticker | P_base@14x | Theme classification |
|---|---|---:|---|
| us-solar-manufacturing | FSLR | 0.83x | supercycle 白送 |
| specialty-siding-pricing-power | LPX | 0.75x | 買緊部分希望 |
| oil-gas-energy | XOM | 0.71x | 買緊部分希望 |
| gas-compression-equipment | USAC | 0.53x | 買緊部分希望 |
| advanced-packaging | AMKR | 0.37x | 大部分係希望 |
| glp1-biologics-packaging | WST | 0.32x | 大部分係希望 |
| tpu-custom-silicon | TSM | 0.32x | 大部分係希望 |
| aerospace-specialty-alloys | ATI | 0.25x | 大部分係希望 |
| memory-supercycle | MU | 0.21x | 大部分係希望 |
| euv-lithography-monopoly | ASML | 0.20x | 大部分係希望 |
| photonics-optical | COHR | 0.11x | 大部分係希望 |
| ai-power-grid | GEV | 0.01x | 大部分係希望 |
| semicap-equipment | AEHR | -0.01x | N/A-binary (option framing) |
| space-satellite | RKLB | -0.08x | N/A-binary (option framing) |
| rare-earth-materials | MP | -0.18x | N/A-binary (option framing) |

**Theme-level split (15 themes): 8 大部分係希望, 3 買緊部分希望, 3 N/A-binary (option framing), 1 supercycle 白送.**

## Full table (sorted by P_base@14x, descending)

| Theme | Ticker | EBIT margin (median) | E_norm | P_base@14x | P@10x | P@18x | g_implied(5y) | Classification | #Q | Source |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| WATCH | **AVT** | 3.3% | $818.0M | 0.89x | 0.64x | 1.15x | 12.5% | supercycle 白送 | 14 | defeatbeta |
| us-solar-manufacturing | **FSLR** | 31.5% | $1.71B | 0.83x | 0.60x | 1.07x | 14.1% | supercycle 白送 | 14 | defeatbeta |
| specialty-siding-pricing-power | **LPX** | 14.1% | $361.5M | 0.75x | 0.54x | 0.97x | 16.5% | 買緊部分希望 | 13 | defeatbeta |
| oil-gas-energy | **XOM** | 12.1% | $39.54B | 0.71x | 0.51x | 0.91x | 17.8% | 買緊部分希望 | 16 | defeatbeta |
| oil-gas-energy | **CVX** | 11.2% | $20.75B | 0.59x | 0.42x | 0.75x | 22.4% | 買緊部分希望 | 16 | defeatbeta |
| gas-compression-equipment | **USAC** | 30.1% | $326.8M | 0.53x | 0.38x | 0.68x | 24.9% | 買緊部分希望 | 16 | defeatbeta |
| WATCH | **KALU** | 4.6% | $168.7M | 0.51x | 0.36x | 0.66x | 25.8% | 買緊部分希望 | 13 | defeatbeta |
| advanced-packaging | **AMKR** | 8.0% | $566.5M | 0.37x | 0.26x | 0.47x | 34.5% | 大部分係希望 | 14 | defeatbeta |
| glp1-biologics-packaging | **WST** | 22.2% | $714.6M | 0.32x | 0.23x | 0.41x | 38.2% | 大部分係希望 | 15 | defeatbeta |
| tpu-custom-silicon | **TSM** | 48.8% | $62.34B | 0.32x | 0.23x | 0.41x | 38.5% | 大部分係希望 | 14 | defeatbeta (TWD→USD @0.0312) |
| aerospace-specialty-alloys | **ATI** | 13.2% | $605.4M | 0.25x | 0.18x | 0.32x | 45.3% | 大部分係希望 | 13 | defeatbeta |
| memory-supercycle | **MU** | 23.3% | $21.05B | 0.21x | 0.15x | 0.28x | 49.7% | 大部分係希望 | 13 | defeatbeta |
| euv-lithography-monopoly | **ASML** | 32.8% | $12.64B | 0.20x | 0.15x | 0.26x | 51.2% | 大部分係希望 | 13 | defeatbeta (EUR→USD @1.1419) |
| aerospace-specialty-alloys | **CRS** | 16.3% | $494.7M | 0.19x | 0.13x | 0.24x | 53.7% | 大部分係希望 | 13 | defeatbeta |
| tpu-custom-silicon | **AVGO** | 42.3% | $31.92B | 0.18x | 0.13x | 0.23x | 54.8% | 大部分係希望 | 14 | defeatbeta |
| advanced-packaging | **ASX** | 7.4% | $1.55B | 0.17x | 0.12x | 0.22x | 56.0% | 大部分係希望 | 15 | defeatbeta (TWD→USD @0.0312) |
| WATCH | **MCHP** | 17.1% | $804.4M | 0.17x | 0.12x | 0.21x | 57.4% | 大部分係希望 | 13 | defeatbeta |
| WATCH | **PTEN** | 1.3% | $61.7M | 0.15x | 0.11x | 0.20x | 60.4% | 大部分係希望 | 13 | defeatbeta |
| photonics-optical | **COHR** | 9.5% | $625.8M | 0.11x | 0.08x | 0.14x | 71.9% | 大部分係希望 | 13 | defeatbeta |
| memory-supercycle | **SNDK** | 9.1% | $1.20B | 0.05x | 0.03x | 0.06x | 102.5% | 大部分係希望 | 10 | defeatbeta |
| ai-power-grid | **GEV** | 1.0% | $380.2M | 0.01x | 0.01x | 0.02x | 155.8% | 大部分係希望 | 13 | defeatbeta |
| semicap-equipment | **AEHR** | -6.1% | -$2.8M | -0.01x | -0.01x | -0.02x | N/A | N/A-binary (option framing) | 13 | defeatbeta |
| ai-power-grid | **BE** | -4.4% | -$107.4M | -0.02x | -0.01x | -0.02x | N/A | N/A-binary (option framing) | 14 | defeatbeta |
| photonics-optical | **LITE** | -13.4% | -$334.0M | -0.06x | -0.04x | -0.08x | N/A | N/A-binary (option framing) | 14 | defeatbeta |
| space-satellite | **RKLB** | -47.4% | -$321.9M | -0.08x | -0.06x | -0.10x | N/A | N/A-binary (option framing) | 14 | defeatbeta |
| rare-earth-materials | **MP** | -55.6% | -$141.3M | -0.18x | -0.13x | -0.23x | N/A | N/A-binary (option framing) | 13 | defeatbeta |
| rare-earth-materials | **USAR** | -1114.9% | -$81.8M | -0.38x | -0.27x | -0.49x | N/A | N/A-binary (option framing) | 2 | defeatbeta |
| space-satellite | **ASTS** | -4510.2% | -$3.83B | -1.94x | -1.38x | -2.49x | N/A | N/A-binary (option framing) | 10 | defeatbeta |

## Caveats (read before trusting any number above)

1. **14x is a baseline assumption, not truth.** It approximates a no-growth, average-quality operating business capitalizing its NOPAT in perpetuity (~7% earnings yield). It is not calibrated per-sector or per-quality; that's why 10x/18x sensitivities are reported alongside -- treat P_base as a RANGE, not a point.
2. **EBIT margin is not stationary.** median(margin) across history smooths cyclicality but does NOT predict where margin normalizes to next cycle -- it's a backward-looking compromise, not a structural forecast.
3. **TTM revenue at a cycle peak inflates E_norm.** E_norm = median_margin x **TTM** revenue. If a name's current TTM revenue is itself cyclically elevated (e.g. a memory or commodity name mid-upcycle), E_norm overstates "normal" earning power even though the margin term is median-smoothed -- the revenue term isn't. This directly inflates P_base and understates how much hope is priced in. See the MU commentary below for a worked example of how to read this bias.
4. **Net debt is computed manually** (Total Debt − Cash&STI, latest balance-sheet quarter), NOT from defeatbeta's own "Net Debt" row -- that row is masked (`*`) or absent for a large share of this universe (MU, GEV, ASTS, AEHR, FSLR, WST, RKLB, USAR, TSM, ASML and others all showed a masked/missing Net Debt row on inspection). Total Debt and Cash rows were clean across the full universe.
5. **"Operating Income," not the "EBIT" row defeatbeta also exposes.** Spot-checked on XOM/MU: EBIT can run >25% above Operating Income for names with material non-operating income (e.g. equity-affiliate earnings) -- Operating Income keeps E_norm anchored to the core, controllable business.
6. **Data depth is short of the "ideal 28+ quarters" target** -- defeatbeta's quarterly_income_statement tops out at 16-17 quarter COLUMNS for large/established names (~4yr), and some quarters inside that window are masked (`*`), so USABLE quarters (what #Q counts) can be fewer still. Below the 12-quarter floor: SNDK (10q), ASTS (10q), USAR (2q). Fewer quarters = the median-margin estimate has seen fewer cycle phases and is less trustworthy -- USAR's 2 usable quarters in particular make its margin figure nearly meaningless (it lands in N/A-binary regardless).
7. **g_implied is undefined (N/A) whenever NOPAT_norm <= 0** -- for those names the market isn't pricing a growth rate off a normalized earnings base at all; it's pricing a binary/optionality outcome (hence the separate "N/A-binary" classification bucket, which should be read qualitatively, not compared numerically to the P_base scale).
8. **Currency alignment**: TSM/ASX report in TWD and ASML in EUR while their ADR market caps are USD. TTM revenue and net debt for those names are converted to USD at the SPOT FX rate on the run date (rate shown in the Source column) -- a spot conversion of a trailing-12m flow is itself an approximation, and FX moves add noise to their P_base that USD names don't have. (The first draft of this run SKIPPED this conversion and produced garbage for all three -- e.g. TSM P_base of -200x -- which is why the check exists.)
9. Raw EV/market-cap/margin inputs are a SNAPSHOT as of the day this script was run; re-running later will move the numbers (that's the point -- re-run to check whether the expectations gap has closed or widened).

## Special-focus commentary (5 tickers)

### USAC — thesis claims "cheapest / most-undiscovered" in the gas-compression theme

P_base@14x = **0.53x**, classification = **買緊部分希望**, EBIT margin(median) = 30.1%, g_implied = 24.9%, 16q data.

`thesis/themes.yaml` flags USAC at the **2nd percentile** of its own 3y ttm_pe history (~27.1x) — "全批候選入面估值最平" (cheapest across the whole candidate batch), i.e. a MULTIPLE-based (relative-to-own-history) cheap read. This P_base reading PARTLY confirms that framing: 53% of USAC's EV is covered by normalized operating earnings at a cycle-agnostic 14x NOPAT (full coverage would need ~26x), which puts it in the top tier of the supercycle-thesis names in this table -- so "cheapest in the batch" holds RELATIVELY. But note it is NOT the cheapest here in absolute coverage terms (AVT/FSLR/LPX/XOM/CVX all print higher P_base), and its balance sheet does the heavy lifting: net debt $2.98B vs $3.84B market cap means most of the EV is debt -- the equity is a leveraged slice of a well-covered asset, not a bargain on an unlevered basis.

### FSLR — 22nd percentile own-history ttm_pe

P_base@14x = **0.83x**, classification = **supercycle 白送**, EBIT margin(median) = 31.5%, g_implied = 14.1%, 14q data.

A 22nd-percentile ttm_pe (cheap-ish vs FSLR's own trading history) lines up with a P_base that also shows meaningful supercycle-free coverage -- the market isn't demanding much US-solar-manufacturing-thesis growth to justify today's EV; the base business (IRA-protected US module pricing) covers a large chunk of it on its own.

### ASML — 98th percentile own-history ttm_pe ("most-discussed semiconductor monopoly story")

P_base@14x = **0.20x**, classification = **大部分係希望**, EBIT margin(median) = 32.8%, g_implied = **51.2%** (5yr), 13q data.

Yes — g_implied of 51.2%/yr for 5 years is a demanding growth ask on top of an already-elevated base, consistent with the 98th-percentile ttm_pe: the EUV-monopoly narrative is fully in the price, and P_base confirms it -- only a 20% slice of EV is covered by normalized (non-growing) earnings power, the rest is a bet that ASML keeps compounding at a rate few monopoly franchises sustain for half a decade.

### ATI — 98th percentile own-history ttm_pe (aerospace specialty alloys)

P_base@14x = **0.25x**, classification = **大部分係希望**, EBIT margin(median) = 13.2%, g_implied = **45.3%** (5yr), 13q data.

Yes, similarly demanding: 45.3%/yr implied growth backs up the 98th-percentile ttm_pe read -- the aerospace-supply-chain-tightness thesis (narrowbody build-rate ramp, titanium/specialty-alloy bottleneck) has to keep delivering above-trend growth for 5 more years just to justify the current EV at a cycle-neutral 14x multiple; P_base of 0.25x means the bulk of the price is that forward bet, not today's normalized earnings.

### MU — TTM revenue at cycle peak (worked example of the E_norm inflation bias)

P_base@14x = **0.21x**, classification = **大部分係希望**, EBIT margin(median) = 23.3%, TTM revenue = $90.27B, g_implied = 49.7%, 13q data.

`thesis/themes.yaml` flags MU's `cycle_stage` as **late** with capex at 2.66x — a supply-response signal that a memory upcycle is maturing. MU's TTM revenue ($90.27B) is running near the TOP of its own multi-year range (the most recent quarters carry the heaviest weight in a trailing-12m sum), so E_norm = median_margin x TTM_revenue is being multiplied by a CYCLICALLY ELEVATED revenue base even though the margin term is itself median-smoothed across the cycle. **How to read this**: P_base as computed here is a BEST-CASE / upper-bound supercycle-free coverage reading for MU specifically -- if TTM revenue mean-reverts down toward a mid-cycle level (as it did in the 2022-2023 memory downturn, visible in the same quarterly series used above), true E_norm and hence true P_base would be LOWER than what's printed in the table. Do not read MU's P_base at face value the way you would for a name with a flatter revenue history (e.g. XOM, ASML) -- it embeds this peak-revenue bias by construction.
