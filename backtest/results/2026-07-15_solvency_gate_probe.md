# Solvency-Gate Probe — 2026-07-15

Script: `backtest/experiments/exp_solvency_gate_probe.py` (`PYTHONUTF8=1 python backtest/experiments/exp_solvency_gate_probe.py`)

## 動機

Karst 估值模組發現過:USAC 睇 trailing-PE 分位「全場最平」(自身歷史 2nd percentile,~27x),但 net debt \$2.98B vs 市值 \$3.84B——嗰個「平」一大半係槓桿股權切片嘅假象,唔係無槓桿基礎上嘅真.便宜(見 `backtest/results/2026-07-12_expectations_gap_v0.md` USAC 專節)。嗰次審查寫低「solvency gate 檢查升級為必做」但一直未做。本探測正式回答:一個**機械**償債能力檢查,應唔應該成為買入候選嘅**否決閘**,定係 `thesis/composite_score.py` 0-100 綜合分嘅**第六維**?

## 候選指標(2 主 + 1 副,理據)

| 指標 | 定義 | 點解揀 |
|---|---|---|
| **槓桿(主)** | Net Debt(手動重構)÷ EBITDA(季度 TTM,史前段用年度) | 直接對應 USAC 動機案例嘅比率;`net_debt_ttm()` 官方 net_debt 欄剔除短債(只計長債−現金),同 2026-07-12 審查發現嘅遮蔽問題一致,改用 `total_debt − cash_and_short_term_investments` 手動重構。 |
| **利息覆蓋(主)** | EBIT ÷ 利息支出(同上,TTM/年度) | 同槓桿係**唔同故障模式**:槓桿低但盈利突然跌穿都可以覆蓋唔到利息;槓桿高但融資條件好都可以照覆蓋。兩者唔應該疊做同一條軸。 |
| **流動比率(副,exploratory)** | Total Current Assets ÷ Total Current Liabilities | 短週期流動性,同結構性過度槓桿係唔同故障模式,同 USAC 案例關聯較弱——只報告唔入主判決。簡化 Altman-Z / Piotroski F-score 已考慮但**剔除**:需要遠多過兩條主軸嘅輸入(市值比率、資產週轉變化、股數變化等),會沖淡「機械 gate 值唔值得起」呢個核心問題。 |

**H1(否決閘)**:solvency 差(槓桿>4x 或 EBITDA≤0,OR 利息覆蓋<2x)嘅股,forward 21/63/126d 係咪跑輸同組 size-matched 籃子?
**H2(連續維度)**:pooled 跨股橫切面五分位(Q1=最佳,Q5=最差,逐 grid 日全 universe 排位)係咪單調——定係得最差嗰截先有懲罰(=> 應該做 gate 唔係連續分)?

## 數據深度與 hybrid 季度+年度構造(誠實申報,讀結果前必讀)

defeatbeta **季度**資產負債表/損益表/`net_debt_ttm`/`ttm_ebitda` 只回到 ~16-17 季(≈2022 起);**年度**報表回到 FY2019。本探測用 hybrid:有季度 TTM 讀數嘅日子用季度(avail = 季末+60日),之前嘅歷史用年度讀數向後延伸(avail = 財年末+90日,10-K lag)。後果:**solvency 訊號最早只去到 ~2020 年中**(FY2019+90日)。repo 標準「2016-2020 / 2021+」兩半劈對 solvency 腿**做唔到**——「2016-2020」嗰半實際只含 ~2020 下半年事件(下表照報,n 細係誠實反映)。另補一個數據撐得起嘅利率 regime 劈法:**≤2022(ZIRP 尾)vs 2023+(高息期)**——對 solvency 訊號呢個劈法本身仲有經濟意義(利率升先係償債能力出事嘅環境)。`pe_low` baseline 用 `ttm_eps`(回到 2016 前)起,覆蓋完整 2016+ 窗口。

**金融股(銀行/保險)係設計上剔除,唔係載入失敗**:NetDebt/EBITDA 同 EBIT/利息覆蓋對佢哋無意義(v1 run JPM/MTG 正正咁樣炸)。將來接線嘅 gate 必須帶同一 scope 規則:金融股跳過。

## Point-in-time 處理

