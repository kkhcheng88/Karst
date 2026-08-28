---
id: KARST-052
title: 從畫面發起重跑與重掃:經唯一入口登記參數集並排隊執行
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-049, KARST-051]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶自此可以在運行詳情按「重跑」、在參數掃描按「重掃」,改參數後由後端經唯一入口登記參數集(同名同節奏同取值自動沿用舊版)並執行,完成後畫面刷新到新運行編號。照原型 rerun/rescan 彈窗實作;執行在後端排隊,前端顯示進行中狀態;不繞過唯一入口、不設參數預設值。

## 驗收條件

- [ ] 運行詳情的重跑彈窗改參數後得出新運行編號並顯示,同取值重跑得同一編號
- [ ] 參數掃描的重掃彈窗可改格子範圍並得出新掃描結果
- [ ] 所有登記經唯一入口,karst verify 照舊清白
- [ ] 既有測試全過

## 結果

## 留言
