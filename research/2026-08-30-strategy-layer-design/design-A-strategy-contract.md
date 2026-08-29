# 設計 A:合約優先(策略合約 + 策略執行台)

> 唯讀設計,未改動 `karst/` 任何一個檔。對應架構審視候選一(策略合約)與候選四(一次掃描收成一個介面)。
> 詞彙照 `CONTEXT.md`;架構詞用模組／介面／實作／深度／接縫／適配器／槓桿／局部性。
> 本設計新造三個詞(策略合約、策略執行台、批次登記),按規矩應落 `CONTEXT.md`;本次唯讀,故列在第七節待落表。

角度:由「一條新策略要交出什麼」出發。先寫合約,再看誰被合約清走。

---

## 1. 接縫放在哪裡

**線畫在「只有這條策略知道的東西」與「每條策略做法一模一樣的東西」之間。**

線的策略那一邊,只剩四件:

1. 這條策略有哪幾格參數、每格的值域與文字寫法(參數規格);
2. 這條策略要登記哪幾條因子(因子規格);
3. 由 K 線面板／價格面板／因子面板,算出**目標比重表**或**規則參數**,連同**選股痕跡**(這是策略的本體);
4. 這條策略用選股漏斗的哪幾層。

線的另一邊,全部收進一個深模組:參數集登記、因子與策略登記、風控設定套用、代號解析、引擎選擇與呼叫、運行編號查重、運行落痕、選股痕跡落庫、掃描格展開、逐格重用、判讀、批次登記、失敗判定。

**為什麼畫在這裡。** 現時三條策略之間唯一真正不同的,就是上面那四件;其餘每一件都能在另外兩個檔找到逐字相同的孿生:

- `strategies/trend_swing.py:470-549` 的 `register_trend_swing` 與 `strategies/factor_mix.py:376-460` 的 `register_factor_mix`,連「同名同節奏同取值即沿用舊版」那句註釋都一字不差;
- `record_trend_swing_run`(`trend_swing.py:552`)、`record_factor_mix_run`(`factor_mix.py:671`)、`record_factor_rotation_run`(`factor_rotation.py:1482`)三份,同一個十一參數簽名,函式體分別只有一行;
- `run_factor_mix:626-668` 與 `run_factor_rotation:1404-1479`:同一段面板守門、同一段 `RankingRebalanceParams(top_n=len(exposures), direction="high")` 填空格、同一句遲到 import `VectorbtEngine`、同一段結果打包;
- 掃描那邊 `sweep/factor_mix.py:218-359` 的 `FactorMixJob` 與 `sweep/factor_rotation.py:225-437` 的 `FactorRotationJob`:`_cadence_of`、`_param_set`、`plan()` 的後半段(取因子版本、取策略版本、砌 `CellPlan`)、`simulate()` 的引擎名核對,全部逐字重覆。

一件東西抄到第三次,它就不是巧合,是一個未收的介面。**槓桿**在這裡量得到:一個合約驅動現有三條策略,加 D-015 Minervini 與 D-018 錯殺兩條未寫的,即五條;每條省下六格抄寫。**局部性**同樣量得到:登記缺陷、落痕缺陷、成本入不入參數集這類決定,日後只可能出錯在一處。

還有一條線**刻意不畫**:因子輪動的驅動器(`factor_rotation.py:366 RotationDriver`,連十個實作)是那條策略**自己的**可換件,不提升到合約。合約若把驅動器也收進去,就會逼因子混合與趨勢波段去實作一個它們沒有的概念——那是把一條策略的內部結構當成全平台的結構,正是介面過闊的起因。

---

## 2. 策略合約(strategy contract)

一個 `Protocol`(不是基類——理由見第七節),名 `StrategyContract`,住 `karst/executor/contract.py`。
兩個宣告欄位、四個方法。呼叫者(執行台)要知的,逐項一句:

| 名 | 呼叫者要知道什麼 |
|---|---|
| `strategy_type: str` | 這條策略在 `store.STRATEGY_TYPES` 八個之中屬哪一類;登記策略時原樣寫入,執行台不猜。 |
| `funnel_stages: tuple[str, ...]` | 這條策略用選股漏斗哪幾層,由上而下;空的即這條策略交不出選股痕跡。執行台用它核對痕跡層名與逐層收窄。 |
| `param_spec() -> ParamSpec` | 這條策略全部參數格的規格:名、型別、值域、寫入參數集時的文字寫法、可否掃描。**一格預設值都沒有,一格都不可以掃不到**;執行台據此驗參數、據此把掃描格一格展開成一個參數集(D-008:參數取值屬用戶領域,平台的責任是把門檻做成可掃描的參數;明文「不設預設值」在 D-009 第 7 條的換倉節奏、D-021 第 7 條的中性化、D-023 第 8 條的合併法)。 |
| `factor_specs(snapshot_id: str) -> tuple[FactorSpec, ...]` | 這條策略要登記哪幾條因子:名、刻度型、產生程序、說明。快照編號由執行台交來,策略把它填入產生程序的輸入數據版本(追溯,D-021)。 |
| `needs_entities(params: Params) -> EntityRequest` | 這一組參數要解析哪些交易代號:持得到的(敞口)、只做訊號的(大市)、宏觀序列代號。執行台在面板第一根 K 線那一日一次過解析,策略不碰定義庫。 |
| `plan(request: RunRequest) -> EnginePlan` | 這條策略的本體:收面板、已驗參數、風控設定、已解析的實體對照,回一份引擎收得的計劃——目標比重表或規則參數二擇其一,連換倉紀錄與選股痕跡。**純函數**。 |

配套的值型別(全部 frozen dataclass,住同一個檔):

- `ParamSpec` / `ParamField`:一格參數的名、型別、值域檢查、文字化函式。取代現時五套並存的純量驗證(`trend_swing.py:277 _as_int`/`:284 _as_float`、`factor_rotation.py:466 _check_tilt`/`:473 _check_lookback_days`、`risk/layer.py:78 RiskRule.check`、`engine/rules.py` 的 `_fraction`/`_positive`)與兩份文字化(`sweep/factor_mix.py:98 weight_text`、`sweep/factor_rotation.py:96 param_text`)。
- `RunRequest`:`panel`(K 線面板或價格面板)、`params`、`risk`(風控設定)、`entities`(唯讀對照:代號→實體編號)、`extras`(宏觀面板一類附加輸入)。**不帶定義庫、不帶 gateway、不帶引擎。**
- `EnginePlan`:`TargetPlan(targets, rebalances, selection)` 或 `RulePlan(rule_params, selection)`。兩者不合一 —— 理由見第七節第一條。

### 不變量

1. `plan` 是純函數:同一個 `RunRequest` 永遠出同一個 `EnginePlan`;不開庫、不讀檔、不寫檔、不 import 任何第三方引擎(D-007 第 3 條;現時靠 `tests/test_engine_rules.py` 正則掃全倉把關,合約不削弱這道閘)。
2. 目標比重表:空白 = 這根 K 線不下單,0 = 清倉到零,兩者不可混(`CONTEXT.md`「目標比重表」)。
3. 比重只可以寫在**執行日**那一行;決策日與執行日必須是相鄰兩根 K 線,成交取執行日開價(D-021)。執行台逐行核對這一條,策略繞不過。
4. 只做訊號的實體(大市那條線、宏觀序列)在目標比重表裡永遠是 0 或者根本沒有那一欄。
5. 選股痕跡的層名必須是 `funnel_stages` 的子集,而且逐層收窄(到達該層,KARST-056)。
6. `factor_specs` 交出的每條產生程序,其輸入數據版本必須等於執行台交來的快照編號。
7. 參數規格所列以外的參數名一律拒收;規格所列而缺的,亦一律拒收——不補預設。換倉節奏尤其明文不可有預設(D-009 第 7 條)。
8. 規格內每一格都要掃得到:一格都不可以寫死在碼裡(D-008;現時靠 `test_trend_swing.py:551` 與 `test_factor_mix.py` 兩份 `ast.parse` 測試守住,見第五節)。
9. 一個參數集要講得出它是**已對齊**還是**示例**:D-038 明令建置期要與用戶對齊旋鈕與掃描範圍,未對齊的示例取值不得當作現役設定。執行台在登記時原樣記下這一格,不替策略猜。
10. 合約不判成敗:失敗運行(D-034/D-040)由執行台判,策略連基準都看不見。

### 錯誤模式

全部是既有 `ContractViolation` 的子型別,執行台在跑引擎**之前**擲出:

- `MissingParameter`(規格有、取值無)、`UnknownParameter`(取值有、規格無)、`ParameterOutOfRange`(值域不合);
- `UnresolvedTicker`(代號在那一日解析不到實體)、`EntityNotInPanel`(解析到但面板沒有它的價格,不猜、不當零)、`DuplicateExposureEntity`(兩格敞口撞同一個實體);
- `InsufficientHistory`(熱身期不夠,`factor_rotation.py:144` 已有此型別,提升至合約層共用);
- `MissingRequiredInput`(驅動器要宏觀面板而沒有給——現時是 `sweep/factor_rotation.py:301-312` 的手寫守門);
- `PlanShapeViolation`(比重寫在非執行日、既非空白亦非合法比重、痕跡層名不在宣告內);
- `EngineNameMismatch`(結果自報的引擎名與落痕寫的不同——現時在兩個 Job 各抄一次)。

---

## 3. 策略執行台(strategy executor)

住 `karst/executor/`,對外只掛四個名。`Executor` 建構時收三件:`gateway`(唯一入口)、`runs`(`RunStore`)、`engines`(目標比重路徑與規則路徑各一個實作,留空即用預設)。

```
Executor(gateway, runs, engines=None)

  .register(contract, *, strategy_name, snapshot_id, param_set_name,
            values, rebalance_cadence, description) -> Setup
  .run(contract, *, setup, panel, params, period, engine_version,
       extras=None) -> RunOutcome
  .sweep(contract, *, setup, panel, grid, sweep_id, objective,
         thresholds, period, engine_version, extras=None,
         progress=None) -> BatchOutcome
  .rejudge(batch_id, *, objective, thresholds) -> BatchOutcome
```

**`register`** —— 一次過:登記共用風控規則、按 `factor_specs` 登記因子(同名而快照不同即出新版)、登記策略、登記參數集、掛上風控引用。全部經唯一入口,一句直接寫庫都沒有(D-020)。回一個 `Setup`(策略版本、參數集、因子版本編號)。參數集連「已對齊／示例」一格一併寫入(D-038)。取代 `register_trend_swing`、`register_factor_mix`、`ensure_factor_mix_setup`、`ensure_factor_rotation_setup` 四份。

**`run`** —— 一次正式運行。次序固定:驗參數 → 讀風控設定 → 解析實體 → `contract.plan()` → 核對計劃(不變量 2-5)→ 算運行編號查重 → 命中即回舊運行(重跑一格都沒改,回同一編號,KARST-052)→ 未命中即叫引擎 → 落痕(來歷=正式運行)→ 寫選股痕跡 → 算指標與基準 → 判失敗運行 → 回 `RunOutcome`(運行編號、指標、是否重用、是否失敗)。取代 `run_*` 三份的樣板段落與 `record_*_run` 三份。

**`sweep`** —— 一次掃描,即**一個批次**(D-042)。次序:展開掃描格 → 逐格由 `param_spec` 砌參數集(經唯一入口,同取值沿用舊版)→ 逐格走與 `run` **同一條落格路徑**,分別只在來歷那一格(掃描格 + 掃描編號,KARST-054)→ 判讀(`sweep.verdict.judge`,純函數,原封不動)→ 登記批次 → 落報告。回 `BatchOutcome`(掃描編號、逐格成績、判讀、來歷、達標比率、最佳格與代表格)。

**一次運行與一次掃描如何共用。** 兩者調用同一個私有 `_execute_cell(contract, identity, request)`:驗參數、叫 `plan`、核計劃、查重、跑引擎、落痕,一步不差。差別只有三格,而這三格正是裁決本身講的差別:

| | 一次運行 | 一次掃描的一格 |
|---|---|---|
| 來歷(KARST-054) | 正式運行 | 掃描格 + 掃描編號 |
| 選股痕跡 | 收(`record_simulation` 只在正式運行收) | 不收 |
| 參數從哪裡來 | 呼叫者給一組 | 掃描格展開,一格一組 |

所以「一次掃描」不是另一套編舞,而是同一條路走 N 次加一次判讀。現時呼叫者要自己記住的十步(讀面板 → 開入口 → 備風控 → 開運行庫 → 砌格 → 造 Job → `run_sweep` → `judge` → 畫投影 → 寫報告)收成一句 `executor.sweep(...)`;那十步現時在實驗腳本與 `web/api_jobs.py:836-880` 各抄一次。

