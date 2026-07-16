# Level-2 Red-Team：aerospace-specialty-alloys(航太噴射引擎特種合金 / ATI + CRS)

- 日期：2026-07-16
- 協議：thesis/DESIGN.md §4b(FALSIFY 升級：INGEST 係審判,唔係歸檔)+ §4c(red-team 判決三通道分流)
- 角色：辯方 red-team。**職責 = 事實補全(搵敘事冇展示嘅重大事實),唔係反對表演。**
  每條反方必須錨喺可引用一手事實/數據;砌唔到錨定事實 = 標「敘事風險」,唔算 finding。
- Pilot 六單教訓已納入:反面狩獵只收一手(數據/日期/公告/filing/先例);強制回答
  「Tier-1 佐證掂嘅係承重 claim 定周邊事實?」;必做 balance-sheet 現金背書檢查。
- 約束:只新增本檔,冇改 themes.yaml / wiki / 任何現有檔。

---

## 1. 控方主張摘要

真.LTA 鎖客護城河(B 型),但已極度 priced-in(ttm_pe 兩隻皆 98th pctile)。
**承重 claim 三支柱**(themes.yaml + wiki + 2026-07-11 discovery radar group A):
- **(a) 具名產品廣度**:[[ATI]] 供應 7 款最先進噴射引擎鎳合金嘅 **6 款**(不可替代技術護城河);
- **(b) re-qualification 換供應鎖客**:[[CRS]] 客戶要重新認證先可以轉供應商(switching-cost 鎖);
- **(c) 多年期 LTA + capacity-constrained**:ATI 19 年 / CRS 15 年一致第一人稱「long-term
  agreements / not short-cycle demand / 24/7 full out」語言 = 結構性受限 + 多年能見度。

現行 verdict `real-moat-but-fully-priced`、confidence **0.24**、cycle **late**、
node magnitude_tier 兩隻皆 **2-3x**(priced-ahead)。sources 單一:`transcript-discovery-radar`(tier 3)。

**與前六單嘅關鍵源結構分別(必須先講清,否則會誤判):**
呢個 thesis 嘅承重證據係 **Tier-1 一手 earnings-call transcript**(corpus.db:ATI 73 篇 2007-2026、
CRS 72 篇 2008-2026),唔似 photonics(COHR/LITE 零一手逐字稿、全 Tier-2 分析文)。
即 (a)(b)(c) 三支柱嘅**機制陳述本身**係管理層親口、19/15 年一致——呢個係比 photonics
更硬嘅起點。本次紅隊唔係要否定護城河存在,而係逐支柱問:**「補全後嘅一手事實集,撐唔撐得起
控方用嘅『多年鎖死 + 唯一稀缺 + 無限切換成本』呢個強版本?」**

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道(Tier-1 財數,最鋒利;必做 balance-sheet 檢查)**

必做項:「19 年 LTA」有冇客戶真金現金背書,定純口頭 backlog?
`defeatbeta quarterly_balance_sheet`(9 季至 2026-03-31),對 deferred revenue / contract
liability / RPO / customer advance 逐行掃 —— **pilot MU「RPO $100B 唔喺 balance sheet」形態,
第三次完整複製:**

| | ATI(2026-03-31) | CRS(2026-03-31) |
|---|---|---|
| Current Deferred Revenue | **$154.4M** | **$6.0M** |
| 佔 TTM 營收 | ~3.4%(TTM rev ~$4.59B) | **~0.2%**(TTM rev ~$3.03B) |
| 9 季走勢 | $161.6M→$154.4M **平穩略降** | $13.7M→$6.0M **跌 ~56%** |
| Non-current 客戶合約負債 | **無**(non-current = pension $196.5M + other) | **無**(標「Non Current Deferred Liab $176.4M」= deferred **TAXES**,同 Non Current Deferred Taxes Liabilities 同一個數) |
| RPO / remaining performance obligation row | **零** | **零** |

