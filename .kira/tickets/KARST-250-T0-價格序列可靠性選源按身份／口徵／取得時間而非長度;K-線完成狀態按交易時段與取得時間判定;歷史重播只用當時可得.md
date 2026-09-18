---
id: KARST-250
title: T0 價格序列可靠性:選源按身份／口徵／取得時間而非長度;K 線完成狀態按交易時段與取得時間判定;歷史重播只用當時可得
type: task
createdAt: 2026-09-19
risk: high
model: opus
fits: 一程做得完:bars.py 選源與完成狀態兩處邏輯、fetch 端補時段／復權欄、定向回歸測試一份
dependsOn: []
claimedBy: Fable主腦
epic: 根基重整
deliverable: KARST-D12
closed: 2026-09-19
---

## 工作內容

依 strategy/specs/SMC與TA工具箱-ClaudeCode執行計劃-v1.md §3(T0)。修 karst/bars.py:(1) series_from_evidence 不再只按 bar 數選來源——先比證券身份、復權／交易時段口徑,再以最新有效快照為主、只在口徑相容時以較舊快照補長歷史並明確處理重疊,每段保留來源;(2) _bar 的 complete 不再只比 bar 日期與請求截止日期——按來源語義、取得時間(fetched_at)與交易所收市時間(含時區、假期、提早收市可配置)判定,未知不升為已確認;週／月最後一期同理;(3) 歷史重播(as_of 早於今日)只用 fetched_at 不晚於 as_of 的證據,不拿今日快照截斷假稱當時可得。fetch/longbridge 端在 prices 記錄補交易時段／復權口徑欄位(有則記,無則 unknown)。回歸測試按 §3.4–3.5 參數化:相同長度新舊快照、較長舊／較短新、盤中快照隔日重用、歷史可用時間截止、週月未完成 bar;BE 樣本 2026-09-17 收市 280.76／量 14,236,326 不得被較早盤中 280.08／11,493,859 蓋過(數值是除錯樣本)。程式只住 karst/,代號與日期由參數傳入。

## 驗收條件

- [x] 同一證券兩份快照,較新 fetched_at 但較短者為主序列,較舊較長者只在口徑相容時補早段,重疊段以新為準且 source 列出兩段來源
- [x] 昨日盤中快照(fetched_at 在收市前)於今日重用時,最後一根 K 線 complete=false;同一日 fetched_at 在收市後者 complete=true;無取得時間或無時區者不升為已確認
- [x] as_of 早於今日的重播只選 fetched_at ≤ as_of 的證據;fetched_at 晚於 as_of 的快照即使含更多歷史亦不入選
- [x] 週／月最後一期在其最後一個交易日未確認收市時標未完成,現有 charts 測試全部仍通過
- [x] 新增 karst/tests 一份參數化回歸測試涵蓋上列五類情況與 BE 樣本值;PYTHONUTF8=1 全套測試通過;未改凍結②考試資料

## 結果

bars.py 選源按價格口徑與取得時間(最新快照為主、舊快照只補早段、segments 記兩段)、完成狀態按交易時段日曆與取得時間、重播只讀當時可得;交易時段由交易所代碼推出。13 個回歸測試,全套 359 通過;commit b2ef423。詳見留言。

## 留言

### agent:Fable主腦 · 2026-09-19 02:43
2026-09-19 完成(Opus 實作、Fable 覆核合併,commit b2ef423)。bars.py 重寫:選源先按證券身份與價格口徑(復權／週期／時段)分組,組內以最新 fetched_at 為主序列,較舊快照只補主序列首根之前並記 source.segments,口徑不相容不合併寫入 gaps;complete = 該日交易時段收市時刻 ≤ min(fetched_at, 截止),交易時段日曆 Session 可配置(時區、收市、半日市、假期)並由 security.exchange 或 EXCHANGE:TICKER 主題推出(未知回美股預設);重播只讀 fetched_at ≤ as_of 的證據。Longbridge prices 記錄 params 一律聲明 period／adjust_type／trade_session(未指定 unknown)——日後取數 source_id 會變,登記器會顯示 added 而非 unchanged,這是宣告口徑的代價。新測試 test_bars_reliability.py 13 個(含 BE 除錯樣本 280.76／14,236,326 不被 280.08／11,493,859 蓋過、盤中隔日重用、重播截止、週月未完成、時段推導)。全套 359 通過、1 跳過;唯一失敗 test_reader 的 symlink 測試是 Windows 無建立 symlink 權限(WinError 1314),屬 GPT 閱讀站既有測試,與本票無關。未改凍結②考試資料。名詞 來源分段／價格口徑／交易時段日曆 已入 CONTEXT.md。
