# Layer 2 — 標的層 Timing(訊號)

> 回答唯一一個問題:**「現在該不該對這個標的有 exposure?」**
> 對所有標的通用(個股 / ETF)。期權怎麼表達在 `layer1_options.md`,不在這裡。

來源:`../../Reference/ideas/2026-06-24_idea-05-ta-breakout-timing.md`(4 家族)、
`idea-06-flow-positioning.md`(flow)、backtest distillation(RSI-2 等)。

---

## 核心洞察:TA 只有 ~4-5 個獨立訊號家族

TA 指標宇宙在外觀上龐大,在資訊含量上狹窄。砍掉冗餘後,只有 4 個 price-based
家族 + 1 個 flow-based 家族真正獨立。加第 6 個指標 = 零新資訊 + 噪音 + 假信心。

| # | 家族 | 回答 | 系統化規則 | 學術錨 |
|---|---|---|---|---|
| 1 | **Trend / Momentum** | 價格在漲嗎? | MACD hist > 0 / Donchian breakout + volume | Jegadeesh-Titman 1993;Asness 2013 |
| 2 | **Mean-reversion** | 過度延伸了嗎? | **RSI(2) < 5 + MA200 filter** | De Bondt-Thaler 1985;Connors 2008 |
| 3 | **Volatility regime** | 要爆發了嗎? | Bollinger BandWidth 1 年最低 10% 分位 + 突破上軌 | Mandelbrot;Bollinger |
| 4 | **Relative strength**(截面) | 比別人強嗎? | 52w-high proximity < 5% + trend filter | George & Hwang 2004 |
| 5 | **Flow**(非價格) | 機構在動嗎? | insider cluster buying / SPY-QQQ GEX | Seyhun 1986;Lakonishok-Lee 2001 |

🔴 **idea-05 已關閉「TA 探索門」:** 4 家族已完整覆蓋,別再找第 N 個方法。已 kill:
SMC、Elliott Wave、Fibonacci(冗餘)、KDJ/LWR/BBI(= Stochastic/MA 變體)。

---

## 已驗證的最高價值訊號:RSI-2 + 趨勢濾網

| 配置 | 結果 | Tag |
|---|---|---|
| **RSI(2) < 5 AND price > 200 SMA** | **+258.6%**(10 年)| 📄 dist §11.5 |
| 對照:SPY buy & hold | +239% | 📄 |
| 對照:RSI(2) < 10(無趨勢濾網) | +98.8%(輸 B&H 140%) | 📄 |

35 個策略只有這 1 個跑贏 B&H(2.9%)。**一行差別(`price > 200 SMA`)決定生死。**

⚠️ **open — 200 SMA 濾網的雙面性:** dist §11.1 說在 500 檔 RSI-2 籃子上,加 200 SMA
濾網**減少 12% 報酬**(濾掉一些深跌反彈);但 §11.5 在指數上,200 SMA 濾網是跑贏
B&H 的**關鍵**。兩者目標不同(籃子總報酬 vs 風險調整後跑贏)。**待回測解決,先不
釘死;Karson 的 ETF/指數情境傾向採用濾網。**

---

## Flow 家族(第 5 獨立源,idea-06)

| 訊號 | 定位 | 規則 | Tag |
|---|---|---|---|
| **Insider cluster buying** | 直接交易訊號 | ≥3 insiders / 30 天 / non-open-market / small-cap | 📄 Seyhun |
| **SPY/QQQ GEX** | regime fragility(**非方向**) | GEX < 0 = dealer 順勢 = 高波動 trend regime | 📄 |
| Positioning 報告(BofA/GS) | context,非 alpha | FMS cash < 4% = 頂部訊號 | 🟡 |

GEX 直接餵 `invariants` 的風控閘(GEX 翻負 → 減 PMCC)。Insider cluster + bottleneck
小市值疊加 = 雙重 edge(domain + flow),供衛星選股。

---

## Regime Gate(決定哪個家族當值)

- **微觀 regime:** ADX > 25 = 趨勢市(trend 家族當值);ADX < 25 = 震盪市
  (mean-reversion 家族當值)。trend 與 mean-reversion 天然反相關。
- **宏觀 regime:** 指向 Compass `regime_matrix`(Risk Appetite × Monetary)——
  決定「能不能動 / 多大倉」。Karst 不重建,消費其輸出。
- **波動 gate:** 賣方策略只在 medium VIX(15–25);VIX > 30 觸發減倉(見 `invariants`)。

---

## Minervini Trend Template(待蒸餾 → 編碼)

Minervini 的 Trend Template(8 條精確 MA/價格條件)是家族 #1(Trend)+ #4(RS)的
**現成可編碼規則**,不是新方法。蒸餾後填入此處作為 trend+RS filter 的具體實作。
書:`../../ebooks/Discretionary Momentum/.../Mark Minervini/`。見 `../lenses/`。

---

## Open Items

- [ ] 200 SMA 濾網雙面性(§11.1 vs §11.5)——回測解決
- [ ] Donchian / ATR breakout 在美股 swing 的 deflated Sharpe(idea-05 falsification)
- [ ] Minervini Trend Template 蒸餾 → 編碼為 trend+RS 規則
- [ ] Volume Profile / POC(需 tick 數據,難回測)——暫緩
