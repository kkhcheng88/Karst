# Crypto — Karst 框架下有冇站得住腳嘅 thesis?(研究報告)

- 日期:2026-07-11
- 方法:同今日 discovery-radar 一樣嘅紀律 —— 第一手 earnings-call transcript 逐字引句、beneficiary-vs-victim 判定、read-full-context、priced-in gate。唔靠第三方報告轉述,唔靠 agent 記憶。
- 語料:`thesis/corpus.db`(195,959 docs,含以下 crypto 候選嘅 transcript 覆蓋)。
- 結論(先講):**冇搵到 STRONG 候選喺 Objective-B(供給約束+定價權)框架下成立。** BTC/ETH 本身係 NOT-APPLICABLE(方法論根本觸唔到),而且係一個要用戶做嘅 design decision;礦企/交易所/穩定幣三條線最多去到 WEAK / NOT-APPLICABLE。逐條理由喺下面。

---

## 0. 先 confirm:現有 15 個 thesis 冇任何一個覆蓋 crypto

- `thesis/themes.yaml`:9 原有 + 6 個 2026-07-11 discovery-radar 新增 = 15 個 thesis,全部係半導體/記憶體/電力/航太/太陽能/氣體壓縮/藥用包裝/能源等實體供需主題。**冇一個 ticker、冇一個 meta_factor、冇一個 note 提及 crypto/bitcoin/穩定幣。**
- `backtest/spine/universe.yaml`:grep 全無 crypto/bitcoin/COIN/MARA/RIOT/stablecoin。
- 即係話:今次係從零判斷 crypto 應唔應該入框架,唔係補一個已存在嘅缺口。

---

## 1. BTC / ETH 本身(as an asset)—— 判定:**NOT-APPLICABLE-TO-OBJECTIVE-B + 需要用戶 design decision**

### 1a. 方法論層面:Objective B 根本觸唔到 protocol 資產
Objective B 嘅整個機制係「讀公司自己喺 earnings call 講嘅 constraint-language」。BTC/ETH:
- **冇公司、冇管理層、冇 earnings call、冇 transcript。** corpus.db 對「BTC」「ETH」as an asset 一句 first-person 供給語言都攞唔到(佢哋唔存在於 transcript 宇宙)。
- 換言之唔係「查完冇證據」,而係**呢個資產類別根本唔喺 Objective-B 方法論嘅定義域入面**。同量子(RGTI/IONQ/QBTS)被 §3f 排除嘅理由部分重疊,但更徹底:量子起碼有公司有 transcript(scanner 對佢哋「靜晒」係證據);BTC/ETH 連被 scanner 掃嘅對象都唔係。

### 1b. 就算勉強講「供給約束」= halving,呢個訊號係框架最唔想要嗰種
- BTC 供給 schedule(21M 上限 + 每 4 年 halving)係**全球公開透明咗 15 年**、係整個資產類別最人盡皆知嘅事實。Karst discovery-radar 要嘅係「supply-tight × **unloved/未被發現**」象限(見 `results/2026-07-09_priced_in_gate.md`;gas-compression USAC 2nd pctile 之所以係新批 confidence 最高,正正因為未被 reprice)。BTC halving 係反面:**supply-known × maximally-discovered**,零「未被發現」edge。
- ETH 更加冇「供給約束」可言:post-Merge PoS + EIP-1559 burn,net issuance 可正可負、由 protocol 用量同治理決定,**根本唔係一個固定樽頸**。連「透明但固定」都算唔上。

### 1c. 佢真正嘅性質:macro/flow 資產,唔係個股供需樽頸
- BTC/ETH 價格由 adoption 敘事、ETF 資金流催化、halving 里程碑、宏觀流動性驅動 —— **無營運槓桿、無公司定價權**。呢啲係 macro/flow 特徵,對應嘅係用戶講嘅 **Objective A(sector-rotation/宏觀流層)**,唔係 Objective B(個股供給樽頸層)。
- 但要老實:即使喺 Objective-A 類比下,Karst 現有嘅宏觀擇時研究(fear/greed)已經得出 **α≈0 = risk knob 唔係 alpha**(記憶:regime-and-fear-greed-findings)。而且 Objective-A 板塊層本身仲係一個**未建成嘅 queued 實驗**(§3h),連股票板塊都未接線,更加冇一個「加密資產類別」嘅接口。

