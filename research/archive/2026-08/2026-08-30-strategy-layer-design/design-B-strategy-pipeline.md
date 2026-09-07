# 設計 B:執行優先 / 數據流角度 —— 把「一次運行」設計成一條管線

> 唯讀設計,未改動任何程式碼。這是「設計兩次」的其中一份;另一份由合約優先角度寫,之後由第三者比較。
> 詞彙照 `CONTEXT.md`;架構詞用模組/介面/實作/深度/接縫/適配器/槓桿/局部性。
> 依據:`research/2026-08-30-architecture-review-backend.md` 候選一與候選四;裁決 D-008、D-013、D-020、D-021、D-029/D-042、D-038;規格第 6.1–6.5、7.1–7.4 節。

## 0. 出發點

不由「策略是什麼」出發,由「一次運行由輸入到落庫經過什麼」出發。現時一次運行實際走這八段:

```
① 取快照 → ② 組面板 → ③ 策略段(出目標比重表 / 出事件規則參數,兼出選股痕跡)
        → ④ 風控層 → ⑤ 引擎 → ⑥ 指標 → ⑦ 運行登記 → ⑧ 選股痕跡落檔
```

八段之中,**只有第三段逐條策略不同**。其餘七段在 `trend_swing.py`、`factor_mix.py`、
`factor_rotation.py` 三個檔各抄一次,在 `sweep/factor_mix.py`、`sweep/factor_rotation.py`
再各抄一次,在實驗腳本與 `web/api_jobs.py:836-920` 又各抄一次。逐行比對可見的最長一段是
15 行連續逐字相同(`factor_mix.py:692-706` ‖ `factor_rotation.py:1502-1516`,即落痕整個函式身)。

更差的一件:**掃描本身有兩套實作**——`karst/sweep/runner.py` 的 `run_sweep` 一套,
`karst/risk/sweep.py` 的 `sweep_risk_settings`(:163)另一套,趨勢波段走的是後者。

所以設計的主張只有一句:**這條管線是一個模組,策略只是它中間可換的一段。**
「一次運行」與「一次掃描」是同一條管線的兩個入口——掃描不過是同一條管線跑 N 個參數格,
而 ①② 兩段只做一次、N 格共用。

---

## 1. 接縫放在哪裡

### 1.1 外部接縫(呼叫者看得見、日後會換件的)

| 接縫 | 為什麼是外部 | 現時證據 |
|---|---|---|
| **策略段**(`StrategyStep`) | v1 規劃五條策略,已寫三條,第四第五條(D-015 Minervini、D-018 錯殺)未動手 | 三條實作已存在,不是假想 |
| **引擎適配層**(`PortfolioEngine` / `RuleEngine`) | D-007 第 3 條裁死「引擎是可換件」;`CostedEngine`(`sweep/factor_mix.py:154`)已經是第三個實作 | 真接縫,不動 |
| **快照來源** | 已收在 `karst/data` 的來源適配器之後(D-026 第 6 條) | 真接縫,不動 |
| **唯一入口** | D-020 第 4 條:全部寫入經同一道門 | 真接縫,不動 |

### 1.2 內部接縫(收在管線之內,呼叫者不必知)

組面板、風控設定注入、指標計算、運行登記、選股痕跡落檔、格子迭代、基準曲線快取、
「同一格重掃不重跑」的查重。**這七件現時全部攤在呼叫者面前**,正是「跑一次掃描要自己串十步」的來源。

### 1.3 一個判斷:掃描不是一個接縫,是同一條管線的第二個入口

現時 `karst/sweep` 對外攤 52 個名(架構審視表:深度 71,介面過闊),而它做的事只有一件:
把同一條管線跑 N 次再判讀。把它當成獨立子系統,就要為它另造一套「一格怎樣跑」的協定
(`CellJob`,`sweep/runner.py:101`),於是每條策略再多一個適配檔。
**把掃描收成管線的第二個入口,`CellJob` 這個協定連同兩個適配檔一併消失。**

### 1.4 一個適配器 = 假想接縫,兩個 = 真接縫

- 策略段:三個實作在手、兩個在路上 → **真接縫,設協定。**
- 引擎輸入的兩種形態(目標比重表 / 事件規則參數):見第 3.3 節,**不設兩個適配器**。
- 「假定義庫」:不造。造它等於在 D-020 那道門旁邊開第二道門(見第 5.3 節)。

---

## 2. 管線模組的介面

