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

### agent:agent-090 · 2026-08-30 11:22
六項工作內容全部落地,三條驗收條件全部剔得到。下面按「新增了什麼、刪走了什麼、13 條運行比對、跑了哪幾個測試檔、開放點」五節交代。

\## 一、新增的模組與介面

**`karst/executor/contract.py`(策略合約,新檔)**
- `StrategyContract` 協定:宣告 `strategy_type`、`funnel_stages`、`engine_path`;方法 `param_spec()`、`factor_specs(snapshot_id)`、`needs_entities(params)`、`plan(request)`。
- 值型別:`ParamSpec`、`ParamField`、`FactorSpec`、`EntityRequest`、`ResolvedEntity`、`FactorVersionRef`、`RunRequest`,以及 `TargetPlan` 與 `RulePlan` 二擇一的引擎計劃(`ENGINE_TARGETS` / `ENGINE_RULES`)。
- `plan` 是純函數:不開庫、不讀檔、不 import 第三方引擎(D-007 第 3 條)。
- 錯誤型別:`MissingParameter`、`UnknownParameter`、`ParameterOutOfRange`、`UnresolvedTicker`、`EntityNotInPanel`、`DuplicateExposureEntity`、`MissingRequiredInput`、`PlanShapeViolation`、`EngineNameMismatch`。

**`karst/executor/executor.py`(策略執行台,新檔)**
- `Executor` 對外只掛 `register` / `run` / `rejudge` 三個方法(`sweep` 按票留給 KARST-091);`run` 與日後的 `sweep` 共用私有 `_execute_cell`,一切寫入經唯一入口。
- 四個模組級函數供搬遷中的舊路徑轉引,亦是驗證用的入口:`register_setup(gateway, contract, *, strategy_name, snapshot_id, param_set_name, values, alignment, description=None)`、`engine_for(contract, engine)`、`resolve_entities(store, request, *, on_date, known_entity_ids=())`、`simulate_plan(engine, panel, plan, *, engine_name)`。
- `simulate_plan` 是**全倉唯一**兩條引擎路徑分岔的地方,`RankingRebalanceParams` 那段填空格由此收成一處(原本散在 `run_factor_mix` 裡)。
- `rejudge` 做了靜態方法:重判不碰庫、不碰引擎,執行台那三件家當(唯一入口、運行庫、快照根)一件都用不着。換判讀口徑之前,先用**舊口徑**對回落檔那份判讀,對不上就不出新判讀(KARST-047)。

**`tests/doubles/engines.py`、`tests/doubles/__init__.py`(新檔)**——四份散落的假引擎收成兩個:`RecordingEngine`(目標權重路徑)、`RecordingRuleEngine`(規則路徑)。

**`tests/conftest.py`(全倉第一個,新檔)**——`writer_name`(**刻意不 autouse**,免得靜靜改動本票不准跑的測試檔的行為)、`gateway`、`store` 三個 fixture;不造假定義庫,照舊起臨時 sqlite 真庫經唯一入口寫。已為 KARST-093 留位。

**`tests/test_executor.py`(新檔)**——補三件別處碰不到的:重判自檢、計劃形狀當場拒收、漏斗層宣告以外的選股痕跡拒收。

\## 二、一份正本:五套純量驗證與四份文字化

**純量驗證**收進 `karst/executor/contract.py`:`check_positive` / `check_fraction` / `check_ratio` / `check_count` / `check_integer` / `check_number`。原本那五套現在只是轉引——
- `karst/strategies/trend_swing.py` 的 `_as_int` / `_as_float` → `check_integer` / `check_number`
- `karst/strategies/factor_rotation.py` 的 `_check_tilt` / `_check_lookback_days` → `check_ratio` / `check_count`
- `karst/engine/rules.py` 的 `_positive` / `_fraction` / `_lookback` → `check_positive` / `check_fraction` / `check_count`

**文字化**收進同一份正本(`value_text` 配 `TEXT_AUTO` / `TEXT_FOUR_PLACES` / `TEXT_EIGHT_PLACES` / `TEXT_VERBATIM`;短名 `value_slug` / `point_slug` 配 `SLUG_PERCENT` / `SLUG_VERBATIM`)。四處轉引:`sweep/factor_mix.py` 的 `weight_text`、`sweep/factor_rotation.py` 的 `param_text` 與 `point_slug`、`sweep/grid.py` 的 `SweepPoint.slug`。**口徑逐位對過**:`quality25-value25-cadencequarterly`、`fallback-cash-cadence-monthly`、`0.25 / 0.1 / 0 / 1`、`0.0005 / 0.005 / 0`、`lookback_months6-modewinner-cadencemonthly`、`6 / 0.5 / true / x` 全部與落庫值相同。

