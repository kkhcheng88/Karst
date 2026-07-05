# Result — MEAN-REVERSION FAMILY:RSI-2 之外有冇增量?(A 時鐘 / B vs SPY / C 避財報 + two-halves)

**Date:** 2026-07-05  **Scripts:** `exp_rsi2_meanrev_family.py`(A+B)、`exp_rsi2_twohalves.py`、
`exp_rsi2_news_filter.py`(C)  **Tag:** active ✅ —— 主結論偏 **negative(增量唔 pay)**,但釘實
「RSI-2 = regime-gated,唔係裸奔 alpha」。

## Question
RSI-2 只係均值回歸家族嘅一個角(超短 2 日 × time-series × 價格 × 振盪器 × 近乎無條件)。逐個測
「喺 RSI-2 之上加咗佢,係咪真係多啲 edge」:
- **A 反轉時鐘** = 同一 RSI-2 換 K 線大細(日/週/月)。
- **B 相對 SPY** = RSI-2 落喺 basket/SPY 比率,弱過 SPY 先買(用戶:落地只 vs 自己 + vs SPY)。
- **C 避財報** = RSI-2 超賣入場,避開財報窗(消息跌 drift、無消息跌先 revert)。RSI-2 係唯一「純價格、
  零資訊」訊號,最盲 → 理論上最需要 news filter。
- **two-halves** = 日K RSI-2「易」核心(大盤+Mag7)劈前後半防 regime 運氣。

## Method
4 類別(大盤指數 SPY/QQQ/SPMO、細價股 IWM/IJR、板塊ETF 11 SPDR、Mag7),資本效率(部署CAGR%/
條件Sharpe/曝險%),全 entry RSI2<{20,15,10,5} × exit RSI2>{75,80,85,90}。窗 2016-01-01+,
10bps/turnover(C 用 2bp/trade,個股層),訊號 shift 一格。C 用 defeatbeta earnings 日期
(`earning_call_transcripts().get_transcripts_list()`,report_date)。

## A1 — 日K self-RSI2(部署CAGR%/條件Sharpe/曝險%),全期 2016+
**大盤指數** B&H 17.1/0.91 · **細價股** B&H 9.8/0.53 · **板塊** B&H 10.4/0.67 · **Mag7** B&H 34.3/1.17

| | 大盤 <20/<10 (>75) | 細價 <15/<10 (>80) | 板塊 <10/<5 (>75) | Mag7 <20/<15 (>75) |
|---|---|---|---|---|
| 代表格 | +29/1.13 · +29/1.06 | +25/0.99 · +22/0.85 | +23/1.00 · +37/1.59 | +50/1.32 · +55/1.36 |
全期睇,日K RSI-2 四類都贏 B&H(尤其鬆入場,曝險 30-55%,交易數百=統計實)。**但 two-halves 揭穿咗
——見下。** 完整 16 格(A1/A2/A3/B × 4 類)喺 `exp_rsi2_meanrev_family.py` console。

## ⚠ TWO-HALVES —— 推翻「易」:優勢幾乎全喺 H2(2021+),H1(2016-2020)唔 work
**大盤指數**
| | H1 2016-2020 (B&H 0.91) | H2 2021-now (B&H 0.92) |
|---|---|---|
| <20/>75 | +8/0.40 | **+48/1.87** |
| <15/>75 | **−6/−0.07** | +51/1.94 |
| <10/>75 | **−6/−0.04** | **+67/2.30** |
| <5/>75 | **−17/−0.32** | +64/2.09 |
→ H1 成塊格 Sharpe < B&H 0.91,緊入場**負數蝕錢**;H2 Sharpe 去到 2.30。**靚 grid 係 H2 一手撐起。**

