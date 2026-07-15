# Earnings-Expectation Extremity Probe — 2026-07-14

Script: `backtest/experiments/exp_earnings_expectation_probe.py` (`PYTHONUTF8=1 python backtest/experiments/exp_earnings_expectation_probe.py`)

## 動機與可回測性

用戶想引入 **trailing P/E ÷ forward P/E** 估值軸(比率高 = 分析師共識要求盈利爆升先撐得住個「平」，例 SNDK trailing 57x / forward 8x = 7.1x，網路泡沫級別)。真.共識 forward estimates **冇免費歷史數據**(defeatbeta 冇、yfinance 只有當前快照)，所以個比率本身**唔可以直接回測**。但佢背後嘅經濟主張可以:**「當市場對一隻股嘅盈利增長預期去到極端，後續回報差」**。本實驗用可得數據回測呢個主張嘅兩個 proxy，對應原比率嘅兩個危險象限。

| Proxy | 對應象限 | 定義(全部 point-in-time) |
|---|---|---|
| **P1 盈利動能極端外推** | SNDK 型「共識要求 EPS 爆升」 | TTM-EPS YoY 增長 ≥ 該股自身歷史 **top decile**(≥90% 分位，expanding) |
| **P2 週期頂低-PE 陷阱** | 文章講嘅韓股/cyclicals「越升越平」 | trailing PE ≤ 自身歷史 **20% 分位** AND TTM-EPS / 自身 3 年中位 EPS ≥ **1.3** |

驗證問題:訊號觸發後,forward 21/63/126 交易日 **相對同組 size-matched 籃子**係咪跑輸(excess<0)?

## Point-in-time 處理(關鍵)

**探測發現 defeatbeta `ttm_pe()` 表有 look-ahead**:佢喺季度結束日(+1-2 交易日)就套用新季 TTM-EPS，而唔係真實 10-Q/10-K **申報日**(MU 5 月底季 defeatbeta 6/2 就用，但實際 ~6/25 先公布;SNDK lag=0)。因此本實驗**唔用**佢個 eps_report_date 切換日做 PIT。改為由 `ttm_eps()`/`quarterly_ttm_eps_yoy_growth()` 嘅 quarter_end **加保守 filing lag = 60 日**(覆蓋 10-Q ~40d、10-K ~60d)先當可得。PE 自己重構為 look-ahead-free:`pe_pit(t) = defeatbeta_close(t) / tailing_eps(quarter_end+60d ≤ t 嘅最新季)`。(defeatbeta 嘅 close 同 eps 同一內部 split-adjusted scale，比率 scale-invariant，所以 PE 有效。)

- **Returns**:`data.load(adjusted=True)` 總報酬價，對齊 SPY 交易日曆(PE 重構同 return 兩條獨立 code path)。
- **Benchmark/excess**:月末 grid event study。每 event date t + horizon H，benchmark = 同 size 組**全部**成份股 [t,t+H] 等權 forward return(size-matched B&H 籃子，剔除自己)。excess = 個股 forward(扣成本) − 組內 EW。「跑輸」= mean excess < 0。
- **成本**:10bps 每邊，round-trip 20bps 由訊號腿扣除(benchmark 係 B&H 冇 turnover)。
- **樣本門檻**:PE 需 ≥504 交易日自身歷史;YoY 需 ≥8 個先前季度;事件由 2016-01-01 起。

## Universe(4 股種 + size-matched benchmark)

- **megacap** (12/12): AAPL, MSFT, NVDA, GOOGL, AMZN, META, AVGO, JPM, LLY, V, XOM, WMT
- **midcap** (11/11): WDC, NTAP, JBL, LSCC, RS, CMC, WGO, GT, SLAB, SWKS, MTG
- **smallcap** (11/11): AEHR, PLAB, KOPN, CEVA, UCTT, ACLS, OSIS, VECO, PLXS, MTSI, DIOD
- **cyclical** (12/12): MU, STX, LRCX, AMAT, KLAC, COP, DVN, OXY, FCX, NUE, STLD, CF

總事件數:1440(每事件 = 一個 grid 月 × 一隻股，至少一個訊號觸發)。

## 結果 A — 逐股種 × 逐 proxy(全期 2016+)

### P1 盈利動能極端外推(YoY top decile)

