# Phase-3 全局架構 + 執行 backlog【Fable 設計 session 總交付,2026-07-08】

> 五份 WS 規格嘅合成頂層。閱讀次序:本檔 → ws1(裁判)→ ws3(生命週期)→ ws4(早期偵測/儀錶盤)
> → ws2(危機 sleeve)→ ws5(表達注碼)。全部經設計 loop + adversarial self-review +
> 四個實證探測(constraint-language ✅ / insider-cluster ❌ / crisis event-study 修訂 / 80 源普查)。

## 1. 數據流(成部機器一張圖)

```
【發現層】(可以濫)                【收編層】(必須嚴)          【持倉層】
 gooptions 每朝自動抓 ──┐          Admission 閘(WS3):        B 型主題(≤7 錶/主題)
 constraint 掃描(季度)──┤          lint 機檢 + 4-KPI cited      ├─ ETF 籃(優先)
 altdata top-5 錶 ───────┼─> 候選 → + kill 寫死 + priced-in 閘 → ├─ 大型純 play
 agent 定期 sweep ───────┤          + 單源封頂 0.30              └─ 細價純 play ≤1/3(10x 位)
 用戶 idea ──────────────┘          + 儀錶盤 fan-out(WS4)      A 型危機 sleeve(WS2):
                                    + 即日入戰績簿               ARM(VIX>40)→ENTER(VIX<30)
                                                                 →63/126d 走;≤衛星10%
【記分層】(必須真,WS1)                     【反饋層】(必須狠)
 戰績簿(單一寫入者,超集 schema)            裁判 PASS → 解鎖全額
 ├─ 05:30 每日影相(log_predictions)         裁判 FAIL → 熔斷:部署上限 25%+凍結
 ├─ 05:50 自動回填到期答案(backfill,新)     kill 觸發 → T+1 離場+除牌
 └─ 裁判狀態機:PRELIMINARY→PASS/FAIL         過期 120d → 降級;beta 化 → 除牌
    (63d excess IC≥0.05,JSON 機讀)          meta-factor 預算 ≤ 衛星 50%(拆 AI 集中度)
```

**設計鐵則**:①每支箭 = 一個檔案 + 一個排程 job;②全機只有兩道人工閘(採納新「玩法類型」/
kill 事實判定);③右側入場係全系統風格(core 買企返 200SMA 上、危機買 VIX 見頂回落 —— 冇一度接刀);
④信任係賺返嚟(裁判未 PASS,注碼有鎖)。

## 2. 部件清單(邊嚿已有/邊嚿新建)

| 部件 | 狀態 | 出處 |
|---|---|---|
| themes.yaml + wiki + corpus + source-nodes | ✅ 已有 | 現行 |
| gooptions/transcripts 每日抓 + 隊列 | ✅ 已有(05:35/05:45)| 現行排程 |
| 戰績簿統一 + 回填 + 裁判狀態機 | 🆕 | WS1 |
| Admission lint / 退場 / meta-factor 預算 | 🆕 | WS3 |
| Constraint 掃描生產化 + 儀錶盤 retrofit + top-5 probe | 🆕 | WS4 |
| A 型 ARM/ENTER 狀態機 + runbook | 🆕 | WS2 |
| sizing.py(狀態機連動注碼)| 🆕 | WS5 |
| insider P0-c 接線(細價 12月版)| 🆕(方向已鎖)| WS5/ROADMAP A3 |
| Dashboard 一頁四格 | 需求已列,任務 6 實作 | WS5 §5 |

## 3. 統一執行 backlog(交日常 session;派工照 10-dispatch + 驗證不自驗)

**Batch 1|地基(1 個 session;唔做呢批,後面全部冇意義)**
1. WS1 全套:遷移 → 單一寫入者 → backfill → 狀態機 →(驗收:05:30 鏈行通、fixture 測 PASS/FAIL)
2. WS3 #1-2:themes.yaml 新欄(9 主題補齊,ai-capex 標 6 個)+ lint 擴充(驗收:壞 fixture 捉到晒)

