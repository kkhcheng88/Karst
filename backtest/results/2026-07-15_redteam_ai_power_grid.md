# Level-2 Red-Team：ai-power-grid(AI 電力 / 供電鏈)

- 日期：2026-07-15
- 協議：thesis/DESIGN.md §4b（FALSIFY 升級：INGEST 係審判，唔係歸檔）+ §4b「事實補全，唔係反對表演」校準
- 角色：辯方 red-team。**職責 = 事實補全（搵敘事冇展示嘅重大事實），唔係反對表演。**
  每條反方必須錨喺可引用一手事實/數據/日期/先例；砌唔到錨定事實 = 標「敘事風險」，唔算 finding，唔壓分。
- 約束：只新增本檔，冇改 themes.yaml / wiki / 任何現有檔。
- **必答（pilot 教訓強制第一問）：Tier-1 佐證掂嘅係承重 claim 定周邊事實？**
  → 答喺判決節：今次系統渠道（GEV balance sheet）**直接掂承重 claim 嘅供給樽頸半截**，係 memory pilot 嘅**鏡像**
  （嗰次 balance sheet 證偽 RPO，今次證實 GEV 現金背書 backlog）。

---

## 1. 控方主張摘要

AI 電力 / 供電鏈係 B 型主題（渦輪 → 電網 → 資料中心配電 → 800V 機櫃 → 功率半導體 → POL）。
**承重 claim =「AI datacenter 電力需求結構性超過供給（渦輪多年交期、電網設備、功率半導體），
hyperscaler capex $1T→$1.7T 路徑成立，呢個係多年期樽頸而唔係一次性需求脈衝。」**
verdict `real-demand-but-priced-ahead-of-ramp`，confidence 0.33、cycle late。

承重 claim 可拆兩截（判決逐截處理）：
- **(A) 供給側樽頸真且多年**（渦輪 sold-out 到 2030、SMR/燃氣 response 慢、POL 雙寡佔、800V 物理逼出）。
- **(B) 需求錨耐久、AI 特定、$1T→$1.7T 路徑成立、唔係一次性脈衝。**

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道（Tier-1，最鋒利）**

- **GEV balance sheet：多年訂單簿係「現金背書」，而且喺表上快速增長 —— 直接佐證承重 claim (A)。**
  （defeatbeta `quarterly_balance_sheet`，2026-07-15 拉）
  - GEV **Current Deferred Revenue（合約負債 / 客戶預付）**：
    2025-03 **$18.7B** → 2025-06 $19.6B → 2025-09 $20.2B → 2025-12 $25.8B → **2026-03 $31.8B**（+70% YoY）。
  - 對照收入：GEV TTM 收入 ~$39.4B → **deferred revenue ≈ 年收入 80%**，且四季連升。
  - **事實補全（memory 嘅鏡像）**：memory pilot 揭「RPO $100B 唔喺 balance sheet、入帳遞延收入僅 $10.2 億」，
    承重 claim 落空。**今次相反**：GEV 嘅多年 backlog **真係以客戶現金預付形式坐落表上**（$31.8B）——
    客戶落訂金鎖產能 = costly signal = 需求真、樽頸真。呢個係 **Tier-1 渠道獨立擊中承重 claim 嘅供給半截**，
    唔係周邊事實（pe / capex 先係周邊）。→ 對 §4a single-source cap 有直接後果（見判決）。

- **GEV capex：由低谷 ~4x 回升 —— 供給開始回應（週期趨晚一致）。**（defeatbeta `quarterly_cash_flow`）
  - 季度 capex：2025-03 $173M → $247M → $671M → $397M（TTM $1.488B）。wiki 記「capex lumpy 0.17→0.67、
    無廣泛供給回應」對 GEV **開始過時**：GEV 明顯喺加建產能（配合 backlog），係「late-cycle 供給回應」嘅早訊號，
    支持 verdict 嘅 `priced-ahead`/`late` 定性，但同時證明供給側**唔係死鎖**（會 2–3 年後放量）。