\## 三、風控三格與參數規格

風控三格(`risk.per_trade_risk`、`sizing.max_position_fraction`、`risk.monthly_loss_cap`)由 `risk_fields()` 出,**進參數規格當普通可掃軸**;`RunRequest` **無**獨立 `risk` 格(有測試斷言簽名裡沒有這個字)。參數規格內每一格自報值域、**一格取值都沒有、一個預設值都沒有**;換擋頻率亦是一格(`SLOT_CADENCE`),沒有預設。已加測試:規格宣告的格數 == 掃描格認得的軸數(5 格),以及缺格 / 多格 / 出界 / 換擋頻率無預設四種拒收。

\## 四、因子混合搬入(刪走了什麼)

- **刪** `register_factor_mix`(登記)與 `record_factor_mix_run`(落痕)——兩者的職責由 `Executor.register` / `Executor.run` 接走。
- **刪** `run_factor_mix` 裡的引擎樣板:遲到 import 與 `RankingRebalanceParams` 填空格那兩段。`run_factor_mix` 簽名不變,現在只是一層薄殼。
- **新增** `FactorMixContract`(策略合約實作)與純函數 `factor_exposures(...)`;`resolve_exposures` 簽名原封不動(測試靠它),內部改為 `resolve_entities` + `factor_exposures` 的轉接。
- **留住** `factor_mix_schedule`、`factor_mix_targets`、`factor_mix_selection_trace`,一行未改。
- 掃描起點 `ensure_factor_mix_setup` 簽名亦原封不動(十幾處呼叫點在本票範圍外),內部改為呼叫 `register_setup` 並明寫 `alignment=SAMPLE`。
- **刪** `tests/test_factor_mix.py` 的登記與落痕編排斷言,以及 `_weight_defaults` 那份 ast 原始碼文本斷言。
- `CostedEngine` 與 `FactorMixJob` 未動——KARST-091 的票管住它們。

\## 五、13 條正式運行的比對結果

**兩層證據,結論:一條都沒變。** 全程只讀,庫先複製一份出來再驗,一句都沒寫回倉。動庫前已備份至 `C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-090.bak`。

1. **身份層**:13 條 `origin='formal'` 的正式運行,逐條由庫內身份重算 fingerprint 與運行編號,**13/13 與落庫那個逐位相同**,零條變號。
2. **內容層**:因子混合那條正式運行 `run-024df83fb4891c89`,用新的策略合約 + 執行台**真的重跑一次引擎**(繞過查重),逐日淨值(2929 列)、逐日持倉、逐筆訂單(188 筆)**逐位相同**。
3. **八項成績指標**:13 條之中 11 條算得出,全部與落檔相同;餘下 2 條(`run-f4c162e5aac34347`、`run-728a01087531258f`)的 parquet 序列在 KARST-057 重建 `data/` 時已經不在倉裡,**與本票無關的既有狀況**,不是本次改動造成。

驗證腳本與結果檔落在本局工作區(`verify_090.py` / `verify_090.json`),需要重驗可以照跑。

\## 六、跑了哪幾個測試檔

一次過跑齊本票所碰的 14 個檔,**79 passed**:

`test_executor.py`、`test_factor_mix.py`、`test_factor_rotation.py`、`test_macro_drivers.py`、`test_engine_costs.py`、`test_engine_rules.py`、`test_engine_ranking_rebalance.py`、`test_engine_audit.py`、`test_sweep.py`、`test_runs.py`、`test_risk_layer.py`、`test_selection_trace.py`、`test_trend_swing.py`、`test_cadence_weekly.py`。

按派工指令,`tests/test_web*.py` 一個都沒有跑(它們直接打生產庫)。因子輪動與趨勢波段兩條既有路徑照樣行得通,測試全綠。

\## 七、開放點(交驗收人與下一程)

