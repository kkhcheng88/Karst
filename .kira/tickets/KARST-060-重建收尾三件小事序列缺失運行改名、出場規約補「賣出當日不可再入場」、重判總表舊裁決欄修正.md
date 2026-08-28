---
id: KARST-060
title: 重建收尾三件小事:序列缺失運行改名、出場規約補「賣出當日不可再入場」、重判總表舊裁決欄修正
type: task
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-057, KARST-059]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

三件互不相干但都細小的收尾。(1) KARST-057 把序列檔案不在的運行標成「過時運行(序列缺失)」,與詞彙表「過時運行」(版本過時)撞名;網頁殼標籤與程式名一律改為「序列缺失運行 / series-missing run」(CONTEXT.md 已入冊)。(2) KARST-059 發現出場規約沒有寫「賣出當日不可再入場;新入場最早在下一個交易日開市」——引擎行為已如此,只補規約文字並加一個把行為釘死的測試,不改引擎邏輯、不加參數。(3) 兩支重判腳本(axis-aware-verdict、macro-rejudge)的總表與 summary.json「最優格舊裁決」欄在最優格本身改判時填成新裁決(逐格對照表才對),修正產生程式並重出總表;因子輪動 summary.json 補「山脊」計數欄(KARST-047 漏補),README 該格由「填不到」改為實數。不重跑引擎。

## 驗收條件

- [ ] 網頁殼與程式內不再出現「過時運行(序列缺失)」,改為「序列缺失運行」,既有測試過
- [ ] 出場規約文字補該句,新增測試證明賣出當日再發訊號只能在下一交易日開市入場
- [ ] 兩份重判總表「最優格舊裁決」與逐格對照表一致;因子輪動 summary.json 有山脊計數,README 該格填實數

## 結果

## 留言
