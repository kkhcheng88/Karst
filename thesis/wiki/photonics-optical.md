---
slug: photonics-optical
type: B
cycle_stage: late
confidence: 0.30
verdict: real-bottleneck-but-crowded
updated: 2026-07-08
tickers: [COHR, LITE, AXTI, MRVL, AAOI, SIVE, LWLG, GLW, FN]
---

<!-- frontmatter = valid-YAML scalars only. Put wiki-links INLINE in the body; cite per claim.
     Never put double-bracket links in YAML frontmatter (breaks the parser). -->

# 光通訊 / 矽光子(B 型)— 真瓶頸,但最擁擠

> 綜合頁。蒸餾自 24 篇 Tier-2 報告(photonics-optical 叢,gooptions)+ 一手驗證(defeatbeta,2026-07-01)。
> **這叢是全批最擁擠(14/24 = 58% bull),confidence 因此壓到 0.30 < 記憶體 0.38**——即使 TAM 更大、
> 瓶頸更硬。示範:crowding 壓 confidence。INITIAL/uncalibrated。

## 一句話(核心張力)
光互連是 **AI scale-up 的物理層瓶頸**:銅撐到 3 公尺、再遠走光,TAM 10x($15B→$154B,高盛)。瓶頸真
(InP 雷射交期 **32 個月**、[[NVDA]] 三張 $2B 支票把產能買死)。**但這是全批最擁擠的主題**——58% 看多、
護城河名估值 75–98 分位、還有無盈利投機股喊 6–8x。→ **真主題、真瓶頸,但重度 priced-in:分層挑質、
別追小型 froth。** 最深護城河 = 無代工雷射 IDM [[COHR]]/[[LITE]];上游咽喉 = [[InP]] 的 [[AXTI]]。

## 價值鏈(6 層架構;毛利 20%→60%,消化到 ticker)

```mermaid
flowchart TD
  NVDA["NVDA 需求錨(下游)<br/>$6B 鎖產能 · $400B capex"] --> DEM["AI scale-up 物理層需求"]
  DEM --> L2
  L1["① 基板 InP<br/>AXTI 唯一美股純玩家 · IQE"] --> L2
  L2["② 雷射 EML/CW IDM ★最深護城河<br/>COHR · LITE 無代工·32月交期"] --> L3
  L3["③ 調變器<br/>LWLG 材料·無營收投機 · POET"] --> L4
  L4["④ 模組<br/>AAOI · FN Fabrinet"] --> L5
  L5["⑤ DSP 被 CPO/LPO 取代中<br/>MRVL · CRDO · ALAB 交界"] --> L6
  L6["⑥ 系統/交換/光纖<br/>AVGO · NOK · CIEN · GLW 康寧"]
  INP["InP 咽喉:32月交期 · 中國掐批次放行"] -.->|"卡點"| L1
  CPO["CPO 架構轉移:每800G 省電>70%"] -->|"重塑"| L5
  CPO -->|"後段耦合良率關(#143:一體共封~19%→需 99.5%)"| COUP
  COUP["④.5 光纖↔PIC 耦合(新增節點)<br/>GLW 玻璃橋 &lt;2dB/24ch(#138) · Teramount→Molex ±30µm · ficonTEC 主動對位=輸家"] --> L6
  ALAB["機架內銅 / retimer(#143)<br/>ALAB · CRDO:CPO 延後→銅多活一年、反受惠"] -.->|"CPO 延後對沖"| L5
  AEHR["AEHR 測試收費站"] -.->|"測試層"| L4
```

## ticker 層(Karst 端產品;6 層 → 分層 conviction)

