---
id: KARST-257
title: S5 增量分流 module(架構候選三):watch → plan → check 的輸入收集與新聞窗口規則集中
type: task
createdAt: 2026-09-23
risk: medium
model: opus
fits: 一程:updates 與 service.plan_update 的輸入收集、store 對私有函式的依賴、daily 的窗口規則
dependsOn: [KARST-256]
claimedBy: Opus-S5
epic: 根基重整
deliverable: KARST-D12
closed: 2026-09-23
---

## 工作內容

依執行計劃 §三 5 及架構評審候選三。updates.plan 純函式保留;把 service.plan_update 的輸入收集、daily 內的新聞窗口規則收進同一 module,store 不再 import updates 的私有 _text。透過新 interface 補測試,覆蓋輸入收集的主要分支。程式只住 karst/。

## 驗收條件

- [x] 新聞窗口規則只有一處定義,daily 經 interface 取得
- [x] store 不再 import updates 的私有名稱
- [x] plan 輸入收集經 interface 有測試,覆蓋研報訂閱、跨公司依賴、價格條件、來源失敗四類
- [x] 既有 updates／service／daily 測試通過

## 結果

· 2026-09-23 15:26 「甚麼時候要重看一隻股票、要重看哪幾層、新聞由哪一天讀起」這套分流規則,以往分散在服務層、日更流程、日更快照和資料庫四處,各寫一份;現在收進同一個模組(`karst/triage.py`,增量分流),四處都經它取得同一條規則。對盤數和研究判斷沒有任何改變:更新計劃、查核紀錄、MCP 回應與日更快照的內容照舊,只是日後要改規則只需改一處,不會出現某一處放行、另一處擋住的情況。
- 新聞窗口規則(只有記下「無變」查核才推進、要求取源完整及沒有未讀的新來源、覆蓋不完整一律不推進)只在該模組定義;日更流程讀新聞起點、日更快照的重評排隊、資料庫收查核時的把關,全部經它取得。
- 資料庫不再借用分流程式的內部函式(該文字檢查改為公開名稱,知識層同步改用公開名稱)。
- 更新計劃要讀的輸入(本公司證據、觀察項帶進的他公司研報與依賴來源、本證券自己的收市價、取源失敗狀態、方法版本、已存關係修訂)由該模組一個入口收集;新增測試直接經此入口覆蓋研報訂閱、跨公司依賴、價格條件、來源失敗四類,另測新聞窗口與查核把關。
- 測試:全套 480 通過、1 略過、1 失敗(失敗者仍只是本機沒有符號連結權限的既知項);新增 8 項。

## 留言

### agent:Opus-S5 · 2026-09-23 15:26

實作與四項驗收全部達成。兩點交代:(1) 既有測試 `test_new_industry_source_routes_across_two_subscribed_company_bundles` 原本替換 `karst.service._records`,輸入收集搬家後改為替換 `karst.triage._records`,只改替換目標一行,斷言不變;(2) `service.plan_update`／`record_update_check` 保留為薄殼(MCP、日更、基準量度照舊呼叫),實作在 `triage.plan`／`triage.record_check`;`record_check` 直接呼叫 `triage.plan`,不再經 `service.plan_update`,目前沒有測試或程式依賴替換後者來影響查核。給 KARST-262:更新任務的範圍物件可由 `triage.inputs` 取得同一份輸入再交 `updates.plan`,查核把關集中在 `triage.check_outcome`,不要在收件模組另寫一份。
