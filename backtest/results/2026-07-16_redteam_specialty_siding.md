# Level-2 Red-Team：specialty-siding-pricing-power（特種護牆板定價權 / LPX）

- 日期：2026-07-16
- 協議：thesis/DESIGN.md §4b（FALSIFY 升級：INGEST 係審判，唔係歸檔）+ §4c（red-team 判決三通道分流）
- 角色：辯方 red-team。**職責 = 事實補全（搵敘事冇展示嘅重大事實），唔係反對表演。**
  每條反方必須錨喺可引用事實/數據；砌唔到錨定事實 = 標「敘事風險」，唔算 finding。
- Pilot 教訓已納入：反面狩獵只收一手（數據/日期/公告/政府數據）；強制回答
  「Tier-1 佐證掂嘅係承重 claim 定周邊事實？」；必做 balance-sheet 檢查。
- 約束：只新增本檔，冇改 themes.yaml / wiki / 任何現有檔。

---

## 1. 控方主張摘要

承重 claim = **「LPX 嘅 SmartSide/ExpertFinish engineered-wood siding 有結構性定價權（近 9 季
7 季講 pricing power，2024 起），由 vinyl→engineered-wood 轉換驅動；2026-05 有真.managed-allocation
緊缺事件佐證。」**（verdict `real-segment-mix-shift-but-diluted-and-priced`，confidence 0.20，
cycle mid，全批最擠 crowding 97.2、≥90 帶。）

**Gatekeeper 已判（backtest/results/2026-07-15_subscore_backfill_draft.md §2.5 + §6）**:呢個定價權
只覆蓋 LPX 一個 segment，commodity OSB 另一盤而家蝕錢，污染 blended PE（pe_pctile 95th 係
whole-company 混合估值，估值格因此判 0.5 documented 降級）。moat 1.0（被虧損 OSB 稀釋，1 分錨）。

承重 claim 拆三支柱逐個審:
- **(i) Siding 定價權係結構性**（唔係齋通脹傳遞 / cost-push pass-through）
- **(ii) vinyl→engineered-wood 轉換係 LP 專屬順風**
- **(iii) 2026-05 managed-allocation 係真.緊缺事件**（供給追唔上需求）

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道（Tier-1，最鋒利）**

- **Balance-sheet 檢查（defeatbeta quarterly_balance_sheet，16 季至 2026-03-31）——pilot MU /
  photonics 形態第三次複製:** LPX balance sheet **完全冇 customer deferred revenue / RPO row**;
  帳上唯一「deferred」係 Current Deferred **Taxes** Liabilities（~$5M）同 Non-Current Deferred
  **Taxes**（~$189M）——全部係遞延稅,唔係客戶預付。即「managed-allocation order file」喺資產
  負債表**零足跡**——係披露式 order file（講稿）,唔係現金背書嘅合約義務。**同 pilot「MU RPO
  $100B 唔喺 balance sheet」、photonics「COHR/LITE 冇 RPO row」同一形態**:order file ≠ 入帳緩衝。
- **存貨裂縫（反向信號,弱）**:LPX 總存貨升到序列最高 **$417M**(前季 $364M)、Finished Goods
  **$247M**(序列高)、WIP $35M。同管理層 May-2026 自認「channel inventories higher than we'd like
  + allocation hangover」+ Q1'26 Siding volume −18% 去庫存故事一致——存貨積壓係**供給鬆綁**嘅簽名,
  唔係緊絀。
- **全公司盈利被 OSB 污染(確認 gatekeeper blended-PE 判斷):** 季度 EBITDA 由峰值 ~$236M 崩到近
  幾季 **$30–78M**,一季淨利 **−$8M**(defeatbeta quarterly_income_statement)。whole-company
  ttm_pe 95th 係「弱 OSB 拉低 E、分母縮」造成嘅假貴,唔係 Siding segment 本身貴——估值 0.5 成立。