**Mag7**(H1 B&H 44.8/**1.48**,H2 B&H 25.5/0.91):H1 `<20/<15` 部署 43-54%/Sharpe 1.14-1.42 →
**仍低過 B&H 1.48**(順勢太強,揸住更好);H2 `<20/>75`=56/1.45、`<5/>75`=70/1.64 → 狂贏。
**Mag7 冇蝕但 outperform 一樣淨係 H2。** 細價/板塊同 pattern(H1 弱/負,H2 勁)。

**四類全部:RSI-2 贏 B&H 嘅優勢集中 H2;2016-2020 冇一類贏到 B&H,大盤仲蝕。**
機制:2016-19 = 超低波順勢爬(冇 dip、亂彈蝕手續費);2021-25 = 高波震盪(dip-buyer 天堂)。
**正正對返 VIX 三區 / `2026-07-05_rsi2_capital_efficiency.md`:RSI-2 高波先 work,低波順勢會死。**

## A2/A3 — 週K / 月K(換時鐘)
- **月K(~2月反轉)鬆入場出奇乾淨**:大盤 A3 `<10`(1.32-1.61)、板塊 A3 `<20-<15`(1.0-1.23),
  曝險 13-25%。**週K(A2)中間最弱最嘈。**
- `<5` 喺週/月K 全部曝險 <10% = 幾單交易(Mag7 A3 `<5`=85/3.95 只 2 筆)→ 噪音,不可信。
- 但月K 一樣冇做 two-halves;**時鐘換嚟換去改變唔到 regime 依賴本質**(同一均值回歸,同一 regime 條件)。

## B — 相對 SPY(弱過 SPY 就買)
- **質優得**:大盤 `<20/>75`=22/1.06、板塊 `<10/>90`=15/0.87、**Mag7 `<5/>75`=54/1.47**(Mag7 弱過
  SPY = 好長機會)。
- **細價股完全唔得**:多數負數(`<5/>75`=−9/−0.25)→ **小型股弱過 SPY 唔會追返,持續落後(係動能唔係
  反轉)。** 呼應反轉夾質優、唔夾細價持續弱勢。

## C — 避財報 filter(150 大型 + 300 細/中型,431 隻有財報日)
NO-NEWS(避財報)vs EARNINGS(財報窗內),每筆%/勝%/部署效率%/yr,代表格:
| | large NO-NEWS | large EARNINGS | **small/mid NO-NEWS** | **small/mid EARNINGS** |
|---|---|---|---|---|
| <20/>75 | +0.5/66/+21 | +0.7/62/+26 | **+0.7/64/+29** | +0.6/60/+22 |
| <10/>75 | +0.5/65/+21 | +0.7/62/+25 | **+0.8/64/+31** | +0.6/61/+22 |
| <5/>75 | +0.5/65/+20 | +1.0/64/+35 | **+0.9/65/+32** | +0.4/59/+12 |

**★ 結果分裂,正正對返 PEAD 文獻(細價漂移更強):**
- **大型股:避財報冇用甚至微傷** —— EARNINGS 入場每筆賺多啲(`<5` +1.0/eff+35),大型股夠效率、財報超賣照彈。
- **細/中型股:避財報有用** —— NO-NEWS 全面高過 EARNINGS,尤其極端 `<5`(NO-NEWS +0.9%/勝65/eff+32 vs
  EARNINGS **+0.4%/勝59/eff+12**)。**財報驅動嘅超賣喺細價會繼續插(drift),無消息超賣先彈。**
- **落地**:核心 sleeve = ETF/大型/Mag7 → **用唔著呢個 filter**;但若系統將來擇時個別**細/中型股** RSI-2,
  **應排除財報窗入場**。C = 有條件正面(細價),對可部署層中性。

## Conclusions(誠實,偏 negative)
1. **RSI-2 已經係短期均值回歸嘅表達;家族其餘部分對可部署層(ETF/大型/Mag7)冇送多啲易攞 edge**:
   A 換時鐘(月K 係另一乾淨時鐘但同 regime 依賴)、B vs SPY(只夾質優、細價唔得)、C 避財報(大型股
   冇用;**細/中型股有用=PEAD**,但非核心 sleeve)。
2. **最重要**:日K RSI-2 贏 B&H 嘅優勢 **regime-gated**——**H2(2021-25 高波)先 work,H1(2016-20
   低波)裸奔會流血(大盤負數)**。「易」係假象=2016-25 dip-buyer 天堂 + 樣本偏 H2。
3. **淨值收穫**:確認唔使砌 news-filter / 全宇宙選股 / 多時鐘複雜嘢——唔 pay。**真正要接嘅係
   RSI-2 × regime gate(VIX/vol)**,而唔係更多均值回歸變體。

## Caveats
- 資本效率階段;總財富=portfolio 階段。
- 週/月K `<5` + 兩半 tight-entry = 少樣本,睇鬆入場鬆離場嗰塊。
- C 大型股 only(top-250 by cap);small/mid 補跑後補結論。survivorship(ETF/megacap 乾淨,個股籃偏高)。

## Confidence: **HIGH(方向)** —— two-halves 係決定性
- 四類一致:RSI-2 outperform 集中 H2;H1 無一類贏 B&H → regime 依賴穩健。
- 同 VIX 三區 / RSI-2 capital-efficiency 主線一致(高波 work、低波死)。
- 增量三件(A/B/C)一致唔 pay,交叉印證。

## Implication for Karst
- **RSI-2 唔好裸奔部署**——2016-19 會慢慢流血。落地 = **RSI-2 × regime gate**(高波/震盪先開,接返
  VIX/F&G regime 研究線 [[regime-and-fear-greed-findings]])。
- 若要用 vs-SPY 相對反轉:**只落質優(大盤/Mag7/板塊),細價股唔好用**(持續弱勢)。
- 唔使投資做 news-filter / 全宇宙 XS 選股 / 多時鐘——已證唔 pay,慳返複雜度。
- Mag7 最耐揸但 outperform 亦係高波期;tier-1(SPY/QQQ)日K RSI-2 必須配 regime 條件。
