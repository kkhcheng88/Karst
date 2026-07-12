# Insider P0-c revisit: owners-breadth (Lynch) + market-wide sell/buy ratio (Chancellor/Marathon)

**Date:** 2026-07-11
**Trigger:** insider P0-c (SEC Form 4 → thesis confidence) has sat parked in backlog since it was
first flagged (`conf_eff` computed but never wired into `expression.py`). Reading Peter Lynch's
*Beating the Street* and Edward Chancellor's *Capital Returns* surfaced two untested angles on the
same underlying data. This note backtests both, honestly, before deciding whether P0-c should move.

**Scripts:** `backtest/experiments/exp_insider_breadth.py` (Task 1),
`backtest/experiments/exp_insider_market_ratio.py` (Task 2). Both reuse the SEC bulk Form 345
archive already cached offline in `backtest/.insider_data` (2006q1-2025q2, 78 quarters) — no re-pull.

**Bottom line: neither angle survives scrutiny. insider P0-c stays parked.**

---

## 0. Data-quality bug found and fixed (applies to BOTH tasks, and is a latent repo-wide issue)

Before any of the numbers below can be trusted, a real bug had to be fixed. The SEC bulk Form 345
data set has rare **fat-finger filings** — individual Form 4 rows with a mis-keyed
`TRANS_PRICEPERSHARE`. Example: accession `0001125282-06-002179` (ticker LCC, filed 2006-04-11) has
a recorded price of **$67,550,000/share**, turning one transaction into a **$118 trillion** "buy".
Neither this repo's existing `exp_insider_validate.py` nor an initial draft of the new Task 2 script
had any sanity check on per-transaction price/value, so a raw dollar SUM (Task 2's market-wide
aggregate) or a dollar VALUE used in a regression (Task 1's confound-control OLS) can be blown up by
a handful of bad rows out of millions. Concretely, before the fix:

- Task 2's April-2006 anecdote check showed `buy$375,782,098M` (~$375 **trillion** in one month) —
  obviously impossible, and it flipped the sign of that whole month's ratio.
- Task 2's baseline NW-regression showed "significant" 3m/6m t-stats of +2.18/+2.68 — driven by
  these outliers inflating `log(sb_ratio)` in specific months.
- Task 1 had 149/9,997 matured events with `value > $10B` (max $34.6 **quadrillion**, ticker AGO,
  2008-04) feeding into `log10(value)` in the OLS confound-control regression.

**Fix applied (both scripts, via a local monkeypatch of the transaction loader — the shared,
already-validated `exp_insider_validate.py` was left untouched):** drop transactions with
implausible per-share price (>$2,000,000 — generous, above even BRK.A) or implausible single-row
dollar value (>$10B for Task 2's raw P/S stream; >$1B for Task 1's purchase-only stream). This
dropped roughly 5-250 rows per quarter (out of tens of thousands) — a small fraction of rows, but
with an outsized effect on dollar-sum statistics. **All numbers in this report are POST-FIX.**

**Action item for the project (not fixed here, flagged for later):** any other experiment in
`backtest/experiments/` that sums, regresses on, or log-transforms the raw `value` field from
`exp_insider_validate.build_events()` should be revisited for the same contamination. The
already-validated PRICE-return t-stats (e.g. the "21d t=5.12" full-universe finding referenced in
`.agents/KARS_MEMORY.md`) are unaffected since they don't depend on the dollar value field, but any
$-value bucketing/regression elsewhere may be.

---

## Task 1 — Owners-breadth (Lynch's graded-conviction hypothesis)

**Question:** Lynch: "7 vice presidents buying 1,000 shares each is more bullish than 1 president
buying 5,000 shares." `exp_insider_validate.build_events()` already collapses this to a binary
`owners>=2` threshold. Does forward return actually scale with the owners COUNT, net of the dollar
value confound (bigger clusters tend to also be bigger $, and bigger companies have more officers)?

**Data:** `IV.build_events()`, 2006q1-2025q2, cluster threshold owners≥2 & $≥500k (unchanged from the
validated pipeline) → 18,631 cluster events / 6,714 tickers post data-quality filter; 9,963 matured
with a priced forward return. Forward excess return vs SPY at 21d/63d/126d (`IV._HOR` convention).

### 1. Owners bucket × forward excess vs SPY

| bucket | n | median $value | median mcap | 21d mean/t | 63d mean/t | 126d mean/t |
|---|---|---|---|---|---|---|
| owners=2 | 3,769 | $1,415k | $1.51B | +1.31% / t=4.22 | +1.73% / t=3.17 | +1.87% / t=2.08 |
| owners=3-4 | 2,737 | $1,229k | $0.65B | +2.53% / t=6.75 | +2.10% / t=3.26 | +1.90% / t=1.42 |
| owners≥5 | 3,457 | $2,741k | $0.50B | +2.59% / t=7.36 | +4.51% / t=6.79 | +6.21% / t=4.82 |

At face value this looks like a breadth premium, especially at 63d/126d. But note: **median market
cap FALLS as owners count rises** (1.51B → 0.65B → 0.50B) — the opposite of the naive intuition that
bigger companies have more officers to generate a high owner-count. This already smells like the
known micro-cap tail (documented in KARS_MEMORY: the insider 21d "t=5.12" finding was traced to a
full-universe micro-cap tail), not a genuine breadth signal.

### 2. Monotonicity — does it actually scale with owners count, or just step at "≥3"?

Spearman corr(raw owners count 2..650, forward excess):

| horizon | rho | p | read |
|---|---|---|---|
| 21d | +0.019 | 0.056 | borderline, tiny effect size |
| 63d | +0.009 | 0.346 | not significant |
| 126d | -0.002 | 0.852 | not significant, wrong sign |

**No graded, monotonic relationship across the full owners range.** Lynch's precise "more insiders =
more bullish, continuously" does not hold. What survives (barely) is a coarse step: "≥3 distinct
insiders" beats "exactly 2" — not a continuum.

### 3. Confound control

**3a. Owners vs $value correlation:** Spearman = +0.123 (p<0.0001, n=9,963) — real but weak; owners
buckets are only mildly $-bigger, so dollar value alone doesn't explain the bucket pattern.

**3b. Value-quartile × owners(2 vs ≥3) double sort, 21d excess:**

| value quartile | owners=2 (n, mean%, t) | owners≥3 (n, mean%, t) |
|---|---|---|
| Q1 (small $) | 810, +1.38%, t=2.37 | 1,681, +2.07%, t=4.39 |
| Q2 | 1,190, +1.21%, t=2.50 | 1,301, +2.42%, t=4.56 |
| Q3 | 1,122, +1.38%, t=2.26 | 1,368, +2.90%, t=5.68 |
| Q4 (large $) | 647, +1.28%, t=1.41 | 1,844, +2.86%, t=5.46 |

Owners≥3 beats owners=2 in **every** value quartile — so the step-effect is not purely a $-value
proxy. This is the strongest piece of evidence FOR a genuine breadth effect in the whole study.

**3c. OLS: forward excess ~ log2(owners) [+ log10(value)] [+ log10(mcap)]** (the decisive test):

| horizon | (a) owners alone | (c) owners + value | (d) owners + value + mcap |
|---|---|---|---|
| 21d | t=+2.30 | t=+2.10 | **t=+0.42** (mcap t=-7.20***) |
| 63d | t=+2.02 | t=+2.36 | **t=+0.31** (mcap t=-5.90***) |
| 126d | t=+1.55 (ns) | t=+1.96 | **t=-0.24** (mcap t=-8.48***, wrong sign) |

**This is the key result.** Owners' significance survives controlling for dollar value alone (3c),
but **collapses to statistical zero at every single horizon once market cap is added** (column d),
while market cap itself stays strongly, consistently significant (smaller cap → bigger forward
excess — the already-known micro-cap effect). Mechanism: high-owner-count clusters occur
disproportionately at *smaller* companies (likely because many small/micro caps run broad-based
officer stock-purchase programs that mechanically generate multiple simultaneous Form-4 purchases),
so "owners count" is really a noisy, inverted proxy for small-cap membership — not independent
information about conviction.

### Task 1 verdict

**No independent breadth edge.** The double-sort (3b) initially looked like a genuine marginal
effect, but the full regression (3c/3d) shows it is fully absorbed by market cap: once you control
for the company being small, "how many insiders bought" adds nothing. Combined with the failed
monotonicity test (§2), Lynch's graded-conviction thesis does not hold up in this dataset. This
extends KARS_MEMORY's existing "insider群買已陰性" finding to the breadth-graded version specifically
— same negative conclusion, now including the confound-control step that hadn't been run before.

---

## Task 2 — Market-wide $ sell/buy ratio (Chancellor/Marathon macro-timing)

**Question:** Marathon Asset Management (via Vickers-style data) reportedly saw ~16:1 market-wide
insider sell:buy ($) near the 2006-07 top and ~2:1 near the Oct-2008 bottom. Does a SEC-bulk-built
version of this ratio predict forward SPY returns?

**Data:** ALL open-market Form-4 purchases (code P, disposition A) and sales (code S, disposition D)
market-wide (not per-ticker), NONDERIV_TRANS only, aggregated to monthly $ sums by FILING_DATE (not
trade date — look-ahead-safe; a Form 4 is public within ~2 business days of the trade, so a live
pipeline could compute this same-day. The SEC BULK research file used here lags 1-2 quarters in
*publication*, which matters for a live deployment but not for this backtest's statistical read).
2006-01 to 2025-06, 234 months, post data-quality filter: 4,154,983 raw P/S rows (1,190,586 buys /
2,964,397 sells).

`sb_ratio = $sold / $bought`. Distribution (clean): min=0.08, p10=0.83, **median=6.45**, p90=27.96,
max=141.30. Median well above 1 is expected/structural — routine RSU-vesting and diversification
sales vastly outnumber open-market purchases in a normal month; the interesting question is whether
*extremes relative to this baseline* predict SPY, not the absolute level.

### 1. Anecdote spot-check (known market top/bottom months)

| month | sb_ratio ($) | sb_ratio (count) | buy$ / sell$ | Marathon's claim |
|---|---|---|---|---|
| 2006-04 | 3.90 | 5.26 | $9,091M / $35,435M | ~16:1 near 2006-07 top |
| 2008-10 | 0.37 | 0.76 | $16,708M / $6,155M | ~2:1 near GFC bottom |
| 2009-03 | 0.72 | 0.68 | $14,418M / $10,387M | (SPX absolute bottom) |
| 2020-03 | 0.54 | 0.83 | $25,804M / $13,823M | (COVID crash bottom) |

The **buying-extreme / bottom side replicates**: all three known market-bottom months (2008-10,
2009-03, 2020-03) show sb_ratio well below the 6.45 median — i.e. insiders really were buying more
(relative to selling) than normal at all three lows. The **selling-extreme / top side does not
replicate** at the specific month Chancellor cites: our April-2006 reading (3.90) is actually *below*
the historical median, the opposite of "extreme selling." (Possible explanations: different universe
or smoothing vs the original Vickers data, or the true SPX top was Oct-2007 — 18 months later — so a
April-2006 reading may be a very early, noisy lead rather than a precise top-timer even in the
original anecdote.)

### 2. Formal test: does it actually predict SPY forward returns?

**Newey-West HAC regression** (forward SPY return ~ log(sb_ratio), HAC lag = horizon in months, to
correct for the fact that overlapping monthly-sampled 3/6/12-month forward windows are highly
autocorrelated and plain OLS t-stats would overstate significance):

| horizon | n | R² | slope | NW-t |
|---|---|---|---|---|
| 3m | 234 | 0.005 | +0.0042 | **+0.68** |
| 6m | 234 | 0.007 | +0.0071 | **+0.70** |
| 12m | 234 | 0.007 | +0.0100 | **+0.56** |

No horizon clears even the loose |t|>2 bar; R² is essentially zero. (Sign is even the "wrong" way —
more selling weakly associated with slightly *higher* forward returns — but since none of this is
significant, the sign isn't meaningful either.)

**Decile test** (top decile = most selling / most bearish-predicted, bottom decile = most buying /
most bullish-predicted, n=24 months each):

| horizon | top-decile fwd | bottom-decile fwd | middle-80% fwd | diff t | p |
|---|---|---|---|---|---|
| 3m | +3.11% | +3.20% | +2.31% | +0.03 | 0.978 |
| 6m | +6.22% | +5.69% | +4.76% | -0.12 | 0.907 |
| 12m | +12.57% | +11.85% | +9.81% | -0.12 | 0.901 |

No meaningful difference between the extreme-selling and extreme-buying months at any horizon.

**Robustness — transaction-COUNT ratio** (guards against a handful of billionaire-executive sales
dominating the $ aggregate): shows a weak hint in the *hypothesized* direction — bottom-decile
(most buying by count) beats top-decile at 12m (t=+1.80, p=0.081) — but this is (a) not significant
at conventional 5%, (b) inconsistent with the $ version showing nothing, and (c) one favorable
result out of roughly 18 tests run across this report, well within what multiple testing alone would
produce by chance.

**Robustness — excluding 10b5-1 scheduled sales** (flag only populated 2023q1+, so this mainly
affects the last ~2.5 years): results essentially unchanged from baseline at every horizon — as
expected given how little of the 19.5-year sample the flag actually touches.

**Robustness — 3-month smoothing** (real-world Vickers-style trackers typically smooth rather than
use a raw single-month reading): smoothing does NOT rescue the signal — NW-t drops further (3m
+0.41, 6m +0.37, 12m +0.41) and decile differences stay small and non-significant.

### Task 2 verdict

**No statistically robust predictive power**, despite a genuinely interesting qualitative match at
the three well-known market-bottom episodes tested (2008-10, 2009-03, 2020-03). Three anecdotal hits
out of a 234-month sample with only a handful of true regime extrema is not distinguishable from
chance, and every formal test (HAC regression, decile split, count-based robustness, smoothing) run
across three horizons and two sample definitions (with/without 10b5-1) confirms it: nothing clears
significance except one borderline count-ratio result (p=0.081) that doesn't survive the multiple-
testing exposure of this report. The signal does NOT replicate as a systematic macro-timing tool.

---

## Overall conclusion and recommendation

| angle | edge found? | mechanism if any |
|---|---|---|
| Task 1: owners-breadth (Lynch) | **No.** Apparent effect is fully absorbed by market cap in OLS (t collapses from ~2.3 to ~0.3-0.4 at every horizon once mcap is controlled) | Mislabeled micro-cap effect, not breadth |
| Task 2: market-wide $ sell/buy ratio (Chancellor/Marathon) | **No.** Fails HAC regression, decile test, and smoothing robustness at all 3 horizons | Qualitative match at 3 known bottoms doesn't survive as a systematic predictor |

**insider P0-c (SEC Form 4 → thesis confidence) stays parked.** Both literature-motivated angles
tested here were genuinely new (neither the binary-threshold per-ticker signal nor a market-wide
timing overlay had been tried before), and both were tested honestly with the project's standard
discipline (t-stats, hit rates, confound control, robustness checks, comparison to a null) rather
than stopping at a favorable-looking raw pattern. Neither survives. This is consistent with — and
extends — the existing KARS_MEMORY finding that insider cluster-buy signals are net negative/flat
for this project's purposes once proper controls are applied.

**One genuine byproduct worth keeping:** the data-quality bug found in §0 (unfiltered fat-finger SEC
Form 345 rows corrupting raw dollar-value aggregates) is real and should be ported into
`exp_insider_validate.py` itself (or any downstream script using its `value` field) the next time
that file is touched, even though it didn't end up changing this report's qualitative conclusions.

**Artifacts:**
- `backtest/experiments/exp_insider_breadth.py` — Task 1 script (owners-bucket, monotonicity,
  double-sort, OLS confound control)
- `backtest/experiments/exp_insider_market_ratio.py` — Task 2 script (market-wide $ ratio builder,
  Newey-West HAC regression, decile test, robustness checks)
- `backtest/experiments/_market_ratio_monthly.csv`,
  `backtest/experiments/_market_ratio_monthly_excl10b51.csv` — saved monthly time series (date,
  buy/sell $ and count, sb_ratio, forward SPY returns) for future reuse without re-running the
  78-quarter load

---

## 2026-07-11 追加:market-cap tier breakdown(P0-c 方法論漏洞覆核)

**觸發:** 用戶對 Task 1 §3c/3d 提出一個尖銳嘅方法論質疑——pooled OLS(全部事件一齊 control market
cap)一加 `log10(mcap)`,owners 嘅 t 值就由 ~2.3 跌到 0.3-0.4。但呢個 pooled regression 淨係答到
「攞走成個樣本嘅**平均**市值效應之後,owners 仲有冇獨立解釋力」,唔係「喺某一個 size tier 入面,
owners 數目本身仲有冇用」。如果 breadth 效應本身係 **tier-specific**(只喺細價股先存在——正正係
KARS_MEMORY 一直記低嘅教訓:insider edge 成日喺細價股),一個 pooled 嘅 mcap control 會將
「tier-specific 效應」同「純粹大細影響」混埋一齊,一齊 regress 走。呢節將**同一批**已經做咗
data-quality fix 嘅 9,963 個 matured cluster events(owners>=2 & $>=500k,2006q1-2025q2,唔重新
pull data)按 market cap 分 tier,喺**每個 tier 入面獨立**再做返 Task 1 嗰套測試(bucket table、
monotonicity、owners=2 vs >=3 step test),仲加多一層 Task 1 冇做過嘅嘢:**within-tier OLS**(連
tier 入面殘餘嘅連續 mcap 都控埋),先算最嚴謹嘅覆核。

**Script:** `backtest/experiments/exp_insider_breadth_mcaptier.py`(`import exp_insider_breadth as B`
reuse `B.build()`——同一個 data-quality monkeypatch、同一批事件,冇重新處理)。

**Tier 邊界:** 跟返 `exp_insider_mktcap.py` 已有嘅切法(方便同項目過往研究對照)——
micro <$300M / small $300M-2B / mid $2B-10B / large >=$10B。另外加一個 4 等分 quantile 切法做
robustness check,確認結論唔係「啱啱好揀中呢組邊界先出現」。

**Mcap 覆蓋率(誠實列出嘅 limitation):** 9,963 個 matured events 之中,8,165 個(82.0%)配到
defeatbeta 嘅 point-in-time market cap,1,798 個(18.0%)因為隻 ticker 冇 mcap 覆蓋而剔除——
defeatbeta 嘅 mcap 覆蓋率本身只有 2,736/6,714 = 40.7% tickers,傾向覆蓋仍然上市/較主流嘅公司。
呢個可能令樣本輕微向「仍然存活、較大」嘅名傾斜,即係**最細、最有可能出現真訊號嘅一批 nano-cap 有可能
被系統性剔除**——呢個 limitation 冇修正,列出嚟俾之後嘅人知。另外,large tier 嘅 mcap 最大值出現
$74,003,488M(=$74 兆)一個顯然係 defeatbeta market-cap 數據入面嘅錯誤點(冇任何公司試過 $74 兆市值,
Apple 歷史高位都只係 ~$3-4 兆)——同 §0 講嘅 fat-finger 交易記錄係同一類問題,但呢度只影響 large tier
嘅顯示範圍,唔影響任何 tier 邊界劃分或者排序統計,冇特別處理。

### Tier 分佈

| tier | n(有 mcap) | % of 8,165 | median mcap | mcap 範圍 |
|---|---|---|---|---|
| micro <$300M | 2,436 | 29.8% | $118M | $0-300M |
| small $300M-2B | 3,023 | 37.0% | $755M | $301M-$2.0B |
| mid $2B-10B | 1,776 | 21.8% | $3,746M | $2.0B-$10.0B |
| large >=$10B | 930 | 11.4% | $27,792M | $10.0B+ |

每個 tier 樣本量都足夠(930-3,023),就算最細嗰個(large-cap,n=930)都遠超 60 嘅「至少夠睇」門檻——
呢節嘅結論唔係「樣本太少睇唔到」嘅問題。

### 每個 tier 入面嘅三層測試(21d/63d/126d)

**Micro <$300M(n=2,436)—全份分析入面表面上最有希望嘅一個 tier:**

| bucket | 21d mean/t | 63d mean/t | 126d mean/t |
|---|---|---|---|
| owners=2 (n=616) | +2.63% / t=2.37 | +3.42% / t=1.81 | +7.89% / t=2.19 |
| owners=3-4 (n=753) | +4.92% / t=5.53 | +6.35% / t=3.93 | +10.69% / t=2.74 |
| owners>=5 (n=1,067) | +4.51% / t=5.82 | +8.37% / t=5.51 | +16.01% / t=4.61 |

Bucket table 睇落**清楚單調遞增**(尤其 63d/126d),遠比 pooled 全樣本嗰個更乾淨。但:

- **Monotonicity (Spearman):** 21d rho=+0.030 (p=0.137, ns);63d rho=+0.041 (p=0.043,勉強顯著);
  126d rho=+0.045 (p=0.025,顯著)。方向啱、但效應量細(rho<0.05)。
- **owners=2 vs >=3 step test:** 21d t=+1.63 (p=0.103);63d t=+1.88 (p=0.061,貼近顯著);
  126d t=+1.33 (p=0.184)。全部未過 5% 門檻。
- **決定性測試——within-tier OLS(連 log10(mcap) 都控埋,即係「喺 <$300M 呢個 tier 入面,
  仲細嘅公司 vs 仲大嘅公司」呢層殘餘 size 效應):**

  | horizon | owners coef | owners t | log10(mcap) coef | log10(mcap) t |
  |---|---|---|---|---|
  | 21d | +0.00077 | **t=+0.15** | -0.02698 | t=-2.17 |
  | 63d | +0.00668 | **t=+0.68** | -0.03170 | t=-1.38 |
  | 126d | +0.01431 | **t=+0.66** | -0.30340 | t=-5.94*** |

  一加返連續 mcap control,owners 嘅 t 就由 bucket table 睇落好似顯著嘅樣,跌返落 0.15-0.68(全部
  ns)。而 `log10(mcap)` 本身**仍然強顯著**(126d t=-5.94)——即係話就算窄到 <$300M 呢個 tier,
  裡面依然存在一個連續嘅「越細越好」殘餘效應,而 owners count 只不過係呢個殘餘 size 效應嘅
  **另一個 noisy proxy**(高 owners 數嘅事件喺 tier 入面都傾向揀中果批更細嘅公司)——同 pooled
  版本搵到嘅機制一模一樣,只係喺更細嘅粒度重演多一次。

**Small $300M-2B(n=3,023):** owners=3-4 喺 63d/126d 甚至跌到 owners=2 之下(126d mean=-0.98%,
方向反轉),monotonicity 21d rho=+0.036 (p=0.050,貼近但唔穩),63d/126d 完全唔顯著(p=0.84,
p=0.79)。Step test 三個 horizon 全部 ns,63d/126d 仲反晒號。OLS(d) owners t 由 +1.17(21d)跌到
-0.33(63d)、+0.09(126d)——冇一致方向,冇信號。

**Mid $2B-10B(n=1,776):** 全部指標貼近零、方向唔一致(bucket mean 21d/63d/126d 喺 owners
buckets 之間冇單調趨勢;monotonicity rho -0.03 至 +0.01,全部 p>0.19;step test t 全部 <1.1;
OLS(d) owners t 介乎 -1.12 至 +0.74)。冇信號。

**Large >=$10B(n=930):** 方向**反晒轉**——owners 越多,forward excess 越差:owners>=5 嘅
126d mean=**-4.43%**(t=-2.12,單一 bucket 入面全報告最「顯著」嘅一個數,但方向係負)。
Monotonicity 三個 horizon 全部負(rho -0.02 至 -0.04),全部 ns。Step test 全部 ns(21d t=-1.20,
63d t=+0.00,126d t=-1.15)。OLS(d) owners t 全部負或近零(-1.54, -0.55, -1.22)。呢個「大價股
insider 群買越多越差」嘅方向性提示幾有趣,但 owners>=5 呢個 sub-bucket 喺 large tier 淨係
n=155,加上呢係成份報告 48 個統計測試入面嘅其中一個,單一 t=-2.12 完全喺 multiple-testing 嘅
noise 範圍之內——列出嚟做觀察,唔當結論用。

### Robustness check:market-cap quantile(4 等分,唔用固定 $ 邊界)

| quartile | mcap 範圍 | 21d step t/p | 63d step t/p | 126d step t/p |
|---|---|---|---|---|
| Q1(小,n=2,042) | $0-234M | t=+1.44, p=0.150 | t=+1.96, p=0.050 | t=+1.22, p=0.224 |
| Q2 (n=2,041) | $234-813M | t=+1.22, p=0.223 | t=-1.22, p=0.222 | t=-0.13, p=0.901 |
| Q3 (n=2,041) | $813M-3.18B | t=+0.23, p=0.820 | t=-0.22, p=0.824 | t=-1.50, p=0.133 |
| Q4(大,n=2,041) | $3.19B+ | t=+0.16, p=0.873 | t=+0.50, p=0.620 | t=-0.51, p=0.607 |

同固定邊界嘅 tier 結果完全一致:**只有最細嗰組(Q1)有方向性提示**(63d 貼近顯著,p=0.050),
其餘三組完全冇信號。呢個 robustness check 確認結果唔係因為 `exp_insider_mktcap.py` 嗰組固定
邊界揀得剛好先出現。

### Multiple-testing exposure

呢節一共跑咗 4 tiers × 3 horizons × 3 tests(bucket/step/OLS)+ 4 quantiles × 3 horizons(step)
= **48 個統計測試**。5% 顯著水平下,純粹靠運氣都預期會有 ~2.4 個「顯著」讀數。實際觀察到嘅
「顯著」讀數(micro tier rho@63d p=0.043、rho@126d p=0.025;small tier rho@21d p=0.050 貼近;
Q1 step@63d p=0.050 貼近;large owners>=5@126d t=-2.12)數量、強度都同 multiple-testing 底下
純噪音預期一致——而且**冇一個喺加返 within-tier mcap control 之後仲存活**。呢個「單變量偶爾中,
多變量控制後即刻消失」嘅 pattern,正正係殘餘 size 假象嘅特徵,唔係真訊號嘅特徵(真訊號應該喺
control 之後仍然有實質、方向一致嘅顯著性,即使強度打咗折)。

### 本節結論

**連分 tier 都搵唔到獨立、經得起 confound control 嘅 owners-breadth edge。** 表面上最有希望嘅
micro <$300M tier(以及對應嘅 quantile Q1)喺原始 bucket table 睇落單調遞增、Spearman rho 喺
63d/126d 名義上顯著,但**呢啲全部係表面訊號**——一加返 within-tier 嘅連續 market-cap control,
owners 嘅 OLS t 值即刻跌返落 0.15-0.68(全部 ns),而殘餘嘅 log10(mcap) 效應仍然強顯著。結論同
Task 1 pooled 版本嘅機制一致,只係喺更細嘅粒度證實多一次:owners count 唔係獨立信息,係
size(而且係喺 tier 入面都仲存在嘅連續 size)嘅 noisy proxy。

### 對 P0-c 嘅建議(更新)

**Task 1 嘅原結論不變,而且經呢次 tier 覆核進一步強化。** 用戶提出嘅方法論疑慮(pooled OLS 會唔會
冚咗一個 tier-specific 效應)已經被正面測試同排除——唔係「未驗證過呢個可能性」,而係
「驗證咗,依然搵唔到」。**唔建議**以「淨係喺 micro-cap 用呢個訊號」嘅形式復活 P0-c:micro tier
入面睇落最有希望嘅 pattern,喺最嚴謹嘅 within-tier OLS 底下同其餘 tier 一樣冧晒。insider P0-c
(SEC Form 4 → thesis confidence)**繼續停喺 backlog**。

如果之後想再開呢個角度,建議方向:(a) 換一個 point-in-time market-cap 覆蓋率更高嘅數據源
(defeatbeta 呢次淨係覆蓋 40.7% tickers,可能漏咗最細、理論上最有機會有真訊號嗰批 nano-cap);
(b) 若要再細分(例如 <$50M nano-cap),要注意而家 <$300M tier 都先得 2,436 個事件(owners=2
純樣本 616 個)——再細分落去樣本量好快會跌穿可靠推論嘅門檻,報告價值有限,唔建議喺呢個
sample size 底下再切。

**Artifacts(本節新增):**
- `backtest/experiments/exp_insider_breadth_mcaptier.py` — tier breakdown script(4-tier bucket
  table、monotonicity、owners=2 vs >=3 step test、within-tier OLS with mcap control、quantile
  robustness check)
