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

- **meta-factor 上限口徑**:現行 sizing.py 用「50% × budget」;PRELIMINARY 期同「總部署 ≤50%」撞
  同一數字 → ai-capex 實際佔部署 ~56%(略過 50% 意圖)。至 PASS(全額)閘正確咬到。修法:
  meta-factor 上限改用「50% × 實際總部署上限」而非 budget。低優先(冷啟動注碼細,6 主題已攤開)。
