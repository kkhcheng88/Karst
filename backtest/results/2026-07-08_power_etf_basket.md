# Result — ai-power-grid 衛星:ETF 籃覆蓋 vs 持倉重疊研究(研究筆記,非訊號回測)

**Date:** 2026-07-08(同日更新:用戶確認「URES」= UTES,已補跑)
**Script:** `backtest/experiments/exp_power_etf_basket.py`  **Status:** active(描述性研究)

> **本檔非訊號回測** —— 冇 IC/alpha/勝率判定,純粹是「用 ETF 籃表達 ai-power-grid 主題,邊 2-3
> 隻組合覆蓋腿最多、重疊最少」嘅描述性統計研究,供用戶 sizing 決策用。

## Question

用戶想用 **ETF 籃**(唔揀個股)表達 `ai-power-grid` 衛星主題(confidence 0.33/late,
`thesis/wiki/ai-power-grid.md`),候選:URA、NLR、「URES」、XLU、GRID。目標:揀
「覆蓋最多子腿 + 持倉重疊最少」嘅 2-3 隻組合。用戶已持 URA 40 股(~$1.6k),將併入呢個衛星。

## Step 0 — 「URES」身份核實 → **用戶確認 = UTES**

第一輪核實:yfinance `Ticker('URES')` 回傳 `quoteType=MUTUALFUND`、`longName=None`、
`exchange=YHD`(Yahoo placeholder)、history 空 —— URES 唔係可交易上市 ETF;WebSearch 亦搵唔到。
當時暫代 URNM(Sprott Uranium Miners)入宇宙分析。

**用戶已確認:原意係 UTES(Virtus Reaves Utilities ETF)** —— 主動管理公用事業 ETF,
AUM $1.40B、費率 0.49%、日均量 17.8 萬股(2026-07-08 yfinance 快照)。已加入宇宙補跑;
URNM 保留做鈾腿對照(佢同 URA 嘅重疊/相關數據對「揀邊隻鈾 vehicle」仍有用)。

## Method

- 宇宙:`{URA, URNM, NLR, XLU, UTES, GRID, FCG}` + 基準 `{SPY, QQQ}`。FCG(天然氣 E&P 股 ETF)
  加入係對應主題筆記「最平乾淨表達 = EQT」呢條氣源腿嘅 ETF 版(FCG 持有 EQT ~4% 權重)。
- 全部 yfinance `download(auto_adjust=True)`,5y 窗(2021-07 起,1254 個交易日;3y 窗 751 日另計)。
- 持倉重疊:yfinance `Ticker.funds_data.top_holdings`(top-9/10),標準 overlap 量度
  `Σ min(w_a, w_b)`(共同持股各自權重取細嗰個加總)。
- 相關矩陣:pairwise 日報酬 corr,3y 窗 + 5y 窗(yfinance 5y history 由 2021-07 開始,
  已係「2020 起」要求可得嘅最長窗)。
- Beta:對 SPY / QQQ 日報酬 OLS beta(cov/var)。
- 基本統計:CAGR/年化波幅/MaxDD(3y / 5y)、費率、AUM、日均量(yfinance `info` 欄位)。
- **誠實框架**(用戶指定要求,寫入呢度):以下全部係**股票 ETF**(鈾礦股/電力設備股/公用股/
  天然氣 E&P 股),唔係商品或對沖工具。「top-10 持倉重疊低」≠「同大市低相關」——corr vs
  SPY/QQQ 全部一齊報,唔可以用低重疊包裝做「對沖」敘事。

## Data provenance

| Series | Source | Rows(5y 窗) | From | To |
|---|---|---|---|---|
| URA/URNM/NLR/XLU/UTES/GRID/FCG/SPY/QQQ | yfinance `download(period='5y', auto_adjust=True)` | 1254 | 2021-07-09 | 2026-07-07 |
| URES | yfinance `Ticker.info`/`.history` | 0(唔存在;用戶確認原意 = UTES) | — | — |

