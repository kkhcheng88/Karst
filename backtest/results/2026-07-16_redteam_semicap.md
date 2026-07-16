# Level-2 Red-Team：semicap-equipment（半導體後段老化測試 / AEHR）

- 日期：2026-07-16
- 協議：thesis/DESIGN.md §4b（FALSIFY 升級：INGEST 係審判，唔係歸檔）+ §4c（三通道分流）
- 角色：辯方 red-team。**職責 = 事實補全（搵敘事冇展示嘅重大事實），唔係反對表演。**
  每條反方必須錨喺可引用事實/數據；砌唔到錨定事實 = 標「敘事風險」，唔算 finding。
- Pilot + photonics 教訓已納入：反面狩獵只收一手（數據/日期/公告/法律先例）；強制回答
  「Tier-1 佐證掂嘅係承重 claim 定周邊事實？」;必做 balance-sheet 檢查（deferred revenue vs backlog）。
- 約束：只新增本檔，冇改 themes.yaml / wiki / 任何現有檔。
- 對象特性：single-name thesis（唯一表達 [[AEHR]]）、solvency_flag=true（EBITDA≤0）、細價股高波動、
  cycle late、confidence 0.20（全批最低）。

---

## 1. 控方主張摘要

老化測試（burn-in / 後段可靠度測試）係 AI 晶片浪潮嘅**橫切收費站**——唔賭邊顆晶片贏，
只要「貴到不容許出貨後才壞」嘅晶片變多，每顆出貨前都要過呢道測試關卡。
**承重 claim = 「[[AEHR]] 係真收費站——結構性、耐久、橫切嘅賣鏟人（Sonoma 封裝級 + FOX-XP 晶圓級），
$41M Sonoma 一手單 + 創紀錄 backlog 係呢個結構需求嘅背書，唔係單一客戶訂單 lumpiness」**
（verdict: `real-tollgate-but-froth-thin`，confidence 0.20，cycle late，全批最低、單名極端 froth）。

承重 claim 拆三個子命題逐個審：
- (i) **係真收費站**（moat/樽頸：橫切、唯一達量產規模、有定價權）
- (ii) **結構需求耐久**（非單一客戶/單一終端市場嘅週期 lumpiness；backlog = 真能見度）
- (iii) **froth + 內部人紅旗**（cycle/priced-in：呢個係 wiki 已捕捉嘅 downside，本次核對現況）

**時效關鍵：wiki 最後更新 2026-07-08，但 [[AEHR]] FY Q4 2026 業績 2026-07-14（本審前兩日）剛出**
——本次狩獵嘅承重新事實大部分嚟自呢份一手業績 + 法說。

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道（Tier-1，最鋒利）**

- **【必做 balance-sheet 檢查】deferred revenue vs backlog——pilot/photonics 形態第三度複製。**
  defeatbeta `quarterly_balance_sheet`（PYTHONUTF8=1，stmt.df()，16 季至 2026-02-28）:
  - **AEHR balance sheet 冇 RPO row；Current Deferred Revenue 2026-02-28 只得 $1.857M**、
    Non-current Deferred Revenue $0.053M——合共 **~$1.91M 入帳緩衝**。
  - 對比控方 backlog:wiki 引 $50.9M;**2026-07-14 新業績更報 year-end backlog $80.6M、
    effective backlog $100.6M**（AEHR PR，2026-07-14）。即 **入帳緩衝 / backlog ≈ 1.9/80.6 ≈ 2.4%**
    ——**~97.6% 嘅「backlog」係披露式訂單（bookings，講稿），唔係現金背書嘅合約負債。**
  - **更硬嘅一刀:deferred revenue 唔單止細，仲係停滯/萎縮——**2023-08 有 $6.114M，之後
    2024-08 $3.541M → 2025-05 $1.981M → 2025-11 $0.443M → 2026-02 $1.857M,**一直喺低單位數
    百萬徘徊,而同期 backlog 由 ~$50M 爆到 $80.6M**。若係「客戶用現金鎖多年供應」嘅真收費站,
    deferred revenue / customer prepayment 應該隨 backlog 升;佢冇。**客戶冇預付鎖單。**
  - 判定:同 pilot「MU RPO $100B 唔喺 balance sheet」、photonics「COHR/LITE deferred≈0」**同一形態,
    第三度落刀命中**。「創紀錄 backlog = 耐久能見度」呢個承重 claim,一手 balance sheet 顯示係
    披露式 backlog,唔係入帳緩衝。

