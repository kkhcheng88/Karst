# Level-2 Red-Team：tpu-custom-silicon（TPU / 自研 ASIC）

- 日期：2026-07-15（狩獵執行 2026-07-16）
- 協議：thesis/DESIGN.md §4b（FALSIFY 升級：INGEST 係審判，唔係歸檔）+ §4b 校準（事實補全，唔係反對表演）
- 角色：辯方 red-team。**職責 = 事實補全（搵敘事冇展示嘅重大事實），唔係反對表演。**
  每條反方必須錨喺可引用事實/數據；砌唔到錨定事實 = 標「敘事風險」，唔算 finding。
- Pilot 三教訓已納入：反面狩獵只收一手（數據/日期/公告/法律先例）；強制回答
  「Tier-1 佐證掂嘅係承重 claim 定周邊事實？」；**強制 balance-sheet 檢查**（前三單：memory RPO 唔喺表中彈、
  photonics backlog 唔現金背書中彈、GEV 現金預付 +70% 補強脫 cap——本單驗 AVGO 係邊種）。
- 約束：只新增本檔，冇改 themes.yaml / wiki / 任何現有檔。

---

## 1. 控方主張摘要

算力重心由訓練移向推理，TPU/自研 ASIC 每有效運算成本比 NVDA 低 20–50% → **結構性咬下 NVIDIA 推理份額**；
最純押法 = 設計端收費站 AVGO（「贏兩次」＝ ASIC 設計 + Tomahawk 交換），全鏈 AVGO/TSM/CLS/MRVL 多年受惠
（verdict `real-share-shift-but-thin-and-consensus`，confidence **0.25**，cycle **mid**；P2 diff 表旗此 theme 公式後
**跨過 v2 sizing magnitude 加成閘**，值得特別留意）。

承重 claim 拆**兩個子命題**逐個審（此拆分係本次判決核心）：
- **(a) 結構性份額轉移**：custom ASIC 對 NVDA 推理份額嘅侵蝕係**行業級結構轉移**，唔係單一客戶（Google TPU）
  嘅週期性 capex。
- **(b) 收費站被財報確認**：AVGO 設計端拿單 / AI 營收會被**財報持續確認**（toll-booth 真收得到錢、且加速）。

**先報最重要嘅方向性事實（校準紀律 2「兩手空空 = 有效判決」）：本次反面狩獵搵唔到「取消潮」。**
custom-ASIC roadmap 除 Microsoft Maia 200 延遲一例外，全部 on-track / ramp；AVGO 指引逐季**上調且 beat**、
$73B backlog 係一手管理層數字。**子命題 (b) 唔單止生還，係被 Tier-1 硬確認**——呢點同 photonics 相反
（嗰單 Tier-1 只掂到周邊毛利、掂唔到 duration）。真正弱點收窄到子命題 (a) 同 balance-sheet 口徑。

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道（Tier-1，最鋒利）**

- **corpus 零 AVGO/MRVL 一手逐字稿。** `thesis/.raw/transcripts/` 只有 DTE/MU/WEST；`corpus.py ticker AVGO/MRVL`
  各返 30 篇全部係 gooptions `trend-core-research-*` Tier-2 分析文。**但本次改用 defeatbeta `earning_call_transcripts()`
  直接抽 AVGO 一手逐字稿**（FY2005 至 FY2026Q2 齊全）——呢個先係系統獨立 Tier-1 渠道實際擊中承重 claim 嘅地方。
- **子命題 (b) 被一手逐字稿 + 財數硬確認：** AVGO FY2026Q2（電話會 **2026-06-03**，Hock Tan 逐字）：AI 半導體營收
  **$10.8B、+143% YoY**、略高於自家指引（beat）；季內 AI **bookings > $30B** vs 出貨 $10.8B（book-to-bill ~3x）；
  Q3 指引 AI **$16B、+200% YoY**。FY2025Q4（2025-12-11）：**$73B backlog**（XPU/switch/DSP/laser，未來 ~18 個月/6 季）。
  指引軌跡逐季上調且 beat：Q4FY25 AI $6.5B → Q1FY26 指引 $8.2B → **Q2FY26 實際 $10.8B**。**呢個係承重 claim (b)
  本身、唔係周邊——Tier-1 直接命中，強過 photonics。**
