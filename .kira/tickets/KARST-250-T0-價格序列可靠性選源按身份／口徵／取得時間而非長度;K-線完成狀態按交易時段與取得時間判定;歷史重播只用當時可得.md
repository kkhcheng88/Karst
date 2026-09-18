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
---

## 工作內容

依 strategy/specs/SMC與TA工具箱-ClaudeCode執行計劃-v1.md §3(T0)。修 karst/bars.py:(1) series_from_evidence 不再只按 bar 數選來源——先比證券身份、復權／交易時段口徑,再以最新有效快照為主、只在口徑相容時以較舊快照補長歷史並明確處理重疊,每段保留來源;(2) _bar 的 complete 不再只比 bar 日期與請求截止日期——按來源語義、取得時間(fetched_at)與交易所收市時間(含時區、假期、提早收市可配置)判定,未知不升為已確認;週／月最後一期同理;(3) 歷史重播(as_of 早於今日)只用 fetched_at 不晚於 as_of 的證據,不拿今日快照截斷假稱當時可得。fetch/longbridge 端在 prices 記錄補交易時段／復權口徑欄位(有則記,無則 unknown)。回歸測試按 §3.4–3.5 參數化:相同長度新舊快照、較長舊／較短新、盤中快照隔日重用、歷史可用時間截止、週月未完成 bar;BE 樣本 2026-09-17 收市 280.76／量 14,236,326 不得被較早盤中 280.08／11,493,859 蓋過(數值是除錯樣本)。程式只住 karst/,代號與日期由參數傳入。

## 驗收條件

- [ ] 同一證券兩份快照,較新 fetched_at 但較短者為主序列,較舊較長者只在口徑相容時補早段,重疊段以新為準且 source 列出兩段來源
- [ ] 昨日盤中快照(fetched_at 在收市前)於今日重用時,最後一根 K 線 complete=false;同一日 fetched_at 在收市後者 complete=true;無取得時間或無時區者不升為已確認
- [ ] as_of 早於今日的重播只選 fetched_at ≤ as_of 的證據;fetched_at 晚於 as_of 的快照即使含更多歷史亦不入選
- [ ] 週／月最後一期在其最後一個交易日未確認收市時標未完成,現有 charts 測試全部仍通過
- [ ] 新增 karst/tests 一份參數化回歸測試涵蓋上列五類情況與 BE 樣本值;PYTHONUTF8=1 全套測試通過;未改凍結②考試資料

## 結果

## 留言
