# Level-2 Red-Team：advanced-packaging（先進封裝 / AI 基板材料）

- 日期：2026-07-15
- 協議：thesis/DESIGN.md §4b（FALSIFY 升級：INGEST 係審判，唔係歸檔；含「事實補全非反對表演」校準 + pilot 三教訓）
- 角色：辯方 red-team。**職責 = 事實補全（搵敘事冇展示嘅重大事實），唔係反對表演。**
  每條反方必須錨喺可引用事實/數據；砌唔到錨定事實 = 標「敘事風險」，唔算 finding。
  「搵唔到重大遺漏」= 有效判決，照直報。
- Pilot 教訓已納入：反面狩獵只收一手（數據/日期/公告/SEC filing/先例）；強制回答
  「Tier-1 佐證掂嘅係承重 claim 定周邊事實？」；強制 balance-sheet 檢查（ai-power-grid GEV
  vs pilot MU 兩型辨識）。
- 約束：只新增本檔，冇改 themes.yaml / wiki / 任何現有檔。

---

## 1. 控方主張摘要

先進封裝係 AI 算力放量嘅**物理咽喉**（CoWoS 排到 2028、約 60% 給 NVDA、台積電自認缺口 3x；
上游 M9 CCL 三材料被日東紡/三井/Hoya 掐死），verdict `real-chokepoint-but-proxies-priced`，
confidence **0.32**（單一 Tier-2 源 gooptions-trend-core，違 §4a single-source cap 0.30），cycle late。

承重 claim 以 wiki + themes.yaml 讀到為準，拆**三個子命題**逐個審：
- **(i) 咽喉係真**（CoWoS/HBM/先進封裝產能結構性受限、售罄、提價）
- **(ii) 唔會短期解除**（材料層 2027-28 先放量、供給無彈性）
- **(iii) 可交易表達 = OSAT 軍火商 AMKR/ASX「誰贏都收錢」**（wiki 逐字：「本叢**最乾淨的可交易護城河邏輯**」，
  moat 2/2 嘅承重腿）

> 注意本 thesis 一個結構特徵：wiki **自己已經誠實承認**真瓶頸擁有者（日東紡/三井/Hoya）非美股、
> 可交易 proxy 全 90-100 分位 priced。故本次 red-team 唔係要拆穿「藏起嘅裂縫」，而係驗
> **moat 2/2 嗰兩分嘅一手地基**——特別係 (iii)：可交易 OSAT 名係咪真係「持有咽喉」定只係咽喉**下游**嘅代工。

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道（Tier-1，最鋒利）**

- **corpus 有一手 transcript，唔係零掛源（修正初判）。** ASX 同 AMKR **各 24 季**逐字稿
  （ASX 2020Q2→2026Q1 `transcript-ASX-2026-04-29`；AMKR 2020Q3→2026Q1 `transcript-AMKR-2026-04-27`，
  存 `thesis/corpus.db`）。**呢點同 photonics（COHR/LITE 零一手逐字稿）相反**——承重的稼動率/訂單語言
  有一手掛源。但 `themes.yaml` `sources:` **只登記 gooptions Tier-2**、未登記呢批一手（漏登記，見 §4）。
- **稼動率語言證實「當下緊」（一手，掂子命題 i）：** ASX 2026Q1 blended 稼動率 **~80%**、
  「capacities finite with limited ability to be pulled forward」、「capacity-constrained」；台灣廠
  「at or near full capacity」；ASE 先進封裝報價 2026-07-01 **再升 >20%**（TrendForce）。AMKR 先進封裝
  「lines filling up quite significantly」、「tightness of supply in some pockets」、基板受限。
  分析師逼問 ASX 有冇 order cut → 管理層答「**not seeing any order cuts**，AI peripheral 需求 more than
  offset softness」；ASX 2025Q3「customer pendulum swinging from booking as-needed to **prebooking
  capacities**」= 能見度**轉強**。→ **子命題 (i)「咽喉真、未見頂」被一手強化，比 photonics 更硬。**