- **定價權簽名相反:毛利隨量壓縮,唔係收費站形態。** defeatbeta `quarterly_gross_margin`:
  2023-11 **51.1%** → 2024-11 40.1% → 2025-05 30.3% → 2025-11 **25.8%**(低點)→ 2026-02 32.7%。
  **毛利大致腰斬(51%→26–33%),隨營收下跌同步跌 = 純營運去槓桿,睇唔到定價權。**
  直接對照 photonics 龍頭:COHR 毛利 9 季 30.3%→37.7%、LITE 16.2%→44.2%(**擴張**)。
  真收費站喺需求週期低位仍應守得住/擴毛利;AEHR 毛利方向同收費站敘事**相反**——
  呢個係承重 (i) 嘅定價權半句最硬嘅 Tier-1 反證。

- **營收滾落 + CEO 親認 lumpy,悶故事一手坐實。** defeatbeta `quarterly_income_statement`:
  季度營收 2023-11 **$21.43M** → 2024-02 $7.56M(單季 -65%)→ … → 2025-11 **$9.88M**
  (peak-to-trough **-54%**);全年 FY26 $50.0M vs FY25 $59.0M(**-15%**,AEHR PR 2026-07-14)。
  TTM operating income **-$14.1M**、TTM EBITDA **-$10.6M**(坐實 solvency_flag EBITDA≤0)、
  TTM net income -$7.1M。**橫切「每顆貴晶片都要過」嘅收費站,唔應該因單一終端市場(SiC 車用)
  週期就單季 -65%、全年 -15%。** 呢個係教科書式單一終端市場訂單 lumpiness。

- **注意一次性:2024-05 季度 net income +$23.86M 係遞延稅估值備抵回沖(Tax Provision -$20.74M)嘅
  one-off,唔係營運盈利。** 免得有人誤以為 AEHR 曾經穩定賺錢——營運層面近 6 季全部蝕。

- **靠發股填蝕:非堡壘。** `quarterly_cash_flow`:FY26 下半經發股籌 ~$19.6M(2025-11 financing +$9.78M、
  2026-02 +$9.83M;Common Stock Issuance 2026-02 $10.2M)填營運蝕損;股數 29.77M→30.95M(**稀釋**)、
  TTM FCF -$5.4M。**mitigant:無有息債、cash $36.9M、capex 細($74K/季,一手)** = 捱得過谷底,但靠攤薄。

- **存貨雙義(同 COHR WIP 形態,但更淡):** 存貨 ~$41M vs TTM 營收 $50M(≈ 1.5 年存貨)、
  Raw Materials 高企 $31M——可讀作 Sonoma ramp pre-build(利多)或 SiC 下行滯銷(利空)。
  **但 Finished Goods 近乎零($0.69M)= 冇塞渠道**,張力比 photonics COHR 淡,標記不判死。

**(b) 外部一手(WebSearch + 2026-07-14 業績/法說,篩走意見文)**

- **FY Q4 2026(2026-07-14 一手)——季度 beat,全年跌:** Q4 營收 **$18.8M**(+33% YoY)、
  GAAP 轉正 net income $1.4M($0.04)、non-GAAP $3.6M($0.11)、股價印後 **+29%**;
  **record bookings $60.7M**(+>500% YoY)。(AEHR PR / 8-K ex-99.1,2026-07-14)
- **FY2027 指引 GIVEN 且進取:$130–150M 營收(+160–200%)、18–22% non-GAAP 稅前利潤率,
  但明言 contingent(「assuming achievement of stated revenue targets」)。** ——即成條增長腿係
  **前瞻承諾,未入 P&L**。(AEHR PR,2026-07-14)
- **$41M Sonoma hyperscaler 單:未 slip、亦未認列。** 「expected to be delivered this year to the
  OSAT of our hyperscale customer, based in Taiwan」;CFO 指 Q2 FY27(非 Q1)先係出貨大季
  ——大單仍喺 backlog,認列推到 H1 FY27。(Q4 FY26 法說逐字稿,2026-07-14)
- **客戶集中度:由單一 SiC 客戶轉向少數 AI 客戶(分散化,反而幫控方 (ii) 一半)。**
  Q4 **三個客各佔營收 >10%**(兩 AI、一數據中心光收發);**SiC 佔 FY26 營收跌到 <5%**
  (兩年前 >95%)、**AI 加速器/CPU/網通 ~71%**。(Q4 法說,2026-07-14)。歷史單一大客戶
  ~90% 嘅集中風險,而家由一個 SiC 客戶擴散做一手 AI 客戶群——**「單一客戶」版嘅悶故事正在減弱,
  但集中度仍高(3 個 >10%),FY26 10-K 精確集中度表未上 EDGAR = 開口誠實標記。**
