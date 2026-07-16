# Level-2 Red-Team：euv-lithography-monopoly（ASML 全球唯一 EUV/High-NA 微影供應商）

- 日期：2026-07-16
- 協議：thesis/DESIGN.md §4b（FALSIFY 升級：INGEST 係審判）+ §4c（red-team 判決三通道標準化）
- 角色：辯方 red-team。**職責 = 事實補全（搵敘事冇展示嘅重大事實），唔係反對表演。**
  每條反方必須錨喺可引用一手事實/數據；砌唔到錨定事實 = 標「敘事風險」，唔算 finding、唔壓分。
- Pilot 教訓已納入：反面狩獵只收一手（數據/日期/公告/法律先例）；強制回答
  「Tier-1 佐證掂嘅係承重 claim 定周邊事實？」
- **本單重點動作 = balance-sheet 檢查**：ASML 商業模式收客戶大額訂金，可能係 GEV 型現金背書
  （客戶真金預付 → 脫 single-source cap 嘅正面先例，前六單 GEV 係第一個）。認真驗咗，結論見 §3。
- 約束：只新增本檔，冇改 themes.yaml / wiki / 任何現有檔。

---

## 1. 控方主張摘要

ASML 係全球唯一 EUV / High-NA 微影設備供應商、零替代品；16 年橫跨 4 個景氣週期，CEO/CFO 第一人稱
反覆講「we are always constraining the business」「12-24 個月 lead time」「客戶 sold out」；AI 驅動先進
製程 capex 拉動需求（verdict `real-monopoly-but-most-priced-in`，confidence **0.22**、cycle **late**、
source 只有一條 → **single-source cap 適用**）。

承重 claim 拆兩截逐個審：
- **(A) 供給壟斷/樽頸半截**：全球唯一 EUV 供應商、零替代、多年 sold-out backlog 係**真**。（結構/工程事實）
- **(B) 買入時機半截**：ttm_pe 98 分位、全市場最人盡皆知 → 「未被發現」溢價完全不存在（priced-in）。

> 關鍵：本 thesis 嘅 verdict 已經係「monopoly 真、但已 priced-in」。red-team 要驗嘅唔係「monopoly 係咪真」
> （控方自己都認貴），而係:(1) 現金背書可唔可以令 (A) 半截脫 single-source cap;(2) 脫咗 cap 有冇實際影響。

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道（Tier-1，最鋒利）——同 photonics「零一手」相反，ASML 一手極厚**

- **corpus 有 29 篇 ASML 一手法說逐字稿（2019-2026，橫跨 4 週期）。** `corpus.py ticker ASML` 返 30 篇，
  當中 29 篇係 defeatbeta 一手 earnings-call transcript（docs_fts_en）——**承重 claim 嘅一手渠道覆蓋 = 厚**，
  唔係 photonics 嗰種「24 篇全係 Tier-2 轉述」。
- **balance-sheet 檢查（重點；defeatbeta quarterly_balance_sheet，17 季至 2026-06-30）——GEV 形態複製，
  唔係 memory/photonics 形態：**
  - ASML 表上有 **Current Deferred Revenue + Non-Current Deferred Revenue 兩行實數**（唔係 memory 嗰種
    「RPO 淨喺附註、balance sheet 零現形」，亦唔係 photonics 嗰種「deferred revenue 細到可忽略」）。
  - **Current Deferred Revenue（年結點）**：2022-12 **$12.48B** → 2023-12 **$11.44B**（-8%）
    → 2024-12 **$12.57B** → 2025-12 **$16.01B**（+27% YoY）。Non-Current 最新 2026-06 **$3.57B**。
  - **合計合約負債 2025-12 ≈ $19.37B，佔 FY2025 營收 $32.7B 嘅 59.3%**（Current 一項已佔 49%）。
    對照 GEV：deferred revenue $31.8B ≈ 年收入 80%。**ASML 介乎 GEV 同「近零」之間、明確落喺現金背書一側。**
  - **一手歸因（ASML 官方財報用語，web 一手核實）**：down payments 定義 = 「客戶就**未來期間出貨嘅系統**
    預付嘅現金」；**2025 年淨合約負債（€16.0B→€17.9B→€18.9B）嘅邊際增長，ASML 明言
    "mainly driven by an increase in down payments for goods and services which will be delivered in
    the future"**——增長主力係**未來系統嘅客戶預付訂金**，唔係服務遞延。
  - **transcript 一手交叉印證（呢個係關鍵：現金背書 = 訂單驅動，唔係服務時點）**：CFO Dassen 2024-01-24
    親口「record level of EUV orders and the associated **partial down payments** that are related to that…
    Down payments were helpful」；2024-10-16「less order intake and therefore **less down payments**」；
    2024-04-17「negative free cash flow, primarily driven by **lower down payments**」。**即訂金隨訂單升跌**——
    2023-24 訂單真空期，Current Deferred Revenue 就跌咗 8%（$12.48B→$11.44B）；2025 AI 訂單回潮就彈 +27%。
    **呢個係前瞻訂單現金訊號嘅簽名（隨 order intake 波動），唔係已出貨業務嘅平滑服務遞延。**
