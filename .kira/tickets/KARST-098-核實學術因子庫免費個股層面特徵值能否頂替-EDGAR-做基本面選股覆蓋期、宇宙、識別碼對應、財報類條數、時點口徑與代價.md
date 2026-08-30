---
id: KARST-098
title: 核實學術因子庫免費個股層面特徵值能否頂替 EDGAR 做基本面選股:覆蓋期、宇宙、識別碼對應、財報類條數、時點口徑與代價
type: research
createdAt: 2026-08-30
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: KARST-098-researcher
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

research/2026-08-29-osap-classic-anomalies.md 第 1.3 節查到:OSAP 免費部分含 209 條**個股層面**橫斷面預測特徵值(寬表、已統一符號方向、1.6GB 壓縮),不需 WRDS。若覆蓋期夠新、宇宙涵蓋標普 500 現役成分、識別碼對得上,則用戶漏斗第一層(基本面選股)今日即有數據,不必等 SEC EDGAR 數據線(D-041)落地,且『我們有沒有算錯』這個問題消失(值是對方算的)。本票只查證不實作,逐條答:(1) firm_char 寬表的實際覆蓋期(最早、最新日期)與更新頻率/最近一次更新日;(2) 觀測頻率是月度還是日度;(3) 宇宙範圍,以及現役快照 2026-08-28-3bf7ab0a522a 的 603 個代號能對上多少(識別碼是 permno,要查 OSAP 有否提供 permno↔ticker/CIK 對照,或需另找對照表——這是本票最可能卡住的一環,查不到要明講);(4) 209 條裡面按 OSAP 官方 Cat.Data 分類,屬 Accounting/Analyst(財報與分析師)類的有幾多條、屬 Price/Trading(純價量)的有幾多條,列出財報類前 20 條的名稱與公布量級;(5) 時點口徑:這批值是否已按知情時點對齊(有無前視偏差),官方文檔怎麼說;(6) 用對方算好的值 vs 自己由 EDGAR 算,代價逐項列(不能自訂變體、更新滯後、覆蓋斷點、授權引用要求、無法做知情時點的自訂還原等);(7) 結論一句:今日夠不夠做基本面選股的第一輪實測,若夠,EDGAR 數據線應否改為押後。實跑取數核實(scratchpad 臨時 venv,`pip install openassetpricing`),不要只讀官網文字。落檔 research/2026-08-30-osap-firm-level-fundamentals.md,含出處連結與『未完全核實事項清單』。不下載 1.6GB 全量到 repo 內;臨時檔一律留在 scratchpad,不入 data/。不改動任何既有程式。

## 驗收條件

- [ ] 七問逐條有答,覆蓋期/頻率/宇宙/識別碼對應率/財報類條數/時點口徑/代價全部有出處
- [ ] 識別碼對照一項實跑核實:現役快照 603 個代號對得上多少,對不上的說明原因
- [ ] 結論明確答『今日夠不夠做基本面選股首輪實測』,並給 EDGAR 數據線的排序建議;報告落檔含未核實清單

## 結果

## 留言
