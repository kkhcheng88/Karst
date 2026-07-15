# Level-2 Red-Team：memory-supercycle(記憶體超級週期)

- 日期：2026-07-15
- 協議：thesis/DESIGN.md §4b（FALSIFY 升級：INGEST 係審判，唔係歸檔）
- 角色：辯方 red-team。**職責 = 事實補全（搵敘事冇展示嘅重大事實），唔係反對表演。**
  每條反方必須錨喺可引用事實/數據；砌唔到錨定事實 = 標「敘事風險」，唔算 finding。
- 約束：只新增本檔，冇改 themes.yaml / wiki / 任何現有檔。

---

## 1. 控方主張摘要

記憶體（DRAM/HBM/NAND）係真·供給約束 + AI 需求爆發 + 三寡頭定價權嘅 B 型超級週期；
**承重 claim = 「LTA / take-or-pay / RPO 令盈利去週期化，今次唔同以往週期，回調地板被墊高」**
（verdict: `real-but-late-cushioned`，confidence 0.38，全簿最高）。

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道（Tier-1，最鋒利，因為係一手且直接掂承重 claim）**

- **MU 資產負債表：聲稱嘅 RPO $1,000 億根本唔喺表上。**（defeatbeta `quarterly_balance_sheet`，2026-07-15 拉）
  - MU **總負債（Total Liabilities）2026-05-31 = $334 億**。聲稱嘅 RPO $1,000 億 = **總負債嘅 3 倍**——
    數學上唔可能坐落 balance sheet。
  - 真正入帳嘅遞延收入（Non Current Deferred Revenue）= **$10.2 億**（一年前 $6.03 億），
    對 $1,000 億 backlog 嘅覆蓋率約 **1%**。YoY 總負債只增 $57 億（$276→$334 億），
    而且大頭係 Payables $134 億（付俾設備/供應商，配合 capex，唔係客戶預付款）。
  - **事實補全**：RPO 係 ASC606 **附註披露嘅履約義務 backlog**（承諾交付、按合約價計量），
    **唔係入帳嘅負債緩衝**。只有收咗客戶預付現金先會變 deferred revenue（=$10.2 億）。
    wiki「RPO $100B 入表 → 真·墊高下跌地板」把「披露 backlog」同「入帳緩衝」混為一談——
    緩衝嘅實質質素 = 呢個 backlog 嘅**執行力 + 價格條款**，兩者 wiki 都冇驗。

- **MU 管理層自己嘅措辭：SCA 保 visibility/volume，冇講保價。**（corpus `transcript-MU-2026-03-18`，FY26 Q2）
  - Mehrotra 原話：SCA「different from prior LTAs and have specific commitments over a multiyear
    time horizon for **improved visibility and stability**」「provide customers greater certainty to plan」。
  - **事實補全**：管理層把 SCA 框成**能見度/穩定性/多年量承諾**，通篇冇「fixed price / price floor」語言。
    wiki 4-KPI moat 格寫「定價權從週期性往結構性移（#128）」——但一手逐字稿只支撐到**量**嘅去週期化，
    唔支撐到**價**嘅去週期化。而記憶體盈利同股價由**價**驅動，唔係量。
  - 附帶（同一句嘅雙刃）：管理層明講 SCA「different from **prior LTAs**」= **承認以前就有 LTA**。
    即係「上一輪都有長約」呢件事，係公司自己認嘅——而上兩輪（2019、2023）記憶體照冧。

- **Insider：MU heavy-selling（net −$29.4M，score −0.35），SNDK/WDC neutral 淨賣。**
  （thesis/insider.py，SEC EDGAR Form 4）——**唔算強 finding**（晚週期高位內部人減持係常態、非 cluster），
  只作弱佐證：冇任何 insider cluster **買入**去獨立追認去週期化承重 claim。

**(b) 外部空方（WebSearch，已避開 gooptions；篩走純意見，只留錨定事實嘅）**

- **2017 DRAM 長約先例：同一產品、同一 take-or-pay 工具，供過於求時被打回現貨。** 上一次缺貨潮簽嘅
  多年框架長約，需求一冷、價 2–3 季跌 >40%，客戶延提 + 重談 + reset 回貼近現貨。
  （BigGo Finance《Memory Industry Valuation Logic Shifts》；
  https://finance.biggo.com/news/UFasXp4BrX5PFN7BxfHq ）
  **註**：wiki #150 **已提**「2017 也曾鎖量長約、結果被打回現貨」——所以呢條**唔算全新遺漏**，
  但 wiki 只當 caveat 記低、冇讓佢郁 confidence；補全嘅係**幅度**（>40%、2–3 季）。