模組名 `karst/pipeline`。**對外只有四個名**:一個建構、兩個入口、一個結果型別。

### 2.1 建構:`Pipeline(...)`

```
Pipeline(
    *,
    gateway,              # karst.gateway.Gateway,唯一入口
    runs,                 # karst.runs.RunStore
    step,                 # StrategyStep,策略段(見第 3 節)
    strategy_name: str,
    snapshot_id: str,     # 價格快照編號,無預設
    period: tuple[str, str],   # 期間,兩頭都要,無預設
    engine=None,          # 留空即按策略段自報的路徑取預設引擎
)
```

**建構期做完 ①② 兩段**:按 `step.needs()` 所報的快照要求取快照、組面板(價格快照必給;
宏觀快照按需,見第 3.4 節),之後面板不再變。這一句就是「一次運行與一次掃描共用取快照與組面板」
的全部機制——掃描三千格,面板只組一次。

**不設任何參數預設**(D-008 第 3 條、D-009 第 7 條):`snapshot_id`、`period` 缺一即拋;
換倉節奏、風控取值、交易成本一律住在參數集裡,由參數集帶,管線一格都不補。

### 2.2 入口一:`run(...)` —— 一次運行

```
run(
    *,
    param_set_name: str,
    values: Mapping[str, Any],     # 參數集全部取值,無預設,缺格即拋
    cadence: str,                  # 換倉節奏,無預設(D-009)
    origin: str,                   # 正式運行 / 掃描格,無預設(KARST-054)
    sweep_id: str | None = None,   # origin 是掃描格時必給
) -> RunOutcome
```

內部次序寫死:登記(因子 → 策略 → 參數集 → 風控引用,全經唯一入口)→ 讀參數 → 策略段 →
引擎 → 指標 → 落痕 → 選股痕跡。呼叫者一步都不用記。

### 2.3 入口二:`sweep(...)` —— 一次掃描(即一個批次)

```
sweep(
    *,
    grid: SweepGrid,               # 沿用現有 karst.sweep.grid,不動
    sweep_id: str,                 # 無預設
    objective: str,                # 判讀目標,無預設
    min_trades: int,               # 無效格門檻,無預設
    lonely_peak_margin: float,     # 孤峰門檻,無預設
    plateau_quantile: float,       # 平原門檻,無預設
    param_set_prefix: str,         # 一格一個參數集名
    progress=None,
) -> BatchOutcome
```

逐格呼叫**同一個** `run(origin="掃描格", sweep_id=...)`,跑完交去 `judge`(`sweep/verdict.py:395`,
純函數,架構審視稱為全套件最乾淨那層,一個字不動),再經唯一入口寫一列批次登記(見第 8 節)。

四個判讀門檻無預設,是刻意的:D-016 第 3 條與 `sweep/__init__.py` 現有註釋都寫明「報告一定要印出來」。
代價是 `run()` 與 `sweep()` 簽名不對稱——這是自覺的取捨,不是疏忽(見第 7 節)。

### 2.4 回傳:`RunOutcome` / `BatchOutcome`

- `RunOutcome`:運行編號、八項指標、達標與否、選股痕跡落點、來歷、參數集版本。
- `BatchOutcome`:掃描編號、逐格 `RunOutcome`、判讀(平原/山脊/孤峰/無效格)、來歷一致性、達標比率、
  中位年化/中位 Sortino/中位最大回撤、最佳單次。**D-042 門面所需的數,全部在這裡算好一次。**

### 2.5 不變量

1. 同一組(策略版本 × 參數集 × 期間 × 數據快照 × 引擎版本)永遠同一個運行編號;`sweep()` 內同一格重掃不重跑(KARST-026、KARST-029)。
2. 掃描編號不入運行編號的計算(KARST-054)。
3. 一切寫入經唯一入口,管線一句都不直接開庫(D-020 第 4 條、D-027 護欄二)。
4. 面板在建構期定死;`run()` 不得換面板,故一個批次的來歷必然一致。
5. 可執行時點由因子合約寫死,策略段不得繞過(D-021 第 3 條)。
6. 達標/失敗(D-040)在落格那一刻判一次並寫入,下游不得再算第二次。

### 2.6 錯誤模式

