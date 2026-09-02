---
id: KARST-165
title: 拆股事件表代號重用污染修補(KARST-158 遺留):CPWR/EP/PARA 等代號被不同公司先後使用,拆股事件表按代號索引令舊公司的拆股套到新公司(共 7 格已知);改以 CIK 為主鍵,列出全部受影響代號與格,重跑受影響面板格核對,面板 v2 不改只出修補清單
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: null
deliverable: KARST-D02
---

## 工作內容

背景:A-041 修補紀錄(KARST-158)指出「拆股事件表按代號索引而代號會被重用(CPWR/EP/PARA 共 7 格),屬拆股基準層,建議另開票」;KARST-160 又發現 CPWR 與 EP 是十倍股名單裡的污染格(代號重用令兩家公司的價格序列被接成一條)。先讀 experiments/2026-09-02-panel-scale-fix/(RULES、scale_fixes.csv、README 提到拆股事件表的位置)、research/2026-09-02-十倍股盤點.md 第 1.5 節與 RULES v2 第九節、data/sec/company_tickers.json 與 cik-lookup-data.txt。做法:①找出拆股事件表與價格序列的主鍵現況;②用 SEC 的 CIK 對照(company_tickers.json、submissions/)逐個代號查是否曾屬多於一個 CIK,列全部重用代號連時段;③對每個重用代號,判定拆股事件與價格段各屬哪個 CIK,寫出修補清單(代號、日期段、正確 CIK、受影響面板格數、受影響的十倍股名單行);④不改 panel_monthly_v2.parquet、不改生產庫;修補清單與建議主鍵方案(CIK+代號+時段)落 experiments/2026-09-03-ticker-reuse/out/ 與 REPORT.md;⑤估算若採 CIK 主鍵,哪些下游(面板、十倍股盤點、鏈表 v1/v2 的 ticker 欄)要跟着改,在票上 raise。

## 驗收條件

- [ ] 全部代號重用清單(代號、各 CIK、時段)落 out/ticker_reuse.csv;已知的 CPWR/EP/PARA 必須在內
- [ ] 修補清單 out/split_fixes_proposed.csv:每格附正確 CIK 與理由;受影響的十倍股名單行標出
- [ ] REPORT.md 建議主鍵方案與下游影響;票上 raise;面板 v2、生產庫一個位元不改,SHA256 首 16 位維持 b168e9f45b578cf9
- [ ] commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言
