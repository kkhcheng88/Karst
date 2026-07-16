# Level-2 Red-Team：space-satellite(太空 / 衛星經濟)

- 日期：2026-07-16(對象 = 2026-07-14 SpaceX IPO 重估後版本)
- 協議：thesis/DESIGN.md §4b(FALSIFY 升級：INGEST 係審判,唔係歸檔)
- 角色：辯方 red-team。**職責 = 事實補全(搵敘事冇展示嘅重大事實),唔係反對表演。**
  每條反方必須錨喺可引用事實/數據;砌唔到錨定事實 = 標「敘事風險」,唔算 finding。
- Pilot 教訓已納入(memory-supercycle / photonics 兩役):反面狩獵只收一手
  (數據/日期/公告/官方文件/法律先例);強制回答「Tier-1 佐證掂嘅係承重 claim 定周邊事實?」;
  **強制 balance-sheet 檢查(backlog 聲稱 vs 入帳 deferred revenue)**。
- 約束:只新增本檔,冇改 themes.yaml / wiki / kill_metrics / 任何現有檔。

---

## 1. 控方主張摘要

太空係**真.早週期結構主題**:發射成本崩塌 **$54,500→$2,720/kg(-95%)** 開啟多十年太空 capex
超級週期;三引擎同時點火——創投單季 **$36B**(史上最大)、Golden Dome CBO **$1.2 兆**、
SpaceX $75B IPO(2026-06-12 掛牌 SPCX,$1.77T)。**承重 claim = 「發射成本 -95% 相變係真,
且呢個相變開啟一個多十年、真實資本承諾嘅太空 capex 超級週期——主題真且早」**
(verdict `real-early-but-froth-priced`,confidence 0.28,cycle early,theme 趨勢已 KILL-WATCH,
可交易表達自認 priced-in)。

承重 claim 拆三個子命題逐個審:
- (i) **相變真**(-95% 發射成本、Starlink 經濟性已兌現)
- (ii) **相變開啟「多十年超級週期」**(三引擎 = 真實、durable 嘅資本承諾,唔止一次性資金潮)
- (iii) **主題真且早**(週期溫度低、供給端仲喺早期建置)

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 強制 balance-sheet 檢查——backlog 聲稱 vs 入帳 deferred revenue(defeatbeta quarterly_balance_sheet,至 2026-03-31)**

pilot / photonics 嗰把「披露式 backlog ≠ 現金背書合約義務」嘅刀,喺本 theme **第三次落刀,
斬得最深,而且斬中全叢最貴嗰個名**:

- **ASTS——「backlog $12B」≈ 98% 唔係 cash-backed。** 2026-03-31 balance sheet:
  Current Deferred Revenue **$25.861M** + Non-Current Deferred Revenue **$207.093M** = 合共
  **≈ $233M**。相對聲稱嘅 **$12B backlog = 僅 ~1.9% 有現金/入帳背書**。ASTS 個 $12B 係
  MNO 定義性協議 + MOU 覆蓋 ~28 億用戶嘅**收入分成 TAM 式數字**,唔係 RPO 式合約義務——
  呢個係全叢**最極端**嘅「backlog = 能見度」對「入帳緩衝」落差,而 ASTS 正正就係 **377x P/S、
  空單 18.4%、全叢最夢想定價**嗰隻。
  - **唯一乾淨碎片(反向,幫控方):** Non-Current Deferred Revenue 由 2025-09 嘅 $43.5M **跳上
    $207.093M(2025-12 起兩季維持)**——即係最近兩季真係有人畀咗現金落訂(真.prepayment 出現咗)。
    呢個係本次狩獵喺 ASTS 財數搵到嘅唯一硬正面事實,但佢仍然只係 $12B 聲稱嘅 ~2%。
  - ASTS Total Liabilities 由 $285M(2024-12)暴脹到 **$3.39B**(2026-03),主體係 Long Term Debt
    **$2.98B**(可轉債)——星系建置係**債務融資**嘅,唔係客戶預付融資嘅。
