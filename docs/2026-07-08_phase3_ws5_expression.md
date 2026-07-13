# Phase-3 WS5 規格 —— 表達與注碼(confidence → 錢)【設計定稿,待執行】

> 設計:Fable(2026-07-08)。核心立場:**信任係賺返嚟 —— 裁判未 PASS,注碼有鎖。**
> 用戶取態:衛星 = 組合 30%(起步 ~$41k,crypto 階梯觸發會增大);偏好 ETF 表達;
> 10x 願望由「主題內細價純 play + A 型期權表達」承載,唔係 registry 撒網。

## 0. 入場紀律(用戶 2026-07-09 追問「late 主題要唔要擇時」定案)

**兩個極端都錯:TA 擇時(已殺,無 alpha)/ 不惜代價買晒(late 主題 = 買喺 priced-in 頂)。**
正確 = **基本面 cycle_stage + sizing 做「timing」,唔用 TA:**

| cycle_stage | 入場方式 |
|---|---|
| **early**(constraint-language 早捉、未 priced-in)| 可爽快建倉(edge 在於早)|
| **mid** | 分段建倉,趁弱加 |
| **late / priced-ahead**(現時 9 主題全部)| **細注 + 分段 + 唔追高 + 等擁擠/估值消散**(主題 note 明寫「don't chase」嗰啲照跟)|

即:satellite 入場 = fundamental-cycle 驅動,唔係 RSI 驅動;early 主題先「買得爽」,late 主題「買得慢」。
呢個係 WS4 早期偵測嘅回報所在 —— 捉得早 = 可以喺 priced-in 前用細擇時代價建倉。**現時全 late →
全部細注耐性入,冇一個「今日買晒」。**

## 1. 冷啟動注碼規則(裁判 = PRELIMINARY 期間;而家至 ~10 月)

1. **單主題上限** = min(confidence × $20k, $15k)。例:AI-電力 0.33 → $6.6k;記憶體 0.38 → $7.6k。
   (你會發現呢啲數細過早前 power-basket 講嘅 $10-12k —— 係,冷啟動期壓細;裁判 PASS 先鬆。)
2. **衛星總部署 ≤ 衛星預算 50%**(其餘現金/T-bills 等訊號)。
3. **表達次序**:①主題 ETF 籃(power-basket 係範本:揀腿零重疊、費率、流動性)→
   ②大型純 play 股 → ③**每主題最多一隻細價純 play(10x 位),佔該主題注碼 ≤ 1/3,必須
   有自己嘅 kill**。
4. 同一 meta_factor 合計 ≤ 衛星 50%(WS3 §4)。
5. **A 型危機 sleeve 另設獨立預算 ≤ 衛星 10%,平時 100% 現金**(WS2 event study 後由 20%
   下調 —— 證據級別 LOW 要匹配;兩段式 ARM→ENTER 規則見 WS2 規格;期權表達可用)。

## 2. 解鎖階梯(裁判狀態 → 注碼)

| 裁判狀態 | 衛星部署上限 | 單主題上限 |
|---|---|---|
| PRELIMINARY | 50% | min(conf×$20k, $15k) |
| **PASS** | 100% | conf × 衛星預算 ÷ Σconf(按校準後信心比例分)|
| **FAIL(熔斷)** | **25%,新倉凍結** | 只減不加;等 session 覆盤 |

## 3. Kill 執行紀律

Kill 事實成立(夜班/日間 session 判定)→ **T+1 收市全部離場,冇裁量**;戰績簿記
`kill_fired: true`;主題 delisted(WS3)。「等多陣睇吓」= 呢個系統要消滅嘅嗰種人類行為。

## 4. 接線現況(forensics 已核)

`backtest/spine/providers.py:40-51` 讀 themes.yaml 5 field —— 接口唔使改;WS3 新欄係加法。
insider `conf_eff`(P0-c)修法:按已定案方向(細價 12 月 portfolio tilt)—— 屬執行 backlog,
方向唔准再改。

## 5. Dashboard 需求清單(餵任務 6,一頁四格)

1. **今日行動格**:core playbook 判定表(已有 log,搬上屏)+ A 型警報燈(平時灰,VIX 分級變色)
2. **主題面板**:每主題 confidence/cycle_stage/status/距 kill 幾遠/部署額;meta_factor 集中度條
3. **裁判成績表**:狀態機(PRELIMINARY/PASS/FAIL)+ matured 進度 + IC 走勢
4. **隊列格**:`_PENDING_ANALYSIS.md` 未剔項 + gooptions 未 ingest + 過期主題警告

## 6. Self-Review(反駁過乜)

| 挑戰 | 裁定 |
|---|---|
| 「ETF 優先同 10x 願望矛盾」| 唔矛盾:ETF = 主題嘅倉,細價純 play = 主題嘅刺刀(≤1/3、有 kill);10x 嘅數學係唔對稱 payoff × 重複落場,唔係注碼大 |
| 「冷啟動 50% 現金係 drag」| 係,呢個 drag 係買緊「唔俾未經證實嘅信心分揸大錢」;裁判 10 月開始出真判決,鎖係有期徒刑唔係無期 |
| 「熔斷 25% 太狠?」| FAIL = 150+ 樣本證明信心分冇料 —— 嗰陣時繼續全額部署先係狠(對自己)|
| 「A 型 20% 預算會唔會太大」| 平時 100% 現金零成本;觸發先入場,且 WS2 數據會定實際注碼(等 event study)|

## 7. 執行 backlog

| # | 項 | 驗收 |
|---|---|---|
| 1 | `thesis/sizing.py`:讀 themes.yaml + 裁判 JSON → 輸出每主題目標注碼表 | 手核 9 主題數啱;熔斷 fixture 測試 |
| 2 | Kill 執行 SOP 寫入 playbook 級文檔(衛星版 runbook)| 存在 + 連 dashboard 需求 |
| 3 | insider P0-c 接線(12 月版,A/B 增量回測過 DSR 先接)| = ROADMAP A3 原驗收 |

**時間盒:≤ 1 個執行 session(sizing.py 半日)。**

## 8. 已知 refinement(2026-07-08 實作後驗證發現,非阻塞)

- **meta-factor 上限口徑(2026-07-13 已修)**:舊版 sizing.py 用「50% × budget」;PRELIMINARY 期同
  「總部署 ≤50%」撞同一數字 → ai-capex 實際佔部署 ~56%(略過 50% 意圖)。**已修**:新增
  `total_cap_for_status()` 做單一事實來源,`apply_meta_factor_cut()` 嘅 cap 基準改用呢個(PRELIMINARY
  期即 25% of budget,唔係 50%)。實跑驗證:ai-capex cap 由 $20,500 收緊到 $10,250。

## 9. Sizing v2 shadow(2026-07-13,`docs/2026-07-12_fable_investment_logic_review.md` P0-1)

**唔取代 v1**——`python thesis/sizing.py --v2-shadow` 喺 v1 表之後多印一個 conf×magnitude
兩軸表做並排比較,兩者都落 log 做 shadow A/B(兩季後先決定用邊個)。規格:
`score = conf × log₂(magnitude_mid)`,`conf<0.25` 唔食 magnitude 加成;top-6、每注 ≥$4,000
floor(唔夠就$0,唔重新分配俾其他候選);event-binary(`cycle_stage=event-driven`)固定
$1,000 微注、唔入排名;集中度 cut 喺**選倉之後**先套用(修 v1 嘅反排序:mf-cap-basis fix
單靠自己修唔到跨組排名倒轉,呢個先係真.修法)。

**magnitude 輸入現況(2026-07-13 實跑)**:15 個主題入面得 `ai-power-grid` 有真.per-node
magnifier rubric 數據(5 nodes),其餘 14 個用 `V2_DEFAULT_MAGNITUDE_MID=2.0` 佔位——
**呢個直接令 v2 依家淨部署到 $6,443(cap 嘅 31%)**,因為大部分主題共用同一個 placeholder
magnitude,score 太接近,冚喺 ai-power-grid 後面冇一個夠得着 $4,000 floor。呢個唔係 bug,係
per-node schema 推廣未做(P2 #12:photonics→advanced-packaging→memory→space)嘅直接後果——
推廣落去先會令 v2 嘅部署額同分辨力反映真實。

**【2026-07-13 同日更新:P2 #12 已推廣到 5/15】** batch 1(photonics 6 nodes、advanced-
packaging 6 nodes)+ batch 2(memory 4 nodes、space 6 nodes)已落 themes.yaml(理據檔
`backtest/results/2026-07-13_pernode_batch{1,2}_draft.md`)。**Shadow A/B 觀察項(大腦審查
記錄,兩季 shadow 期要盯)**:space-satellite 混合 magnitude = 5.35(6/10 隻 ticker 屬
binary node,ticker-count 加權拉高)而 conf 0.28 啱啱過 V2 gate(0.25)→ v2 影子可能將
space 排上高位;但 space 同時處 KILL-WATCH(趨勢已破 200SMA),且 `is_event_binary()` 讀
theme 級 cycle_stage(space="early"≠"event-driven"),theme 級 binary 微注處理唔會觸發。
「趨勢破位但 v2 排名高」呢個 artifact 正正係 shadow 期要驗嘅嘢——如果兩季後仍出現,v2 落地
前要考慮:(i) binary node 佔比高嘅 theme 用 damped 混合,或 (ii) v2 疊 trend gate。而家
唔改 formula(shadow 嘅意義就係唔郁住,睇佢自己表現)。oil-gas-energy 按 Fable 指示唔
node 化,拆分方案 = `docs/2026-07-13_oilgas_split_proposal.md`(待用戶拍板)。

**【2026-07-13 batch 3 之後第二個 shadow artifact:地板 × 平分數 → 零部署】** per-node
推廣到 14/15 後,scores 反而變得好平均(0.20-0.68 窄帶),top-6 每份按比例攤 ~$3.4k,
**全部低過 $4,000 地板 → 除 event-binary micro 外零部署($1,000/$20,500)**。用真
magnitude 數據示範咗 Fable spec「top-K + 不重分配地板」喺平分數 regime 下嘅結構缺陷:
分數愈平均,部署愈接近零——同「集中化」嘅設計原意相反。修法候選(shadow 完先郁):
(i) 地板改「取唔夠就縮 K」(top-6 → top-3 直到每份過地板);(ii) 地板後重新歸一化
(違反而家嘅不重分配原則,要 Fable 級覆核);(iii) 接受零部署做「冇夠說服力嘅集中機會
= 唔部署」嘅 feature。紙上擂台(paper_league.py)會令呢個 regime 嘅代價透明。
