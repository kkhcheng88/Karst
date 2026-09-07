# 策略層兩份設計的評審與裁定

> 唯讀評審,未改 `karst/` 任何一個檔、未 commit、未碰 `.kira/`。
> 甲=合約優先(`design-A-strategy-contract.md`);乙=執行優先/數據流(`design-B-strategy-pipeline.md`)。
> 所有源碼聲稱皆已回源核實,錯號與漏項在第二節逐項列明。

---

## 一、準則逐項評分

| # | 準則 | 甲 | 乙 | 一句理由 |
|---|---|---|---|---|
| 1 | 深度(要學幾個名 / 換來幾多行為) | **4** | **3** | 甲的策略作者要交六件、乙只要四件,但乙的 `read_params(param_set) -> Any` 回一個不透明型別,管線對參數一無所知——於是「一格掃描格怎樣變成一個參數集」「參數怎樣文字化」兩件事在乙的介面裡無處安放,而文字化正是運行編號的輸入;甲多出來的 `param_spec` 就是填這個洞的那一件。 |
| 2 | 接縫位置(真接縫還是假想接縫) | **4** | **4** | 兩份對真接縫的判斷一致而且正確:引擎有四個實作(`VectorbtEngine`、`CostedEngine`、`VectorbtRuleEngine`、`VectorbtSignalMatrixEngine`),策略有三個實作加兩條規劃,兩者都是真接縫;兩份亦都拒絕造假定義庫(唯一入口與定義庫各只有一個實作,造協定即是假想接縫)。分歧只在假引擎放哪:甲放 `tests/doubles/` 正確,乙放進生產包 `karst/engine/` 會把生產介面再撐闊一格,而介面過闊正是候選四要治的病。 |
| 3 | 局部性(改一件事要碰幾處) | **5** | **3** | 甲把四份參數文字化(`weight_text`、`param_text`、`point_slug`、`SweepPoint.slug`)與五套純量驗證(`_as_int`/`_as_float`、`_check_tilt`/`_check_lookback_days`、`RiskRule.check`、`_fraction`/`_positive`)收成一份正本,並且點明「一旦飄開,同一組參數會算出兩個運行編號」;乙因為沒有參數規格,這兩類重複原地不動。改落痕格式、改批次登記兩項兩份同樣收成一處。 |
| 4 | 三條策略的搬入成本與風險(清單有沒有漏或錯) | **3** | **5** | 逐個符號回源核對:兩個真錯號全部在甲(`run_factor_mix` 實為 `:609` 不是 `:626`、`run_factor_rotation` 實為 `:1378` 不是 `:1404`),另引用了一條不存在的裁決(見第二節)。更重的是漏項:乙點名趨勢波段其實走 `karst/risk/sweep.py:163 sweep_risk_settings`(核實成立),甲由頭到尾沒有這個檔;乙又點出因子輪動連登記函式都沒有、策略型別直接等於因子混合、`ensure_factor_rotation_setup` 全身只有一句轉呼(三項核實全部成立),而這幾件正是搬入時會絆倒人的地方。 |
| 5 | D-042 批次登記哪份接得更直接 | **5** | **4** | 兩份的欄位清單幾乎相同,都是掃描收尾經唯一入口寫一列。甲多兩句有操作價值的:批次登記要**入治理清單、`karst verify` 核得到**(直接接上剛做完的候選二),以及**舊掃描可以事後補登記、既有運行一個位都不動**,於是遷移可以切成「先上執行台、後上批次登記」兩步。乙勝在有一張逐條對住 D-042 七項條文的表,可讀性較好,但把「新開一張表還是靠 `sweep_id` 聚合」留作未裁,少了一個決定。 |
| 6 | 與已有裁決的衝突 | **3** | **4** | 甲在三處貼得比乙緊:`funnel_stages` 把 D-013 的選股漏斗做成可核對的宣告、不變量三把 D-021 第 3 條的決策日／執行日做成逐行核對、參數集自報「已對齊／示例」正面回應 D-038。但甲有一處實質衝突:`RunRequest` 把風控設定與參數分開,風控三格因此不在參數規格之內,也就掃不到——**直接踩 D-008 第 3 條「平台對策略內部數值的責任形態是做成可掃描的參數」**,而現時 `sweep_risk_settings` 正正在掃這三格。乙把風控取值當普通參數由參數集帶,這一格乾淨。兩份都守住 D-009 第 7 條與 D-020 第 4 條。 |
| 7 | 自覺程度與盲點 | **3** | **4** | 乙列十條未決點,逐條回源核對後全部成立(尤其第 7 條「輪動要補一次首次登記、可能生成新策略版本」與第 9 條「靜態宣告載不載得起 `trend_swing.py:507-515` 按快照換因子版本」)。甲列九條亦誠實,但漏了自己模型的那個結構性缺口(風控軸無處安放),而且甲的 `factor_specs(snapshot_id)` 其實已經正面解決了乙的第 9 條——甲解決了卻沒發覺,乙發覺了卻沒解決。 |
| | **合計** | **27** | **27** | 總分打平,但強項不重疊——這正正是應該嫁接而非二選一的形狀。 |

