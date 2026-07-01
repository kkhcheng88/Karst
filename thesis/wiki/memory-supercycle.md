---
slug: memory-supercycle
type: B
cycle_stage: late
confidence: 0.38
verdict: real-but-late-cushioned
updated: 2026-07-01
tickers: [MU, SNDK, WDC, DRAM]
---

<!-- frontmatter = valid-YAML scalars only. Put wiki-links INLINE in the body; cite sources inline
     per claim. Never put double-bracket links in YAML frontmatter (breaks the parser). -->

# 記憶體超級週期(B 型)— real but LATE,被 LTA 去週期化墊高地板

> 綜合頁。蒸餾自 22 篇 Tier-2 報告([[memory-supercycle]] 叢,gooptions)+ 一手驗證(defeatbeta
> capex/ttm_pe,2026-07-01)。confidence = INITIAL/uncalibrated;當「有紀律的相對強弱 × 週期溫度」讀。

## 一句話(核心張力 = thesis 本身)
記憶體(DRAM / [[HBM]] / [[NAND-CMX]])是真的供給約束 + 需求爆發 + 三寡頭 [[pricing-power]] 的 B 型
超級週期。**多方說「[[LTA]] 去週期化」把它從週期商品變結構受約(這次不一樣);一手 capex 卻是教科書
供給回應頂訊號。** 誰對?→ **LTA 記分卡是可證偽的裁決變數。** 現在:**晚期、別追高,但 LTA 墊高了
下跌地板 → 小注 + 盯 LTA。** 可交易表達:[[MU]](核心)、[[SNDK]]([[NAND-CMX]] 純押)、[[WDC]]。

## 價值鏈(實體 + 關係;消化到 ticker)

```mermaid
flowchart TD
  HYPER["超大規模 capex + 折舊融資<br/>GOOGL·MSFT·AMZN·META·ORCL"] --> TRAIN["AI 訓練"]
  HYPER --> INFER["AI 推論 / agentic<br/>KV-cache 數十 TB 塞不進 DRAM"]
  TRAIN --> HBM["HBM ★瓶頸"]
  INFER --> DRAM["DRAM"]
  INFER --> NAND["NAND-CMX 記憶體層(第三支柱)"]
  ADVPKG["先進封裝 CoWoS / TSM"] -->|"產能閘"| HBM
  WF6["WF6 鎢氣體<br/>中國掐鎢·日本~25%·2026 +200%"] -->|"成本支撐"| HBM
  WF6 --> DRAM
  WF6 --> NAND
  HBM --> SUP["三寡頭供給"]
  DRAM --> SUP
  NAND --> SUP
  LTA["LTA/SCA 長約<br/>照付不議·不可取消·RPO 入表"] -->|"去週期化引擎"| SUP
  SUP --> MU["MU ✅美股 · LTA #1"]
  SUP --> SKH["SK Hynix ✗非美股"]
  SUP --> SAM["Samsung ✗非美股"]
  NAND --> SNDK["SNDK ✅美股 · NAND"]
  NAND --> WDC["WDC ✅美股"]
  WF6 -.->|"相對受益"| FOO["Foosung ✗非美股·韓"]
  MU --> DOWN["下游驗證：NVDA · AVGO · hyperscalers ▼非記憶體表達"]
  SKH -.->|"非美股→ETF 表達"| ETF["DRAM ETF"]
```

## ticker 層(Karst 端產品 = 這張表)

| ticker | 鏈上角色 | 可交易 | 一手驗證(Tier-1) | conviction 含義 |
|---|---|---|---|---|
| [[MU]] | DRAM+HBM+NAND 三線、[[LTA]] #1(16 份 SCA、RPO $100B 入表) | ✅ US | capex **2.94→7.83B(2.66x)** = 供給回應頂訊號 ✅;ttm_pe 26(67%) | **核心表達,但晚期兩面**:LTA 墊地板 vs capex 頂訊號 |
| [[SNDK]] | [[NAND-CMX]] 純度高、LTA book(RPO $41.6B) | ✅ US | ttm_pe **79(97%,n=94 史短不可靠)**;capex ~0.04B(輕資產→供給回應風險低) | NAND-CMX 純押;**估值需盯**(史短) |
| [[WDC]] | NAND/HDD 鄰接 | ✅ US | ttm_pe 38(82%);capex ~0.1–0.3B(平) | 次要、鄰接 |
| SK Hynix / Samsung | HBM 龍頭 / 寡頭核心 | ✗ 非美股 | — | 用 [[MU]]/[[SNDK]] 或 [[DRAM-ETF]] 表達 |
| Foosung | [[WF6]] 材料相對受益 | ✗ 非美股(韓) | — | thesis 輸入,不可交易 |
| NVDA / AVGO / hyperscalers | 需求驗證 | ✅ | — | **下游、非記憶體表達,別混淆** |

## 4-KPI(每條 cited;Tier-2 報告 # + Tier-1 一手)

