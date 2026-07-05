# Karst 風控/擇時層 — 結算報告(2026-07-05)

> **一份收埋成個「價量/擇時/風控層」(Phase 0/1/4 + 選股/突破/regime)嘅詳細報告。** 標準化量度、逐訊號
> 結算、決策矩陣、已關/未閉 sections、轉去 Phase 2/3。細節見各 `backtest/results/2026-07-05_*.md`;
> 索引見 `backtest/experiments/README.md`;跨 Phase 地圖見 `ARCHITECTURE.md`。

## 0. 一句結論
**價量/擇時層 = 風控/timing,唔係大 alpha。** Capital-efficiency 係**真但細**嘅 T1 擇時 alpha(+2-6%/yr,
`exp_alpha_decomp`),要靠個股/多-sleeve portfolio 兌現。**唯一乾淨改良 = 20 日高突破 timer。** 真 alpha
靶心 = **Phase 3 thesis(forward IC ≥ 0.05),未證。**

## 1. 標準化量度(所有訊號回測一律照此 — THE measure)
| 維度 | 定義 |
|---|---|
| **量度** | **資本效率**:部署CAGR%(只計在場日年化)/ 條件Sharpe(在場日)/ 曝險%。**唔用 Jensen α**(T2 β 拖累誤導) |
| **α 分解** | α = Cov(pos,mkt)[**T1 擇時技巧**] + (曝險−β)·mean_mkt[**T2 結構拖累**];T1>0 真但 index in/out 被 T2 食 |
| **覆蓋** | 4 類別(大盤 SPY/QQQ/SPMO・細價 IWM/IJR・板塊 11 SPDR・Mag7)+ 4 市值層(micro/small/mid/large 個股籃) |
| **穩健** | **two-halves**(H1 2016-2020 vs H2 2021+);size-matched benchmark(細價 vs IWM 非 SPY) |
| **紀律** | 全 entry×exit 網格(唔靜靜 drop 格);per-cell n;survivorship/成本/tail flag;下負面結論前對文獻 |
| **階段界線** | 呢層講**資本效率**(部署嗰陣);**總財富 vs B&H = portfolio 階段**先計 |
(來源:memory `backtest-testing-standard`;`tier1-metrics-decision`。)

## 2. 核心綜合 — 兩引擎 + 一開關 + filters
| | 定性 | 穩健度 |
|---|---|---|
| **① Momentum/趨勢** | 買強勢 = **側避跌浪(downside protection)** | H2/跌浪先顯,H1 平穩牛≈B&H;**冇 regime 大輸**;micro 兩半狂贏 |
| **② Mean-rev/RSI-2** | 買弱勢搏反彈 | **regime-gated(高波)+ cap-gated(micro=落刀)**;RS-leader filter 救 H1 |
| **Gate:Vol/VIX regime** | switch ①②,自己**唔係引擎** | 低波→動能;高波→均值回歸;低波選股/vol-timer 非 alpha |
| **RS** | **選股**(揸 leaders,兩半贏)+ **filter**(gate RSI-2 dip) | LEVEL 係 edge;TREND 只對 dip-filter 反向有用 |
| **可用組合** | (a) regime switch;(b) **RS 揀 leader × RSI-2 揀 dip**(名股層,救 regime 脆弱) | — |