- **RKLB——「backlog $2.2B(+108%)」≈ 89% 唔係 cash-backed(但比 ASTS 乾淨好多)。**
  2026-03-31:Current Deferred Revenue **$241.412M**、Non-Current Deferred Revenue **≈ $0**
  (帳上 $1.352M「Non Current Deferred Liabilities」係遞延**稅項**唔係收入)。合共 **≈ $241M
  = 聲稱 $2.2B backlog 嘅 ~11%**。RKLB 個 backlog 含真實 launch service agreement + Space
  Systems 合約,~11% 里程碑式入帳對發射/製造商算正常比例——**RKLB 個 backlog 比 ASTS 實得多**,
  但「+108% backlog」呢個增長敘事,89% 仍然係披露口徑而非現金背書。
  - RKLB 現金 **$1.205B**(集資後)、Total Debt 跌返 $138.7M、Equity $2.26B——資產負債表健康,
    但呢個係「有錢燒」嘅健康,唔係「客戶搶住預付」嘅緊絀。

**必答(pilot checklist):Tier-1 佐證掂嘅係承重 claim 定周邊?**
- **掂到承重 claim 核心嘅一手佐證 = Starlink S-1 財數**(2025 收入 $11.4B、營業利潤率 39%、
  EBITDA 63%)——呢個**直接、first-hand 證實子命題 (i)「相變真」**,係全 corpus 入面最硬、
  真.掂到承重 claim 嘅 Tier-1(與 photonics「Tier-1 只掂周邊」明顯不同,照校準紀律照直報:
  呢點利控方)。
- **但子命題 (ii)「多十年超級週期量級」嘅三引擎佐證,全部係周邊 or 敘事**:backlog(上面證咗
  唔 cash-backed)、VC $36B(下面證係寬口徑 + IPO buzz)、Golden Dome $1.2T(下面證撥款 ~$38B)。
  capex 放量、ttm_pe、backlog 存在——一手驗到嘅係「有呢啲嘢」,唔係「呢啲嘢真係墊到一個多十年
  超級週期」。

**(b) 外部一手(WebSearch,篩走意見文)**

- **Golden Dome 撥款落差 = 本次最硬反題材,且打穿 wiki 自己個 bear 框。** CBO 2026-05-12 估
  20 年 **$1.2T**;但五角大廈自估約 **$185B**、Trump 講 $175B/3 年;**真實已授權 ≈ $38B**
  (2025 對帳法案 OBBBA ~$25B + FY2026 國防撥款 2026-02-03 通過嘅 $13.4B Golden Dome)。
  **wiki 自己寫「$1.2T 只是 CBO 願景、已到位僅 $250B」——呢個 $250B 一手查無實據,較真實撥款
  高估約 7 倍。** 即係話,連 thesis 自己嗰個「保守 bear 讀數」都仲係把呢條增長引擎誇大咗一個
  數量級。(來源:CBO 2026-05-12 via Federal News Network;FY2026 國防撥款 via SpaceNews;
  OBBBA via Taxpayers for Common Sense)
- **VC $36B 係最寬口徑 + IPO buzz 驅動。** Space Capital「Space IQ Q1 2026」= $36B/148 家
  (含 GPS/地理空間廣義 Applications);但 **Novaspace 同季只計 $9.4B/82 家**、窄義純太空約
  **$7.9B**;多份一手報告直指 Q1 暴衝同 **SpaceX IPO 熱潮**綁定 = 事件驅動非結構。窄義基建融資
  Space Capital 自報 $6.7B。(Space Capital / Novaspace,2026Q1)
- **Starship 仍未入軌、未回收——「再降 10x」純承諾。** Flight 12(2026-05-22,v3 首飛)釋放 20 顆
  模擬 Starlink,但 **Super Heavy boostback 點火失敗墜海、上面級失一台 Raptor Vac、印度洋濺落後
  翻倒起火 = 次軌道測試,無入軌、無回收**;Flight 13(今日 2026-07-16 待飛)目標**同 Flight 12
  幾乎一樣**(即上次未達成)。官方零「已達 10x 降本」里程碑。(NPR 2026-05-23;SpaceX 官方;
  FAA 2026-07-13 結束 Flight 12 事故調查)→ **子命題 (ii) 嘅「下一個相變」(Starship/軌道運算)
  工程驗證仍然係零**。
- **SPCX 掛牌後基本面新事實方向偏空。** 2026-07-15 **首次跌穿 $135 發行價、創上市新低**
  (自 6 月高位約 -39%);S-1 顯示 **2026Q1 收入按年僅 +15%(顯著放緩)**、P/S >100x;首份
  10-Q 要 **2026-08-06** 先出;**180 天鎖倉 2026-12-08 到期** + Q2 財報後首批 20% 解鎖 = 供給雙懸空。
  (Quartz / Yahoo Finance 2026-07-15;招股書)