- `ContractViolation`:缺參數(節奏、期間、快照、判讀門檻)、面板型別不對、格子空、策略段回傳形狀不對、`origin` 是掃描格而無掃描編號。
- `NotFound`:快照不在、宏觀序列不在。
- `DuplicateDefinition`:由管線的登記段吸收(現時兩條策略各自 `try/except` 一段,`trend_swing.py:507`、`factor_mix.py` 同段),不再外洩。
- **一格拋錯不中斷整個批次**:記入 `BatchOutcome` 的失敗格清單,判讀時當無效格處理。三千格跑到第 2900 格才炸,重跑代價不可接受。

---

## 3. 策略段的介面

### 3.1 策略作者要交什麼(三個方法 + 一個宣告)

```
class StrategyStep(Protocol):
    def needs(self) -> StrategyNeeds: ...
    def read_params(self, param_set: ParamSet) -> Any: ...
    def step(self, panels: Panels, params: Any) -> StepOutput: ...
```

- **`needs()`** —— 靜態宣告,不碰庫:策略型別、要登記哪幾個因子(名、刻度型、產生程序)、
  要哪幾種面板(K 線面板 / 價格面板)、要不要宏觀序列(哪幾條)。
  管線據此做登記編舞——**這一個宣告,取代 `register_trend_swing`(80 行)與 `register_factor_mix`(80 行)
  那兩段連註釋一字不差的重抄。**
- **`read_params()`** —— 參數集 → 策略自己的參數型別;缺格即拋,一格都不補(D-008、D-038)。
- **`step()`** —— 面板 + 參數 → 引擎輸入 + 選股痕跡 + 旁產物。**這是策略獨有的那一件。**

### 3.2 `StepOutput` 交三件

1. `engine_input`:兩種型別之一(見 3.3)。
2. `selection`:選股痕跡(逐決策日逐層候選、逐日逐隻分數名次;KARST-056)。目標比重路徑天生有,規則路徑可留空。
3. `extras`:策略獨有的旁產物,例如趨勢波段的歷史案例表(`entry_cases`、`cases_frame`、`case_stats`)。管線原樣落檔,不解讀。

### 3.3 兩種策略形態:同一段的一個方法,兩個回傳型別

**取捨:不設兩個適配器,亦不開兩條管線分支;`step()` 只有一個,回傳一個帶標籤的聯合型別。**

- 規則類(K 線面板 → 事件規則):`RuleInput(rule_params)` → 引擎走 `from_order_func`(規格 6.2)。
- 因子類(因子面板 → 排名/比重):`TargetWeightsInput(targets, cadence, initial_cash, fees, costs)` → 引擎走 `from_orders` 目標比重路徑(規格 6.3)。

**為什麼不分兩條管線**:兩條路在八段之中只有第⑤段那一句不同,其餘七段一字不差。
分兩條 = 把七段重抄一次,正是現在這個病的來源。管線只在第⑤段做一次 `match`。

**為什麼不硬夾成一個型別**:硬夾的代價現在看得見——`factor_mix.py:643-646`(與 `factor_rotation.py:1451-1455` 逐字相同那 5 行)被迫用 `RankingRebalanceParams(top_n=len(exposures), direction="high")` 填兩個用不著的格,註釋自認「適配層欠一個與排名無關的組合參數型別」。新的 `TargetWeightsInput` 就是那個缺了的型別。

**為什麼不算兩個適配器**:適配器是「同一個介面的兩個實作」;這裡只是同一個方法的兩種回傳,管線內部一個分支處理——造兩個適配器等於為一件事開兩個假想接縫。

### 3.4 面板那一段會不會分岔

不會。K 線面板(開高低收四張)是價格面板(開收兩張)的超集(`CONTEXT.md`)。
管線一律組 K 線面板,目標比重路徑取其子集。宏觀序列由 `needs()` 宣告(現時
`factor_rotation.macro_series_needed()`:975),管線在建構期一併取,不入策略段。
**未查證的一格見第 7 節。**

---

## 4. 現有三條策略怎樣搬入

### 4.1 趨勢波段 `karst/strategies/trend_swing.py`(981 行)