- **收費站經濟學被財數確認（掂承重、亦係 §4a 潛在第二源）：** Kirsten Spears（同場）：季度 capex 得 **$231M**
  （≈營收 1%）、FCF **$10.3B（46% 營收）**。極輕資產 + 高 FCF = 設計端 toll-booth 高 ROIC 結構真。
- **★ balance-sheet 檢查（強制，pilot 第三單）——AVGO 屬「披露 backlog、唔現金背書」型，同 MU/photonics 同族，
  非 GEV 型：**
  - defeatbeta `quarterly_balance_sheet`（至 2026-04-30，17 季）：AVGO **有** deferred revenue（Current
    **$10,038M** + Non-current **$4,204M** ≈ $14.2B）——**表面上似 GEV 型現金背書**。但時序拆穿：deferred revenue
    喺 **2023-10-31 $2,487M 一跳到 2024-01-31 $9,593M**，正正係 **VMware 收購埋數（2023-11-22）**。即表上 deferred
    revenue **係 VMware 軟體訂閱**（ratable），**唔係 AI/custom-ASIC 硬體 backlog**。
  - **VMware deferred revenue 仲係 flat-to-declining**：Non-current deferred revenue 由 2024-07 峰值 **$5,759M
    跌到 $4,204M**、Current 亦 flat（$9.4–10.5B 橫行）——**冇隨 AI 故事上升**。
  - **$73B backlog / $30B 季度 bookings = 披露式 order-book，零 balance-sheet 現金背書。** Hock 親口叫佢做
    "backlog"/"bookings"，喺表上**搵唔到對應嘅合約負債增長**。同 pilot「MU RPO $100B 唔喺 balance sheet」、
    photonics「order book 到 2028 但 deferred≈0」**同一形態，第三次落刀斬中**。
  - **反向硬事實：客戶唔預付，反而 AVGO 融資客戶。** $30B bookings 冇產生任何 deferred revenue 增量；
    相反 **Receivables 由 2024-04 $5,500M 暴增到 2026-04 $16,748M（+205%）**，DSO 由 ~53 日升到 **~69 日**。
    真慌嘅買家會預付（GEV +70% 現金預付脫 cap）——AVGO 嘅客戶**反而收 AVGO 嘅賒帳**。溫和陰性（DSO 升幅唔算爆），
    但方向清楚：backlog 唔係現金鎖單。
- **Insider / constraint-scanner：** 本次未跑 EDGAR insider（叢內 3 名 mega-cap，insider 訊號稀薄且機械交易主導，
  參考價值低）；constraint-language 由逐字稿人手讀取（見下最關鍵一句）。

**（最關鍵一手：管理層自認唔係供給樽頸）** Joe Moore 問點解 backlog 咁多，Hock Tan 答：
「…**It's not because of shortage of our components**, it's also the other elements that need to be put in place,
which particularly relates to **power** and connection into an infrastructure…」+「the bookings that are coming,
is **not for immediate delivery**」。→ **AVGO 自認自身唔係咽喉**，$30B/$73B backlog 係客戶為 power/lead-time
提前規劃（週期頂典型行為），唔係 AVGO 供給結構性受限。呢句直接侵蝕「設計端結構樽頸」讀法。

**(b) 外部一手（WebSearch，篩走意見文）**

- **取消潮不存在（誠實報告，兩手空空）：** custom-ASIC roadmap 唯一確認延遲 = **Microsoft Maia 200（Braga）
  延 ≥6 個月**（設計變更 + 團隊 ~1/5 流失，The Information via DCD）。其餘全 ramp：Meta MTIA「shipping now」
  （官方 blog 2026-03，四代兩年路線）、Amazon Trainium3 出貨（2025-12，近售罄）、OpenAI-Broadcom 10GW
  （2025-10-13）+ Jalapeño 晶片（2026-06-24，2026 末首批）、Apple Baltra N3P（2026H2；Apple×Broadcom 延至
  2031、$30B，2026-07-06）。**搵唔到任何 hyperscaler「因 ASIC 失望回補 NVIDIA」嘅一手案例**（一致係 dual-track）。
