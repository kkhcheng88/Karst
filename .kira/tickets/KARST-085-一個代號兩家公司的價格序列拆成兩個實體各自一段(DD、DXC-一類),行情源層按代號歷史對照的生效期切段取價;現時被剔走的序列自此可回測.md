---
id: KARST-085
title: 一個代號兩家公司的價格序列拆成兩個實體各自一段(DD、DXC 一類),行情源層按代號歷史對照的生效期切段取價;現時被剔走的序列自此可回測
type: task
createdAt: 2026-08-30
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-084]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
closed: 2026-09-14
cancelReason: V1 引擎票;引擎已於 2026-09-13 重整刪除(tag pre-reset-2026-09-13),代號分段已落在 data/universe/ticker_periods.parquet,需要時在根基重整 D09 之下重開
---

## 工作內容

源自 KARST-083:DD、DXC 各自橫跨兩家不同公司(同一代號先後屬兩個實體),免費行情源只給今日持有人的整段歷史,現時規則只能整條剔走。完成後:(1) 來源適配器取價時按代號歷史對照的生效起訖切段,每段掛到對應實體,段外日線不入該實體;(2) 今日持有人以外那家公司的歷史若免費源根本沒有(價格屬另一家),該段明確標「行情源無此段」留空,不拿另一家的價格充數;(3) 對 DD、DXC 與 KARST-083 剔走清單內同類代號跑一次,結果落 experiments/2026-08-29-ticker-history/README.md;(4) 重凍與因子重入不在本票(留待下次一併)。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/。

## 驗收條件

- [ ] 切段取價有測試(一個代號兩段生效期、各掛不同實體;段外日線不入)
- [ ] DD、DXC 核對結果落檔,講明哪段有價、哪段標「行情源無此段」
- [ ] 只跑所涉測試檔;未重凍

## 結果

## 留言

### agent:main-agent · 2026-08-30 23:57
依 D-058/D-054:本票服務標普 500 個股宇宙,個股層排在板塊層之後——**降優先**,現階段不派工,不取消。