- **ETN：負債跳升係收購債，唔係有機預付 —— ETN 唔攞到 GEV 同款佐證。**
  - ETN Total Liabilities 2025-12 $21.8B → 2026-03 **$35.3B**（+$13.5B 單季跳），對應 Boyd Thermal ~$9.5B 液冷收購融資
    （Non Current Deferred Liabilities 265M→1,605M、長債擴張），**唔見 GEV 式 deferred-revenue 有機增長**。
    → ETN 99th 分位估值嘅「priced-in」判斷企得穩，冇被一手數據翻案。

- **constraint-language 掃描：ai-power-grid density 中游、無趨勢 —— 第二渠道對「樽頸更緊」冇加強。**
  （`thesis/constraint_scan.py`，2026-07-15_constraint_scan_production.md）
  - ai-power-grid 逐季 density：2025Q1 **0.79** → Q2 0.71 → Q3 0.38 → Q4 0.77 → 2026Q1 **0.64** → Q2 **0.71**。
  - 對照長期釘死 1.00 嘅主題：gas-compression、aerospace-specialty-alloys、memory-supercycle、us-solar。
  - **事實補全**：ai-power-grid 嘅「約束語言」渠道**波動、無單調上升，2026 反而低過 2025Q1**——即整叢管理層口徑
    嘅「sold-out / lead-time / 提價」密度**冇 memory / gas-compression 咁鐵板一塊**。呼應 wiki「moat 不均、被商品段稀釋」
    嘅 1.5/2 判斷（唔支持升 2）。註：呢個係**籃子平均**，會被公用事業/氣源等商品段拉低，唔等於 GEV/MPWR 個別轉弱。

**(b) 外部一手事實（WebSearch，已避開 gooptions；篩走純意見）**

- **渦輪產能/交期：零反面事實，樽頸更緊。** GEV gas turbine backlog + slot 由 2025 年底 83GW → 2026Q1 **100GW**
  （+17GW），CEO Strazik 稱 2026 年底「sold out 到 2030」；2026H1 新單每 kW 價較 2025Q4 高 **10–20%**；三大 OEM 交期
  **5–7 年**。（Utility Dive〈GE Vernova gas turbine backlog hits 100 GW〉；Bloomberg〈gas-turbine bottlenecks〉）
  - 供給回應屬實但落地慢：三大 2026 起擴產 25–35%/年、Mitsubishi 兩年內翻倍——**但擴產後仍 oversold 到 2028**，
    支持「多年樽頸」而非推翻。（PowerMag；E&E News）
  - `敘事風險`（非 finding）：2025Q4 GEV 簽 24GW 之中 **21GW 只係 slot reservation、僅 3GW firm order**——若需求逆轉
    可取消；但**現時零取消數據**，屬結構脆弱性、唔壓分。（GEV Q1 8-K）

- **新增供給時間表：零反面事實，供給確實慢。** SMR 商業落地 2030 代初中（建照 5–8 年）；最快 OPG BWRX-300 2029、
  Holtec Palisades SMR 2030。無任何「供給提前解除」證據。（Stanford Understand Energy；Sustainable Atlas）

- **Hyperscaler capex：上修為主，但有一條逐字「見頂」訊號。** 四大 2026 合計 ~$725B（vs 2025 ~$410B，+77%），
  無一家 roll over；Evercore/BofA 估 2027 >$1T（$1.7T 路徑方向成立）。**但 Meta 管理層明言 capex 2026 見頂(peak)、
  2027 normalize**，Q1'26 後股價單日 −10%——四家中唯一畀出增速拐點指引。capex–revenue 缺口 ~$600B 且擴大。
  （Fortune/Yahoo；CNBC〈2027 capex >$1T〉；IndexBox〈Meta −10%〉；Forbes〈capex-revenue gap〉）

