# Result — FACTOR FAMILIES 續:MOMENTUM / LOW-VOL / RELATIVE-STRENGTH(+ 大綜合)

**Date:** 2026-07-05  **Scripts:** `exp_momentum_family.py`、`exp_lowvol_family.py`、
`exp_rs_selection_filter.py`  **Tag:** active ✅ —— 完成四家族嘅其餘三個(mean-rev 見
`2026-07-05_meanrev_family.md`)。資本效率 + 全網格 + 4 類別 + two-halves,2016+,10bps。

## 大綜合(先講結論,細節喺下)
四家族清出**兩個真引擎 + 一個 gate + 一個防守 tilt**:
| | 定性 | 穩健度 |
|---|---|---|
| **① 動能/趨勢** | 買強勢揸趨勢 = 側避跌浪(downside protection) | **少輸多贏:H1平穩牛≈B&H、H2跌浪先贏;micro兩半狂贏**(正版TSMOM重驗,見下) |
| **② 均值回歸/RSI-2** | 買弱勢搏反彈 | **regime-條件**(高波先 work,H2-only) |
| **Gate:Vol/VIX regime** | switch ①②,自己唔係引擎 | 低波→動能;高波→均值回歸 |
| **RS** | **選股**(揸 leaders,穩健)+ **filter**(揀 leader 買 dip) | 穩健(選股兩半贏) |
| **低波選股** | 唔係 alpha,防守 tilt(低回撤),且 survivorship | — |
**兩種可用組合**:(a) regime 層 switch(高波 MR / 低波動能);(b) **名股層合體 = RS 揀 leader × RSI-2 揀 dip**
(後者唔使等 regime,而且救返 RSI-2 嘅 regime 脆弱——見 RS 段)。

---

## MOMENTUM / 趨勢(`exp_momentum_family.py`)
時序動能 timer:price > SMA(入場期) 揸、< SMA(出場期) 走現金。網格 entry×exit SMA {50,100,150,200}。
- **大盤指數**(B&H 17.1/0.91):FULL 部署 10-18%/Sharpe 0.75-**1.17**,曝險 ~77%。**兩半都贏 B&H**
  (H1 Sharpe 至 1.24、H2 至 1.27)。CAGR≈B&H,價值在 Sharpe/低回撤。**穩健**。
- **Mag7**(B&H 34.3/1.17):FULL 部署 29-**42**%/Sharpe 1.15-**1.56**,兩半都勁(H1 至 1.74、H2 至 1.50)。
  **CAGR + Sharpe 都贏 B&H,穩健** —— 動能最強嘅籃。
- **細價股 / 板塊**:ABS 趨勢**弱**(Sharpe 0.16-0.72 / 0.16-0.64),僅僅貼 B&H,唔值得。
- **RS 趨勢(basket/SPY vs SMA)**:Mag7 兩半都強(至 1.82);大盤偏 H2(H2 至 1.69、H1 0.47-0.94);
  **細價/板塊 H1-only**(H1 Sharpe 至 2.38,H2 冧至負)——即相對動能喺呢兩類 2016-20 有、之後冇。
- **★ 動能 vs 均值回歸 = regime 互補**:動能穩健兩半,RSI-2 H2-only → 印證「vol regime 做開關」。

## LOW-VOL(`exp_lowvol_family.py`)
**(1) 選股(BAB 異常):** 低波籃 vs 高波籃(個股月度,132 月)。
| | 低波 CAGR/Sharpe/MaxDD | 高波 CAGR/Sharpe/MaxDD |
|---|---|---|
| FULL | +7.1/0.56/−29 | +14.5/**0.62**/−58 |
| H1 | +8.9/0.63/−29 | +34.2/**1.16**/−27 |
| H2 | +5.5/**0.49**/−19 | −1.0/0.09/−58 |
→ **低波異常唔成立**:高波 raw + Sharpe 喺 FULL/H1 反而贏(但**高波側 survivorship 嚴重**,死咗嘅高波股跌
晒出去 → 唔可信)。**唯一穩健**:低波 MaxDD 一路細(−29 vs −58)、H2 逆市企得住 → **低波 = 防守,唔係 return。**

