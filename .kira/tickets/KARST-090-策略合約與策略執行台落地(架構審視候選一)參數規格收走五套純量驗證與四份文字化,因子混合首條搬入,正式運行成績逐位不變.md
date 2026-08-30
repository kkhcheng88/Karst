---
id: KARST-090
title: 策略合約與策略執行台落地(架構審視候選一):參數規格收走五套純量驗證與四份文字化,因子混合首條搬入,正式運行成績逐位不變
type: task
createdAt: 2026-08-30
risk: medium
model: opus
fits: 多程
approvalRequired: false
dependsOn: [KARST-087]
claimedBy: agent-090
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

源自 research/2026-08-30-architecture-review-backend.md 候選一(D-043),設計以 research/2026-08-30-strategy-layer-design/design-A-strategy-contract.md 為骨架,嫁接 design-B 的三件(見同目錄 design-judge.md 第三節)。完成後:(1) 新增 karst/executor/contract.py,載 StrategyContract 協定(宣告 strategy_type、funnel_stages;方法 param_spec、factor_specs、needs_entities、plan)與值型別 ParamSpec/ParamField/FactorSpec/EntityRequest/RunRequest/EnginePlan(TargetPlan 與 RulePlan 二擇一的聯合);plan 是純函數,不開庫不讀檔不 import 第三方引擎。(2) 新增 karst/executor/executor.py,載 Executor,對外只掛 register / run / rejudge 三個方法(sweep 留給 KARST-091),register 與 run 共用私有 _execute_cell;一切寫入經唯一入口。(3) 風控取值收進參數規格當普通可掃軸,RunRequest 不設獨立 risk 格(D-008 第 3 條);參數規格內每一格都要掃得到、一格預設值都沒有(D-009 第 7 條);參數集自報「已對齊／示例」(D-038)。(4) 五套純量驗證(trend_swing.py:277 _as_int、:284 _as_float、factor_rotation.py:466 _check_tilt、:473 _check_lookback_days、engine/rules.py 的 _fraction/_positive)與四份參數文字化(sweep/factor_mix.py:98 weight_text、sweep/factor_rotation.py:96 param_text、:114 point_slug、SweepPoint.slug)收成 ParamSpec 一份正本,文字化口徑須與現行逐位相同。(5) 因子混合搬入:刪 register_factor_mix(factor_mix.py:376)、record_factor_mix_run(:671)、run_factor_mix(:609)的引擎樣板(遲到 import 與 RankingRebalanceParams 填空格那兩段);留 resolve_exposures(:468)、factor_mix_schedule(:513)、factor_mix_targets(:539)、factor_mix_selection_trace(:578)。(6) 新增 tests/doubles/engines.py,把四份散落的假引擎(test_engine_ranking_rebalance.py:384、test_engine_rules.py:396、test_factor_rotation.py:82、test_macro_drivers.py:172)收成兩個;新增全倉第一個 conftest.py。不造假定義庫,測試照舊起臨時 sqlite 真庫經唯一入口寫。要留的測試:test_sweep.py 的判讀與格、test_runs.py、test_risk_layer.py、test_selection_trace.py、test_engine_rules.py、test_engine_ranking_rebalance.py(含 :344 _cadence_defaults)、test_engine_audit.py:230、三條策略本體的計算測試。要刪的測試:test_factor_mix.py 的登記與落痕編排斷言,以及 :676 _code_symbols 配 :706 _weight_defaults 那份 ast.parse 原始碼文本斷言(改為斷言參數規格宣告的格數等於掃描格認得的軸數、每格有值域無取值)。驗證方式:因子混合的既有正式運行以執行台重跑,運行編號與八項成績指標逐位相同;全部 12 條 origin='formal' 的正式運行一條都不得變號。行號以 2026-08-30 為準,可能飄移,按內容找。動庫前備份到 C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-090.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 karst/web/static/ 與 prototype/;不 commit。

## 驗收條件

- [ ] 策略合約與策略執行台落地,因子混合經 Executor.register/run 走完一次正式運行;全部 12 條既有正式運行重跑後運行編號與八項成績指標逐位相同(測試:逐條比對舊 fingerprint)
- [ ] 參數文字化與純量驗證各只剩一份正本;參數規格宣告的格數等於掃描格認得的軸數,每格有值域無取值,風控三格在內(測試:缺一格拒收、多一格拒收、值域不合拒收、換倉節奏無預設)
- [ ] tests/doubles/engines.py 與 conftest.py 已建,四份假引擎收成兩個;只跑所涉測試檔;備份已做

## 結果

## 留言