**`rejudge`** —— 不重跑引擎,只換判讀口徑重判一次落檔的掃描表(KARST-047/048)。留它是因為它便宜而且已經是既有做法;它讀批次登記,不碰引擎。

---

## 4. 現有三條策略如何搬入

### 趨勢波段 `karst/strategies/trend_swing.py`(981 行 → 約 350)

- **刪**:`register_trend_swing:470-549`、`record_trend_swing_run:552-591`、`params_grid:829-864`、`TrendSwingSweepCell:867-905`、`TrendSwingSweepResult:908-929`、`sweep_trend_swing:932-981`、`run_trend_swing:449-457` 那三段 `isinstance` 守門。
- **改**:`TrendSwingParams.to_param_values:218` / `.from_param_set:233` / `_as_int:277` / `_as_float:284` 收成一份 `param_spec()` 宣告——來回轉換由執行台按規格做,策略只講規格。`run_trend_swing:436` 改名 `plan`,回 `RulePlan(rule_params=params.rule_params(risk), selection=None)`,引擎那三句由執行台接手。
- **留**:`TrendSwingParams.entry/stop/rule_params:188-216`(這條策略獨有的規則組裝)、`build_bar_panel:296`、以及案例那一整段 `EntryCase:620` / `entry_cases:665` / `cases_frame:727` / `CaseStats:753` / `case_stats:791`——案例表是趨勢波段自己的產物,不是每條策略都有的東西,不入合約。
- **要留意的**:`sweep_trend_swing` 現時**根本不落庫**——它逐格跑完只交一張 DataFrame,沒有運行編號、沒有留痕、沒有判讀。搬入執行台之後這條策略的掃描才第一次接上批次與判讀;代價是每格都會寫一條運行(見第七節)。

### 因子混合 `karst/strategies/factor_mix.py`(706 行 → 約 300)

- **刪**:`register_factor_mix:376-460`、`record_factor_mix_run:671-706`、`run_factor_mix:626-668` 的樣板(面板守門、`RankingRebalanceParams` 填空格、遲到 import、`engine.simulate`、結果打包)。
- **改**:`resolve_exposures:468-510` 不再收 `DefinitionStore`,改收執行台傳入的實體對照;`FactorSleeve` 那四格的產生程序(`:407-429`)由編排式改成 `factor_specs()` 的宣告式。
- **留(這就是它的本體)**:`factor_mix_schedule:513-536`(混權重策略第一根 K 線就做決策日那條規矩)、`factor_mix_targets:539-575`、`factor_mix_selection_trace:578-601`(兩層漏斗)。`plan` 就是這三個順住叫一次。
- `funnel_stages = (STAGE_SCOPE, STAGE_SELECTED)`——現時這件事寫在 `factor_mix_selection_trace` 的函式體裡,改成宣告之後,執行台核對得到。

### 因子輪動 `karst/strategies/factor_rotation.py`(1,516 行 → 約 1,200)

- **刪**:`record_factor_rotation_run:1482-1516`、`run_factor_rotation:1449-1479` 的引擎樣板。
- **改**:`run_factor_rotation:1378` 改名 `plan`;`:1417-1437` 那段大市代號解析與「大市不可以同時是持倉」的核對,改由 `needs_entities` 宣告 + 執行台解析與核對(不變量 4);`_prepare_macro:1332` 保留為策略內部的守門,但「沒有給宏觀面板」那一句改擲 `MissingRequiredInput`。
- **不動(佔本檔七成)**:`DriverView:159-350`、`RotationDriver:366`、十個驅動器實作 `:489-899`、`normalise_weights:389`、`rotation_targets:1242`。驅動器是這條策略自己的接縫,合約看不見它。
- `_check_tilt:466` / `_check_lookback_days:473` 兩個純量驗證由 `param_spec` 的值域接手。

### 掃描適配檔:消失

