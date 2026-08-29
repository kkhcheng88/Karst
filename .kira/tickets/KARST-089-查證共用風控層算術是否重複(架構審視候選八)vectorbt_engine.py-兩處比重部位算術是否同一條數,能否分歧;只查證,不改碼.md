---
id: KARST-089
title: 查證共用風控層算術是否重複(架構審視候選八):vectorbt_engine.py 兩處比重/部位算術是否同一條數,能否分歧;只查證,不改碼
type: task
createdAt: 2026-08-30
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: agent-089
epic: V1 建置
deliverable: KARST-D03
closed: 2026-08-30
---

## 工作內容

源自 research/2026-08-30-architecture-review-backend.md 候選八(D-043:先查證再決定開不開實作票)。審視指 karst/engine/vectorbt_engine.py 約 213 行與約 324 行兩處各自計算共用風控層的部位/比重算術,懷疑同一條數寫了兩次。完成後:(1) 兩處算術逐項對照表(輸入、公式、四捨五入、邊界處理)落檔 experiments/2026-08-30-risk-layer-arith/README.md;(2) 一個對照腳本:用現有正式運行的參數集各跑兩處算術,報告是否逐位相同,結果檔落同一目錄;(3) 結論三選一寫在票上:甲 完全相同、應合併(附建議的單一模組位置);乙 刻意不同、各有理由(附理由與應加的註解位置);丙 已經分歧、結果數字受影響(列出受影響的運行編號,並寫入 .kira/assumptions.jsonl)。不改 karst/;只跑對照腳本;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/。

## 驗收條件

- [x] 對照表與對照腳本及結果檔已落 experiments/2026-08-30-risk-layer-arith/
- [x] 票上有甲/乙/丙結論;若丙則 assumptions 已記
- [x] 未改 karst/

## 結果

**乙:刻意不同、各有理由,不應合併。** 甲處 `_order_rules_nb`(第 207–219 行,
njit 純量,`from_order_func` 正路)與乙處 `VectorbtSignalMatrixEngine.simulate_rules`
(第 319–328 行,numpy 向量,`from_signals` 對照臂)是刻意對齊的孿生碼,不是失手
寫了兩次:乙處存在的目的就是用另一條引擎路重算一次做對照,合併會令對照自我印證。

12 個參數集 × 18 個輸入 = 216 格,204 格逐位相同;唯一分歧的 12 格要成交價細到
5e-324(浮點次正規數)才踩得到,真實股價去不到。**對盤數沒有影響**:乙處那條路
(`vectorbt-signals`)一個運行都未曾產出過。所以不是丙,沒有寫 assumptions。

產出:`experiments/2026-08-30-risk-layer-arith/`(`README.md` 逐項對照表、
`compare.py`、`result.json`)。定義庫唯讀開啟,`karst/` 一個檔都沒有改。

建議(另開票才做,本票不動):兩處都只加註解——甲處第 212–219 行之上補一句回指
對照臂,第 216–219 行註明乙處多一道 `isfinite` 閘。

待收貨。

## 留言

### agent:agent-089 · 2026-08-30 04:58
結論:**乙 —— 刻意不同、各有理由,不應合併**。

**兩處在哪**(2026-08-30 當日行號):甲處 `_order_rules_nb` 第 207–219 行(njit 純量,走 `from_order_func` 正路);乙處 `VectorbtSignalMatrixEngine.simulate_rules` 第 319–328 行(numpy 向量,走 `from_signals` 對照臂)。

**為什麼是乙,不是甲**:乙處是對照臂,存在的目的就是用另一條引擎路重算一次,證明兩條路算得出同一個數;源碼第 323 行那句註解「與 `_order_rules_nb` 逐個運算符對齊,好令兩條路算出同一個浮點數」寫明了貼成一樣是刻意的。合併會令對照變成自我印證,證不到嘢;而且甲處是 njit 內圈純量碼、乙處是整張矩陣的 numpy 碼,形態本身也合不埋。兩處唯一一個語意上的真分別是注碼基數——甲處預設取當下權益,乙處只能取起始本金,因為 `SignalContext` 看不見組合的現金與權益;乙處的處理不是靜靜當作起始本金,而是當場拋 `RuleNotExpressible` 拒收(第 313–317 行)。這一格在 `RiskFractionSizing` 的說明已經寫明是對照臂專用。

**對照結果**:12 個參數集 × 18 個輸入 = 216 格,204 格逐位(bit-for-bit)相同。輸入、公式、運算次序、四捨五入(兩處都沒有取整)、以及零/負/缺值/超上限/恰好等於上限各個邊界,全部一致。唯一分歧的 12 格是同一個輸入:成交價細到 5e-324(浮點次正規數)時股數與上限同為 +inf,乙處有 `np.isfinite` 閘擋得住、甲處的 `if shares > cap` 擋不住(`inf > inf` 不成立)。真實股價去不到這個數量級。

**對盤數有無影響:沒有。** 庫內 `vectorbt-signals`(乙處)那條路一個運行都未曾產出過——正式運行 9 個走 `vectorbt-order-func`(甲處)、3 個走 `vectorbt`(目標比重路,不經這兩段算術),掃描 8,305 個全部走 `vectorbt`。所以不是丙,沒有寫 `.kira/assumptions.jsonl`。

**另外兩點要交低**:(1) 庫內 12 個參數集沒有一個原封不動跑得動乙處——每一個都同時踩正它拒收的兩件事(熔斷開住 0.06、基數取 current_equity),腳本要先關熔斷、基數改起始本金才對照得到。(2) 這 12 個全部叫「示例-KARST-028」,按 D-038 未經用戶對齊、不算現役;庫現時就只有這些。取值一改結論仍然成立,因為兩處算式逐個運算符相同,與取值無關。

**建議(不在本票做,要開票才做)**:兩處都只加註解、不改行為——甲處第 212–219 行之上補一句回指對照臂(現時只有乙處那邊寫了對齊,由甲處入手的人看不見還有第二處);甲處第 216–219 行封頂那兩句註明乙處多一道 `isfinite` 閘。

**產出**:`experiments/2026-08-30-risk-layer-arith/README.md`(逐項對照表)、`compare.py`、`result.json`。腳本不是抄一份算術出來重寫,是原地行真碼:甲處用 numba 的 `.py_func` 取回原函式直接呼叫,乙處攔截 `vbt.Portfolio.from_signals` 接住它算好的 `size` 矩陣。定義庫用 `sqlite3` `mode=ro` 唯讀開啟(刻意不行 `DefinitionStore.open()`,那條路會建表兼寫 `schema_meta`)。`karst/` 一個檔都沒有改。