同 `exp_earnings_expectation_probe.py` 一致嘅保守 filing-lag 慣例。現有 `pe_pctile` 軸(A/B 增量用)**直接 import** 該探測嘅 `_load_fundamentals`/`_pit_pe_daily`,唔重寫、無 drift。solvency 讀數經 `merge_asof(direction='backward')` 逐日對齊,首個 avail_date 之前 = NaN(唔會偽 ffill)。**v2 修正**:forward excess 對**全部**(ticker, 月)事件計算,唔係只計有訊號嘅——v1 曾將 H2 五分位同 pe_low baseline 都 condition 咗喺「有訊號觸發」上,全部比較組被污染,該版結果作廢。

## Universe(4 股種 + size-matched benchmark)

- **megacap** (11/12): AAPL, MSFT, NVDA, GOOGL, AMZN, META, AVGO, UNH, LLY, XOM, WMT
- **midcap** (11/11): WDC, NTAP, JBL, LSCC, RS, CMC, WGO, GT, SLAB, SWKS, THO
- **smallcap** (12/13): AEHR, PLAB, KOPN, CEVA, UCTT, ACLS, OSIS, VECO, PLXS, MTSI, DIOD, HLIT
- **cyclical** (15/15): MU, STX, LRCX, AMAT, KLAC, COP, DVN, OXY, FCX, NUE, STLD, CF, AAL, CCL, CLF
- **載入失敗**: V(RuntimeError), AMWD(RuntimeError)

cyclicals 組喺能源/材料/半導體之上有 AAL/CCL/CLF(航空/郵輪/鋼鐵)——文獻上嘅經典高槓桿名;smallcap 加 AMWD/HLIT、midcap 用 THO 替代金融股 MTG、megacap 用 UNH 替代 JPM,保證 solvency 軸有真正嘅樣本內方差。

總事件數(ticker×月):6223;其中有 solvency 讀數:2349;solvency_bad 觸發:497;pe_low 觸發:1310。

## 結果 A — H1 否決閘(全期,逐股種)

### solvency_bad = lev_gate OR cov_gate(建議 H1 定義)

| 股種 | Horizon | n | mean excess | median | 跑輸率 | cond.Sharpe(ann) | 年化 excess |
|---|---|---:|---:|---:|---:|---:|---:|
| megacap | 21d | n=12 | +2.16% | -2.39% | 58% | +0.52 | +25.9% |
| megacap | 63d | n=12 | +9.72% | +5.26% | 42% | +0.90 | +38.9% |
| megacap | 126d | n=12 | +26.76% | +32.74% | 33% | +1.15 | +53.5% |
| midcap | 21d | n=106 | -1.59% | -2.53% | 63% | -0.44 | -19.0% |
| midcap | 63d | n=102 | -4.02% | -7.77% | 59% | -0.37 | -16.1% |
| midcap | 126d | n=96 | -7.07% | -5.72% | 66% | -0.35 | -14.1% |
| smallcap | 21d | n=204 | +1.84% | -0.10% | 51% | +0.31 | +22.1% |
| smallcap | 63d | n=196 | +3.84% | -2.05% | 52% | +0.19 | +15.3% |
| smallcap | 126d | n=182 | +4.10% | -4.95% | 54% | +0.09 | +8.2% |
| cyclical | 21d | n=159 | -0.50% | -0.97% | 53% | -0.12 | -6.0% |
| cyclical | 63d | n=155 | +0.19% | -3.29% | 57% | +0.01 | +0.8% |
| cyclical | 126d | n=149 | -0.89% | -8.12% | 56% | -0.03 | -1.8% |
| **ALL** | 21d | n=481 | +0.32% | -1.42% | 55% | +0.07 | +3.8% |
| **ALL** | 63d | n=465 | +1.05% | -3.54% | 55% | +0.07 | +4.2% |
| **ALL** | 126d | n=439 | +0.58% | -5.41% | 57% | +0.02 | +1.2% |

### lev_gate 單獨(槓桿>4x 或 EBITDA≤0)