| 股種 | Horizon | n | mean excess | median | 跑輸率 | cond.Sharpe(ann) | 年化 excess |
|---|---|---:|---:|---:|---:|---:|---:|
| megacap | 21d | n=127 | +0.08% | -0.46% | 52% | +0.04 | +1.0% |
| megacap | 63d | n=127 | +0.27% | +1.02% | 46% | +0.04 | +1.1% |
| megacap | 126d | n=127 | -0.25% | -1.30% | 53% | -0.02 | -0.5% |
| midcap | 21d | n=126 | +0.46% | -0.01% | 50% | +0.13 | +5.5% |
| midcap | 63d | n=120 | +1.97% | -1.30% | 52% | +0.15 | +7.9% |
| midcap | 126d | n=111 | +8.21% | -2.64% | 58% | +0.21 | +16.4% |
| smallcap | 21d | n=129 | -0.02% | -0.96% | 53% | -0.01 | -0.3% |
| smallcap | 63d | n=129 | -1.57% | -6.83% | 64% | -0.13 | -6.3% |
| smallcap | 126d | n=129 | -3.46% | -7.88% | 60% | -0.11 | -6.9% |
| cyclical | 21d | n=144 | +0.84% | -0.36% | 53% | +0.25 | +10.1% |
| cyclical | 63d | n=144 | +1.68% | -3.00% | 53% | +0.15 | +6.7% |
| cyclical | 126d | n=144 | +6.69% | -8.12% | 60% | +0.19 | +13.4% |
| **ALL** | 21d | n=526 | +0.36% | -0.35% | 52% | +0.11 | +4.3% |
| **ALL** | 63d | n=520 | +0.60% | -2.74% | 54% | +0.05 | +2.4% |
| **ALL** | 126d | n=511 | +2.73% | -4.75% | 58% | +0.08 | +5.5% |

### P2 週期頂低-PE 陷阱(PE低 AND EPS週期高)

| 股種 | Horizon | n | mean excess | median | 跑輸率 | cond.Sharpe(ann) | 年化 excess |
|---|---|---:|---:|---:|---:|---:|---:|
| megacap | 21d | n=154 | -1.42% | -1.68% | 58% | -0.65 | -17.0% |
| megacap | 63d | n=152 | -3.58% | -3.67% | 62% | -0.51 | -14.3% |
| megacap | 126d | n=149 | -7.70% | -9.86% | 68% | -0.52 | -15.4% |
| midcap | 21d | n=213 | -0.17% | -0.53% | 52% | -0.07 | -2.0% |
| midcap | 63d | n=213 | +0.52% | +0.43% | 49% | +0.07 | +2.1% |
| midcap | 126d | n=213 | +3.52% | +2.92% | 47% | +0.24 | +7.0% |
| smallcap | 21d | n=169 | -0.88% | -1.38% | 56% | -0.28 | -10.5% |
| smallcap | 63d | n=169 | -4.19% | -5.78% | 64% | -0.40 | -16.8% |
| smallcap | 126d | n=169 | -6.10% | -8.95% | 60% | -0.29 | -12.2% |
| cyclical | 21d | n=187 | +0.09% | -0.10% | 51% | +0.04 | +1.1% |
| cyclical | 63d | n=187 | -0.03% | -1.86% | 53% | -0.00 | -0.1% |
| cyclical | 126d | n=187 | -0.32% | -4.75% | 55% | -0.02 | -0.6% |
| **ALL** | 21d | n=723 | -0.53% | -0.96% | 54% | -0.20 | -6.4% |
| **ALL** | 63d | n=721 | -1.59% | -2.91% | 56% | -0.20 | -6.4% |
| **ALL** | 126d | n=718 | -2.08% | -4.58% | 57% | -0.12 | -4.2% |

### Baseline: pe_low ALONE(現有 pe_pctile 軸 proxy，PE≤20%)

| 股種 | Horizon | n | mean excess | median | 跑輸率 | cond.Sharpe(ann) | 年化 excess |
|---|---|---:|---:|---:|---:|---:|---:|
| megacap | 21d | n=207 | -0.82% | -1.20% | 55% | -0.35 | -9.8% |
| megacap | 63d | n=205 | -1.51% | -3.07% | 59% | -0.20 | -6.1% |
| megacap | 126d | n=201 | -3.51% | -6.40% | 62% | -0.20 | -7.0% |
| midcap | 21d | n=348 | -0.39% | -1.34% | 54% | -0.14 | -4.7% |
| midcap | 63d | n=345 | -0.59% | -1.28% | 54% | -0.07 | -2.3% |
| midcap | 126d | n=339 | -0.15% | -2.01% | 53% | -0.01 | -0.3% |
| smallcap | 21d | n=266 | -0.66% | -0.98% | 54% | -0.22 | -7.9% |
| smallcap | 63d | n=265 | -3.16% | -4.29% | 61% | -0.32 | -12.6% |
| smallcap | 126d | n=264 | -5.61% | -6.85% | 59% | -0.26 | -11.2% |
| cyclical | 21d | n=284 | +0.23% | -0.09% | 51% | +0.08 | +2.8% |
| cyclical | 63d | n=284 | +0.91% | -0.16% | 50% | +0.12 | +3.6% |
| cyclical | 126d | n=284 | +1.81% | -0.75% | 52% | +0.11 | +3.6% |
| **ALL** | 21d | n=1105 | -0.38% | -0.91% | 53% | -0.14 | -4.5% |
| **ALL** | 63d | n=1099 | -0.99% | -1.95% | 55% | -0.12 | -4.0% |
| **ALL** | 126d | n=1088 | -1.58% | -3.80% | 56% | -0.09 | -3.2% |