- **⚔ 最鋒利一刀 — balance-sheet + 毛利：咽喉租金唔流去可交易名（掂 iii 承重腿）：**
  - **deferred revenue = pilot MU 型，唔係 GEV 型。** AMKR `Current Deferred Revenue`
    2023-03 **$80.6M → 2026-03 $81.8M**（三年**橫行**、僅佔單季營收 $1685M 嘅 **~4.9%**）；
    **ASX 資產負債表冇任何 deferred revenue / contract-liability / RPO 行**（唯一「Current Deferred
    Liabilities」數值同「Current Deferred **Taxes** Liabilities」一模一樣 = 遞延**稅**，非遞延收入）。
    ASX 口頭講「capacity will run 7 to 10 years」「10 years of AI cycles」、AMKR 講「multiyear value
    creation journey」+ 11 客戶/10 active engagement，但**冇任何現金/入帳合約義務背書**——同 ai-power-grid
    GEV「deferred revenue +70% 現金背書」**相反**，係 pilot MU「RPO $100B 唔喺 balance sheet」同型。
    **判定：ASX/AMKR = 披露式 backlog，唔脫 single-source cap。**
  - **毛利證實 OSAT **唔**捕捉咽喉租金（結構性、一手）：** 咽喉真、CoWoS 售罄、ASE 提價 >20%，
    但可交易 OSAT 名嘅毛利係商品級：**AMKR TTM 毛利 14.4%**（2026-03 14.2%、2025-03 低見 11.9%、
    仲**低過** 2022-09 嘅 20.2%——冇擴張，甚至倒退）；**ASX 2026-03 毛利 20.1%**，但只係**週期性回到
    2022 峰值**（2022-06 21.4%、2023 谷 14.8%），非突破。**最硬證據 = 管理層自己嘅多年指引**：
    AMKR Investor Day（2026-05-21 SEC 8-K）**2028 目標毛利 17.5%、2030 先至 22%+**；ASX 法說自陳
    「稼動率 80%+ 毛利先返 high 20s」= 滿載天花板都係 ~28%。**對照 photonics COHR/LITE 毛利 9 季擴張到
    37.7%/44.2%——嗰邊 Tier-1 至少證到定價權（周邊）；呢邊連定價權都唔喺可交易名度現形。**
    咽喉租金流去 TSMC（CoWoS 毛利 50%+，但 wiki 自己判 TSM「被侵蝕現任、不列多方」）同非美股材料商。
  - **存貨：AMKR 輕微反向**（$311M@2024-12 → $495M@2026-03，+59% 快過營收 +3%），一條要標記嘅溫和裂縫；
    **ASX 存貨乾淨**（76B TWD@2026-03，天數低過 2023 谷底 86B/131B）。
  - **「軍火商誰贏都收錢」= Tier-2 敘事，零一手原話。** 一手 transcript grep 全篇**冇**管理層講
    「無論邊個贏我都收」；只有間接：ASX 2025Q3「TSMC…build some CoWoS process, and Amkor committed to
    build some substrate process」。wiki 最乾淨嘅可交易 moat 邏輯，一手掛源 = **無**。

**(b) 外部一手（WebSearch，篩走意見文）**

- **供給回應 dated、部分收窄——直接打子命題 (ii)：**
  - **TSMC CoWoS 月產能**：2024末 ~35k → 2025末 ~75k → **2026末 ~125-130k wpm**（業界估算）；
    TSMC 官方原話（2026-05 技術論壇）**CoWoS 2022-2027 CAGR >80%**。加 OSAT 全行業 2026 ~200k wpm。
  - **缺口收窄（唯一明確 dated 一手）**：TrendForce 2026-06-15，CoWoS 供需缺口由 2026 年初 ~20%
    收至 **2026 年底 ~10%**、2027 進一步改善。
  - **但「追上需求」冇任何 dated checkpoint**；C.C. Wei「sold out through 2026」、後段封裝 lead time
    52-78 週、bookings 入 2027。ASX 2026 capex **上調至紀錄 US$8.5B**（Digitimes 2026-04-30），LEAP 收入
    指引 +10% >$3.5B。AMKR 2026 capex $2.5-3.0B，但**新增美國實質產能（Arizona $7B）量產要 2028**。
- **交期方向仍惡化 / 提價未停（幫控方）**：搵唔到任何「先進封裝或 HBM 產能會喺某具體日期追上/超過需求」
  嘅一手；ASE 2026-07-01 仲加價 >20%、SK Hynix 2026 sold out、Micron 2026 fully booked、
  TrendForce 2026-06-02 稱 **HBM 2027 合約價料翻倍**（反向指標，2027 仍緊）。
  **kill 軸「產能 ramp 超前需求」當下未觸發。**
