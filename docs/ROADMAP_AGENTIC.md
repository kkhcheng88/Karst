# Karst 全自動 Agentic 投資決策系統 — 實施計畫

> 版本:2026-07-03 v1(制度化 session 產出)。活文件:每完成一個 Phase 更新狀態欄。
> 依據:`2026-07-03_strategy_methodology_review.md`(P0-P3 編號沿用)、
> `2026-07-03_dashboard_decision_experience.md`、`ARCHITECTURE.md`、
> `~/.claude/playbooks/`(agent 調度與驗證制度)。

## 零、「全自動」的定義與邊界(先釘死,防漂移)

**全自動 = 決策管線零人工提示地日常運轉**:
每日掃描 → 出卡 → 紙上成交 → 帳本更新 → dashboard/警示 → 週稽核 → 月校準報告,
全程無人推動。**人只保留三件事**:
1. **下單執行**(鐵律:決策支援,人執行;改此邊界 = 用戶明示決策,agent 不得代決)
2. **新 thesis 類型的採納閘**(DESIGN 原設計的唯一嚴格人閘)
3. **制度變更**(invariants、sizing 上限、kill-switch 閾值)

**反漂移警句**(Charter):持續加結構層可能是方法論救贖式拖延;edge 在 Phase 3 的
forward IC ≥ 0.05,其他一切是管線。每個 Phase 都有時間盒。

---

## Phase A — 修接線(1–2 週)|狀態:未開始

把已驗證但沒接上的訊號接上,把斷的迴路接通。全部是審查 P0 項。

| # | 任務 | 對應 | 驗收條件 |
|---|---|---|---|
| A1 | 統一 track_record schema、`log_predictions` 併入每日排程、實作 outcome 回填 job | P0-3 | jsonl 每日以完整 schema 增長;+21d 首批到期自動回填實現報酬 |
| A2 | credit 軸(HYG/LQD)+ `trend_risk_divergence` 進 `context.py`/`schemas.py`;與 `fragile` 整併 | P0-2 | 回放 2018-Q4/2020-02/2022-10,背離旗標全部亮起;先探測 HYG/LQD 資料覆蓋 |
| A3 | insider 改接 21d 戰術 tilt(擇時側,帶衰減);廢除或明文降級 `conf_eff`;修 docstring | P0-1 | A/B 增量回測(long-only mirror、21d horizon)過 DSR 後才接線;不過就 display-only |
| A4 | `forward_ic.report()` 程式化判定(PRELIMINARY/PASS/FAIL + JSON 輸出) | P0-4 | auditor agent 可機讀 |
| A5 | 衛生:`spine/__init__` docstring、`lint.py` 進每日排程、殭屍欄位渲染或刪 | P3 | lint 每日自動跑;殭屍欄位清單歸零 |

**驗證紀律**(全 roadmap 通用):每個任務按 `~/.claude/playbooks/10-dispatch.md` §6
——做的 agent ≠ 驗的 agent;驗收報告必須有 file:line/命令輸出證據。

## Phase B — 閉決策迴路(2–4 週)|狀態:未開始

讓系統的每日輸出變成可度量的戰績,而不是一疊沒有後果的卡片。

| # | 任務 | 驗收條件 |
|---|---|---|
| B1 | **持久化價格庫**(parquet + as-of manifest;`KARST_DATA_SOURCE=store`) | 全部 exp_*.py 可離線重跑;實驗檔記 manifest hash |
| B2 | **Paper ledger v0**:每日卡片 → 規則化紙上成交(次日開盤價)→ 合併 NAV;sleeve registry(tier-1 期權/tier-2 做多/現金=乾火藥) | 連續 10 個交易日全自動記帳;每筆可溯源到當日卡片 |
| B3 | **乾火藥政策**:恐慌觸發部署/貪婪出場(✅ 已驗規則)接進現金 sleeve | 部署事件與 `exp_mr_roundtrip.py` 規則一致 |
| B4 | **tier-1 指標面板**(memory `tier1-metrics-decision`):時序 IC/資本效率/PnL÷曝險/conditional Sharpe/DD/正交性,月更 | 不含 Jensen alpha;基準矩陣 SPY vs SPY、QQQ/SPMO vs {自己,SPY} |
| B5 | Dashboard:決策條/翻轉警示/兩軸完整版/系統戰績條(姊妹篇 §6 步 1-6) | 5 分鐘決策流程可走完;戰績條由 B2 餵 |
| B6 | 稅務參數(jurisdiction=HK 預設,⚠️ 需用戶確認)進 capstone 級比較 | 「vs 無腦 QQQ 稅後」有真數字 |

