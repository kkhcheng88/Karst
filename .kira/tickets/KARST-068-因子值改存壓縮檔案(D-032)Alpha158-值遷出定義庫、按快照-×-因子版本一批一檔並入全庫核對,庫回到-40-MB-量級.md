---
id: KARST-068
title: 因子值改存壓縮檔案(D-032):Alpha158 值遷出定義庫、按快照 × 因子版本一批一檔並入全庫核對,庫回到 40 MB 量級
type: task
createdAt: 2026-08-29
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-064]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

依 D-032(用戶 2026-08-29 裁決)。範圍:(1) 因子值承載體由 factor_value 表改為 Parquet 檔,按「數據快照 × 因子庫批次(Alpha158 一批)」一檔,放 data/ 之下與快照、運行並列的目錄;(2) 定義庫因子表只留登記:因子、因子版本、產生程序版本、快照編號、檔案路徑、內容雜湊、行數、三個時點的口徑;factor_value 表原地遷移為登記表或清空並保留表結構(schema 加一版,原地遷移保留既有編號);(3) karst verify 把因子檔雜湊納入核對;(4) 讀取介面:給定快照 × 因子版本 × 日期窗口取回長表或寬表,供預測力面板與策略用;(5) 以十二隻快照重新入庫一次,對照 KARST-064 的 summary.json 行數、缺值比例一致;然後 VACUUM,庫檔回到 40 MB 量級,落檔前後大小。舊 1.6 GB 值遷出(先 Copy-Item 備份到 ~/.claude/backups/karst.sqlite.2026-08-29-068.bak)。不加參數預設值;只跑所涉測試檔。

## 驗收條件

- [ ] Alpha158 十二隻重新入庫後值住在 Parquet 檔,定義庫只有登記與雜湊;行數、缺值比例與 KARST-064 一致
- [ ] karst verify 核對因子檔雜湊,清白;庫檔大小回到 40 MB 量級並落檔
- [ ] 讀取介面有測試;只跑所涉測試檔

## 結果

## 留言