- **反面事實真實但錯位**：放緩集中 **mainstream / 消費端**（PC/手機/汽車/iOS），AMKR 合理化 7 間日本廠、
  「underutilized mainstream assets」；AI/先進封裝側 tight/full。**冇任何一手講 AI 側 backlog 見頂或能見度
  轉弱**——反面事實掂唔到承重 AI 咽喉腿。

**(c) 歷史先例**

- **無直接可比嘅「OSAT 封測泡沫爆破」先例落到手**（未搵到一手，標記為缺口，唔當 finding）。
  可比機制參照 pilot：MU「RPO $100B」+ photonics COHR「order book 到 2028」皆被本系統驗為披露式 backlog；
  本單 ASX/AMKR 屬同一類（口頭多年能見度、零入帳背書），**係本系統第三次落同一把刀**。

### 動作 2 — Steelman 反方（非 wiki/文章自供，事實錨齊）

**「可交易 OSAT 名（AMKR/ASX）係咽喉**下游**嘅商品代工，唔係持有咽喉——咽喉租金流去佢哋買唔到嘅實體」：**
1. **管理層自己嘅多年毛利指引**：AMKR 8-K（2026-05-21）**2028 GM 17.5% / 2030 GM 22%+**；ASX 自陳滿載
   天花板「high 20s」。咽喉若真被 OSAT 持有，售罄 + 提價 >20% 應推毛利上結構性新高（如 TSMC 50%+、
   memory 擴張型），而唔係停喺 17-28%。
2. **deferred revenue 零增長 + ASX 零 contract-liability 行**：客戶**冇**用現金鎖多年供應
   （對比 photonics COHR 就預付 $22M 鎖上游 AXT——真慌買家嘅行為喺別處有示範，但 OSAT 嘅下游客戶
   冇對佢哋做）。「7-10 年能見度」係講稿，唔係入帳。
3. **供給回應快（CAGR >80%、缺口 20%→10% by 2026 末）**：OSAT 先進封裝產能可擴、且正快速擴
   （ASX capex 破紀錄 $8.5B）——「供給無彈性」呢個 (ii) 前提對 **OSAT 層**唔成立（只對非美股材料層成立）。

呢條 steelman 唔需要「AI 需求係假」——就算 AI capex 全真，咽喉租金嘅**歸屬**同咽喉嘅**可交易性**
係兩回事；OSAT 稼動滿 ≠ OSAT 持有定價權。

### 動作 3 — 平庸解釋測試

**悶故事：「AI capex 週期高峰 + 半導體常規復甦」可以解釋幾多？**
- 解釋到（可交易 OSAT 層，齊）：ASX 營收 2022 峰（189B）→2023 谷（133B）→2024-26 復甦返 ~2022 水平
  （174B）= 教科書週期；毛利週期性回峰值非突破；AMKR 2025Q1 營收仲 dip 穿 2024Q1；稼動率 ~80% + 提價 =
  任何硬體週期頂嘅標準現象（DRAM 2017-18、車用 MCU 2021 都有齊）。**呢層唔需要「結構性多年樽頸」呢個更強假設。**
- 解釋唔到（結構故事嘅額外證據，真）：(1) AI 加速器**物理上必需**先進封裝（無繞過路徑）= 工程事實，
  非週期現象；(2) 上游材料（T-glass 日東紡 90% / HVLP 三井配額）供給無彈性、2027-28 先放量 = 真結構
  ——但**呢兩點都指向非美股實體**，唔係可交易 OSAT 名嘅護城河。
- **可區分觀測（datable）**：
  1. **2026 年底 = 天然實驗**：TrendForce 缺口 20%→10% 若落地兼 ASE 提價停/回吐 → 週期故事贏；
     若售罄 + 提價捱過新產能上線 → 咽喉真有 duration。
  2. **AMKR 毛利 vs 自己 2028 指引（17.5%）**：若毛利始終困 mid-teens = 坐實「OSAT 唔捕捉租金」。
  3. **deferred revenue / customer prepayment**：若始終唔升 = 「多年鎖單」一直只係講稿。
- 結論：**子命題 (i) 咽喉真——一手強化（比 photonics 硬）；(iii) 可交易表達嘅 moat——悶故事解釋晒
  可交易 OSAT 名嘅財數，結構租金唔喺佢度**；(ii) 對材料層真、對 OSAT 層被 dated 供給回應侵蝕。