- **Insider(EDGAR Form 4,剔機械交易後):** Director **F. Nicholas Grasberger III 公開市場買入
  20,000 股(2026-02-19)**——真.看漲買盤,但**單一 director、非 cluster**;CEO/CFO 只有 RSU/PSU
  歸屬 + tax-withholding 賣(機械)。判定:**弱陽性,但唔構成 §4a「insider cluster 獨立擊中承重
  claim」**,不足以脫 single-source cap。

**(b) 外部一手(WebSearch,篩走意見文;派 subagent 狩獵,只收一手)**

- **子命題 (i) 定價權結構性——生還,且有殺手級正證(掂承重 claim):**
  - **FY2025 Siding net sales +8%,price +4% / volume +4%**(管理層明言 "evenly split",+$131M 營收
    /+$91M EBITDA;LPX Q4/FY2025 call 2026-02-17)——**量價齊升**,唔係需求破壞式純加價。
  - **殺手級正證**:呢 +4% 加價**發生喺 OSB / 木材通縮期**(管理層自認 OSB 實質價「20 年最低」)。
    投入成本**下跌**環境仍加得起 4% 並守住毛利 → 定價**同 cost-push 脫鈎**,直接反駁「齋通脹傳遞」
    嘅平庸解釋。2022 年 Siding 成本 +$123M 亦被 price+volume 完全吸收(LPX 2022 ARS)——兩點互證。