### 1. moat / bottleneck — 強(2/2)
- **三寡頭 + HBM 瓶頸**:HBM 受 [[advanced-packaging]](CoWoS/TSM)產能閘限(Tier-2 #126/#132)。
- **上游材料咽喉 [[WF6]]**:中國掐鎢、日本約 25% WF6 產能 7 月起減、2026 合約 +70–90%、現貨 +200%
  → 全體記憶體成本上升、韓國 Foosung 相對得利(Tier-2 #110,`corpus.py get wf6-tungsten-memory-chokepoint`)。
- **定價權**:短缺 + LTA 硬約束 → 定價權從週期性往結構性移(Tier-2 #128)。

### 2. 資本配置 / ROIC — 中偏弱(1/2)+ 頂訊號 ✅
- **MU capex 一年 2.66x**:$2.94B(2025-05)→ 7.83B(2026-05)(Tier-1 defeatbeta `quarterly_cash_flow`,
  2026-07-01 拉)。**教科書「供給回應」頂訊號**——多年 underinvestment 正在反轉、產能加速。
- SNDK 輕資產(capex ~0.04B)→ 供給回應風險低,但也少了護城河式重資產壁壘。

### 3. 估值 / priced-in — 中(1/2)
- **MU ttm_pe 26(自身 5y 67 分位,中高非極端)**;WDC 38(82%);SNDK 79(97% 但 n=94 史短不可靠)。
  (Tier-1 `ttm_pe`,2026-07-01)。
- **peak-earnings 陷阱**:supercycle 讓盈利爆 → PE 看似不貴,但那正是週期頂的偽裝(估值研究通則)。

### 4. 成長耐久 / TAM — 中強(1.5/2)
- **三支柱需求**:HBM(訓練)+ DRAM + **[[NAND-CMX]]**(推論 KV-cache,NVIDIA 稱 CMX;資料中心 NAND
  需求 →40% by 2031)= NAND 從儲存變記憶體層,**真·新增 TAM**(Tier-2 #135,bull)。
- 但記憶體本質週期,非軟體 secular;**[[LTA]] 去週期化「若為真」才延長耐久性** → 這是關鍵 if。

## cycle_stage = LATE(三頂訊號)+ 去週期化墊高地板
| 訊號 | 現況 |
|---|---|
| 供給回應 ✅ 已確認 | **MU capex 2.66x**(一手)= 產能加速 = 教科書頂訊號 |
| 擁擠 🟡 | SK Hynix 喊 2034 擴產 3 倍(像 2017 逃命鐘)但 SanDisk 反漲(Tier-2 #104/#128);gooptions 記憶體叢 **僅 3/22 bull** → 這叢反而**沒到最擁擠** |
| 估值 🟡 | MU 67% 中高、peak-earnings 陷阱 |
| **去週期化(offset)** | **[[LTA]]/SCA 照付不議、不可取消、RPO 入表**(MU $100B、SNDK $41.6B)→ **真·墊高下跌地板**,downside 比過去週期淺——*若 LTA 紀律維持* |

→ **LATE 站得住(capex 頂訊號硬),但這輪有真結構 offset([[LTA]])→ 不是純追高、是 kill-bounded 的
兩面小注。** 進場鏡像(便宜 + 供給緊 + 未共識)不成立;但下跌不像過去無底。

## confidence 推導(可追溯)
```
KPI: moat 2/2 · capital 1/2(capex 2.66x 頂訊號)· valuation 1/2(MU 67% + peak-earnings)
     · growth 1.5/2(NAND-CMX 新 TAM,但 LTA-if)                      = 5.5/8 = 0.69 base
cycle penalty (LATE, capex 頂訊號確認,但 LTA 去週期化墊地板 → 罰輕於純晚期): × ~0.55  → 0.38
佐證: capex ✅ + ttm_pe ✅(Tier-1 已拉);LTA/RPO ✅(Tier-2 #128 財報入表,可信度高於一般 KOL)
      逐字稿受限語言 + LTA 記分卡前瞻追蹤仍待接 → 不加分
→ confidence ≈ 0.38  (INITIAL, uncalibrated)
```
**讀法:真主題 + 真結構 offset(LTA)但晚期已確認(capex 頂訊號)+ peak-earnings → 0.38。相對強弱有、
別追高;要吃 [[MU]] 小注 + 盯 LTA 記分卡,或 [[DRAM-ETF]] 分散。**

## kill_condition(LTA 中心,可證偽)
> **[[LTA]] 記分卡停止前進或反轉** —— 合約(LTA/SCA)價格轉跌 **或** 淨新增 LTA 簽署停滯(去週期化敘事
> 不再被財報追認)**或** HBM / [[advanced-packaging]] 產能 ramp 超前 AI 推論需求(轉過剩)。
> 觸發 → confidence 歸零,記憶體回歸經典週期頂、mean-revert。

## Agent 追蹤(定日可證偽預測 → track_record)
- **2026-07-01**:記憶體 = 晚期超級週期、被 LTA 結構墊高地板。表達 [[MU]](核心)+ [[SNDK]]([[NAND-CMX]])。
  方向:**不追高**(晚期);相對強弱小注;**追蹤變數 = LTA 記分卡 + 合約價**;kill = LTA 轉跌。
- forward-IC 評估器(待建)N 天後回填 → 這條預測的 forward IC 才是「thesis 有沒有 edge」的裁判。

## 待補(降「未確認」扣分)
- [ ] 接 LTA 記分卡的前瞻追蹤(每季 RPO / 新 LTA 簽署數 → 自動更新 cycle/confidence)。
- [ ] 逐字稿抽 MU/SNDK 管理層 HBM 受限 / 定價 / LTA 語言(moat + 去週期化證據補強)。
- [x] ✅ MU capex 2.66x(一手,供給回應頂訊號)— 2026-07-01。
- [x] ✅ MU/SNDK/WDC ttm_pe 分位(一手)— 2026-07-01。
- [ ] FNSPID 撈過去記憶體週期頂同期新聞,做乾淨 base rate(深化)。

## 來源
Tier-2(gooptions 記憶體叢 22 篇,見 `thesis/wiki/sources/`,全文在 `corpus.db`):關鍵 #128(MU LTA
證明)、#135([[NAND-CMX]])、#110([[WF6]])、#104/#068/#069(LTA 記分卡)、#133(2028 錨)、#103(融資
第二棒)。Tier-1:defeatbeta `quarterly_cash_flow`(capex)、`ttm_pe`(2026-07-01)。
