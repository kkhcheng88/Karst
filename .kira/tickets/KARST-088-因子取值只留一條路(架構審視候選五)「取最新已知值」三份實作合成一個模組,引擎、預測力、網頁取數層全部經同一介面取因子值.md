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
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

源自 research/2026-08-30-architecture-review-backend.md 候選五(用戶 2026-08-30 授權:技術性候選全部做)。完成後:(1) 「按知情時點取最新已知因子值」只有一個模組、一個介面(輸入:快照、因子版本、知情時點、實體集合;輸出:因子面板),知情時間閘、可執行時點、不可執行值的處理全部住在它裡面;(2) 定義庫內 factor_value 小批人手值與 Parquet 批次兩個來源都收在該介面之後,呼叫者分不出來源;(3) 引擎的 FactorValueSource、預測力 factorpredict、網頁取數層三處改為呼叫它,舊的三份實作刪除;(4) 一組對照測試:同一快照同一時點,三處呼叫者取回的面板逐格相同;既有 IC 實驗結果(experiments/2026-08-29-factor-ic/summary.json)重跑一次逐位不變。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 karst/web/static/ 與 prototype/。

## 驗收條件

- [ ] 只剩一個「最新已知值」模組;三處呼叫者經同一介面;舊實作已刪
- [ ] 對照測試逐格相同;IC 實驗重跑逐位不變
- [ ] 只跑所涉測試檔

## 結果

## 留言