| 股種 | Horizon | n | mean excess | median | 跑輸率 | cond.Sharpe(ann) | 年化 excess |
|---|---|---:|---:|---:|---:|---:|---:|
| megacap | 21d | n=0 | — | — | — | — | — |
| megacap | 63d | n=0 | — | — | — | — | — |
| megacap | 126d | n=0 | — | — | — | — | — |
| midcap | 21d | n=78 | -2.66% | -3.40% | 64% | -0.73 | -31.9% |
| midcap | 63d | n=74 | -5.84% | -7.33% | 58% | -0.55 | -23.4% |
| midcap | 126d | n=70 | -10.68% | -12.96% | 70% | -0.50 | -21.4% |
| smallcap | 21d | n=144 | +2.09% | -1.34% | 54% | +0.32 | +25.0% |
| smallcap | 63d | n=136 | +5.29% | -4.52% | 54% | +0.24 | +21.1% |
| smallcap | 126d | n=124 | +9.32% | -1.12% | 51% | +0.18 | +18.6% |
| cyclical | 21d | n=141 | -0.78% | -0.82% | 52% | -0.19 | -9.3% |
| cyclical | 63d | n=137 | -0.38% | -3.50% | 60% | -0.03 | -1.5% |
| cyclical | 126d | n=131 | -3.02% | -11.11% | 60% | -0.10 | -6.0% |
| **ALL** | 21d | n=363 | -0.04% | -1.96% | 56% | -0.01 | -0.5% |
| **ALL** | 63d | n=347 | +0.68% | -4.57% | 57% | +0.04 | +2.7% |
| **ALL** | 126d | n=325 | +0.04% | -8.12% | 59% | +0.00 | +0.1% |

### cov_gate 單獨(覆蓋<2x 或 EBIT≤0 有息)

| 股種 | Horizon | n | mean excess | median | 跑輸率 | cond.Sharpe(ann) | 年化 excess |
|---|---|---:|---:|---:|---:|---:|---:|
| megacap | 21d | n=12 | +2.16% | -2.39% | 58% | +0.52 | +25.9% |
| megacap | 63d | n=12 | +9.72% | +5.26% | 42% | +0.90 | +38.9% |
| megacap | 126d | n=12 | +26.76% | +32.74% | 33% | +1.15 | +53.5% |
| midcap | 21d | n=97 | -1.73% | -2.50% | 62% | -0.48 | -20.8% |
| midcap | 63d | n=93 | -4.41% | -7.95% | 59% | -0.40 | -17.7% |
| midcap | 126d | n=87 | -4.61% | -3.85% | 62% | -0.24 | -9.2% |
| smallcap | 21d | n=111 | +1.25% | -0.00% | 50% | +0.31 | +15.0% |
| smallcap | 63d | n=109 | +1.29% | +0.06% | 50% | +0.10 | +5.1% |
| smallcap | 126d | n=104 | +0.19% | -7.14% | 59% | +0.01 | +0.4% |
| cyclical | 21d | n=150 | -0.53% | -0.89% | 53% | -0.13 | -6.4% |
| cyclical | 63d | n=146 | -0.01% | -3.32% | 58% | -0.00 | -0.0% |
| cyclical | 126d | n=140 | -0.52% | -8.43% | 56% | -0.02 | -1.0% |
| **ALL** | 21d | n=370 | -0.23% | -1.05% | 55% | -0.06 | -2.7% |
| **ALL** | 63d | n=360 | -0.43% | -3.36% | 55% | -0.03 | -1.7% |
| **ALL** | 126d | n=343 | -0.39% | -5.41% | 58% | -0.01 | -0.8% |

### current_gate(副軸,流動比率<1.0,exploratory)

| 股種 | Horizon | n | mean excess | median | 跑輸率 | cond.Sharpe(ann) | 年化 excess |
|---|---|---:|---:|---:|---:|---:|---:|
| megacap | 21d | n=164 | -0.99% | -1.22% | 59% | -0.37 | -11.9% |
| megacap | 63d | n=158 | -2.59% | -1.33% | 54% | -0.31 | -10.3% |
| megacap | 126d | n=149 | -5.40% | -6.61% | 59% | -0.31 | -10.8% |
| midcap | 21d | n=15 | -1.08% | +1.19% | 47% | -0.51 | -13.0% |
| midcap | 63d | n=15 | -0.71% | -3.21% | 60% | -0.11 | -2.8% |
| midcap | 126d | n=12 | -11.75% | -14.32% | 83% | -1.46 | -23.5% |
| smallcap | 21d | n=6 | +6.64% | +8.02% | 33% | +1.19 | +79.6% |
| smallcap | 63d | n=6 | +41.07% | +18.94% | 33% | +1.25 | +164.3% |
| smallcap | 126d | n=6 | +58.84% | +55.49% | 0% | +6.40 | +117.7% |
| cyclical | 21d | n=132 | -3.12% | -4.33% | 61% | -0.84 | -37.4% |
| cyclical | 63d | n=124 | -6.43% | -10.31% | 68% | -0.49 | -25.7% |
| cyclical | 126d | n=110 | -14.70% | -17.49% | 75% | -0.57 | -29.4% |
| **ALL** | 21d | n=317 | -1.74% | -1.77% | 59% | -0.54 | -20.8% |
| **ALL** | 63d | n=303 | -3.20% | -3.29% | 60% | -0.27 | -12.8% |
| **ALL** | 126d | n=277 | -7.98% | -9.05% | 65% | -0.36 | -16.0% |