**(2) 波動 timer(vol-pct 低=揸,高=走):** 大盤/Mag7 表面 Sharpe 靚(1.4-1.7 兩半),**但**:(a) 條件Sharpe
天生偏袒平靜日=半 artifact;(b) 同趨勢 timer 重疊;(c) 高波走現金 = **賣咗 capitulation 反彈**(對返
top-days + VIX 逆向)。學術 Moreira-Muir 撐、Cederburg 反,爭議 → **頂多溫和風控,唔係 alpha。**
**淨結論:vol = regime GATE(開關),唔係選股又唔係 standalone timer。**

## RELATIVE-STRENGTH(`exp_rs_selection_filter.py`)—— 用戶正確指出:RS 係 selection/filter 唔係 timer
個股宇宙 3143,126d RS(vs SPY)分 5 tier。**forward return 已 clip [-0.9,3.0] 殺 penny 爆炸**(未 clip 前
Q1 = +inf 污染,曾誤導成「Q5 最強」;clip 後真相不同——記錄為教訓)。

**(1) SELECTION(前望年化%,21/63/126/252d):**
| tier | FULL | H2 2021-now |
|---|---|---|
| Q5 leaders | 17.5/17.8/16.3/12.5 | 9.3/8.7/6.7/4.7 |
| Q1 laggards | 21.9/12.5/9.1/9.8 | 5.2/**−2.5/−6.1/−5.4** |
| 宇宙均值 | 14.4/12.1/10.3/9.2 | 7.0/4.2/1.6/0.9 |
→ **Q5 leaders 全 horizon 贏宇宙均值、FULL+兩半穩健 = RS-momentum 選股係真.穩健 edge**(最勁 21-63d)。
Q1 只短期(21d)彈、長 horizon 衰退、**H2 負數** = 純短期反轉、脆弱。21d 見 U 形(兩極>中間)。

**(2) FILTER on RSI-2(每筆%/勝%/效率%,entry<5):**
| tier | 每筆% | 勝% | 效率% |
|---|---|---|---|
| Q1 最弱 | +1.8 | 58 | +55 |
| Q5 最強 | +0.8 | 61 | +29 |
| Q3 中 | +0.2 | 61 | +6 |
→ 原始彈幅:**跌殘(Q1)> leaders(Q5)> 中間**;但 Q1 勝率最低(58%)、penny/survivorship、**唔可交易**。
**可交易版 = 買 Q5 leaders 嘅 dip**(質優、61%勝、清晰贏中間 +29 vs +6)。

**★ (3) FILTER TWO-HALVES —— RS gating 救 RSI-2 regime 脆弱(entry<5,每筆%/效率%):**
| tier | H1 2016-20(basket RSI-2 死) | H2 2021-now |
|---|---|---|
| Q5 leaders | +0.5/+17 | +1.0/+36 |
| Q2-Q4 中 | **−0.3~−0.1 / −9~−3(死)** | +0.5/+17~19 |
| Q1 deep-value | +2.4/+77 | +1.4/+46 |
→ **H1 中間 tier 死** = 正正解釋裸奔 basket RSI-2 點解 H1 死(basket≈平均≈中間)。**兩極生還**:Q5 leaders
兩半都正、Q1 deep-value 最勁但垃圾。**∴ RS-leader gating 令 RSI-2 兩半都 work = 補返 regime 脆弱。**

## 市值層補測(`exp_families_mktcap_tiers.py`)—— momentum + mean-rev × micro/small/mid/large × two-halves
(ETF 類別漏咗個股市值層;此補。個股籃等權,returns clip ±,survivorship 偏高睇相對。)
| tier | 動能(SMA趨勢) | 均值回歸(RSI-2) |
|---|---|---|
| micro <$300M | ✅ **最強**(H1 Sharpe 2.69,FULL 1.86) | ❌ **兩半全負**(落刀,FULL −13~−34) |
| small $300M-2B | ✅ 穩健兩半(Sh 0.76-1.22) | ⚠ H2-only;**H1 緊入場地雷**(<5/>75 −41) |
| mid $2B-10B | ✅ 穩健兩半 | ⚠ **H2 怪獸**(<5/>75 +101/2.61);H1 大地雷(<5 −43) |
| large >$10B | ✅ 穩健兩半(Sh 0.9-1.6) | ⚠ H2-lean(<5 +73/2.55);H1 緊入場負 |
→ **動能:全市值 × 兩 regime 通吃。均值回歸:regime-gated(H2)+ cap-gated(micro 死)+ 低波緊入場係地雷。**
買 dip 最靚 = **mid/large × 高波 × 鬆入場**;**micro 永遠唔好 dip-buy**(純動能標的)。

## RS LEVEL×TREND 2×2(`exp_rs_trend.py`)—— 修正「trend 假設」(hypothesis 一半錯,誠實記低)
LEVEL = 126d rel vs SPY 嘅 sign(leader RS>0 / laggard RS<0);TREND = RS line vs 自己 SMA50(升/跌)。
- **SELECTION**:**RS LEVEL 先係 edge;TREND 幾乎無關**且 regime 間會反 —— L+/T↑ 加速 leader FULL 最高(21d
  18.1 vs 宇宙 14.4)但 L+/T↓ 褪色 leader 一樣勁贏宇宙(16.7),**H2 褪色仲贏埋加速**(12.5 vs 10.2)。
  L−/T↑(弱但翻身)最差(H2 負)。→ **「褪色 leader = 陷阱」不成立;揸就揸 leader(RS>0),升跌唔緊要。**
- **FILTER on RSI-2**:**TREND 有用但方向同直覺相反** —— **「回調緊嘅 leader」(L+/T↓)嘅 dip 彈贏「加速緊」
  (L+/T↑),兩半穩健**(entry<5:H1 +0.4 vs +0.2、H2 +0.9 vs +0.7,62% 勝);避「弱又翻身」(L−/T↑,H1 −0.3)。
  機制:dip = 均值回歸,RS 跌緊 = 更超賣 = 彈更多;**「買 leader 回調」個「回調」本身就係短期 RS 下跌。**

## ★ RE-VALIDATION —— 正版 TSMOM 取代粗糙 SMA timer(`exp_momentum_proper.py`;修正上面結論)
用戶指出「price vs 單一 SMA」係粗糙 trend filter,唔係公認 momentum。改用 **time-series momentum
(Moskowitz-Ooi-Pedersen 2012):trailing L-月報酬 >0 就揸**(L=3/6/9/12,+ composite 6/9/12 多數決;
vol-scaling 未加=portfolio 階段)。條件Sharpe(composite)vs B&H:
| 籃 | B&H F/H1/H2 | TSMOM F/H1/H2 | 判 |
|---|---|---|---|
| **micro** | 0.78/1.40/0.27 | **1.32/1.66/1.03** | ✅ 兩半狂贏 |
| large | 1.01/0.97/1.06 | 1.06/1.09/1.03 | ✅ 兩半微贏 |
| small | 0.79/0.89/0.69 | 0.90/0.94/0.87 | ✅ 兩半溫和贏 |
| 大盤指數 | 0.91/0.91/0.92 | 1.07/**0.82**/1.28 | ⚠ H1≈/低,H2 先贏 |
| Mag7 | 1.17/1.48/0.91 | 1.30/1.42/1.19 | ⚠ H1≈B&H,H2 贏 |
| mid | 0.90/0.95/0.86 | 0.94/1.09/**0.83** | ⚠ 混合 |
| 板塊ETF | 0.67/0.58/0.80 | 0.40/**−0.08**/0.82 | ⚠ H1 負,H2 先贏 |
| 細價ETF | 0.53/0.57/0.48 | 0.38/0.26/0.45 | ❌ 弱 |
**修正**:(1) **收返「beats B&H 兩半」**——大盤/Mag7/板塊 momentum outperform 集中 **H2**,H1 平穩牛只 ≈ B&H
(之前 SMA「16 格揀最靚」誇大咗 H1)。(2) **但「momentum > mean-rev 穩健」仍成立,機制講清**:RSI-2 H1 蝕錢
(whipsaw),momentum H1 只 ≈ B&H(唔蝕)→ momentum **冇 regime 大輸**先係佢「穩健」真義,唔係「處處贏」。
(3) 正確模型:趨勢 = **側避跌浪**,有跌浪(H2)先顯現,平穩牛(H1)冇嘢好避。(4) **micro 例外兩半狂贏**。
(5) 甜區 ~9 月 lookback;composite 最穩。

