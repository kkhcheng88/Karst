---
id: KARST-209
title: ①SaaS 事件籃子重定義——以 IGV(擴展軟件)與 CIBR(網絡安全)兩隻 ETF 於衝擊日(2026-01-12)前後的成分股為籃子,算每家衝擊窗相對大市跌幅與至今回補,對照 KARST-200 的 35 家找出漏掉的暴露,並按收費模式粗分類,出新籃子表供並排分析選材
type: research
createdAt: 2026-09-11
risk: low
model: sonnet
fits: 用戶 2026-09-11 原話:「What is your scope of SaaS? I think you should test IGV. and CIBR consititute stock as I think although the name is SaaS kill. But the impact of Anthopic is actually to software.」;①對齊紀錄第 35 條;KARST-200 籃子 35 家由新聞點名定,是「被叫做 SaaS」的名單不是「受衝擊的軟件」名單
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D05
---

## 工作內容

第一步成分股:取 IGV(iShares Expanded Tech-Software Sector ETF)與 CIBR(First Trust NASDAQ Cybersecurity ETF)成分股,優先用衝擊日前後(2025-12 至 2026-01)的持股快照——來源次序:發行商網站歷史持股 csv、data/ 內已有的 ETF 持股檔(先 Glob 查)、web.archive.org(本倉已知不可讀,試一次即放棄)、最後才用今日持股並在表上標「今日成分,非衝擊日成分」與偏差方向;去重、合併、記每家屬哪隻 ETF 與權重。第二步價格:用 data/prices/daily/ 或 yfinance(收市價,退回邏輯照 strategy/tools/README.md KARST-195 段)算每家 2026-01-12 至急性期低點(沿用 KARST-200 的 02-24/26)相對 SPY 跌幅、全期低點(04-10)相對跌幅、至今回補比例;基準口徑與 KARST-200 籃子表一致,方便對照。第三步對照:標出哪些在 200 的 35 家之內、哪些不在;不在的按跌幅排序,列出前二十家並標市值,答「35 家漏了哪些最重要的暴露」。第四步粗分類:對新籃子每家用 10-K 收入確認附註或業績稿一句,標收費模式(席位/用量或交易/資產或存戶/混合/授權或永久/其他)與證據出處;做不到的標查不到,不猜。第五步:出新籃子表 csv/md 與一頁總覽(籃子家數、跌幅分佈、與 35 家的差異、收費模式分佈、建議並排選材的候選十家與理由)。落檔 research/2026-09-methodology/2026-09-11-①SaaS籃子重定義/。不改 KARST-200 與 206 既有輸出;含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不 commit。

## 驗收條件

- [ ] IGV+CIBR 成分股表落檔,標來源與快照日期;若只得今日成分,偏差方向明寫
- [ ] 每家衝擊窗相對跌幅、全期低點跌幅、至今回補落檔,口徑與 KARST-200 一致;與 35 家的差異表與「漏掉的前二十家」落檔
- [ ] 收費模式粗分類附出處,查不到者標明;總覽含建議並排選材十家
- [ ] 不改 200/206 既有輸出、karst/ strategy/ library/;含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不 commit

## 結果

## 留言