## Table 1 — 持倉重疊(top-10,Σmin(w_a,w_b);只列非零對)

| Pair | Overlap weight | 共同持股 |
|---|---|---|
| URA – URNM | **0.401**(極高) | CCO.TO, NXE.TO, KAP, UEC, EFR.TO, PDN.AX(6 名共同) |
| **XLU – UTES** | **0.257**(高) | CEG, AEP, SRE, ETR, VST, XEL(6 名共同)——兩隻公用 ETF 唔應該同時揸 |
| URA – NLR | 0.238 | CCO.TO, OKLO, NXE.TO, UEC |
| URNM – NLR | 0.228 | CCO.TO, NXE.TO, DML.TO, UEC |
| NLR – UTES | 0.083 | CEG(唯一共同) |
| NLR – XLU | 0.056 | CEG(唯一共同) |
| 其餘所有對(URA/URNM × XLU/UTES/GRID/FCG;XLU/UTES × GRID/FCG;GRID–FCG…) | 0.000 | 無 |

**驗證咗預期**:URA↔URNM↔NLR 三隻鈾/核 ETF 持倉高度重疊(0.23-0.40)。XLU↔UTES 重疊 0.257
(同屬公用板塊,6 個共同名)——**佢哋係同一條腿嘅兩個候選,唔係兩條腿**。UTES 對 URA/URNM/GRID/FCG
嘅 top-10 重疊全部 0.000,只透過 CEG 同 NLR 有 0.083 微弱交集。

## Table 2 — Pairwise 日報酬相關矩陣(3y 窗,751 交易日)

| | URA | URNM | NLR | XLU | UTES | GRID | FCG | SPY | QQQ |
|---|---|---|---|---|---|---|---|---|---|
| URA | 1.00 | 0.95 | 0.96 | 0.22 | 0.42 | 0.59 | 0.19 | 0.50 | 0.52 |
| URNM | 0.95 | 1.00 | 0.90 | 0.17 | 0.34 | 0.50 | 0.18 | 0.42 | 0.43 |
| NLR | 0.96 | 0.90 | 1.00 | 0.32 | 0.53 | 0.62 | 0.22 | 0.53 | 0.53 |
| XLU | 0.22 | 0.17 | 0.32 | 1.00 | 0.83 | 0.38 | 0.26 | 0.33 | 0.18 |
| UTES | 0.42 | 0.34 | 0.53 | 0.83 | 1.00 | 0.55 | 0.29 | 0.48 | 0.41 |
| GRID | 0.59 | 0.50 | 0.62 | 0.38 | 0.55 | 1.00 | 0.29 | 0.82 | 0.81 |
| FCG | 0.19 | 0.18 | 0.22 | 0.26 | 0.29 | 0.29 | 1.00 | 0.38 | 0.29 |

(5y 窗 1254 日方向一致:URA-URNM 0.96、XLU-UTES **0.88**、NLR-UTES 0.56、GRID-SPY 0.85、
FCG-URA/URNM 升到 0.39——鈾 ETF 同 FCG 喺 2021-22 能源上升週期一齊跑,3y 窗已滑落。)

**觀察**:URA/URNM/NLR 互相 corr 0.90-0.96(幾乎同一敞口)。XLU-UTES corr 0.83(3y)/0.88(5y)
——再次確認佢哋係同一腿嘅替代品。**UTES 對 URA(0.42)/NLR(0.53)/GRID(0.55)嘅 corr 全部
明顯高過 XLU 對應數(0.22/0.32/0.38)**——因為 UTES 重倉 IPP(VST/CEG/TLN),呢批股同
AI-power 敘事共振,同鈾/電網腿嘅相關自然更高。呢個係「主題濃度」嘅代價,唔係持倉重疊(top-10
重疊 0.000)。GRID 對 SPY/QQQ corr 0.81-0.82,大市 beta 重;XLU 對大市 corr 最低(0.33)但係
低 beta 防守性質,唔係負相關對沖。