## Conclusions
1. **動能 = 穩健引擎(少輸多贏),非「處處贏 B&H」**:價值 = 側避跌浪(H2/跌浪 regime 顯現,H1 平穩牛 ≈ B&H);
   **RSI-2 會喺 H1 蝕、momentum 只 ≈ B&H 唔蝕 → momentum 更穩健**。**micro 個股例外(兩半狂贏)**;細價/板塊 ETF 弱。
2. **低波:選股異常唔成立(高波側 survivorship);低波只係防守 tilt。波動 timer 半 artifact,唔係 alpha。
   Vol 嘅真正角色 = regime GATE(開關)。**
3. **RS 係穩健 SELECTION(揸 leaders,兩半贏宇宙)+ 好用 FILTER(揀 leader 買 dip)。**
4. **★ 最實收穫**:**RSI-2 dip × RS-leader filter = 兩 regime 都 work 嘅可部署組合**,解決裸奔 RSI-2 嘅
   H2-only。= 動能揀 what × 均值回歸揀 when。**再細化**:買 dip 揀「回調緊嘅 leader」(L+/T↓,RS>0 但短期
   RS 下跌)—— quality + 正超賣;避「弱又翻身」(L−/T↑)。
5. **市值**:動能全市值通吃;均值回歸只做 **mid/large × 高波 × 鬆入場**,**micro 純動能(dip=落刀)**。
6. **RS trend hypothesis 修正**:trend 對 SELECTION 無用(level 先係 edge)、對 dip-FILTER 有用但方向相反
   (回調 leader > 加速 leader)。誠實記低:我原假設「褪色=陷阱」錯。

