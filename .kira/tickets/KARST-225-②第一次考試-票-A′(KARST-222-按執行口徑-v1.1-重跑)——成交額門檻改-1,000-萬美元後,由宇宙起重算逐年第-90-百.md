---
id: KARST-225
title: ②第一次考試 票 A′(KARST-222 按執行口徑 v1.1 重跑)——成交額門檻改 1,000 萬美元後,由宇宙起重算逐年第 90 百分位、入口池、分年分桶抽 84 主 + 44 後備並鎖定於 A2/picks_before_results.md、建 84 個 T1 遮蔽取證包與對照預測 C1–C3;沿用 A/ 的腳本與快取,不動 A/
type: research
createdAt: 2026-09-13
risk: low
model: opus
fits: 用戶 2026-09-13 原話「Make it 1000萬美元」(決策簿新條);執行口徑 v1.1 修訂頁;KARST-222 收檔留言與執行紀錄——A.md;D-175 機械工作交 DeepSeek
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D06
---

## 工作內容

沿用 research/2026-09-methodology/2026-09-12-②第一次考試/A/ 的 s1–s13、pxlib.py、finlib.py、buckets.py 與 cache/(events_raw、xbrl_metrics、price_metrics、merger_days、guidance.jsonl、edgar_cache/),只改宇宙門檻一項:公布前 60 個交易日日均成交額(算術平均)≥ 1,000 萬美元(同時記中位數欄);逐年第 90/95/80 百分位門檻必須在新宇宙的事件上重算;入口池、分層比例、抽樣(種子 20260912、同 buckets.py、同 s7 規則)全部重做;新宇宙的強勢反應子集若有事件未抓過 EX-99.1 文本則補抓(單線程),已抓的不重抓;取證包沿用 s9 體例,與 A/packets/ 同 event(同 accessionNumber)且規格相同者可複製並記錄,其餘新建;controls_operating.csv 另檔重算。全部輸出到 A2/(population.csv、entry_pool.csv、thresholds.md、picks_before_results.md、packets/、controls_operating.csv、執行紀錄——A2.md);A/ 一個檔都不改。執行紀錄要多寫:v1 與 v1.1 的宇宙內事件數、入口池數、逐年門檻值的差;v1 主清單 84 個之中有多少個仍在新宇宙、多少個出現在 v1.1 主清單(重疊數);抽樣純機械、無手動換名的聲明。硬規矩同 KARST-222:含中文檔案只用 Read/Write/Edit;PYTHONUTF8=1;申報原文不入庫;不 commit;不改 strategy/ 與既有輸出;記憶體逐檔處理、單線程。

## 驗收條件

- [ ] A2/thresholds.md 逐年門檻在新宇宙上重算;反例:任何一年的宇宙內事件數等於 A/thresholds.md 同年數字(即沒有重算),即不合格
- [ ] A2/population.csv 含 turnover_mean_60d 與 turnover_median_60d 兩欄,宇宙門檻用平均值 ≥ 1,000 萬;反例:任何一列 turnover_mean_60d < 10,000,000 而 in_universe 為真,即不合格
- [ ] A2/picks_before_results.md 主 84 + 後備 44、種子 20260912、每年每桶數、SHA-256;落檔時間早於 A2/packets/ 與 A2/controls_operating.csv 任何檔;執行紀錄寫明與 v1 主清單的重疊數
- [ ] A2/packets/ 84 包,任何一包含 T1 之後日期的資料即整批不合格;複製自 A/packets/ 的包逐個記錄並核 accessionNumber 相同
- [ ] A2/controls_operating.csv 每事件一行 C1/C2/C3,不出現於任何包;A/ 目錄 git status 乾淨;不 commit

## 結果

## 留言