### 1d. 所以呢條線係 design decision,唔係 agent 砌框架
把 BTC/ETH 加入 core allocation 等於**新開一個資產類別 + 一套新方法論**(托管/custody、sizing、波動率、同 SPY 嘅相關性同 drawdown、對「MaxDD 貼 SPY」mandate 嘅衝擊、點量度 edge)。呢個正正係:
- §3f 講嘅「想玩 = 另一個投機 sleeve、另一套規則(里程碑、極細注、option 式)」;
- thesis `DESIGN.md` §6 + 專案慣例講嘅「adopt a NEW thesis type / 新方法論」= **人做決定嘅 gate,唔係 agent 自砌**;
- karst-role 記憶:範圍內俾具體 call,範圍外老實講「無依據」唔扮有。

**Angle-1 判定:NOT-APPLICABLE-TO-THIS-FRAMEWORK(Objective B 觸唔到);如果用戶想要 crypto 曝險,係一個要用戶拍板嘅 design decision(新 sleeve/新規則),agent 唔應該自己加 BTC/ETH exposure 或自砌新框架。**

---

<!-- 以下角度由 transcript 逐字證據支撐,待 subagent quote-harvest 完成後填入 -->

## 2. 比特幣礦企

Corpus 覆蓋(`corpus.py ticker <TK>`,2026-07-11 量度):MARA 30 篇(2014-2026)、RIOT 13 篇(2012-2026)、CLSK 20 篇(2021-2026)、CORZ 11 篇、IREN 16 篇、CIFR 19 篇、WULF 13 篇、HUT 24 篇 —— 覆蓋充足,唔使 prefetch 新資料。

### 2a. Pure-play 挖礦(MARA、RIOT、CLSK)—— 判定:**FAIL(commodity beta,冇結構性定價權)**

派 subagent 掃全部 63 篇 transcript,結論非常乾脆:**"pricing power" 呢個詞喺 63 篇 transcript 入面得出現一次**(MARA 2022-05-04),而且係用嚟講**礦企冇呢樣嘢**——真正有 pricing power 嗰個係 ASIC OEM。**"sold out"/"price-taker"/ASIC 短缺投訴一次都冇出現過。**

**判死引句(MARA,Fred Thiel CEO,2022-05-04,分析師問 ASIC cost-per-terahash 會唔會同 BTC 價格脫鈎):**
> "Yes. So at the end of the day, **the price of Bitcoin does end up driving it, because it drives demand.** ... you are going to find is miners maybe capital constrained... you are going to see a glut kind of equipment like in prior cycles. And so pricing, **the buyer is going to have pricing power.** ... today only **Bitmain arguably has 65% of the market.**"

呢句一次過確認兩件事:(1) ASIC 價格跟 BTC 價格走,唔係獨立議價空間;(2) 管理層自己點名真正瓶頸擁有者係 **Bitmain(~65%市佔)/ MicroBT / 上一層嘅 TSMC/Intel** —— 即係 ADI trap 教識我哋嗰種:礦企係 victim/customer,唔係 beneficiary。

**Difficulty auto-adjustment = 結構性 price-taker 機制(MARA,Salman Khan CFO,2026-05-11 最新一季):**
> "We mined 2,247 Bitcoin... approximately 39 fewer BTC than prior year period, **reflecting a higher network difficulty level**..." / "Revenues in Q1 of 2026 were $174.6 million compared to $213.9 million... **primarily driven by an 18% decrease in Bitcoin's average price**."

**RIOT 一句道出挖礦而家淨係「monetize megawatt 嘅工具」(Jason Les CEO,2025-10-30):**
> "We don't see Bitcoin mining operations as the end goal, but instead as **a means to an end, and that end is maximizing the value of our megawatts.**"

**CLSK 挖礦降格做「功能貨幣」(Gary Vecchiarelli CFO,2026-05-11):**
> "**Bitcoin mining is really our functional currency going forward, and that's what's gonna pay the bills** until we get... a stabilized lease."

三隻嘅共通結構:BTC 價格跌 → revenue 跌(price-taker);全網算力升 → difficulty 升 → 同一注電力挖到愈嚟愈少 BTC、單位成本愈嚟愈貴(協議自動削你優勢,唔係公司自己嘅結構性優勢);ASIC 一時買平一時賣舊機,價格全部跟 BTC 走,冇一句「supply-constrained/allocation」嘅供給訴求。呢個係教科書式 commodity beta,同 §3f 講嘅「無規模產品、無供給約束、無 allocation 語言」嗰種被排除主題性質相似(雖然呢度連公司都有,但供給側完全唔喺公司自己手上)。