- **競爭者切入:狩獵兩手空空(有效判決,幫控方)。** 搵唔到 Advantest/Teradyne/Cohu/inTEST
  任何一則 dated 公告切入晶圓級/封裝級量產老化測試;「佢哋唔做 AI 功率級全晶圓 burn-in」係
  **敘事(narrative-only),唔算 finding**。唯一浮現嘅真對手係 SiC 領域嘅 **SemiNexus Test**
  (中資、遷冊馬來西亞),而 **AEHR 喺台灣 SiC 客戶對決贏咗佢**(技術/成本/信譽)。(Q4 法說,2026-07-14)
  ——「唯一達量產規模」moat 未被一手證偽。
- **CPO/矽光子測試需求:真、非純願景(幫控方 (i)):** 領先矽光子客戶已量產且**續單**
  (過去一年 + 本財年再有 follow-on,全自動晶圓級 burn-in for AI optical I/O);**第二個新客戶
  (「global leader in networking」)2025-11 先接觸,已訂 2 套 9-wafer FOX cell + 2 FOX NP**。
  (Q4 法說,2026-07-14)。真採用(已出貨/已訂單),但客戶未具名、第二客 <1 年,仍早。
- **SiC/GaN:off-trough 拐點一手:** 過去一個月(2026-06/07)收 ~$8M 新 SiC 晶圓級 burn-in/WaferPak 單
  (領先 SiC 客戶為中國 EV 產能追單 + 一間「全球最大車廠」)(AEHR PR「$8M SiC…」,2026-07);
  管理層:「encouraging signs of recovery in SiC」、客戶今年開始俾「real numbers, real forecasts」。
  GaN 係新腿:「world's first 300mm GaN wafer-level burn-in」、十幾個 GaN WaferPak sampling(仍 pre-volume)。
- **內部人(SEC Form 4,~180 日;最乾淨嘅 bear-tilt 事實):** CEO Gayn Erickson **5 年 0 買 / 13 賣**;
  **2026-04-10 公開市場賣 152,824 股 @ ~$70.58(~$10.8M),疑非 10b5-1**,再申報 90 日內意圖再賣 ~96k 股
  (~$6.8M)。**印後(2026-07-15)嘅內部人動作係例行 RSU 代扣稅處置(非公開市場賣),CEO 另獲 RSU/PSU 授予**
  ——**呢點比 wiki「印前六日賣」嘅敘事略淡,誠實記錄。** 全窗**零公開市場買入**。

**(c) 平庸解釋 vs 結構解釋(悶故事測試預演,詳動作 3)**

- CEO 逐字:**「One of the challenges in our business is that it is always going to be lumpy… we do not
  want to put money in place and infrastructure that is permanent because the business is cyclical.」**
  (Q4 法說,2026-07-14)。**悶故事(單一大單 lumpiness + 週期)由 CEO 一手講出口。**

### 動作 2 — Steelman 反方(非 wiki/文章自供,事實錨齊)

**「$80.6M record backlog 唔係耐久收費站能見度,而係一張未認列大單 + 幾個客戶 ramp 撐起嘅前瞻賭注,
承重嘅係 lumpy 訂單,唔係結構性多年 toll」**:
1. **一手 balance sheet:入帳緩衝(deferred revenue)得 $1.91M = backlog 嘅 2.4%,且停滯萎縮**
   ——客戶冇用現金鎖多年供應;真收費站嘅上游客戶會預付(對照 photonics COHR 自己預付 $22M 鎖 AXT)。
2. **一手毛利:51%→26–33% 隨量壓縮 = 冇定價權**;收費站應喺低位守毛利,佢冇。
3. **一手營收:全年 FY26 -15%、單季曾 -65%;CEO 親口「always lumpy… cyclical」** = 悶故事錨齊。
4. **FY27 +160–200% 指引 100% 靠前瞻**:$41M 單未認列(推到 Q2 FY27)、僅 3 個 >10% 客戶 ramp,
   任何一個延單/砍單即傳導;指引自己標 contingent。
