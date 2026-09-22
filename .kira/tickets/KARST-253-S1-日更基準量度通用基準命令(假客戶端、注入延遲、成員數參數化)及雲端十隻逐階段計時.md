---
id: KARST-253
title: S1 日更基準量度:通用基準命令(假客戶端、注入延遲、成員數參數化)及雲端十隻逐階段計時
type: task
createdAt: 2026-09-23
risk: medium
model: opus
fits: 一程:karst 內一個基準入口、一份測試、一次雲端計時回執
dependsOn: []
claimedBy: Opus-S1
epic: 根基重整
deliverable: KARST-D12
closed: 2026-09-23
---

## 工作內容

依 strategy/specs/日更規模化與架構加深-執行計劃-v1.md §三 1。在 karst/ 內加通用基準入口(成員數、每來源延遲、失敗率由參數傳入,用假客戶端,不連外網),逐階段量度 refresh_scope 的取源、序列重建、plan_update、checkpoint 耗時與記憶體;另以雲端現行 daily-monitoring 十隻實跑一次(只讀,不記 check、不推進窗口若工具允許;否則說明)取得逐階段真實耗時。結果寫 cards/runs/daily-scale-2026-09-23/baseline.json。程式只住 karst/,代號與日期由參數傳入,不寫一次性腳本(D-180)。

## 驗收條件

- [x] 基準入口可用 N=10、50、200 假成員跑出逐階段耗時,並有一份定向測試
- [x] 雲端十隻逐階段真實耗時入回執,註明哪些階段隨成員數線性增長
- [x] 回執列出 200 隻的推算耗時及主要瓶頸排序

## 結果

· 2026-09-23 02:54 基準入口、定向測試、本機三組量度及雲端十隻實測完成,回執 cards/runs/daily-scale-2026-09-23/baseline.json
- 入口:`python -m karst.daily_bench --members N [--price-delay --news-delay --failure-rate --no-news --news-items --prior-news --history-bars --seed]`(karst/daily_bench.py);假 Longbridge 與假 RSS、暫存資料目錄、不連外網;逐階段以包裝既有函數量度(扣除子階段),日更程式本身未改。測試 karst/tests/test_daily_bench.py(2 項)。
- 本機(Windows,無注入延遲)每隻:N=10 0.80 秒、N=50 0.89 秒、N=200 1.11 秒;N=200 全程 223 秒。取源、登記、封包、序列重建、plan_update 每隻成本不隨 N 變(總量線性);全文索引重複檢查(31→74→236 毫秒／隻)與整份回執重寫(3→9→32 毫秒／隻)隨 N 上升,總量屬平方級。峰值記憶體 81–86 MB。
- 雲端 daily-monitoring 十隻(run daily-152d8a05…):94.7 秒,全部 ready_for_review;每隻約 2.8 秒固定成本加每篇新文章約 0.46 秒(MSFT 73 篇佔 37 秒)。雲端回執沒有逐階段欄位,階段拆分按本機基準推算;MCP 回傳 246 KB,超出客戶端工具結果上限。
- 200 隻推算(現行逐隻順序):新聞日約 32 分鐘,純價格下限約 10 分鐘;目標(5／10 分鐘、單次呼叫 60 秒)全未達。
- 瓶頸排序:①逐隻順序等網絡;②每筆證據登記都重讀、驗證、重寫整份清單;③全文索引重複檢查全表掃描;④每隻重寫並回傳整份回執;⑤plan_update 每隻兩次、協議載入四次(影響小)。

## 留言

### agent:Opus-S1 · 2026-09-23 02:55
完工。雲端只呼叫 refresh_daily_scope 一次,沒有記查核、保存或發布;該次按現行規則寫入每日回執及新聞／價格證據(工具本身行為)。對 KARST-256 最要緊:並行只解決第①項;②③④與並行無關,是按筆重寫或平方級成本,不先修則 200 隻即使並行仍受拖累,而③會隨每日累積證據繼續變慢。全套測試 439 過、1 略過,唯一失敗為已知 Windows 符號連結權限項(test_reader)。
