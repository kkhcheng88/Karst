---
id: KARST-026
title: 回測運行留痕:唯一命名與逐日淨值、持倉序列保存
type: task
createdAt: 2026-08-27
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-021]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-27
---

## 工作內容

每一次回測運行自此可以重算,亦可以不重跑就重看:運行蓋齊策略版本 × 參數 × 期間 × 數據快照得出唯一命名,並保存逐日淨值與持倉序列。保存逐日淨值與持倉序列是本票的重點——它是「檢視視窗(view window)」可以在同一次運行的結果上另揀一段日期重看的前提(規格 7.4、8.5;用戶原話「if I just want to focus on the performance since 2023 then I don't need a rerun?」)。範圍是運行記錄與這兩條序列的保存與讀取,指標計算不在本票。舊運行永不自動更新、只標過時(D-020 第 7 條、規格 7.3)。

## 驗收條件

- [x] 同一組策略版本 × 參數 × 期間 × 數據快照,兩次運行得出同一個唯一名並可重算出同一結果(規格 7.4)
- [x] 逐日淨值與逐日持倉序列逐次運行保存得住,讀得回任何一日的淨值與當日持倉(規格 7.4)
- [x] 由已保存的逐日序列,不重跑引擎就算得出任一子期間的淨值,基準由該段起始日重設(規格 8.5、詞彙表 view window)
- [x] 因子或策略出新版之後,舊運行內容一字不變、只被標為過時(D-020 第 7 條、規格 7.3)

## 結果

· 2026-08-27 23:58 回測運行留痕做齊,四項驗收條件逐項有測試蓋住(`tests/test_runs.py` 五個測試全綠;全倉 21 個測試全綠)。

**驗收 1(同一組輸入得同一個唯一名)** 運行編號 = 「策略版本 × 參數集 × 期間 × 數據快照 × 引擎版本」的內容雜湊(`run-` + sha256 前 16 位)。落雜湊的是**內容**——策略名 + 版本號、參數集逐項的值與換倉節奏、因子名@版本號、期間、快照編號、引擎名 + 版本——不是庫內流水號,故此換一個庫重建同一組定義,算出來仍然是同一個編號。同一組輸入重錄不會多一筆,原封不動回舊記錄(與數據快照登記同制)。期間或任何一件一改即另一個編號。

**驗收 2(逐日序列保存得住、讀得回)** 每次運行三份 parquet,按運行編號分目錄:`<root>/<run_id>/equity|holdings|orders.parquet`;登記表 `run_artifact` 記路徑、內容雜湊與列數(D-026 第 1 條:大批數據住 parquet,單一定義庫只登記落點)。`equity_on(run_id, day)` 讀回任何一日的淨值,`holdings_on(run_id, day)` 讀回當日持倉(實體編號 → 股數)。逐日持倉存長表,沒有那一列就是當日沒持有——與因子值同制,不填 0(D-021 第 4 條)。

**驗收 3(不重跑就重算任一子期間)** `RunStore.window_stats(run_id, start, end)` 只讀已保存的逐日淨值,一條引擎都不碰;淨值由該段起始日重設為 100,回累計回報、年化(252 交易日當一年)、最大回撤(負數表示)。測試證到把全期切開兩段再相乘,與全期一模一樣(段首那一日在兩段都是基準日,回報為零,不會重覆計算);開完視窗之後重新核對三條序列的雜湊,運行一個字都沒變——是重看不是重跑。

**驗收 4(舊運行只標過時,內容一字不變)** `run_stale_reasons(run_id)` 比對運行蓋住的策略版本、參數集版本、因子版本與各自的最新版,逐條講出過時在哪;沒有過時就回空。測試中因子出第 2 版、策略再出第 2 版之後,舊運行仍然蓋住第 1 版,逐日序列與雜湊一字不變,只是查得出已經過時。運行不可改寫設兩道:同一身份錄入不同結果,在動任何檔案**之前**當場拒收(`ImmutabilityViolation`);繞過本層直接 `UPDATE` / `DELETE` 由 sqlite trigger 擋。

**落點**

- 新增 `karst/runs/`:`registry.py`(落痕、讀回、核對)、`window.py`(檢視視窗)、`synthetic.py`(合成序列);測試 `tests/test_runs.py`。
- `karst/schema.py` 追加 `backtest_run`、`run_artifact`、`run_factor_ref` 三張表連不可改/不可刪 trigger;`SCHEMA_VERSION` 2→3(舊庫重開自動補建;版本印記改為跟住升,免得庫身已是新版、印記仍寫舊版)。
- `karst/store.py` 追加 `RunRecord`、`RunArtifact` 與 `run_fingerprint` / `run_id_for` / `register_run` / `get_run` / `list_runs` / `run_stale_reasons` / `run_is_stale`;既有簽名一個都沒改、一張表都沒刪。
- `pyproject.toml` 的 `packages` 加 `karst.runs`,兼補回前一票漏了的 `karst.gateway`。

**接引擎** `RunStore.record_simulation(result, ...)` 只認 `equity_curve` / `holdings` / `orders` 三個欄位,正是引擎適配層 `SimulationOutput` / `BacktestResult` 的形狀;本層刻意不 import `karst.engine`——引擎是可換件(D-007 第 3 條),留痕不應綁死在任何一個引擎的型別上。引擎接上之後換源不用改本層。運行來源現時用 `synthetic_simulation`(同一 seed 同一條線的確定性假序列),只為今日就走通端到端,不是回測。

**未解/風險**

- 「過時」比對的是**最新版**,不是詞彙表的「現役設定」——現役設定是用戶指定紙上交易跟隨的那一個參數集,由誰指定、存在哪裡未有票蓋住;要在畫面上標「非現役」,還欠這一格。
- 序列的內容雜湊經 `pandas.util.hash_pandas_object`,同一個 pandas 版本內穩定;日後大升 pandas 版本,`verify_run` 可能對舊運行報不符(登記本身不受影響)。
- 年化用 252 交易日當一年;日後若改用日曆日,數字會與現時已落痕的運行對不上。
- 新詞兩個未落 `CONTEXT.md`,留給主 session 裁:**運行編號 run id**、**過時運行 stale run**。

## 留言