**唯一近似「owned bottleneck」嘅例外**——RIOT 自己擁有一間 switchgear/transformer 製造商 ESS Metron(Jason Chung CFO,2026-04-30):
> "Low and medium voltage switchgear, transformers, and power distribution centers are among the **most severely constrained components** in the data center supply chain... **Because Riot owns a dedicated switchgear and power distribution manufacturer**, we can sequence, prioritize, and de-risk..."

呢句雖然係真.beneficiary 語言(擁有稀缺零件生產商),但講嘅係**data-center 電網設備**,唔係 ASIC/挖礦,屬於下面 2b 嗰個 power/AI-HPC 故事,唔應該計入挖礦 thesis。

**2a 判定:MARA/RIOT/CLSK 挖礦業務本身 = FAIL。** 冇結構性供給樽頸、冇定價權(協議 difficulty 機制結構性排除呢個可能),BTC 價格 beta 加 network difficulty 週期性,同 HAL/PTEN 油服股喺上升週期先講「sold out」嘅 commodity-beta 陷阱性質一致。

### 2b. AI/HPC 電力 pivot 前礦企(CORZ、IREN、CIFR、WULF、HUT)—— 判定:**NOT-A-DISTINCT-THESIS(已被現有 ai-power-grid thesis 覆蓋)**

呢批已經由純挖礦轉型做 hyperscaler AI/HPC hosting/托管。查證 ~15 份 2025-2026 transcript(subagent 8 個 tool call 核實),結論非常一致:**佢哋自己講嘅樽頸,同現有 `ai-power-grid` thesis(GEV/ETN/PWR/GNRC/SPXC/CAT)一字不差 —— 只係由「賣設備嗰邊」搬去「租電力嗰邊」講。**

- **WULF**(Paul Prager CEO,2026-05-08):"the broader AI build-out ... is increasingly constrained by power, including interconnection delays, transmission limitations, the need for new generation ... **The constraint is not GPUs, it is power.** ... We are fundamentally a power company that builds digital infrastructure."
- **HUT**(Asher Genoot CEO,2026-05-06):"**Power is a scarce resource. Those who control access to power will ultimately shape the industry.**" —— 但同一位 CEO(2026-02-25)又講緊自己**買緊** "high to medium voltage breakers at the substation, different transformers"(即係 ETN/switchgear 嗰類設備嘅**買家**,唔係擁有者——victim/customer 角色)。
- **CORZ**(Adam Sullivan CEO,2026-03-03,全批最關鍵一句):"power is often treated as the bottleneck ... we think that can be overstated. **In practice, the bigger constraints are often securing long lead equipment and lining up experienced general contractors** ... We already have more power in our pipeline than we can build."—— 連公司自己都話真正瓶頸喺上游設備/EPC 層,唔喺自己度。
- **CIFR**(Tyler Page CEO,2025-11-03 / 2026-05-05):"scarcity of energy capacity and frenzied demand from tenants" + "a site that is already energized ... trades at a premium" —— beneficiary of 已energized interconnect,但呢個都係 ai-power-grid 講嘅「interconnection queue」稀缺,唔係加密特有機制。
- **IREN**(Kent Draper CCO,2026-02-05):"Power is the scarce resource today" + "constraints ... whether it's long lead time procurement or skilled labor."

**Beneficiary/victim 雙重身份**:呢批公司對「已 energized 嘅電力/interconnection」係 beneficiary(擁有稀缺資產,可以加租金),但對「transformer/switchgear/breaker 設備」係 victim/customer(佢哋喺搶同一批 ETN/GEV 賣緊嘅嘢)。管理層自己(CORZ、IREN)仲主動將樽頸歸因去「長前置期設備 + 承包商」。

**判定:呢五隻唔係獨立 crypto thesis,係現有 `ai-power-grid` thesis 嘅下游表達(「邊個揸緊已通電嘅 megawatt」呢條腿)。** 加入做新 thesis 會同 ai-power-grid 重複算 exposure。唯一可能差異化嘅角度係「2021-2023 年提早圈落嘅 interconnect queue position」timing/optionality 優勢(HUT/CIFR 都強調呢啲 interconnect 係 AI 需求塞爆 queue 之前搞掂),但呢個都係「電力稀缺嘅受益者」,唔係加密特有故事,未做深度驗證,唔升做 thesis。

---

## 3. Crypto 基建 / 交易所(COIN)+ 穩定幣發行商(CRCL)

Corpus 覆蓋:COIN 21 篇(2021-2026),CRCL 3 篇(2025-11 至 2026-05,2025年5月先上市)。Subagent 掃咗全部 12 篇 transcript 嘅 capacity constraint / waitlist / backlog / allocation / lead time / sold out / limited supply / scarce 呢類詞:**零命中**(唯一「allocation」命中係資本配置/回購,唔係產能分配)。

