# Level-2 Red-Team：photonics-optical（光通訊 / 矽光子）

- 日期：2026-07-15
- 協議：thesis/DESIGN.md §4b（FALSIFY 升級：INGEST 係審判，唔係歸檔）
- 角色：辯方 red-team。**職責 = 事實補全（搵敘事冇展示嘅重大事實），唔係反對表演。**
  每條反方必須錨喺可引用事實/數據；砌唔到錨定事實 = 標「敘事風險」，唔算 finding。
- Pilot 教訓已納入：反面狩獵只收一手（數據/日期/公告/法律先例）；強制回答
  「Tier-1 佐證掂嘅係承重 claim 定周邊事實？」
- 約束：只新增本檔，冇改 themes.yaml / wiki / 任何現有檔。

---

## 1. 控方主張摘要

光互連係 AI scale-up 嘅物理層瓶頸（銅撐 3 米、TAM $15B→$154B）；
**承重 claim = 「InP 基板/雷射 IDM 係真.供給樽頸（雷射交期 32 個月、order book 到 2028），
且光互連係 AI scale-up 物理層必經之路——樽頸唔會短期內被解除或繞過」**
（verdict: `real-bottleneck-but-crowded`，confidence 0.30，cycle late，全簿最擠叢 58% bull）。

承重 claim 拆三個子命題逐個審：
- (i) 樽頸係**真**（32 月交期、order book 到 2028）
- (ii) 樽頸**唔會短期內被解除**（產能追唔上）
- (iii) 樽頸**唔會被繞過**（光互連物理層必經、CPO/LPO 唔係逃生門）

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道（Tier-1，最鋒利）**

- **corpus 零 COHR/LITE 一手逐字稿。** `thesis/.raw/transcripts/` 只有 DTE/MU/WEST 三隻；
  `corpus.py ticker COHR/LITE` 各返 30 篇全部係 gooptions `trend-core-research-*` Tier-2 分析文。
  即成叢 24 篇報告嘅一手渠道覆蓋 = 零。
- **「32 個月交期」出處判定 = Tier-2 自陳，零一手掛源。** 原文 #092（2026-05-30）
  「磷化銦雷射交期一路拉到 32 個月」——同篇其他數字（高盛 TAM、NVDA 支票）都有掛源，
  **唯獨 32 個月冇任何 earnings/行業機構出處**。外部一手狩獵同樣追溯唔到呢個數字
  （只能一手證到「EML 交期推過 2027」「30%+ 供給缺口」，TrendForce / Lumentum 法說，2026）。
- **「order book 到 2028」係口徑放大鏈嘅中間層。** gooptions 自己嘅 #139 體檢文已拆穿三口徑：
  CEO 2026-03 一手精確講「售罄到 **2027 年底**」→ 法說轉述鬆成「下兩年 ≈ 2028」→
  KOL 灌水到「2029」兼錯掛出處。wiki 引用嘅「2028」係比 CEO 一手口徑鬆一級嘅定性轉述。
- **財務驗證（defeatbeta，9 季至 2026-03-31）——pilot MU 形態完全複製：**
  - COHR/LITE balance sheet **都冇 RPO row**；唯一入帳緩衝 Current Deferred Revenue
    細到可忽略（COHR ~$62M、LITE $1→$7M）。「order book 到 2028」係**披露式 backlog（講稿），
    唔係現金背書嘅合約義務**——同 pilot「MU RPO $100B 唔喺 balance sheet」同一形態。
  - **毛利擴張係真（掂周邊，唔掂 duration）**：COHR 毛利 30.3%→**37.7%**（9 季單調）、
    LITE 16.2%→**44.2%**；營收 COHR $1209M→$1806M、LITE $366M→$808M。
    證實「而家賣得起價」（定價權/供需偏緊嘅**結果**），但 12 個月緊、24 個月緊、
    32 個月緊都同呢組數相容——毛利分唔到 duration。
  - **COHR 存貨裂縫（反向信號）**：存貨 $1292M→**$2127M**（+65%）快過營收（+49%）、
    近四季加速、**WIP $628M→$1238M 翻倍**、存貨天數 ~138→~170 日。
    真.32 月交期嘅緊絀，龍頭應該出貨即走——WIP 暴脹係雙義（InP pre-build vs 需求前置裂縫），
    係一條要標記嘅真張力。**LITE 相反係乾淨緊絀簽名**：存貨 +50% 慢過營收 +90%、
    Finished Goods 反跌（$104M→$87M）。
