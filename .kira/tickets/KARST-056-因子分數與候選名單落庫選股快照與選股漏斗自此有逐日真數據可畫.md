---
id: KARST-056
title: 因子分數與候選名單落庫:選股快照與選股漏斗自此有逐日真數據可畫
type: task
createdAt: 2026-08-28
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-050, KARST-054]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
closed: 2026-08-29
---

## 工作內容

策略詳情頁的選股快照與選股漏斗自此畫得齊原型全貌。KARST-050 發現 factor_value 與 active_setup 零列,運行產物只有淨值/持倉/委託,逐股因子分數與「範圍 → 基本面關 → 技術關 → 持倉」各層候選名單無從填,現時只畫兩層並註明。範圍:引擎每次運行把各決策日的候選名單各層與逐股因子分數落到運行產物(parquet,與淨值同一目錄,入運行編號的產物清單),策略詳情頁改讀真數據;不改運行編號的組成;示例運行重跑後編號不變。

## 驗收條件

- [x] 兩個示例運行重跑後產物多出候選名單各層與逐股因子分數,運行編號逐位不變
- [x] 策略詳情頁選股快照顯示逐股因子分數,漏斗畫齊有數據的各層,不再顯示「未有逐日因子分數」
- [x] 既有測試全過,karst verify 清白

## 結果

引擎每次正式運行,除了淨值/持倉/委託三條序列,另外落兩份 parquet 到同一個運行目錄:
`candidates.parquet`(逐個決策日、逐層的候選名單)與 `factor_scores.parquet`(逐個決策日、
逐隻的分數與名次),另加一份 `selection.json` 作索引與內容雜湊。策略詳情頁的選股快照與
選股漏斗自此全部讀這兩份真數據,不再是兩層加一句「未有逐日因子分數」。

**產物擺位偏離了票面寫法,要記一筆。** 票上寫「入運行編號的產物清單」,實際做法是照
查帳序列那一套旁掛(`selection.json` + parquet),沒有加入 `run_artifact` 的產物清單。
原因有二:一、`RUN_ARTIFACT_KINDS` 住在 `store.py`,本票的檔案分工明文不准碰;
二、那張清單的合約寫明「三條缺一不可」,把一份可有可無(舊運行本來就沒有)的產物塞進去,
會令那道閘由「驗三條齊不齊」變成講大話。旁掛一樣有內容雜湊、一樣入 `karst verify`,
`verify_selection()` 對得住。

**運行編號。** 因子混合等權逐位重現 `run-024df83fb4891c89`,三條原有序列的檔案時間戳都
沒有動過。趨勢波段出了 `run-2120914a42d21911`,不是票面的 `run-7e3b498e086bdb88`——
不是本票造成:參數集「示例-KARST-028」在本票開工前已被另一條線改到第 6 版
(`entry.breakout_lookback_days` 由 50 逐版改到 59),本票跑回 N=50 於是出第 7 版。
同一份碼連跑兩次,編號逐位相同;加不加痕跡都不影響編號(痕跡不入 `run_fingerprint`)。

**掃描格不落痕跡。** 自動收痕跡那一段以 `origin == FORMAL_RUN` 為閘。一幅掃描動輒四千格,
格格存一份逐日名單,磁碟先爆;而掃描頁看的是格與格之間的成績差異,不看逐日名單。

**數據。** 趨勢波段:2,929 個決策日,候選名單 32,902 列(範圍 29,290 / 技術關 2,036 /
入選 1,576),分數 57,559 列(突破幅度、計劃賠率);入選 1,576 與該次運行報稱的入場訊號
1,576 張對得上。因子混合:47 個換倉日,候選名單 376 列,分數 188 列(目標比重),
47 × 4 = 188 對得上。

**分數的名。** 沒有把不是因子分數的數字叫做因子分數。趨勢波段那個因子登記的尺是 boolean,
因子混合根本沒有排名步驟,所以分數表帶一欄 `score_name` 講明每個數字實際是什麼
(突破幅度 / 計劃賠率 / 目標比重;排名再平衡路徑則是該因子的真名)。

**漏斗的語意是「到達該層」。** 規則類策略當日入選往往得 0-1 隻,但持倉是幾星期前開的 3 隻,
照字面畫會出現持倉多過入選。仍在場的名早已過齊每一關,所以每一關的名單與持倉取聯集,
提示文字寫明「當日過關,或早前過關後仍在場」;逐行的狀態欄照舊誠實分持倉/入選/觀察/未過。

**實開頁面核對過。** 本機起網頁殼,瀏覽器實開兩頁:
`/strategy?run=run-2120914a42d21911` 見漏斗四層(範圍 10 → 技術關 3 剩 30% → 入選 3 →
持倉 3)、快照表多出「突破幅度」「計劃賠率」兩欄連名次、狀態欄分持倉/未過;
`/strategy?id=1&run=run-024df83fb4891c89` 見三層(範圍 4 → 入選 4 → 持倉 4)、「目標比重」
一欄、基期列註明「分數與名單出自決策日 2026-06-30」。按漏斗任何一層,快照表即篩到該層名單,
數目與該層的數對得上。

**順手修一處對不齊。** 快照表是固定欄寬佈局,加了分數欄之後,沒有指定寬度的「名稱」被壓到
只剩一個字。分數欄改為按數量收窄(1 欄 96px / 2 欄 80px / 3 欄以上 72px),其餘欄位一併
收緊,名稱回到 100px 以上;全名照舊在 title 上。沒有加減欄位,不是改設計決定。

**改動的檔**:新增 `karst/engine/funnel.py`、`tests/test_selection_trace.py`;改
`karst/runs/registry.py`、`karst/runs/__init__.py`、`karst/engine/`(rules、rule_runner、
selection、runner、contracts、__init__)、`karst/web/api_strategy.py`、
`karst/web/static/strategy.js`、`karst/strategies/`(trend_swing、factor_mix)、
兩個示例運行的實驗目錄。`karst/data/`、`store.py`、`schema.py`、`experiments/snapshot_ids.py`
一個字都沒有動。

**跑過的測試檔**(按用戶指示只跑所涉檔,不跑全庫):`test_selection_trace.py`、
`test_web_strategy.py`、`test_web.py`、`test_web_overview.py`、`test_runs.py`、
`test_engine_rules.py`、`test_engine_ranking_rebalance.py`、`test_factor_mix.py`、
`test_trend_swing.py` —— 50 項全過。改動落定之前另跑過
`test_engine_audit.py`、`test_engine_costs.py`、`test_engine_exit_reentry.py`、
`test_cadence_weekly.py`、`test_risk_layer.py`、`test_web_series_missing.py`、
`test_web_concurrency.py`、`test_sweep.py`、`test_metrics.py`,亦全過。
`python -m karst.gateway verify` 全庫清白。

## 留言