- **GrafTech take-or-pay 崩盤 + 「negotiation from weakness」**：分析論證 MU 鎖 20% DRAM / 30% NAND 量，
  本身係「若從強勢會做固定定價」嘅**弱勢談判訊號 + 對未來現貨審慎**。石墨電極 GrafTech 2018 鎖 60–70% 產量、
  五年 take-or-pay 固定 $9,700/MT；現貨崩後長約淪為「帶懸崖嘅倒數時鐘」，IPO 後 6 個月破發。
  （acidinvestments；https://acidinvestments.substack.com/p/some-weekend-muses-on-long-term-contracts ）
  **性質：直接反駁「LTA=去週期化=更高倍數」嘅估值邏輯本身。wiki 完全未提，屬全新遺漏事實。**

- **Kyocera v. Hemlock（2011 太陽能多晶矽 take-or-pay）——雙刃，誠實兩面呈現**：Kyocera 預付逾 $514.8M
  鎖到 2020；現貨崩後主張 force majeure 拒提。**法院判 take-or-pay 條款可執行（force majeure 不成立）——
  呢點對控方有利**；**但** Kyocera 最終仍走數 + 和解，放棄預付款、認蝕約 $450M。
  （Kyocera Corp. v. Hemlock Semiconductor, Mich Ct App 2015 / 6th Cir 2018；
  https://caselaw.findlaw.com/court/mi-court-of-appeals/1719993.html ）
  **性質：downturn 時「執行 take-or-pay」= 經年訴訟 + 折衷 reset，唔係乾淨嘅價格地板。**

- **2027 產能（文章冇展示嘅供給側數字）**：SK Hynix HBM 佔 DRAM 產能比重 **今年 ~30% → 2027 ~40%**；
  Yongin 群聚 ₩120tn（$89B）、目標 2030 月產 100 萬片 DRAM；M15X 由 4 萬片 → 2027 約 8 萬片/月。
  （en.sedaily.com / TradingKey；https://en.sedaily.com/finance/2026/01/01/samsung-sk-hynix-launch-massive-chip-capex-race-investment ）
  **性質：一般週期空方（供給側時鐘）。capex 大擴張=教科書頂訊號，同 wiki 自己嘅「MU capex 2.66x=供給回應頂」同向。**

- **MU 毛利 84.9%（指引 ~86%）高出 2018 峰值約 25 個百分點**——「遠超任何歷史先例、不可維持」。
  （useluminix DRAM Cycle Position Analysis；
  https://www.useluminix.com/reports/industry-analysis/dram-cycle-position-analysis-peak-timing-indicators ）
  **性質：均值回歸炸彈，錨定具體數字。同「平庸解釋」直接相關（見動作 3）。**

- **（標「敘事風險」，唔算 finding）**：Morgan Stanley「peak rate of change」、UncoverAlpha「every cycle ends
  the same」——係**意見/類比**，非記憶體特定嘅新遺漏事實；記錄作背景，唔給 finding 分量。

### 動作 2 — Steelman 反方（至少一條非文章自供）

> **最強反面敘事：「LTA 保量唔保價；記憶體盈利同股價由『價』驅動；所以 LTA 墊嘅係『量嘅地板』，
> 唔係『價/盈利/股價嘅地板』。呢輪唯一真結構分別（HBM 受 CoWoS 封裝閘限）係『供給更緊嘅週期頂』，
> 唔係『去週期化』。」**
>
> 支撐（全部錨定事實，非空談）：
> 1. MU balance sheet：$1,000 億 RPO 對應入帳遞延收入僅 $10.2 億（動作 1a）——冇「入帳緩衝」實體。
> 2. MU 管理層親口：SCA = visibility/volume commitment，**冇** price floor 語言（動作 1a）。
> 3. 機制：take-or-pay 通常保**提貨量**；RPO 按**合約價**計量，而記憶體合約價逐季重定。glut 時
>    RPO 帳面金額可維持（量鎖住），但**已實現毛利照樣塌**——量地板 ≠ 盈利地板。
> 4. 先例三連（2017 DRAM / GrafTech / Kyocera）：downturn 時買方寧願延提、重談、打官司、蝕錢和解，
>    都唔照單提貨；「地板」實際係「經年訴訟 + reset」。

**非文章自供嘅獨立反方硬性條**：**GrafTech「locking volume = negotiation from weakness」反框**——
把 wiki 視為「護城河證據」嘅 LTA book，重新解讀成「管理層自己都唔信現貨守得住」嘅**弱勢訊號**。
wiki 全篇（含 22 篇 gooptions + 一手驗證）冇任何地方提出呢個反框。

### 動作 3 — 平庸解釋測試

**MU TTM EPS YoY +697% 可唔可以齋用「普通超級週期頂部 + 低基數」解釋，唔使「結構去週期化」？**

