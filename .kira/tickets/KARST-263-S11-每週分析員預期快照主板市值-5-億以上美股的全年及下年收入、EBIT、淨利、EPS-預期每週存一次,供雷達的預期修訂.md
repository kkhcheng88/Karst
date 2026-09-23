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

- [ ] karst/consensus.py 通用:代號由名單或參數傳入,碼內不寫死股票
- [ ] 每週一檔 data/consensus/<YYYY-Www>.jsonl 及完成紀錄;已存的代號重啟後不再取
- [ ] 速率受限:用獨立來源額度,429002 視作可重試
- [ ] 一個可跑的測試覆蓋摘取、續跑、完成紀錄
- [ ] HTTP 服務啟動每週背景檢查;本機 stdio 不啟動

## 結果

## 留言