- `karst/sweep/factor_mix.py`(359 行):`FactorMixJob:218-359` 與 `ensure_factor_mix_setup:184-215` **消失**。`weight_grid:41`、`reference_point:76` 是掃描格構造,搬去 `sweep/grid.py` 旁邊留住;`weight_text:98`、`cost_text:110`、`cost_values:124`、`cost_slug:140` 搬入執行台的參數文字化(單一正本,同時清走 `sweep/factor_rotation.py:96 param_text`、`:114 point_slug` 那第二份);`CostedEngine:154` 搬入執行台——它是「成本注入引擎參數」的補丁,與哪一條策略無關。
- `karst/sweep/factor_rotation.py`(696 行):`FactorRotationJob:225-437`、`ensure_factor_rotation_setup:196-222` **消失**;`rotation_grid:123` 留作格構造;`ScoreEntry:445` / `scoreboard:460` / `segment_excess:514` / `CostPair:580` / `cost_comparison:598` / `provenance_note:658` 是報告層,搬去 `sweep/report.py`。
- `karst/sweep/runner.py` 的 `CellJob:101` 協定連同 `run_sweep:290` 一併退役:`CellJob` 本來就是「一格怎樣跑」——那正是策略合約要答的問題,兩個協定並存即是同一個接縫畫了兩次。`CellPlan:63`(一格的身份)保留,改由執行台按 `param_spec` 自動砌。
- 兩個適配檔合共約 1,055 行,收剩格構造與報告兩截,估計餘 250 行上下。

`karst/web/api_jobs.py` 的重掃路徑(`_rescan:836-880`)由三十行編排收成一句 `executor.sweep(...)`;`RESCAN_FAMILIES:778` 那張「按策略名派工」的表可以整張刪走——按名派工正是沒有合約的病徵。

---

## 5. 測試面

**經介面測得到什麼。** 寫一個假合約(`FakeContract`:兩格參數、一條因子、回一張兩行的目標比重表),即可經執行台的四個方法打中以下全部行為,一次都不用起 vectorbt:

- 缺一格參數即拒收、多一格參數即拒收、值域不合即拒收;換倉節奏無預設(D-009 第 7 條);
- 同名同節奏同取值不出新版本(KARST-046);
- 同一組輸入兩次 `run` 得同一個運行編號、第二次不跑引擎(KARST-026、052);
- 比重寫在非執行日即拒收、空白與 0 分得清(目標比重表不變量);
- 選股痕跡層名不在宣告內即拒收、逐層不收窄即拒收(KARST-056);
- 掃描一格與正式運行的來歷分別正確、掃描編號不入運行編號(KARST-054);
- 失敗運行判定與批次達標比率同一個口徑(D-034/D-040);
- 參數集自報「已對齊／示例」,示例那批不會被當成現役設定(D-038)。

**假引擎／假定義庫的適配器放哪(內部接縫)。** 一個 `tests/doubles/` 目錄,配一個全倉唯一的 `conftest.py`(現時 43 個測試檔、126 個 fixture、跨檔零共用、**沒有 conftest.py**):

- **假引擎放得**:`PortfolioEngine` 與 `RuleEngine` 是**真接縫**——`vectorbt_engine.py` 本身就有訂單函式臂(`:235`)與訊號矩陣臂(`:302`)兩個實作,而且引擎適配層全倉只有一個 `import vectorbt`(`vectorbt_engine.py:23`)。現時假引擎已有四份散在四個檔:`_FakeEngine`(`test_engine_ranking_rebalance.py:384`)、`_FakeRuleEngine`(`test_engine_rules.py:396`)、`RecordingEngine`(`test_factor_rotation.py:82` 與 `test_macro_drivers.py:172`,兩份近乎逐字相同)。四份收成 `tests/doubles/engines.py` 兩個。
- **假定義庫不要造**:`Gateway` 與 `DefinitionStore` 各自只有一個真實作,為它們發明一個 Protocol 就是**一個適配器 = 假想接縫**。現有測試已經起臨時 sqlite 真庫(`test_factor_rotation.py:131`、`test_sweep.py:190`、`test_trend_swing.py:170`、`test_runs.py:31` 一律 `Gateway.open(tmp_path/"karst.sqlite")`),照舊;執行台的測試同樣用真庫,只是不再需要真引擎。
- 因此執行台對外只認兩個型別化的門:引擎(可替身)與唯一入口(真庫)。`test_gateway.py:160` 那個刻意直連 sqlite 證明繞不過去的測試照舊有效。

**保留的測試**:`test_sweep.py`(1,088 行 / 17 個)裡判讀與格的那批——孤峰/山脊/平原分得開、無效格、鄰域只沿連續軸、重掃同格重用不再跑引擎——`sweep/verdict.py` 的 `judge` 是純函數,一個字不動;`test_runs.py`(5 個:同輸入同運行編號、子期間不重跑、新版本標過時);`test_risk_layer.py`(7 個,含「風控層不 import gateway」);`test_selection_trace.py`(4 個:補痕跡後運行編號逐位不變);`test_engine_rules.py` 與 `test_engine_ranking_rebalance.py`;策略本體的計算測試(`factor_mix_targets` 的空白/0、`entry_cases` 的案例、四個驅動器同一張計分板)。