- **建設取消：有具體事件，但 2025 舊聞、非約束、之後被上修蓋過。** MSFT 2026-02 撤 200MW→擴至 2GW（**non-binding LOI**，
  另有 ~5GW binding 預租）；AWS 2025-04 暫停部分 colocation 洽談（稱 routine）。**搵唔到 2026 涉 firm contract 嘅取消。**
  （SemiAnalysis；CNBC）

**(c) 先例（事實錨）**

- **2000 電訊 capex 泡沫（強數字錨，但反向類比）**：鋪 >8,000 萬英里光纖，2002 年僅 **2.7% 點亮**，2005 年底仍 **85% 暗光纖**，
  頂峰 capex ~$120B、頻寬價崩 ~90%、電訊股市值蒸發 >$2 萬億、~十年消化。（Fabricated Knowledge）
  **性質**：提供「需求無限」敘事點收場嘅精確錨，**但目前 AI 電力係短缺唔係過剩，方向相反**，只可作「若供給 2–3 年後放量
  + 需求同時見頂」嘅尾景，唔可直接當現況。
- **公用事業過度外推（當下、監管者自己講）**：ERCOT 2026-04 監管官員與 PUC 一致認為 load forecast「很可能高估」
  （大負荷 interconnection 排隊有 phantom/重複計算）。（Texas Tribune）
  反向脈絡：Grid Strategies 連三年**上修**全國負荷預測（2022 估 5 年 +2.6% → 現 +4.7%），歷史係持續 upside surprise。

### 動作 2 — Steelman 反方（非文章自供、事實錨）

> **最強反面敘事（錨定一手數字）：「渦輪 backlog 唔係 AI 故事——GEV 100GW backlog 只約 20% 綁 datacenter，
> 約 80% 係傳統公用/IPP/工業（更換週期 + 一般電氣化/reshoring）。而真正 AI 特定嘅一層（電網設備 ETN、
> 配電/散熱 VRT、功率半導體 MPWR/ON）正正就係估值 90–99 分位、內部人賣、分析師目標低於現價嗰批。
> 即係:最乾淨、最現金背書嘅樽頸(渦輪)最唔 AI；最 AI 嘅名最貴。」**
>
> 支撐（全部一手）：
> 1. GEV backlog ~20% datacenter-bound（Power-Eng/Yahoo）；Electrification 分部 AI 曝險較高（Q1 有 $2.4B DC 設備單）。
> 2. GEV deferred revenue $31.8B 現金背書（動作 1a）——訂單真，但**現金背書唔區分「AI 樽頸」定「一般電力樽頸」**。
> 3. wiki 自認 quality 名（ETN 99th/ON 90th/MPWR 89th/BE 91st）估值極端 + 內部人賣 + NVTS 分析師目標 $13.59<現價 $28.51。

**非文章自供硬性條**：**「AI-attribution 缺口」反框**——把 GEV 現金背書 backlog 由「AI 電力樽頸鐵證」重新解讀成
「大部分係非 AI 電力需求」，令承重 claim 嘅 **AI-特定半截 (B)** 同**最乾淨嘅供給證據 (渦輪)** 脫鈎。wiki 全篇冇提出此反框。

### 動作 3 — 平庸解釋測試

**GEV backlog 爆滿 + deferred revenue $31.8B，可唔可以齋用「更換週期 + 一般電氣化」解釋，唔使 AI？**

**部分可以，而且對渦輪段更省。** 一手數字：GEV 100GW backlog 約 **80% 屬傳統公用/IPP/工業負荷**，僅 ~20% 明確綁 datacenter
（Power-Eng）。即係渦輪熱潮嘅大頭**唔一定需要 AI 敘事成立**——美國電網老化更換 + reshoring + 一般電氣化足以解釋。
**邊度平庸解釋唔成立**：AI-特定曝險**集中喺 Electrification / 功率半導體段**（$2.4B DC 設備單、onsemi 每櫃含量 10x
$9.5k→$115k、SiC/GaN 0→64% BOM、800V 物理逼出）——呢啲係「搶份額之上再造新需求」嘅 additive 機制，悶故事解唔到。
**結論**：平庸解釋對**渦輪段(GEV)成立**、對**器件/配電段(MPWR/ON/VRT/ETN)唔成立**。呢個**唔推翻**承重 claim，
但**收緊**咗 verdict：thesis 已講「別追 quality 名、乾淨便宜表達 = EQT/氣源」——平庸解釋測試**加強**咗呢個方向
（最乾淨嘅樽頸恰恰最唔 AI、最平；最 AI 嘅段恰恰最貴）。

