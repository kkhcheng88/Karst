---
id: KARST-093
title: 網頁測試改打臨時庫:六個 test_web*.py 直接對倉根生產庫跑,jobs 那個每跑一次在生產庫多寫一條正式運行;改為每次測試起臨時 sqlite,並清走測試寫入的正式運行
type: task
createdAt: 2026-08-30
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-088]
claimedBy: agent-093
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

源自 KARST-087 收工觀察:tests/test_web.py、test_web_data.py、test_web_holdings.py、test_web_overview.py、test_web_strategy.py、test_web_sweep.py(及 test_web_jobs 若存在)直接對倉根 data/ 下的生產資料庫跑;jobs 相關測試每跑一次就經正式路徑多寫一條 origin='formal' 的運行,正式運行由 12 條變 13 條即為此故。完成後:(1) 全部網頁測試經 conftest fixture 起臨時 sqlite 真庫(複製 schema,種入最少假數據經唯一入口寫),不再讀寫倉根生產庫;(2) 查明生產庫內由測試寫入的正式運行(以參數集/期間/寫入時間辨認,列清單在票上),經唯一入口把它們標為測試污染(不刪列;若無現成標記途徑,加一個經簽章的標記方式並入治理清單),使正式運行計數回到 12 條;(3) test_web.py 那條「運行清單頭 8 名」舊斷言改為不依賴生產庫內容;(4) 設計系統色值那條紅燈(原型改動所致)查明來源,屬 prototype/ 的不改,屬 karst/web/static/ 的改回設計系統 token。動庫前備份到 C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-093.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 prototype/。

## 驗收條件

- [ ] 六個(或以上)test_web*.py 全部經臨時庫跑,倉根生產庫在跑完前後位元不變(測試:跑前後雜湊比對)
- [ ] 測試寫入的正式運行已辨認、標記並留痕,正式運行計數回到 12 條;verify 清白
- [ ] test_web.py 兩條紅燈轉綠;只跑所涉測試檔;備份已做

## 結果

## 留言