| ticker | 層 / 角色 | 可交易 | 一手驗證(Tier-1) | conviction 分層 |
|---|---|---|---|---|
| [[COHR]] | ② 雷射 IDM 最深護城河、訂單到 2028、NVDA 夥伴 | ✅ | **ttm_pe 188(98%!)+ capex 0.11→0.29B(2.6x)** | **質最優但估值極端 + 供給回應** → 擁有護城河、慎入場 |
| [[LITE]] | ② 雷射 IDM、NVDA $2B 首押、高 beta | ✅ | ttm_pe 159(75%) | 質優但貴 / 高 beta |
| [[AXTI]] | ① [[InP]] 唯一美股純玩家、32 月交期咽喉;COHR 預付 $22.28M 鎖 3 年 6 吋(#139/#141) | ✅ | ttm_pe 16 是**盈利觸頂尾隨假象**(#141:當季虧損 −14.7%、預估 PE 72.8×、P/S 61×→38.6×、−41% vs 50 日均);6 吋良率僅 15–20% | **咽喉真、但「唯一便宜」下修**(#141);−13% 為 CPO 延後連坐非爆雷 |
| [[MRVL]] | ⑤ 架構定義者、跨鏈(自研 ASIC+1.6T DSP+光子 fabric) | ✅ | ttm_pe 102(86%) | 質優但貴、跨鏈 |
| [[AAOI]] | ④ 模組、9x 擴產宣言、InP 自製 | ✅ | ttm_pe 25(48%)、capex 0.03→0.06B(2.1x) | 投機-中、波動大 |
| [[SIVE]] | 100% CPO 1.6T 純玩家、喊 6–8x、估值全押 CPO 時程(#143) | ✅ | **無盈利;P/S ~190× 且營收年減(#143)** | **純投機 / CPO 延後最曝險端** |
| [[LWLG]] | ③ 調變器材料、無營收、IP 授權 | ✅ | **無盈利** | **純選擇權** |
| [[GLW]] | ⑥ 光纖 + ④.5 玻璃橋耦合 + 玻璃基板 + 玻璃晶圓 OCS = **四條光鏈**(#138);三雲鎖單 Meta $6B/NVDA 認股權證/Amazon | ✅ | **46× FY27 PE / 36× FY28、Truist 維持 Hold**(#138)= 非「便宜防守」;玻璃橋尚未變現 | 質優大型但估值已反映、發表≠量產 |
| [[FN]] | ④ 模組代工(Fabrinet) | ✅ | — | 代工、鏟子 |
| [[ALAB]] / CRDO | 機架內銅 / retimer、CPO 延後多活一年反受惠(#143) | ✅(待拉一手) | 未拉 ttm_pe → 待補 | **CPO 延後對沖**、非純光鏈多方 |
| NVDA / AVGO / GOOGL | 需求錨 / 下游交換 | ✅ | — | **非光通訊表達,排除** |

## 4-KPI(每條 cited)
### 1. moat / bottleneck — 強(2/2)
- **雙瓶頸**:上游 [[InP]] 基板(雷射交期 32 個月,#092)+ **無代工、產能不可共享的 EML/CW 雷射 IDM**
  (COHR/LITE,最佳 Coherent,#092)。NVDA 三張 $2B 支票($6B)鎖產能 = 卡點被外部確認。
- **6 層架構、毛利差 3 倍(20%→60%,#054)**:「把 LITE 和 LWLG 當同類 = 把台積電當聯發科」→ 護城河極
  不平均,集中在雷射 IDM 那層。
- **InP 咽喉再獲 SEC 背書(#139/#141)**:COHR 預付 **$22.285M 鎖 3 年 6 吋 InP 包銷**(8-K,2026-06-25),
  連自擴 6 吋的 Coherent 都得向 AXT 排隊 → 咽喉未鬆(kill 未觸發);AXT 6 吋單晶良率僅 15–20%,最高價值的
  雷射料(硫摻雜 n 型)仍是尺寸遷移**落後者**、量產主力還在 3 吋(#141)。
- **新增耦合關(#138)**:CPO 後段「光纖對不準 PIC」是**新瓶頸節點**——康寧玻璃橋(離子交換波導、被動對位、
  <2dB、24 通道)vs Teramount(併入 Molex,±30µm/0.5dB、晶圓級)競逐;傳統主動對位設備(ficonTEC)結構性輸家。

### 2. 資本配置 / ROIC — 中(1/2)+ 供給回應形成中
- **COHR capex 2.6x**(0.11→0.29B,一手)、AAOI 喊 9x、AXTI 4x 增資 → **供給正在回應**(晚期形成訊號)。
- GLW:光通訊 ROIC 將超顯示器(#070)→ 資本效率敘事偏正,但仍是敘事待證。

### 3. 估值 / priced-in — 弱(0.5/2)⚠️ 最大拖累
- **護城河名估值極端**:COHR ttm_pe **98 分位**、MRVL 86%、LITE 75%(一手,2026-07-01)。
- **無盈利投機**:SIVE、LWLG 無盈利,報告本身喊 6–8x(#063)、9x(#060)= froth。
- **crowding**:24 篇 **58% bull**、滿是 SALP/Leopold 持倉、NVDA 鎖單、「8 天 4 家確認」「集體訊號週」
  (#055)= 賣方一致、資金湧入 → 重度 priced-in。
- **AXTI 去溢價 + 「唯一便宜」下修(#141)**:AXTI P/S 自 61× 殺到 38.6×、−41% vs 50 日均,但**當季轉虧
  (−14.7%)、預估 PE 72.8×** → 過去的「唯一便宜錨(ttm_pe 16/26 分位)」是**盈利觸頂尾隨假象**、不宜再當
  便宜入口(同一修正見 [[advanced-packaging]]、[[rare-earth-materials]] 的 AXTI 引用)。

### 4. 成長耐久 / TAM — 強(2/2)
- **TAM $15B→$154B(10x,高盛,#092)**;光互連是 AI scale-up 的**物理層必需**(非題材),CPO 省電 >70%
  → 真、additive、若 AI capex 續則耐久。

## cycle_stage = LATE / 最擁擠(crowding 壓 confidence 的示範)
| 訊號 | 現況 |
|---|---|
| 擁擠 🔴 **全批最高** | **58% bull** + 護城河名 75–98 分位 + 小型股 6–8x 目標 + SALP/NVDA 鎖單敘事 |
| 供給回應 🟡 形成中 | COHR capex 2.6x、AAOI 9x / AXTI 4x 擴產宣言 |
| 瓶頸仍真 🟢 | InP 交期 32 月未解、中國僅**精準批次放行**(#115)+ COHR 預付鎖 6 吋(#139/#141)= 短缺未結束 → 主題有腿 |
| crowding 開始消風 🟡(新,#141/#143) | **CPO 延後恐慌單日殺 10%、AXTI −13%** = 擁擠端首度回修;但屬「時程滑動」非「替代」——龍頭 COHR/LITE 靠可插拔+EML 訂單、延後不痛(Lumentum $808M **+90% YoY**),純押注 SIVE/LWLG(P/S ~190×)最曝險 → 分層洗牌、非全鏈利空 |

→ **真物理瓶頸,但被市場搶先定價到極端。** 對比記憶體(3/22 bull、MU 67 分位),這叢**更晚更擠** →
confidence 更低。**挑質(COHR/LITE/GLW)、避 froth(SIVE/LWLG);要進場等 crowding 消風。**

## confidence 推導
```
KPI: moat 2/2 · capital 1/2(COHR capex 2.6x) · valuation 0.5/2(COHR 98%/MRVL 86% + SIVE/LWLG 無盈利)
     · growth 2/2(TAM 10x 物理層必需)                                   = 5.5/8 = 0.69 base
crowding/cycle penalty (LATE + 58% bull 最擁擠 + 護城河名 75-98 分位 + 小型投機 froth): × ~0.43  → 0.30
→ confidence ≈ 0.30  (< 記憶體 0.38 — 擁擠壓低,即使 TAM 更大、瓶頸更硬。INITIAL, uncalibrated)
```

## kill_condition(可證偽)
> [[InP]] 短缺解除(32 月交期壓縮 / 中國全面放行 / 新產能上線 → 基板不再是卡點)**或** CPO 導入時程實質
> 落後([[LPO]]/可插拔續當 good-enough,#107)**或** 雷射 IDM(COHR/LITE)訂單能見度(到 2028)/定價破裂。
> **crowding-unwind:** 無盈利投機(SIVE/LWLG)+ 75–98 分位護城河名,任何 AI-capex 打嗝即重挫。
> 觸發 → confidence 歸零。
> **(#143 更新:CPO 延後已現──NVIDIA CPO 交換機推遲一季、2026 僅出貨數千台;但屬「時程滑動」非「替代」,
> 龍頭訂單來自可插拔+EML 不痛 → 逼近 kill 但未觸發。真觸發要 LPO/可插拔長期勝出、或龍頭訂單能見度破裂。)**

## Agent 追蹤(定日可證偽預測 → track_record)
- **2026-07-01**:光通訊 = 真物理瓶頸但**最擁擠、重度 priced-in**。表達分層:質 [[COHR]]/[[LITE]]/[[GLW]]
  (擁有護城河、慎入場)vs froth [[SIVE]]/[[LWLG]](避)。方向:**不追**;等 crowding 消風;追蹤變數 =
  InP 交期 + 護城河名估值分位 + bull 佔比;kill = InP 解除 / CPO 落後。
- **2026-07-05**(ingest #138/#139/#141/#143):瓶頸**再確認**(COHR 預付鎖 6 吋 InP、龍頭延後不痛),同時
  **擁擠開始消風**(CPO 延後單日殺 10%、AXTI −13%)= 論述地基未破、froth 開始回修 → confidence 維持 0.30、
  cycle 維持 LATE;修正:AXTI「唯一便宜」下修為盈利觸頂假象;新增 ④.5 耦合節點 + ALAB/CRDO 銅對沖。
- forward-IC 評估器(待建)N 天後回填 → 裁判。

## 2026-07-08 update:#149(free preview)新證據 —— 層輪動,非板塊看空(confidence/cycle_stage 維持)

- **網路扁平化 = 層輪動,不是整個光通訊看空(#149)**:OpenAI **MRC**(兩層交換即可連 **10 萬+ GPU**,
  背書名單 AMD/AVGO/INTC/MSFT/NVDA)+ Amazon **RNG**(用被動光學取代主動網路設備,**−60%+**)一起把
  「交換機對交換機」(switch-to-switch)這一層壓平,直接砍掉這層最密集的收發器需求。
- **第一次具名券商行動**:B. Riley 以「網路扁平化」為由把 [[AAOI]] 降評至中性、目標價 **$129**——
  理由不是缺貨/CPO 延後,而是拓撲壓縮本身,這與過去(系列 21/#107)「CPO 取代 DSP、光學含量不變」的
  元件換代邏輯是**不同機制**(前者砍模組數量、後者只換模組內部元件)。[[AAOI]] 反向對賭需求持續:
  官宣德州擴產至約 **70 萬顆/月**、雷射磊晶擴增約 **350%**。
- **TAM 總量仍增,價值往上游遷移**:光學 TAM $15B→$154B(仍是 10x 級成長),但收發器層承壓、價值往
  上游光源/CPO/矽光/InP 遷移 → **強化本頁既有立場(挑質 [[COHR]]/[[LITE]]/[[GLW]]、避收發器層/froth)**,
  不改變 confidence 0.30 / cycle LATE(這是分層訊號,非新增瓶頸或新增擁擠證據)。
- [[ai-capex-macro-risk]]:收發器層壓力若擴散成整條光鏈需求下修(而非純架構層輪動),要對照該頁「承諾
  −run-rate 缺口」與「四大 FCF 軌跡」兩盞燈,分辨是架構重組還是 AI-capex 打嗝的前兆。

## 待補
- [ ] 接「crowding 溫度」自動量測(bull 佔比 + 估值分位 → 動態 cycle/confidence)。
- [ ] 逐字稿抽 COHR/LITE 管理層產能/交期/定價語言(moat + 32 月交期證據補強)。
- [x] ✅ COHR/LITE/AXTI/MRVL/AAOI ttm_pe + capex(一手)— 2026-07-01。
- [ ] universe.yaml 加光通訊 grouping,讓 scan 覆蓋(目前 thesis 層有、scan 未覆蓋)。
- [ ] SIVE/LWLG 無盈利 → 用選擇權/事件框架(非 PE)另評。
- [ ] 拉 [[ALAB]]/CRDO ttm_pe/capex(一手),CPO-延後對沖曝險,再評是否納 universe.yaml。
- [ ] 拉 GLW FY27/28 PE 一手核(#138 稱 46×/36×),校準「便宜防守」→「已反映」的定位。

## 來源
Tier-2(photonics 叢 24 篇,`thesis/wiki/sources/`,全文 `corpus.db`):#092(雷射 IDM 護城河)、#054
(6 層架構)、#055(InP 集體訊號週)、#059(AXTI InP 純玩家)、#063(SIVE CPO 純玩家)、#070(GLW 康寧)、
#107(CPO 取代 DSP 非模組廠)、#115(中國批次放行 InP);**新增批次(2026-07-05):#138(GLW 玻璃橋≠玻璃基板、
新增耦合節點、三雲、46× PE)、#139(多頭長推體檢、COHR 預付 $22.28M 鎖 6 吋 InP)、#141(AXTI 殺盤=去估值溢價、
分階段爬坡、雷射仍 3 吋)、#143(CPO 延後三排受害地圖、龍頭不痛、ALAB 銅窗口)**;**新增(2026-07-08):
#149(free preview,網路扁平化 OpenAI MRC/Amazon RNG 壓收發器層、B. Riley 具名降評 AAOI、層輪動非板塊看空)**。
Tier-1:defeatbeta `ttm_pe`/`quarterly_cash_flow`(2026-07-01)。
