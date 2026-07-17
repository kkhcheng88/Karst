# FOMO 研究院(fomosoc.com)首輪 INGEST — 判詞正本(2026-07-17)

> **一個正本**:本檔係 FOMO 首輪 ingest 嘅唯一判詞記錄。逐篇內容檔喺 `thesis/.raw/fomosoc/`,
> 索引 `thesis/.raw/fomosoc/INDEX.md`。來源資格評估正本仍然係
> `backtest/results/2026-07-17_source_registry.md` §3b(**本檔對 §3b 提出三項修正,見 §6**)。
>
> **本檔只出建議。`thesis/themes.yaml` / wiki 一隻字都冇郁**(等 gatekeeper 覆核)。

## 執行摘要(一句業務判詞)

**十篇讀完:出到 1 個 scoped WEAKEN + 1 個真.框架更正 + 1 個 kill_metric 候選 —— 剛好命中 registry §3b 預先寫低嘅「證實有用」門檻,但 yield 只有 2/10,而且最大收穫係反面嘅:佢示範咗一個策展渠道點樣令同一份 SemiAnalysis 報告睇落似兩個獨立來源。**

---

## §1 總表

| 期 | 日期 | free/paid | 免費 % | theme | 判決 | 一句理由 |
|---|---|---|---|---|---|---|
| **#55 3D封裝** | 07-15 | only_paid | 65-70% | `advanced-packaging` | **WEAKEN**(scoped) | 逐字「OSAT 幾乎無法參與」混合鍵合,價值歸晶圓廠(TSMC)+ 設備商(BESI/ASMPT,**全非美**)→ 命中 `osat-arms-dealers` 嘅承重 claim「whoever wins gets paid」 |
| **#54 玻璃基板** | 07-01 | only_paid | 60-65% | `advanced-packaging` | **WEAKEN(弱)+ 框架更正** | **CoPoS ≠ 玻璃**(形狀 vs 材料,非硬性綁定);第4章標題(免費可見)「上游玻璃材料:重要,但**不是你該下注的地方**」= 對 GLW 點名負面,但理據牆後 + 循環論證 |
| **#53 NAND 控制器** | 06-24 | only_paid | 65-70% | `memory-supercycle` | NEUTRAL | 標題主角 SIMO/群聯「僅標題提及,內文未深入」;零出處;**唯一美股 ADR 機會落空** |
| **#52 功率半導體** | 06-17 | only_paid | **40-45%** | `ai-power-grid` | NEUTRAL | 標題問「誰是贏家」,免費段零個贏家名;17%/30% 滲透率無出處**且分母同 kill 軸對唔上** |
| **#51 利率路徑** | 06-10 | only_paid | 60-65% | **無**(`rates-duration`=RESERVED) | NEUTRAL(範圍外) | 全批出處密度最高 —— 但全部係我哋一手攞得到嘅公開宏觀數據(CME/FOMC/BLS) |
| **#50 HVDC/台達電** | 06-03 | only_paid | **45-50%** | `ai-power-grid` | **NEUTRAL(且無證據價值)** | ★ 開篇自認「**本篇在撰寫時參考 SemiAnalysis 報告**」→ 佢係我哋已一手持有嘅 PDF 嘅二次轉述 |
| **#49 GlobalFoundries** | 05-27 | only_paid | 65-70% | **無**(擦邊) | NEUTRAL(範圍外) | GFS = 代工平台唔係瓶頸擁有者(同 CIEN 剔除先例同構);兩個數字有數量級紅旗,未核實 |
| **#48 DCI** | 05-20 | only_paid | ~67% | `photonics-optical`(弱) | NEUTRAL | 專講 DCI 卻由頭到尾冇提 COHR/LITE = argument from silence + 99% 無出處 → 零證據價值 |
| **#47 Cloudflare** | 05-13 | only_paid | ~35-65%(未核實) | **無** | NEUTRAL(範圍外) | NET 已於 07-15 正式判出 Karst 範圍;純軟體 |
| **#55 Datadog**(撞號) | 07-08 | only_paid | 65-70% | **無** | NEUTRAL(範圍外) | 純軟體;**零具名出處**;⚠️ 同 3D 封裝篇撞「第55期」= 作者自己編號有錯 |
| **#46 KP 筆記** | 06-13 | **everyone** | **無牆** | `ai-power-grid` | NEUTRAL | ★ **全批對 theme 資訊量最高 —— 而佢係免費文**:SemiAnalysis(native 推遲 2028+)+ **摩根士丹利具名反駁** + **Google/Meta ±400V**(open question) |

**分佈:WEAKEN 2 / NEUTRAL 9 / STRENGTHEN 0。**

**一句業務判詞:零 STRENGTHEN 唔係意外 —— Level-1 本身就唔准升 confidence;真正嘅訊號係「WEAKEN 2 篇全部落喺同一個 theme(advanced-packaging)嘅同一條承重腿(美股 proxy 收唔收到租)」。**

---

## §2 ★ 交叉驗證:#50 / #52 / #46 vs「Inside the 800VDC Revolution」PDF