**被取代的測試**:

- `test_trend_swing.py`(726 行)、`test_factor_mix.py`(746 行)、`test_factor_rotation.py`(504 行)裡斷言「登記編排」與「落痕編排」的那批,收成執行台一份;
- 兩份 `ast.parse` 原始碼文本斷言——`test_trend_swing.py:551` 配 `_code_symbols:657` / `_value_defaults:686`,與 `test_factor_mix.py:682` 配 `_weight_defaults:712`——它們守的是「每格參數都掃得到、碼裡無硬編數值」。有了 `param_spec` 之後,這條規矩由讀原始碼變成讀規格:斷言「規格宣告的格數 = 掃描格認得的軸數,且每格都有值域無取值」,一份取代兩份。
- **兩份不動**:`test_engine_ranking_rebalance.py:344 _cadence_defaults`(守 D-009 第 7 條的節奏無預設)與 `test_engine_audit.py:230`(守策略層讀不到高低價、抄不了出場規約)——它們守的是引擎層,不在本次搬遷範圍。
- `test_sweep.py:145` 的 `_Job`(手砌一個 `CellJob`)隨 `CellJob` 協定一併退役,改用假合約。

**順帶留意**:`test_web_sweep.py` 與 `test_web_strategy.py` 不建臨時庫,而是讀專案根目錄那個真 `karst.sqlite`,不在就整批 skip——CI 上基本全跳。批次登記落庫之後(第八節),這批測試才有一個起得出的真數據源。

**介面就是測試面**:合約只有六個名,執行台只有四個;新加第四、五條策略時,要寫的新測試只有「這條策略的 `plan` 算得對不對」,登記、落痕、查重、掃描一條都不用再測一次。

---

## 6. 刪除測試

**問:把策略執行台刪走,複雜度會在哪裡重現?**

1. `register_*` 編排:現時 2 份(趨勢波段、因子混合),加輪動借用因子混合那份;第四、五條策略各再一份 → **5 處**。
2. `record_*_run`:現時 3 份,同一個十一參數簽名 → **5 處**。
3. 掃描編排:現時 3 套並存——`sweep/factor_mix.FactorMixJob`、`sweep/factor_rotation.FactorRotationJob`、`strategies/trend_swing.sweep_trend_swing`(這一套連庫都不落)→ **5 處**。
4. 網頁重掃的十步編排:`web/api_jobs.py:836-880` 一份,加實驗腳本各一份 → **每新增一條可重掃的策略再加一格 `RESCAN_FAMILIES`**。
5. 參數文字化:`weight_text` 與 `param_text` 兩份、`point_slug` 與 `SweepPoint.slug` 兩份 → **2-4 處**,而且一旦飄開,同一組參數會算出兩個運行編號。
6. 純量驗證:現時 5 套並存(`_as_int`/`_as_float`、`_check_tilt`/`_check_lookback_days`、`RiskRule.check`、`_fraction`/`_positive`);笛卡兒積 3 處各自砌。

六類、合共二十餘處。這不是過手——每一處都是呼叫者要**記得住**的不變量(成本要入參數集、熱身期要入參數集、宏觀快照要入參數集、引擎名要對得上落痕、掃描格要用掃描來歷)。忘記其中一條,後果不是報錯,是**靜靜地讀回一個不該重用的舊運行**。複雜度不會因為刪掉這個模組而消失,它會在二十處重現——即是它在賺錢,值得收成介面。

---

## 7. 風險與未決點