### 動作 4 — kill 距離（逐軸估當下距離）

`python thesis/kill_metrics.py --report`（2026-07-15）：**ai-power-grid 冇任何可量化 kill 軸**——同 memory 一樣喺
`themes_without_kill_metrics` 名單，kill_condition 全 prose，夜班判唔到數值距離。逐條 prose 估：

| kill 軸（prose） | 當下距離估計 |
|---|---|
| ① hyperscaler/DC capex 由 $1T→$1.7T 路徑 roll over | **中—遠（level 遠、2 階導已亮）**。四大 2026 +77% YoY、賣方確認 2027 >$1T；**但 Meta 已逐字指引 2026 peak/2027 normalize**，$600B capex-revenue 缺口擴大。level 未跌，rate-of-change 拐點係最領先嘅一手 tell。 |
| ② 800V/HVDC 第 3–4 階段再延 / 48V 續 good-enough | **遠（但只能 2027 見真章）**。800V 仍物理逼出、NVIDIA 29 家聯盟、2027 次世代機櫃。屬「延遲」型風險，未觸發。 |
| ③ 渦輪三巨頭訂單確認 2026 見頂（GEV 裂縫 #086/#134）| **遠，而且反向遠離**。backlog 83→100GW、sold-out 到 2030、提價 10–20%、deferred rev +70% YoY——**與「見頂」相反**，wiki 引嘅 #086/#134 訂單裂縫被最新讀數推翻。潛在脆弱：21/24GW 係 slot reservation 非 firm。 |
| ④ Infineon 漲價循環反轉 | **遠**。Infineon 連兩漲（2026-04、2026-07），TI 亦加入。未觸發。 |
| ⑤ 中國稀土/釔出口管制進一步收緊 | **最近（LIVE）**。rare-earth-materials theme kill_metric 有 deadline 2026-11-30（138 日）；GEV 釔葉片塗層依賴係 CEO 親口確認嘅斷點。**但呢軸雙刃**：若觸發，係打擊 GEV 交付能力（供給更緊 = scarcity 對主題偏 bullish，但個別 GEV 中彈）。 |

**新識別、未入 kill_condition 嘅需求側軸**：**AI 推理能效**——Nvidia Vera Rubin（2H26）每 token 成本較 Blackwell 低 **10x**、
推理性能 5x；B200 純軟件兩個月每百萬 token $0.11→$0.02（5x）。**若單位算力電耗下降快過部署增長（Jevons 反向），會削弱
「電力需求隨 compute 線性外推」——目前未觸發（負荷預測仍連年上修），但係 kill_condition 漏咗嘅需求側一手軸。**

---

## 3. 判決

**承重 claim → 生還（Level-2 survived），並獲一條新鮮 Tier-1 獨立佐證；同時「priced-ahead」nuance 被收緊。**

逐截：

- **(A) 供給側樽頸真且多年 → 強生還，獲 Tier-1 獨立佐證。**
  兩渠道齊證：GEV deferred revenue $18.7B→$31.8B 現金背書（一手 balance sheet）、backlog 100GW sold-to-2030、提價 10–20%、
  交期 5–7 年、SMR/燃氣 response 慢、零取消。**呢截 red-team 完全打唔冧，反而補強。** 供給回應（GEV capex 4x）只係
  把 cycle 定性推向 late，唔動搖樽頸為真。