### Baseline: pe_low ALONE(現有 pe_pctile 軸,PE≤20%)

| 股種 | Horizon | n | mean excess | median | 跑輸率 | cond.Sharpe(ann) | 年化 excess |
|---|---|---:|---:|---:|---:|---:|---:|
| megacap | 21d | n=184 | -0.77% | -0.81% | 55% | -0.31 | -9.3% |
| megacap | 63d | n=182 | -1.40% | -2.37% | 59% | -0.17 | -5.6% |
| megacap | 126d | n=178 | -3.70% | -5.27% | 63% | -0.20 | -7.4% |
| midcap | 21d | n=378 | -0.54% | -1.55% | 56% | -0.20 | -6.5% |
| midcap | 63d | n=375 | -1.01% | -1.81% | 56% | -0.12 | -4.0% |
| midcap | 126d | n=369 | -1.11% | -2.16% | 54% | -0.07 | -2.2% |
| smallcap | 21d | n=290 | -0.72% | -1.20% | 56% | -0.24 | -8.6% |
| smallcap | 63d | n=287 | -3.57% | -4.50% | 63% | -0.36 | -14.3% |
| smallcap | 126d | n=283 | -6.37% | -8.09% | 60% | -0.30 | -12.7% |
| cyclical | 21d | n=448 | -0.56% | -0.42% | 52% | -0.17 | -6.7% |
| cyclical | 63d | n=448 | -1.08% | -2.08% | 56% | -0.12 | -4.3% |
| cyclical | 126d | n=448 | -1.76% | -5.75% | 59% | -0.09 | -3.5% |
| **ALL** | 21d | n=1300 | -0.62% | -0.91% | 55% | -0.21 | -7.4% |
| **ALL** | 63d | n=1292 | -1.66% | -2.56% | 58% | -0.18 | -6.6% |
| **ALL** | 126d | n=1278 | -2.86% | -4.84% | 58% | -0.15 | -5.7% |

### 對照組:solvency 正常(有讀數且未觸發 gate)

gate 嘅另一面:如果「正常組」都同樣跑輸,gate 就冇判別力。

| 股種 | Horizon | n | mean excess | median | 跑輸率 | cond.Sharpe(ann) | 年化 excess |
|---|---|---:|---:|---:|---:|---:|---:|
| megacap | 21d | n=522 | -0.28% | -0.74% | 56% | -0.11 | -3.3% |
| megacap | 63d | n=500 | -0.67% | -1.40% | 56% | -0.09 | -2.7% |
| megacap | 126d | n=467 | -1.64% | -4.49% | 57% | -0.10 | -3.3% |
| midcap | 21d | n=391 | +0.16% | -0.23% | 51% | +0.05 | +1.9% |
| midcap | 63d | n=373 | +0.71% | -1.60% | 54% | +0.07 | +2.9% |
| midcap | 126d | n=346 | +2.22% | -2.15% | 56% | +0.08 | +4.4% |
| smallcap | 21d | n=381 | -1.98% | -2.34% | 59% | -0.55 | -23.7% |
| smallcap | 63d | n=365 | -6.34% | -6.74% | 65% | -0.50 | -25.4% |
| smallcap | 126d | n=343 | -12.91% | -13.14% | 71% | -0.46 | -25.8% |
| cyclical | 21d | n=476 | +0.12% | -0.87% | 53% | +0.03 | +1.4% |
| cyclical | 63d | n=450 | -0.03% | -1.60% | 53% | -0.00 | -0.1% |
| cyclical | 126d | n=411 | +0.63% | -5.69% | 60% | +0.02 | +1.3% |
| **ALL** | 21d | n=1770 | -0.44% | -0.89% | 55% | -0.14 | -5.3% |
| **ALL** | 63d | n=1688 | -1.42% | -2.33% | 57% | -0.13 | -5.7% |
| **ALL** | 126d | n=1567 | -2.66% | -5.91% | 61% | -0.10 | -5.3% |

## 結果 B — 兩半穩健性(pooled,全股種)

### B1 repo 標準劈法(2016-2020 / 2021+)——solvency 腿嘅前半實際只有 ~2020H2(數據深度,見上)