**任務假設**:「兩個獨立來源講同一件事,睇佢哋一致定矛盾」。
**實測結論:假設唔成立 —— 佢哋唔係兩個獨立來源。**

### 2.1 決定性事實

- 我哋一手持有:`thesis/.raw/zsxq/pdf/Inside the 800VDC Revolution – Part 1.pdf`(**SemiAnalysis** 出品,2026-05-26),已於 2026-07-17 ingest 入 `thesis/wiki/ai-power-grid.md` 第 182-192 行,判決 NEUTRAL。
- **FOMO #50(2026-06-03)開篇自認:「本篇在撰寫時參考 SemiAnalysis 報告」。**
- **FOMO #46(2026-06-13)明文引 SemiAnalysis** 講 native 800VDC 推遲 2028+。

→ **FOMO 係下游轉述,唔係獨立覆蓋。兩者「一致」= 零證據價值(同一份報告 + 佢嘅讀後感)。**

### 2.2 逐項對帳

| 項目 | SemiAnalysis PDF(一手) | FOMO #50 / #46 | 判 |
|---|---|---|---|
| 階段框架 | **Phase 1–4** | #46 簡化成兩階段(Sidecar / Native) | **簡化,丟失錨** |
| Sidecar 時程 | Phase 1 late-2026/2027 | #46:2026 下半年 | **一致**(預期之內) |
| Native 時程 | Phase 2 Turning Point **2027/2028** | #46:**2028 或更晚** | **FOMO 偏悲觀約半年** |
| 效率 | 1GW IT 負載 ~**5%** facility 節省 = ~50MW;Phase 4 效率 87.4% | #50:PUE **1.1→1.05**(≈4.5%) | **一致** —— 但因為同源,**唔算印證** |
| 600kW 機櫃 | 600kW rack 電流 54V→800V 降 ~14.8-16.7x | #50:Rubin Ultra **600kW** | **一致**(同源) |
| TAM / ASP | sidecar TAM ~$11B(2028)、SST ~$13B(2030)、HVDC rack ASP $400-500K | **兩篇皆無** | **丟失** |
| 可觀測錨 | UL 認證(2026-05 冇 vendor 完成)、NEC 2029 code、3300V+ SiC limited production、ABB「post-2028 opportunity」 | **兩篇皆無** | **丟失** |
| 器件滲透率 | high-power TAM **CY25 = $0**,**CY27 先 inflection**(+667%) | #52:**2026 = 17% → 2030 = 30%**(無出處) | ⚠️ **分母唔同,唔可對帳**(見 2.3) |

### 2.3 兩個表面矛盾,逐個拆

**(a) #52「無延遲、2026 滲透 17%」vs SemiAnalysis「CY25 TAM $0、CY27 先 inflection」**
→ **唔係矛盾,係分母唔同**:#52 度緊「SiC/GaN 器件喺資料中心電源系統嘅滲透率」(含 sidecar / 48V 世代用量);SemiAnalysis 度緊「800VDC **native** 架構 / high-power TAM」。
→ **實際後果:#52 個 17% 對我哋 kill 軸零用處** —— 唔可以用佢講「kill 未觸」。

