---
id: KARST-033
title: 數據快照歸一化:同一段日線重抓後編號相同,不再多出重複快照
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-027]
claimedBy: KARST-033-normalize
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

同一段日線重抓兩次,自此得同一個快照編號。KARST-027 收檔時發現:派過息的股票,yfinance 每次回來的已調整價在第六、七位小數有微小飄移(相對誤差約百萬分之一),而快照編號按內容雜湊,差一位即算新快照,重抓一次就多一份幾乎一樣的檔。用戶 2026-08-28 裁決(原話「yes normalize it. no duplicated copy」):凍結前先把價格歸一化到固定精度,令重抓得同一編號;歸一化規則寫入快照說明檔,是數據定義的一部分。

## 驗收條件

- [ ] 同一窗口同一宇宙相隔一段時間抓兩次,得同一個快照編號(真實抓取,離線自動略過)
- [ ] 歸一化規則(精度與方式)寫在快照說明檔範本正本,並在票上列明低價已調整舊價的精度損失估算
- [ ] 既有離線與真實抓取測試全部照過

## 結果

## 留言
