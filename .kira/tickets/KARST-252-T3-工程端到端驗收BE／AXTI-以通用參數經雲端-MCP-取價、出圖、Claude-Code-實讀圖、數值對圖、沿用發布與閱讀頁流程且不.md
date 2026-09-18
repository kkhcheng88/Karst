---
id: KARST-252
title: T3 工程端到端驗收:BE／AXTI 以通用參數經雲端 MCP 取價、出圖、Claude Code 實讀圖、數值對圖、沿用發布與閱讀頁流程且不覆蓋舊版
type: task
createdAt: 2026-09-19
risk: medium
model: opus
fits: 一程做得完:部署後兩隻股各跑一次取價→出圖→讀圖→發布→閱讀頁,寫紀錄
dependsOn: []
claimedBy: Fable主腦
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依 strategy/specs/SMC與TA工具箱-ClaudeCode執行計劃-v1.md §7 與用戶 2026-09-19 指令第 4 點。T0／T1 合併部署到 Zeabur 後,對 BE 與 AXTI 以通用參數:(1) 雲端 refresh_sources 取最新 Longbridge 日線,核來源與最後一根 K 線(日期、收市、量、complete 狀態)正確;(2) 雲端 render_charts 出四張圖,read_chart 實際返回可讀圖像,Claude Code 端實際打開圖並以 derived.json 數值核對圖上 MA／支阻／結構事件一致;(3) 圖上保留影響判斷的結構與支阻且清楚;(4) 以既有 publish_research 對現有最新研究版本重新發布(新 pub 目錄、舊版不改)並以 karst/reader 生成閱讀頁,標明「工程樣本、未經覆核、不是投資建議」;(5) 紀錄寫入 cards/runs/<通用命名>/紀錄.md,分清已實作／已部署／已實測／待 GPT 驗收。GPT 端讀圖與投研驗收不代稱通過。程式只住 karst/;不新增股票專用腳本。

## 驗收條件

- [ ] 兩隻股雲端取價後最後一根 K 線的日期、收市、量與 complete 狀態在紀錄中列出並與 Longbridge 直查一致
- [ ] 兩隻股雲端 render_charts 成功、read_chart 返回圖像,Claude Code 端實際讀圖並記錄至少三項圖上數值與 derived.json 對得上
- [ ] 圖上可見最近結構事件與支阻,圖例分清;紀錄附圖檔路徑
- [ ] 以既有發布流程各出一個新 pub 目錄指回原版本,原發布目錄 sha 不變;閱讀頁生成並標工程樣本
- [ ] 紀錄分清已實作／已部署／已實測／待 GPT 驗收;地圖 D12 與 HANDOFF 同步

## 結果

## 留言