5. **先例(本系統已三連):** pilot MU「RPO $100B 唔喺 balance sheet」、photonics「COHR/LITE deferred≈0」,
   加本次 AEHR——「披露 backlog ≠ 入帳緩衝」呢類 claim 喺本系統已**三連敗**。

呢條 steelman 唔需要「AI 需求係假」或「AEHR 技術唔掂」——就算技術真、AI capex 全真,
backlog 長度都可以 ≠ 真實耐久需求長度,而承重嗰筆重量喺一張未認列大單度。

### 動作 3 — 平庸解釋測試

**悶故事:「AEHR 係一隻做利基老化測試設備嘅細價週期股,營收由少數大單/單一終端市場(SiC 車用)
驅動,而家 AI 換咗個新終端市場再嚟一轉單」——可以解釋幾多?**
- 解釋到:全年 -15%、單季 -65%/+33% 嘅劇烈波動、毛利隨量升跌、record bookings 由一張 $41M 大單撐、
  backlog 爆但 deferred revenue 唔升——**全部係「少數大單驅動嘅利基設備股」嘅標準現象,
  CEO 自己都認 lumpy/cyclical**,唔需要「結構性耐久橫切收費站」呢個更強假設。
- 解釋唔到(結構故事嘅額外證據,幫控方):
  1. **技術唯一性未被證偽**:狩獵搵唔到大廠(Advantest 等)dated 切入;AEHR 對 SemiNexus 贏頭對頭;
     矽光子第二客戶自發上門——「唯一達量產規模」係工程/競爭事實,唔係純週期現象。
  2. **需求基礎正真實分散**:SiC>95%→<5%、AI→71%、3 個 >10% 客戶——「單一客戶 lumpiness」嘅
     最尖版本(依賴一個 SiC 客戶)正在減弱。
- **可區分觀測(datable):**
  1. **FY27 H1(~2026 底–2027 春)= 天然實驗**:$41M Sonoma 單認列 + FY27 +160–200% 指引兌現與否。
     若如期認列 + 多客戶 ramp → 結構故事贏;若延單/砍單/指引下修 → 悶故事贏。
  2. **deferred revenue / customer prepayment**:若始終唔隨 backlog 升 → 「多年鎖單」一直只係講稿。
  3. **毛利**:量回升時毛利收唔收得返上 40%+ → 定價權真定假嘅照妖鏡。
- 結論:**子命題 (ii)「結構需求耐久」大部分可以齋用悶故事解釋(區分要等 FY27 H1 實驗);
  子命題 (i)「係真收費站」嘅技術/競爭半句悶故事解釋唔到(有工程 + 競爭事實背書),
  但定價權半句被一手毛利反證。** (iii) froth 係現況核對,見動作 4。

### 動作 4 — kill 距離(逐條)

| kill 軸 | 當下事實 | 距離判定 |
|---|---|---|
| **內部人續賣不止**(反向聰明錢不轉弱) | CEO 5 年 0 買 13 賣、2026-04 賣 ~$10.8M(疑非 10b5-1)+ 意圖再賣 ~$6.8M;**但印後 2026-07-15 係例行 RSU 代扣稅、非公開市場賣**,且 CEO 獲新 RSU/PSU | **未實質轉弱、但亦未新惡化**;紅旗仍在(零公開市場買入),惟印後動作較 wiki 敘事淡——**中距離,方向未定** |
| **backlog 認列破功**($41M/大單延期、大客戶砍 Sonoma、單客戶集中傳導) | $41M 單未 slip 但未認列(推 Q2 FY27);FY27 +160–200% 全靠前瞻 + 3 個 >10% 客戶 ramp;backlog $80.6M 但 deferred≈$1.9M | **未觸發、但槓桿最高嘅一軸**:FY27 H1 = 第一個可證偽窗口(~2 季內);deferred revenue 停滯 = 早期警戒 |
| **競品切入解構「唯一」**(Advantest/TER/COHU/INTT 切封裝級量產老化測試) | 狩獵零 dated 切入;AEHR 對 SemiNexus(SiC)贏頭對頭 | **未觸發、距離遠**;本次一手狩獵反而**加固**呢軸(競爭者缺席) |
| **froth-unwind**(AI-capex 打嗝即放大重挫) | 印後 +29%、β3.27;**但 FY27 指引 $130–150M 令 forward P/S 由 ~64x(trailing)降到 ~20x(guided)**——froth 若指引兌現會被 de-rate | **持續有效**,同 [[ai-capex-macro-risk]] 聯動;惟估值 downside 被新指引部分緩衝(前提:指引兌現) |

