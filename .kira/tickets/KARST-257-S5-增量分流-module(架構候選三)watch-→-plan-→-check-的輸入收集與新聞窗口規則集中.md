---
id: KARST-257
title: S5 增量分流 module(架構候選三):watch → plan → check 的輸入收集與新聞窗口規則集中
type: task
createdAt: 2026-09-23
risk: medium
model: opus
fits: 一程:updates 與 service.plan_update 的輸入收集、store 對私有函式的依賴、daily 的窗口規則
dependsOn: [KARST-256]
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依執行計劃 §三 5 及架構評審候選三。updates.plan 純函式保留;把 service.plan_update 的輸入收集、daily 內的新聞窗口規則收進同一 module,store 不再 import updates 的私有 _text。透過新 interface 補測試,覆蓋輸入收集的主要分支。程式只住 karst/。

## 驗收條件

- [ ] 新聞窗口規則只有一處定義,daily 經 interface 取得
- [ ] store 不再 import updates 的私有名稱
- [ ] plan 輸入收集經 interface 有測試,覆蓋研報訂閱、跨公司依賴、價格條件、來源失敗四類
- [ ] 既有 updates／service／daily 測試通過

## 結果

## 留言
