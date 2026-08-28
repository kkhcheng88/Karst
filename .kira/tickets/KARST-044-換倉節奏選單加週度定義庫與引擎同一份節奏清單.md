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
closed: 2026-08-28
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

週度換倉的參數集自此登記得入定義庫並跑得出回測。KARST-043 發現引擎認得週度,但定義庫的節奏選單只有日/月/季,週度參數集登記不了;兩邊各有一份清單違反單一定義。範圍:節奏清單只留一份正本,定義庫與引擎共用;加週度;不設預設。

## 驗收條件

- [x] 節奏清單全倉只有一份正本,定義庫校驗與引擎同取一處
- [x] 週度參數集經唯一入口登記成功並跑得出一次回測
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

· 2026-08-28 10:20 **收檔**:三條驗收條件全數做完。週度換倉的參數集自此登記得入定義庫、
跑得出回測;節奏清單全倉只有一份正本,加一個節奏庫身自己跟住走,不會再出現
「引擎認得、庫身收不到」。本機真庫已就地搬好,4,090 個參數集一列不動、簽章全數仍然有效。

裁決:改 `param_set` 表結構獲准,照下面 09:51 那條留言四步做——**主 agent 依用戶
「單一定義」一句推出**(節奏清單只可有一份正本;本票的驗收條件本來就要求週度登記成功),
不是用戶裁決。

補上一條未做的驗收條件:

- **[已做] 週度參數集經唯一入口登記成功並跑得出一次回測** —— 庫身那條 CHECK 已經歸位:
  `karst/schema.py` 不再逐個字寫死節奏,建表那一刻由正本 `karst.engine.contracts.CADENCES`
  砌出取值表(遲到匯入,做法照 `store.py` 那條現成路;`DDL` 改由模組層 `__getattr__`
  即場砌出,呼叫端一個字不用改)。SCHEMA_VERSION 6 → 7。
  週度經 `karst strategy register --cadence weekly` 一句寫得入庫,再用庫身讀回的那個節奏
  跑出一次完整回測(90 根 K 線排得出十幾次換倉,逐日淨值無缺口),跑完 `karst verify`
  全庫清白。
- **舊庫遷移** —— 偵測到庫身收的節奏與正本對不上,重開時就地重建 `param_set`
  (新表同欄位只換 CHECK → INSERT SELECT → DROP → RENAME → DDL 補回觸發器),
  全程一個交易,前後收放 `PRAGMA foreign_keys`,完事跑 `PRAGMA foreign_key_check`。
  只在偵測到舊版時跑一次,重開不重跑。
  **本機真庫實搬**(動之前已整檔備份到 `~/.claude/backups/karst.sqlite.2026-08-28.bak`):
  `param_set` 4,090 列、`param_value` 19,889 列、`gateway_write` 的 4,090 個 param_set 簽章,
  三樣逐位相同;`param_set_id` 由 1 到 4,090 原封不動,自增序號仍然接住 4,090;四條觸發器
  補回、外鍵與完整性檢查清白;搬完 `karst verify` 照舊「全庫清白」。
- **既有運行再核對一次** —— 搬表之後兩個示例運行重跑:`run-f4c162e5aac34347`(季度,
  累計 +321.86%、最大回撤 −34.93%)與 `run-728a01087531258f`(日度規則路徑,累計 +249.83%、
  最大回撤 −20.84%),編號與成績一字不差,腳本自己那道核對閘全過,兩個 `summary.json`
  經 git 核對逐位相同(無改動)。

測試:新增 `tests/test_cadence_weekly.py` 兩條——
`test_a_weekly_param_set_registers_through_the_gateway_and_runs_a_backtest`(週度經唯一入口
登記、用庫身讀回的節奏跑回測、跑完 verify 清白)與
`test_an_old_database_migrates_in_place_without_touching_a_single_row`(把一個現成的庫改回
舊 CHECK 再重開:三個參數集的 id 與內容逐個不變、觸發器仍在、外鍵清白、版本印記跟上、
verify 清白、週度自此寫得入、第二次開庫不再搬)。上面 09:51 已有那兩條(正本唯一、
每個節奏都收得住)仍在 `tests/test_definition_store.py`。
**全倉 `python -m pytest -q` 140 個測試全過。**

**產物**:`karst/schema.py`(改)、`tests/test_cadence_weekly.py`(新增)。
`karst/store.py`、`karst/gateway/` 這一程一個字都不用改——庫身歸位之後,上面兩層本來
就已經取同一份正本。

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

· 2026-08-28 10:20 上一條舉手已有裁決:**准**,照那四步做,已全部做完。
裁決人是主 agent,**依用戶「單一定義」一句推出**——節奏清單只可有一份正本,而本票的
驗收條件本來就要求週度登記成功。**用戶本人沒有就這件事講過話**,不要記成用戶裁決。

搬表比原本估的多做兩件:(一)偵測改為「比對庫身現有的 CHECK 收哪幾個節奏與正本
對不對得上」,不是靠版本號印記——這樣正本日後再加一個節奏,舊庫重開一樣會自己跟上;
(二)新表的欄位名不在遷移碼裡另抄一份,即場向舊表自己問(`PRAGMA table_info`),
免得「同欄位」這件事又多一份影像。