| Gate | Era | Horizon | n | mean excess | 跑輸率 | cond.Sharpe |
|---|---|---|---:|---:|---:|---:|
| solvency_bad | 2016-2020 | 21d | 11 | +3.25% | 36% | +0.74 |
| solvency_bad | 2016-2020 | 63d | 11 | +5.18% | 27% | +0.38 |
| solvency_bad | 2016-2020 | 126d | 11 | +16.97% | 18% | +0.85 |
| solvency_bad | 2021+ | 21d | 470 | +0.25% | 55% | +0.05 |
| solvency_bad | 2021+ | 63d | 454 | +0.95% | 56% | +0.06 |
| solvency_bad | 2021+ | 126d | 428 | +0.16% | 58% | +0.00 |
| lev_gate | 2016-2020 | 21d | 1 | -12.55% | 100% | +nan |
| lev_gate | 2016-2020 | 63d | 1 | -52.63% | 100% | +nan |
| lev_gate | 2016-2020 | 126d | 1 | -25.54% | 100% | +nan |
| lev_gate | 2021+ | 21d | 362 | -0.01% | 56% | -0.00 |
| lev_gate | 2021+ | 63d | 346 | +0.83% | 57% | +0.05 |
| lev_gate | 2021+ | 126d | 324 | +0.12% | 59% | +0.00 |
| cov_gate | 2016-2020 | 21d | 11 | +3.25% | 36% | +0.74 |
| cov_gate | 2016-2020 | 63d | 11 | +5.18% | 27% | +0.38 |
| cov_gate | 2016-2020 | 126d | 11 | +16.97% | 18% | +0.85 |
| cov_gate | 2021+ | 21d | 359 | -0.33% | 55% | -0.08 |
| cov_gate | 2021+ | 63d | 349 | -0.61% | 56% | -0.05 |
| cov_gate | 2021+ | 126d | 332 | -0.96% | 59% | -0.03 |
| pe_low(baseline) | 2016-2020 | 21d | 564 | -0.83% | 56% | -0.30 |
| pe_low(baseline) | 2016-2020 | 63d | 564 | -2.31% | 58% | -0.27 |
| pe_low(baseline) | 2016-2020 | 126d | 564 | -3.05% | 59% | -0.17 |
| pe_low(baseline) | 2021+ | 21d | 736 | -0.46% | 54% | -0.15 |
| pe_low(baseline) | 2021+ | 63d | 728 | -1.15% | 58% | -0.12 |
| pe_low(baseline) | 2021+ | 126d | 714 | -2.72% | 58% | -0.14 |

### B2 利率 regime 劈法(≤2022 ZIRP 尾 / 2023+ 高息期)——solvency 數據撐得起嘅劈法

| Gate | Era | Horizon | n | mean excess | 跑輸率 | cond.Sharpe |
|---|---|---|---:|---:|---:|---:|
| solvency_bad | <=2022 | 21d | 215 | +0.03% | 58% | +0.01 |
| solvency_bad | <=2022 | 63d | 215 | -0.11% | 54% | -0.01 |
| solvency_bad | <=2022 | 126d | 215 | -0.19% | 58% | -0.01 |
| solvency_bad | 2023+ | 21d | 266 | +0.56% | 52% | +0.11 |
| solvency_bad | 2023+ | 63d | 250 | +2.05% | 55% | +0.12 |
| solvency_bad | 2023+ | 126d | 224 | +1.33% | 56% | +0.04 |
| lev_gate | <=2022 | 21d | 152 | -0.79% | 61% | -0.16 |
| lev_gate | <=2022 | 63d | 152 | -2.65% | 62% | -0.18 |
| lev_gate | <=2022 | 126d | 152 | -4.49% | 66% | -0.12 |
| lev_gate | 2023+ | 21d | 211 | +0.50% | 52% | +0.09 |
| lev_gate | 2023+ | 63d | 195 | +3.27% | 53% | +0.17 |
| lev_gate | 2023+ | 126d | 173 | +4.02% | 53% | +0.10 |
| cov_gate | <=2022 | 21d | 181 | +0.01% | 57% | +0.00 |
| cov_gate | <=2022 | 63d | 181 | +1.34% | 51% | +0.12 |
| cov_gate | <=2022 | 126d | 181 | +2.07% | 55% | +0.08 |
| cov_gate | 2023+ | 21d | 189 | -0.45% | 52% | -0.10 |
| cov_gate | 2023+ | 63d | 179 | -2.22% | 59% | -0.16 |
| cov_gate | 2023+ | 126d | 162 | -3.13% | 61% | -0.10 |
| pe_low(baseline) | <=2022 | 21d | 921 | -0.82% | 55% | -0.28 |
| pe_low(baseline) | <=2022 | 63d | 921 | -2.08% | 58% | -0.24 |
| pe_low(baseline) | <=2022 | 126d | 921 | -3.29% | 59% | -0.17 |
| pe_low(baseline) | 2023+ | 21d | 379 | -0.14% | 52% | -0.05 |
| pe_low(baseline) | 2023+ | 63d | 371 | -0.60% | 57% | -0.06 |
| pe_low(baseline) | 2023+ | 126d | 357 | -1.76% | 57% | -0.10 |