- **子命題 (iii) managed-allocation 緊缺——中彈 / 證偽(最鋒利一刀):** 搵唔到任何一手支持「2026-05
  緊缺」;一手證據**方向啱啱掉轉**:
  - LPX **2026-02-01 came off allocation,而且早過預期**,原因係 **Green Bay 新線 +50M sqft(+25%)
    產能上線 + OEE 設備效率改善**(LPX Q4 call 2026-02-17)——即**供給追上**,唔係需求爆。
  - 到 **May 2026 仲喺處理 "ExpertFinish allocation hangover" + channel inventories「higher than
    we'd like」+ Q1'26 volume −18%**(LPX Q1'26 call 2026-05-06)。
  - 即 2026 真實故事 = **由 on-allocation 轉 off-allocation(供給鬆綁)→ 通路庫存偏高 → 減量**。
    控方把一個**供給追上需求**嘅事件錯讀成「緊缺事件」。ExpertFinish 擴產一手清單佐證係主動擴產:
    Green Bay +50M sqft、Bath NY +20M sqft、North Branch MN(2028 ramp)。
- **子命題 (ii) vinyl→EW 轉換——半生還,有敘事風險:** engineered wood 搶 vinyl 份額成立(Freedonia:
  fiber cement 2025 ~26.8% 份額、premium 段已超 vinyl;EW 作 mid-price 快增)。**但 James Hardie
  FY26 6-K 明言 fiber cement「continues to take market share from lower-cost alternatives such as
  vinyl and wood」**——即 JHX 公開 claim 反過嚟搶緊 **wood(=engineered wood)**份額,先係更兇嘅
  share-gainer。「vinyl→EW 為 LP 專屬紅利」有敘事風險,fiber cement 兩頭食。
- **需求驅動偏逆風(周邊,加壓):** US Census 2026-05 housing starts **−15.4% MoM、SAAR 1.177M、
  2020-05 以嚟最低**;single-family 持續低於趨勢。Harvard LIRA R&R 較韌(+1.9%~mid-single)。
  LP volume 要靠搶份額 + R&R 頂,唔係品類自然增長——支持「Q1 volume −18% 部分係真需求疲弱」。

**(c) 歷史 / 平庸對照**:LEN/TOL 嘅「chronic housing underproduction」15 年老敘事已喺 group D 判 WEAK
(macro、input-constrained victim role)。LPX 之所以喺同批脫穎而出,正正因為佢講嘅係**自身產品**嘅
premium 定價,唔係 macro 短缺——呢個區分本次狩獵再確認(cost-decoupled 加價係 company-specific)。

### 動作 2 — Steelman 反方（非文章自供，事實錨齊）

**「2026 年 Siding 嘅強勁毛利/定價,係 2024–25 一次性 pre-buy 拉貨 + off-allocation 去庫存造成嘅
高基數,volume 嘅結構性需求未被證明」**:
1. Q1'26 Siding **volume −18%**、net sales −10%(LPX 2026-05-06 一手),管理層歸因「年頭加價前
   prebuy + shed 通路去庫存」——但 sell-through 正常化只有口述,**未有 Q2 落實**;
2. US Census 2026-05 housing starts 2020 年以嚟最低 → 品類需求逆風,volume 靠搶份額,而搶份額
   對手 JHX(fiber cement)FY26 明言反搶 wood 份額;
3. balance sheet 冇 deferred revenue / 客戶預付 = 下游**冇**用現金鎖多年供應(真緊缺時買家會預付);
   存貨升到序列高 = 積壓,唔係緊絀;
4. 先例:本系統 pilot(MU RPO)、photonics(COHR/LITE)已兩度證「披露 backlog/order file ≠ 入帳緩衝」,
   LPX managed order file 係第三例同型。

呢條 steelman 唔需要「定價權係假」——就算 price leg 全真,volume/結構需求嘅耐久性都可以係
未證(價升量跌,share-gain 對手更兇)。

### 動作 3 — 平庸解釋測試

**悶故事:「2021–23 全建材通脹傳遞 + 2024–25 pre-buy 高基數 + off-allocation 去庫存」解釋到幾多?**
- 解釋到:2022 提價、2025 revenue 增長、Q1'26 量跌——大部分價量走勢係任何建材週期都有。
- **解釋唔到(結構故事嘅額外證據,承重 claim 生還錨):** **FY2025 +4% 加價發生喺 OSB 20 年最低價
  通縮期**——通脹傳遞故事要求成本上升先加得到價,但呢度成本跌緊仍加價 = **cost-decoupled**,
  悶故事解釋唔到,係 company-specific 定價權嘅硬證。呢點係整個 thesis 最難反駁嘅單點。
- **可區分觀測(datable):**
  1. **Q2'26 Siding sell-through**:若去庫存後 volume 回正 + 加價守住 → 結構需求贏;若 volume 續跌 +
     ASP 鬆 → 高基數/去庫存故事贏。**這是 magnitude(volume)腿最近嘅可證偽窗口。**
  2. **Siding ASP net of 成本**:若後續季度成本回升而 ASP 跟唔上 → cost-decoupling 只係週期巧合。
  3. **JHX vs LPX 份額**:若 fiber cement 續搶 wood 份額 → 「LP 專屬轉換紅利」證偽。
- 結論:**子命題 (i)(定價權結構性)悶故事解釋唔到,有 cost-decoupled 硬證背書 → 生還。子命題
  (ii)(iii) 大部分可以齋用悶故事 / 供給鬆綁解釋。**

### 動作 4 — kill 距離（逐條，對現行 kill_condition）

| kill 軸（現行 wiki/themes.yaml） | 當下事實 | 距離判定 |
|---|---|---|
| **pricing-power 語言下季 transcript 消失** | 7/9 季持續,2026-05 最新季仍明講「pricing power of SmartSide helped offset lower volume」+ FY2025 cost-decoupled +4% | **未觸發、遠**;核心軸最硬 |
| **ExpertFinish allocation 下個上升週期冇再出現(=一次性)** | **軸本身 mis-specified**:控方把 allocation 讀成「緊缺 = 好」,但 2026-02 came off allocation 係**供給鬆綁**;allocation 再現與否唔一定係壞(可以係擴產去化)。應改為 volume/份額軸 | **軸需改寫**(見 §4) |
| **OSB 疲弱拖累到 Siding 強度反映唔到股價** | **已部分實現且係現行主症**:全公司 EBITDA 崩、淨利一度 −$8M、blended PE 假貴、OSB FY2026 指引 −$40M。Siding EBITDA $101M vs OSB −$12M | **已觸發中**:呢個正正係 confidence 0.20 + 估值 0.5 嘅根源;非新事實 |
| **vinyl 競爭者收窄價格/性能差距侵蝕 share-gain** | 部分實現但嚟自 **fiber cement / JHX**(唔係 vinyl):JHX FY26 明言搶 wood 份額;housing starts 2020 以嚟最低 | **未觸發、中距離**;kill 軸應擴至涵蓋 fiber-cement 競爭,唔淨係 vinyl |

---

## 3. 判決:**核心生還(且強化)+ 一條佐證支柱證偽 + magnitude(volume)腿未證 = 分岔**

按 §4b 校準(判決標準 = 承重 claim 面對補全事實集企唔企得住),逐支柱:

- **(i)「Siding 定價權結構性」——生還,且被補全事實集強化。** 最硬一手事實:**FY2025 +4% price ×
  +4% volume,發生喺 OSB/木材 20 年最低價通縮期** = cost-decoupled,量價齊升。悶故事(通脹傳遞)
  解釋唔到,有 company-specific 定價權硬證。這半句係全 claim 最硬部分。
- **(ii)「vinyl→EW 轉換為 LP 專屬」——半生還。** 轉換真,但 JHX(fiber cement)一手 claim 反搶 wood
  份額 + housing starts 最低 → LP 非唯一贏家,「專屬紅利」有敘事風險,volume 耐久性未證。
- **(iii)「2026-05 managed-allocation 緊缺事件」——中彈 / 證偽。** 一手證據方向掉轉:2026-02-01
  came off allocation(因 +25% 新產能 + OEE = 供給鬆綁),May 仲喺 hangover + 通路庫存偏高。控方把
  **供給追上需求**嘅事件錯當**緊缺**佐證。balance-sheet 零 deferred revenue 佐證:order file 無現金
  背書(pilot 第三例同型)。
- 附:Siding **price leg 已證(cost-decoupled)但 volume/share-gain magnitude 腿未證**(Q1 −18%、
  JHX 競爭、需求逆風,等 Q2 sell-through)——這正正係**分岔**形態:已-priced 嘅定價權部分證實,
  搏大升幅嘅結構性 volume/份額腿中彈/未證。

**Rubric 掛鈎(§4a;2 分前提 = 承重 claim 經 Level-2 且生還 + 不稀釋直接持有咽喉):**
- **moat 格:維持 1.0(不變)。** 定價權核心經 Level-2 生還兼強化(本質支持升格),**但 §4a 1 分錨
  「護城河被非核心業務稀釋」係結構性綁定**——虧損 OSB 污染 whole-company 經濟係實在,red-team 生還
  唔改稀釋事實。**紀律:唔因 red-team 生還而喺 confidence 數字度放大(§4c 原則)。** 若日後 segment
  reporting 能隔離 Siding 估值/ROIC,再重估上限(gatekeeper 待補已列)。
- **growth 格:維持 1.0(不變),但標 magnitude_unconfirmed。** 轉換機制真但公司只佔一角(1 分錨),
  加 volume/份額耐久性未證 + JHX 競爭 → 唔升;未證 volume 腿觸發通道 3。
- 估值(0.5,documented 降級)/資本配置(1.0)格照 gatekeeper 裁定,本協議不覆核。

---

## 4. 建議（不執行;郁數留返日間 confidence 迴路）—— 三通道分流(§4c)

| 通道 | 動作 |
|---|---|
| **通道 1（subscore→公式）** | **不變。** moat 1.0 / growth 1.0 / valuation 0.5 / capital 1.0 = 3.5/8 = 0.4375;penalty(crowding 97.2 ≥90 × mid)= 0.55 → raw **0.241**;single-source cap min(0.241, 0.30)= **0.241**（cap 未綁住）。**confidence = 0.24**（現行 themes.yaml 0.20 → 建議採 gatekeeper 遷移值 0.24,red-team 不再進一步移動——中彈落喺周邊佐證同 magnitude 腿,唔喺核心 subscore）。 |
| **通道 2（cap 資格,binary）** | **不脫 cap。** Tier-1 佐證(cost-decoupled 毛利/加價)係**同一批 transcript 嘅深讀**,唔係獨立渠道;insider Grasberger 係**單一 director 非 cluster**;財務直證掂嘅係定價權**結果**(周邊),唔係獨立擊中承重機制。照 §4a **唔足以**當獨立第二源。維持 single-source。 |
| **通道 3（magnitude 加成,sizing 層）** | **收起 magnitude 加成。** node `siding-segment-diluted`(magnitude_tier 2x)嘅 volume/share-gain 腿未證(Q1 −18%、JHX 反搶、housing starts 最低,等 Q2 sell-through)→ 建議標 **`magnitude_unconfirmed: true`**,sizing v2 對此 node 回落到 confidence-only 基準注碼,唔俾憑潛在 2x share-shift 加碼。**這先係本次 red-team 殺傷力真正落腳點——唔喺 confidence 數字,喺「搏大升幅嗰部分未證 → 唔加碼」。** |

**wiki / kill 措辭修訂(留返日間切):**
1. **「2026-05 真 managed-allocation 緊缺事件」改寫**:標明係 **2026-02-01 came off allocation
   (供給鬆綁,因 Green Bay +25% 新產能 + OEE),非緊缺**;order file 無 balance-sheet 現金背書
   (pilot MU / photonics 同型)。呢個係最鋒利一刀,現行 wiki + themes.yaml note + kill 軸 2 都需更正。
2. **kill 軸 2(ExpertFinish allocation 再現)mis-specified,建議改為 volume/份額軸**:例
   「Q2'26 起 Siding volume 連續兩季負增長且 ASP 鬆動(去庫存後未回正)」或「Siding EBITDA 份額
   被 fiber-cement 侵蝕」——現行「allocation 冇再出現 = 一次性」會把供給鬆綁誤讀成利淡。
3. **kill 軸 4(vinyl 競爭)擴至涵蓋 fiber cement / JHX**:JHX FY26 一手明言搶 wood 份額,
   先係比 vinyl 更兇嘅威脅。
4. **記生還錨**:FY2025 +4% price × +4% volume 喺 OSB 20 年最低價通縮期做到 = cost-decoupled,
   係定價權結構性最硬單點證據,應入 wiki 證據段(現行 wiki 只有語言 quote,冇 cost-decoupled 拆分)。
5. **早期警戒標記(非 kill)**:總存貨 / finished goods 續升穿序列高兼 Siding volume 未回正、
   Q2'26 sell-through 是否落實、housing starts 續探底、JHX vs LPX 份額。

**sources cap 註記**:本次 Tier-1(cost-decoupled 毛利/加價、單一 insider buy)佐證掂嘅係定價權
**結果 / 周邊**,唔係獨立擊中承重機制,照 §4a **唔足以**脫 single-source cap。

---

## 5. Meta-review（一句）

呢次 red-team 最有價值嘅唔係搵到反面而否定 thesis——核心定價權反而被 cost-decoupled 硬證**強化**;
而係發現控方引用嘅「2026-05 緊缺事件」**方向掉轉**(實情係供給追上、came off allocation),
提醒 INGEST checklist 要常設一問:**「呢個 allocation / backlog 事件,係緊絀簽名定係鬆綁簽名?」**
——同 pilot「披露 backlog ≠ 入帳緩衝」、photonics「32 月交期零掛源」同源:事件係真,方向/機制要核。
真正嘅賭注紀律唔喺 confidence 數字(維持公式 0.24),喺 magnitude 腿未證 → sizing 唔加碼。
