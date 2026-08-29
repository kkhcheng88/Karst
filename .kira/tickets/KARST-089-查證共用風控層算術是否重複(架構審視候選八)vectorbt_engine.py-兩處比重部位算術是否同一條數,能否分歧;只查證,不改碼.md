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
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

源自 research/2026-08-30-architecture-review-backend.md 候選八(D-043:先查證再決定開不開實作票)。審視指 karst/engine/vectorbt_engine.py 約 213 行與約 324 行兩處各自計算共用風控層的部位/比重算術,懷疑同一條數寫了兩次。完成後:(1) 兩處算術逐項對照表(輸入、公式、四捨五入、邊界處理)落檔 experiments/2026-08-30-risk-layer-arith/README.md;(2) 一個對照腳本:用現有正式運行的參數集各跑兩處算術,報告是否逐位相同,結果檔落同一目錄;(3) 結論三選一寫在票上:甲 完全相同、應合併(附建議的單一模組位置);乙 刻意不同、各有理由(附理由與應加的註解位置);丙 已經分歧、結果數字受影響(列出受影響的運行編號,並寫入 .kira/assumptions.jsonl)。不改 karst/;只跑對照腳本;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/。

## 驗收條件

- [ ] 對照表與對照腳本及結果檔已落 experiments/2026-08-30-risk-layer-arith/
- [ ] 票上有甲/乙/丙結論;若丙則 assumptions 已記
- [ ] 未改 karst/

## 結果

## 留言