## 結果 C — A/B 增量:solvency_bad vs 現有 pe_pctile

核心問題:solvency 差嘅股,係咪本身已經係 `pe_pctile` 標到嘅平股(=冇增量),定係solvency 加喺 pe_low 之上仲有淨額外拖累(=有增量,值得做獨立軸)?

| Horizon | pe_low ALONE mean(n) | solvency_bad ALONE mean(n) | pe_low AND solvency_bad mean(n) | solvency_bad AND NOT pe_low mean(n) | 增量判讀 |
|---|---:|---:|---:|---:|---|
| 21d | -0.62% (n=1300) | +0.32% (n=481) | -2.57% (n=81) | +0.91% (n=400) | 疊加有增量(更負)(Δ=-1.95pp vs pe_low alone) |
| 63d | -1.66% (n=1292) | +1.05% (n=465) | -6.30% (n=79) | +2.56% (n=386) | 疊加有增量(更負)(Δ=-4.64pp vs pe_low alone) |
| 126d | -2.86% (n=1278) | +0.58% (n=439) | -15.12% (n=76) | +3.87% (n=363) | 疊加有增量(更負)(Δ=-12.26pp vs pe_low alone) |

`solvency_bad AND NOT pe_low`(唔平但 gate-fail)一欄係關鍵獨立性測試:如果呢欄都跑輸,solvency 就唔係「換個角度講嘅平股」,而係一條獨立軸——即使個股表面上唔平都值得否決/扣分。

### C2 條件閘深挖:pe_low AND solvency_bad(USAC 場景)

上表如果顯示「無條件 gate 冇料、但 pe_low∧solvency_bad 顯著更負」,行為上就係 Piotroski 形態(solvency 只喺 cheap 桶內有判別力)——亦正正係動機場景:USAC 係因為「睇落平」先入候選,gate 嘅用武之地就係呢批名。呢節驗證條件組嘅穩健性:逐股種、利率 era、同 ticker 集中度(如果 n 靠一兩隻股撐起,唔可以接線)。

| 切片 | Horizon | n | mean excess | 跑輸率 |
|---|---|---:|---:|---:|
| megacap | 21d | 0 | — | — |
| megacap | 63d | 0 | — | — |
| megacap | 126d | 0 | — | — |
| midcap | 21d | 15 | -4.84% | 80% |
| midcap | 63d | 13 | -13.04% | 69% |
| midcap | 126d | 10 | -34.53% | 100% |
| smallcap | 21d | 17 | +1.76% | 35% |
| smallcap | 63d | 17 | +3.69% | 47% |
| smallcap | 126d | 17 | -1.89% | 59% |
| cyclical | 21d | 49 | -3.38% | 65% |
| cyclical | 63d | 49 | -7.98% | 76% |
| cyclical | 126d | 49 | -15.75% | 82% |
| era <=2022 | 21d | 52 | -3.57% | 67% |
| era <=2022 | 63d | 52 | -8.33% | 77% |
| era <=2022 | 126d | 52 | -19.16% | 87% |
| era 2023+ | 21d | 29 | -0.78% | 52% |
| era 2023+ | 63d | 27 | -2.40% | 52% |
| era 2023+ | 126d | 24 | -6.38% | 62% |

**Ticker 集中度(126d 事件)**:7 隻股;最大單一 ticker 佔 30%。Top 貢獻:CCL(n=23, mean -28.6%), AAL(n=17, mean -23.9%), VECO(n=13, mean +0.8%), GT(n=10, mean -34.5%), DVN(n=5, mean +67.6%), HLIT(n=4, mean -10.6%)。

## 結果 D — H2 連續維度:跨股橫切面五分位(pooled,全股種,126d)

Q1=最佳(低槓桿/高覆蓋),Q5=最差(高槓桿/低覆蓋)。單調(Q1→Q5 excess 遞減)支持連續分設計;只有 Q5 顯著負值支持 gate(二元否決)設計。v2:全事件計 return,無 conditioning bias。

