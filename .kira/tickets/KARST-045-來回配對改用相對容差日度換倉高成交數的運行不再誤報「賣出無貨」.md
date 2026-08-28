---
id: KARST-045
title: 來回配對改用相對容差:日度換倉高成交數的運行不再誤報「賣出無貨」
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-039, KARST-043]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

指標層對日度換倉、單一實體累積兩千多筆成交的運行自此照樣算得出八項指標。KARST-043 發現先入先出配對的浮點殘差可達 1.4e-12 股,超過現行 1e-12 絕對容差,整個掃描中斷。範圍:容差改為相對持倉量的比例(寫明取值理由),真正的「賣出無貨」仍要拋錯。

## 驗收條件

- [ ] 日度換倉的合成運行(單一實體逾兩千筆成交)算得出八項指標不拋錯
- [ ] 真正賣出多過持倉的情況仍拋錯並講明實體與日期
- [ ] 既有運行的八項指標逐位不變

## 結果

## 留言