---

## 二、回源核實:兩份的事實差錯

**乙對、甲漏的那一項(派工指名要核的)。** `sweep_trend_swing`(`trend_swing.py:932`)在 `:961` 呼叫 `sweep_risk_settings`(`risk/sweep.py:163`),該函式全身只有三個型別檢查加一個迴圈叫 `run_rule_strategy`,**沒有運行編號、沒有寫運行庫、沒有判讀**,交回 `RiskSweepResult`(要另叫 `.frame()` 才有表)。乙在第 0 節與 4.1 表格明文點名;甲只寫「不落庫、只交一張 DataFrame」——前半對,後半不準,而且**整份設計沒有處理 `karst/risk/sweep.py` 的去向**,而該檔另有 `risk/__init__.py` 的再導出與 `tests/test_risk_layer.py:317,342` 兩處測試依賴。`trend_swing.py:941` 的註釋更明寫它是「共用風控層的**正本**掃描器」,即不是遺留物,是有意的設計——搬入時必須明文裁決它的去向。

**甲的四處差錯。**(1) `run_factor_mix` 錯號;(2) `run_factor_rotation` 錯號;(3) 引用「D-023 第 8 條的合併法」,但 D-023 只有三條決策,沒有第 8 條;(4) 把 `CostedEngine` 歸入執行台,實情它是 `PortfolioEngine` 的第二個實作,乙說搬去引擎適配層才對。

**兩份共有的小瑕。** `ScoreEntry:445`、`CostPair:580` 指到 `@dataclass` 裝飾器行而非 class 行(差一行,無實質影響)。

**兩份都沒看見的一件。** `karst/sweep/__init__.py` 導出 52 個名,而 `sweep/factor_rotation.py` **一個都沒有導出**——輪動那半邊要直接 import 子模組。適配檔消失之後這張導出表要順手收窄,否則模組深度沒有改善,只是把淺的東西搬了個位(甲的未決點有提到收窄,但沒發現兩個適配檔的導出待遇本來就不一致)。

**與交付有關的一個數字更正。** 派工寫「現有九條正式運行」,但 `karst.sqlite` 的 `backtest_run` 表 `origin='formal'` 實為 **12 條**(另有 8,305 條掃描格運行)。九很可能是 D-040 之下畫面看得見的那批。驗證方式應該對住全部 12 條,不是九條。

---

## 三、裁定

**以甲為骨架,嫁接乙的三件。**

選甲為骨架的理由只有一條,但是決定性的:**參數規格(`ParamSpec`)是整個設計的承重件**。沒有它,掃描格變參數集、參數文字化、五套純量驗證合一、D-008「每格都要掃得到」的把關,四件事都沒有落腳處;乙的 `read_params -> Any` 是一個真空,而 `sweep()` 收了 `param_set_prefix` 卻沒有交代一格怎樣變成一個參數集。此外甲有 `rejudge` 入口(重判是 CONTEXT.md 已收錄的既有能力),而乙把策略名、快照、期間全部釘死在 `Pipeline` 的建構期,重判在乙的介面裡無處安放。乙的「八段管線、只有第三段不同」是更好的**敍事**,但敍事不是介面。

要嫁接進來的三件,逐件講明:

1. **風控取值收進參數規格,取消 `RunRequest` 的獨立 `risk` 那一格。** 風控三格自此是普通的可掃軸,由參數集帶——這樣才守得住 D-008 第 3 條,而且 `sweep_risk_settings` 那套私掃描器自然退役(或降級為風控層內部工具,見未決點一)。這一件同時補上甲最大的結構缺口。
2. **乙第 4.3 節對因子輪動的實情盤點,連同「一格拋錯不中斷整個批次」。** 輪動沒有登記函式、沒有選股痕跡、沒掛 `strategies/__init__.py` 的 `__all__`、策略型別直接等於因子混合——搬入時要補一次首次登記,而那會生成新的策略版本,甲承諾的「運行編號逐位不變」對輪動未必成立,必須事先講明。三千格跑到第 2,900 格才炸就要整批重跑,失敗格記入批次結果當無效格處理。
3. **`CostedEngine` 歸引擎適配層,以及 `TargetWeightsInput` 取代填空格那一段的論證。** 現時 `factor_mix.py:643-646` 被迫用 `RankingRebalanceParams(top_n=len(exposures), direction="high")` 填兩個用不著的格,註釋自認適配層欠一個與排名無關的組合參數型別——乙把這個缺件講清楚了,甲只是含糊帶過。

甲的其餘部分照用:合約六個名、執行台四個方法、`funnel_stages` 宣告與逐層收窄核對、`factor_specs(snapshot_id)` 解決按快照換因子版本、參數集自報「已對齊／示例」、假引擎放 `tests/doubles/`、批次登記入治理清單、遷移分兩步。

---

## 四、實作票草案

工作量明顯超過一程,拆三張,次序 A → B → C。搬入次序刻意不照兩份設計的排法:**因子混合先(樣板最完整、有正式運行可以逐位對)、因子輪動次(要補首次登記,風險獨立處理)、趨勢波段最後(牽涉最多新裁決,而且要與用戶對齊參數)。**

> 註:本倉的票其實是 YAML frontmatter 加 Markdown 正文的 `.md`,不是 JSON;下面按派工指定的鍵輸出,落票時照倉內格式轉寫即可。票號按現時最大編號 KARST-089 順推,即 A=KARST-090、B=KARST-091、C=KARST-092,`dependsOn` 已照此填。另注:全倉 `risk` 實測只有 `low`／`medium`、`fits` 實測全部「一程」、`model` 實測全部 `opus`——下面用「多程」是全倉第一次,落票前值得確認閘規收得。