- **NVDA 反擊 = 生態鎖定，唔係割喉：** NVLink Fusion（**2025-05-19** Computex 官方）讓第三方 custom ASIC
  透過 NVLink 接入 NVIDIA rack（首批 MediaTek/Marvell/Alchip/Astera）——**雙刃**：一方面證實「客戶要自研 ASIC」
  需求大到 NVIDIA 要開介面遷就（背書 MRVL/Alchip），另一方面把 custom ASIC **併入 NVIDIA 生態**（against 純
  toll-booth 敘事；NVIDIA 另傳 $2B 入股 Marvell = soft lock-in）。Blackwell 未見激進砍價（GB300 NVL72 整櫃
  ~$3.7–4M，走「低 cost-per-token」論述）。Jensen GTC 2026（2026-03-16）主打「inference inflection」要守
  ——顯示 ASIC 威脅係真，但反擊係整櫃系統經濟性。
- **設計端擴散只喺「供應商層」+「同一批巨頭多下單」：** MediaTek 首個 hyperscaler ASIC 專案（2026-04-30 call，
  Q4 2026 ~$2B）、Alchip 做 Trainium 設計服務——供應商入場；但**客戶端仍鎖同一批 hyperscaler/frontier lab**，
  **搵唔到中型企業/長尾簽 custom silicon 嘅一手證據**。AVGO+MRVL 仍控 custom-AI ASIC co-design ~95%。

**(c) 歷史先例**

- **2018-19 crypto ASIC 崩盤（Bitmain）：** 2018H1 淨利 $742.7M → Q3 2018 虧 ~$500M、庫存膨脹、2018-12 裁員約半、
  $15B IPO 撤回；挖礦硬體佔營收 96%，需求隨幣價急凍數季內崩。**類比警示**：單一終端需求驅動嘅 ASIC 榮景可數季蒸發；
  惟屬幣價週期，與 AI inference 真實算力需求不同——**類比強度需折價**。
- **挑戰 NVDA 嘅替代架構多陣亡：** Intel Larrabee（2009-12 取消）、Xeon Phi（2018-07 EOL）、IBM Cell（~2009 停開發）。
  **今輪結構分別（真，幫控方）**：呢啲係「單一供應商產品」失敗，今輪係「多家 hyperscaler 各自出資自研 + AVGO/MRVL
  代設計」嘅分散結構，死法唔同構。
- **Google TPU 9 年外部採用仍極集中：** 外部客戶僅 Apple、Anthropic、SSI（+ OpenAI 傳經 GCP）；最大 anchor =
  Anthropic（承諾多達 100 萬顆 TPU）。**9 年 = 外溢面窄、單 anchor 集中**——隱性 concentration risk。

### 動作 2 — Steelman 反方（非文章自供，事實錨齊）

**「AVGO AI 爆升係單一客戶（Google TPU）週期性 capex 事件，唔係行業結構轉移；custom = 一兩條鯨魚擴張 +
鯨魚之間換供應商，唔係行業重構到長尾」**：
1. **Morgan Stanley 一手估計**：Google TPU **現佔 AVGO AI 營收約 2/3**（並預期隨新客戶 ramp「下降到約 60%」，
   反推當下更高）；AVGO 保有 Google TPU ~80% 份額。
2. **量產出貨客戶極少**：AVGO「few **six** customers」（Hock 逐字），但只有 **Google + Meta 係 volume shipping**；
   OpenAI（Jalapeño）/Apple（Baltra）係 **2027+ 未出貨**。TPU 誕生 9 年外部採用仍集中 Anthropic anchor。
3. **AVGO 整體客戶集中度高**：FY2025 10-K top-5 客戶 ~40% net revenue；FY2024 單一 distributor 客戶 28%。
4. **MRVL 同型且更脆**：FY2026 10-K top-10 客戶 **82%**；傳 **Microsoft 把 Maia ASIC 由 Marvell 轉去 Broadcom**
   （The Information，2025-12-05）——**鯨魚會換供應商**＝供應商份額博弈，唔係行業結構擴散。
