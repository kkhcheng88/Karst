# Layer 2 — 標的層 Timing(SPY / QQQ / SPMO 核心)

> 唯一問題:**「現在該不該對這個標的有 exposure?何時進出?」**
> 聚焦 3 個核心 ETF。期權怎麼表達在 `layer1_options.md`,不在這裡。

來源:Reference distillation §11–§25;`idea-05`(4 家族)、`idea-06`(flow)。
Tag:✅ verified / 📄 distilled / ⚠️ open

---

## 0. 地基判斷:指數上,TA 幾乎贏不了 Buy & Hold

| 證據 | 數據 | 來源 |
|---|---|---|
| SPY 35 策略 vs B&H | 只有 **1 個(RSI-2+200SMA)贏**,34 個輸(97%) | §15.1/§25.1 `RMbizBn9Pw4` |
| 疊指標摧毀報酬 | MA8/21 單獨 1,319% → 加 RSI 剩 **41%**(−97%) | §15.2/§20.8 `nXMEPQQYwQ0` |
| 簡單 > 複雜 | EMA200 trend 贏其餘 26 個策略 | §12.4 `RdE5E2W8AxY` |

🔴 **結論:Layer-2 = 一層精瘦的 trend / regime / IV 濾網,作用是「風險控制 + 結構選擇」,
不是 alpha。規則上限:1 指標 + 1 濾網。** 對 SPY/QQQ/SPMO 這種高效率標的,「更多 TA」
≈ 更差。

---

## 1. Trend Gate(家族 #1)— 唯一最穩的工具:200 EMA

| 規則 | 數據 | Tag |
|---|---|---|
| **EMA200 trend** | **PF 1.44,Sharpe 2.16,贏其餘 26 個策略(#1)** | 📄 §12.4 `RdE5E2W8AxY` |
| MA 8/21 cross | PF 1.36(可用,但**別疊 RSI**) | 📄 §12.4 |
| ❌ golden/death cross 50/200 | PF 0.87(太慢) | 📄 §12.4 |

**用途:LEAP / PMCC long leg 只在 `price > 200 SMA`(右側)開倉。= INV-6。**
這是整份 backtest 裡最穩健的單一 TA 工具。

---

## 2. Mean-reversion 戰術進場(家族 #2)— RSI-2(唯一 B&H beater,但濾網有爭議)

| 配置 | 結果 | Tag |
|---|---|---|
| **RSI(2) < 5 AND price > 200 SMA** | +258.6%(10yr)> B&H +239% | 📄 §15.1 `RMbizBn9Pw4` |
| ⚠️ 反例(stress test) | 同濾網 **−84%**(QQQ 196%→71.8%) | 📄 §11.6 `kkWmw1s1u1c` |

**用途:上升趨勢內買回調**(改善 LEAP 進場時點 / CSP 在 dip 賣)。
⚠️ **open:** 那個讓 RSI-2 贏 B&H 的 200SMA 濾網,在另一 test 反而傷 84%。
**濾網 regime-dependent——連最佳 edge 都脆弱。不釘死,待 walk-forward。**

> §20.9 說「trend > 反轉」,§21 說「反轉 > trend」——表面衝突,實則互補:
> RSI-2(反轉進場)**在** EMA200(趨勢濾網)**之內**,兩者疊起來就是上面那條,不是對立。

---

## 3. Volatility Regime(家族 #3)

| 規則 | 數據 | Tag |
|---|---|---|
| **BB squeeze breakout** | PF 1.22(A-tier) | 📄 §12.4 |
| ❌ BB mean reversion | PF 0.67 | 📄 §12.4 |
| ❌ VWAP(指數無效) | SPY +22% / QQQ +47%(只在 volatile asset 強) | 📄 §12.3 `3kr4qm2-74Q` |

擇時連結 layer1:**IC → VIX level(medium 15–25);CSP → IV rank(low,video 56/57);
LEAP 買方 → 低 IV**。

---

## 4. Relative Strength(家族 #4)— SPY / QQQ / SPMO 三選一

- **§20.13:underlying selection > strategy selection**(同策略 NVDA 賺 / TSLA 虧)。
- 用 relative strength 在三者間挑最強。**SPMO = S&P 500 Momentum,本身就是 RS factor 的
  打包**——當「momentum regime」訊號用。
- ⚠️ **open:** SPMO 不在 distillation(只測 SPY/QQQ/IWM);由 SPY/QQQ 外推,需自行驗證。

---

## 5. Flow(家族 #5,idea-06)

- **SPY/QQQ GEX** = regime fragility(非方向);GEX < 0 → 高波動 → 減倉(餵 `invariants`)。
- **Insider cluster buying** = 衛星選股訊號(非指數層)。

---

## 6. 進出場 / 停損(strategy-dependent,§18.6)

| 結構 | 出場 | 停損 | 來源 |
|---|---|---|---|
| CSP / IC / 0DTE(賣方) | **50% PT** | **無**(stop 傷賣方) | §18.5/§18.6 |
| QQQ LEAPS | **hold to expiration**(PT 砍半報酬) | 無 / 寬 | §18.6 |
| Deep OTM LEAPS(成長) | **let winners run** | 無 | §18.6 |
| 方向性 momentum | — | **寬 > 緊**(1.5ATR/5.0 target 最佳) | §18.1 `gKKWhA6ZN5Q` |

🔴 **賣方一律 no stop loss**(§18.5 鐵律,跨 IC/0DTE/bear call 全驗證)。
🔴 **方向性用寬停損**(§18.1:wide stop 64% 獲利 vs tight 54%)。

---

## 7. Regime 閘(決定能不能動 / 哪個家族當值)

| 觸發 | 動作 | 來源 |
|---|---|---|
| ADX > 25 / < 25 | 趨勢市用 trend 家族 / 震盪市用 mean-reversion | idea-05 |
| VIX 15–25 | IC 賣方唯一安全區 | §20.6 |
| IV rank low(CSP)| CSP 賣方最佳區 | video 56/57 |
| **FOMC 會議** | **賣方暫停**(short straddle −$3,337);可選 tactical:會前買 16Δ strangle(PF 3.96,全系列最佳風險調整)| §16.1 `qTs0smZwDWY` |
| VIX > 30 / GEX < 0 | 減倉 PMCC / 暫停 CSP | idea-06 |
| 宏觀 regime | 消費 Compass `regime_matrix` | Compass |

---

## 8. 反清單(指數上別碰)

疊指標(−97%)、VWAP(僅 volatile asset)、golden/death cross(PF 0.87)、
engulfing / candlestick patterns(PF 0.62,全系列最差)、scalping(SMB −$50K,PF 0.07)、
1 DTE、low VIX 賣方。

---

## 9. Minervini Trend Template(待蒸餾 → 編碼)

Minervini Trend Template(8 條 MA/價格條件)= 家族 #1 + #4 的**現成可編碼規則**,
不是新方法。蒸餾後填此處。書:`../../ebooks/Discretionary Momentum/.../Mark Minervini/`。

---

## Open Items

- [ ] 200 SMA 濾網 regime 依賴(§11.5 +258% vs §11.6 −84%)——walk-forward 解,**這是核心未決項**
- [ ] SPMO 無 distillation 數據,需獨立驗證
- [ ] Minervini Trend Template 蒸餾 → 編碼
- [ ] ADX regime 切換的具體閾值/實作
