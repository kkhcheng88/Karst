---
id: KARST-057
title: 數據目錄重建:重抓三份快照、重跑七支成績腳本,舊登記標示序列缺失
type: task
createdAt: 2026-08-28
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-052, KARST-054]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

2026-08-28 22:12 主倉 data/ 被誤清空(runs、snapshots、macro_snapshots 共 436 MB;見 KARST-055 留言與運作觀察簿),karst.sqlite 完好。用戶 2026-08-28 裁決(原話「沒有 → 我會在另外兩條線落地後派一隊統一重建」):無備份,當作重建。範圍:(1) 動庫前整檔備份 karst.sqlite;(2) 經唯一入口重抓三份快照——SPY、QQQ 及十隻大型股 2015-01-02~2026-08-26 日線、六隻因子 ETF(SPY、QQQ、QUAL、VLUE、MTUM、USMV,不在起步宇宙名單者要先登記宇宙名單或以 Python 直呼 build_price_snapshot,在票上講明走了哪條路)、宏觀十四序列;(3) 依 experiments/ 七支腳本重跑全部成績(趨勢波段、因子混合等權、權重掃描、驅動器掃描、成本與重掃、宏觀驅動器、兩次重判),新快照編號與新運行編號登記入庫,每支腳本的 README/summary 更新新編號並記舊編號對照;(4) 舊 4,087 條運行登記不刪(定義表不可刪),網頁殼讀取層對序列缺失的運行標示「過時運行(序列缺失)」並不列入正式運行清單與掃描清單;(5) 成績數字與舊 README 逐項對照,差異列表;(6) 收工 karst verify 清白、全套測試過,KARST-055 的「既有測試全過」一併補驗並關檔;(7) 交付摘要 .kira/deliverables/KARST-D02.md 的快照與運行編號改為新編號。重抓要上網(yfinance 免費,免鑰匙)。

## 驗收條件

- [ ] 三份快照重抓成功並經唯一入口登記,快照編號與抓取登記齊全
- [ ] 七支腳本全部重跑,新運行編號登記入庫,四頁網頁殼用真數據畫得出;成績與舊 README 逐項對照表落檔
- [ ] 舊運行登記標示序列缺失,不入正式運行清單與掃描清單;karst verify 清白
- [ ] 全套測試過,KARST-055 關檔,KARST-D02 交付摘要編號更新

## 結果

## 留言
