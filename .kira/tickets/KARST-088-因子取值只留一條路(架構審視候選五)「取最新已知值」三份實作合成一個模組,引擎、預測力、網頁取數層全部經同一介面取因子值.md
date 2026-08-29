---
id: KARST-088
title: 因子取值只留一條路(架構審視候選五):「取最新已知值」三份實作合成一個模組,引擎、預測力、網頁取數層全部經同一介面取因子值
type: task
createdAt: 2026-08-30
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-087]
claimedBy: agent-088
epic: V1 建置
deliverable: KARST-D03
closed: 2026-08-30
---

## 工作內容

源自 research/2026-08-30-architecture-review-backend.md 候選五(用戶 2026-08-30 授權:技術性候選全部做)。完成後:(1) 「按知情時點取最新已知因子值」只有一個模組、一個介面(輸入:快照、因子版本、知情時點、實體集合;輸出:因子面板),知情時間閘、可執行時點、不可執行值的處理全部住在它裡面;(2) 定義庫內 factor_value 小批人手值與 Parquet 批次兩個來源都收在該介面之後,呼叫者分不出來源;(3) 引擎的 FactorValueSource、預測力 factorpredict、網頁取數層三處改為呼叫它,舊的三份實作刪除;(4) 一組對照測試:同一快照同一時點,三處呼叫者取回的面板逐格相同;既有 IC 實驗結果(experiments/2026-08-29-factor-ic/summary.json)重跑一次逐位不變。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 karst/web/static/ 與 prototype/。

## 驗收條件

- [x] 只剩一個「最新已知值」模組;三處呼叫者經同一介面;舊實作已刪
- [x] 對照測試逐格相同;IC 實驗重跑逐位不變
- [x] 只跑所涉測試檔

## 結果

**三份實作本來一致,沒有分歧。** 候選五要抓的靜默分歧,這一次抓不到:同一批數
逐格對過,三條路答的是同一個數。

新模組 `karst/factorvalues.py`(`FactorValueReader`),四種問法,全部無參數預設值:

| 問法 | 交出什麼 |
|---|---|
| `latest_known(reference, as_of, *, snapshot_id, entity_ids)` | 每個實體截至該知情時點最新已知的一個值 |
| `value_for(reference, entity_id, as_of, *, snapshot_id)` | 單點查詢;查不到即 `NOT_APPLICABLE`(不參與,不是 0) |
| `history(references, *, snapshot_id, as_of, start, end, entity_ids)` | 整段長表(給預測力對齊用) |
| `panel(reference, *, snapshot_id, as_of, start, end, entity_ids)` | 「事件時點 × 實體編號 → 值」寬面板 |

知情時間閘、最新已知值的挑法、不可執行值的處理全部住在它裡面;定義庫的
`factor_value` 表與因子值批次(Parquet)兩個住處收在介面之後,呼叫者分不出一個值
來自哪一邊。`snapshot_id` 沒有預設:指名一份即當「我要那一份批次上的值」,查無
登記就拋 `NotFound`(「沒有算過」不可以用空表頂替);傳 `None` 即當「全部住處
一齊看」,批次那邊一個都沒有就由表補。

刪掉的三份:`karst/engine/factorvalues.py`(整個檔,`FactorValueSource`)、
`DefinitionStore.latest_known_values` 與 `value_for`(store.py 那條 SQL 視窗函數)、
`FactorValueStore.read_panel`(factorstore.py)。

**票面「三處呼叫者」實為兩處。** `karst/web/` 五個檔全域搜 `factor_value` /
`latest_known` / `read_long` / `read_factor_values` / `knowledge_time` /
`executable_time` 一個都沒有——網頁層讀的是運行產物(`reader.runs.factor_scores`
那份 parquet)與因子登記中介資料,從來不按知情時點取因子值。已落
`.kira/assumptions.jsonl` A-013。真正的生產呼叫者兩處,兩處都已換路:引擎選股
(`karst/engine/selection.py`)、因子預測力(`karst/gateway/cli.py` 的 `factor-ic`)。

待收貨。

## 留言

### agent:agent-088 · 2026-08-30 06:11
**三處是否本來一致:是,一格都沒有分歧。** 候選五怕的靜默分歧,這一次抓不到。

**新模組位置與介面**:`karst/factorvalues.py`,類 `FactorValueReader(store, root)`(`root` 無預設——批次檔放在哪是呼叫那一層答的事)。四種問法,每一格參數都要呼叫方明寫,沒有預設值:

* `latest_known(reference, as_of, *, snapshot_id, entity_ids)` —— 每個實體截至該知情時點最新已知的一個值(即詞彙表「最新已知值」那張面板);
* `value_for(reference, entity_id, as_of, *, snapshot_id)` —— 單點查詢,查不到回 `NOT_APPLICABLE`(不參與,不是 0);
* `history(references, *, snapshot_id, as_of, start, end, entity_ids)` —— 整段長表,給預測力對齊用;
* `panel(reference, *, snapshot_id, as_of, start, end, entity_ids)` —— 「事件時點 × 實體編號 → 值」寬面板。