---

## 3. 判決:**分岔(§4c)——已-priced 收費站生還兼加固,未證嘅耐久 magnitude 腿中彈**

按 §4b 校準 + §4c 三通道:判決標準 = 承重 claim 面對補全後嘅事實集企唔企得住。逐子命題:

- **(i) 「係真收費站」——技術/競爭半句生還兼加固,定價權半句中彈。**
  技術唯一性(唯一達量產規模晶圓級 + 封裝級 burn-in)未被一手證偽——競爭者零 dated 切入、
  對 SemiNexus 頭對頭贏、矽光子第二客戶自發上門、SiC $8M 拐點單。**呢半句悶故事解釋唔到,有工程 +
  競爭事實錨,補全後更硬。** 但**「定價權」半句被 Tier-1 毛利直接反證**(51%→26–33% 隨量壓縮,
  同收費站形態相反),moat 因此封頂喺 1 分、上唔到 2。
- **(ii) 「結構需求耐久」——分岔核心:已-priced 部分證實,耐久 magnitude 腿未證兼中彈。**
  市場已知(已-priced)嘅部分 = AEHR 係真實、技術獨特、有真訂單嘅 burn-in 供應商(所以先炒到 +8x)——
  **呢部分一手加固**(record bookings $60.7M、客戶由 SiC 單一客擴散到 3 個 AI 客、FY27 進取指引)。
  但 thesis 真正押注嘅**耐久橫切 magnitude**(compound 到 $130–150M+ 兼持續)**係前瞻賭注,未入 P&L**:
  FY26 營收實際**跌 -15%**、$41M 單**未認列**、FY27 +160–200% 全靠 contingent 指引 + 3 個客戶 ramp、
  **CEO 親口「always lumpy… cyclical」**、backlog $80.6M 但**入帳緩衝得 $1.9M(2.4%)且停滯**。
  ——耐久 magnitude 腿**中彈**。
- **(iii) 「froth + 內部人紅旗」——維持,但兩面誠實更新。**
  紅旗仍在(CEO 5 年 0 買 13 賣、4 月賣 ~$10.8M 疑非 10b5-1、零公開市場買入);
  但**印後 2026-07-15 內部人動作係例行 RSU 代扣稅,非公開市場拋售**(較 wiki 敘事淡),
  且**FY27 指引令 forward P/S 由 ~64x trailing 降到 ~20x guided**,極端 froth 嘅估值 downside
  被部分緩衝(前提:指引兌現)。呢個係本次唯一淨利多嘅估值面事實,誠實記錄,唔誇大。
- 附:**「披露 backlog ≠ 入帳緩衝」呢把刀,pilot MU / photonics COHR-LITE / 本次 AEHR 三連命中**
  ——應正式升格做 INGEST checklist 常設一問。

**Tier-1 佐證掂承重定周邊(強制回答):**
本次 Tier-1(balance sheet + income statement + gross margin)**直接掂到承重 claim,且方向為負**:
backlog 唔係現金背書(打 (ii))、毛利隨量壓縮(打 (i) 定價權)、營收 FY26 跌(打 (ii) 耐久)。
而 wiki 原標「已驗 ✅」嘅 Tier-1($41M 單/內部人賣超對到 IR/SEC)**驗嘅係周邊事實**
(「有呢單嘢」「有人賣」),**唔係承重機制**(「呢單嘢係耐久 toll 定 lumpy 訂單」)——
同 pilot 完全同型:佐證掂周邊,唔掂 duration。

---

## 4. 建議(不執行;郁數留返日間 confidence 迴路)

**§4c 三通道機械分流(分岔 → 唔靠酌情調 confidence 數字):**

- **通道 1(subscore,入公式):** growth 格 1.5 → **1.0**。未證嘅耐久 magnitude 腿對應 growth 格:
  rubric「機制真但兌現中/部分靠未證嘅下一階段」= 1 分——FY26 營收實際跌、兌現全靠 FY27 前瞻指引,
  符合 1 分而非 1.5。moat **維持 1**(技術/競爭半句補全後更硬 = 頂住,但定價權半句被毛利反證 = 上唔到 2,
  兩力大致抵銷)。capital **維持 0.5**(capex 紀律在、但營運蝕 + 發股稀釋)。valuation **維持 0**
  (GAAP 全年蝕、指引未兌現、印後仍高;forward P/S ~20x 係緩衝但屬未證前瞻,唔加分)。
  → 新 subscores = moat 1 + capital 0.5 + valuation 0 + growth 1.0 = **2.5/8 = 0.3125 base**。