- **Insider（EDGAR 180 日，剔機械交易後）**：COHR net −$2.7M、LITE net −$12.5M，
  兩隻**零 P-buyer、無 cluster**。弱陰性：冇任何 insider 獨立追認承重 claim。

**(b) 外部一手（WebSearch，篩走意見文）**

- **供給回應有一手、有日期、部分落喺短期**——直接打子命題 (ii)：
  - **AXT/Tongmei**：2026Q1 完成 **$632.5M 融資**；公司稱 2026 InP 產能 vs 2025Q4
    **翻倍且「ahead of schedule」**、2027 再翻倍 + 新專用 fab；2026-06-25 同 Coherent
    簽三年 6 吋 InP Master Supply Agreement；InP backlog 破 $100M（SEC 8-K / investors.axt.com）。
  - **住友電工**：數據中心光元件產能 **2028 = 2023 嘅 12 倍**、增產投資 ~¥1000 億
    （官方成長策略簡報，2025-11-13）。
  - **TSMC COUPE**：2026 下半量產；PIC 產能 500 → **10,000 wpm（2026Q2）** → 25,000 wpm（2028）
    （TSMC PR + TrendForce/Digitimes）。
  - **雲南鍺業（鑫耀）**：中國唯一 6 吋 InP 量產，良率 **70–85%**、¥1.89 億擴產、
    華為鎖 53% 產能（東方財富，2026-04）；惟中國僅佔全球 ~10%。
- **交期方向反而惡化（幫控方）**：搵唔到任何「32 月縮短」一手報導；TrendForce 稱 NVDA
  鎖起大部分 EML 產能、交期推**過 2027**；Lumentum 法說披露 **30%+ EML 缺口且擴大**。
  kill 軸 1 當下未觸發。
- **CPO 時程係「加速」唔係淨延後**：Broadcom 第三代 CPO（TH6-Davisson 102.4T）
  **2025-10-08 已出貨**；NVIDIA Quantum-X 2026 上半商用、出貨指引 >10,000 → **50,000 台（5x 上調）**。
  （對照 wiki #143 記嘅「NVIDIA 延後一季」：兩者並存 = 時程雜訊，唔係方向逆轉。）
- **LPO/CPO 唔係繞過 InP（幫控方，最強擋子彈）**：LPO 只拆 DSP、因失去數位補償
  對雷射/調變器要求**更嚴**（IEEE EPS 等技術文獻一致）；CPO 外置雷射（ELS）要 400mW+
  高功率 CW = 現有 SiPho CW（30–70mW）嘅 **6–11 倍功率**（semiengineering / Lumentum ELS
  datasheet）。繞過路徑仍食 InP，且每 port InP 含量更高——需求可能由 EML **遷移**去
  CW DFB epi（樽頸換位，唔係換走）。子命題 (iii) 被事實強化。
- **Double-ordering 已被行業一手證實**：LightCounting 明講「客戶因預期持續短缺而超額下單,
  加劇問題」、短缺「**應於 2026 年底消退**」、屆時 double ordering 消失 → 跌價加速 + 庫存積壓。
  AOI 2026-04 單月收 $71M 上調 800G 訂單、backlog 翻倍——訂單能見度嘅耐久性可疑。

**(c) 歷史先例（2000 光纖泡沫）**

- **JDS Uniphase**：營收 $283M（FY99）→ $3.23B（FY01）；2001-07 **$45B 減值**（當時史上最大）;
  2001-09 **財報重編**（channel stuffing / 對經銷商加速認列）;股價 $153 → <$2。
  上一輪「backlog = 能見度」敘事嘅死法 = double-ordering 退潮後 backlog 一夜蒸發。
- **今輪結構分別（真，幫控方）**：2000 = 電信商投機性長途 capex（暗光纖 ~95% 未點亮，
  需求係第三方投機）；今輪 = hyperscaler **自用** AI capex，需求端有真實算力對應。
- **但庫存幻覺機制兩輪相同**：LightCounting 一手證實超額下單正在發生（見上）+
  COHR WIP 翻倍——機制健在，只係幅度未知。

### 動作 2 — Steelman 反方（非 wiki/文章自供，事實錨齊）

**「order book 到 2028 = 雙重下單製造嘅假能見度，唔係結構性多年樽頸」**：
1. LightCounting（行業出貨統計機構）一手：客戶正超額下單、短缺應於 **2026 年底消退**；
2. COHR 自己財數：存貨 +65% 快過營收 +49%、WIP 翻倍、存貨天數 138→170 日
   ——同「緊到出貨即走」相斥；
