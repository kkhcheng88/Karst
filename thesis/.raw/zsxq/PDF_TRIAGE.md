# zsxq 投行 PDF 分流(2026-07-17)

範圍:`thesis/.raw/zsxq/pdf/` 27 份。只做分流判決,唔做 ingest/red-team,唔改 themes.yaml/wiki。
對照:`thesis/themes.yaml` 17 個 active theme(15 舊 + mag7-hyperscaler + semiconductor-cycle)。

⚠️ **環境限制**:呢部機冇裝 poppler(`pdftoppm`),Read 工具嘅 PDF 渲染路徑用唔到;改用 `pdftotext`
直讀文字層。6 份 PDF 嘅文字層本身壞咗(CMap/字型損毀,`pdftotext` 出嚟係亂碼雜湊)或者純圖片
(冇文字層),完全讀唔到內容,見下表同「讀唔開」一節。

## 總表(27 行)

| # | 檔名 | 類別 | 對應 theme/候選 | 一句判決 |
|---|---|---|---|---|
| 1 | 0522 Bofa The Flow Show | C | 市況/flow | Bull&Bear 8.8、AI/mega-IPO 令市場集中度逼近歷史泡沫;narrative-flow 原料 |
| 2 | 20260513 JPM Flows & Liquidity | C | 市況/flow | 三大 mega IPO lock-up 到期對指數 free-float 嘅機械性影響;流動性/市場結構原料 |
| 3 | 20260514 GS US Equity Views 散戶交易 | C | 市況/flow | 散戶交易量 4 月中以來 +28%、散戶持股~10%市值;結構背景非個股 thesis,narrative-flow 原料 |
| 4 | 20260515 GS Weekly Kickstart AI Momentum | C | 市況/flow | 「一個大交易」——科技佔 SPX 今年報酬 85%、動能因子急升;擁擠度背景,narrative-flow 原料 |
| 5 | 20260526 GS Futu Holdings 會議紀要 | C | 無(china caveat) | FUTU 中國業務監管/一次性罰款,中國自身持牌券商,唔入 theme;純市況參考 |
| 6 | 20260527 MS MSFT Infrastructure Monetization | **A** | mag7-hyperscaler | 見下 P1 |
| 7 | 20260527 Nomura Asia Insights 中國AI/地產/K-shape | 讀唔開 | 疑 C(china caveat) | 純圖片 PDF,文字層零;標題判斷屬中國宏觀市況,即使讀到都係 C |
| 8 | 20260529 BofA The Flow Show | C | 市況/flow | 「後泡沫:長期羞辱、短期狂妄」基調,SPX 創新高但廣度極窄(21隻);narrative-flow 原料 |
| 9 | 20260604 MS Broadcom Expectations miss | **A** | tpu-custom-silicon | 見下 P2 |
| 10 | 20260608 Bernstein Quantum Leap | B | 量子運算(候選) | CPU/GPU/QPU 三處理器未來,經濟價值要到~2030 先兌現,而家揀贏家太早;夠料開 discovery 但優先級低 |
| 11 | 20260611 BofA The Flow Show | C | 市況/flow | Bull&Bear 賣出訊號、科技 ETF 資金流創紀錄、1994-CPI 類比警號;narrative-flow 原料 |
| 12 | 20260616 JPM Broadcom TPU v9 CY28 | **A** | tpu-custom-silicon | 見下 P1 |
| 13 | 20260629 MS China EVs 訂單 | 讀唔開 | 無(china caveat) | 文字層損毀(CMap 亂碼)。標題屬中國車廠週度訂單情緒追蹤,china caveat 下即使讀到都係 C |
| 14 | 20260630 JPM Semiconductor Tech Materials | **A** | memory-supercycle / advanced-packaging / semicap-equipment | 見下 P1 |
| 15 | 20260630 MS Asia Summer School Powering AI Asia DC | 讀唔開 | 疑 A/ai-power-grid 亞洲對應(未證實) | 文字層損毀。標題暗示亞洲 AI 資料中心供電,可能係 ai-power-grid 亞洲版但唔同 ticker,需讀到先能確認 |
| 16 | 20260709 BofA The Flow Show | C | 市況/flow | 「無衰退/無加息/無減息/無掃貨」共識、Bull&Bear 9.5 極端賣出訊號、hyperscaler capex 共識$800B'26/$1T'27;narrative-flow 原料 |
| 17 | 20260710 GS US Equities Weekly Rundown | C | 市況/flow(觸及 ai-power-grid/semiconductor-cycle 情緒) | 對沖基金倉位:半導體本週淨買入、AI Power vs AI Hardware 配對 -4.5% WoW;純 flow 非證據 |
| 18 | 20260713 HSBC TSMC capex pressure | **A** | semiconductor-cycle / tpu-custom-silicon | 見下 P1 |
| 19 | 20260713 JPM TSMC 2Q26 sales | 讀唔開 | 疑 A(同 #18 重複) | 文字層損毀。標題同 HSBC TSMC 高度重疊(2Q26 guidance 高端達標、毛利率有望超標),即使讀到料同 #18 冗餘 |
| 20 | 20260713 MS Micro Meets Macro 2Q Preview | B(弱) | 無(廣度策略,非個股) | 等權>市值加權輪動持續、AI採用「可量化影響」升至 40%;無 ticker 級硬數,唔值得 ingest |
| 21 | 20260713 MS Semiconductors NA Weekly NVDA roadshow | **A** | semiconductor-cycle(NVDA監察軸) | 見下 P2 |
| 22 | 20260713 Nomura China Internet LLM專家電話 | 讀唔開 | 無(china caveat) | 文字層損毀。標題屬中國互聯網/LLM,china caveat 下即使讀到都係 C |
| 23 | 20260714 Bernstein Korea Naver neocloud | B | neocloud funding/SPV(候選) | Naver 起 Nebius 式 neocloud、SPV+GPU供應商融資+韓國主權AI 8.4GW背書;夠料開 discovery,但南韓外國實體非可交易 theme |
| 24 | 20260714 MS SpaceX DVFS | **A** | space-satellite | 見下 P2 |
| 25 | Global Semiconductors | **A** | ai-power-grid | 見下 P1 |
| 26 | Inside the 800VDC Revolution Part 1 | **A**(非B) | ai-power-grid | 見下 P1 |
| 27 | Seeking_Alpha_2026_H2_Top_Picks | 讀唔開 | 疑 C | 零文字層(疑掃描/截圖式)。按標題/類型判斷屬散戶多股精選合集,非單一 thesis,即使讀到都係 narrative-flow 原料 |

## A 類詳述(9 份)

### #6 — MS MSFT「Infrastructure Monetization」(2026-05-27)
- **theme**:mag7-hyperscaler(核心監察鏡,ETF-only MAGS/QQQ,監察 hyperscaler capex/雲增長/AI 兌現)
- **claim**:MSFT 部署 AI 資料中心產能明顯快過近期變現——裝機容量 FY24 ~5GW → MS 估 FY28 ~20GW;每 MW 營收雖然下降但唔足以抵銷容量擴張,暗示 Street 估計偏低,OW/PT $650(現價 $416)
- **硬數據**:GW 容量軌跡(5→20)、每MW營收/資本密度模型、PT 上調空間——可餵 mag7-hyperscaler kill_metrics 嘅 capex→monetization 兌現軸(現有 kill_metrics 用 MSFT commercial RPO/AI run-rate,呢篇補「容量 vs 營收」呢條獨立角度)
- **建議**:值得 INGEST,**P1**(hard 容量/貨幣化數字,直接對應 mag7-hyperscaler 監察嘅核心問題「capex 能否兌現」,唔係純 reiterate)

### #9 — MS Broadcom「Expectations miss amid very strong demand」(2026-06-04)
- **theme**:tpu-custom-silicon(AVGO)
- **claim**:PT 微升 $485→$502,「對本身 thesis 影響:大致不變」;標題暗示某項指引/細節未達市場預期但需求本身非常強勁
- **硬數據**:淨係 PT 調整,冇新結構性數字(未見具體 capacity/ASP/份額硬數)
- **建議**:唔算高優先 ingest 素材——偏 reiterate + 估值微調,**P2**(留意但唔急)

### #12 — JPM Broadcom「Ignore The Noise TPU v9 2nm ASIC CY28 Ramp No Delays」(2026-06-16)
- **theme**:tpu-custom-silicon(AVGO, TSM)
- **claim**:正面駁斥賣方/供應鏈流傳嘅 TPU 延誤傳聞——TPU v9 2nm ASIC 專案 CY28 量產如期,冇延誤;5年期 GOOG/AVGO 協議(3月簽)鎖定未來4代 TPU(v8-v11)、逐年營收承諾遞增至2031;Broadcom 較 Google 自研 COT 團隊領先18個月以上
- **硬數據**:2027 AI營收增長指引 2-2.5x YoY、2028 再 2x;新加坡先進封裝廠 8月投產;2.5D/3.5D 封裝(15x reticle)CY28 到位——可直接餵 magnitude/kill metrics
- **建議**:**值得 INGEST,P1**(以一手研究正面反駁看空傳聞,information-not-in-price,非 reiterate)

### #14 — JPM「Semiconductor Tech Materials — Feedback from meetings」(2026-06-30)
- **theme**:memory-supercycle(NAND/MU,SNDK)+ advanced-packaging/semicap-equipment(WFE 上修)
- **claim**:投資人對半導體/記憶體材料股情緒偏多頭,儘管估值有疑慮;NAND 定價展望轉更牛(Kioxia 效法 Micron 6月簽5年不可撤銷 LTA;NAND ASP 4-6月 QoQ +69-90%,料升到 Q4);WFE 市場預測上修至 $159B(+28%)/$205B/$237B(CY26-28),Terafab 可能推上 $250B+(CY28)
- **硬數據**:NAND 定價區間、WFE 美元金額、Terafab capex 規模($55-119B)——直接可餵 memory-supercycle kill_condition 嘅「LTA/SCA scorecard」呢條主軸(theme 自己標明呢係最關鍵嘅監察指標)
- **建議**:**值得 INGEST,P1**(全新量化 NAND 定價+WFE 讀數,直擊 memory-supercycle 現有 kill_condition 命門)

### #18 — HSBC「TSMC — Increasing capex pressure」(2026-07-13)
- **theme**:semiconductor-cycle(監察鏡,TSM)+ tpu-custom-silicon(TSM)
- **claim**:預期 2Q26 溫和超標(毛利率 68% vs 指引 65.5-67.5%);FY27 capex 估計上修至 $80.2B(由 $70.6B,高於市場共識 $65.2B),認為呢個數都未必夠追上代工緊張;2027 營收增長預估上修至 36% YoY,目標價升至 TWD3,350
- **硬數據**:capex 金額、2nm/3nm 產能增速(+78%/+41% YoY 2027)、2029 營收敏感度(+4-19%)——直接可餵 semiconductor-cycle kill_metrics 嘅 `tsm_monthly_rev_yoy`/`tsm_inventory_days_dio`
- **建議**:**值得 INGEST,P1**(業績前 capex 重估、硬數據、時效性強——搶在 TSMC 7/16 實際公布前 3 日)

### #21 — MS「Semiconductors North America Weekly — NVDA road show feedback」(2026-07-13)
- **theme**:semiconductor-cycle(NVDA 係明文監察軸而非買入 ticker——DIO/需求監察)
- **claim**:路演回饋確認 NVDA 近期基本面強勁,營收加速增長(~95% YoY,尚未到主要新產能週期);另揭露 NVDA 正試行「neocloud」信貸支援/收入分成新模式,幫細型雲端商上車
- **硬數據**:無新量化 capacity/ASP/份額數字,純定性回饋
- **建議**:唔值得 P1 ingest(無硬數),但 neocloud-信貸模式呢個角度值得標記 **P2**(同 #23 Naver neocloud 候選互相呼應)

### #24 — MS「Space Exploration Technologies Corp. — DVFS」(2026-07-14)
- **theme**:space-satellite(SPCX)
- **claim**:重申 OW,PT $300(現價 $139),核心論點 = 無可比擬嘅垂直整合(Dimensionality/Verticality/Flexibility/Speed)
- **硬數據**:更新 EPS 預估(2026e $0.28、2027e $2.18、2028e $6.29)+ PT——SPCX 覆蓋薄,估計調整本身有訊號值
- **建議**:值得 INGEST,**P2**(reiterate + 估值修正,非新結構性證據,但因為覆蓋稀薄故估計 delta 有參考價值)

### #25 — 「Global Semiconductors」(BofA,~2026-05-25)
- **theme**:ai-power-grid(TXN, ON, NVTS, WOLF, MPWR, VICR 重疊)
- **claim**:AI 類比電源 TAM 自下而上模型——每機櫃電源用料~25倍跳升($36K→~$300K/機櫃),800VDC 驅動嘅 AI 類比電源市場由 $7.9B 增至 CY30 $27B(CAGR 28%),份額領先 TXN/Infineon/ADI/ON
- **硬數據**:全新自下而上 TAM/份額數字——正正係 ai-power-grid theme 自己標明「priced ahead of ramp」缺嗰塊 magnitude 證據
- **建議**:**值得 INGEST,P1**(量化 TAM 建構、多個 theme ticker 份額判斷,直擊 magnitude 空白)

### #26 — 「Inside the 800VDC Revolution – Part 1」(SemiAnalysis)
- **theme**:ai-power-grid(非新 theme——內容深化現有 800VDC 論述,唔係新方向,故判 A 非 B)
- **claim**:800VDC 轉型三階段拆解(sidecar 改造→DC配電→SST終局),1GW IT負載下~5%機房電力節省(~50MW連續)
- **硬數據**:設備用料含量/MW 建置方法論、逐階段 BoM 細節——比現有 BofA 筆記更粒度化
- **建議**:**值得 INGEST,P1**(直接深化 ai-power-grid 現有 kill_condition/magnitude 證據,工程級細節優於已引用嘅資料)

## 讀唔開(6 份,已誠實記低)

| 檔名 | 失敗原因 |
|---|---|
| 20260527 Nomura Asia Insights 中國AI/地產/K-shape | 純圖片 PDF,`pdftotext` 輸出零文字(watermark hash) |
| 20260629 MS China EVs 訂單 | 文字層 CMap/字型損毀,`pdftotext` 只出亂碼字串 |
| 20260630 MS Asia Summer School Powering AI Asia DC | 同上,文字層損毀 |
| 20260713 JPM TSMC 2Q26 sales | 同上,文字層損毀 |
| 20260713 Nomura China Internet LLM專家電話 | 同上,文字層損毀 |
| Seeking_Alpha_2026_H2_Top_Picks | 純圖片/掃描式,零文字層 |

**根因**:呢部機冇裝 poppler-utils(`pdftoppm`),Read 工具嘅 PDF 圖片渲染路徑用唔到;`pdftotext`
可以救返文字層完好嘅 PDF(21/27 份成功),但對純圖片或字型/CMap 已損毀嘅 PDF 完全無力。要讀返呢
6 份需要:(a) 裝 poppler-utils 啟用 OCR-via-image 路徑,或 (b) 另外攞一份文字層正常嘅版本。

## 建議正式 INGEST 名單(6 份,connected 排序)

1. **JPM Broadcom「Ignore The Noise TPU v9」(#12)**——以一手研究正面駁斥市場流傳嘅延誤傳聞,附
   多年營收承諾同產能時程硬數,information-not-in-price 程度全批最高。
2. **HSBC TSMC capex pressure(#18)**——硬 capex/毛利率/產能數字,同時餵 semiconductor-cycle
   同 tpu-custom-silicon 兩個管道,業績前發表、時效性強。
3. **JPM Semiconductor Tech Materials(#14)**——NAND 定價同 WFE 硬數據直擊 memory-supercycle
   自己標明最關鍵嘅「LTA/SCA scorecard」監察軸。
4. **Global Semiconductors(#25)**——ai-power-grid 自下而上 TAM/份額量化,正中 theme 自己承認
   缺席嘅 magnitude 證據缺口。
5. **Inside the 800VDC Revolution Part 1(#26)**——工程級深化 ai-power-grid 核心需求驅動嘅粒度
   證據,優於現有已引用資料。
6. **MS MSFT Infrastructure Monetization(#6)**——mag7-hyperscaler 呢個核心監察鏡首份「容量 vs
   貨幣化」硬數據,直接補強其 kill_metrics 監察面。

排序理據:6 份全部帶「非重複」硬數據且各自對應唔同 theme/kill_condition 缺口(冇兩份餵緊同一條
軸),1-3 屬供應鏈上游強證據(半導體週期本身),4-5 屬 ai-power-grid 需求端量化,6 屬 core-monitor
早期警號補強——覆蓋面互補而非重疊。#9/#21/#24(Broadcom reiterate/NVDA roadshow/SpaceX DVFS)
降做 P2,留待下一輪或有新硬數據時再考慮。
