---
id: KARST-083
title: 代號歷史對照收尾:32 個人手待辨代號逐個查明所屬公司與 CIK、補入對照表,重凍標普 500 歷史成分快照,Alpha158 因子批次按新快照重入
type: task
createdAt: 2026-08-30
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-082]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

接 KARST-082。完成後:(1) experiments/2026-08-29-ticker-history/manual-review.csv 的 32 個代號逐個查明在其成分期屬於哪家公司、CIK 幾多(以 SEC 申報名稱窗口、EDGAR 全文檢索、維基百科標普 500 成分變動表交叉核對,每個代號寫明證據來源;查不出的明確標「未能辨明」並留佔位錨,不猜);(2) 補入 karst/data/universes/sp500_ticker_anchors.csv,對照規則不變;(3) 按等價重用規矩重凍快照,新舊編號(含 2026-08-28-493fd1df1cb9、2026-08-28-c442236133d4)並列寫入同一 README,舊快照不刪;(4) 用 karst factor ingest-alpha158 --snapshot <新編號> 把 Alpha158 因子批次按新快照重入,karst verify 清白;(5) 舊快照上的示例運行不重跑(D-038:示例運行留到建置期對齊參數後才算數),但在 README 講明哪些運行仍掛舊快照。只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不遞歸刪除倉外目錄;不碰 karst/web/。

## 驗收條件

- [ ] 32 個代號逐個有結論(辨明+CIK+證據,或明確未能辨明),落 experiments/2026-08-29-ticker-history/manual-review-resolved.csv
- [ ] 對照表已補;新快照已凍、三代編號並列;Alpha158 批次已按新快照重入且 verify 清白
- [ ] 只跑所涉測試檔;README 列明仍掛舊快照的運行

## 結果

## 留言
