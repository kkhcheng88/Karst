---
id: KARST-044
title: 換倉節奏選單加週度:定義庫與引擎同一份節奏清單
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-043]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

週度換倉的參數集自此登記得入定義庫並跑得出回測。KARST-043 發現引擎認得週度,但定義庫的節奏選單只有日/月/季,週度參數集登記不了;兩邊各有一份清單違反單一定義。範圍:節奏清單只留一份正本,定義庫與引擎共用;加週度;不設預設。

## 驗收條件

- [x] 節奏清單全倉只有一份正本,定義庫校驗與引擎同取一處
- [ ] 週度參數集經唯一入口登記成功並跑得出一次回測
- [x] 既有日/月/季運行編號與成績逐位不變

## 結果

· 2026-08-28 09:51 **未收檔**:三條驗收條件做起兩條,餘下一條卡在派工範圍以外的一個
檔,已在下面舉手。

逐項對驗收條件:

- **[已做] 節奏清單只有一份正本** —— 正本定在引擎合約 `karst.engine.contracts.CADENCES`
  (它本來就有週度)。`karst/store.py` 以前另存一份日/月/季的清單,現已刪走:
  `_check_cadence` 改為即場向正本取清單,`REBALANCE_CADENCES` 改為由正本推出來
  (經模組層 `__getattr__`,呼叫端一個字不用改)。本檔只留一份 `_CADENCE_LABELS`
  中文名對照——名不是選單:正本多一個節奏而這裡漏了中文名,就用取值本身頂上,
  不會反過來令那個節奏收不到。正本要遲到用時才匯入,因為 `karst.engine` 反過來
  要匯入 `store`,寫在檔頭會兜成一個圈。
  測試:`tests/test_definition_store.py::test_the_cadence_menu_has_exactly_one_source_of_truth`
  (兩邊取值逐個對得上;臨時在正本加一個節奏,定義庫即刻認得)與
  `::test_the_store_validates_every_cadence_the_engine_knows`(引擎認得的每一個節奏
  定義庫都收得住,不在正本的照樣拒收,缺節奏照樣拒收)。
- **[未做] 週度參數集登記成功並跑得出回測** —— Python 那一層已經收得到週度,引擎亦
  一早算得出週度排期(實測 2024 Q1 有 13 個決策日、12 次可執行換倉)。**卡住的是庫身**:
  `param_set` 表有一條 `CHECK (rebalance_cadence IN ('daily','monthly','quarterly'))`,
  週度一寫就被 sqlite 當場擋住(`IntegrityError: CHECK constraint failed`)。那條約束
  住在 `karst/schema.py`,而且改它就是改表結構——兩樣都在本次派工明文劃走的範圍以外。
  做法已寫在下面留言,等人裁決。
- **[已做] 既有日/月/季運行編號與成績逐位不變** —— 兩個示例運行重跑:
  `run-f4c162e5aac34347`(季度)與 `run-728a01087531258f`(日度規則路徑)編號不變,
  腳本自己核對「一字不差」,兩個 `summary.json` 經 git 核對逐位相同。全倉 137 個
  測試全過。

## 留言

· 2026-08-28 09:51 raised:要人裁決——**准不准改 `param_set` 的表結構**。

週度走不到最後一步,只差庫身那條 CHECK 約束。sqlite 改不到 CHECK,只可以整張表重建。
做法(建議一併做,免得同一件事第三次各走各路):

1. `karst/schema.py` 那條 CHECK 不要再逐個字寫死節奏,改為由同一份正本
   (`engine.contracts.CADENCES`)砌出來——正本加一個節奏,DDL 自己跟住走,
   不會再出現「引擎認得、庫身收不到」。
2. 舊庫要重建 `param_set`:開一張新表(欄位一模一樣,只換 CHECK)、
   `INSERT INTO 新表 SELECT * FROM param_set`、`DROP TABLE param_set`、改名、
   再讓 DDL 補回四條觸發器(`trg_param_set_no_update` / `no_delete` /
   `trg_param_value_*`,它們隨舊表一齊消失,但 DDL 是 `IF NOT EXISTS`,重開即補)。
   全程包一個交易,前後 `PRAGMA foreign_keys` 收放,完事跑一次 `PRAGMA foreign_key_check`。
3. **`param_set_id` 必須逐個原封搬過去**:入口簽章是按 `param_set[<id>]` 這個 row key
   記的,`param_value` 亦以它做外鍵。取值一個字不改,所以內容雜湊不變、簽章仍然有效
   ——搬完 `karst verify` 應該照舊清白,這一點要當作驗收條件之一。
4. 收工前補一個測試:週度參數集經唯一入口登記成功,並跑得出一次回測。

範圍不大(一條約束加一段搬表),但它動的是已落庫的定義表,所以不由代理自把自為。