知情時間閘、最新已知值的挑法、不可執行值的處理全部住在它裡面。定義庫的 `factor_value` 表(小批人手值)與因子值批次(Parquet)兩個住處收在介面之後,呼叫者分不出一個值來自哪一邊;同一個鍵兩邊各有一個**不同**的值即當場拋 `ContractViolation`(那是矛盾,不是重複,不靜靜揀一個)。`snapshot_id` 沒有預設,呼叫方一定要答:指名一份快照即當「我要那一份批次上的值」,查無批次登記就拋 `NotFound`(「沒有算過」與「算過而無值」是兩件事,不可以用空表頂替);傳 `None` 即當「全部住處一齊看」,批次那邊一個都沒有就由表補。

**刪了哪三份**:(1) `karst/engine/factorvalues.py` 整個檔(`FactorValueSource`,兩者合流那份,249 行);(2) `DefinitionStore.latest_known_values` 與 `DefinitionStore.value_for`(`karst/store.py`,sqlite 那條 `ROW_NUMBER()` 視窗函數);(3) `FactorValueStore.read_panel`(`karst/factorstore.py`,Parquet 那條寬面板)。`read_factor_values` 與 `read_long` 留下來——它們只交回原本那幾列,是讀庫/讀檔層,不是「揀哪一列」;揀法自此只有一份。

**票面「三處呼叫者」實為兩處。** `karst/web/` 五個檔(`data.py` 815 行、`api_strategy.py`、`api_overview.py`、`api_sweep.py`、`api_jobs.py`)全域搜 `factor_value` / `latest_known` / `read_long` / `read_factor_values` / `knowledge_time` / `executable_time`,一個都沒有:網頁層讀的是運行產物(`reader.runs.factor_scores(run_id)` 那份 parquet)與因子登記中介資料(`data.py:71 factor_payload`),從來不按知情時點取因子值。若照票面字面做,就要在網頁層生一條沒有人用的取值路徑再去比對它,對照測試看似三方一致、實情只證明新模組自己等於自己。已落 `.kira/assumptions.jsonl` 的 A-013。真正的生產呼叫者兩處,兩處都已換路:引擎選股 `karst/engine/selection.py`、因子預測力 `karst/gateway/cli.py` 的 `factor-ic`。

**對照測試**:`tests/test_factorvalues.py`,11 項,全綠。先在**舊實作未刪之前**跑一次三方對照(舊甲 sqlite 那條、舊乙 Parquet 那條、舊丙合流那份,對三條因子——值住檔的、值住表的、兩邊都有的——逐日逐格比),全部通過;然後把舊三份當日交出來的那幾格抄成凍檔 `tests/frozen/karst-088-retired-implementations.json`,才動手刪。所以刪完之後這裡比的仍然是那三份的輸出,不是新模組自己等於自己。舊乙的**長表** `read_long` 不入凍檔——它留在原地,照舊即場對照。另外兩項是生產呼叫者換路前後不變:引擎那張「決策日 × 實體」因子面板逐格等於取值口逐日取回的值;預測力那條由新模組餵入與由 `read_long` 餵入,對齊表與 IC 摘要逐格相同。

**IC 重跑**:`experiments/2026-08-29-factor-ic/run_factor_ic.py` 改行新模組後在生產庫上重跑一次(兩個宇宙 × 三個持有期 × 158 條 = 948 行,用時 1,583 秒;原本 1,504 秒)。與舊 `summary.json` 逐位比對:**948 行、0 格不同**;剔走 `seconds` 那一行之後整份檔的 SHA-256 完全相同(`3471ae1ef36e9ce1…`)。唯一不同的一格就是用時本身。即是說兩個住處合流之後,Alpha158 那批值一格都沒有變——`factor_value` 表對這些因子版本沒有任何一列,合流沒有帶進第二個講法。

**跑了哪些測試檔**(只跑所涉,沒有跑全局,亦按派工明令沒有跑 `test_web_jobs`):`tests/test_factorvalues.py`、`test_definition_store.py`、`test_engine_factor_batch.py`、`test_factor_parquet.py`、`test_engine_ranking_rebalance.py`、`test_cadence_weekly.py`、`test_risk_layer.py`、`test_factorpredict.py`、`test_gateway.py`、`test_alpha158_ingest.py` —— 一次過 **81 項全綠**。`ruff` 對 `karst/` 與改動過的測試檔清白(順手清走 `store.py` 因刪 `value_for` 而剩下的兩個 unused import)。

**其他**:詞彙表 `CONTEXT.md` 加「因子取值口 / factor value reader」;`karst/__init__.py` 匯出 `FactorValueReader`,套件說明文字由 `store.value_for` 改為取值口的寫法;`karst/schema.py` 與 `karst/gateway/alpha158.py` 兩處指向舊 API 的說明一併改正。動庫之前已備份到 `C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-088.bak`(IC 重跑唯讀,庫身無改動)。沒有 commit。

**留一格給下一手**:`NOT_APPLICABLE` 這個「不參與」標記,自此只有取值口的 `value_for` 用得着,而 `value_for` 在 `karst/` 內零個生產呼叫(本票之前它住在 `DefinitionStore`,一樣是零)。留住它是因為「缺失 ≠ 0」這條是 D-021 第 4 條的正身,不是死碼;但要不要連同這個標記一齊退役,是另一張票的事,本票不動。