- **判定:「19/15 年 LTA」喺 balance sheet 上零現金背書。** 客戶並冇用預付/存款鎖多年供應——
  CRS 嘅 deferred revenue 仲要**由 $13.7M 跌到 $6.0M**,同管理層口講嘅「customers prioritizing
  security of supply, asking when they can book more」**行為上相斥**(真慌嘅買家會預付鎖量;
  呢度冇)。ATI $154M 較大但只係一般製造商正常 advance-billing 水平、平穩略降、無 non-current 腿。
- **獨立第二渠道(一手 filing)完全印證同一結論**(見動作 1b):ATI FY2024 10-K 明文
  「LTA **do not represent the contract with the customer**」;confirmed-order backlog **$3.9B、
  其中 70% 喺 12 個月內**;CRS 用 practical expedient **免披露 RPO**。→ 承重支柱 (c) 嘅
  「多年鎖死」係**披露式 backlog / 需求能見度,唔係入帳緩衝或合約現金地板**。

**(b) 外部一手(WebSearch,篩走意見文;派工只收 filing / earnings / OEM 官方指引 / LME)**

- **LTA 合約硬度(直接打支柱 c)**:ATI 8-K 附件 99.1(2023-06-19)原文——「secured an
  **estimated** $1.2 billion in new sales commitments」、「**$200M per year in estimated
  revenue** 2024-2029」;通篇「estimated / commitments」,**無 binding / take-or-pay /
  minimum purchase 字眼**。CRS 舊 Pratt 12 年最低採購量約 2025 屆滿、已從現行 10-K 消失。
  → wiki 記嘅「$1.2bn 新承諾」係**估算 framework 能見度,唔係現金保證**。
- **供給回應(kill 軸,最強一手信號:龍頭自己填缺口)**:
  - **ATI**:2026 capex 淨額 $220-240M,投**全新初熔 VIM 爐 + 鎳熔煉系統**,**2027 上線**,
    目標 **2028 年中 $350M 增量鎳收入 run-rate**(Q4 2025 電話會)。
  - **CRS(Carpenter)**:Athens AL $400M brownfield、**1 台 VIM 爐**、+9,000 噸(+7% SAO 產能),
    FY28 commissioning,qualification 拖到 **CY2030**。
  - **VDM Metals(Acerinox)**:€67M、產能 +15%、2027 完成。中國撫順特鋼規劃 +6 台真空感應爐;
    AECC-BIAM DD6 第二代單晶已裝國產航發(未進西方 OEM qualification)——侵蝕「全球僅 6-7 家
    最先進」唯一性敘事,但未直接切入西方引擎供應鏈。
- **原料價(反而幫控方,排除平庸解釋)**:LME 鎳 2024 均價 $16,812/噸(**較 2023 跌 22%**)、
  2025-26 低位盤整。ATI/CRS 兩家都以**剔除 surcharge 口徑**報利潤率;**鎳跌 22% 期間 ex-surcharge
  利潤率仍連續擴張**(CRS SAO 調整營業利潤率 25.2%(Q4FY24)→ **35.6%(Q2FY26)**、連 17 季;
  ATI 毛利率 FY24 20.6%→FY25 22.0%)。→ 毛利擴張**唔係原料順風/成本轉嫁**,係真.差異化定價權。
- **build-rate(平庸週期解釋:災後復產 catch-up,唔係滿產基線上嘅新結構擴張)**:Boeing 737 MAX
  Q4 2025 升至 42/月、787 過渡 8/月(措辭「穩定」非「加速」);Airbus A320 rate-75 推至 **2027 年底**、
  口徑軟化 70-75、**點名 P&W 引擎供應不足拖累**、A350 由 10 砍到 6/月;GE Aerospace Q1 2026 交 520 台
  LEAP(+63% YoY)「demand continues to exceed supply」backlog $211B。→ 需求真、未見頂、卡喺供給,
  **但 rate-75 / rate-47 一旦達標(2027-2028),OE 增量斜率會 mean-revert**。