## Phase C — Agentic 運維(第 2–3 個月)|狀態:未開始

用 agent 角色接管維護迴路。全部走 playbooks 調度制度(模型選擇/升降級/回報合約)。

| 角色 | 觸發 | 職責 | 模型 |
|---|---|---|---|
| **Scanner** | 每日 cron(已有) | 確定性腳本:掃描/記帳/渲染——不需要 LLM,保持腳本化 | — |
| **Analyst** | 事件觸發:財報逐字稿發布、insider cluster-buy、翻轉警示 | thesis INGEST(`/thesis` skill 已有):抽 KPI、更新 confidence(引用齊全)、記預測 | sonnet,判斷密集升 opus |
| **Auditor** | 每週 | lint + IC 狀態(A4 的 JSON)+ invariants 檢查 + 殭屍欄位/schema drift + 戰績 vs 基準摘要 → 週報落檔 | sonnet;異常升 opus |
| **Librarian** | 語料批次到達 | corpus build、source nodes、wiki 斷鏈修復 | haiku/sonnet |

驗收:**連續一週 thesis 維護零人工提示**;週稽核報告自動出現在 repo;
每個 agent 產出都有獨立驗收(不自驗)。

**LLM 判斷漂移防護**(誠實極限:confidence/cycle_stage 是 agent 判斷):
(a) lint 強制引用完整性;(b) 重大 confidence 變動(>0.15)需第二個 fresh agent
覆核並留雙簽紀錄;(c) 校準數據(A1)是最終裁判——判斷跑贏不了 forward IC。

## Phase D — 校準與擴編(第 3–6 個月)|狀態:未開始

| # | 任務 | 前置 |
|---|---|---|
| D1 | confidence 校準映射(≥20 筆到期 outcome 後):confidence 分桶 vs 實現命中率/超額,產出校準曲線與修正函式 | A1 跑滿 |
| D2 | **IC 裁決**:forward IC 對 0.05 的正式判定(A4 狀態機 + 3-6 個月資料)→ go/no-go 落檔 | A1/A4 |
| D3 | 危機 sleeve(Type-A:VIX>40 + 被打爛系統板塊)規格+回測(walk-forward 標準) | B2 registry |
| D4 | Supercycle sleeve 產品化(bottleneck thesis → 可配置 sleeve) | D2 若 PASS |
| D5 | 組合 optimizer v1:風險貢獻 sizing + 正交性輸入 + 每 sleeve 上限;目標函數 = 組合 Calmar/Sharpe | B2/B4 |
| D6 | 事件引擎薄版(FNSPID base rates)——時間盒 2 週,超時即停 | D2 若 PASS |

**D2 是分水嶺**:IC FAIL → 不擴編,回到 thesis 品質與覆蓋(或誠實承認質性層也無 α,
系統定位改為「風控完善的 beta 底座 + 部署計時器」——這也是有價值的結論)。

---

## 風險與 kill-switch(全期有效)

| 風險 | 防護 |
|---|---|
| 資料源脆弱(Yahoo 限流/defeatbeta 落後) | B1 價格庫 + 新鮮度 banner + staleness >2 交易日 → 掃描標記 degraded,決策條變灰 |
| 回撤斷路 | 紙上組合 DD > 歷史 MaxDD ×1.25 → auditor 立即出異常報告 + 凍結新倉建議 |
| 兩軸背離 | 背離持續 >10 交易日 → confidence 全域 temper(審查 P0-2 的下游) |
| 過擬合蔓延 | 新規則一律 walk-forward+DSR(P1-5);反建議清單(審查 §三)常查 |
| agent 判斷漂移 | Phase C 雙簽 + 校準裁判;所有 agent 產出走不自驗制度 |
| 制度腐化 | `~/.claude/playbooks/40-maintenance.md` 精簡輪與退化偵測 |

## 依賴圖(關鍵路徑)

```
A1(校準資料流)──→ D1(校準)──→ D2(IC 裁決)──→ D4/D6
A2(兩軸)──→ B5(dashboard 完整版)
B1(價格庫)──→ B2(ledger)──→ B3/B4/B5(戰績條)──→ D5(optimizer)
A4 ──→ C(auditor)
```
最先動手:**A1**(每天不修就流失一天校準資料)與 **B1**(一切重現性的地基)可並行。