- **衛星供過於求嘅一手前兆確實出現(打子命題 iii 嘅「早」)。**
  - **Telesat**:GEO 債權人 2026 起訴,指其藉 LEO「Lightspeed」轉型逃避 **2026-12 到期 $1.7B**
    + 2027 約 $450M 債務。(Fierce Network,2026)
  - **Amazon(Leo/Kuiper)**:已申請將 FCC 首階段死線(2026-07-30 前部署半個星座 1,618 顆)
    **延兩年至 2028**(里程碑跳票);同時稱今年稍後推服務、開始同 Starlink 打價。
    (New America / SatelliteToday 2026-03;CNBC 2026-07-02)
  - **Starlink**:已推 $0.30–0.50/Mbps 方案,Amazon 入場前價格侵蝕已開始。
- **RKLB Neutron 官方確認滑期。** 時間線:原「2025 年底」→ 2025-11 延至「2026Q1 上台架」→
  **2026-01 第一級燃料箱資格測試失敗(製造缺陷)→ 首飛推至 Q4 2026**。當下口徑正正就係
  kill_metrics 個 2026-12-31 死線,但 1 月失敗已吃掉早段窗口,年底再滑機率非零。(Aviation Week;
  NASASpaceFlight 2026-07)
- **ASTS 部署真.推進但重度後置。** BB6(2025-12-22 發射)、BB8-10 Block 2(2026-06-17 Falcon 9
  發射)、FCC 已批 248 顆;年底目標在軌 **45–60 顆**,但**截至 2026 年中實際在軌僅約個位數**
  → 「2026H2 足量上天」需下半年爆發式量產發射,執行風險集中喺 kill 死線前嗰半年。(AST 8-K,SEC)

**(c) 歷史先例(先前 LEO 週期)**

- **銥星(Iridium)1999**:發射後九個月申請破產保護——wiki 自己引用嚟講「發射成本 -95% 令同一個
  LEO 點子由破產變 Starlink $11.4B」。呢個先例係**雙面**:一面證相變真(利控方,發射成本係當年
  死因);另一面提醒 **LEO 通訊嘅需求/單位經濟一旦供過於求會極速崩**(利辯方,對照今日 Telesat
  債務訴訟 + Amazon/Starlink 價格戰前兆)。
- **今輪 vs 銥星結構分別(真,幫控方)**:Starlink 需求已由 ~10.3M 付費訂戶兌現(S-1),唔係銥星
  當年嘅投機供給;但**價格戰機制(多星座擠同一頻譜/軌道 + 減價搶份額)喺兩輪之間係同一部機器**,
  只係今輪由 Starlink 佔上風、輸家(Telesat/Viasat/Amazon 里程碑跳票)開始浮面。

### 動作 2 — Steelman 反方(非 wiki/文章自供,事實錨齊)

**「三引擎超級週期入面,有兩條引擎(Golden Dome、VC)嘅『量級』係願景/口徑放大,唔係已承諾資本;
真正兌現咗嘅只有一條(Starlink),而佢正進入價格戰。」**
1. **Golden Dome**:CBO $1.2T 係 20 年情境;真實已授權 ≈ **$38B**(OBBBA $25B + FY2026 $13.4B,
   兩者皆一手撥款文件);五角大廈自估 $185B。wiki 自己個「$250B 已到位」高估約 7 倍。
   → 呢條引擎嘅「已承諾」部分係一條**正常國防預算 line item**,唔係一個 $1.2T 超級週期。
2. **VC**:$36B 係含 GPS/Applications 嘅最寬口徑;窄義純太空 $7.9–9.4B,且靠 SpaceX IPO buzz 拉動
   (Novaspace / 多份一手報告點名事件驅動)。
3. **供給回應已開始**:Telesat 債務訴訟($1.7B 2026-12 到期)、Amazon FCC 里程碑延兩年、Starlink
   減價——「早週期、供給端仲喺建置」嗰個前提,已經有一手訊號顯示個別軌道/頻譜開始擠。
4. **先例**:銥星證 LEO 單位經濟可以一夜蒸發;pilot/photonics 已兩度證「披露 backlog ≠ 入帳緩衝」,
   本役 ASTS $12B backlog 僅 ~2% cash-backed = 第三度坐實。

呢條 steelman **唔需要「Starlink 係假」**——就算 Starlink 全真,超級週期嘅「多引擎、多十年」量級
仍然主要靠兩條未兌現/口徑放大嘅引擎撐,而已兌現嗰條開始面對價格戰。