5. **先例**：Bitmain（單一終端需求數季崩）、Larrabee/Xeon Phi/Cell（挑戰者架構陣亡）。

**呢條 steelman 唔需要「AI 需求係假」**——就算 AI capex 全真，只要需求集中喺 Google 一家嘅 TPU 週期，
「行業結構轉移」呢個更強假設就唔成立。

### 動作 3 — 平庸解釋測試

**悶故事：「Google TPU 週期性擴產 + 少數鯨魚為 power/lead-time 提前雙重下單」可以解釋幾多？**
- **解釋到（子命題 a 大部分）**：$30B bookings（Hock 自認係 lead-time 規劃、"not for immediate delivery"、
  "not because of shortage of our components"）、book-to-bill 3x（客戶前置下單＝週期頂典型，同 photonics
  double-ordering 同機制）、~2/3 營收係 Google 單一客戶——全部係「一兩條鯨魚週期性擴產」嘅標準現象，
  **唔需要「行業結構份額轉移」呢個更強假設**。
- **解釋唔到（結構故事嘅額外證據，幫控方）**：
  1. **設計端 IP toll-booth 位真**：AVGO+MRVL ~95% custom-AI ASIC co-design；連 Microsoft 由 MRVL 轉 AVGO
     都係「份額喺收費站之間輪動、但仍過收費站」——呢個結構喺任何鯨魚贏都收費，係真 additive 結構，悶故事解釋唔到。
  2. **toll-booth 營收兌現係真**（非願景）：財報已收到錢（+143%、beat、$10.3B FCF）。
- **可區分觀測（datable）**：
  1. **TPU 走出 Google 嘅「出貨」而非「bookings」**：OpenAI Jalapeño（2026 末）/ Apple Baltra（2027）如期
     轉成 shipped revenue → 結構故事贏；若滑期 / 仍係 Google 一家撐 → 週期故事贏。
  2. **AVGO 客戶集中度披露**：下份 10-K 若單一客戶佔比續升 → 單客戶讀法確認。
  3. **Receivables/DSO**：DSO 續升穿 70 日兼 bookings 減速 = 週期裂縫；deferred revenue 若始終唔升 =「多年鎖單」
     一直只係講稿。
- **結論**：**子命題 (a)「結構性 vs 單客戶週期」——悶故事解釋到大部分，控方未能區分**；子命題 (b) toll-booth 位 +
  營收兌現係悶故事解釋唔到嘅結構真材。

### 動作 4 — kill 距離（kill_condition 逐條）

| kill 軸 | 當下事實 | 距離判定 |
|---|---|---|
| **① TPU 走出 Google 停滯**（Anthropic/Meta 之後無新 hyperscaler/企業） | 名單反而擴（OpenAI Jalapeño 2026 末、Apple Baltra 2031 長約、MediaTek）——但**全部仍係 hyperscaler/frontier-lab tier，且多數 2027+ 未出貨**；長尾企業採用零一手證據 | **未觸發**；但「擴散」係 bookings 層非 shipped 層——**中距離**，區分窗口 = OpenAI/Apple 晶片 2027 出貨兌現 |
| **② AVGO AI order-book/營收停止 beat**（收費站未被財報確認） | **明確相反**：逐季上調 + beat（$6.5B→指引$8.2B→$10.8B）、$30B bookings、3x book-to-bill、$73B backlog | **遠離觸發、方向反向**——**全 claim 最硬嘅 bull 軸**，Tier-1 硬確認 |
| **③ New-Street 追蹤 NVDA 推理份額不見鬆動** | **未解**：本次搵唔到 New-Street 份額一手數；share-shift 正正係承重 claim (a) 未證嗰半 | **未解、真正開口風險**——結構故事嘅裁判喺呢度，而家冇一手讀數 |
| **④ 真護城河「開源模型都長成 GPU 形狀」holds / Gemma 養唔出 TPU-shaped 開源** | NVLink Fusion（2025-05）證 NVIDIA 反把 custom ASIC 併入自身生態（ecosystem lock）——**輕微向此 kill 軸移動** | **未觸發、輕微收窄**；CUDA/生態鎖仍係最深護城河（corpus #146/#159） |
| **crowding-unwind**（AI-capex 打嗝即重挫） | 已現：AVGO **record 財報單日 −12%**（corpus #095，2026-06-05；fwd P/E ~22x vs MRVL ~51x）、MRVL −18%（2025-08-29 data-center miss） | **持續有效、已實質首發**，同 [[ai-capex-macro-risk]] 聯動 |