- **penalty:** cycle late + 單名極端 froth,惟叢內 0% bull(無分析師共識搶跑)為 mitigant,維持 wiki 口徑 **~0.55**。
  → **confidence_raw = 0.3125 × 0.55 ≈ 0.172**。single-source(#087/#150 同批事實)cap 0.30 **唔綁定**
  (0.172 < 0.30)。→ **confidence:0.20 → ~0.17**。
- **通道 2(cap 資格,binary):** **唔脫 single-source cap。** Tier-1 掂到承重但**方向為負**,
  且 corpus 仍實質單源(#087/#150 同批)——冇「Tier-1 獨立擊中承重 claim(正向)」,不符脫 cap 條件。
- **通道 3(magnitude 加成,sizing 層):** node 標 **`magnitude_unconfirmed: true`**
  ——「耐久橫切 toll compound 到 $130–150M+」呢條 magnitude 腿由前瞻指引撐、Tier-1 未兌現。
  **sizing v2 對呢個 node 收起 magnitude 加成**(回落 confidence-only 基準注碼)。呢度先係分岔嘅
  真正殺傷力落腳點——唔喺 confidence 數字(細郁),喺「唔俾佢憑 FY27 潛在倍數加碼」。

**verdict:維持 `real-tollgate-but-froth-thin`**——判決結構未變,但 wiki 措辭應更新(留日間迴路):
1. **必加 FY Q4 2026(2026-07-14)一手**:季度 beat($18.8M/+33%/GAAP 轉正)但全年 FY26 -15%($59M→$50M)、
   record bookings $60.7M、backlog $80.6M/effective $100.6M、FY27 指引 $130–150M(contingent);
   $41M 單未 slip 未認列(推 Q2 FY27)。
2. **記 balance-sheet 檢查結果**:deferred revenue $1.91M = backlog 2.4% 且停滯 →「披露 backlog ≠ 入帳緩衝」
   (pilot/photonics 同型,第三度)。
3. **記毛利反證**:51%→26–33% 隨量壓縮 = 定價權半句未立(對照 photonics 龍頭毛利擴張)。
4. **記客戶分散化**(SiC>95%→<5%、AI 71%、3 個 >10% 客)= 「單一客戶」悶故事版本減弱,但集中仍高。
5. **內部人更新兩面**:紅旗仍在(0 買 13 賣)但印後係例行 RSU 代扣稅、非公開市場拋售(較舊敘事淡)。
6. **標 `magnitude_unconfirmed: true`**(FY27 耐久腿);wiki 加 red_team 段記錄邊條腿未證(lint 要求)。

**kill 軸微調建議:**
- 「backlog 認列破功」軸應把**基準錨定喺 deferred revenue 停滯 + $41M 單 Q2 FY27 認列 checkpoint**,
  而非 backlog 名目金額(名目 backlog 已由 $50.9M 爆到 $80.6M 但入帳緩衝冇動,用名目做基準會遲報)。
- 新增早期警戒標記(非 kill):毛利量回升時收唔返 40%+、deferred revenue 持續 ≈backlog 2%、
  FY27 H1 客戶 ramp 進度、內部人是否恢復公開市場拋售。

**sources cap 註記:** 本次 Tier-1 掂承重但方向為負,**不構成脫 cap 嘅獨立第二正向源**;
整叢仍實質單源(#087/#150 同批)——照 §4a/§4c 定義 cap 維持。

---

## 5. Meta-review(一句)

本次 red-team 最有價值嘅唔係「壓低」——反而係**兩面都補全咗**:一邊 balance-sheet 檢查第三度證實
「披露 backlog ≠ 入帳緩衝」+ 毛利反證定價權 + CEO 親認 lumpy(承重耐久腿中彈);另一邊競爭者缺席、
客戶真分散、矽光子第二客自來、FY27 指引 de-rate 估值(已-priced 收費站生還兼加固)。
呢個正正係 §4c「分岔」要嘅精度:**confidence 數字只細郁(0.20→~0.17),真正嘅紀律喺 sizing 層——
`magnitude_unconfirmed` 令「搏 FY27 倍數」嗰部分唔准加碼**。而「披露 backlog ≠ 入帳緩衝」三連命中,
確認應升格做 INGEST checklist 常設一問。