## Table 3 — 對 SPY/QQQ 嘅 corr/beta(3y 窗)

| Ticker | corr vs SPY | corr vs QQQ | beta vs SPY | beta vs QQQ |
|---|---|---|---|---|
| URA | 0.50 | 0.52 | 1.39 | 1.08 |
| URNM | 0.42 | 0.43 | 1.22 | 0.94 |
| NLR | 0.53 | 0.53 | 1.21 | 0.92 |
| XLU | 0.33 | 0.18 | 0.35 | 0.15 |
| UTES | 0.48 | 0.41 | 0.68 | 0.44 |
| GRID | 0.82 | 0.81 | 1.10 | 0.82 |
| FCG | 0.38 | 0.29 | 0.69 | 0.38 |

**誠實框架落實**:XLU 對 SPY corr 低(0.33)係公用股低 beta(0.35)嘅結果,唔係反向敞口;
UTES beta 0.68 = 介乎 XLU(0.35)同大市之間,IPP 權重令佢防守性明顯弱過 XLU。GRID 係對大市
beta 最高、corr 最高嘅一隻——加 GRID 係加大市系統性風險。

## Table 4 — 基本統計(CAGR/波幅/MaxDD/費率/AUM/流動性)

| Ticker | CAGR(3y) | CAGR(5y) | Vol(3y) | MaxDD(3y) | MaxDD(5y) | 費率 | AUM($bn) | 日均量 |
|---|---|---|---|---|---|---|---|---|
| URA | 31.2% | 20.4% | 42.4% | -37.8% | -37.9% | 0.69% | 6.00 | 3.89M |
| URNM | 19.5% | 15.3% | 44.8% | -50.8% | -50.8% | 0.75% | 1.90 | 0.70M |
| NLR | 26.7% | 19.0% | 35.2% | -32.6% | -32.6% | 0.52% | 4.21 | 0.49M |
| XLU | 15.4% | 10.5% | 16.5% | -17.3% | -25.3% | 0.08% | 23.11 | 20.85M |
| **UTES** | **23.9%** | **16.5%** | 21.8% | -17.6% | -20.4% | 0.49% | 1.40 | 0.18M |
| GRID | 21.9% | 15.9% | 20.4% | -20.8% | -29.6% | 0.56% | 12.08 | 0.81M |
| FCG | 7.7% | 14.8% | 27.3% | -29.4% | -33.3% | 0.59% | 0.59 | 0.98M |
| SPY | 20.9% | 13.2% | 15.3% | -18.8% | -24.5% | 0.0945% | 781.2 | 54.5M |
| QQQ | 25.4% | 15.3% | 20.3% | -22.8% | -35.1% | 0.18% | 490.1 | 44.4M |

**重點**:UTES 3y CAGR 23.9% vs XLU 15.4%(+8.5pp/年)、5y 16.5% vs 10.5%(+6.0pp/年),
MaxDD 反而更淺(5y -20.4% vs -25.3%)——主動 IPP tilt 嘅往績遠遠冚過 0.41pp/年費率差
(注意:呢段正好係 AI-power 敘事最有利嘅窗,唔係跨週期證據)。URNM 5y MaxDD -50.8%
(商品性極強)。UTES 流動性最弱(17.8 萬股/日 ≈ $1,100 萬/日成交額)——對 $10-15k 部位無問題,
但唔好當佢係 XLU 級流動性。

## Table 5 — 子腿映射表(對照 thesis 價值鏈)