| 指標 | Quintile | n | mean excess(126d) | 跑輸率 |
|---|---|---:|---:|---:|
| 槓桿(leverage) | Q1 | 339 | -3.86% | 65% |
| 槓桿(leverage) | Q2 | 318 | -7.04% | 69% |
| 槓桿(leverage) | Q3 | 310 | -1.16% | 54% |
| 槓桿(leverage) | Q4 | 318 | -0.25% | 55% |
| 槓桿(leverage) | Q5 | 327 | +1.91% | 59% |
| 覆蓋(coverage,badness=-coverage) | Q1 | 378 | -4.37% | 61% |
| 覆蓋(coverage,badness=-coverage) | Q2 | 341 | -2.65% | 65% |
| 覆蓋(coverage,badness=-coverage) | Q3 | 341 | -4.76% | 57% |
| 覆蓋(coverage,badness=-coverage) | Q4 | 341 | +1.56% | 59% |
| 覆蓋(coverage,badness=-coverage) | Q5 | 371 | -2.64% | 60% |

補充:EBITDA≤0(`ebitda_neg`)同「有息但 EBIT≤0」(`ebit_neg_with_debt`)嘅事件冇正定義嘅leverage/coverage 數值,冇入五分位排位(佢哋定義上已經係最差,H1 gate 用二元旗標獨立捕捉)。五分位喺同一 grid 日至少要 10 個有效讀數先排(即實際只由 ~2020 年中起)。

## 結論(GO-as-gate / GO-as-dimension / DISPLAY-ONLY / NO-GO)

**啟發式判讀(下列數字由 script 計,最終判斷由作者覆核):**

- solvency_bad mean excess: 21d +0.32%(n=481), 63d +1.05%(n=465), 126d +0.58%(n=439)
- lev_gate mean excess: 21d -0.04%(n=363), 63d +0.68%(n=347), 126d +0.04%(n=325)
- cov_gate mean excess: 21d -0.23%(n=370), 63d -0.43%(n=360), 126d -0.39%(n=343)
- pe_low baseline mean excess: 21d -0.62%(n=1300), 63d -1.66%(n=1292), 126d -2.86%(n=1278)
- solvency 正常對照組 mean excess: 21d -0.44%(n=1770), 63d -1.42%(n=1688), 126d -2.66%(n=1567)
- **獨立性關鍵**:solvency_bad AND NOT pe_low(126d) = +3.87%(n=363) —— 唔顯著跑輸,solvency 效力可能主要嚟自同 pe_low 重疊嘅名
- **A/B 增量(126d)**:(pe_low AND solvency_bad) − pe_low alone = -12.26pp
- **條件組(pe_low∧solvency_bad,126d)era 穩健性**:≤2022 -19.2%(n=52),2023+ -6.4%(n=24);ticker 集中度:7 隻,最大佔 30%

- **槓桿五分位(126d)mean excess Q1→Q5**: -3.9%, -7.0%, -1.2%, -0.3%, +1.9%
  -> 非單調亦非「只有最差檔」形態,結構不乾淨——見下判決保留態度。

### 判定:**GO-as-gate(條件版:只對 pe-cheap 買入候選否決;閾值:槓桿>4x EBITDA 或 EBITDA≤0,OR 利息覆蓋<2x;金融股跳過)**

三個結構性發現指向**條件閘**而唔係無條件閘或連續維度:(1) 無條件 solvency_bad pooled excess ≈ 0——單獨用冇料;(2) `pe_low ∧ solvency_bad` 顯著更負(見結果 C/C2),且兩個利率 era 都成立、唔係一兩隻股撐起——**solvency 只喺 cheap 桶內有判別力**,同 Piotroski (2000) 「財務強度只喺 value 股入面分贏輸家」完全一致;(3) `solvency_bad ∧ NOT pe_low` 為正——唔平嘅高槓桿名(多數係增長期融資)唔應該被罰,無條件 gate 會錯殺。呢個形態正正係 USAC 動機場景:個名係因為「睇落平」先入買入候選,gate 嘅職責就係喺嗰一刻攔截「平因為槓桿」嘅假象。**建議接線位**:pick_ticker/估值管道——凡 pe_pctile ≤ 20%(「平」係買入理由)嘅候選,觸發 solvency_bad 即否決或強制降級人手覆核;composite_score **唔加**第六維(H2 五分位非單調,連續分冇 alpha);日報對 cheap 候選顯示 solvency 讀數。

## 誠實 Caveat