## 結果 B — 前後半穩健性(pooled，全股種)

| Proxy | Era | Horizon | n | mean excess | 跑輸率 | cond.Sharpe |
|---|---|---|---:|---:|---:|---:|
| P1 | 2016-2020 | 21d | 263 | -0.74% | 53% | -0.33 |
| P1 | 2016-2020 | 63d | 263 | -2.95% | 57% | -0.45 |
| P1 | 2016-2020 | 126d | 263 | -6.51% | 63% | -0.48 |
| P1 | 2021+ | 21d | 263 | +1.45% | 51% | +0.37 |
| P1 | 2021+ | 63d | 257 | +4.22% | 50% | +0.29 |
| P1 | 2021+ | 126d | 248 | +12.54% | 52% | +0.29 |
| P2 | 2016-2020 | 21d | 323 | -0.96% | 55% | -0.39 |
| P2 | 2016-2020 | 63d | 323 | -3.12% | 58% | -0.41 |
| P2 | 2016-2020 | 126d | 323 | -4.39% | 59% | -0.27 |
| P2 | 2021+ | 21d | 400 | -0.18% | 53% | -0.07 |
| P2 | 2021+ | 63d | 398 | -0.35% | 55% | -0.04 |
| P2 | 2021+ | 126d | 395 | -0.18% | 54% | -0.01 |
| pe_low(baseline) | 2016-2020 | 21d | 485 | -0.52% | 53% | -0.19 |
| pe_low(baseline) | 2016-2020 | 63d | 485 | -1.71% | 55% | -0.21 |
| pe_low(baseline) | 2016-2020 | 126d | 485 | -2.20% | 56% | -0.13 |
| pe_low(baseline) | 2021+ | 21d | 620 | -0.27% | 53% | -0.09 |
| pe_low(baseline) | 2021+ | 63d | 614 | -0.43% | 56% | -0.05 |
| pe_low(baseline) | 2021+ | 126d | 603 | -1.09% | 56% | -0.06 |

## 結果 C — A/B 增量:新軸 vs 現有 pe_pctile

核心問題:現有 `pe_pctile`(PE≤20%)已經捕捉幾多?加「EPS 週期高」條件(=P2)有冇**增量** drag?delta = P2 mean excess − pe_low mean excess(更負 = 新條件有增量識別週期頂陷阱)。

| Horizon | pe_low mean(n) | P2 mean(n) | delta (P2 − pe_low) | 判讀 |
|---|---:|---:|---:|---|
| 21d | -0.38% (n=1105) | -0.53% (n=723) | -0.16pp | ≈冇增量(pe_pctile 已捕捉) |
| 63d | -0.99% (n=1099) | -1.59% (n=721) | -0.60pp | 新軸有增量(更負) |
| 126d | -1.58% (n=1088) | -2.08% (n=718) | -0.49pp | ≈冇增量(pe_pctile 已捕捉) |

P1 冇對應嘅現有軸,佢嘅 benchmark 就係「同組籃子」本身(excess 已中性化組別 beta),所以 P1 mean excess < 0 本身即係「相對唔觸發嘅同儕」跑輸嘅證據。

## 結論(GO / DISPLAY-ONLY / NO-GO)

**啟發式判讀(下列數字由 script 計,最終判斷由作者覆核):**

- P1 mean excess: 21d +0.36%(n=526), 63d +0.60%(n=520), 126d +2.73%(n=511)
- P2 mean excess: 21d -0.53%(n=723), 63d -1.59%(n=721), 126d -2.08%(n=718)
- pe_low baseline mean excess: 21d -0.38%(n=1105), 63d -0.99%(n=1099), 126d -1.58%(n=1088)
- **A/B 增量(126d)**:P2 − pe_low = -0.49pp

