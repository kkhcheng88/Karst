---
id: KARST-233
title: ②第一次考試 票 B-ds——DeepSeek 臂:用提示詞 v1.1 對 A3 最終清單 84 個補強後取證包逐事件判斷改善驅動可持續性(每事件一次執行,只用 T1 前資料,不讀對照與結果),交 84 張卡與 84 行 28 欄機械版到 B/ds/;與 Opus 臂(KARST-223)互不讀
type: research
createdAt: 2026-09-13
risk: low
model: opus
fits: ②第四輪外評雙臂設計與用戶 2026-09-13 兩問(次序:DeepSeek 臂先跑全部 84);執行口徑 v1.2 修訂頁「判斷層雙臂」;提示詞 v1.1;十宗試跑觀察報告;D-175 對照臂由 DeepSeek 跑
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D06
---

## 工作內容

輸入:A3/picks_final.md 的 84 個 event_id(KARST-232 交回後);取證包 A3/packets/<event_id>.json(補強版:同業四位數、十項新數列、上一稿指引句、逐字稿有則入);截止前文件本體 A/edgar_cache/<local_gz>。方法正本一字不改:strategy/specs/提示詞——改善驅動可持續性判斷-v1.1.md 第三步至第八步(第九步熊方另票);共同指令 B/子代理共同指令——票B.md(輸出目錄 B/ds/;凡 A3/packets 即現行)。每事件一次執行,順序照 picks_final;寫完不改;發現錯誤另寫 note。輸出 B/ds/卡-<event_id>-<ticker>-<signal_date>.md、B/ds/rows/<event_id>.csv(28 欄,Python csv 模組 QUOTE_ALL)、B/ds/執行紀錄——ds.md(模型名 deepseek-v4.1-flash、effort、每事件 date -u 實測起訖、讀了哪些文件、失敗與重跑)。硬界線:只用取證包與包列本地文件;禁網;禁讀 A3/controls_operating.csv、population*、entry_pool、thresholds、picks_before_results、cache/、執行紀錄、data/、B/opus/、試跑/;共識欄若包內有(富途預測對實際)照用,否則查不到;contamination_note 必填。含中文檔案只用 Read/Write/Edit;不 commit;工人若被中止,續做 prompt 由主 agent 派,已落檔事件不重判。

## 驗收條件

- [ ] B/ds/rows/ 有 84 個單行 csv,event_id 與 A3/picks_final.md 一一對應,標準 csv 解析恰 28 欄;反例:任何一個 event_id 缺行、兩行、欄數不對或取值不在允許集合,即該行不合格並列入執行紀錄
- [ ] 每張卡含第一至八步、contamination_note、執行紀錄節(date -u 原始輸出);反例:出現 T1 之後資料、包外來源或分析員預期數字(包內無者),即該卡作廢
- [ ] 執行紀錄——ds.md 齊;沒有讀禁讀清單;沒有改 A3/ 與 strategy/;不 commit

## 結果

## 留言