**額外 corpus 矛盾（掃系統自己 Tier-2 庫）：**
- **#095（2026-06-05）**：AVGO 交 record AI 財報卻 **−12%**——市場獎勵敘事斜率、懲罰無上修嘅高基期。crowding
  脆弱性已實證觸發，非理論。
- **#160（2026-07-13）**：Google 一邊 2026 capex $180–190B + 增資 $85B，一邊把 **100 萬顆 TPU 租畀對手 Anthropic**。
  即「TPU 走出 Google」有一大截係 **Google 自己嘅算力套利/配置選擇**（單一擁有者對外分租），而非獨立行業採用
  ——**加強子命題 (a) 嘅單客戶讀法**：外溢嘅源頭仍係 Google 一家。

---

## 3. 判決：**部分中彈（承重 claim 一分為二：收費站營收生還兼被 Tier-1 硬確認；結構份額轉移中彈）**

按 §4b 校準，逐子命題：

- **(b)「收費站被財報確認」——生還，且係全系統少見嘅 Tier-1 直擊承重 claim。** AI 營收 +143%、逐季 beat、
  $73B backlog（管理層一手）、capex ~1% 營收 + FCF 46% = 高 ROIC 收費站真材。**呢度 Tier-1 掂嘅係承重 claim 本身，
  唔係周邊**——同 photonics（Tier-1 只掂毛利周邊）相反，亦同 pilot MU（RPO 唔喺表）唔同。**pilot 嗰把刀喺呢半邊
  斬唔落。**
- **(a)「結構性份額轉移」——中彈。** 三重打擊：(1) Google TPU ~2/3 AI 營收（MS）+ 量產客戶得 Google/Meta +
  9 年外部採用集中 Anthropic → 平庸解釋（單客戶週期）解釋到大部分，控方未能區分；(2) Hock 自認「唔係我哋零件短缺」
  → 設計端結構樽頸讀法被管理層親口削弱；(3) corpus #160：外溢源頭仍係 Google 自己對外分租。**「share-shift」
  呢個字 over-claim**——已證嘅係「toll-booth 真收得到錢」，未證嘅係「行業級份額由 NVDA 結構轉走」。
- **★ balance-sheet 裁定：AVGO = 披露 backlog 型（MU/photonics 同族），非 GEV 現金預付型。** $73B/$30B backlog
  零 balance-sheet 現金背書；表上 deferred revenue 係 VMware 軟體且 flat/declining；receivables +205%、DSO 53→69 日
  = 客戶收賒帳唔預付、AVGO 融資客戶。**但注意**：呢刀斬嘅係 backlog 嘅 **duration/能見度**（$73B「18 個月」
  有幾實），**唔係當下營收存在性**（營收真喺度 shipping、經 receivables 收緊）。呢個係本單同前兩單嘅分別：
  MU/photonics 係「機制本身可疑」，AVGO 係「當下真、但 duration 靠披露撐」。

**Rubric 建議（§4a 掛鈎：moat/growth 攞 2 分前提 = 承重 claim 經 Level-2 且生還）：**
- **moat 格：維持 1.5。** 設計端 toll-booth 位真且被 Tier-1 確認（AVGO+MRVL ~95% co-design、輪動仍過收費站）
  ——生還支持 1.5；但**升唔到 2**，因 (i) Hock 自認非自身樽頸（唔係「供給結構性受限」嗰種 2 分錨）、
  (ii) Google 同跑 3 條 TPU 設計線 + NVLink Fusion 生態鎖係長期稀釋、(iii) 承重嘅「結構份額轉移」半邊未證。