```json
[
  {
    "title": "策略合約與策略執行台落地(架構審視候選一):參數規格收走五套純量驗證與四份文字化,因子混合首條搬入,正式運行成績逐位不變",
    "type": "task",
    "risk": "medium",
    "fits": "多程",
    "epic": "V1 建置",
    "deliverable": "KARST-D02",
    "dependsOn": ["KARST-087"],
    "approvalRequired": false,
    "what": "源自 research/2026-08-30-architecture-review-backend.md 候選一,設計以 research/2026-08-30-strategy-layer-design/design-A-strategy-contract.md 為骨架,嫁接 design-B 的三件(見 design-judge.md 第三節)。完成後:(1) 新增 karst/executor/contract.py,載 StrategyContract 協定(宣告 strategy_type、funnel_stages;方法 param_spec、factor_specs、needs_entities、plan)與值型別 ParamSpec/ParamField/FactorSpec/EntityRequest/RunRequest/EnginePlan(TargetPlan 與 RulePlan 二擇一的聯合);plan 是純函數,不開庫不讀檔不 import 第三方引擎。(2) 新增 karst/executor/executor.py,載 Executor,對外只掛 register / run / rejudge 三個方法(sweep 留給 B 票),register 與 run 共用私有 _execute_cell;一切寫入經唯一入口。(3) 風控取值收進參數規格當普通可掃軸,RunRequest 不設獨立 risk 格(D-008 第 3 條);參數規格內每一格都要掃得到、一格預設值都沒有(D-009 第 7 條);參數集自報「已對齊／示例」(D-038)。(4) 五套純量驗證(trend_swing.py:277 _as_int、:284 _as_float、factor_rotation.py:466 _check_tilt、:473 _check_lookback_days、engine/rules.py 的 _fraction/_positive)與四份參數文字化(sweep/factor_mix.py:98 weight_text、sweep/factor_rotation.py:96 param_text、:114 point_slug、SweepPoint.slug)收成 ParamSpec 一份正本,文字化口徑須與現行逐位相同。(5) 因子混合搬入:刪 register_factor_mix(factor_mix.py:376)、record_factor_mix_run(:671)、run_factor_mix(:609)的引擎樣板(遲到 import 與 RankingRebalanceParams 填空格那兩段);留 resolve_exposures(:468)、factor_mix_schedule(:513)、factor_mix_targets(:539)、factor_mix_selection_trace(:578)。(6) 新增 tests/doubles/engines.py,把四份散落的假引擎(test_engine_ranking_rebalance.py:384、test_engine_rules.py:396、test_factor_rotation.py:82、test_macro_drivers.py:172)收成兩個;新增全倉第一個 conftest.py。不造假定義庫,測試照舊起臨時 sqlite 真庫經唯一入口寫。要留的測試:test_sweep.py 的判讀與格、test_runs.py、test_risk_layer.py、test_selection_trace.py、test_engine_rules.py、test_engine_ranking_rebalance.py(含 :344 _cadence_defaults)、test_engine_audit.py:230、三條策略本體的計算測試。要刪的測試:test_factor_mix.py 的登記與落痕編排斷言,以及 :676 _code_symbols 配 :706 _weight_defaults 那份 ast.parse 原始碼文本斷言(改為斷言參數規格宣告的格數等於掃描格認得的軸數、每格有值域無取值)。驗證方式:因子混合的既有正式運行以執行台重跑,運行編號與八項成績指標逐位相同;全部 12 條 origin='formal' 的正式運行(karst.sqlite 實測 12 條,不是九條)一條都不得變號。動庫前備份到 C:\\Users\\Kaho\\.claude\\backups\\karst.sqlite.2026-08-30-A.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 karst/web/static/ 與 prototype/;不 commit。",
    "ac": [
      "策略合約與策略執行台落地,因子混合經 Executor.register/run 走完一次正式運行;全部 12 條既有正式運行重跑後運行編號與八項成績指標逐位相同(測試:逐條比對舊 fingerprint)",
      "參數文字化與純量驗證各只剩一份正本;參數規格宣告的格數等於掃描格認得的軸數,每格有值域無取值,風控三格在內(測試:缺一格拒收、多一格拒收、值域不合拒收、換倉節奏無預設)",
      "tests/doubles/engines.py 與 conftest.py 已建,四份假引擎收成兩個;只跑所涉測試檔;備份已做"
    ]
  },
  {
    "title": "掃描收成執行台第二入口(架構審視候選四):兩個掃描適配檔與 CellJob 協定退役,因子輪動搬入並補首次登記,批次登記落庫入治理清單",
    "type": "task",
    "risk": "medium",
    "fits": "多程",
    "epic": "V1 建置",
    "deliverable": "KARST-D02",
    "dependsOn": ["KARST-090"],
    "approvalRequired": false,
    "what": "源自架構審視候選四與 D-042。完成後:(1) Executor 加 sweep 入口,一次掃描即一個批次;逐格走與 run 同一條落格路徑,分別只在來歷(掃描格加掃描編號,KARST-054)、不收選股痕跡、參數由掃描格逐格展開三處;判讀沿用 sweep/verdict.py 的 judge(純函數,一個字不動);四個判讀門檻無預設。(2) 一格拋錯不中斷整個批次,失敗格記入結果當無效格處理。(3) sweep/factor_mix.py 的 FactorMixJob(:218)與 ensure_factor_mix_setup(:184)、sweep/factor_rotation.py 的 FactorRotationJob(:225)與 ensure_factor_rotation_setup(:196)四件刪走;sweep/runner.py 的 CellJob(:101)協定與 run_sweep(:290)退役,CellPlan(:64)保留改由執行台按參數規格自動砌。(4) weight_grid(:41)、reference_point(:76)、rotation_grid(:123)留作掃描格構造;CostedEngine(sweep/factor_mix.py:154)搬去 karst/engine/ 與 VectorbtEngine 並列(它是 PortfolioEngine 的第二個實作,不是掃描的事);ScoreEntry、scoreboard、segment_excess、CostPair、cost_comparison、provenance_note 搬去 sweep/report.py。(5) karst/sweep/__init__.py 那 52 個對外名順手收窄,並補上輪動那半邊本來一個都沒導出的不一致。(6) 因子輪動搬入:刪 record_factor_rotation_run(:1482)與 run_factor_rotation(:1378)的引擎樣板;run_factor_rotation 改名 plan;:1417-1437 的大市代號解析與「大市不可以同時是持倉」核對改由 needs_entities 宣告加執行台解析;_prepare_macro(:1332)保留為策略內部守門,macro_series_needed(:975)變 needs_entities 的一格;RotationDriver(:366)與十個驅動器不動。輪動現時沒有登記函式、策略型別直接等於因子混合、沒掛 strategies/__init__.py 的 __all__、沒有選股痕跡——搬入要補一次首次登記,會生成新的策略版本,舊運行依 D-021 第 9 條標過時不改,不得倒推。(7) sweep 收尾經唯一入口寫一列批次登記:掃描編號、策略名與版本、期間、數據快照、引擎與版本、總格數、達標格數、隱藏的失敗運行條數、中位年化、中位 Sortino、中位最大回撤、判讀目標與三個門檻、最佳格、代表格、批內最佳單次的運行編號、報告落點與內容雜湊;批次登記入治理清單,karst verify 核得到。舊掃描可以事後補登記,既有運行一個位都不動。失敗判定呼叫 web/data.py:110 is_failed_run 同一份正本,不另寫第二套(D-034/D-040)。(8) web/api_jobs.py 的 _rescan(:836,約 110 行)收成一句 executor.sweep;RESCAN_FAMILIES(:778-781)整張刪走。要刪的測試:test_sweep.py:145 的手砌 _Job、test_factor_rotation.py 的登記與落痕編排斷言。要留的測試:test_sweep.py 的判讀與格、test_macro_drivers.py 的驅動器計分板。驗證方式:既有掃描逐格以執行台重跑,運行編號逐位相同、判讀結果逐格相同;12 條正式運行仍然一條都不變號。動庫前備份到 C:\\Users\\Kaho\\.claude\\backups\\karst.sqlite.2026-08-30-B.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 karst/web/static/ 與 prototype/;不 commit。",
    "ac": [
      "CellJob 協定與兩個掃描適配檔的 Job 已退役,既有掃描逐格重跑後運行編號與判讀結果逐格相同,12 條正式運行不變號(測試:逐格比對舊 fingerprint 與舊 verdict)",
      "批次登記經唯一入口落庫並入治理清單,karst verify 分列且清白;達標與失敗判定只有 is_failed_run 一份正本(測試:直接寫庫的批次登記被 verify 點名)",
      "因子輪動經執行台跑得通,首次登記所生成的新策略版本已記錄、舊運行只標過時;只跑所涉測試檔;備份已做"
    ]
  },
  {
    "title": "趨勢波段搬入策略執行台:風控三格改為普通可掃軸,risk/sweep.py 私掃描器去向裁決,該策略的掃描首次落庫並接上判讀(含 D-038 參數對齊)",
    "type": "task",
    "risk": "medium",
    "fits": "一程",
    "epic": "V1 建置",
    "deliverable": "KARST-D02",
    "dependsOn": ["KARST-091"],
    "approvalRequired": true,
    "what": "源自架構審視候選一,並收拾兩份設計都沒有完整處理的一件:趨勢波段的掃描其實不走通用掃描器。完成後:(1) 開工第一步是與用戶對齊參數(D-038 明令每條策略建置期必有此步):哪幾個旋鈕、每個掃描範圍、判讀目標與三個門檻、代表格如何揀;現有示例取值(突破回望 59 日、單筆風險 2%、月度熔斷 6%、賠率門檻 1.5、單一持倉上限 25%)未經對齊,不視為現役設定,對齊結果落在本票。(2) 趨勢波段搬入:刪 register_trend_swing(trend_swing.py:470)、record_trend_swing_run(:552)、sweep_trend_swing(:932)、TrendSwingSweepCell(:868)、TrendSwingSweepResult(:909)、run_trend_swing(:449-457)那三段 isinstance 守門;run_trend_swing(:436)改名 plan,回 RulePlan;params_grid(:829)搬去掃描格構造一族;build_bar_panel(:296)搬去執行台的組面板段;to_param_values(:218)、from_param_set(:233)收成 param_spec 宣告;留 TrendSwingParams 的 entry/stop/rule_params(:188-216)與案例那一整段(EntryCase:620、entry_cases:665、cases_frame:727、CaseStats:753、case_stats:791,經旁產物交出,不入合約);factor_specs 承接 :507-515 按快照換因子版本那段動態。(3) 裁決 karst/risk/sweep.py(213 行)的去向:風控三格既已收進參數規格成為普通可掃軸,sweep_risk_settings(:163)不再是趨勢波段的掃描路徑;它另有 risk/__init__.py 的再導出與 tests/test_risk_layer.py:317,342 兩處依賴,而 trend_swing.py:941 的註釋稱它為共用風控層的正本掃描器,故不得默默刪走——按未決點一的裁決結果執行,並在 CONTEXT.md 與 decisions.md 留下痕跡。(4) 趨勢波段的掃描自此第一次落運行庫、接上運行編號查重與判讀,並在 D-042 的批次表上第一次出現;代價是每格寫一條運行,先量一次寫入量與耗時再決定要不要分批。(5) 要刪的測試:test_trend_swing.py 的登記與落痕編排斷言、:655 _code_symbols 配 :681 _value_defaults 那份 ast.parse 文本斷言(改為參數規格斷言);要留的測試:test_trend_swing.py:431-435 守「策略層碰不到風控型別」那批、案例計算那批、test_risk_layer.py 七個(風控掃描相關兩個按未決點一的裁決調整)。驗證方式:趨勢波段既有正式運行重跑後成績逐位相同;12 條正式運行全部不變號;三條策略自此在同一個批次表上比得到。動庫前備份到 C:\\Users\\Kaho\\.claude\\backups\\karst.sqlite.2026-08-30-C.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 karst/web/static/ 與 prototype/;不 commit。",
    "ac": [
      "參數對齊一節已與用戶完成並落在本票,示例取值與現役設定在參數集上分得出(D-038)",
      "趨勢波段經執行台跑得通,風控三格是普通可掃軸,該策略的掃描首次落運行庫並出判讀;12 條正式運行重跑後成績逐位相同(測試:逐條比對舊 fingerprint)",
      "risk/sweep.py 的去向已按裁決執行並留痕,test_risk_layer.py 相應調整;只跑所涉測試檔;備份已做"
    ]
  }
]
```