**可以，而且更省。** 每一輪記憶體上行都製造爆炸性 EPS（2018、2022 皆是），之後崩。
+697% 係「谷底低基數 × 週期頂」嘅標準簽名，唔係去週期化嘅證據。佐證：MU 毛利 84.9% 高於 2018 峰值 25pt
（useluminix）——正正係「週期頂偽裝」，唔係「新常態地板」。

**邊啲觀測可以區分兩個假說？**
- 去週期化假說預測：**下一個谷底比歷輪淺**（盈利唔轉負、毛利守喺歷輪谷底之上、股價回撤 < 歷輪 −50~60%）。
- 普通超級週期假說預測：正常 −50~60% 盈利/股價回撤，時間點領先基本面 1–2 季。
- **關鍵**：兩個假說**只喺 downturn 先分岔**；上行段**觀測等價**（observationally equivalent）。
  downturn 未到 → 承重 claim 目前**未被證實、亦未被證偽**。confidence 公式**唔應該當佢已確認**去記分。

### 動作 4 — kill 距離

- `python thesis/kill_metrics.py --report`（2026-07-15）：**memory-supercycle 冇可量化 kill 軸**——
  kill_condition 全 prose（「LTA scorecard stalls or reverses」「HBM glut」皆質性），themes.yaml 冇
  `kill_metrics:` 欄位。系統確認：本 theme **冇數值 tripwire**，離觸發幾遠全靠人手判。
- prose 逐條估當下距離：
  | kill 軸（prose） | 當下距離估計 |
  |---|---|
  | 合約價 roll over | **最近**。useluminix：合約價 QoQ 動能已由 +90–95%(Q1) → +58–63%(Q2) → 預測 +13–18%(Q3)；「動能見頂領先價格見頂 2–4 季」。價未跌，但**二階導已明顯轉弱**。 |
  | 淨新增 LTA 簽署停滯 | **未觸發**。MU 剛簽「first five-year SCA」，仍在加。 |
  | HBM/封裝 ramp 超前需求（glut） | **中距**。2027 產能種子已落（SK Hynix HBM 佔比 →40%、Yongin），但 2026 仍短缺（高盛「15 年最嚴重」）。 |

---

## 3. 判決

**承重 claim「LTA 去週期化真係成立、今次唔同」→ 部分中彈（partially hit）。**

拆開兩截：

- **「real（真超級週期 + HBM 封裝樽頸）」→ 生還。** HBM 受 CoWoS/先進封裝產能閘限係真、MU 直接持有；
  2026 短缺真（合約價、高盛「15 年最嚴重」）。呢截 red-team 冇打冧。
- **「de-cyclicalisation / cushioned floor（LTA 墊高盈利/股價地板）」→ 中彈。** 錨定事實三連：
  (1) RPO $1,000 億對應入帳緩衝僅 $10.2 億（總負債 3 倍嘅 backlog 唔喺表上）；
  (2) 管理層自己只承諾 visibility/volume、無 price floor；
  (3) 先例（2017 DRAM / GrafTech / Kyocera）一致顯示 take-or-pay 喺 glut 被 reset/走數。
  「地板」被降級為**量嘅能見度**，唔係**價/盈利/股價嘅地板**。而 verdict 個字眼 `cushioned` 高估咗價地板。

**額外決定性發現（用系統自己嘅公式，非辯方砌故事）：memory-supercycle 觸犯 §4a single-source cap。**
themes.yaml `sources:` 只有一條（`gooptions-trend-core`，tier 2）。§4a 定義：Tier-1 要**獨立擊中承重 claim**
先算第二源。實情：capex（供給回應頂，其實偏空）/ ttm_pe（估值）/ RPO（出自同一 gooptions #128）全部只掂**周邊事實**；
而我今日拉嘅 balance sheet（一手）**唔單止冇追認承重 claim，仲直接同「RPO 入表墊地板」矛盾**。
→ **冇任何獨立源追認去週期化承重 claim** → 應受 `min(raw, 0.30)` cap 綁。
（DESIGN §4a 行 102 本身已預告「memory 呢類現正違規嘅會向下修返合規」——red-team 只係一手確認咗個 cap 真係適用。）

**對應 rubric（§4b moat/growth 掛鈎）：**
- **moat 格：2 → 1.5。** 樽頸真（HBM/封裝）但**承重 claim（LTA→定價權結構化）未經 Level-2 生還**——
  §4b 明文：「moat 攞 2 分嘅前提 = 該格承重 claim 經 Level-2 red-team 且生還；齋引用最高 1.5」。
  LTA-定價權嗰半截中彈，故降 1.5。
- **growth 格：維持 1.5。** NAND-CMX 新 TAM 真，但 wiki 原本已為「LTA-if」打折至 1.5，判決一致，唔重複扣。
- 估值(1)/資本配置(1) 係機械讀數，不受 red-team 影響。

---

## 4. 建議（不執行）