### 動作 4 — kill 距離（逐條）

| kill 軸（現行 kill_condition 拆解） | 當下一手事實 | 距離判定 |
|---|---|---|
| **上游材料瓶頸鬆動**（T-glass/HVLP 2027-28 提前放量、Q-glass 去獨家） | 無一手指提前；材料層仍 2027-28 先放量 | **未觸發、遠**（材料層供給無彈性係本 thesis 最硬腿，但**非美股、買唔到**） |
| **格式戰收斂單一贏家**（吸走 AMKR/ASX 軍火商溢價） | CoWoS 在位 + EMIB-T 追（Google 2028 向 INTC 下單 >300 萬顆，#152）；兩制並存 | **未觸發**；但**注意**：軍火商溢價本身係 Tier-2 敘事、一手毛利（17-28%）顯示溢價**本來就細**——就算收斂，可交易名損失有限 |
| **CoWoS/EMIB 產能 ramp 超前 AI 需求**（咽喉→過剩） | CoWoS CAGR>80%、2026末 ~125-130k wpm；TrendForce 缺口 2026末 20%→10%；但仍 sold out through 2026、HBM 2027 價料翻倍、Amkor 新增產能 2028 先到 | **未觸發、距離收窄中：第一個可證偽窗口 = 2026 年底**（缺口讀數 + ASE 提價 cadence）；「追上需求」無 dated checkpoint，最遠一手只到「2027 改善」 |
| **可交易 proxy 估值分位由 90-100 均值回歸**（peak-multiple 破裂） | AMKR 91/ASX 90/TTMI 96/MKSI 94/KLAC 94 分位；#150 出稿日設備股盤中回檔 6-10% | **持續有效**，同 [[ai-capex-macro-risk]] 聯動；本次無新事實，係最可能先觸發嗰條 |
| **早期警戒標記（非 kill）** | AMKR deferred rev 停滯 ~$81M + 存貨 +59%>營收；ASE 提價 cadence；AMKR 毛利 vs 2028 指引 17.5% | 新增，見 §4 建議 |

---

## 3. 判決：**部分中彈**（咽喉腿一手生還兼強化；可交易 moat 腿中彈、租金歸屬證偽；duration 半句降級）

按 §4b 校準：判決標準 = 承重 claim 面對補全後嘅事實集企唔企得住。逐子命題：

- **(i)「咽喉真」——生還，且一手強化（初判修正）。** 同 photonics 唔同，ASX/AMKR **有 24 季一手逐字稿**：
  稼動率 ~80%、finite capacity、not seeing order cuts、客戶轉 prebooking、ASE 提價 >20%、CoWoS sold out
  through 2026。呢腿有一手約束語言錨，悶故事解釋唔到「AI 側零 order cut + 能見度轉強」。
- **(iii)「可交易表達 = OSAT 軍火商 moat 2/2」——中彈（本次最鋒利發現）。** 三條一手事實同斬：
  (a) AMKR 自己 2030 目標毛利 22%+ / 2028 17.5%、ASX 滿載天花板 high-20s——咽喉租金**唔流去可交易名**；
  (b)「誰贏都收錢」零一手原話、係 Tier-2；(c) 真咽喉擁有者（TSMC CoWoS + 日東紡/三井/Hoya）wiki 自認
  非本 thesis 多方 / 非美股。**§4b rubric moat 2 分判準「一手證據顯示供給結構性受限，且有可交易名直接
  持有咽喉」——後半截明確 FAIL**：AMKR/ASX 係咽喉**下游**代工，稼動滿但商品毛利，唔持有咽喉。
- **(ii)「唔會短期解除」——對材料層生還、對 OSAT 層部分中彈。** 材料層供給無彈性真（非美股）；
  但 OSAT/CoWoS 層供給回應 dated 且快（CAGR>80%、缺口 2026末 20%→10%、ASX capex 破紀錄）。
  當下未解除（提價未停、售罄），但 duration 係「2027 定 2028」嘅時點問題，唔係「有冇」。
- 附：deferred revenue = pilot MU 型（披露 backlog、零現金背書），**唔脫 single-source cap**；
  AMKR 存貨 +59% 係唯一龍頭財數反向裂縫（溫和）；ASX 財數乾淨。