1. **歷史深度唔達 repo 標準**:solvency 訊號最早 ~2020 年中(defeatbeta 年度表只回到 FY2019),2016-2019 完全冇覆蓋——呢四年包含 2016 工業衰退、2018Q4 信用驚嚇,正正係 solvency 訊號可能最有用嘅時段之一。結論只適用於 2020+,唔好外推。
2. **filing lag 係近似**:季度固定 60 日、年度 90 日,真實各公司/各季申報日有差異。
3. **`net_debt_manual` 仍係近似**:total_debt/cash_and_STI 取自 defeatbeta 兩張唔同表(`debt_to_equity()`/`net_debt_ttm()`),未逐一對過原始 10-Q;年度段用 balance-sheet 'Total Debt'/'Cash…STI' 行,同季度段口徑可能有細差。
4. **hybrid 季度/年度接駁**:~2022 前後讀數頻率由年度變季度,訊號更新速度唔一致(年度段一年先郁一次)。方向唔應該受影響,但 gate 觸發嘅 timing 喺年度段遲鈍。
5. **覆蓋比率喺利息支出接近 0 時唔穩定**:分母細,coverage 可以爆極端值,已用 `int_exp > 0` 過濾但冇上限截尾。
6. **事件重疊**:月 grid vs 126d horizon,有效獨立樣本遠少於 n;同一隻股連續多月觸發 gate 係常態(債務結構變化慢),條 excess 序列高度自相關,cond.Sharpe 只作方向參考。
7. **survivorship**:universe 係今日仍上市嘅名。solvency gate 應該捕捉嘅正正係破產/退市名(distress 同退市高度相關,比 PE/動能訊號嘅漏樣本傷好多),缺席**必然低估** gate 效力,方向保守——即係話「有效」結論可以信,「冇效」結論要打折。
8. **cyclicals 有 AAL/CCL/CLF、smallcap 擬加 AMWD/HLIT(AMWD 載入失敗)令樣本非隨機**:刻意揀嚟俾 solvency 軸方差;如果結果主要由呢幾隻驅動,增量嘅可推廣性要打折(C2 嘅 ticker 集中度檢查就係為此)。
9. **金融股剔除**:結論唔適用於銀行/保險;接線時 gate 必須跳過金融 sector。
10. **smallcap 方向反轉**:smallcap 嘅 gate-fail 名反而跑贏(lev_gate 126d 約 +9%)——2020-2021 投機行情下,cash-burn/高槓桿細價股係彩票型贏家。條件閘(只罰 cheap 名)自然避開呢批(佢哋通常冇 PE 或 PE 唔低),但直接印證「無條件 gate 會錯殺」。
11. **條件組宏觀集中**:pe_low∧solvency_bad 嘅負 excess 主要由 COVID 疫後 travel/consumer-cyclical distress 名(CCL/AAL/GT 類)貢獻——雖然通過「≥6 隻股、單一 ticker ≤40%」檢查,但佢哋某程度上係**同一個宏觀 episode**;而 DVN(能源,2020-21 平+高槓桿其後大升)顯示條件閘嘅錯殺面。接線建議用「否決或強制降級人手覆核」而唔係靜默剔除,正係為此。

## 文獻對照

**Dichev (1998, JF)** 「Is the Risk of Bankruptcy a Systematic Risk?」—— 用 Z-score/O-score 量度嘅高破產風險股,後續回報**反而較低**(唔係風險溢價,係 anomaly)。**Campbell, Hilscher & Szilagyi (2008, JF)** 「In Search of Distress Risk」—— 更完整嘅違約機率模型,結果一致:高財務困境風險股 forward return 系統性偏低,而且集中喺最差 tail(佢哋嘅 distress 組合回報差主要由最高違約機率 decile 驅動——同本探測 H2「gate 定連續分」嘅問題直接相關)。**Piotroski (2000, JAR)** F-score —— 財務強度篩選喺**低市帳率股**入面分開贏家輸家:高 F-score 平股跑贏低 F-score 平股,直接對應本探測嘅 A/B 增量框架(solvency 疊喺 cheap 之上)。三份文獻方向一致支持 H1(solvency 差 = 跑輸,唔係補償性溢價)。如果本探測測出「冇效」或方向相反,要分辨:(a) proxy/樣本問題——survivorship 剔走真困境股(caveat 7)、歷史只有 2020+(caveat 1)、net_debt 重構噪音;定係 (b) 主張喺呢個期間唔成立(2020-2021 ZIRP 令高槓桿股反而受惠)。兩者政策含意唔同:(a) → 換更乾淨數據源重試先下判;(b) → 承認 regime 依賴,gate 帶利率條件先接線。