### 3a. COIN —— 判定:**FAIL**

用戶特別提到嘅 2024-05-02「institutional pricing power」quote,查返**問題同答案**先發現係反面證據——嗰句其實出自**分析師嘅提問**,CFO 冇確認:
> **分析師 Kyle Voigt:** "...whether the strong market share on the ETF custody side ... has given you some pricing power in the institutional business..."
> **CFO Alesia Haas 嘅回答:** "...when you see the fee go up, it's really driven by a **mix shift** and we're seeing more growth on Coinbase Prime than we saw on the Exchange... **It's just continued engagement**..."

CFO 冇答「係,我哋有定價權」,而係將 fee 上升歸因於產品組合轉移(客戶用緊較貴嘅 Prime 產品),同「主動加價」完全唔同一回事。

管理層仲**主動否定監管稀缺性做護城河**(Brian Armstrong CEO,2025-05-08):
> "the lack of regulatory clarity that we had in the past, **this was not a moat for Coinbase. It was a barrier to the entire industry growing.**"

COIN 自己講嘅護城河係品牌信任 + 流動性網絡效應(2026-05-07 四大支柱:"most trusted brand"、"pooled global liquidity... network effect"、最大受監管穩定幣平台、產品執行力),**冇一項係供給約束型護城河**。同時營收明確係加密價格/成交量 beta(2026-05-07:"Total crypto market cap and total crypto trading volume were both down more than 20% quarter-over-quarter"),而公司自己嘅戰略敘事(擴展 subscription/services)正正係想**逃離**呢個 beta。

**3a 判定:COIN = crypto 價格/成交量 beta + 品牌/網絡護城河,唔係供給約束型定價權故事。Objective B 唔適用。**

### 3b. CRCL —— 判定:**FAIL(需求增長故事,唔係供給約束)**

CFO 自己定義商業模式(Jeremy Fox-Geen,2025-11-12):
> "Stablecoins are a network business... **We earn reserve income on the assets backing our stablecoins**, and we incentivize strategic partners to grow distribution."

即係 revenue = USDC 流通量 × 儲備殖利率。兩份最新 transcript 顯示公司對主要收入嘅殖利率**完全冇議價權**,仲喺跌緊:
> "2025-11-12: reserve return rate was **4.15%**... **down 96 basis points** year-on-year, reflecting the decline in SOFR."
> "2026-05-11: reserve return rate was **3.5%**... **down 66 basis points** year-over-year, reflecting the decline in SOFR."

呢個係反面證據入面最乾淨嗰句:Circle 主要收入嘅價格由 Fed 定,仲要係跌緊(GENIUS Act 仲禁止俾息俾持有人)。「supply」呢個字喺 CRCL corpus 出現時,全部指**USDC 流通量/採用率**(2026-05-11:"$77 billion of USDC in circulation, representing 28% year-over-year growth"),即係需求增長,唔係供給稀缺。

護城河方面 CRCL 講嘅係監管牌照(2025-11-12:"over 55 licenses activated")+ 信任/網絡效應,同 COIN 一樣屬於監管/品牌護城河,唔係「供給約束+allocation」類型嘅 Objective B 樽頸。

**3b 判定:CRCL = 需求/採用增長故事 + Fed 定嘅利率 beta(仲跌緊)+ 監管牌照護城河。「供給約束」框架完全唔啱用。**

---

## 4. 穩定幣 → 美債 需求故事

呢個係用戶特別點名要查嘅角度:穩定幣發行商因為儲備規定要買大量短期美債,係咪一個「供給約束」故事?

**查證結論(基於 §3 CRCL 逐字證據):唔啱套用 Objective B 框架,原因喺公司自己嘅用詞已經講晒。** CRCL 自己形容嗰個係「USDC **supply** growth」+「reserve income」——兩個組件分別係:
- USDC 流通量增長 = **需求側**(市場想用幾多 USDC),唔係 Circle 擁有嘅稀缺供給;
- 買美債嘅殖利率 = **Fed 定價**(SOFR 掛鈎),Circle 淨係跟隨,毫無定價權,而且過去兩季一路跌。

換句話講,「儲備買美債」呢條線本身係 Circle 站喺美債市場嘅**買方**(demand side),唔係擁有咗一個供給稀缺資產(Objective B 要嘅係公司自己擁有/受益嘅供給樽頸)。呢個更加似一個宏觀 flow/需求敘事(美債買盤結構性增加),同 Objective A(宏觀/板塊輪動層,§3h)嘅性質更接近,但 Objective A 本身都仲係 queued 未接線嘅實驗,冇現成接口。