### 動作 3 — 平庸解釋測試

**悶故事:「AI 資金潮外溢 + 國防預算週期」可以解釋幾多,唔使『相變』?**
- **引擎 1(發射成本 -95%)——悶故事解釋唔到,係真相變。** Starlink $11.4B 收入 / 63% EBITDA 係
  工程 + 財報雙重兌現,唔係資金潮或預算週期產物。**子命題 (i) 生還,有硬錨。**
- **引擎 2(VC $36B)——悶故事大致解釋到。** 窄義純太空只 $7.9–9.4B、暴衝同 SpaceX IPO buzz 綁定
  = 典型「AI/熱門 IPO 資金潮外溢」,唔需要「太空相變」呢個更強假設。
- **引擎 3(Golden Dome $1.2T)——悶故事大致解釋到。** 真實撥款 ~$38B = 正常國防預算週期一條線,
  唔係一個 $1.2T 結構超級週期;$1.2T 係 20 年 CBO 情境。
- **可區分觀測(datable):**
  1. **Starship Flight 13+(2026 下半)**:若入軌 + Super Heavy 回收成功 → 「下一個相變」開始有工程
     錨,超級週期量級故事贏;若繼續次軌道/無回收 → 「10x 再降本」一直係承諾。
  2. **SPCX 2026-08-06 首份 10-Q**:Starlink 分部收入按年增速——若 Q2 續跌向 kill 閾值 30%
     (S-1 FY2025 = 49.8%,但 2026Q1 合併收入已跌到 +15%)→ 已兌現嗰條引擎減速確認。
  3. **Golden Dome FY2027 NDAA / 撥款**:任務訂單實際落地 vs $1.2T 願景——續喺 $10B 級 = 悶故事贏。
  4. **LEO 供給**:Telesat 重組結果、Amazon 2028 延後里程碑達唔達到、Starlink 進一步減價幅度。
- **結論:子命題 (i) 悶故事解釋唔到(相變真、有工程錨);子命題 (ii) 嘅「超級週期量級」大部分
  可以齋用「AI 資金潮 + 國防預算週期」解釋——區分要等 Starship 入軌/回收 + Golden Dome FY2027
  撥款;子命題 (iii) 嘅「早」開始受供給回應一手訊號侵蝕。**

### 動作 4 — kill 距離(逐條對 kill_metrics,2026-07-16 報告)

| kill 軸 | kill_metrics 讀數 | 當下一手事實 | 距離判定 |
|---|---|---|---|
| **Starship 快速重複使用長期延宕**(成本停 Falcon 量級、軌道運算敘事延後) | 質性軸,無數值 | Flight 12(05-22)無入軌無回收;Flight 13 今日待飛、目標同上次一樣;零 10x 降本里程碑 | **未觸發但無正面進展**:相變二嘅工程證據仍然係零;每次試飛 = 一個 datable checkpoint |
| **Golden Dome 遭砍/推遲**($1.2T 只 CBO 願景) | 質性軸 | 真實撥款 ~$38B vs 願景 $1.2T;wiki 自己「$250B 已到位」高估 ~7x;FY2026 已過($13.4B) | **未觸發,但基準要校正**:呢條引擎嘅「已承諾」量級遠細過 wiki 記錄;下個 checkpoint = FY2027 撥款 |
| **starlink_rev_yoy < 0.30** | current **0.498**、trigger 0.30、緩衝 **+66%** | S-1 FY2025 = 49.8%;**但 2026Q1 合併收入已跌到 +15% YoY**;首份上市後 10-Q 2026-08-06 | **未觸發,但 +66% 緩衝可能虛高**:current 用 FY2025 年數,最新季度已顯著減速;8 月 10-Q 係第一個真讀數 |
| **rklb_neutron_first_flight 過 2026-12-31** | 死線 168 日 | 官方已滑至 Q4 2026(1 月箱體測試失敗吃掉早窗口) | **未觸發,距離收窄**:當下口徑貼死線,年底再滑機率非零 |
| **asts_satellite_deployment 過 2026-12-31** | 死線 168 日 | BB8-10 已於 06-17 發射、FCC 批 248;但年中在軌僅個位數,需 H2 衝量到 45–60 | **未觸發,執行風險集中死線前半年** |
| **gsat_amazon_fcc_close 過 2027-12-31** | 死線 533 日 | (本役無新事實) | **未觸發,遠距離** |
| **純玩家獲利遲不轉正 / 燒錢加速** | 質性軸 | RKLB 仍虧損但現金 $1.2B;ASTS 債務融資 $2.98B 建星系;SPCX 合併淨損 -$4.9B | **持續有效**,同 [[ai-capex-macro-risk]] 聯動 |

