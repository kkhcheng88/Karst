---
id: KARST-070
title: 跑一次帶宏觀快照的正式運行:因子輪動宏觀驅動器以掃描最佳格參數登記參數集、經唯一入口執行,策略頁序列齊全度標記自此在正路上出現
type: task
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-067]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

KARST-067 指出庫內沒有一次帶宏觀快照的正式運行(只有掃描格),策略頁新加的「序列齊全度」標記在正路上見不到。範圍:從 experiments/2026-08-28-macro-rejudge/ 的最佳格取一組宏觀驅動器參數,經唯一入口登記為參數集(名稱註明示例與來源掃描編號)、以現役宏觀快照 2026-08-28-dc2d9f1a1778 執行一次正式運行(來歷 FORMAL_RUN);把運行編號與參數集版本一併寫入 experiments/2026-08-28-macro-drivers/README.md 與 D02 摘要示例運行一行(A-009 教訓:編號要連參數集版本)。瀏覽器實開策略頁核對標記出現。不改引擎、不改策略、不加參數預設值;只跑所涉測試檔。

## 驗收條件

- [ ] 一次因子輪動宏觀驅動器正式運行入庫,運行編號與參數集版本落檔
- [ ] 策略頁在該策略正路上顯示序列齊全度標記(截圖或文字核對落檔)
- [ ] karst verify 清白;只跑所涉測試檔

## 結果

## 留言
