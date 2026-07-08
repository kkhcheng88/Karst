# Phase-3 WS4 規格 —— 早期偵測與主題儀錶盤【設計定稿(四探測實證後),待執行】

> 設計:Fable(2026-07-08)。實證底:`results/2026-07-08_constraint_language_probe.md`(✅ 主管道)
> /`_insider_cluster_probe.md`(❌ 陰性)/`_altdata_census.md`(80 源普查 + top-5)。
> 核心立場:**早期訊號嚟自「行為」唔係「敘事」** —— 公司喺電話會嗌短缺、實體量轉向,
> 全部行喺分析員寫文之前。

## 1. 發現/監察輸入 —— 實證裁決表

| 管道 | 裁決 | 依據 |
|---|---|---|
| **Constraint-language 掃描**(財報電話會措辭計分)| ✅ **主管道,升做生產 job** | MU 受限分數 2023-12 轉正,**早過 gooptions 敘事 ~17 個月**;第二波早 8 個月;WDC/STX 落後 MU 3-6 季(→ MU 係鏈頭錶);defeatbeta 覆蓋 76-83 季 |
| Insider 群買做發現器 | ❌ **唔建**(誠實陰性)| 主題粒度十年零 fire(記憶體/電力);單 insider 已知唔可靠;insider 留守已證崗位(細價 12月 tilt = P0-c)。尾巴:GICS sub-industry 粒度未試,低優先 |
| **Altdata top-5 probe**(pre-registered,普查收斂)| 🔬 逐個 probe | ① 3-2-1 crack spread(EIA,油氣主題)② EIA-930 電網逐時(AI-電力)③ ISM New Orders−Inventories(FRED,宏觀閘 —— 要先驗同 200SMA 閘有冇冗餘)④ Cass Freight/AAR 鐵路(實體物流)⑤ **TWSE 台廠月度營收**(法定披露、免費免 key —— 記憶體鏈月頻確認器)|
| T2 社交聲量 | ⚠ 改道 | Reddit/X 數據源 2023 後收費化/死亡 → 擁擠計改用:thematic ETF 資金流 + 新 ETF 上市 + 報告 bull 比率(已有)+ Google Trends(仲免費)|
| 已測死家族 | 標死唔回收 | GEX/credit-做大市軸/breadth LEVEL;**但同數據換 mirror 可以重問**(行業級息差喺免費源根本冇 —— 普查證實,呢條線閂埋)|

## 2. 主題儀錶盤協議(Theme Instrument Panel)—— 本 WS 核心機制(用戶 2026-07-08 設計輸入)

**觸發**:①admission 必經一步 ②季度刷新 ③主題轉 watch/meta-factor 警報時。

**Fan-out 四步(opus 級 agent 做)**:
1. 由 wiki 頁 4-KPI 拆出承重 claim;
2. 每個 claim 問「呢個 claim 變強/變弱,邊個公開數字最先郁?」—— 按 T1 實體量/T2 注意力(倒轉=擁擠)/T3 事件機率三類 fan out(零件庫 = altdata_census;主題特有新錶回饋落庫);
3. 每個錶寫規格:來源/API、頻率、**領先定滯後(判斷+理由)**、方向映射、**閾值語義(乜讀數=確認、乜讀數=靠近 kill)**;
4. 落 themes.yaml 機器可讀 `instruments:` 塊 + wiki 章。

```yaml
instruments:
  - {name: MU-RPO, class: T1, source: 10-Q, freq: Q, direction: up=confirm, maps_to: kill-watch}
  - {name: TWSE-monthly-rev-chain, class: T1, source: TWSE-OpenAPI, freq: M, maps_to: cycle_stage}
  - {name: memory-ETF-flows, class: T2, source: etf-flows, freq: W, direction: up=crowding, maps_to: priced-in-gate}
```

**監察迴路**:API 型錶 → 夜班 job 自動記讀數、超閾值亮燈;文件型錶(RPO 呢啲)→ 掛財報日曆由 session 讀。讀數更新:cycle_stage 證據、**距 kill 幾遠(由散文變儀錶)**、擁擠餵 priced-in 閘。

**護欄**:每主題 3-7 個錶封頂;每個錶必須映射到具體 claim 或 kill;T2 一律倒轉解讀;讀數只入 confidence 輸入,唔准直通注碼;原型 = `ai-capex-macro-risk.md` 五盞燈(手工版已運作)。

## 3. Constraint-language 生產化規格

- 頻率:每季財報季後批跑(+ 記憶體/電力鏈重點股出 transcript 即掃);
- 覆蓋:由 15 隻擴到 themes.yaml 全部 ticker + 每主題鏈頭股(MU 型領先者優先);
- 輸出:板塊×季度熱力表 + 突變警報 → 入 `_PENDING_ANALYSIS.md` 式隊列;
- 詞表紀律:anti-noise(新詞要跨 ≥3 公司 + ≥2 季覆現先升級);雙向(受限/鬆動)必須並列;
- 已知風險:詞義歧義(「allocation」可指資本配置)—— 抽查樣本人手核,誤判率落檔。

## 4. Self-Review(反駁過乜)

| 挑戰 | 裁定 |
|---|---|
| 「17 個月 lead 係單一案例(記憶體),會唔會係彩?」| 成立一半:電力鏈同方向但對照弱;所以 top-5 probe 逐個 pre-registered 驗、生產 job 出嘅每個警報都入戰績簿 —— 用 forward 紀律補 backward 樣本薄 |
| 「儀錶盤會變成 agent 每季燒錢嘅儀式」| 每主題 3-7 錶封頂 + 零件庫複用 + 只有 admission/季度/警報三個觸發;唔係常開 |
| 「ISM 分項會唔會同 200SMA 閘冗餘(又一個 credit 軸故仔)?」| 正正係 probe 規格第一條驗收:對 200SMA/VIX 做增量檢定,冇增量就唔入 |
| 「T2 改用 ETF flows 夠唔夠?」| 擁擠計唔使完美,要一致:ETF flows + 新 ETF 上市 + bull 比率三個一齊睇,方向一致先算訊號 |

## 5. 執行 backlog

| # | 項 | 驗收 |
|---|---|---|
| 1 | constraint scanner 生產化(擴 ticker、季度 job、警報隊列)| 首份熱力表落檔;警報進隊列 |
| 2 | 現有 9 主題儀錶盤 retrofit(agent fan-out ×9,零件庫用 census)| themes.yaml 每主題 instruments 3-7 個 + lint 過 |
| 3 | Top-5 probe 逐個跑(pre-registered 規格喺 census 檔)| 每個一份 results 檔;ISM 嗰個要過增量檢定先入 |
| 4 | TWSE 月度營收 job(記憶體鏈先行)| 月度自動抓 + 入儀錶盤 |
| 5 | 夜班 job 加「儀錶讀數 + 亮燈」段 | playbook_log/夜班 log 見到錶 |

**時間盒:#1-2 一個執行 session;#3-5 隨後分批。**
