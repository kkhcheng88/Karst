# Level-2 Red-Team：oil-gas-energy(石油天然氣 / 能源)

- 日期：2026-07-16
- 協議：thesis/DESIGN.md §4b(FALSIFY 升級：INGEST 係審判)+ §4c(三通道分流)
- 角色：辯方 red-team。**職責 = 事實補全(搵敘事冇展示嘅重大事實),唔係反對表演。**
  每條反方必須錨喺可引用事實/數據；砌唔到錨定事實 = 標「敘事風險」,唔算 finding。
- Pilot / photonics 教訓已納入：反面狩獵只收一手(數據/日期/公告/財數);強制回答
  「Tier-1 佐證掂嘅係承重 claim 定周邊事實?」
- 約束：只新增本檔,冇改 themes.yaml / wiki / 任何現有檔。

---

## 1. 控方主張摘要

`oil-gas-energy`(type B、confidence **0.25**、cycle **late**、verdict `thin-split-watch`)。
theme 自己 note 已標「THIN(2 reports)+ heterogeneous」——油 macro(#116 neutral、Brent
$100→$78、near-term oversupply/bearish)硬綁 gas→power(#058 bull、SEI 3.1 GW BTM buildout)。

**承重 claim(依任務定義,以讀到為準):**
1. **gas→AI 電力 behind-the-meter 需求**係結構性、**EQT 係最乾淨平價表達**(pe 10/35 分位 +
   紀律 capex + AI 表後拉動;Homer City 4.4 GW BTM 2027 啟動);
2. **油側 diversify** Iran-binary macro(XLE/XOP 避單名雷);
3. tickers 現含 KMI(discovery radar 逐隻驗證,一個 2023-10-18 gathering-at-capacity transcript datapoint)。

承重 claim 拆三個子命題逐個審:
- (i) gas→power 需求係**真**且**有現金合約背書**(mandated balance-sheet 檢查嘅落腳點)
- (ii) EQT 係**最乾淨平價表達**(cheap + 紀律 + 直接受惠)
- (iii) 呢個 theme **應唔應該係一個 thesis**(note 自認唔係;red-team 要判到底)

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道(Tier-1,mandated balance-sheet 檢查)**

一手來源:defeatbeta `quarterly_balance_sheet`(EQT/KMI,回溯 2022,Data Update 2026-07-16)
+ yfinance `quarterly_balance_sheet`(EQT/KMI/SEI/LNG 交叉核對,一致)。

- **EQT:客戶預付式 deferred revenue ≈ 零——gas→power 需求冇現金合約背書。**
  - Current Deferred Revenue 逐季:2026-03 `*`(可忽略)、2025-12 **$6.2M**、2024-12 $24.2M、
    2023-12 $2.9M。近乎不存在。
  - 表上 **$3,882M「Non Current Deferred Liabilities」= 100% deferred TAXES**(同
    「Non Current Deferred Taxes Liabilities」逐分逐分完全相等),**唔係客戶預付款**。
  - **Homer City 4.4 GW 係「agreement in principle」披露式 backlog,唔係入帳合約負債。**
    外部一手(Homer City Redevelopment PR、Natural Gas Intel):EQT 供氣「up to 665,000
    MMBtu/day、power slated 2027、GE Vernova 七台 7HA.02 turbine 2026 起交付」——真.工業訂單,
    但 primary release **冇** "behind-the-meter" 字眼(描述為 exclusive gas-supply agreement)。
    **同 pilot MU「RPO $100B 唔喺 balance sheet」、photonics COHR/LITE「deferred≈0」同一形態——
    披露 backlog ≠ 入帳緩衝,第三度落刀。**
  - 附(掂周邊、幫控方):EQT net debt **$7.8B→$5.7B**(一年去槓桿)、capex 平——**資本紀律屬實**。
- **EQT 係重度對沖商(hedge book 雙刃,一手):** Q1 2026 8-K/10-Q:衍生品**淨虧 $238M**、
  現金淨結算**付出 $304M**($114M NYMEX gas + $190M basis/liquids);遠期沽 call 均價 $4.94–5.13/Dth。
  → 對沖封住 gas 急升嘅上行(價升時 hedge 出血),「便宜 gas E&P 直接搏 AI-power gas 高價」嘅
  線性樂觀被 hedge book 削一截。
- **KMI:表上完全冇 deferred revenue 行——take-or-pay 唔係現金緩衝。**
  - 只有 deferred TAXES $3,120M;net debt **$31.9B**(多年平穩)= 高槓桿中游。
  - take-or-pay / MVC 係**收入確認合約條款**,唔會坐 balance sheet;所以「gathering 到 capacity」
    嘅需求 claim 喺財數上**冇現金印證**,且 note 引嘅 datapoint 係 **2023-10-18(2.5 年舊)**。
    屬 gas leg 自然延伸嘅弱佐證,唔升級。
- **SEI:四隻入面唯一有客戶預付(細但真、增長中);但 3.1 GW 係用槓桿唔係客戶現金建。**
  - Current Deferred Revenue $5.2M(2025-03)→ **$29.4M**(2026-03);Non-Current Deferred Revenue
    **$46.5M(2026-03 首度出現)**;合共 ~$76M。**係四隻入面唯一見到客戶真金預付款嘅名**——
    輕微正面,但 $76M vs「>2 GW 已簽 / $1B EBITDA」框架屬杯水。
  - **net debt 一年 4x 爆:$300M→$1,252M;total debt $328M→$1,618M**;再加 $1.3B 6.375%
    senior notes(2026-05-05 定價)。3.1 GW buildout 主要靠**債**,唔係客戶現金。
    annualized run-rate EBITDA ~$340–370M vs net debt $1.25B ≈ 3.5x 且快速上升 = 成長-capex-on-leverage 簽名。

**(b) 外部一手(WebSearch,篩走意見文,只留 dated 事實)**

- **最鋒利:thesis 喺戰爭「睇似結束」嘅 3 週窗口(6/17–7/01)寫成,而 macro 前提今日已 INVERT。**
  - 6/19 MOU **確實簽咗**(Trump-Pezeshkian,6/17 memorandum,Geneva 6/19 儀式;60 日免費過境 +
    30 日掃雷)——但 **~7/8 崩、美國 2026-07-14 重啟荷莫茲海軍封鎖**、7/14–15 連夜空襲、
    **3 艘油輪受損、1 名船員死亡**。**今日荷莫茲功能性再封、戰事再熱。**
  - Brent 路徑:$78.84(6/17)→ **跌穿 $74(6/24,戰爭以來首次)**→ **$70.82(7 月初 = 回到戰前價)**
    → **重上 $85 逼近(7/14–15,MOU 崩 + 美國復襲)**(TradingEconomics / Al Jazeera 7/8、7/15)。
  - Iran「$300B + 荷莫茲控制權」索賠:**primary 14-point MOU 文本追溯唔到**(標未證)。
- **Henry Hub gas:結構性「溫和」唔係「高」——「gas structurally high」措辭誇大。**
  $3.29/MMBtu(2026-07-06,EIA/FRED),中旬區間 $3.15–3.34。**方向受支持**(EIA 7/7 STEO
  上修 2026 年均 $3.67、Rigzone 7/15 報 EIA 調高 2026/27 預測、power-burn 45.6 Bcf/d +15% w/w),
  但**絕對值 $3.3 唔係極端高位**。#058 靠嘅「能源新秩序 / gas 結構高」係戰爭溢價敘事,gas 現貨唔背書。
- **SEI 治理二元:mis-dated + 半解決,冇爆成股災,但被告 insider 已清倉。**
  - Morpheus 空報告係 **2025-03-17**(唔係 2026!):指 co-owner **John Tuma** = 環保犯罪重罪犯、
    涉 $800M 休斯頓燃氣輪機圍標案;股價當日 **−16.9% 至 $20.46**。
  - 之後**反彈 ~3x**;證券集體訴訟(class period 2024-07-09→2025-03-25)**至 2026-04 仍 PENDING
    (motion-to-dismiss 階段)——未坐實、未撤銷**。
  - **KTR(Tuma)2026-04-30 前後以 $70.75 沽 2,000,000 股 Class A、直接持股削到零**——
    被指控 insider **喺 3.5x 低位反彈後全身而退**。治理質素黃旗,唔係股災觸發器。
  - **NOT FOUND**:任何 2026 SEC 執法 / 起訴更新 / 合約解約 / SEI 正式反駁。
- **SEI 3.1 GW / $1B EBITDA:capacity 獲印證且增長,冇解約;但 $1B 係 2028 stretch 唔係現實。**
  Q1 2026(4/27 一手 IR):rev $196M(+55%)、adj EBITDA $84M、簽第三家 IG 客戶(600+ MW、
  10+5 年)、>2 GW / 3 家客戶;Q2 guidance 上調 $83–93M。但 run-rate ~$340–370M 年化,
  **$1B 係 full-deployment(~2028)願景**;客戶集中(3 家、歷史 xAI 重)未解——正正 Morpheus 當年點名嘅風險。

**(c) 歷史 / 結構先例**

- 油側係**教科書地緣溢價 round-trip**:$126(3 月封鎖)→ $70(7 月初回戰前)→ $85(復襲)。
  「規模唔決定方向」(#116 自己嘅論點)已被自己驗證——但方向而家 invert 返上行。
- gas→power BTM 需求嘅**耐久 driver 係 AI-capex**(Aschenbrenner 100GW / Chamath >$700B),
  唔係戰爭;戰爭溢價 unwind 唔殺呢條腿,但呢條腿 = **ai-capex 軸**(同 memory/photonics/tpu 同軸),
  themes.yaml `meta_factors` 已補標 `ai-capex` 認咗呢點。

### 動作 2 — Steelman 反方(非 wiki/文章自供,事實錨齊)

**「呢個 theme 唔係一個 oil-gas thesis;剝晒之後淨返一個中性油-beta籃 + 一隻靠 ai-capex 嘅平價 gas 名(EQT)」:**
1. 油側 #116 自認 neutral;三力(OPEC+瓦解/制裁疲勞/中國需求)係**宏觀 β**,唔係 supply-constrained
   B 型定價權——油商係 price-taker,XOM/CVX/COP 高 PE = 谷底盈利(peak-earnings 鏡像,wiki 自認)。
   「XLE/XOP diversify」= **風控 knob(β 管理),唔係 alpha**(對齊 MEMORY:fear/greed MR α≈0)。
2. gas→power 腿嘅真 driver 係 AI-capex(themes.yaml 自己 meta-tag `ai-capex`),攞返去 ai-power-grid
   之後,「oil-gas-energy」剩低嘅方向性內容 = EQT 一隻平價 gas E&P + AI-power optionality(Homer City)。
3. SEI(唯一 bull 名)其實 cluster 屬 `ai-power-grid`(#049 frontmatter `cluster: ai-power-grid`),
   佢嘅承重 driver、估值(pe 97)、治理二元全部係 BTM-power 故事,唔係「油氣」商品故事。
4. themes.yaml meta 自己寫低:energy-macro cluster「borderline causal-test case、weaker than
   ai-capex's clean pass」——即系統內部已經知呢個 cluster 因果測試勉強過關。

呢條 steelman 唔需要「AI 需求係假」——就算 gas→power 全真,佢都係 **ai-capex thesis**,唔係
**oil-gas supercycle thesis**;而純油側係 neutral β。兩者夾埋 ≠ 一個方向 B 型主題。

### 動作 3 — 平庸解釋測試

**悶故事:「AI-capex 週期高峰拉動燃氣表後電力 + 油係一次普通地緣溢價 round-trip」解釋到幾多?**
- 解釋到:gas-power 訂單湧現、EQT/KMI gathering 緊、SEI 簽約加速、油 $100→$70→$85 波動——
  全部係「AI 硬體週期頂 + 戰爭溢價來回」嘅標準現象,唔需要「能源新秩序結構超級週期」呢個更強假設。
- 解釋唔到(結構故事嘅額外證據):**gas→AI-power BTM 嘅工業機制係真且 additive**——Homer City
  4.4 GW 已簽、GE Vernova turbine 2026 交付、power 2027;呢個唔係商品週期,係新增需求類別。
  **但呢條正正係 ai-capex 腿,唔係 oil-gas 腿。**
- **可區分觀測(datable):**
  1. **Brent $90 關**:若復襲推 Brent 決定性收復 $90 → 油側「near-term bearish」框架被**向上**證偽
     (= bullish kill 觸發,要改寫);若戰事再降溫回 $70 → super-glut 故事贏。**天然實驗當下進行緊。**
  2. **EQT deferred revenue / customer prepayment**:若始終唔升,「gas→power 多年鎖單」就一直只係
     Homer City 一單披露式 backlog,唔係現金合約組合。
  3. **SEI $1B EBITDA**:若 2027–28 run-rate 唔向 $1B 收斂(當下 $340–370M),magnitude 腿證偽。
- 結論:**子命題 (i) gas→power 需求係真但屬 ai-capex 腿、且無現金背書;(ii) EQT「最乾淨」成立但
  「最平價表達」嘅 upside 靠 hedge book 削返 + Homer City 未入帳;(iii) 悶故事幾乎解釋晒「oil-gas」
  部分——結構性溢價只喺 ai-power 腿,而嗰腿唔屬呢個 theme。**

### 動作 4 — kill 距離(逐條;含 kill_metrics 時效驗證)

| kill 條件 | 當下事實(2026-07-16) | 距離判定 |
|---|---|---|
| **油腿:Brent 決定性收復 > $90**(→ oversupply/bearish 框架失效、需改寫 bullish) | MOU 7/8 崩、美國 7/14 復封荷莫茲、Brent **重上 ~$85 逼近中**、3 油輪 7/14 受襲 | **未觸發但急速逼近(~$5)**;**⚠️ kill_metrics 記錄 `current:78 / as-of 2026-07-08` 已 stale ~$7 + 一次 regime flip**——theme 行緊近自己 kill 一個星期而 metric 未捉到(action-4 命中) |
| **油腿:Brent 跌穿 $60**(中國需求崩,long-energy-equity 腿破) | 7 月初低見 $70.82 後反彈,未近 $60 | **未觸發、遠** |
| **gas-power 腿:SEI 治理二元惡化**(Morpheus 坐實 / KTR 續拋 / 大長約解約) | Morpheus 係 2025-03 舊案、股價反彈 3x、訴訟仍 pending(未坐實未撤)、**KTR 已沽清(持股=0,唔會再 dump)**、無解約 | **軸部分 moot**:「KTR keeps dumping」唔再可能(已清零);「allegations confirmed」仍未定。應改寫(見 §4) |
| **gas-power 腿:AI 表後 capex 停滯**(hyperscaler 砍單) | SEI Q2 guidance 上調、簽第三家 IG、無砍單;但 = ai-capex 軸,同 [[ai-capex-macro-risk]] 聯動 | **未觸發**;呢條先係 gas-power 腿真正 kill 軸,且屬 ai-capex 共用軸 |

---

## 3. 判決:**部分中彈 + 結構判決「唔應該當一個方向 thesis」**(機制生還、現金背書中彈、macro 前提 stale/inverted、SEI 名 mis-specified)

按 §4b 校準:判決標準 = 承重 claim 面對補全後嘅事實集企唔企得住。逐子命題:

- **(i) 「gas→AI-power 需求真」——機制生還,現金合約背書中彈。** Homer City 4.4 GW 係真.dated
  工業訂單(turbine 交付中、power 2027),機制屬實;但 **EQT deferred revenue ≈ 零、KMI 零、
  SEI 僅 $76M**,「多年鎖單 = 現金地板」冇任何 balance-sheet 印證——**披露 backlog ≠ 入帳緩衝,
  pilot 嗰把刀第三度斬中**。且呢條需求嘅耐久 driver 係 **ai-capex 軸**(themes.yaml 自己 meta-tag),
  唔係 oil-gas 商品結構。
- **(ii) 「EQT 最乾淨平價表達」——大致生還,但 upside 被兩件一手事實削。** cheap(pe 10)+ 紀律
  (net debt $7.8B→$5.7B)屬實、係四隻最乾淨;但 (a) **重度對沖(Q1 衍生淨虧 $238M、付 $304M)
  封住 gas 急升上行**;(b) Homer City upside 未入帳。「最乾淨」✅,「最平價 + 直接搏高 gas」需打折。
- **(iii) 「應唔應該係一個 thesis」——結構判決:唔應該(補強 wiki 自認)。** 剝走 (a) 已 stale/inverted
  嘅油-macro 方向、(b) 兩腿矛盾依賴嘅戰爭溢價、(c) SEI(cluster 本屬 ai-power-grid),剩返嘅
  「oil-gas-energy」方向內容 = **一個中性油-β 籃(#116 neutral)+ 一隻靠 ai-capex 嘅平價 gas 名(EQT)**。
  唔清 B 型 supercycle(供給受限 + 定價權 + 催化)嘅門檻——油側係 price-taker β,gas 側係 ai-capex 借殼。
- 附:**兩腿喺同一場戰爭嘅宏觀前提上自相矛盾**——#058(5/11)靠「能源新秩序 / 荷莫茲 / 卡達 LNG
  force majeure / gas 結構高 / 3–5 年修復」,而同一發行商 #116(6/17,一個月後)記錄嗰個戰爭溢價
  **unwind**($100→$78、super-glut)。gas-power 腿嘅宏觀 tailwind 早被 theme 自己嘅油腿否定;
  今日戰事再熱又 flip 返轉頭——證明兩腿唔止方向唔同,係同一 driver 上互相打架。

**Rubric 建議(§4a 掛鈎;§4c:red-team 唔准酌情郁 confidence 數字,只入三通道):**
- **moat 格:維持 1/2。** 油無定價權(price-taker)+ gas 樽頸屬 BTM/ai-power 而唔係油氣本身——
  一手事實冇改變呢個判斷(2 分「一手證據顯示供給結構性受限 + 可交易名直接持咽喉」明顯唔成立;
  0 分「冇樽頸」又太重,gas-power 機制係真)。維持 1。
- **capital 格:維持 1/2。** EQT/KMI/油商資本紀律佳(EQT 去槓桿一手證實),但供給頂訊號在體制外
  (OPEC+/UAE);SEI 成長 capex 靠債(net debt 4x + $1.3B notes)——混合,維持 1。
- **valuation 格:維持 1/2。** EQT pe 10 便宜(生還);油商高 PE = 谷底盈利兩義;SEI pe 97 極端。
  機械讀數,本協議不覆核方向。
- **growth 格:維持 1/2。** 油需求衰退 + gas-power 新 TAM(Homer City additive 屬真)= 淨分裂;
  gas-growth 半句生還但屬 ai-capex 腿。維持 1。
- → subscore 4/8 不變。**紀律結論:red-team 冇搵到令 subscore 移動嘅硬事實**(承重機制生還),
  殺傷力全部落喺**通道 2/3 + kill_metrics 時效 + wiki 措辭**,唔喺 confidence 數字。

### 三通道分流(§4c)

- **通道 1(subscore):不變。** 4/8;承重 gas→power 機制生還,無格降。
- **通道 2(single-source cap,binary):維持受 cap 綁,confidence = 公式輸出。**
  theme `sources:` 只有 `gooptions-trend-core`(單源)→ single-source cap 0.30 適用。
  Homer City / EQT 財數係 Tier-1,但**掂嘅係「已 priced / 市場已知」嘅周邊**(合約存在、EQT 便宜、
  去槓桿),**唔係承重嘅 magnitude 腿**(gas-power 多年結構需求 + SEI $1B EBITDA)。
  照 §4c **分岔規則:唔脫 cap**。公式:(1+1+1+1)/8 = 0.50 × penalty(50% bull crowding / late)
  → 現值 **0.25 維持**(< cap 0.30,cap 不綁)。**red-team 唔郁數字。**
- **通道 3(magnitude 加成,sizing 層):建議標 SEI `magnitude_unconfirmed`。**
  SEI「$1B EBITDA 中期框架 / 3.1 GW→結構主導」係 magnitude 腿,當下 run-rate $340–370M、
  $1B 係 ~2028 stretch、且靠債建、客戶集中未解——**未證**。建議 SEI node 標 `magnitude_unconfirmed:
  true`,sizing v2 對 SEI 收起 magnitude 加成(回落 confidence-only 基準注碼)。
  (註:oil-gas-energy 現為 flat theme、未有 per-node schema;此為推廣時嘅建議。)

---

## 4. 建議(不執行;郁數 / 改檔留返日間 confidence 迴路 + 用戶過目)

- **confidence:0.25 維持**(公式輸出,§4c 唔准酌情;thin + heterogeneous + 50% bull penalty
  已預先壓咗)。red-team 淨效果 = **時效修正 + 措辭修正 + magnitude 收注**,唔係數字下修。
- **⚠️ kill_metrics 時效(最急):** 記錄 `brent_upper_trigger current:78 / as-of 2026-07-08`
  已 stale——Brent 實際重上 ~$85 逼近 $90,MOU 已崩、荷莫茲 7/14 復封。**theme 行緊近自己嘅
  bullish kill 一個星期而 metric 未捉到**。建議更新 current/as-of,並注意:一旦收復 $90,
  觸發嘅係「油腿需**向上**改寫成 bullish」,唔係下架(WATCH 本身唔死,係方向 lean stale)。
- **wiki 措辭應改(留日間):**
  (1)「Brent crashed 100→78 / near-term oversupply/bearish」加註「6/17 快照;7/8 MOU 崩、7/14
     荷莫茲復封、Brent 重上 ~$85——方向已 flip,near-term 框架 stale」;
  (2)「gas structurally high」→「gas 結構性**溫和偏firm**(Henry Hub ~$3.3、EIA 上修 2026 $3.67);
     方向受支持、絕對高位敘事係戰爭溢價,唔應以 gas 高位加碼」;
  (3) Homer City 標「披露式 gas-supply agreement-in-principle backlog,**唔係入帳合約負債**
     (EQT deferred revenue ≈ 零);pilot MU / photonics 同型」;
  (4) SEI 治理二元 mis-dated 修正:「Morpheus = **2025-03 舊案**、股價反彈 3x、訴訟仍 pending
     (未坐實未撤)、**KTR 已沽清(持股=0)**——binary 冇爆成股災,但被告 insider 全身而退 =
     治理質素黃旗;kill 軸『KTR keeps dumping』已 moot(清零),改為『訴訟坐實 / SEC 執法 /
     大長約解約』」;
  (5) 記 SEI「$1B EBITDA = ~2028 full-deployment stretch,當下 run-rate $340–370M、靠債建
     (net debt 4x 至 $1.25B + $1.3B notes)、客戶集中未解」= magnitude 腿未證。
- **結構建議(留用戶決策):** 本 red-team 補強 note 自認嘅「唔係一個 thesis」——建議正式將
  gas-power 腿(SEI)歸位去 [[ai-power-grid]](#049 frontmatter 本身就係 `cluster: ai-power-grid`),
  `oil-gas-energy` 收窄成「油-macro WATCH(neutral β)+ EQT 單名(cheap gas + AI-power optionality)」;
  對齊 themes.yaml meta 自己標嘅「energy-macro borderline causal-test、weaker than ai-capex clean pass」。
- **sources cap 註記:** 本次 Tier-1(Homer City / EQT-KMI-SEI 財數 / hedge book)掂嘅係**已-priced
  周邊**(合約存在、EQT 便宜去槓桿、SEI 有細額預付),**唔掂承重 magnitude 腿**(多年結構需求現金背書 /
  SEI $1B),照 §4a/§4c 定義**唔足以**當獨立第二源解 single-source cap。

---

## 5. Meta-review(一句)

呢次 red-team 最有價值嘅三件:(1)**mandated balance-sheet 檢查令 pilot 嗰把「披露 backlog ≠
入帳緩衝」嘅刀第三度斬中**(EQT deferred≈0 / KMI 零 / SEI 僅 $76M vs $1B 框架)——應正式升格做
INGEST 常設一問;(2)**action-4「當下狀態驗證」實戰命中**——theme 喺 kill_metrics 眼皮底行緊近
自己嘅 bullish kill 一個星期(Brent 78 記錄 vs 實際 85、MOU 已崩),證明 stale kill_metric 係真.
盲點,唔淨係流程細節;(3)**mis-dated 治理二元**——wiki 當 2026 live binary 嘅 Morpheus 其實係
2025-03 舊案、被告 insider 已清倉全走,「治理二元」由『會唔會爆』變成『已半解決但留黃旗』,
kill 軸要重寫。承重 gas→power 機制本身生還,但佢係 ai-capex 腿借殼,唔係 oil-gas supercycle。