**4 判定:NOT-APPLICABLE-TO-OBJECTIVE-B。** 呢個係需求增長故事,唔係供給約束故事,同 Objective B 定義嘅機制方向相反(Objective B 要「supply-tight」,呢度係「demand-growing」)。誠實講:呢個角度連 WEAK 都算唔上,係方法論層面嘅 mismatch,唔係證據不足。

---

## 5. 最終綜合判定

| 角度 | Ticker/資產 | 判定 | 一句總結 |
|---|---|---|---|
| 1. BTC/ETH 本身 | BTC、ETH | **NOT-APPLICABLE**(方法論觸唔到) | 冇公司/transcript;halving supply-known×已被發現,同 discovery radar 要嘅「未被發現」相反;真正性質係宏觀/flow 資產,需要新開資產類別 = design decision |
| 2a. Pure-play 挖礦 | MARA、RIOT、CLSK | **FAIL** | Commodity beta;difficulty auto-adjust 結構性排除定價權;管理層自己講「buyer has pricing power」(即 Bitmain 有,礦企冇) |
| 2b. AI/HPC pivot 前礦企 | CORZ、IREN、CIFR、WULF、HUT | **NOT-A-DISTINCT-THESIS** | 樽頸語言同現有 `ai-power-grid` 一字不差(power/interconnection/transformer/lead-time);對電力係 beneficiary,對設備係 victim;會重複算 exposure |
| 3a. 交易所 | COIN | **FAIL** | Crypto 量/價 beta + 品牌/網絡護城河;CFO 冇確認定價權提問(歸因 mix shift);CEO 明確否定監管護城河 |
| 3b. 穩定幣發行商 | CRCL | **FAIL** | 需求/採用增長 + Fed 定嘅殖利率(跌緊)+ 監管牌照護城河,唔係供給約束 |
| 4. 穩定幣買美債 | CRCL/Tether | **NOT-APPLICABLE** | 需求增長故事,方向同 Objective B 要嘅「供給約束」相反,方法論 mismatch 而非證據不足 |

### (a) 有冇搵到 STRONG 候選?
**冇。** 6 個角度全數 FAIL / NOT-APPLICABLE / NOT-A-DISTINCT-THESIS,一個 STRONG 或 WEAK 都冇。呢個結果本身有價值——證明咗 Karst 嘅證據紀律(beneficiary vs victim、read full context、priced-in gate)喺 crypto 呢個資產類別度**一致噉篩走晒**,冇因為「用戶想要 crypto」而放水。

### (b) 建議嘅 ticker/thesis 名
**冇建議新增 thesis。** 如果想要 crypto 相關 exposure,現時最貼近但已有更好歸屬嘅選項係:透過現有 `ai-power-grid` thesis(已含 GEV/ETN/PWR/GNRC/SPXC/CAT)間接捕捉「數據中心電力」呢條腿——CORZ/IREN/CIFR/WULF/HUT 只係呢個故事嘅下游表達,唔應該疊加做第二個 exposure。

### (c) 為咩冇搵到
- **加密資產(BTC/ETH)本身唔喺 Objective-B 方法論嘅定義域**(冇公司/earnings call),呢個唔係查極都冇證據,而係範疇根本唔啱。
- **礦企**:結構上係雙重 price-taker(BTC 價格 + ASIC 價格皆跟隨大市),協議層 difficulty auto-adjustment 更加令任何一間礦企都冇辦法建立持久定價權——呢個唔係暫時證據薄,而係**協議設計本身排除咗呢種護城河**。
- **交易所/穩定幣**:兩者都有真.護城河(品牌網絡效應、監管牌照),但呢類護城河**唔係 Objective B 定義嘅「供給約束+allocation」型樽頸**,佢哋嘅收入結構更似需求增長/beta,唔係供給樽頸個股。

### (d) BTC/ETH 呢條線係咪需要用戶做 design decision?
**係。** 呢個唔係「證據不夠,遲啲再查」,而係一個範疇問題:Objective B 嘅整套機制(transcript constraint-language scanner)結構性觸唔到冇公司嘅 protocol 資產。如果用戶想要 BTC/ETH exposure,需要用戶明確拍板開一個新嘅資產類別/新方法論(例如:純粹 macro/flow 判斷 + 獨立嘅 sizing/custody/風控規則,類似 §3f 講嘅「另一個投機 sleeve」),呢個唔應該由 agent 自己砌一套新框架加落去。喺果個決定之前,Karst 依家嘅证据紀律下,crypto 冇一個站得住腳嘅 Objective-B thesis。