3. deferred revenue 近乎零 = 客戶**冇**用現金鎖多年供應（真慌嘅買家會預付——
   對照 COHR 自己就預付 $22.285M 鎖 AXT 三年：買家真慌時嘅行為喺上游有示範，
   但 COHR/LITE 嘅下游客戶冇對佢哋做同樣嘢）；
4. 先例：JDSU 2001（backlog 蒸發 + 重編）、且 pilot 已證 MU「RPO $100B」都係
   披露式 backlog 唔係入帳緩衝——「backlog = 地板」呢類 claim 喺本系統已兩連敗。

呢條 steelman 唔需要「AI 需求係假」——就算 AI capex 全真,double-ordering 都可以
令 order book 長度 ≠ 真實需求長度。

### 動作 3 — 平庸解釋測試

**悶故事：「AI capex 週期高峰 + 慣常雙重下單」可以解釋幾多？**
- 解釋到：order book 爆滿、交期拉長、毛利擴張、提價——全部係任何硬體週期頂嘅標準現象
  （2017-18 DRAM、2021 車用 MCU 都有齊）,唔需要「結構性多年樽頸」呢個更強假設。
- 解釋唔到（結構故事嘅額外證據）：(1) LPO/CPO 技術路線**全部**收斂返 InP 雷射
  （繞過路徑唔存在——呢個係物理/工程事實,唔係週期現象）;(2) 無代工 IDM 結構
  （產能不可共享）係真;(3) hyperscaler 自用需求 vs 2000 投機需求嘅結構差異。
- **可區分觀測（datable）**：
  1. **2026 年底–2027 上半 = 天然實驗**：AXT 產能翻倍落地 + LightCounting 預測短縮消退期。
     若交期/提價捱得過新產能上線 → 結構故事贏;若交期急縮 + 跌價 → 週期故事贏。
  2. **COHR 存貨天數**：續升穿 170 日而營收減速 = 週期裂縫確認;WIP 轉化做出貨 = pre-build 證實。
  3. **客戶預付行為**：COHR/LITE deferred revenue / customer prepayment 若始終唔升,
     「多年鎖單」就一直只係講稿。
- 結論：**子命題 (i)(ii) 大部分可以齋用悶故事解釋**（區分要等 2026 年底實驗）;
  **子命題 (iii) 悶故事解釋唔到**,有工程事實額外背書。

### 動作 4 — kill 距離（逐條）