- **估值 / 一致預期(熊案未觸發,屬「等 catalyst」)**:ATI 2026-06-22 ATH $204、YTD +41%、
  trailing P/E **62**、EV/EBITDA 32;CRS P/E **59**、兩年升逾兩倍。ATI Q1 2026 管理層一手否認
  de-stock:「**no changes to our order books or request for delivery deferrals**」;guidance 全上調、
  無 cut/miss。唯一近似熊訊 = 內部人:**CRS 過去一年 13 宗賣、0 宗買**(叢集但金額細);
  ATI CEO 10b5-1 預定賣(證據力弱)。無空頭報告、無減值。

**(c) 歷史先例(航太合金 de-stock,corpus 內一手)**

- **KALU(Kaiser Aluminum)2016-10-20**(同批 discovery radar group A 一手 transcript):
  「our lead times for heat treat plate are **down to six weeks** and we have indications that the
  aerospace supply chain will experience **destocking in 2017**」——同一航太金屬子行業,
  「lead times extending」語言喺一個週期內**反轉成 destocking** 嘅一手先例。證明航太合金嘅
  「交期拉長 = 多年能見度」敘事有內生週期性,唔係單向結構。
- 機制與 pilot 一致:MU RPO $100B、photonics COHR/LITE order-book-to-2028 —— 兩次都係
  「披露式 backlog 隨週期蒸發」。本簿呢類「backlog/LTA = 地板」claim,經一手核實後已**三連軟**。

### 動作 2 — Steelman 反方(非 wiki/文章自供,事實錨齊)

**「LTA『多年鎖死』其實係軟 framework 能見度 + 航太 build-rate 復產高峰,唔係合約級多年護城河」:**
1. ATI FY2024 10-K 一手:「LTA do not represent the contract with the customer」、可執行義務只在
   PO 層產生、confirmed backlog $3.9B 其中 70% 喺 12 個月內 → 真正合約能見度 ≈ **12 個月,唔係 19 年**;
2. balance-sheet 一手:CRS deferred revenue 跌到營收 0.2% 且下降、ATI 無 non-current 客戶合約負債 →
   客戶**冇**用現金鎖多年量;
3. 8-K 一手:$1.2bn 係「estimated commitments」,無 take-or-pay / minimum purchase;
4. OEM 一手:需求爆滿嘅近因係 Boeing 罷工/品質災後復產 + P&W 引擎荒(Airbus 親口),
   係 **catch-up 週期**,rate-75/47 達標後 mean-revert;
5. 先例:KALU 2016 同子行業「lead times → destocking」一個週期內反轉。

呢條 steelman 唔需要「航太需求係假」(需求真、未見頂)——就算需求全真,**LTA 合約長度 ≠ 真實鎖死
長度、當下緊絀 ≠ 多年結構樽頸**。

### 動作 3 — 平庸解釋測試

**悶故事:「航太 build-rate 復產超級週期高峰 + 特種金屬慣常緊絀」可以解釋幾多?**
- 解釋到:order book 爆滿、交期拉長、24/7 full out、提價、guidance 上調——全部係任何航太上行週期頂
  嘅標準現象(radar report 入面 KALU/STLD/OSK 同窗口都有齊「sold out / lead times extending」語言)。
- **解釋唔到(結構故事嘅額外證據,幫控方)**:
  1. **ex-surcharge 毛利連 17 季擴張、期間鎳跌 22%** —— 純週期/成本轉嫁解釋唔到定價權嘅**持續**擴張;
     呢個係差異化/qualification 護城河嘅真.簽名(悶故事會預期毛利跟商品價擺)。
  2. **具名產品廣度(6/7)+ re-qualification 認證難** —— Special Metals S-1(SEC 1997)一手:
     「all superalloy producers must secure certifications from GE, Rolls Royce, Pratt & Whitney and
     SNECMA, which are **difficult to obtain because extensive product evaluations including engine
     testing** are usually required」。技術/認證護城河係真、Tier-1 錨定。