- **必答（Tier-1 佐證掂承重定周邊）**：**掂承重 claim (A) 供給/backlog 半截，唔係周邊。** 兩條獨立 Tier-1
  各自擊中承重:(1) 客戶就**未交付** EUV 系統落現金訂金 → costly signal，直接證「多年 backlog = 真前瞻需求」;
  (2) 16 年第一人稱約束語言（transcript）直接講出樽頸/壟斷本身。**pe/capex 先係周邊——本次擊中嘅係供給半截。**
  **呢個係 memory pilot 嘅鏡像**：嗰次 balance sheet **證偽** RPO 入表（承重落空 → 應受 cap）；今次
  balance sheet **證實** ASML 客戶預付（承重補強）。
- **Insider**：ASML 係外國發行人（報 20-F），Section 16 豁免 → **無 Form 4 insider 數據，渠道結構性 N/A**
  （唔係 photonics 嗰種「零 P-buyer」弱陰性，係根本冇呢個渠道；中性、唔加唔減）。

**(b) 外部一手（WebSearch，篩走意見文）**

- **Backlog / order book**：2025 年末 **backlog ~€38.8B**（Q4 2025 net bookings €13.2B，其中 EUV €7.4B）。
  **ASML 由 Q1 2026 起停止揭露季度 net bookings**（改年度 backlog 揭露）→ 前瞻能見度嘅硬數變粗（見動作 4）。
  Q2 2026（2026-07-15）：淨銷售 €9.3B、淨利 €2.9B、毛利 54%；FY2026 guidance 上調至 **€43–45B**；
  CEO Fouquet「order intake remained extremely strong in the first half」。（ASML 6-K / GlobeNewswire）
- **中國政策逆風（一手，已 guide、已進行中）**：中國佔系統銷售 **2024 ~41% → 2025 33% → 2026 guide ~20%**
  （CFO 明講；季度一度 36%→19%）。DUV 2025 全年 €12B（-6% YoY），主因中國囤貨潮退。**MATCH Act 仍係提案
  （proposed，未立法）**，若通過會加禁 DUV immersion 兼禁維修在華裝機。（SCMP / CNBC 2026-04-15、07-15）
- **High-NA 客戶採用（分化，非集體滑坡）**：**Intel 2026-07-15 成為全球第一家用 High-NA EUV 量產出貨
  高量邏輯（14A）**；Samsung 已收 EXE:5200B 導入 SF2/HBM4；**TSMC 公開表明初代 A14 跳過 High-NA**
  （用標準 EUV multi-patterning 延壽，分析師估 ~2029 先導入 = 意見非一手）。→ **有客戶分化、無集體推遲/取消**。
- **DUV 中國需求**：一手證實因囤貨潮退下滑，但**已被管理層 guide、且被非中國（先進邏輯/HBM）需求部分抵銷**
  （2027 DUV immersion 產能仍 +30%）→ 下滑真，全線崩盤假。

**(c) 歷史先例（2018-19 記憶體下行——ASML 自己嘅週期簽名）**

- **淨銷售**：Q4 2018 €3,143M → **Q1 2019 €2,229M（QoQ -29%）** → Q3 恢復增長 → Q4 2019 €4,036M。
  **Net bookings**：Q4 2018 €1,587M → Q1 2019 €1,399M（谷底）→ **Q3 2019 €5,111M（V 彈）**。
  復原 ~2 季（logic 客戶 leading-edge ramp 承接 memory 空檔）。（ASML 官方季度 press release）
- **教訓**：**ASML 唔係非週期股——2019 淨銷售單季 -29%。** 壟斷令佢**捱得快、跌完彈返**（份額零流失、定價權在），
  但唔令需求**唔跌**。「sold out / backlog」嘅**幅度係週期性**，「唯一供應商」嘅**結構係非週期性**——兩者要分開睇。