---

## 3. 判決:**部分中彈**(承重相變生還、超級週期量級三支柱降級、兩軸距離收窄)

按 §4b 校準:判決標準 = 承重 claim 面對補全後嘅事實集企唔企得住。逐子命題:

- **(i)「相變真」——生還,且係全 corpus 唯一真.掂到承重 claim 嘅一手佐證。** Starlink S-1
  $11.4B 收入 / 63% EBITDA 直接證實發射成本 -95% 已把 LEO 通訊由「銥星九個月破產」變成獲利生意。
  悶故事解釋唔到,有工程 + 財報雙錨。**呢半句最硬,照校準紀律照直報:利控方,唔壓分。**
- **(ii)「相變開啟多十年超級週期」——部分中彈,三條量級支柱全部降級為敘事。**
  1. **backlog(RKLB $2.2B / ASTS $12B)**:balance-sheet 證實 RKLB ~11%、**ASTS ~1.9%** cash-backed;
     ASTS 個 $12B 係 TAM 式 MOU,坐實 pilot 第三刀,且斬中全叢最貴嗰隻。
  2. **Golden Dome $1.2T**:真實撥款 ~$38B;wiki 自己「$250B 已到位」高估 ~7x——連 bear 框都誇大
     一個數量級。
  3. **VC $36B**:窄義純太空 $7.9–9.4B、IPO buzz 驅動。
  加上**「下一個相變」(Starship/軌道運算)工程驗證仍然零**(Flight 12 無入軌無回收)。
  → 超級週期「量級」而家主要靠一條已兌現引擎(Starlink,正進入價格戰)+ 兩條口徑放大引擎撐。
- **(iii)「主題真且早」——生還但邊際被侵蝕。** theme 早週期屬實(VC 剛放量、Golden Dome 未大額
  撥款);但供給回應一手訊號(Telesat 債務訴訟、Amazon 里程碑延兩年、Starlink 減價)顯示個別
  軌道/頻譜嘅「早」開始有價格戰前兆,唔再係純粹空白建置期。

**最鋒利一刀:** ASTS「$12B backlog」——377x P/S、全叢最夢想定價嗰隻股嘅核心敘事錨——經 balance
sheet 證實僅 **~1.9% 有現金/入帳背書**($233M deferred revenue,其中 $207M 係最近兩季先出現嘅
真.prepayment);pilot「披露 backlog ≠ 入帳緩衝」嘅刀第三度落刀、斬得最深。

**Rubric 影響(§4a 掛鈎):**
- **moat 1/2:維持。** 承重相變(發射成本崩塌)本身正在崩塌(唔係 durable 樽頸)、最深護城河
  SPCX 混 xAI——wiki 已給 1 分,backlog 降級唔進一步壓(moat 本來就冇靠 backlog 攞分)。
- **growth 2/2 → 建議 1.5(半格向下壓力)。** additive 機制(Starlink $11.4B)已兌現、生還——
  呢個係 2 分嘅「已兌現」半截,穩。**但 2 分嘅另一半截「供給結構性慢(耐久)」開始受一手侵蝕**:
  發射樽頸正崩 + LEO 供給回應訊號(Telesat/Amazon/Starlink 減價)出現 = 耐久性弱化。半格降。
- **capital 1/2、valuation 0.5/2:維持。** SPCX 跌穿發行價 + 2026Q1 +15% 減速 = valuation 0.5
  底分再獲一手坐實(唔需下調,已喺底)。

**confidence 郁唔郁(重要——避免 miscalibration):**
- **建議維持 0.28,唔郁**,但記錄 red-team 淨效果 = **向下**(growth 半格 + 三支柱敘事降級 +
  兩軸距離收窄),供日間 confidence 迴路 / 公式遷移時扣。**明確唔升。**
