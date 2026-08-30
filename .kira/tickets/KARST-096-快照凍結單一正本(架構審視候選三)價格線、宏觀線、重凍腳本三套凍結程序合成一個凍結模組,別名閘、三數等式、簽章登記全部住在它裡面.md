---
id: KARST-096
title: 快照凍結單一正本(架構審視候選三):價格線、宏觀線、重凍腳本三套凍結程序合成一個凍結模組,別名閘、三數等式、簽章登記全部住在它裡面
type: task
createdAt: 2026-08-30
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-094]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

源自 research/2026-08-30-architecture-review-backend.md 候選三(D-043)。KARST-087 已令三處凍結程序全部經唯一入口簽章寫庫,但「凍結」本身(拉數→對齊實體編號→別名閘→三數等式→寫檔→登記)仍有三份實作:karst/data/pipeline.py(價格線)、karst/data/macro.py(宏觀線自己一套)、experiments/2026-08-29-ticker-history/refreeze*.py(重凍)。完成後:(1) 一個凍結模組、一個介面(輸入:宇宙名單或代號歷史對照、日期範圍、數據來源適配器;輸出:快照編號與說明檔),別名閘、三數等式、簽章登記、說明檔格式全部在它裡面;(2) 價格線、宏觀線、重凍三處改為呼叫它,各自只剩「來源適配器」那一段;macro.py 的私家凍結刪除;(3) 對照:用現役 S&P500 快照 2026-08-28-3bf7ab0a522a 的輸入重凍一次,快照編號(內容雜湊)逐位相同,說明檔逐行相同;宏觀線同樣重凍一次比對;(4) CONTEXT.md 加「凍結模組 / snapshot freezer」詞條。動庫前備份到 C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-096.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不遞迴刪 repo 外目錄;不碰 karst/web/static/ 與 prototype/;不 commit。

## 驗收條件

- [ ] 只剩一個凍結模組;三處呼叫者只剩來源適配器;macro.py 私家凍結已刪
- [ ] 現役 S&P500 快照與宏觀快照重凍後編號與說明檔逐位相同;verify 三類清白
- [ ] 只跑所涉測試檔;備份已做

## 結果

## 留言