1. **D-038「已對齊／示例」目前只在記憶體裡,未落庫。** 落庫兩條路都會撞牆:當一格參數值 → 參數集內容變 → **運行編號會變**,13 條逐位不變那條就守不住;當 `param_set` 新一欄 → `content_digest` 變 → **全部既有寫入者簽章作廢**,`karst verify` 會全紅。現行做法是 `register_setup` 強制明寫 `alignment`(無預設值),結果掛在記憶體的 `Setup` 上。**要落庫的話需要一次遷移,建議另開票。**
2. **`rejudge` 的簽名與 design A 不同**:design A 是 `rejudge(batch_id, ...)`,但批次登記要到 KARST-091 才落地,所以現在收的是成績與格。091 接上批次登記之後應該補回。
3. **`TargetWeightsInput` / `CostedEngine` 的搬遷按票留給 KARST-091**;本票只把 `RankingRebalanceParams` 填空格收成一處,以保住運行成績逐位不變。
4. **票面寫 12 條正式運行,實際庫內是 13 條**;13 條全部驗過,全部不變。
5. `run-2120914a42d21911` 的八項指標與 `run-7e3b498e086bdb88` 完全相同(2.4983 / 0.1138 / -0.2084),**很可能就是 KARST-093 要清的那條測試污染**,留給 093 判。

\## 八、一條新策略現在要動幾多個檔

一個:寫一份策略合約(`param_spec` / `factor_specs` / `needs_entities` / `plan`),登記、參數驗證、標的解析、引擎呼叫、查重、落痕、成績、失敗判讀全部由執行台接走。

### agent:agent-090 · 2026-08-30 11:24
**問題**：參數集自報「已對齊／示例」(D-038)要不要落庫?本票內兩條要求互相打架:落庫就守不住「正式運行編號逐位不變」那條驗收條件。

**前文後理**：工作內容第 3 條要參數集自報已對齊／示例(D-038);驗收條件第 1 條要 13 條 origin='formal' 的正式運行重跑後編號與八項成績逐位相同。兩條同時滿足不到:(甲)把對齊標記當一格參數值 → 參數集內容變 → 運行編號一定變,13 條全部變號;(乙)把它做成 param_set 一條新欄 → 該表的 content_digest 變 → 全部既有寫入者簽章作廢,karst verify 會全紅。本票現行做法是折衷:register_setup 強制明寫 alignment(無預設值,漏填當場拒收),結果掛在記憶體的 Setup 上,未寫入庫。掃描起點(ensure_factor_mix_setup)明寫 alignment=示例。三條驗收條件在這個折衷下全部剔得到:13/13 運行編號與 fingerprint 逐位相同,因子混合那條連逐日淨值、持倉、訂單重跑後亦逐位相同;所涉 14 個測試檔 79 passed。

**建議**：我建議照現行折衷收貨,另開一張票專做落庫遷移。理由:對齊標記是一件治理資料,不是策略身份的一部分——它不應該改變運行編號,所以(甲)本身在概念上就是錯的。(乙)概念上對,但代價是一次簽章重簽,那是一件要獨立驗證、獨立備份的事,擠進本票只會令「逐位不變」那條驗收條件失去意義。

**選項**：
- 甲（建議）：照現行折衷收貨,另開一張票做 param_set 加欄 + 簽章重簽的遷移 —— 運行編號與既有簽章兩樣都保住;落庫這件事有自己的驗證與備份,值得一張獨立的票
- 乙：本票內即做 param_set 加欄與全庫簽章重簽 —— D-038 一次過落地,不留手尾;但要接受本票的「逐位不變」改為「編號不變、簽章全部重發」,驗收口徑要改寫
- 丙：維持記憶體版,不另開票,當 D-038 對登記入口的要求已經滿足 —— 登記時漏填 alignment 已經當場拒收,人為錯誤那條路已經封;但庫裡查不到哪個參數集是示例,日後看報告的人分不出

**要睇邊份稿**：
- research/2026-08-30-strategy-layer-design/design-A-strategy-contract.md
- research/2026-08-30-strategy-layer-design/design-judge.md

### agent:main · 2026-08-30 11:26
**裁決**：「已對齊／示例」標記不寫入參數集內容(不進運行編號雜湊、不動既有簽章);改為另一張經唯一入口簽章的旁表,按參數集編號記標記與對齊日期,另開 KARST-094 做。本票維持「登記時強制申報、不入庫」收貨。

**出處**：主腦(main)決定;依 D-038(示例參數不是現役,建置期對齊)與 KARST-026(運行編號由內容雜湊而來,同輸入永同編號)推出