- 目標比重路徑與規則路徑要不要共用一個 `EnginePlan` 型別:強行合一會多一層轉譯(與架構審視候選八同一個疑問),本設計選擇兩個型別、一個聯合,但未經實作驗證。
- `sweep_trend_swing` 現時一格都不落庫;搬入執行台後每格都寫一條運行,一次幾百格的掃描要先量寫入量與耗時,再決定要不要分批。
- 宏觀面板是第二種輸入,現時以 `macro=` 一格特事特辦;`RunRequest.extras` 這個一般化是否夠用(第三種輸入來時會不會又要開一格),未定。
- `param_spec` 的文字化口徑必須與現時 `weight_text`/`param_text` 逐位相同,否則舊運行編號會變、查重失效、舊掃描全部重跑——遷移時要先寫一個逐位對照的測試。
- 失敗運行判定的正本現住讀取層 `web/data.py:110 is_failed_run`;執行台落格時已經有基準年化,應該呼叫**同一份正本**落一格,不可另寫第二套判準。
- 合約用 `Protocol` 還是基類:基類方便共用 helper,但會誘使策略去繼承編排——那正是要拆走的東西,故選 `Protocol`;若日後發現三條策略都要抄同一段 helper,即是合約還未夠深。
- `karst/sweep/__init__.py` 現時 52 個對外名;適配檔消失後要順手收窄,否則模組深度沒有改善,只是把淺的東西搬了個位。
- 新詞「策略合約 / strategy contract」、「策略執行台 / strategy executor」、「批次登記 / batch registry」按規矩要落 `CONTEXT.md`,本次唯讀未落。
- D-038 要求每條策略建置期與用戶對齊旋鈕、掃描範圍與代表格揀法,而現庫那批示例取值(突破回望 59 日、單筆風險 2% 一類)未經對齊、不算現役設定;「已對齊／示例」這一格要落在參數集還是批次登記,未定——落錯層會令畫面分不出兩者。
- `sweep_trend_swing` 現時交出的那張表沒有判讀,搬入執行台後趨勢波段第一次要揀判讀目標與三個門檻,而那正是 D-038 要與用戶對齊的東西之一,不可以由代理揀。

---

## 8. 對 D-042 批次畫面的影響

**現況**:程式裡沒有一個叫批次的東西。一次掃描在庫裡的痕跡只有運行表上一格 `sweep_id` 字串(`store.py:1745` 一帶),其餘全在 `experiments/` 底下的 CSV;`web/api_sweep.py:240` 直接 `pd.read_csv` 掃實驗目錄反推——那是全站唯一真正繞過定義庫的地方,而且那個檔 959 行零測試。同一份掃描結果被整形兩次(`sweep/report.py` 寫 CSV、`api_sweep.py` 由 CSV 反推),欄名常數手抄,`_choice_axes_from_layer` 甚至把層標籤字串反解回選擇軸名。

**執行台補上的那一列(批次登記)**:`sweep()` 收工時經唯一入口寫一列批次——掃描編號、策略名與版本、期間、數據快照、引擎與版本、總格數、達標格數、隱藏的失敗運行條數、中位年化、中位 Sortino、中位最大回撤、判讀目標與三個判讀門檻、最佳格、代表格、批內最佳單次的運行編號、報告落點與內容雜湊。經入口寫即蓋寫入者簽章,並應入治理清單,`karst verify` 核得到(順帶補上架構審視候選二點名的那類缺口)。

那幾個中位數不是為了好看:D-042 明文把**最佳批次**定義為「達標運行的中位數年化最高」,而門面左半就是這四個數(N 條達標/M 條、中位年化、中位 Sortino、中位最大回撤)。它們現時要由 CSV 反推。

**批次層畫面因此讀得到**:

- **最佳批次**由庫一句排序算得出,不必讀 CSV;
- **密度熱帶**只需要「這個批次的達標運行清單」——由運行表的 `sweep_id` 查得到,逐條讀既有淨值序列;疊上去的三條線(批內最佳單次、SPY、QQQ)其中第一條已在批次登記那一列;
- **批內選次**就是同一個批次之內揀一條運行作篩選(不是另一頁),兩層用同一份數,不會出現「批次層一個數、運行層另一個數」;
- **達標比率與隱藏條數**與策略總覽的失敗運行判定同出一份正本(見第七節),兩頁對得上——D-042 明令門面要標明隱藏了幾多條失敗運行,現時無處讀。
- D-042 同時取消運行詳情頁與參數格熱力圖頁,即是 `api_sweep.py` 那條由 CSV 反推的路本來就要重寫;執行台的批次登記正好是它的替代來源,重寫成本最低的時機就是現在。

**不影響運行編號**:掃描編號本來就不入運行編號(KARST-054),批次登記是**加一列**,舊掃描可以事後補登記,既有運行一個位都不動。這一點令遷移可以分兩步:先上合約與執行台(運行編號逐位不變,以現有掃描逐格對回落檔自檢),再上批次登記與批次畫面。