## Caveats
- 資本效率階段;總財富=portfolio 階段(尤其動能/vol-timer 高曝險,vol-timer 疑走漏 bounce,待 total-CAGR 證)。
- 個股/RS/低波 = cache survivorship 偏高;Q1 deep-value 尤甚(penny/退市)。ETF 類乾淨。
- RS filter tier 用 pooled-distribution 分位(近似);未做逐日 cross-section。

## Confidence
- **HIGH**:動能穩健兩半、RS-momentum 選股兩半贏、RS-leader gating 救 RSI-2——皆 two-halves 確認。
- **MEDIUM**:低波 timer(爭議 + artifact 疑慮);Q1 deep-value 磁幅(survivorship)。

## Implication for Karst
- **可部署核心**:①動能(SPY/QQQ/Mag7,趨勢 timer,兩 regime)②**RSI-2 dip × RS-leader filter**(質優名,
  兩 regime)③Vol/VIX regime 做開關 switch 動能↔均值回歸。
- **唔使做**:低波選股(非 alpha)、vol-timer 當 alpha、RS-timer、細價/板塊 趨勢。
- **接線**:RS 做 tier-2 個股 selection(揸 leaders)+ gate RSI-2 入場;vol/VIX regime 餵 [[regime-and-fear-greed-findings]]
  嘅開關;動能趨勢做 tier-1 曝險/低回撤層。財富貢獻待 portfolio 階段。

---

## Addendum(2026-07-06 補存):vol-timer 全 4 類數字(細價/板塊此前從未落檔)

**背景**:`docs/2026-07-06_wiki_verification.md` 核實發現,原文只講咗大盤/Mag7 嘅 vol-timer 數
(「表面 Sharpe 1.4-1.7」),KARST_WIKI §5.6 嗰行「細價 —·板塊 —」明文標「呢兩類數未落檔」。本補存
用真數據(yfinance,`backtest/data.py`)重跑 `exp_lowvol_family.py` 嘅 **TIMER 部分**(SELECTION 鏡
已喺上面存過,無變,冇再跑),補齊 4 類全部格。

**Method 冇變**:vol-pct(63d realized vol 嘅 2 年滾動百分位)<entry 揸、>exit 走現金,entry∈{40,30,
20,10}×exit∈{60,70,80,90},2016+,10bps/turnover,報**條件 CAGR(部署年化)/條件 Sharpe/曝險%**,
FULL + H1(2016-20)+ H2(2021+)。**資料**:yfinance 即日拉取(SPY/QQQ/SPMO/IWM/IJR/11 SPDR/Mag7 共 23
個 symbol),non-cache,live。