- **可區分觀測(datable)**:
  1. **2027H2–2028 = 天然實驗**:ATI VIM 爐 2027 上線 + Carpenter Athens FY28 + 供給缺口填補期
     撞正 rate-75/47 達標。若交期/ex-surcharge 毛利捱得過新產能上線 → 結構故事贏;若交期急縮 +
     毛利見頂 → 週期故事贏。
  2. **confirmed backlog $3.9B / 12-month cover 比率**:若 12-month cover 由高位滑落 = 能見度縮水確認。
  3. **客戶預付行為**:CRS/ATI deferred revenue 若始終唔升,「多年鎖單」就一直只係講稿。
- 結論:**支柱 (a) 差異化/定價權 —— 悶故事解釋唔到,有 ex-surcharge 一手 + 認證一手背書,生還。**
  **支柱 (c) 多年 duration —— 大部分可以齋用悶故事(復產高峰 + 慣常緊絀)解釋,區分要等 2027H2 實驗。**

### 動作 4 — kill 距離(逐條)

| kill 軸(現行 wiki) | 當下一手事實 | 距離判定 |
|---|---|---|
| **OEM build-rate guidance 回落** | 未回落但**斜率封頂**:Airbus A320 rate-75 推遲至 2027 年底、A350 由 10 砍到 6/月;Boeing「穩定」非「加速」;GE「demand exceeds supply」 | **未觸發、中距離**;真正風險係 rate-75/47 **達標**(2027-2028)後 OE 增量 mean-revert,唔係硬回落 |
| **LTA 新簽/backlog 成長停滯**（$1.2bn 唔再出現） | ATI 2026-04「several LTA in negotiation」仲 live | **未觸發,但軸 mis-specified**:「$1.2bn commitments 再出現」係監測一個**估算 framework 軟數字**(8-K 明文 estimated、無 take-or-pay)。用軟數字做 kill-metric 會遲報。**建議改監測 confirmed backlog $3.9B 趨勢 + 12-month cover + ex-surcharge 毛利**(見 §4) |
| **競爭者帶新產能上線,削弱 6/7 稀缺** | **最強一手 kill 訊號 = ATI/CRS 自己各上一台 VIM 爐**(ATI 2027 上線/2028 年中 $350M 鎳 run-rate、Carpenter Athens FY28/qual CY2030)+ VDM +15%@2027 + 中國 DD6 單晶入國產航發 | **未觸發、距離收窄:kill-window 2027H2 起**;稀缺唯一性有**時限**,龍頭親手填緊未來缺口 |
| **估值純 multiple 驅動持續擴張** | P/E ~60、YTD +41%、EV/EBITDA 32;但 guidance 全上調、backlog 創新高、毛利擴張 → 當下**唔係**純 multiple(有盈利/backlog 驅動) | **未觸發**;但 P/E ~60 令任何一軸觸發時下行 beta 放大 |

---

## 3. 判決:**部分中彈**(核心護城河生還且 Tier-1 更硬、量化錨中彈、duration 支柱降級)

按 §4b 校準:判決標準 = 承重 claim 面對補全後嘅事實集企唔企得住。逐支柱:

- **(a) 具名產品廣度(6/7)+ 差異化定價權 —— 生還,且比 photonics 更硬。** 機制係 Tier-1 一手
  (19 年管理層原話 + Special Metals S-1 認證一手),且 **ex-surcharge 毛利連 17 季擴張 / 鎳跌 22%**
  獨立擊穿「成本轉嫁」平庸解釋。呢支柱悶故事解釋唔到,係全 claim 最硬部分。**惟唯一性有時限**
  (2027H2 龍頭自建 + 中國 DD6),下次審查要重估。