| ETF | 覆蓋子腿 | 對主題估值警告嘅關係 |
|---|---|---|
| **URA** | 鈾礦/濃縮(CCO/NXE/UEC/KAP)+ 少量 SMR/反應堆技術(OKLO 6.7%)—— 廣義「鈾+核組件」 | 唔含 ETN/ON/MPWR 呢批 90th+ 分位名;鈾礦股估值週期由鈾現貨驅動,唔係 AI-capex 分位 |
| **URNM** | 純鈾礦股 + 實物鈾信託(Sprott Physical Uranium Trust 14%)—— 最窄、最純「現貨鈾」代理 | 同上,更貼鈾現貨,較少 SMR/reactor-tech 稀釋 |
| **NLR** | 鈾礦(CCO/NXE/UEC)+ 核電 IPP/公用(CEG 8.3%、PEG 7.1%、Fortum 5.6%)+ SMR(OKLO 5.2%、SMR 4.8%)+ 零件商(BWXT 6.5%)—— 全鏈最廣單一 ticker | CEG 都貴,但 NLR 入面權重 8.3%,被鈾礦+公用稀釋 |
| **XLU** | 廣義受監管公用(NEE/SO/DUK/AEP/SRE/D/XEL ~7 隻合計 ~44%)+ AI-power IPP(CEG 5.6%、VST 3.5%、ETR 3.7%,**合計 ~13%**) | **AI 故事稀釋度高**:僅 ~13% 權重對應 AI 電力敘事,~87% 傳統受監管公用、利率敏感 |
| **UTES** | 主動管理公用,**重倉 AI-power IPP:TLN 11.6% + VST 10.0% + CEG 9.9% = top-3 合計 31.5%**(全部係 AI 資料中心 PPA 故事核心名),再加 ETR 5.1%;其餘 XEL/CNP/AEP/LNT/IDA/SRE 受監管公用 | **AI 濃度 ~37% vs XLU ~13%(2.8 倍)**——就係主題表達想要嘅嘢,但代價係:IPP 呢批名(VST/CEG/TLN)正正係 AI-power 敘事炒起嘅股,估值同鈾/quality 名一樣唔平,mean-revert 風險共擔 |
| **GRID** | 電網設備/EPC(ETN 8.5%!、PWR 8.1%!、ABB 8.1%、Schneider 8.3%、JCI 8.0%、National Grid 4.1%、Prysmian 3.9%、nVent 2.9%、Hubbell 2.6%) | **直接持有 thesis 點名嘅 ETN(99th 分位!)+ PWR**,合計 ~16.6%——「主題估值最擠腿」最直接嘅 ETF 化身,只係用非美股/多元工業股攤薄單一名風險 |
| **FCG** | 天然氣 E&P(WES/HESM/EOG/COP/FANG/**EQT 4.0%**/DVN/EXE/OXY/PR) | 持有 thesis「最平乾淨表達」EQT 但只 4% 權重——**弱/被稀釋嘅氣源代理** |

## Table 5b — 關鍵判斷:UTES 定 XLU 做「公用/發電」腿?

| 維度 | XLU | UTES | 判定 |
|---|---|---|---|
| (a) AI-電力主題濃度 | IPP ~13%(CEG 5.6+VST 3.5+ETR 3.7),~87% 受監管公用稀釋 | **IPP ~31.5% top-3(TLN 11.6/VST 10.0/CEG 9.9)+ ETR 5.1 ≈ 37%**,主動揀 AI-PPA 受惠名 | **UTES 勝**(2.8 倍濃度;衛星目的係表達主題,唔係買防守) |
| (b) 同其餘兩腿(URA/GRID)嘅重疊/相關 | top-10 重疊 0/0;corr 0.22/0.38 | top-10 重疊 0/0;corr 0.42/0.55 | **XLU 勝**(UTES 嘅 IPP 同 AI-power 敘事共振 → corr 較高;但注意呢個唔係持倉重複,係主題濃度嘅自然結果) |
| (c) 費率差 0.41pp/年值唔值 | 0.08% | 0.49% | **UTES 勝**——3y 跑贏 XLU +8.5pp/年、5y +6.0pp/年、MaxDD 更淺(-20.4% vs -25.3%),遠冚費率差;但呢段正好係 IPP 敘事最順嘅窗,主動優勢唔保證延續 |
| (d) 內部 pairwise corr(same combo) | URA+GRID+XLU = **0.397** | URA+GRID+UTES = 0.52 | **XLU 勝**(數字上;但見下面判詞) |
| 防守性 / 利率敏感 | beta 0.35,最防守 | beta 0.68,防守性減半 | 睇用戶目的:衛星係 offense,唔係 defence |
| 流動性 | 20.85M 股/日 | 0.18M 股/日(~$11M/日) | XLU 勝(但 $10-15k 部位兩者都無問題) |