### 大盤指數(SPY/QQQ/SPMO)—— B&H FULL +17.3%/0.92/−31%,H1 +17.2%/0.91/−31%,H2 +17.3%/0.93/−27%
最佳格:FULL `<30進/>60出` +20%/**1.49**/40%曝險;H1 `<10進/>70出` +22%/**2.01**/31%;H2 `<30進/>80出`
+23%/**1.40**/59%。**FULL/H1 大部分格(15/16、12/16)贏 B&H Sharpe**,只係鬆出場(>90)格穩定輸;H2
較弱(6/16 格輸)。

### Mag7 —— B&H FULL +34.4%/1.17/−49%,H1 +44.8%/1.48/−33%,H2 +25.5%/0.91/−49%
最佳格:FULL `<30進/>70出` +42%/**1.68**/55%;H1 `<10進/>70出` +49%/**2.07**/43%;H2 `<30進/>70出`
+39%/**1.51**/66%。**兩半大部分格贏 B&H**(FULL 16/16、H2 16/16 全贏;H1 得緊出場>60 一欄 4 格輸,
其餘 12 格贏)——4 類入面**最穩健**。

### 板塊ETF(11 SPDR)—— B&H FULL +10.4%/0.67/−37%,H1 +9.6%/0.58/−37%,H2 +11.1%/0.80/−20% 🟡 唔穩健
最佳格:FULL `<40進/>60出` +10%/**0.90**/50%;H1 `<10進/>90出` +9%/**0.80**/31%;H2 `<40進/>70出`
+13%/**1.14**/69%。**FULL 大致貼近/微贏(11/16 格贏),但兩半唔一致**:**H1 幾乎全輸**(15/16 格低過
0.58,得鬆出場單一角落例外)、**H2 幾乎全贏**(15/16 格高過 0.80)。→ regime-dependent,唔算穩健
timer(fail 咗兩半robustness 門檻)。

### 細價股(IWM/IJR)—— B&H FULL +9.8%/0.53/−44%,H1 +11.3%/0.57/−44%,H2 +8.6%/0.48/−30% ❌ 明確唔work
最佳格都輸或勉強打平:FULL 最高得 `<10進/>70出` +6%/**0.42**/32%(仍低過 B&H 0.53);H1 全數 16 格
**全部低過** B&H 0.57(最高得 0.36)。H2 48 格入面得 **2 格**貼近/高過 0.48(`<10進/>70出` 0.88、
`<10進/>80出` 0.80,兩格都喺曝險最低〔28-29%〕嘅角落,樣本細、疑 artifact)。**FULL+H1+H2 三期合共
48 格,46 格輸、2 格贏且喺低樣本角落**——4 類入面**最差**,同「edge 常喺細價股」嘅一般印象相反
(呢度反而係細價股令個 timer 明確唔 work)。

### 補充判定(完成 4 類覆蓋,呼應 backtest-testing-standard)
1. **原結論不變但要加「唔係全宇宙一致」嘅 caveat**:「vol-timer 頂多溫和風控,唔係 alpha」依然成立,
   但依家可以講得更準——**只喺大盤指數/Mag7 兩半都有(粗略)穩健**;**板塊 ETF regime-dependent**
   (H1 死、H2 生);**細價股decisively 唔 work**(近乎全格輸)。
2. **同「edge 喺細價股」教訓唔一致,值得記低**:呢個特定 vol-timer 機制**唯獨喺細價股表現最差**,同
   insider/RS 家族「edge 喺細價」嘅方向相反——提醒:唔係所有訊號都喺細價股有 edge,方向要逐個訊號驗
   唔可以套用一般印象。
3. **維持原判**:即使大盤/Mag7 格數靚,原文already 指出呢個係「條件Sharpe 天生偏袒平靜日嘅半
   artifact + 走漏 capitulation 反彈」(跟 top-days/VIX 逆向發現一致)——呢次補測只補齊覆蓋,冇推翻
   呢個機制疑慮,淨值判斷不變:**vol = regime gate,唔係獨立 timer/alpha**。

**Provenance**:yfinance via `backtest/data.py`,2026-07-06 即日拉取,23 symbols(SPY/QQQ/SPMO;
IWM/IJR;XLK/XLF/XLE/XLV/XLP/XLU/XLI/XLB/XLY/XLC/XLRE;AAPL/MSFT/NVDA/AMZN/GOOGL/META/TSLA),
2016-01-01 起,10bps/turnover,signal shift(next-bar)。SELECTION 鏡冇再跑(數字同上文,未變)。