**Rubric 建議（§4a 掛鈎：2 分前提 = 承重 claim 經 Level-2 且生還）：**
- **moat 格：2 → 1。** 咽喉真（一手），但 rubric 2 分要求「可交易名直接持有咽喉」明確 FAIL：
  真咽喉喺不可交易實體（TSMC/日東紡/三井/Hoya）、可交易 OSAT 名一手毛利（14-28%）證實唔捕捉租金、
  「軍火商」moat 係 Tier-2 無一手。正中 rubric 1 分錨點「樽頸真但護城河**主要喺不可交易實體**；
  或證據主要 Tier-2」。
- **growth 格：維持 2/2。** additive 機制（AI 算力必需先進封裝、無繞過）一手兌現（稼動填滿、
  computing multi-year acceleration、2.5D 11 客戶 4 個 2026 量產）；供給結構性慢對材料層成立。
  惟「多年」duration 係口頭非入帳，下次審查若 2026 底缺口如 TrendForce 收窄要重估。
- **估值（0.5）/ 資本配置（1）格照舊**——機械讀數，本協議不覆核。

---

## 4. 建議（不執行；郁數留返日間 confidence 迴路）

- **confidence：0.32 → ~0.26。** 公式重算：moat 2→1 令 base (1+1+0.5+2)/8 = **4.5/8 = 0.5625** ×
  penalty ~0.46 ≈ **0.26**。呢個數**低過** single-source cap 0.30，故 cap 唔再綁定（cap 係天花板非地板）；
  即使有人爭議 moat 唔應降、維持 0.32，**single-source cap 仍獨立強制 ≤0.30**——兩條路都證 0.32 太高。
- **verdict：維持 `real-chokepoint-but-proxies-priced`。** 呢個 verdict 本身準確——咽喉真、proxy 貴——
  本次抗辯係補實「proxy 唔止貴、仲唔捕捉咽喉租金」。
- **sources 漏登記要補（§4a 執行檢查）：** `sources:` 現只列 gooptns Tier-2，但 corpus 有 ASX/AMKR
  各 24 季一手逐字稿 + AMKR 8-K Investor Day。建議登記為 Tier-1，但 `corroborates:` 要**誠實標**：
  一手掂到嘅係「當下咽喉緊 / 未見 AI order cut」（周邊 + 子命題 i），**唔係**「OSAT 持有咽喉 / 多年
  現金鎖單」（承重 iii 反而被同一批一手毛利/BS **證偽**）。故照 photonics 先例（毛利擴張掂周邊唔掂
  duration，不解 cap），**呢批一手同樣唔足以解 single-source cap 至 raise confidence**。
- **wiki 措辭應改（記錄用）：** (1)「軍火商誰贏都收錢」標「Tier-2 敘事、無一手管理層原話」；
  (2) 記 AMKR 2028/2030 毛利指引 17.5%/22%+ + ASX high-20s 天花板 = 咽喉租金唔流可交易名；
  (3) 記 deferred revenue ~$81M 橫行 + ASX 零 contract-liability 行 =「披露 backlog ≠ 入帳緩衝」
  （pilot MU 第三次同型）；(4) 記反面事實錯位（mainstream 弱 / AI 側緊）。
- **kill 軸調整建議：** 現行四軸方向正確。新增早期警戒標記（非 kill）：**AMKR 毛利連續季持平 mid-teens
  兼低於自己 2028 指引 17.5%**、**deferred revenue 持續 ~$81M 不升**、**ASE 先進封裝提價 cadence 停/回吐**、
  **2026 年底 TrendForce CoWoS 缺口讀數（20%→10% checkpoint）**。「格式戰收斂」軸可降權——一手毛利顯示
  軍火商溢價本來就細，收斂對可交易名衝擊有限。

---

## 5. Meta-review（一句）

呢次 red-team 最有價值嘅唔係搵到反面，而係**分離咗「咽喉真唔真」同「咽喉可唔可以買」**：一手逐字稿把
子命題 (i) 撐得比 photonics 更硬（真有 order-book 未見頂），但同一批一手（管理層自己嘅 2028/2030 毛利
指引 17.5%/22%+ + 零 deferred-revenue 背書）反手證偽咗承重腿 (iii)——咽喉租金流去你買唔到嘅實體。
pilot 嗰把「披露 backlog ≠ 入帳緩衝、Tier-1 掂周邊定掂承重」嘅刀，第三次落刀仲係斬得中，
應正式升格做 INGEST checklist 常設一問。
