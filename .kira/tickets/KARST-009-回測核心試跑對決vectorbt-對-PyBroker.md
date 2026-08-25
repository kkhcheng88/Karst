---
id: KARST-009
title: 回測核心試跑對決:vectorbt 對 PyBroker
type: task
createdAt: 2026-08-25
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: null
epic: V1 藍圖
deliverable: KARST-D01
---

## 工作內容

完成之後有什麼是之前做不到的:「借用哪個回測核心」這個決定有實測數據支撐,不再只憑文件。考題(照 D-006 的主場景設):同一個玩具選股策略——按一個模擬因子橫斷面排名、每月選 N 隻、平均分再平衡——在 vectorbt 與 PyBroker 各實作一次,規模數百股乘約十年日線,並做一輪約一千組參數掃描。比較三樣:表達直觀度(選股邏輯寫出來扭不扭曲)、耗時(單次回測與掃描)、接自家資料層的順暢度。同時判定假設 A-001 的真假。結論寫建議但明寫最終由用戶裁決(D-005)。

## 驗收條件

- [ ] 兩邊實作代碼落倉並可重跑,環境依賴有記錄
- [ ] 耗時數據表落檔(單次回測與參數掃描,同機同數據)
- [ ] 表達力與接駁順暢度有逐項對比與建議,明寫由用戶裁決
- [ ] A-001 在假設冊更新狀態(holds 或 overturned),附一句證據

## 結果

## 留言