### 動作 2 — Steelman 反方（非 wiki/文章自供，事實錨齊）

**「現金背書 backlog 係週期性抵押品，唔係結構性地板」**：
1. **backlog 現金背書本身會隨週期變薄**：Current Deferred Revenue 喺 2022→2023 訂單真空期跌咗 8%
   （$12.48B→$11.44B）,CFO 親證同期「lower down payments」拖累 FCF——真慌時客戶預付會縮,地板喺你最想要嗰陣蒸發;
2. **ASML 淨銷售 2019 單季 -29%**(一手歷史),證明「sold out」狀態可以逆轉;
3. **一整條需求腿正被政策結構性移除**:中國由 41%→20%(-€數十億)係已 guide、進行中,唔係尾部風險;
4. 先例分工:memory pilot 已證「backlog = 地板」類 claim 要睇入唔入表——ASML 呢次**入到表**(脫穎而出),
   但入到表嘅嗰舊錢**本身係週期性**,唔等於「多年不變嘅地板」。

呢條 steelman 唔需要「AI 需求係假」或「壟斷係假」——**就算 monopoly 全真、AI capex 全真,backlog 嘅
幅度依然係週期敏感,而 (B) 半截(貴)先係 thesis 真正嘅約束**。

### 動作 3 — 平庸解釋測試

**悶故事:「AI capex 週期高峰」可以解釋幾多 sold-out,唔使「結構性壟斷多年」?**
- **解釋到(幅度半截)**:當下 backlog 爆滿、bookings 創紀錄、提價、毛利 54%——全部係任何設備週期頂嘅
  標準現象。2019 個逆例證實同一機制可以 -29% 咁反轉。**「sold out for 2026」呢個狀態,悶故事(AI capex peak
  + 週期高點)解釋得晒,唔使更強嘅「結構多年樽頸」假設。**
- **解釋唔到(壟斷半截,結構故事嘅額外證據)**:(1) 零可行競爭者——SMEE EUV 仍實驗室、零晶片、實際 ~2030;
  Canon nanoimprint ≠ High-NA EUV(defect/良率未達 leading-edge);Nikon S6xx 排 FY2028 且設計成相容 ASML
  光罩非取代。(2) 無代工結構(產能不可共享)。(3) 份額零流失 + 定價權(2019 跌完彈返、GM 一路 52-54%)。
  ——**呢啲係工程/結構事實,週期解釋唔到。**
- **淨結論**:平庸解釋**對 (A) 供給半截嘅「幅度」成立、對「壟斷結構」唔成立**——**同 thesis 現行判斷完全一致**
  (wiki 自己講「耐久護 downside 不加 forward upside」「late+98 分位釘死 2-3x band 頂 = MU-today 教材」)。
  **平庸解釋測試喺呢單係驗證咗現行 verdict,唔係推翻。**

### 動作 4 — kill 距離（kill_condition 逐腳）

| kill 腳 | 當下一手事實 | 距離判定 |
|---|---|---|
| **① 可行 EUV/High-NA 競爭者出現**（SMEE 突破 / Canon-Nikon 重返 High-NA） | SMEE 仍實驗室原型、零晶片、目標 2028 實際 ~2030；Canon 交 nanoimprint（≠EUV）；Nikon S6xx FY2028 且相容非取代 | **未觸發、遠**（結構護城河最硬嗰腳，無收窄跡象） |
| **② AI 先進製程 capex 停滯/逆轉**（TSMC/三星/Intel guidance 回落） | **反向遠離**：TSMC 2026 capex $52–56B（+32%）、Samsung 半導體 capex+R&D >₩110T（+128%，史上最大）；唯 Intel 降。**但上游二階燈已轉黃**：ai-capex-macro-risk hub 五盞燈——四大 FCF 年減（AMZN −97%/GOOGL −12%/MSFT −12%/META −8%）、OpenAI 承諾 $600B vs run-rate $20–30B 缺口 | **未觸發、level 遠**；但**係本 thesis 唯一真.活軸**——雲端 capex 打嗝要先傳到晶圓廠 guidance 先輪到 ASML（wiki 2026-07-12 已記傳導滯後）。二階領先燈黃 = 中距離、要逐季睇 hub |
| **③ lead time 縮返 <6 個月**（12-24 月 → <6） | lead time 仍 12–24 月，CEO 2026-04 反而警告「persistent supply constraints」；backlog €38.8B、2027 產能仍 +30% | **未觸發、遠**（方向仍供不應求） |
| **附:中國政策 Type C（wiki 已記，非正式 kill 腳）** | 41%→20% 已 guide、進行中；MATCH Act 仍 proposed | **收入逆風真、已 priced/已 guide**；係已知的需求組成風險,唔掂壟斷結構 |