- **(b) re-qualification 換供應鎖 —— 方向生還,量化版本未證。** 「認證難、要上機測試、time-consuming
  and costly」係 Tier-1(Special Metals S-1 / Nadcap)。但撐估值嘅**強版本**——「5-10 年上機 /
  切換成本近乎無限 / 歷史無人換過」——**全部係二手博客,零一手實案**(有日期、有涉事雙方、有量能
  轉移嘅換廠案例查唔到)。呢個 switching-cost 靠「冇人做過」嘅反面推論支撐,可證偽性低。
- **(c) 多年期 LTA / capacity-constrained duration —— 中彈(承重收緊)。** 呢度係 balance-sheet 把刀
  落腳:(1) ATI/CRS deferred revenue = 營收 3.4% / **0.2%(且下降)**、零 RPO、零 non-current 客戶
  合約負債;(2) ATI 10-K 明文「LTA ≠ 客戶合約」、confirmed backlog $3.9B 其中 **70% 在 12 個月內**;
  (3) $1.2bn 係 8-K 明文 estimated framework。→ **「19 年多年鎖死」係口頭/framework 能見度,唔係
  合約現金地板;真正合約能見度 ≈ 12 個月。** Pilot 嗰把「披露 backlog ≠ 入帳緩衝」嘅刀,
  **第三次落刀仍斬得中**(MU RPO → photonics order-book → 今次 LTA)。
- **Tier-1 佐證掂嘅係承重定周邊?(pilot 強制一問)**:Tier-1 一手 transcript **掂到承重機制**
  (6/7 廣度、認證、capacity-constrained 語言)—— 呢點勝過 photonics。但獨立 Tier-1 財數/filing 渠道
  掂 duration 支柱嗰刻係**陰性**(LTA 無現金背書);而 ex-surcharge 毛利/OEM build-rate 呢啲一手
  掂嘅係**周邊/已 priced**(定價權係結果、需求真係已知),唔掂「多年 duration」機制本身。

**Rubric 建議(§4a 掛鈎:2 分前提 = 承重 claim 經 Level-2 且生還):**
- **moat 格:2 → 1.5。** 具名廣度 + 認證機制真且 Tier-1(生還,值 ≥1.5),但格內「供給**結構性**
  受限」嘅 duration 半截被打:LTA 零現金背書、confirmed cover ≈12 個月、龍頭自建 VIM 2027H2、
  切換成本量化版未證。「一手證據顯示供給結構性受限」呢個 2 分判準,「結構性(耐久)」嗰截唔完整。
- **growth/耐久 格:建議 1(非 2)。** additive-機制唔成立——航太合金需求主要係 build-rate 週期
  (復產 catch-up + 長期客運增長),唔係創造全新需求;且「供給結構性慢」嗰半個判準正被 dated
  產能(2027-2028)侵蝕。營收/毛利兌現係真但耐久性未證。
- 估值格:**pe_pctile 98th → 0 分**(≥90 判準),兩隻皆全批最貴之二。資本配置格:ex-surcharge
  毛利擴張 + guidance 上調偏正,但 capex 由紀律轉放量($220-240M / $400M)本身係 §3 late-cycle
  頂訊號 → ~1。此兩格機械讀數,本協議不作最終覆核。

---

## 4. 建議(不執行;郁數留返日間 confidence 迴路)

- **confidence:建議維持 ~0.24(紅隊唔向下推)。** 理由(§4c 紀律:red-team 殺傷力唔准酌情折入
  confidence 數字):核心護城河**生還且 Tier-1 更硬**,現行 0.24 本身已為「transcript-only、
  未做 ROIC/TAM 深度」保守設定,而中彈嘅 duration/LTA-lock 風險**已被 late + 98th-pctile penalty
  吸收**。若日間套 §4a 凍結公式重算(moat 1.5 / capalloc ~1 / valuation 0 / growth 1,late×
  crowding penalty),落點約 **0.22-0.28**,與現值同區間——本紅隊唔構成向下修正理由,只確認
  現值合理 + 補完 kill 精度。