| kill 軸 | 當下事實 | 距離判定 |
|---|---|---|
| **InP 短缺解除**（交期壓縮/中國全面放行/新產能上線） | 交期方向仍惡化（EML 推過 2027、缺口 30%+ 擴大中）→ **未觸發**;但供給回應已由「宣言」變「dated 承諾」:AXT 2026 翻倍 ahead of schedule、2027 再翻倍;住友 12x@2028;TSMC PIC 20x@2026Q2;雲鍺 6 吋良率 70–85%。LightCounting:短缺 2026 年底消退 | **未觸發、距離收窄中:約 12–18 個月**(2026 年底–2027 上半係第一個可證偽窗口) |
| **CPO 導入時程實質落後**（LPO/可插拔續當 good-enough） | 兩向並存:NVIDIA 延後一季(#143)vs Broadcom 三代已出貨(2025-10)+ NVIDIA 指引 5x 上調至 50,000 台 | **軸本身 mis-specified**:本次狩獵證實 LPO/可插拔都食 InP 雷射(仲要更高質)——CPO 快慢只重排叢內贏家(SIVE vs ALAB),**掂唔到雷射 IDM 承重 claim**。建議改寫(見 §4) |
| **雷射 IDM 訂單能見度/定價破裂** | 毛利仍擴張(COHR 37.7%、LITE 44.2%,至 2026-03 季)→ **未觸發**;早期警戒標記 = COHR WIP/存貨天數 + deferred revenue 停滯 + double-ordering 退潮(LightCounting 預測 2026 年底) | **未觸發、中距離**;注意「能見度」基準應校返 CEO 一手口徑「售罄到 2027 年底」,唔係「2028」——用錯基準會令破裂遲報一年 |
| **crowding-unwind**（AI-capex 打嗝即重挫） | #141/#143 已現首輪(CPO 恐慌單日 −10%、AXTI −13%);58% bull 未實質消風 | 持續有效,同 [[ai-capex-macro-risk]] 聯動,本次無新事實 |

---

## 3. 判決:**部分中彈**(機制生還、量化錨中彈、duration 半句降級)

按 §4b 校準:判決標準 = 承重 claim 面對補全後嘅事實集企唔企得住。逐子命題:

- **(iii) 「唔會被繞過」——生還,且被補全後事實集強化。** LPO 拆 DSP 但要更高質雷射;
  CPO ELS 要 6–11x 功率 CW;TrendForce 證實需求向 InP epi 遷移。呢半句係全 claim
  最硬嘅部分,有工程事實錨,悶故事解釋唔到。
- **(i) 「樽頸真」——機制生還,量化錨中彈。** 供需偏緊係真(毛利 9 季擴張、交期仍惡化、
  COHR 預付鎖 AXT 上游),但「32 個月」係 Tier-2 自陳零掛源、「order book 到 2028」係
  CEO 一手「2027 年底」嘅放鬆轉述、balance sheet 零 RPO/deferred revenue 可忽略
  ——兩個承重數字都係敘事級,唔係一手事實。**Tier-1 真正掂到嘅(毛利/營收/預付)全部係
  周邊事實,唔係 duration 機制本身**——pilot 嗰把刀喺度斬中第二次。
- **(ii) 「唔會短期內被解除」——部分中彈。** 當下未解除(交期惡化中),但「唔會」呢個
  斷言而家對面企咗四線 dated 產能承諾(AXT/住友/TSMC/雲鍺)+ 一手證實嘅 double-ordering
  + LightCounting「2026 年底消退」預測。樽頸解除唔再係「有冇」問題,係「2027 定 2028」
  嘅時點問題。
- 附:COHR 存貨/WIP 裂縫係本次狩獵唯一喺龍頭財數入面搵到嘅**反向**硬事實;
  LITE 財數簽名反而乾淨。叢內質分層應記呢個差異。

**Rubric 建議(§4a 掛鈎:2 分前提 = 承重 claim 經 Level-2 且生還):**
- **moat 格:2 → 1.5。** 樽頸機制真 + 不可繞過(生還),但格內承重數字(32 月/2028)
  經抗辯後降級為敘事、且 duration 喺 Tier-1 財數零現形、COHR 有存貨反向裂縫
  ——「一手證據顯示供給結構性受限」呢個 2 分判準,一手嗰截唔完整。
- **growth 格:維持 2/2。** 「物理層必需」半句生還兼強化(工程事實錨);additive 機制
  已被財報兌現(營收 COHR +49%/LITE +90%、毛利同步擴張)。惟「供給結構性慢」嗰半個
  判準開始受 dated 產能侵蝕,下次審查若 AXT 2026 翻倍如期落地要重估。
- 估值(0.5)/資本配置(1)格照舊——機械讀數,本協議不覆核。

---

## 4. 建議(不執行;郁數留返日間 confidence 迴路)

- **confidence:0.30 → ~0.27。** 公式重算:(1.5+1+0.5+2)/8 = 0.625 × penalty ~0.43 ≈ 0.27。
  移動細因為 crowding penalty 已預先壓咗大部分風險;本次抗辯淨效果 = moat 半格。
- **verdict:維持 `real-bottleneck-but-crowded`**,但 wiki 措辭應改:
  (1)「32 個月交期」標「Tier-2 自陳、未經一手核實」;(2)「order book 到 2028」
  改用 CEO 一手口徑「售罄到 2027 年底」;(3) 記 COHR 存貨/WIP 裂縫 + LITE 乾淨簽名
  嘅叢內分層;(4) 記 deferred-revenue≈0 =「披露 backlog ≠ 入帳緩衝」(pilot MU 同型)。
- **kill 軸改寫:** 軸 2(CPO 時程)mis-specified——CPO 快慢掂唔到雷射 IDM claim,
  建議由「CPO 導入時程實質落後」改為「**任何一手證據顯示 LPO/CPO 路線減少每 port InP
  雷射含量/價值**」(而家事實方向相反,好清晰可證偽)。新增早期警戒標記(非 kill):
  COHR 存貨天數 >170 日兼營收減速、deferred revenue 持續≈0、AXT 2026 翻倍落地後
  交期/價格反應、LightCounting 2026 年底短缺消退 checkpoint。
- **sources cap 註記:** 本次 Tier-1 毛利擴張佐證掂嘅係周邊(定價權結果)唔係承重 claim
  (duration 機制),照 §4a 定義**唔足以**當獨立第二源解 single-source cap。

---

## 5. Meta-review(一句)

呢次 red-team 最有價值嘅唔係搵到反面,而係發現承重 claim 嘅兩個量化錨(32 月/2028)
喺 24 篇報告 + 一手財數入面追溯唔到源頭——「叢好大」同「地基好深」係兩回事,
pilot 嗰把「披露 backlog ≠ 入帳緩衝」嘅刀,第二次落刀仲係斬得中,應該升格做
INGEST checklist 嘅常設一問。