| 欄位 | 現值 | 建議 | 理由 |
|---|---|---|---|
| moat subscore | 2/2 | **1.5/2** | 承重 claim 未經 Level-2 生還（§4b rubric 掛鈎） |
| base（Σ/8） | 5.5/8=0.69 | **5.0/8=0.625** | moat −0.5 |
| confidence | 0.38 | **0.30（觸 cap）** | 兩條獨立理由收斂：(a) single-source cap，冇 Tier-1 掂承重 claim；(b) 0.625×late penalty ≈ 0.31–0.34，再被 cap 壓到 0.30 |
| verdict | `real-but-late-cushioned` | **`real-but-late, volume-visibility-not-price-floor`**（或 `...floor-UNCONFIRMED`） | 「cushioned」高估價地板；量地板真、價地板未證 |
| kill_condition | 全 prose | **加一條可量化軸** | 合約價 QoQ 動能（useluminix 框架：<X% 或轉負即 flag）+ 2027 HBM 產能佔比（SK Hynix →40%）→ 令 kill_metrics.py 計到數，脫離純 prose |
| sources | 1 條 tier-2 | **維持 cap，或補真獨立源** | 現時冇任何源獨立追認承重 claim；balance sheet 一手驗證**失敗**（唔追認），唔可以拎嚟解 cap |

**淨效果**：confidence 0.38 → ~0.30，仍係「有相對強弱、細注、盯」嘅 late-cycle 讀數，但**唔再宣稱結構去週期化已成立**；
把「cushioned floor」由**結論**降級為**待 downturn 先能證偽嘅未決假說**。

**公平記錄控方做啱嘅**：thesis 本身**唔係天真 bull**——已判 late、confidence 只 0.38、kill 圍住 LTA scorecard、
已引 2017 先例、已標 peak-earnings 陷阱。red-team 冇推翻一個 naive 敘事，而係**收緊一個本身已審慎嘅晚週期 call**，
並用一手數據把「cushioned」個字嘅過度自信擠出嚟。

---

## 5. 協議 meta-review（§4b pilot 校準）

**最有價值嘅步：**
1. **§4a single-source cap 檢查**——最平、最決定性。誠實問一句「有冇 Tier-1 獨立掂**承重** claim（唔係周邊事實）」，
   即刻得出一個具體、可辯護嘅 confidence 修訂，全程零 bear theater。**建議列為 Level-2 red-team 嘅強制第一步。**
2. **一手 balance sheet 事實補全**（RPO $100B vs 入帳 $10.2 億）——正正係協調員要嘅「補全事實，唔係鬥氣」：
   一個數據點就把 verdict 個 `cushioned` 字眼證為過度延伸，唔使砌任何反面故事。
3. **平庸解釋測試**——乾淨咁證明兩假說上行段觀測等價 → 防止把去週期化當「已確認」入分。**高性價比。**

**低價值/浪費嘅步：**
- **insider 檢查**：晚週期高位內部人減持係常態、非 cluster，資訊量近零；只堪作「冇 cluster 買入追認」嘅弱佐證。
- **WebSearch bear case 有一半係「敘事風險」唔係「遺漏事實」**（MS「peak rate of change」、UncoverAlpha
  類比屬意見）。協調員中途校準（「反方必須錨事實，否則只算敘事風險」）**啱到核心**——我要主動篩走 9 條入面
  嘅 4–5 條意見/類比，只留錨定數字嗰啲。

**下次 red-team 其他 theme 要改：**
1. **web bear-hunt 要 scope 收窄**成「wiki 冇 cite 嘅事實」，唔係「任何 bear take」——否則 subagent 交返一半意見，
   浪費篩選成本。派工 prompt 應明寫「只要一手數據/日期/先例，唔要券商觀點」。
2. **加一個 checklist item**：「Tier-1 驗證係掂**承重** claim 定**周邊事實**?」——呢個區分係 source-cap 生死線，
   今次係最鋒利嘅一刀，但協議冇明文要 red-team 逐個 Tier-1 佐證去問呢句。
3. **kill_metrics 空軸嘅 theme 應觸發「補一條可量化軸」嘅建議**（如本檔動作 4 提嘅合約價 QoQ 動能）——
   純 prose kill 令夜班判唔到距離，係已知弱點，red-team 係補呢個軸嘅好時機。

---

## 附：本檔用到嘅一手驗證命令（可複現）

```
python thesis/kill_metrics.py --report                 # memory 無可量化 kill 軸
python thesis/corpus.py get transcript-MU-2026-03-18   # MU 管理層 SCA 措辭
python thesis/insider.py MU|SNDK|WDC                    # 內部人淨賣、無 cluster
# defeatbeta MU quarterly_balance_sheet：Deferred Revenue $1.02B vs Total Liabilities $33.4B
```
