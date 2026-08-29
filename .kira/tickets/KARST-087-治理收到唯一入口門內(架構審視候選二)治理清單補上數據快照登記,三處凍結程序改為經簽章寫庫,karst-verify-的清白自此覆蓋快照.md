---
id: KARST-087
title: 治理收到唯一入口門內(架構審視候選二):治理清單補上數據快照登記,三處凍結程序改為經簽章寫庫,karst verify 的清白自此覆蓋快照
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
---

## 工作內容

源自 research/2026-08-30-architecture-review-backend.md 候選二(用戶 2026-08-30 授權:技術性候選全部做)。完成後:(1) 治理清單(D-020 第 4 條)收入數據快照登記(data_snapshot 與其抓取登記),與現有的快照除名一致;(2) 現時繞過簽章直接寫庫的三處凍結程序(價格線、宏觀線、重凍腳本)一律改為經唯一入口的簽章寫入,定義庫本身不再接受無簽章的快照登記;(3) 既有已登記的快照補簽(經唯一入口的補簽命令,留補簽痕跡:誰、幾時、為什麼),補簽後 karst verify 對全部快照核簽章;(4) verify 報告分開列「定義、因子批次、快照」三類各自清白與否。動庫前備份到 C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-087.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 karst/web/static/ 與 prototype/。

## 驗收條件

- [ ] 治理清單含數據快照登記;三處凍結程序無一繞過簽章(測試:直接寫庫的快照登記被 verify 點名)
- [ ] 既有快照已補簽並留痕;verify 三類分列且全部清白
- [ ] 只跑所涉測試檔;備份已做

## 結果

## 留言