| 動作 | 對象 |
|---|---|
| **刪** | `register_trend_swing`(:470-549)→ 收成 `needs()` 一個宣告 |
| **刪** | `record_trend_swing_run`(:552)→ 落痕歸管線 |
| **刪** | `sweep_trend_swing`(:932)、`TrendSwingSweepCell`(:868)、`TrendSwingSweepResult`(:909)→ 掃描歸 `Pipeline.sweep()`。**它走的是 `karst/risk/sweep.py` 的 `sweep_risk_settings`(:163),完全不經通用掃描:沒有運行編號查重、不落運行庫、不出平原判讀。** |
| **搬** | `params_grid`(:829)→ 掃描格宣告,歸 `karst/sweep/grid` 一族 |
| **搬** | `build_bar_panel`(:296)→ 管線的組面板段(它不是策略獨有的事) |
| **改** | `run_trend_swing`(:436)→ `step()`:只交 `RuleInput(params.rule_params(risk))`,不再自己呼叫 `run_rule_strategy`、不再收 `engine` 參數 |
| **留** | `TrendSwingParams`(:149)、`param_values`(:257)、`read_setup`(:270)→ `read_setup` 即 `read_params()` |
| **留** | `entry_cases`(:665)、`cases_frame`(:727)、`case_stats`(:791)→ 經 `StepOutput.extras` 交出 |

### 4.2 因子混合 `karst/strategies/factor_mix.py`(706 行)

| 動作 | 對象 |
|---|---|
| **刪** | `register_factor_mix`(:376-467)——與 `register_trend_swing` 那 80 行連註釋一字不差 |
| **刪** | `record_factor_mix_run`(:671)→ 落痕歸管線 |
| **改** | `run_factor_mix`(:609)→ `step()`:刪走 `engine is None` 那段遲到 import(:651-655)與 `RankingRebalanceParams` 那個填空格(:643-649),改交 `TargetWeightsInput` |
| **留** | `resolve_exposures`(:468)、`factor_mix_schedule`(:513)、`factor_mix_targets`(:539)、`factor_mix_selection_trace`(:578) |

### 4.3 因子輪動/宏觀 `karst/strategies/factor_rotation.py`(1,516 行)

它連登記函數都沒有——登記編舞住在掃描適配檔的 `ensure_factor_rotation_setup`
(`sweep/factor_rotation.py:196`),而那個函式的內文**只有一句:整個轉呼 `ensure_factor_mix_setup`**;
連策略型別 `FACTOR_ROTATION_STRATEGY_TYPE`(:85)都直接等於混合那個。它亦沒有掛在
`strategies/__init__.py` 的 `__all__` 上,而且三條策略之中只有它一個選股痕跡都沒有。
**三條策略連「登記、掃描、痕跡住在哪裡」都各行各路,本身就是沒有介面的證據。**

| 動作 | 對象 |
|---|---|
| **刪** | `record_factor_rotation_run`(:1482) |
| **改** | `run_factor_rotation`(:1378)→ `step()`,交 `TargetWeightsInput` |
| **搬** | `_prepare_macro`(:1332)、`macro_series_needed`(:975)→ 前者歸管線的取快照段,後者變 `needs()` 的一格 |
| **不動** | `RotationDriver` 協定(:366)與十個驅動器(`FactorMomentumDriver`:490 至 `FedExpectationDriver`:869)——那是策略段**內部**的第二層接縫,不上管線;換驅動器不改引擎與目標比重路徑(KARST-036) |

### 4.4 掃描適配檔會不會消失

**會,但不是整檔蒸發,是拆三份:**

| 現時 | 去向 |
|---|---|
| `sweep/factor_mix.py` `FactorMixJob`(:218)、`ensure_factor_mix_setup`(:184) | **消失**——`CellJob` 協定連同兩個實作一併不需要 |
| `sweep/factor_rotation.py` `FactorRotationJob`(:225)、`ensure_factor_rotation_setup`(:196) | **消失** |
| `weight_grid`(:41)、`reference_point`(:76)、`rotation_grid`(:123)、`point_slug`(:114) | 留低,歸掃描格宣告一族 |
| `CostedEngine`(`sweep/factor_mix.py:154`) | **搬去引擎適配層**——它是引擎的替換件,不是掃描的事 |
| `scoreboard`(:460)、`segment_excess`(:514)、`cost_comparison`(:598)、`provenance_note`(:658) | 搬去 `sweep/report.py`,是報告工具 |

兩個 Job 值不值得收,逐行比對已經答了:`plan()` 尾段 20 行逐字相同
(`sweep/factor_mix.py:318-337` ‖ `sweep/factor_rotation.py:391-410`)、`_param_set` 13 行逐字相同
(:298-310 ‖ :353-365,連 KARST-046 那句註釋)、`_cadence_of` 9 行逐字相同(:285-293 ‖ :340-348)。
**兩個 Job 之間真正不同的只有中間那一句:一個砌 `FactorMixParams` 跑 `run_factor_mix`,
另一個先 `build_driver` 再砌 `FactorRotationParams` 跑 `run_factor_rotation`。**
那一句正是策略段的 `step()`。

