---
id: KARST-032
title: 本機網頁殼 v0:讀真實運行畫淨值圖與蠟燭圖
type: task
createdAt: 2026-08-27
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-026, KARST-030]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

瀏覽器開一個本機網址,自此睇得到真實回測結果:淨值圖與蠟燭圖畫得出,進出場點落在蠟燭圖對應的日子上——回測結果要在蠟燭圖上看得到出入場點,體驗對標 TradingView/Futu(D-002 第 2 條)。範圍是網頁殼與一層薄 REST:數據來自一次真實運行,不是假數據;圖表用 lightweight-charts(D-019),樣式取 design-system.md 的 token。這是把 KARST-015 原型第十版那個已核准基線接上真數據的第一步,畫面決定不在本票重開(D-023 第 1 條)。

## 驗收條件

- [ ] 瀏覽器開本機網址睇得到淨值圖與蠟燭圖,進出場標記落在對應日期的蠟燭上(D-002 第 2 條、D-020 第 2 條)
- [ ] 圖上數據經薄 REST 層來自一次真實回測運行,頁面內查不到寫死的假數據(規格 8.7)
- [ ] 圖表用 lightweight-charts 畫,顏色與字級取 design-system.md 的 token,無自定色值(D-019)
- [ ] 換一次運行,整頁的圖跟住換,該次運行的編號在頁面上顯示得到(規格 7.4、詞彙表 view run)

## 結果

## 留言