- **P1 有 era sign-flip(126d)**:2016-2020 -6.5%(跑輸,外推陷阱成立)→ 2021+ +12.5%(反轉跑贏)。post-COVID 動能melt-up 期,極端高增長股繼續跑贏——外推陷阱主張喺呢個 regime 失效。
- **P2 效力隨期衰減(126d)**:2016-2020 -4.4% → 2021+ -0.2%(近乎歸零)。
- **P2 逐股種異質(126d)**:megacap -7.7%、midcap +3.5%、smallcap -6.1%、cyclical -0.3% ——「週期頂低-PE 陷阱」喺 midcap/cyclical(正正係文章講嘅 cyclicals)最弱,反而喺 megacap/smallcap 最強,與原主張嘅直覺相反。

### 判定:**DISPLAY-ONLY**

P2(週期頂低-PE 陷阱)方向對:forward excess 全 horizon 穩健為負(-0.5% ~ -2.1%),跑輸率 54-57%,cond.Sharpe -0.12 ~ -0.20——modest 但真。BUT 三個理由令佢**唔夠格入自動 sizing,只作 dashboard 提示/人手參考**:(1) 相對現有 pe_pctile 嘅增量得 ~0.5pp(邊際),pe_pctile 已捕捉大部分;(2) 只喺 megacap/smallcap 得,midcap/cyclical(文章嘅 cyclicals 本命)反而唔顯著;(3) 效力 2021+ 衰減近零。P1(動能極端外推)因 era sign-flip **NO-GO**——2016-2020 跑輸但 2021+ 反轉跑贏,唔可以單向用。**整體:P2 DISPLAY-ONLY,P1 NO-GO。**

## 誠實 Caveat

1. **Proxy ≠ 真比率**:trailing/forward P/E 用**分析師共識**做分母;本實驗兩個 proxy 只係佢危險象限嘅**可計算 backward-looking 代理**。P1 用已實現 TTM-EPS YoY(唔係 forward 預期)、P2 用自身歷史 EPS 週期位置(唔係共識隱含增長)。真比率捕捉「市場**預期**幾誇張」，proxy 捕捉「盈利**已經**去咗幾極端」——有相關但唔等同,呢個係最大 gap。
2. **PIT filing lag 係近似**:用固定 60 日,真實各公司/各季申報日有差異(10-Q vs 10-K)。lag 太短 = 殘留 look-ahead,太長 = 訊號過時。60 日偏保守;縮到 45 日結果方向唔應該變(未逐一測)。
3. **樣本量**:訊號係極端 tail(top decile / 低分位),逐股種逐 horizon 事件數可以好細,細價股組尤甚——見表內 n。cond.Sharpe 喺 n<30 時只作方向參考。事件有重疊(月 grid vs 126d horizon),有效獨立樣本少過 n。
4. **PE 分位用 expanding 全歷史**:早年样本少,而且**負 EPS 日 PE 未定義而剔除**——盈利波動大嘅cyclicals(memory/materials)喺蝕錢年份冇 PE 分位,會漏咗部分週期頂前的轉折。
5. **excess 中性化組別 beta 但唔中性化市場**:size-matched EW 籃子已剝走同組共同 move;若整個板塊同步見頂,個股相對籃子可以睇落唔輸,但絕對回報仍差——DISPLAY-ONLY 判斷已考慮呢點。
6. **survivorship**:universe 係今日仍上市嘅名,爆煲退市名(正正係 proxy 應該捕捉嘅)缺席,**偏向低估**訊號效力(保守方向)。

## 文獻對照

概念有文獻支持:**La Porta (1996)** 高 long-term-growth 預期股後續系統性跑輸;**Bordalo, Gennaioli, La Porta & Shleifer (2019, JF)** 分析師長期盈利增長預期被**過度外推**、高預期組 forward return 顯著為負;**Lakonishok-Shleifer-Vishny (1994)** value/glamour——glamour(高增長外推)跑輸。**如果本實驗測出「冇效」**,要分辨係(a) proxy 唔夠力(用已實現 EPS 代替共識預期,訊號被稀釋),定係(b) 主張喺**呢個 universe/期間**唔成立(2016+ 大型科技單邊牛,高增長外推持續有效,反而懲罰咗做空高預期)。兩者政策含意唔同:(a) → 值得等有 forward-estimate 數據再試;(b) → 呢個 regime 唔啱用呢個軸。結論會據實際數字判定,唔會一句「冇用」了事。