- **(B) 需求錨耐久 + AI 特定 + $1T→$1.7T 路徑成立 → 未被證偽，但出現兩條需明文追蹤嘅一手反面：**
  (1) **AI-attribution 缺口**：最乾淨、最現金背書嘅樽頸（渦輪）約 80% 非 AI（平庸解釋對渦輪段成立）；AI-特定曝險集中喺
  最貴嗰批器件/配電名。(2) **需求側 rate-of-change**：Meta 逐字指引 2026 capex peak、$600B capex-revenue 缺口、Nvidia 能效
  5–10x/代、ERCOT 監管者稱負荷預測高估。**呢啲唔推翻「路徑成立」（其餘三大仍升、負荷預測仍連年上修），但係承重 claim (B)
  嘅真 kill-axis，且部分未入 kill_condition。**

**必答（Tier-1 佐證掂承重 claim 定周邊事實）**：**掂承重 claim (A) 供給半截**——GEV 現金背書 backlog 直接證「多年樽頸 + 客戶
預付鎖產能」，唔係 pe/capex 嗰種周邊事實。呢個係 memory pilot 嘅**鏡像**（嗰次 balance sheet **證偽** RPO 入表 → 承重落空 →
應受 cap；今次 balance sheet **證實** GEV 預付 → 承重補強 → **合理脫離 single-source cap**）。

**§4a single-source cap 檢查**：themes.yaml `sources:` 只有一條（`gooptions-trend-core`，tier 2）。§4a 規定 confidence 0.33 > 0.30
須有 Tier-1 獨立擊中**承重 claim**先可脫 cap。**今次動作 1a 提供咗**：GEV balance sheet（一手）獨立追認承重 claim 嘅供給樽頸半截。
→ **ai-power-grid 合理脫離 cap，0.33 企得住**（與 memory 相反——嗰次一手驗證失敗、應被壓到 0.30）。

**對應 rubric（§4b moat/growth 掛鈎）：**
- **moat 1.5/2 → 維持 1.5（今經 Level-2 生還）。** POL 雙寡佔 + 800V 物理 + 渦輪 sold-to-2030 + GEV 現金背書 backlog 生還；
  但 constraint-density 中游無趨勢 + 商品氣/電網段稀釋 + 平庸解釋對渦輪段成立 → **唔升 2**。1.5 由「齋引用」升格為「Level-2 生還」。
- **growth 2/2 → 維持 2/2（校準:唔製造反對）。** additive 機制（onsemi 10x 含量、SiC/GaN 0→64%）**已被財報兌現**（onsemi Q1 DC +30%）、
  供給結構性慢（渦輪 5–7yr、SMR 2030+）——符合 2 分錨。能效 5–10x/代係真 WATCH item **但目前未證偽**（負荷預測仍連年上修、
  四大三家仍升）→ 現況降 growth = 對唔支持嘅事實製造反對，**唔改**。改為把能效軸寫入 kill_condition。
- 估值 0.5/2、資本配置 1/2 係機械讀數，不受 red-team 影響（ETN 一手驗證確認 99th priced-in 企得穩）。

**淨效果**：confidence **維持 0.33**，verdict `real-demand-but-priced-ahead-of-ramp` **維持**——但底層由「單一 Tier-2 源、疑觸 cap」
升級為「**Tier-1（GEV balance sheet）獨立追認供給樽頸、正式脫 cap**」，同時「priced-ahead」由籠統判斷收緊為
「**最乾淨樽頸最唔 AI/最平、最 AI 段最貴**」嘅可操作分層。red-team 冇推翻主題，而係**補強供給半截 + 收緊表達分層 + 補出漏咗嘅需求側 kill 軸**。

---

## 4. 建議（不執行）