---

## 五、要進 CONTEXT.md 的新詞

| 中文 | 英文 | 它是什麼 |
|---|---|---|
| 策略合約 | strategy contract | 一條策略要交出的那幾件東西的宣告:它屬哪一類、用選股漏斗哪幾層、有哪幾格參數、要登記哪幾條因子、要解析哪些交易代號,以及由面板與參數算出目標比重表或規則參數的那一個純函數。 |
| 策略執行台 | strategy executor | 收走每條策略做法一模一樣那一截的模組:登記、驗參數、解析實體、叫引擎、查重、落痕、掃描、判讀、批次登記,全部住在它裡面,策略只交策略合約。 |
| 參數規格 | param spec | 一條策略全部參數格的宣告:每格的名、型別、值域、寫入參數集時的文字寫法。一格預設值都沒有,一格都要掃得到;它同時是掃描格展開成參數集的依據。 |
| 批次登記 | batch registry | 一次掃描收工時經唯一入口寫落庫的那一列:掃描編號、策略、期間、格數、達標格數、幾個中位數成績、判讀目標與門檻、最佳格與代表格。批次層畫面自此不用讀 CSV。 |

註:「批次 / batch」已由 D-042 收錄並鎖死為「一次參數掃描跑出來的那批運行」,批次登記是它落庫的那一列,兩者不衝突;亦不可與已收錄的「因子值批次 / factor value batch」混淆。

---

## 六、要用戶裁決的未決點

1. **`karst/risk/sweep.py` 的私掃描器,退役還是降級?** 風控三格收進參數規格之後,趨勢波段不再需要它,但它有自己的測試,而且註釋稱它為共用風控層的正本掃描器。建議:整檔退役,風控軸自此只有執行台一條路——理由是同一件事留兩個掃描器,正是這次要治的病;`test_risk_layer.py` 那兩個測試改打執行台。
2. **因子輪動補首次登記會生成新的策略版本,接受嗎?** 它現時連登記函式都沒有,策略型別直接借用因子混合的。搬入必然要補登記一次,舊運行依 D-021 第 9 條標過時、永不自動更新。建議:接受,並在 B 票明文記錄新版本編號與被標過時的運行清單,不追求輪動的舊運行編號不變(其餘兩條策略照樣逐位不變)。
3. **趨勢波段的掃描第一次要揀判讀目標與三個門檻,誰揀?** D-038 明令這正是建置期要與用戶對齊的東西,代理不得代揀。建議:留在 C 票的參數對齊一節,與旋鈕、掃描範圍、代表格揀法一次過對齊,故 C 票的 `approvalRequired` 設 `true`(全倉第二張)。