**判詞**:(b)(d) 表面上 XLU 贏,但要拆開睇——UTES 對 URA/GRID corr 較高**唔係持倉重疊**
(top-10 重疊 0.000),而係「三條腿都真係載住 AI-power 敘事」嘅共振。用戶目的係**表達主題**,
唔係砌一個「主題內互相唔郁」嘅籃——如果純粹想 corr 低,揸 87% 受監管公用嘅 XLU 等於用
「唔係主題嘅嘢」溝淡個籃,腿覆蓋名存實亡。**所以「公用/發電」腿推薦 UTES**,前提用戶明白:
(i) 呢個選擇令成個籃更似「一注 AI-power」,mean-revert 時三腿一齊跌嘅機會更高;
(ii) UTES 嘅 IPP 名(VST/CEG/TLN)本身都係炒起咗嘅名,唔係平價腿。
如果用戶想要「主題曝險 + 防守 ballast」兩樣兼得,先至用 XLU(或 XLU/UTES 各半——但兩者
corr 0.83/重疊 0.257,各半嘅分散效益好薄,主要係攤薄費率同 IPP 濃度,唔係真分散)。

## Table 6 — 組合建議(2-3 隻;判準:腿覆蓋最多 + 內部 corr 最低 + 避開最擠估值腿)

| Combo | 成分 | 覆蓋腿 | 內部平均 corr(3y) | top-10 重疊(3 對) | 費率(等權) | Blended beta(SPY/QQQ,等權) |
|---|---|---|---|---|---|---|
| **A(推薦,主題表達優先)** | URA + GRID + UTES | 鈾燃料/核組件 + 電網設備(ETN/PWR)+ **AI-power IPP 濃度腿**(TLN/VST/CEG ~37%) | 0.52((.59+.42+.55)/3) | 全部 0.000 | 0.58% | 1.06 / 0.78 |
| **B(防守變體)** | URA + GRID + XLU | 鈾燃料/核組件 + 電網設備 + 廣義公用(AI 濃度僅 ~13%) | **0.397**((.59+.22+.38)/3) | 全部 0.000 | 0.443% | 0.95 / 0.68 |
| C | URNM + GRID + UTES | 純鈾/現貨 + 電網設備 + IPP | 0.46((.50+.34+.55)/3) | 全部 0.000 | 0.60% | 0.99 / 0.73 |
| D | URA + GRID + FCG | 鈾 + 電網 + 氣源(弱代理,EQT 僅 4%) | 0.357 | 全部 0.000 | 0.613%(冇平價錨) | 1.06 / 0.76 |

**推薦 Combo A(URA + GRID + UTES)**,理由:
1. **保留用戶已持嘅 URA**(40 股 ~$1.6k);URA vs URNM 差異細(corr 0.95、重疊 0.401),
   URA 流動性/AUM 優勢(3.89M vs 0.70M 股/日)令佢係更好嘅鈾 vehicle。
2. **UTES 取代 XLU 做公用/發電腿**(Table 5b 判詞):AI-電力濃度 ~37% vs ~13%,係「表達主題」
   同「買防守公用」嘅分別;3y/5y 往績跑贏 XLU 6-8.5pp/年,遠冚 0.41pp 費率差。
3. 三腿 top-10 持倉重疊全部 0.000;內部平均 corr 0.52 高過 Combo B 嘅 0.397,但呢個差距係
   「三腿都載住主題」嘅共振,唔係持倉重複——**如果用戶接受「一注 AI-power、跌市三腿齊跌」,
   A 係正解;如果想要防守 ballast,降級揀 B**。