**(b) 作者自己 #46(06-13,「800 VDC **延期了**?」)vs #52(06-17,「**無延遲**、快速上升」)**
→ **唔算硬矛盾**(#46 講 native 架構,#52 講器件滲透率),**但係 framing 不一致**:同一作者四日內,免費文以「延期」開題,收費文以「無延遲」開題,而收費文**冇帶返自己四日前引嘅 SemiAnalysis 延期 caveat**。
→ **對來源評估嘅意義:佢兩條產品線(免費筆記 / 收費深度)之間唔互相 reconcile。淨讀一篇會攞到誤導性 framing。**

**(c) 摩根士丹利具名反駁(#46 獨有,PDF ingest record 冇)**
→ MS:「供應鏈調查顯示 800V 直流電根本冇延誤」,證據 = 台達電 Q3 量產 800V 電源機櫃。
→ **覆核後:呢個反駁冇反駁到我哋條 kill 軸。** MS 講嘅係 **sidecar**(台達電 Q3),kill 軸講嘅係 **native**(SemiAnalysis stages 3-4)。KP 自己都寫「兩方都對,只係討論不同樓層」。
→ **kill 軸站得住,唔使改。** 但值得記低:**條軸建基喺 SemiAnalysis 一家嘅曲線上,而呢條曲線有具名嘅賣方對手盤。**

### 2.4 ★ 元教訓(本輪最有價值嘅單一發現)

**如果冇讀到 #50 開篇嗰句「參考 SemiAnalysis 報告」,呢輪 ingest 嘅自然結論會係:「FOMO #50/#52 同 SemiAnalysis PDF 講嘅嘢高度一致 → 兩個獨立來源互相印證 → `n_sources` 由 1 升到 2 → 脫 single-source cap 0.30 → confidence 可升。」**

**呢個結論會係完全錯,而且錯得好合理、好難察覺。**

→ **「唔准升 n_sources」呢條紀律唔係程序主義,係實質正確。** 策展型來源(FOMO / zsxq / gooptions)嘅本質就係**轉述**別人嘅一手研究 —— 佢哋之間、佢哋同一手報告之間嘅「一致」,係**同源**唔係**印證**。
→ **建議寫入 DESIGN §4a 嘅 independent-source 定義做註腳**(⚠️ 唔喺本輪授權範圍,**只出建議**)。

---

## §3 建議嘅 theme 更新(**只出建議 —— themes.yaml 一隻字冇郁,等 gatekeeper 覆核**)

### 3.1 `advanced-packaging` — 三項建議

#### (A) note 追加 evidence 段(草稿)

```
2026-07-17 夜班 ingest(FOMO 研究院 #55「3D封裝/混合鍵合」+ #54「玻璃基板」,Tier-2,
單一策展渠道、唔升 n_sources、Level-1 red-team 唔升 confidence;收費文免費段,分別 65-70%/
60-65% 免費,「邊個贏」全喺牆後;⚠️ 兩篇皆零具名出處,係佐證唔係證據):
(a) #55 逐字判死 OSAT 喺混合鍵合嘅角色:「傳統獨立封測代工廠(OSAT)幾乎無法參與...
    基本上被鎖在晶圓代工巨頭(如台積電)與整合元件製造商(如Intel)的體系之內。價值的最大
    受益者主要有兩類:掌握先進製程與封裝平台的晶圓廠 + 提供關鍵設備的製造商」。設備商點名
    BESI(阿姆斯特丹)/ASMPT(香港)——兩個都非美股,同本 theme note 現有「真瓶頸擁有者
    (Nittobo/Mitsui/Hoya)非美」嘅結構完全同型。★ 呢個獨立命中 2026-07-16 red-team 已判嘅
    「moat 2→1(OSAT 交易 proxy 唔捕捉真正租金)」——但 SCOPE 要清楚:只涵蓋 3D/混合鍵合
    段 TAM,冇否定 2.5D CoWoS 級嘅 format-war 軍火商論點(#131 原論點)。即係話「whoever
    wins gets paid」有一個未涵蓋缺口:當贏家係 3D 混合鍵合嗰陣,收錢嘅唔係 OSAT。
    ⚠️ 平庸解釋未排除:新技術初期鎖喺 foundry、成熟後外流去 OSAT 係歷史常態(覆晶/TCB 都係
    咁),#55 冇處理呢個反駁,我哋亦無證據判 → open question。
(b) #55 對 KLIC 係雙向:混合鍵合本質係消滅 TCB(KLIC 入本 theme 嘅逐字理由係「TCB 熱壓鍵合
    直接受惠」#150)= 長線逆風;但 #55 標題本身係「混合鍵合被推遲了?」+ 第四章講 HBM
    「層數從 8 層一路飆到 16 層,卻遲遲不肯換上這項新技術」= TCB 壽命延長、KLIC 近端順風。
    → 淨判:KLIC 嘅 TCB 論點係一個有到期日嘅論點,到期日 = HBM 幾時轉混合鍵合。→ kill_metric
    候選(見下)。⚠️「HBM 點解唔轉」嘅答案喺牆後,未讀。
(c) #54 框架更正(★ 即使零硬數據都有價值):「CoPoS ≠ 玻璃」——CoPoS 本質係形狀革命
    (圓晶圓→方面板),玻璃係材料升級,兩者係不同維度,「大面板化令玻璃剛性優勢凸顯,
    因此成為最佳夥伴,但並非硬性綁定」(即有人可以用面板唔用玻璃)。→ 本 note 2026-07-14
    (gooptions #157)寫嘅「CoPoS 坐實 GLW 玻璃基板呢條 2027-28 接棒線嘅結構性」講得過頭,
    建議改為:「CoPoS(形狀)同玻璃(材料)係兩條要分開觀測嘅軸;CoPoS 進展 ≠ GLW 受惠」。
    #54 另拆第二軸:玻璃中介層(難、慢)vs 玻璃核心載板 GCS(易、快,Intel 領頭,已展示
    20+ 層堆疊樣品)。
(d) #54 第四章標題(免費可見,理據牆後)逐字:「上游的玻璃材料:重要,但不是你該下注的
    地方」,導言點名 Corning。方向同本 theme 現有 glass-substrate-nextgen node 嘅 2x
    (「大型稀釋+慢 2027 變數」)一致 —— ⚠️ 但呢個係循環論證(「上游材料重要但唔值得買」
    係通用投資格言,唔係玻璃獨有洞見)+ 理據喺牆後 → 證據力極弱,唔足以動 magnitude。
(e) AMAT 覆核後唔入 tickers:#54 對 AMAT 只講「Absolics/SKC 引入應用材料資金」= 投資/融資
    關係,唔係供需瓶頸證據。依用戶 2026-07-10 方法論修正(入 basket 須有具體證據證明個名
    自己有瓶頸,唔可以淨係「被點名」)+ CIEN 剔除先例 → 唔夠料。記做 watch。ONTO 同理。
confidence 0.30 / cycle late / 全部 magnitude_tier 維持(Tier-2 零出處、Level-1 唔准升,
且 WEAKEN 方向已喺 07-16 red-team 反映)。
```

#### (B) kill_metric 候選(**新**)

| 候選 | 觀測 | 觸發 | 點解值 |
|---|---|---|---|
| **KLIC TCB 到期鐘** | HBM 由 TCB 轉混合鍵合嘅時點(觀測代理:HBM4/HBM4E 量產世代有冇採用 hybrid bonding;或 KLIC 業績會 TCB 訂單/營收含量) | HBM 主流世代確認轉混合鍵合 → **KLIC 入 theme 嘅逐字理由(「TCB 直接受惠」)失效** → `process-equipment-test` node 要拆 KLIC 出嚟 | 現有 kill 五條軸(T-glass 鬆綁 / 格式戰收斂 / CoWoS 過剩 / proxy de-rate)**冇一條捕捉到「設備世代更替打沉個別設備商」呢個機制**。呢條係新軸,唔係現有軸嘅重述 |

⚠️ **誠實**:呢條軸嘅證據來自一篇零出處 Tier-2。**建議 gatekeeper 只當「候選」記低,要一手驗(KLIC 10-K/業績會 TCB 含量、TSMC/SK 海力士 HBM4 封裝路線圖)先正式入 kill_condition。**

#### (C) magnitude 影響 —— **建議唔改,但提一個 option 俾 gatekeeper 判**

| node | 現值 | 建議 |
|---|---|---|
| `osat-arms-dealers` (AMKR/ASX) | 2-3x | **建議維持 2-3x。** 理由:證據零出處 + scoped(只 3D 段)+ 平庸解釋未排除 + 07-16 red-team 已經就同一條 claim 做咗 moat 2→1(唔應該就同一個發現扣兩次)。<br>**⚠️ 但提一個 option 俾 gatekeeper**:考慮加 `magnitude_unconfirmed: true`(現有機制,sizing v2 已接線,先例 = semicap-equipment/AEHR)。**論據**:承重 claim「whoever wins gets paid」而家有一個**已知、未經一手驗證嘅缺口**(3D 混合鍵合唔經 OSAT)。**反論據**:FOMO 唔算獨立源,用佢觸發一個有真實 sizing 後果嘅 flag,等於偷偷俾咗佢 n_sources 嘅地位。**我傾向反論據 → 建議唔加,淨係入 review queue。呢個係 judgement call,唔係公式輸出,交你。** |
| `process-equipment-test` (含 KLIC) | 2-3x | **建議維持。** KLIC 雙向(長線逆風/近端順風),淨效果未定 → 唔改,靠上面 kill_metric 候選追 |
| `glass-substrate-nextgen` (GLW) | 2x | **建議維持。** #54 對 GLW 嘅負面 = 循環論證 + 理據牆後 → 零增量 |

### 3.2 `ai-power-grid` — 一項建議(**最實用嗰項**)

#### note 追加(草稿)

```
2026-07-17 夜班 ingest(FOMO 研究院 #50「HVDC與台達電」+ #52「功率半導體」+ #46 KP筆記
「800 VDC延期了?」,Tier-2,單一策展渠道、唔升 n_sources、Level-1 唔升 confidence):
★ 最重要嘅唔係內容,係來源結構:#50 開篇自認「本篇在撰寫時參考 SemiAnalysis 報告」,#46
明文引 SemiAnalysis。即係話 FOMO 呢條 800VDC 線係我哋 2026-07-17 已一手 ingest 嘅
「Inside the 800VDC Revolution – Part 1」(SemiAnalysis, 2026-05-26)嘅二次轉述,唔係
獨立覆蓋。→ 佢同 PDF「一致」= 零證據價值;任何時候引用一律引 PDF 一手,唔好引 FOMO。
⚠️ 呢點推翻咗 2026-07-17_source_registry.md §3b 第 114 行「同一條軸 = 獨立覆蓋」嘅標註
(建議一併修正)。
逐項對帳(詳:backtest/results/2026-07-17_fomosoc_ingest.md §2):FOMO 版把 SemiAnalysis
四階段簡化成兩階段(Sidecar 2026H2 / Native 2028+),丟失晒 TAM($11B sidecar 2028、
$13B SST 2030)、ASP($400-500K/rack)、可觀測錨(UL 認證未有 vendor 完成、NEC 2029 code、
ABB「post-2028 opportunity」)。#50 免費段(只 45-50%)零逐條出處、零公司層面新事實、
US-listed 新標的 0(MPWR/VRT 已在 tickers,純分類提及)。#52 免費段(只 40-45%)標題問
「供應鏈誰是贏家」但一個贏家名都冇派;佢個「SiC/GaN 資料中心滲透率 2026=17%→2030=30%」
無出處,而且分母同本 theme kill 軸(800VDC native / high-power TAM,SemiAnalysis 稱
CY25 TAM 實為 $0、CY27 先 inflection)對唔上 → 唔可以用佢講「kill 未觸」。
兩個副產品值得記:
(a) #46 帶出摩根士丹利具名反駁(「供應鏈調查顯示 800V 直流電根本沒有延誤」,證據=台達電
    Q3 量產 800V 電源機櫃)。覆核後:呢個反駁冇反駁到 kill 軸 —— MS 講 sidecar,kill 軸講
    native,KP 自己都寫「兩方都對,只是討論不同樓層」。→ kill 軸站得住,唔改。但記低:
    條軸建基喺 SemiAnalysis 一家嘅曲線,有具名賣方對手盤。
(b) ★ OPEN QUESTION(唔開新 kill 軸,因為判唔到):#46 稱 Google/Meta 傾向採用「替代方案
    (±400V)」。業界慣例上「800VDC」好多時本身就係以 ±400V 實作(對地 ±400V = 800V 差動)
    → 咁樣嘅話 ±400V 唔係替代、佢就係 800VDC,FOMO 呢句可能係概念混淆。但亦有可能佢指
    真正嘅另一種拓撲,影響逐層含量分配。免費段解唔到,SemiAnalysis PDF ingest record 亦
    無呢條。→ 如果係真嘅第三條路線,現有 kill 軸「800V native slips OR 48V+pluggable stays
    good-enough」就漏咗佢。建議下次讀 SemiAnalysis Part 2 或一手查 OCP 規範時解決。
(c) #52 副產品:佢個「SiC 價值 50%+ 壓喺基板/上游咽喉」框架,對住「WOLF(美股唯一純 SiC
    垂直整合)已實現破產」呢個 ex-post 事實 = 咽喉 ≠ 定價權 ≠ 賺到錢嘅活教材。⚠️ 公道講,
    WOLF 破產可有其他成因(過度舉債擴產、EV 需求不如預期),唔足以否定咽喉論 → open
    question,唔當定論。呼應現有 pre-earnings-optionality node 嘅 5-10x-binary 標籤。
confidence 0.40(UNCALIBRATED_CAP 綁)/ cycle late / 全部 magnitude_tier 維持。
```

**一句業務判詞:呢個 theme 嘅建議入面,唯一有真實價值嘅係 (a) 記低「FOMO ≠ 獨立來源」—— 咁樣下次有 agent 讀到 FOMO 講 800VDC,唔會誤當第二個來源去升 n_sources。**

### 3.3 `memory-supercycle` / `photonics-optical` — **零建議**

- `memory-supercycle`(#53):標題主角 SIMO/群聯零內容、全篇零出處。**零行動。** SIMO 唔夠料入 tickers(同 CIEN 剔除先例同構)。
- `photonics-optical`(#48):argument from silence + 99% 無出處。佢捧嘅 Nokia/Cisco 正正係 theme 2026-07-10 已判過唔要嗰類「系統整合商非組件擁有者」。**零行動。**

### 3.4 範圍外(**零行動**)

#51 Fed(冇宏觀 theme,`rates-duration` = RESERVED/unused)、#49 GFS(代工非瓶頸)、#47 Cloudflare(NET 已於 07-15 判出範圍)、#55 Datadog(純軟體)。

---

## §4 來源最終判決 — 對照 gooptions 交付標準

registry §1a 定義咗**論述源**嘅兩條真判準 + §3 加咗第三條(kill metric 門檻)。逐條實測:

| gooptions 交付嘅嘢 | **FOMO 研究院(10 篇實測)** | 過? |
|---|---|---|
| **① 揪出我哋冇睇過嘅名**(二階/供應鏈/瓶頸,唔係 mega-cap) | **有揪到名,但淨可表達美股 = 0**。BESI/ASMPT/Absolics/SKC/群聯/台達電 = **非美**;SIMO(美股 ADR)= **免費段零內容**;AMAT/ONTO = **只係被點名,冇瓶頸證據**(同 CIEN 剔除先例同構);Nokia/Cisco/GFS = **系統整合商/代工廠,非瓶頸擁有者**(同 CIEN 同構);DDOG/SNOW/MDB/NET = 範圍外 | **◐**(揪到名,但**冇一個可入**) |
| **② 啲數字有冇出處** | **收費深度文(牆前)≈ 0-10% 有出處**。#55/#54/#53/#52/#48/#55Datadog = **零具名出處**。#50 = 開篇一句「參考 SemiAnalysis」但**零逐條標註**(= 望落有出處、驗唔到,§3 逐字「比冇數字更差」)。#51 = 出處密度最高,但**全部係公開宏觀數據,我哋一手攞得到**;#47 = Dell'Oro 一個 | **✗** |
| **③ 可餵 kill metric 嘅門檻** | **零**。冇一篇俾到可以直接餵 `kill_metrics.py` 嘅數量門檻。唯一 kill_metric 候選(KLIC TCB 到期鐘)係**我哋自己由佢個機制推出嚟**,唔係佢提供嘅門檻 | **✗** |

### 4.1 但要守住 registry 自己寫低嘅預先判準(唔准搬龍門)

registry §3b 逐字寫低咗本次實測嘅**預先註冊門檻**:

> 「**實測(而家零成本,做得過)**:攞 #55 **免費段**行一次 INGEST → 餵到 advanced-packaging 嘅 magnitude / kill_metric **或出到 WEAKEN**(非美廠賺走價值)= **證實有用**;**全 NEUTRAL = 好睇嘅嘢**」

**實測結果:命中。**
- #55 **出到 WEAKEN**(scoped),而且**正正係 registry 預言嗰個機制** —— 「非美廠(BESI/ASMPT)賺走價值」。
- 另加 1 個 kill_metric 候選(KLIC TCB 到期鐘)+ 1 個真.框架更正(CoPoS ≠ 玻璃)。
- **唔係「全 NEUTRAL」。**

→ **依預先註冊嘅標準,FOMO 過關。我唔會搬龍門。**

### 4.2 **最終判決:過關,但降級 —— 唔建恆常管道,改「按需拉取」**

**判決:保留為 red-team / 框架更正素材庫,唔建立恆常 ingest 管道。**

理由(全部係實測數,唔係印象):
1. **Yield = 2/10。** 10 篇出到 2 篇有用嘅(#55 WEAKEN、#54 框架更正),8 篇零行動。
2. **佢做唔到 gooptions 嘅 ①(可入嘅新名 = 0)同 ②(出處 ≈ 0)。** 過關全靠 ③ 嘅反面 —— **佢嘅價值係「否定」唔係「發現」**。
3. **「否定」呢種價值唔需要恆常管道。** 恆常管道(push)嘅前提係「有新嘢就要知」;但 red-team 素材係**你要 red-team 嗰陣先去揾**(pull)。
4. **成本結構啱 pull**:archive API 免費、每篇一次 WebFetch。要 red-team `advanced-packaging` 嗰陣去 archive 揾有冇對應期數,一次性讀 —— **零常態成本,零漏嘢風險**(佢啲文唔會消失)。

**建議操作模式(pull)**:
- **唔入** `daily_*.cmd` / `nightly_analysis.py` 任何自動管道。
- **唔加** `sources:` 條目、**唔升** `n_sources`(同 zsxq PDF 同等待遇)。
- **觸發條件**:當一個 theme 要做 Level-2 red-team,或者一個 node 嘅承重 claim 要 falsify 嗰陣 → 去 `https://www.fomosoc.com/api/v1/archive?sort=new&limit=40` 揾對應期數 → 讀免費段 → 只攞「反面證據 / 框架更正」。
- **永遠唔做買入來源**(名多數非美,或者係已判過唔要嘅類別)。

### 4.3 過去 3 個月夠唔夠料下判斷?**夠。**

- Archive 覆蓋 **2026-05-09 → 2026-07-15**(約 2.2 個月),23 篇,**10 篇逐篇讀晒**(全部深入分析 + 1 篇關鍵免費筆記)。
- **模式高度一致,唔係樣本雜訊**:免費段 = 教育/機制,牆後 = 「邊個贏」;深入分析篇出處密度接近零;最好嘅名非美。**10 篇入面 10 篇都跟呢個模式。**
- ⚠️ **但要守紀律 —— 唔由一篇推及全刊嘅教訓要雙向用**:registry §3 尾記低咗 2026-07-17 同日犯咗三次「樣本太窄就落通則」。**本輪 n=10 夠落通則,但仍有一個具體缺口**(#45「記憶體需求減半」/ #48 筆記「SK 減產 HBM」未讀,見 §5)。**判決唔變,但缺口要記。**

---

## §5 誠實節

### 5.1 牆斬走咗咩(逐篇)

| 期 | 牆後係咩 | 痛唔痛? |
|---|---|---|
| #55 | **BESI vs ASMPT vs 韓美設備商鬥法**(即標題主打)、HBM 點解唔轉混合鍵合 | **痛** —— 「HBM 點解唔轉」正正係 KLIC kill_metric 候選要嘅答案 |
| #54 | 誰是贏家、TGV(標題有,免費段零出現)、材料/檢測/面板/載板逐層 | **中** —— 但贏家多數非美,痛感有限 |
| #53 | **SIMO / 群聯全部分析**(免費段僅標題提及) | **最痛** —— 唯一美股 ADR 機會 |
| #52 | **供應鏈誰是贏家**(標題主打)、IDM vs Fabless 喺 SiC 嘅適用性 | **中** |
| #50 | **台達電角色**(標題主角)、「沒有人能一條龍」供應鏈分析 | **細** —— 台達電非美 |
| #48 | Arista 崛起 + 三股威脅 | **細** |
| #51/#49/#47/#55D | 範圍外 | 唔痛 |

**一句業務判詞:牆永遠斬喺「邊個贏」之前 —— 呢個係佢嘅商業模式,唔係意外;而「邊個贏」正正係 Karst 自己會做嘅嘢,所以互補;但同時亦即係話,佢免費派嘅嘢係機制,唔係標的。**

### 5.2 邊篇冇料(直接講)

- **#53 NAND 控制器** — **全批最差**。標題主角零內容、全篇零出處。同 #55(規格密集)同一條產品線、同一作者,**質素差一個級數**。registry §3b 預警咗「逐篇判,唔好一竹篙」→ **實測完全證實**。
- **#48 DCI** — 可追溯性 ~2/10,99% 無出處,連 Cisco 高峰年份都寫錯(講 1999,實際 2000-03)。
- **#52 / #50** — 免費比例全批最低(40-45% / 45-50%),而且**兩篇標題都問「誰是贏家」,兩篇免費段都零個贏家名**。
- **#49 GFS** — ⚠️ 兩個數字(「$70B+ 年營收」、「$3.75B 換 1% → 隱含估值 $375B」)**表面上差一個數量級**(GFS 實際營收 ~$7B、市值 ~$20-30B)。**我未一手核實,唔知係原文錯定 WebFetch 摘要失真 → 唔用、亦唔拿嚟指控作者。記低係因為兩個可能性都要知。**

### 5.3 US-listed 覆蓋率(本輪核心限制)

| 類別 | 數目 | 名單 |
|---|---|---|
| 點名嘅公司總數(免費段) | **~35** | — |
| **非美 → 只做證據** | **10** | BESI(阿姆斯特丹)、ASMPT(香港)、群聯(台灣)、台達電(台灣)、Absolics/SKC(韓)、三星(韓)、Infineon(德)、Renesas(日)、Schneider(法)、Siemens(德)、ABB(瑞士,僅 ADR ABBNY) |
| **美股但已喺 theme tickers**(零新增) | **5** | INTC、GLW、MPWR、VRT、ON |
| **美股但唔夠料入**(被點名 ≠ 有瓶頸證據) | **4** | AMAT、ONTO(融資/被點名關係)、SIMO(免費段零內容)、GFS(代工非瓶頸) |
| **美股但已判過唔要 / 同 CIEN 剔除先例同構** | **3** | Nokia(NOK)、Cisco(CSCO)、NET |
| **美股但範圍外** | **4** | DDOG、SNOW、MDB、ANET |
| **★ 淨新增可表達美股標的** | **0** | — |

**一句業務判詞:registry §3b 預言「佢最好嘅名大部分唔喺美股 → 但呢個反而可能更有用,因為佢係 advanced-packaging 嘅負面證據」—— 實測兩邊都應驗:美股新名 0(預言 ①),而 BESI/ASMPT 賺走混合鍵合價值確實出咗個 WEAKEN(預言 ②)。**

### 5.4 本輪方法論限制(必須講)

1. **`.raw` 檔唔係逐字原文。** 全部經 WebFetch 小模型重構。`.raw` 慣例係「immutable full text for citation」—— **本目錄唔滿足呢個慣例,已喺每個檔頭 + INDEX 標明**。任何引用前必須返原 URL。**呢個係真限制,唔係免責聲明。**
2. **牆後內容零覆蓋**(用戶已定唔訂閱)。所有「佢冇講 X」嘅觀察都受呢點污染 —— **可能佢牆後有講**。#48 嘅「冇提 COHR/LITE」尤其要小心(牆後 33% 未讀)。
3. **免費 % 全部係 WebFetch 目測估算,冇量過字數。** #47 嘅估算自相矛盾(同一次回應講 65-70% 又講 30-35%)→ 未核實。
4. **Level-1 red-team only** —— 唔可以升 confidence,本輪亦冇升。所有 WEAKEN 都只入 review queue,冇改任何數。

---

## §6 建議修正 `2026-07-17_source_registry.md` §3b(**只出建議,未改**)

依「一個正本」紀律,來源資格嘅正本係 registry §3b。本輪實測有**三項**同 §3b 對唔上,建議 gatekeeper 一併修:

| # | §3b 現寫 | 實測 | 建議 |
|---|---|---|---|
| **1** | 「★ 關鍵發現:『收費』深度分析 **70-80% 免費可讀**」(基於 #55 70-75% + #53 75-80% 兩篇樣本) | **10 篇實測:40-70%,平均 ~60%**。#52 = 40-45%、#50 = 45-50%(全批最低) | 改為「**40-70%,逐篇差好遠,越舊嘅文牆斬得越前**」 |
| **2** | 「佢**免費派嗰部分正正係 Karst 要嘅嘢(名 + 機制)**」 | **只有 2/10 成立**(#55 派咗 BESI/ASMPT/Ziptronix;#53 派咗名但**零內容**)。#52/#50 兩篇標題問「誰是贏家」,免費段**零個贏家名** | 改為「**免費派嘅係機制,唔係名。名有時派有時唔派,且派咗都可能零內容(#53)**」 |
| **3** | 第 114 行:#50 HVDC「**同 2026-07-17 ingest 嘅『Inside the 800VDC Revolution』PDF 同一條軸 = 獨立覆蓋**」 | **推翻** —— #50 開篇自認「本篇在撰寫時參考 SemiAnalysis 報告」 | 改為「**唔係獨立覆蓋:#50 自認轉述同一份 SemiAnalysis 報告 → 引用一律引 PDF 一手**」 |

**另建議**(⚠️ 超出本輪授權,只提):§2 表「FOMO 研究院」列 → 由「**候選——待實測**」改為「**過關但降級:pull-only red-team 素材庫,唔入自動管道、唔升 n_sources、唔做買入來源**」,正本指向本檔。

---

## §7 未解 / 風險

| # | 項目 | 風險 | 建議 |
|---|---|---|---|
| **1** | **#45「記憶體需求減半」/ #48 筆記「SK 海力士減產 HBM」未讀** | **本輪最明顯缺口**。兩篇標題方向直插 `memory-supercycle` kill 軸(「HBM/advanced-packaging capacity ramps AHEAD of demand → glut」)。**兩篇都係免費筆記,零成本可讀 —— 我冇讀,係我本輪嘅覆蓋漏洞** | **下輪優先讀呢兩篇** |
| **2** | **±400V 係咪真.第三條路線?** | 如果 Google/Meta 真係行緊 800VDC 以外嘅拓撲,`ai-power-grid` kill 軸「800V native slips **OR** 48V stays good-enough」**漏咗第三條路** | 一手查 OCP 規範 / SemiAnalysis Part 2 |
| **3** | **「新技術初期鎖 foundry、成熟後外流 OSAT」平庸解釋未排除** | 如果成立,#55 個 WEAKEN 就只係時序問題唔係結構問題 → `osat-arms-dealers` 唔應該扣 | 查覆晶/TCB 嘅歷史外流時序做 base rate |
| **4** | **KLIC TCB 到期鐘要一手驗** | 現時只有零出處 Tier-2 支撐 | 查 KLIC 10-K/業績會 TCB 營收含量 + TSMC/SK 海力士 HBM4 封裝路線圖 |
| **5** | **#49 兩個數量級紅旗未核實** | 唔知係作者算術錯(= 來源質素證據)定 WebFetch 失真(= 我哋管道問題)。**兩個可能性嘅意涵差好遠** | 返原 URL 核一次 |
| **6** | **`.raw` 唔係逐字原文** | 未來 agent 可能當佢係可引用原文 | 已喺每檔頭 + INDEX 標明;如果 FOMO 要長期用,考慮改用 headless 抓真原文 |
| **7** | **建議寫入 DESIGN §4a:「策展源之間嘅一致 = 同源,唔係印證」** | 呢個 failure mode(§2.4)唔止 FOMO 有,gooptions/zsxq 同樣係轉述型 | ⚠️ 超出授權,交 gatekeeper |

---

## §8 產物

| 檔 | 內容 |
|---|---|
| `thesis/.raw/fomosoc/INDEX.md` | 索引 + 三條使用紀律 + 判決分佈 + 未抓記錄 |
| `thesis/.raw/fomosoc/2026-07-15_3dhybrid-bondingbesiasmpt-553d.md` | #55 3D封裝 — **WEAKEN**(OSAT 判死 + KLIC 雙向) |
| `thesis/.raw/fomosoc/2026-07-01_copostgv-54.md` | #54 玻璃基板 — **WEAKEN(弱)+ 框架更正**(CoPoS ≠ 玻璃) |
| `thesis/.raw/fomosoc/2026-06-24_hbm-dramnvidia-ssd-53nand-flash-simo.md` | #53 NAND 控制器 — NEUTRAL(全批最差) |
| `thesis/.raw/fomosoc/2026-06-17_sicgan800v-52.md` | #52 功率半導體 — NEUTRAL(WOLF 張力) |
| `thesis/.raw/fomosoc/2026-06-13_800-vdcspacex-ipowwdc-kp46.md` | #46 KP筆記 — NEUTRAL(MS 反駁 + ±400V) |
| `thesis/.raw/fomosoc/2026-06-10_fed-51.md` | #51 利率 — NEUTRAL/範圍外 |
| `thesis/.raw/fomosoc/2026-06-03_800v-hvdc-50hvdc.md` | #50 HVDC — NEUTRAL(**非獨立來源正本**) |
| `thesis/.raw/fomosoc/2026-05-27_3-49globalfoundries.md` | #49 GFS — NEUTRAL/範圍外 |
| `thesis/.raw/fomosoc/2026-05-20_dci-48nokiacisco.md` | #48 DCI — NEUTRAL |
| `thesis/.raw/fomosoc/2026-05-13_aiagentic-ai-47cloudflare.md` | #47 Cloudflare — NEUTRAL/範圍外 |
| `thesis/.raw/fomosoc/2026-07-08_ai-ai-55datadog.md` | #55 Datadog — NEUTRAL/範圍外 |
| **`backtest/results/2026-07-17_fomosoc_ingest.md`** | **本檔 — 判詞正本** |

**冇郁過**:`thesis/themes.yaml`、`thesis/wiki/*`、`thesis/DESIGN.md`、`confidence_formula.py`、`sizing.py`、`lint.py`、`backtest/results/2026-07-17_source_registry.md`。