- **注意遷移張力(留俾用戶/日間處理,red-team 不擅自郁數):** DESIGN §4b 明確**點名
  space-satellite 0.28 做「舊手工推導把表達層風險折入 penalty」嘅例子**,新方法論表達層風險唔准
  再折入 penalty(改由 magnitude_tier + valuation KPI 承擔)。用凍結公式重算,penalty(early ×
  低擁擠)會遠高過舊手推嘅 ~0.50,base 4.0/8(growth 降半格後)× 高 penalty 可能**高於** 0.28。
  即係:red-team 方向向下,但公式遷移方向向上,兩者係唔同軸嘅嘢——**唔應該喺 red-team 度用「補全
  後事實」嘅名義去抵消遷移效應**。呢個張力喺 migration 過目時處理,red-team 只交「淨效果向下 +
  唔升」嘅判斷。

---

## 4. 建議(不執行;郁數留返日間 confidence 迴路 / 公式遷移)

- **confidence:維持 0.28,標記 red-team 淨效果向下、明確唔升。** 遷移時(§4b 已點名本 theme)
  再一併處理 penalty 方法論改動,唔喺 red-team 郁。
- **verdict:維持 `real-early-but-froth-priced`。** 承重相變生還,froth/priced-in 讀數獲 SPCX
  跌穿發行價 + 15% 減速一手坐實。
- **wiki 措辭應改(記錄用,本役不改檔):**
  1. **RKLB backlog $2.2B / ASTS backlog $12B 加註**:「披露/TAM 式口徑,非 cash-backed;
     一手 balance sheet deferred revenue = RKLB ~11% / ASTS ~1.9%」(pilot 第三刀,同 MU RPO 同型)。
  2. **Golden Dome「已到位僅 $250B」= 一手查無實據,應改真實撥款 ~$38B**(OBBBA $25B + FY2026
     $13.4B);$1.2T 標明係 20 年 CBO 情境、五角大廈自估 $185B。
  3. **VC $36B 加註**:寬口徑(含 GPS/Applications);窄義純太空 $7.9–9.4B、IPO buzz 驅動。
  4. **記 ASTS Non-Current Deferred Revenue $207M**(2025-12 起兩季)= 唯一乾淨正面碎片(真.prepayment
     出現),但仍僅 $12B 之 ~2%。
  5. **記供給回應一手訊號**:Telesat 債務訴訟、Amazon FCC 里程碑延兩年、Starlink 減價——「早週期
     純建置」前提開始受侵蝕。
- **kill_metrics 應加/校正(記錄用):**
  1. **starlink_rev_yoy 個 current=0.498 係 FY2025 年數,+66% 緩衝可能虛高**;2026Q1 合併收入已
     +15%。**加一條** early-warning:2026-08-06 SPCX 首份 10-Q 出 Starlink 分部季度增速,校正 current。
  2. **加 Starship 里程碑做可量化軸**:「Flight N 入軌 + Super Heavy 回收」達成日期 vs 目標——
     子命題 (ii)「下一相變」嘅唯一工程 checkpoint,而家係質性軸,可 datable 化。
  3. **加 Golden Dome 撥款軸**:FY2027 NDAA/撥款實際數 vs $1.2T 願景(閾值可設「累計授權 < $60B
     到 FY2027」= 引擎熄火早訊)。
- **sources cap 註記:** 本役新增嘅唯一真.掂承重 claim 嘅一手 = Starlink S-1(掂子命題 i)。
  但佢同現有 Tier-2 叢(#101)係轉述同一組 S-1 數字,**唔算獨立第二源**;子命題 (ii)(iii) 仍係
  single-source 敘事框架(gooptions 一個腦)。theme 仍受 single-source cap 0.30 綁(現 0.28 已在 cap 下)。

---

## 5. Meta-review(一句)

本役最有價值嘅發現有二:(1)pilot「披露 backlog ≠ 入帳緩衝」嘅刀**第三度落刀、斬中全叢最貴嗰隻
(ASTS $12B backlog 僅 ~2% cash-backed)**,坐實呢一問應升格做 INGEST 常設 checklist;(2)**thesis
自己個 bear 框都可以有一手錯誤**——wiki「Golden Dome 已到位 $250B」較真實撥款高估 ~7 倍,提醒
red-team 唔止要質疑 bull claim,連 thesis 自供嘅「保守讀數」都要對一手撥款文件核。承重相變(發射
成本 -95%)本身生還兼有全 corpus 最硬嘅一手承重佐證(Starlink S-1)——照校準紀律照直報:呢個 theme
嘅地基(相變真)企得穩,中彈嘅係「超級週期量級」嗰層敘事鷹架,唔係地基。