`sweep/runner.py` 的 `run_sweep`(:290)、`CellJob`(:101)、`CellPlan`(:64)三件被
`Pipeline.sweep()` 取代;`SweepCell`、`SweepRun`、`SweepProvenance` 三個結果型別轉成
`BatchOutcome` 的內件。`grid.py`、`verdict.py`、`report.py` 三檔留住不動。

---

## 5. 測試面

### 5.1 經介面測得到什麼

打 `Pipeline` 這一道門,一次覆蓋:登記編舞(缺參數即拋、同名同取值沿用舊版)、運行編號穩定性
(經 `store.run_fingerprint` 同輸入同編號、重掃不重跑)、來歷正確、目標比重表形狀(空白≠0,KARST-023)、
選股痕跡行數與「到達該層」的收窄性(KARST-056;現時三條策略三個做法——混合有自己一個
`factor_mix_selection_trace`、波段借引擎的 `rule_selection_trace`、輪動沒有)、達標/失敗判定(D-040)、
批次登記讀得回、一格拋錯不中斷批次。

**現時這些一件都測不到**,因為沒有一道門可以打——所以才會出現一批靠 `ast.parse`
斷言原始碼文本的測試(`test_trend_swing.py:655`、`test_factor_mix.py:676`,兩檔幾乎逐字重覆)。
**用文本斷言代替行為斷言,正是「沒有介面可打」的病徵。**

### 5.2 保留 / 取代

- **保留**:`test_sweep.py`(格子與判讀;`judge` 是純函數)、`test_engine_*.py` 六個、`test_metrics.py`、`test_risk_layer.py`、`test_runs.py`、`test_selection_trace.py`、`test_definition_store.py`、`test_gateway*.py`。
- **取代**:`test_trend_swing.py`、`test_factor_mix.py`、`test_factor_rotation.py` 三檔之中「登記 + 跑一次 + 落痕」那批(三份 fixture 逐字重抄)→ 收成一份管線測試 × 三個策略段。
- **刪**:兩檔的 `ast.parse` 文本斷言。
- **新增**:一份 `conftest.py`——全倉現時零 conftest、126 個 fixture 跨檔零共用;管線介面正是那個共用落點。

### 5.3 假引擎 / 假定義庫的適配器放哪

- **假引擎放 `karst/engine/`**,與 `VectorbtEngine` 並列,不放測試目錄:它是引擎適配層的又一個實作,`CostedEngine` 已經是先例。好處是「引擎是可換件」這條裁決(D-007 第 3 條)由測試每日行使一次,不是紙上宣告。
- **假定義庫不造。** 造它等於在唯一入口旁邊開第二道門,直接踩 D-020。測試用記憶體 sqlite 起一個真庫,照樣經唯一入口寫——快得起,而且順帶測到寫入者簽章。
- 管線測試的標準接縫組合:**假引擎 + 真庫(記憶體)+ 合成面板**。

---

## 6. 刪除測試:刪掉這個模組,複雜度重現在哪

刪走 `karst/pipeline`,那八段編舞不會消失,它會在**六處**重現:

1. **登記編舞** —— 每條策略一份。現時兩份 80 行,策略版本那 12 行逐字相同(`trend_swing.py:523-534` ‖ `factor_mix.py:439-450`);第四第五條策略落地即四份。
2. **落痕** —— 每條策略一個 `record_*_run`,同一個 11 參數簽名;函式身 15 行逐字相同(`factor_mix.py:692-706` ‖ `factor_rotation.py:1502-1516`)。現時三份。
3. **引擎那句** —— `engine is None` 加遲到 import `VectorbtEngine`,現時三處(`factor_mix.py:653`、`factor_rotation.py:1461`、`sweep/factor_mix.py:173`)。
4. **掃描一格怎樣跑** —— 每條策略一個 `CellJob` 實作加一個 `ensure_*_setup`。現時三個形狀各異(趨勢波段那個甚至住在策略檔裡,而且走另一套掃描)。
5. **十步編舞** —— 每個呼叫者一份。現時實驗腳本一份、`web/api_jobs.py:836-880` 一份。
6. **掃描結果整形** —— 現時 `sweep/report.py` 寫一次 CSV,`web/api_sweep.py:240` 由 CSV 反推第二次,連欄名常數都手抄。