4. 覆蓋 3/5 子腿(鈾燃料週期、電網設備、發電/IPP)。缺氣源(EQT)——FCG 只 4% EQT 權重,
   邊際效益薄,想要氣源曝險**直接持 EQT 個股**(thesis 點名「最乾淨便宜表達」)。
5. **valuation 警告仍在,而且 A 比 B 更擠**:GRID 揸 ETN(99th 分位)+PWR ~16.6%;UTES 揸
   VST/CEG/TLN 呢批 AI-PPA 炒起名 ~31.5%。**ETF 化只攤薄單一名風險,冇消除主題「quality 名貴」
   嘅估值風險;揀 A 等於自覺揸多啲呢個風險去換主題濃度。**

**Sizing 提示**:主題 confidence 0.33/late,用戶衛星額度 ~$41k / 九主題 → ai-power-grid
衛星倉位**唔好超過 ~$10-15k**(含已有 URA ~$1.6k)。若採 Combo A,大致等權(URA 保留、
UTES/GRID 各補至相近金額),總曝險封頂 $10-15k 內;confidence 0.33 屬偏低 + cycle late,
起步貼近下限($10k)更合理,留 headroom 等估值消風再加。

## Caveats

1. 全部係 **2020 後先熱嘅主題 ETF**(URA/URNM/NLR/GRID 喺 AI-power 敘事興起後先大幅擴 AUM;
   UTES 2015 年成立但 IPP tilt 係近年主動調整)——3y/5y 窗嘅 CAGR/corr 未經歷完整週期。
2. **UTES 主動管理往績唔保證延續**:3y/5y 跑贏 XLU 嘅窗正好係 IPP/AI-PPA 敘事最順嘅段;
   如果 kill condition 觸發(AI capex 指引轉降),IPP 濃度會由 alpha 來源變成 drawdown 來源。
3. **鈾 ETF 商品性極強**(現貨鈾價驅動),URNM 5y MaxDD -50.8%——鈾腿係「鈾現貨週期」曝險,
   同「AI 電力敘事」唔完全等同。
4. **XLU/UTES 利率敏感**——公用股 duration 特性冇拆開(冇對 10Y 殖利率 regression);UTES 嘅
   IPP 權重令利率敏感度低過 XLU 但仍在。
5. 「持倉重疊低」≠「風險分散」——GRID 對 SPY corr 0.82 全宇宙最高;XLU/UTES 對大市低 corr 係
   低 beta,唔係反向。**系統性風險冇消失,只係主題內部特異性風險有分散。**
6. AUM/expense/avgVolume 係 yfinance `info` 快照(2026-07-08);UTES 日均量僅 17.8 萬股,
   大額執行(>$100k)先需要留意,$10-15k 無問題。
7. 分析純粹基於 top-10 持倉(唔係全持倉),NLR/GRID/UTES 呢類 top-10 以外仲有長尾嘅 ETF,
   完整重疊可能同估算有出入。

## Implication

「URES」確認 = UTES(Virtus Reaves Utilities,主動公用,IPP 重倉 TLN/VST/CEG ~31.5%)。
**推薦 URA(已持)+ GRID + UTES**:覆蓋鈾燃料/核組件、電網設備(ETN/PWR)、AI-power IPP 三條腿,
top-10 持倉零重疊;UTES 對 XLU 嘅 AI 濃度優勢(37% vs 13%)+ 3y/5y 跑贏 6-8.5pp/年,冚過
0.41pp 費率差同較高嘅內部 corr(0.52 vs 0.397)。防守變體 = 換 XLU(Combo B)。缺氣源腿——
直接持 EQT 個股補足,唔好用 FCG。Sizing 封頂 ~$10-15k、起步貼 $10k(confidence 0.33/late)。
警告:Combo A 係自覺加大「主題估值擠」風險換主題濃度——kill condition 觸發時三腿齊跌。