**三腳 kill 當下全部未觸發;唯一活軸係 ② 嘅上游二階燈(hyperscaler FCF / 承諾缺口),透過 hub 監察。**

---

## 3. 判決：**生還，且承重 (A) 半截被雙 Tier-1 補強；(B) 半截（真正約束）未被觸及**

按 §4b 校準（判決標準 = 承重 claim 面對補全後嘅事實集企唔企得住）:

- **(A) 供給壟斷/樽頸半截——生還，且被補強。** 兩條獨立 Tier-1 各自擊中承重:(1) balance-sheet 現金背書
  （合約負債 $19.4B ≈ 59% 營收、2025 增長由未來系統客戶預付訂金驅動、隨 order intake 升跌 = GEV 型簽名）;
  (2) 16 年第一人稱約束語言 transcript。kill 三腳全遠。**呢半截係全 3 批單股最硬嘅護城河,本次狩獵冇搵到
  任何一手反面。**
- **(B) 買入時機半截——未被觸及,亦係 thesis 真正約束。** ttm_pe 98 分位 = 估值 KPI 0 分（rubric「≥90 → 0」）;
  late-cycle + most-consensus crowding penalty。**red-team 冇任何事實可以令佢變平——ASML 就係貴。**

### 係咪脫 single-source cap?——**技術上脫得，但脫咗係 null-op（本單最鋒利一刀）**

- **脫得**:按 §4a 定義,「系統自己嘅 Tier-1 渠道獨立擊中**承重** claim」即脫 cap。ASML 有**兩條**符合:
  現金背書 down payments（財務一手）+ 約束語言 transcript（逐字稿一手,§4a 明列嘅正例）。**真.現金背書,
  合資格 = GEV 之後第二個正面先例。**
- **但脫咗零數字影響**:**ASML 根本唔係俾 single-source cap 綁住——confidence 0.22（公式重算 ~0.25）本身
  就 < 0.30 cap。** 綁死佢嘅係**估值(98 分位 = 0 分)+ crowding penalty**,唔係來源數。
  - 對照 GEV:GEV raw 0.33 **> cap**,而且相對平 → 脫 cap **有效**拉返 0.33。
  - ASML raw ~0.25 **< cap**,俾估值封頂 → 脫 cap **inert**。
- **淨效果**:現金背書令 verdict `real-monopoly-but-most-priced-in` 嘅「real-monopoly」半截由「一致但單源」
  升級為「雙 Tier-1 獨立追認」;但「most-priced-in」半截（真正壓 confidence 嗰個）**紋風不動**。
  **信心數字唔郁,係因為佢一路都俾對嘅理由(貴)綁住,唔係俾錯嘅理由(來源數)綁住。**

### §4c 三通道分流（標準化,唔酌情）

| 通道 | ASML 判定 |
|---|---|
| **通道 1（subscore，入公式）** | moat/樽頸 **2/2**（承重經 Level-2 生還兼補強,§4a「2 分前提」滿足）；估值 **0**（98 分位）；資本配置 ~1.5（GM 52.8%/OpM 34.6%/高 ROIC,未深研）；成長耐久 ~1.5（additive 真兌現,但幅度週期性）。Σ=5.0/8 × penalty(late,crowding≥90 ~0.40) **≈ 0.25** |
| **通道 2（cap 資格，binary）** | **脫 single-source cap**（雙 Tier-1 獨立擊中承重）——但 raw < cap,**脫咗不改數**。屬「補強」但 cap 非約束 |
| **通道 3（magnitude 加成，sizing 層）** | **不變、無 `magnitude_unconfirmed`**。ASML 唔似 tpu/space 有「未證 magnitude 腿」——壟斷係已證嘅全部故事;2-3x band 頂已由 node schema 因「late+98 分位」正確封住（貴 ≠ 未證）。 |

