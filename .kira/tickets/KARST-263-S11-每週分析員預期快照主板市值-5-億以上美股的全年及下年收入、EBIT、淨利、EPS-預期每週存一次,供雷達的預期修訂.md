---
id: KARST-263
title: S11 每週分析員預期快照:主板市值 5 億以上美股的全年及下年收入、EBIT、淨利、EPS 預期每週存一次,供雷達的預期修訂
type: task
createdAt: 2026-09-24
risk: medium
model: opus
fits: 一程
dependsOn: []
claimedBy: claude-main
epic: 根基重整
deliverable: KARST-D09
---

## 工作內容

用戶 2026-09-24 同意每週記錄分析員預期(原話:「Every week is fine too.」「I think 收入預期 and 支出預期?」,並以「ok」回覆開工)。Longbridge financial-consensus-detail(period_type=af)經 SDK HttpClient 以服務憑證取得;範圍 = 主板、市值 ≥ 5 億(參數)。只存未公布的預測期,每股一行,每 ISO 週一檔;中途重啟可續跑;雲端服務在週六及週日(UTC)自動補做本週。依據 資料來源.md §四 10-0(d):雷達屬橫向掃描產品,可由程式抓存多股序列。

## 驗收條件

- [x] karst/consensus.py 通用:代號由名單或參數傳入,碼內不寫死股票
- [x] 每週一檔 data/consensus/<YYYY-Www>.jsonl 及完成紀錄;已存的代號重啟後不再取
- [x] 速率受限:用獨立來源額度,429002 視作可重試
- [x] 一個可跑的測試覆蓋摘取、續跑、完成紀錄
- [x] HTTP 服務啟動每週背景檢查;本機 stdio 不啟動

## 結果

· 2026-09-24 02:55 已交付於 daily-scale 分支(aa8fa6b),核心 0.2.16。
- `karst/consensus.py`:範圍經 SDK 全市場名單→主板→市值(本機實測 4,869 隻,9.6 秒);逐股取 `/v1/quote/financial-consensus-detail?period_type=af`,只存未公布財年的全部預期欄(收入、EBIT、淨利、正常化淨利、EPS、正常化 EPS);失敗多過一成則該週不標完成,下次檢查補做。
- `limits.py`:新來源 `longbridge_consensus` 每秒 1.5 次、一次一個(實測每秒 2 次已被 429002 拒);429 系列廠商代碼改作可重試,令既有 Longbridge 行情呼叫遇 429002 時亦會退避重試(之前直接失敗)。
- `mcp_server.py`:HTTP 模式啟動每週背景檢查(UTC 週六、日,每小時一次);`/healthz` 加 `consensus_week`(最近完成週)作雲端讀回。
- 本機實跑 20 隻(含 BRK.B、SPY、新股 JMKE):12.7 秒全部成功,19 隻有預期,SPY 無。3 項新測試加全套 488 項通過(略過本機沒有符號連結權限的閱讀層測試)。
- 未驗:雲端首個完整週(預計約 55 分鐘、約 4,900 次呼叫)要待部署後的週六讀回 `consensus_week`。

## 留言
