---
id: KARST-255
title: S3 來源覆蓋回報(架構候選五):取源結果表達逐來源成功／失敗／部分,移除新聞特例旁路
type: task
createdAt: 2026-09-23
risk: medium
model: opus
fits: 一程:fetch port 的回報形狀、news adapter、service 與 daily 的覆蓋判斷
dependsOn: []
claimedBy: Opus-S3
epic: 根基重整
deliverable: KARST-D12
closed: 2026-09-23
---

## 工作內容

依執行計劃 §三 3 及架構評審候選五。現況 LandedRecord 表達不到部分 feed 成功,新聞覆蓋靠 coverage.json 側檔,service 內有 if adapter == 'news_rss' 特例,daily 由四個欄位拼出取源是否完整。改為每個 adapter 回報逐來源覆蓋(ok／failed／partial 及原因),service 與 daily 只讀這一份覆蓋回報判斷完整性。不改證據內容與指紋。程式只住 karst/。

## 驗收條件

- [x] service 內沒有按 adapter 名稱的特例分支
- [x] daily 的「取源是否完整」只由覆蓋回報一處決定
- [x] 兩個 RSS 其中一個失敗時,回報為 partial 並列出失敗來源;全部失敗不得當作無新聞
- [x] 既有 fetch／daily／service 測試通過,新增部分成功的定向測試

## 結果

· 2026-09-23 16:30 來源接口加上取源覆蓋回報,新聞特例與側檔移除
- `port.cover(adapter, fetch)` 是唯一判定處,回 `(記錄, {adapter, status: ok|partial|failed, scope, feeds[]})`;每個 feed 記 status、cause(error／timeout／rate_limited／empty)、reason、detail。讀多個 feed 的 adapter 回 `port.Landing`(仍是記錄 list,另帶逐 feed 結果);單一來源 adapter 不改,由 cover 從落地記錄推出。`port.complete(coverage)` 答「是否全部 ok」。
- 新聞 adapter 不再寫 `coverage.json`;全部 feed 失敗不再拋錯,改回 failed 覆蓋並列出兩個 feed 及原因;零篇但 feed 有回應仍是 ok。
- service:刪去 `coverage.json` 側檔讀取與 `if adapter == 'news_rss'` 特例;結果欄 `adapter_errors`、`news_coverage` 合為單一 `coverage`,同一份寫入 `refresh_status`。
- daily:`sources_complete = port.complete(coverage)` 一處決定;歷史補取後以補取那次的價格覆蓋取代(與 store 逐 adapter 取代同一語義);`ready_for_review` = sources_complete 且 history_ready。
- 舊雲端資料:暫存目錄逐次為 scratch,舊 `coverage.json` 不再讀,不需遷移;`refresh_state` 舊列的 status(ok／empty／error)下游只按「是否 ok」使用,仍相容,下次刷新逐 adapter 取代;舊 daily_runs 回執續跑只沿用 ready_for_review 結果,不讀舊欄。
- 證據內容與指紋不變;全套 444 通過、1 跳過,只有已知 test_reader symlink(WinError 1314)失敗。

## 留言

### agent:Opus-S3 · 2026-09-23 16:30

完工。給 KARST-256:並行或限速時,逾時／被限速的來源在 feed 以 cause=timeout／rate_limited 標出(`port.failure_cause` 認 TimeoutError、「timed out」、HTTP 429),可只重試該來源;排程器自行中止的來源可交 `Landing(feeds=[FeedOutcome(名稱, 'failed', 'rate_limited', 原因)])` 經 cover 報出。KARST-262 讀 `coverage` 或 `refresh_status` 即可,不必看個別 adapter。