## 3. 逐訊號結算(訊號 | 量度結果 | 信心 | 接線?)
| 訊號 | 量度結果(資本效率) | 信心 | 接線建議 | 檔 |
|---|---|---|---|---|
| **F&G 買恐懼/賣貪婪** | 部署CAGR+條件Sharpe 贏 B&H;甜區 extreme<5-10;活躍1/3-1/2 | HIGH(風控) | 恐懼加曝險/CSP 窗;`<10`門檻 | fg_timed_capital_efficiency |
| **RSI-2 mean-rev** | H2-only;H1 低波蝕;micro 落刀;mid/large H2 怪獸(+101/2.61) | HIGH(特徵) | **RSI-2 × RS-leader × 高波 gate** | meanrev_family |
| **RS 選股(leaders)** | Q5 全 horizon 贏宇宙、兩半穩健 | HIGH | Phase-1 選股 tilt | factor_families |
| **RS filter on RSI-2** | 買「回調緊 leader」(L+/T↓)最佳,兩半 | HIGH | gate RSI-2 入場 | factor_families(RS 2×2) |
| **Momentum timer** | **20日高突破 > TSMOM > SMA**;兩半贏、修H1 | HIGH | **Phase-4 20日高突破 timer** | breakout_momentum |
| **低波選股** | 高波籃 raw 贏(survivorship);低波=低回撤防守 | HIGH(非alpha) | 防守 tilt only | factor_families |
| **Vol timer** | 條件Sharpe 靚一半 artifact;走漏 capitulation | MED(非alpha) | 用 regime gate 唔用 timer | factor_families |
| **VCP 收縮型態** | 3次一致:無增量、輕微傷;IC≈0 | HIGH(negative) | **唔建** | vcp_pattern |
| **突破 SELECTION(Minervini)** | ≈/低過 B&H;risk-layer 斬贏家傷回報 | HIGH(negative) | 唔當 alpha;risk-layer=封尾部 | breakout_momentum |
| **GEX** | 對 VIX partial≈−0.08 無增量 | HIGH(negative) | **唔建**;VIX 已 subsume | gex_test |
| **Insider(Phase 3)** | 大型股 21d/63d 顯著;survivorship 打折 | MED | 已建,v3 待補分類 | insider_rigor/literature |

## 4. 決策矩陣 — 接乜入 spine(風控層)
1. **Phase 4 擇時**:加 **20日高突破 timer**(取代/補 SMA;比 TSMOM 快、修 H1)——當**風控/timing 欄**,絕不乘結構分。
2. **Phase 4 mean-rev**:RSI-2 **× RS-leader filter × 高波 regime gate**(裸奔 RSI-2 H1 流血)。
3. **Phase 1 選股**:RS-leader tilt(揸 leaders)。
4. **Phase 0 gate**:VIX/credit/RV(已有)= 開關;**唔加 GEX**;DIX 免費 flow context 可選。
5. **唔做**:低波選股當 alpha、vol-timer 當 alpha、VCP、Minervini 全套選股、GEX、細價/板塊 ETF 趨勢。

## 5. Sections 狀態
**✅ 已關(測完+落檔):** F&G-timing · mean-rev 家族(horizon/vs-SPY/news/two-halves)· 四因子家族 ·
RS level×trend · 市值層 momentum/mean-rev · 正版 TSMOM 重驗 · 突破 timer(SPEC D)· Minervini 突破+risk-layer ·
**VCP(3次一致 no-edge)· GEX(對 VIX 無增量)**。
**⚠ 未閉(細):** 突破 + **成交量確認**(cache 無量;唯一可能救 Minervini selection);VCP 量維度;
20日高突破 timer **接線入 `spine/timing.py`**(已測未接)。
**📁 Findings 位置:** `backtest/results/*.md`(30 檔,dated)← `backtest/experiments/README.md`(索引)←
`STATUS.md`+`ARCHITECTURE.md`+ auto-memory 摘要。本報告 = 風控層單一 synthesis 入口。

## 6. 轉向 — Phase 2 & 3(alpha 靶心)
風控層特徵徹底釘死,冇乜好再挖。真正推進 Karst 目標(可證偽 alpha,forward IC ≥ 0.05)嘅係:
- **Phase 3 質性 thesis**(唯一 alpha 門):價值鏈→ticker→一手驗證→crowding→confidence sizing;
  裁判 = forward-IC 累積(數月)。9 個 Type-B 已建但**未證**。→ 落地 pilot + 累積 forward IC。
- **Phase 2 資金流/敘事**(🔴 未建):flow/narrative;insider(已建 Phase 3)+ DIX(免費)可餵;
  同 thesis crowding/催化劑扣。
- **界線**:風控層(價量)= 防你爆;Phase 2/3 = 畀你嗰一擊。**下一個 session 重心 = Phase 3 落地。**