- **growth 格：2 → 1.5。** additive 機制（toll-booth 營收）已兌現支持高分；但「供給結構性慢/耐久」嗰半個判準受
  **單客戶集中（Google 2/3）+ backlog 係披露非現金 + 歷史先例（單一終端需求數季崩）**侵蝕——「耐久」未過 Level-2。
  **呢格下調係本次淨負面主因。**
- **估值（0.5）/資本配置（1）格照舊**——機械讀數，本協議不覆核。惟資本配置格註記：capex $231M/FCF 46% 係
  **正面**一手，下次覆核可考慮 1 → 1.5（設計端輕資產高 ROIC 已被財報證）。

---

## 4. 建議（不執行；郁數留返日間 confidence 迴路）

- **confidence：維持 0.25（唔升）。** 淨效果 = growth 半格下調（結構耐久未過 Level-2）抵銷 toll-booth 營收確認嘅
  正面。**明確唔准因「取消潮不存在 + 逐季 beat」而上調**——因為嗰啲確認嘅係子命題 (b)（已 priced、最共識），
  真正未證嘅係子命題 (a)（結構份額轉移）同 duration。§4b 硬規則：uncalibrated 升 confidence 要承重 claim 全體生還，
  而家係一半生還一半中彈。
- **verdict 措辭建議改**：`real-share-shift-but-thin-and-consensus` →
  `real-tollbooth-revenue-but-single-customer-and-consensus`（或 wiki 內註明「share-shift 半邊未證、
  當下爆升 ~2/3 係 Google 單客戶週期」）。**「share-shift」係 over-claim，已證嘅係 toll-booth 營收唔係份額轉移。**
- **§4a single-source cap 處理（重要）**：本次 **defeatbeta AVGO 一手逐字稿 + 財數獨立擊中承重 claim (b)**
  （toll-booth 營收 +143%/$73B backlog/$10.3B FCF）——**呢個算獨立第二源、可登記 `sources:` 解 cap 嘅一半**
  （corroborates: toll-booth-revenue）。但**唔可以當佢解埋子命題 (a)**——結構份額轉移仍係 single Tier-2（#129 系）+
  未證，cap 對 (a) 仍在。建議 `sources:` 加一條 `id: defeatbeta-avgo-transcript, tier: 1,
  corroborates: tollbooth-revenue-confirmed`（唔係 corroborates: structural-share-shift）。
- **P2 sizing magnitude 加成閘覆核（用戶特別提示）**：magnitude 加成部分靠「多年結構耐久」——但耐久嗰截
  （子命題 a + backlog duration）本次中彈。**建議 magnitude 加成應掛喺 AVGO node 嘅 toll-booth 營收確認（已證），
  唔好掛喺結構份額轉移（未證）**；若加成公式讀嘅係「結構轉移多年」，應重估。
- **kill 軸強化**：軸 ③（NVDA 推理份額）係結構故事真正裁判但**當下零一手讀數**——建議接 New-Street / 具體
  inference 份額 tracker 做定期 checkpoint，否則子命題 (a) 永遠證偽唔到。新增早期警戒標記（非 kill）：
  AVGO 單一客戶佔比（10-K）、DSO >70 日兼 bookings 減速、OpenAI/Apple 晶片 2027 出貨兌現。

---

## 5. Meta-review（一句）

本單同前三單嘅結構差異值得記入 checklist：**AVGO 係第一單 Tier-1 直擊承重 claim（toll-booth 營收真、財報硬確認）
嘅 theme**——pilot 嗰把「披露 backlog ≠ 入帳緩衝」嘅刀仍斬中（$73B 零現金背書、receivables +205% 而非預付），
但只斬到 **duration/能見度**，斬唔到**當下營收存在性**。真正嘅弱點唔係「機制假」，而係「**當下真爆升 ~2/3 係
Google 一家嘅週期，被 packaging 成行業結構轉移**」——校準嘅意義係：唔好因為「取消潮唔存在 + 逐季 beat」就上調，
因為嗰啲全部係已 priced 嘅子命題 (b)；真正未證、又正正係 magnitude 加成所依賴嘅，係子命題 (a) 嘅結構性。
