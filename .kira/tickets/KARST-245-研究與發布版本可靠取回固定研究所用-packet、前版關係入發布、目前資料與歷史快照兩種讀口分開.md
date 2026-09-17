---
id: KARST-245
title: 研究與發布版本可靠取回:固定研究所用 packet、前版關係入發布、目前資料與歷史快照兩種讀口分開
type: task
createdAt: 2026-09-18
risk: high
model: opus
fits: 一程做得完:store / service / publish 三檔內的改動加測試;不改契約 schema
dependsOn: []
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

承 2026-09-18 架構評審與 GPT 覆核(交付一)。三件:(1) 研究版本保存時連同它驗證所用的 packet 與證據快照(packet_id、evidence 記錄或其指紋)一起存;publish_research(version_id) 只用該版本當時的 packet 與證據,不讀公司 bundle 當下的 packet——公司資料更新後再發布舊研究不得失敗或換內容。(2) service 發布路徑傳 previous_publication_id(由 store 前版的 publication 取得),0.3 發布鏈「指回前版」在 service 路徑成立;首屏「與上次相比」可由前版取回。(3) 證據讀口分兩種問法並在介面明寫:「目前可用資料」(manifest / 公司證據倉)與「某次研究當時使用的資料」(該版本的 evidence 快照);SQLite sources 表定位為可重建索引,補讀者或刪;不把兩者合成永遠讀最新。驗證只有一份規則:intake 回帶內容指紋的已驗證結果,同一次操作對同一固定內容重用不重驗;重新讀入或內容改變時核版本與內容指紋;發布複製檔案時保留內容一致性檢查(不刪)。先量度重驗耗時再決定是否減省。程式只住 karst/,代號由參數傳入(D-180)。

## 驗收條件

- [ ] 公司證據倉更新(新增證據、新 packet)後,對舊研究版本 publish_research 仍成功且頁面內容與首次發布一致
- [ ] 第二版發布的 publication.json 帶 previous_publication_id 指向第一版;資料室頁與首屏可顯示前後差異
- [ ] get_research_context / search_evidence 有明確參數區分「目前可用」與「某版本當時使用」,兩種問法回傳不同集合並有測試
- [ ] 驗證重用有內容指紋守門:改動任一證據檔或 research 內容後保存或發布即被拒;耗時量度寫入紀錄
- [ ] sources 表要麼有生產讀者要麼刪除;零呼叫的 store 方法與從未寫入的狀態值刪除,任務狀態轉換集中一處

## 結果

## 留言