| 欄位 | 現值 | 建議 | 理由 |
|---|---|---|---|
| sources | 1 條 tier-2 | **登記第二條 Tier-1 佐證**（GEV deferred-revenue / balance sheet，`corroborates: 供給樽頸-多年訂單簿`）| 一手獨立擊中承重 claim (A)，正式脫 single-source cap；令 0.33 有 §4a 依據 |
| confidence | 0.33 | **維持 0.33** | 脫 cap 後 base×penalty 不變；供給補強 vs 需求側新 watch 相抵 |
| moat subscore | 1.5/2 | **維持 1.5（標記 Level-2 生還）** | 承重供給半截經 Level-2 生還（§4b rubric 掛鈎），但商品段稀釋 + 平庸解釋對渦輪成立 → 唔升 2 |
| growth subscore | 2/2 | **維持 2/2** | additive 機制已財報兌現 + 供給結構慢；能效反面未證偽，降分 = 對唔支持嘅事實製造反對（§4b 校準禁止）|
| kill_condition | 全 prose、缺需求側能效軸 | **加兩條可量化軸** | (a) GEV backlog GW + sold-out 年限（trigger：QoQ 轉降 / sold-out 視窗縮入 2028 內）；(b) 四大 hyperscaler capex YoY（trigger：≥2 家確認 Meta 式 peak / YoY 轉負）。**新增需求側質性軸**：AI 每-token 電耗下降速度是否快過部署增長（Jevons 反向）|
| kill_metrics.py | 空軸 | **接返 ai-power-grid 數值 tripwire** | 現同 memory 一樣純 prose，夜班判唔到距離；至少 GEV backlog GW（現 100，sold-2030）+ capex YoY 兩軸可即接 |
| wiki 反方段 | 未有獨立反框 | **記 `red_team:` 段**：AI-attribution 缺口反框（渦輪 backlog ~80% 非 AI）+ 需求側能效軸 | §4b 硬性要求至少一條非文章自供反方 |
| wiki「無供給回應」 | GEV capex 平 | **更新**：GEV capex 由低谷 4x 回升（$173M→$671M/季）| 一手數據，late-cycle 供給回應早訊號 |

**公平記錄控方做啱嘅**：thesis 本身**唔係天真 bull**——已判 late、confidence 只 0.33、已標 quality 名 90–99 分位 priced-in、
已引內部人賣 + 分析師目標低於現價、kill 圍住 capex/800V/渦輪見頂/Infineon/稀土五軸、已明講「別追、乾淨表達 EQT」。
red-team 冇推翻一個 naive 敘事，而係用一手 balance sheet **補強咗供給樽頸半截**、用一手 attribution 數字**收緊咗表達分層**、
並**補出承重 claim (B) 漏咗嘅需求側 kill 軸（能效）**。

---

## 5. 協議 meta-review（§4b pilot 校準，一句）

**最鋒利一刀係「必答：Tier-1 掂承重 claim 定周邊事實」**——同一問令 memory 中彈（RPO 唔喺表）、令 ai-power-grid 補強
（GEV 預付喺表），證明呢條 checklist 係雙向裁判、唔係單向壓分工具；而「事實補全唔係反對表演」校準喺今次直接兌現——
最有價值嘅產出係**確認生還 + 收緊分層**，而唔係砌 downgrade（若硬降 growth 2→1.5 就係對「負荷預測仍連年上修」呢個事實製造反對）。

---

## 附：本檔用到嘅一手驗證命令（可複現）

```
python thesis/kill_metrics.py --report                        # ai-power-grid 無可量化 kill 軸（themes_without_kill_metrics）
python thesis/constraint_scan.py                              # ai-power-grid density 中游無趨勢（0.64-0.71 vs 釘死 1.00 嘅主題）
# defeatbeta GEV quarterly_balance_sheet: Current Deferred Revenue 18.7B->31.8B (+70% YoY), ~80% of TTM rev 39.4B
# defeatbeta GEV quarterly_cash_flow: CapEx 173M->671M/qtr (4x off trough), TTM 1.488B
# defeatbeta ETN quarterly_balance_sheet: Total Liab 21.8B->35.3B = Boyd Thermal 收購債, 非有機 deferred-rev
# WebSearch 一手: GEV backlog 83->100GW sold-2030 (+提價10-20%); Meta capex 2026 peak/2027 normalize;
#   GEV backlog ~20% datacenter-bound (Power-Eng); Nvidia Vera Rubin 10x lower cost/token; ERCOT load forecast 高估 (2026-04)
```