六個呼叫者都要記住同一段東西,即是這個模組在賺錢,值得收成介面。

---

## 7. 風險與未決點(一句一個)

1. 一律組 K 線面板:某些來源或宏觀快照可能砌不出高低價,未查證。
2. 引擎輸入的兩種型別會不會在錯殺策略(D-018,同時要選股閘與進出場規則)之外變成第三種,未知。
3. `RankingRebalanceParams` 換成 `TargetWeightsInput` 若進入運行編號的雜湊,舊運行會全部對不上,要裁。
4. 管線在建構期把面板釘死,三千格全程佔住記憶體,未量。
5. 批次登記是新開一張表,還是靠 `sweep_id` 聚合現有運行表,未裁。
6. `run()` 與 `sweep()` 簽名不對稱(判讀門檻只在後者),是自覺取捨,但會不會令呼叫者以為兩者是兩件事,未驗。
7. 因子輪動現時沒有登記函數,搬入時要補一次首次登記,可能生成一個新策略版本,要事先講明。
8. `DuplicateDefinition` 的處理歸管線還是歸唯一入口,未裁——歸入口更乾淨,但改動範圍大過本次。
9. 策略段宣告因子(`needs()`)是靜態的,而趨勢波段現時會按快照換因子版本(`trend_swing.py:509-515`),靜態宣告載不載得起這個動態,未驗。
10. 選股痕跡不入運行編號、舊運行可以沒有(KARST-056),管線要不要對舊運行補寫,未裁。

---

## 8. 對 D-042 批次畫面的影響

**對得上的地方**:D-042 第 1 條「批次 = 一次參數掃描跑出來的那批運行」,
在這個設計裡就是 `Pipeline.sweep()` 一次呼叫。程式裡第一次有一個叫批次的東西
(架構審視候選四原話:「D-042 已把批次變成第一等概念,但程式裡現時沒有一個叫批次的模組」)。
**順帶補一個現時的空白**:趨勢波段的掃描不落運行庫,所以它在 D-042 的批次畫面上**一個批次都沒有**;
收入管線之後,三條策略才第一次在同一個批次表上比得到。

**必須補的一件:掃描結果要落庫,不只落檔。**
現時掃描結果只寫 CSV(`sweep/report.py:400` `write_report`),網頁層由 CSV 反推
(`api_sweep.py:240` 直接 `pd.read_csv` 掃實驗目錄——全站唯一真正繞過定義庫的地方,而且 959 行零測試)。
D-042 要的「最佳批次 = 達標運行的中位數年化最高」是**跨批次排名**,在一堆散落的 CSV 上算不出來。

**建議**:`sweep()` 收尾時經唯一入口寫一列批次登記,欄位直接對住 D-042 的門面:
掃描編號、策略名、策略版本、格數、達標數、達標比率、中位年化、中位 Sortino、中位最大回撤、
最佳單次運行編號、四個判讀門檻的取值、來歷一致性。

**逐項對上 D-042**:

| D-042 條文 | 這個設計怎樣供得起 |
|---|---|
| (2) 最佳批次 = 達標中位年化最高 | 批次登記一句 SQL 排序;不用讀任何 CSV |
| (4) 密度熱帶 = 批內每條達標運行的淨值疊起 | 批次登記給「這批哪幾條達標」→ `RunStore.equity_curve(run_id)` 逐條讀;現有路徑,不用新增 |
| (5) 掃描批次表可切換 | 就是批次登記表本身,一行一批 |
| (6) 批內選次 = 批次的篩選器 | 批次 → run_id → 現有運行讀取,不開新路 |
| (7) 批次層持股分布(頻率、平均持有日數、平均累計報酬) | 由該批達標 run_id 逐條 `RunStore.holdings()` 聚合;聚合歸後端,不歸網頁層(候選六) |
| (4) 熱帶只計達標運行、門面標明隱藏幾多條失敗運行 | 達標/失敗由管線在落格那一刻判一次寫入(不變量 6);網頁層不再自己算第二次 |

**順帶收掉的一個病**:失敗運行(D-040)的判定口徑現時可以在網頁層另算一套
(`api_strategy.py:366 _row_metrics` 已經為速度另寫一套指標口徑,docstring 自認)。
管線在落格時判死,批次登記帶住,網頁層只讀不算——這正是詞彙表「薄 REST 層」原本的意思。