- **verdict:維持 `real-moat-but-fully-priced`。** 護城河真(且比 photonics 更硬)、priced-in 確認。
  wiki 措辭應補:(1)「多年期 LTA」標「披露式 framework 能見度、非 take-or-pay、10-K 明文
  『LTA ≠ 客戶合約』、confirmed cover ≈12 個月」;(2)「$1.2bn」標「8-K 明文 estimated」;
  (3) 記 balance-sheet deferred revenue 近零(CRS 0.2% 且下降)= 客戶無現金鎖多年供應;
  (4) 記 re-qualification switching-cost 嘅「5-10 年/無限成本」係二手、未有一手換廠實案。
- **kill 軸改寫(§4c 通道 1 精度修正,唔郁 confidence 數字):**
  - 軸 2「$1.2bn 再出現」係軟 framework 數字 → 改監測 **confirmed-order backlog $3.9B 趨勢 +
    12-month cover 比率 + ex-surcharge 調整營業利潤率**(呢三個先係一手、硬、可證偽)。
  - **新增 dated kill-window「2027H2」**:ATI VIM 爐上線 / Carpenter Athens FY28 commissioning /
    rate-75 達標期。checkpoint:新產能上線後交期同 ex-surcharge 毛利有冇捱得住。
  - 新增早期警戒標記(非 kill):CRS/ATI deferred revenue 持續 ≈0/下降、confirmed cover 由高位滑落、
    中國 DD6 進西方 OEM qualification。
- **sources cap 註記(§4a/§4c 通道 2):** theme 現為單一 source(`transcript-discovery-radar` tier 3),
  但該 source 罕有地係 **Tier-1 一手 transcript**。本次獨立第二渠道(10-K/balance-sheet)掂到嘅係
  duration 支柱嘅**陰性**(LTA 無背書)+ 定價權嘅**周邊正面**(ex-surcharge 毛利)——按 §4a 定義,
  **唔算「Tier-1 獨立擊中承重 claim」→ 唔脫 single-source cap**。惟 cap 對本 theme 不 binding
  (raw confidence < 0.30),cap 通道 moot。
- **magnitude 通道(§4c 通道 3):** 兩 node 已標 `2-3x`(priced-ahead),thesis 本身冇押「結構超級
  週期」嘅大倍數腿——本紅隊確認「多年 duration」未證,但**冇 magnitude 加成可收**(node 已係 fully-
  priced quality-at-price,唔係搏倍數)。此為特性,唔需 `magnitude_unconfirmed` 標記。

---

## 5. Meta-review(一句)

呢次 red-team 最有價值嘅發現有兩個對稱面:**一面**——承重護城河(6/7 具名廣度 + 差異化定價權)
**比前六單都硬**,係 Tier-1 一手 + ex-surcharge 毛利穿越鎳跌 22% 嘅獨立驗證,唔應該為咗交 findings
而壓佢;**另一面**——「19 年 LTA 多年鎖死」呢個量化錨,一手 balance-sheet(deferred rev CRS 0.2% 且
下降、零 RPO)+ 10-K 明文(「LTA ≠ 客戶合約」、12-month cover)證實佢係**口頭 framework 能見度,
唔係合約現金地板**——pilot 嗰把「披露 backlog ≠ 入帳緩衝」嘅刀,**第三次落刀仍然斬中**,已足以
升格做 INGEST checklist 嘅常設一問:「凡承重 claim 靠 backlog/LTA/order-book 撐 duration,
先過 balance-sheet 現金背書關。」真正嘅 kill 唔喺外部競爭,喺龍頭自己 2027H2 上線嘅 VIM 爐。