**Batch 2|儀錶化(1-2 個 session)**
3. WS4 #1-2:constraint 掃描生產化 + 9 主題儀錶盤 retrofit(agent fan-out ×9)
4. WS2 #1-2:L5 補測(右側+naive worst-2)定案對象腿;ARM/ENTER 入 playbook_readout(警報行)
5. WS3 #3-4:集中度報表 + beta 化月檢
6. WS5 #1:sizing.py(讀裁判 JSON,熔斷 fixture 測)

**Batch 3|Probe 與接線(分批,隨財報季/數據節奏)**
7. Altdata top-5 逐個 probe(ISM 嗰個必須過「對 200SMA/VIX 增量」檢定先入)
8. TWSE 月度營收 job(記憶體鏈)
9. insider P0-c 接線(A/B 增量回測過 DSR 先接 —— ROADMAP A3 原驗收)
10. Dashboard(任務 6)用 WS5 §5 需求清單實作;任務 8 第一輪 sweep(≥50% 非 AI)用新機制行

## 4. 時間線(誠實版)

- **即刻可做**:Batch 1-2(機器起晒)
- **7 月底**:首批 21d 預測到期 → 回填開始有真數
- **~10 月**:63d 判決線 → 裁判出第一個似樣讀數;PASS 解鎖全額部署
- **下一單 VIX>40**(唔知幾時):A 型 sleeve 上膛狀態等緊
- **每季**:constraint 熱力表 + 儀錶盤刷新 + sweep 一輪新主題

## 5. 系統級 Top-3 缺陷(Phase-3 以外;用戶 2026-07-08 問「仲有乜大缺陷」嘅誠實答案)

| # | 缺陷 | 金額邏輯 | 修法(全部平)|
|---|---|---|---|
| 1 | ~~治理覆蓋率~~(**2026-07-13 已修,`thesis/crypto_governance.py`**):紀律只管 39% 資金(crypto 61% 無 kill 無階梯實數)| core α +$9k/年 vs ETH 一個 −30% 月 = −$62k | 已做:ETH 上行 ladder 落實數(用戶原有數字,$2,600/$3,500/$4,338)+ SOL 同款推導(標明「DERIVED」)+ ETH/BTC 比率裝錶。**刻意冇做**:下行/時間出口——`docs/2026-07-08_transition_plan.md` §8 已記低用戶 2026-07-08 知情後拒絕呢個(「唔再重提」),本次修法尊重呢個決定,唔重提 |
| 2 | **LEAP 定價模型風險**:α 估計 +6.5~+12.4 嘅 2 倍寬幅純因 30d→1y IV 映射未驗 | 直接影響 delta 檔位/premium 預算決策 | `playbook_readout` 已拉真鏈 → 加每日快照存盤(~20 行)+ 現價 spot-check model(策略檔 §7 原 to-do)|
| 3 | **數據單點 + 冇對數迴路**:yfinance 靜默腐爛風險(SIVE/停市後垃圾 IV 已見);冇 trade ledger = 執行漂移隱形、core 冇自己嘅裁判 | 一個 miss 咗嘅 200SMA cross = 該 cycle 全部 core edge | 05:30 批次加數據哨兵(新鮮度/跨源抽查/log 頂行警報);極簡 CSV 台帳 + 月度「實際 vs 保守α預期」對數 job |

→ 併入 backlog 做「**Batch H|系統加固**」(~2 個 session,可同 Batch 1-2 交錯)。

## 5b. 設計期烈士名單(俾證據殺咗嘅想法 —— 留檔防還魂)

- 「系統性震央+政策」做危機選股篩選(L3 輸 naive;政策做 context 唔做閘)
- Insider 群買做主題發現器(主題粒度十年零 fire)
- 行業級 HY 息差做主題溫度計(免費源根本冇產業切法)
- 社交聲量做擁擠計(數據源已收費化/死亡;改 ETF flows+bull 比率)
- 「sonnet 粗讀層」(材料太短,慳唔到錢加複雜度 —— 用戶捉嘅)