**§4c 框架補充（本單新觀察,值得記入標準化）**:「補強 → 脫 cap」呢個通道 2 動作,**只有喺 raw > cap 先有效**。
對一個**估值封頂（raw < cap）**嘅 theme,「脫 cap」係機械上合格但數值上 null-op。標準化框架應明記:
**通道 2 嘅殺傷力/加成力都受「raw 相對 cap 邊一側」閘住**——ASML 係「合格脫 cap 但無感」嘅乾淨案例
（對照 GEV「脫 cap 且有感」、memory「唔脫 cap 應被壓」、photonics「唔夠格脫 cap」——四種形態齊集）。

---

## 4. 建議（不執行；郁數留返日間 confidence 迴路）

- **confidence:0.22 → 公式重算 ~0.25（微升,非因脫 cap,係 moat 2/2 + 現行 0.22 略偏保守）。** 移動細,
  留待日間遷移逐個覆核;**唔好將「脫 cap」誤讀成升 confidence 嘅理由**——脫 cap 喺呢單零數值後果。
- **verdict:維持 `real-monopoly-but-most-priced-in`**（判斷準確,red-team 驗證咗而非推翻）。wiki 措辭建議補:
  (1) 登記 balance-sheet 現金背書（合約負債 $19.4B ≈ 59% 營收、2025 增長由客戶預付驅動、CFO transcript 印證
  訂金隨 order intake 升跌）作承重 (A) 半截嘅**第二條 Tier-1 佐證**;
  (2) 記 2018-19 週期簽名（淨銷售 -29% QoQ、~2 季 V 彈)作「壟斷令捱得快、但需求仍週期」嘅錨;
  (3) 記 ASML 由 Q1 2026 停揭季度 bookings → 前瞻硬數變粗,能見度改睇 backlog 年度數 + hub 二階燈;
  (4) 記 High-NA 客戶分化（Intel 先行量產 14A / TSMC 初代 A14 跳過）——結構壟斷不變,但採用曲線分岔。
- **sources 登記建議**:現行 `sources:` 只有 `transcript-discovery-radar`（tier **3**）——**呢個 tier 標低咗**:
  底層係 defeatbeta 一手 earnings-call transcript（§5 原料分級明列 transcript = **Tier 1**）。建議:
  (a) 將 transcript 源正名為 Tier-1;(b) **新增第二條 Tier-1**:`asml-balance-sheet-downpayments`,
  `corroborates: 供給樽頸-多年 backlog 現金背書`。兩條齊 → 正式脫 single-source cap（雖數值 null-op,
  但令 `sources:` 誠實反映證據厚度,亦令 lint 嘅 cap 狀態正確）。
- **kill_condition 建議**:三腳保留;第 ② 腳「AI capex 停滯/逆轉」嘅具體監察應明接 ai-capex-macro-risk hub
  五盞燈（四大 FCF / 承諾-run-rate 缺口),而唔係等 TSMC/三星自己 guidance 落實——傳導滯後一層,燈黃要提早重估。
  中國 Type C（41%→20%、MATCH Act）建議由 note 升做正式的「近期收入風險」腳注（已進行中、已 guide,非尾部）。

---

## 5. 未解 / 風險（誠實報告）

- **唯一追溯唔到嘅硬數**:合約負債 note 內 **down payments vs deferred-service-revenue 嘅確切金額拆分表**
  （SEC 20-F HTML 回 403、官方 PDF 二進位無法一手解析,accession 000162828026011378 待直接拉表）。
  **現金背書結論靠 ASML 一手歸因文字（「2025 增長主要由未來系統客戶預付訂金驅動」)+ 一手 balance-sheet
  趨勢（隨 order intake 升跌)+ CFO transcript 印證,係一手文字 + 一手趨勢,但唔係一手拆分數字表。**
  方向穩,佔比精度待補;若要把「大部分係現金訂金」由「傾向」升做「硬結論」,需拉該 note 表格。
- **crowding penalty 具體檔位**:本檔用 ≥90（most-consensus）估 ~0.40 late,實際 crowding composite pctile
  應由 crowding_composite.py 讀返;若實際落 80-90 檔,penalty 0.45、raw ~0.28（仍 < cap,結論不變）。
- **週期定時**:kill ② 上游二階燈（hyperscaler FCF 年減、承諾缺口）已黃,但 level 未跌、ASML 直接客戶
  capex 仍 +32%/+128%。呢個係「level 遠、rate-of-change 拐點需逐季睇」嘅典型 late-cycle 張力,非當下觸發。
</content>
