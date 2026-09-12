---
id: KARST-227
title: ②第一次考試 十宗試跑——DeepSeek 臂與 Opus 臂各自獨立對同一批 10 個取證包(A2 版,只作模型行為觀察,不計入主考試)用提示詞 v1 判斷一次,主 agent 出觀察報告(格式合格率、引用是否捏造、漏答、讀了哪些文件、一致性、時間與費用),供用戶決定 84 宗主考試的模型安排;不開任何結果、不比較準確度
type: research
createdAt: 2026-09-13
risk: low
model: opus
fits: 用戶 2026-09-13 原話「Compare 10 first. And get the observation first」(推翻主 agent「十宗看不出準不準」的保留,主 agent 已講明並照做);②第四輪外評雙臂設計;執行口徑 v1.2 修訂頁「判斷層雙臂」與「次序」列;D-175 判斷層 Opus,DeepSeek 臂為對照
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D06
---

## 工作內容

十個事件固定為 A2/packets 的 E001、E009、E017、E025、E033、E041、E049、E057、E065、E073(每隔八個取一,跨 2015–2024;A2 是已作廢的 v1.1 版本,試跑只觀察模型行為,輸出不入主考試,主考試 84 宗另由 A3 重判)。兩臂各自獨立:DeepSeek V4.1 Flash(kira-worker,effort high,一隊順序做十宗)與 Anthropic Opus 5(Agent 工具,兩隊各五宗);同一提示詞 v1、同一共同指令(B/子代理共同指令——票B.md,取證包改讀 A2/packets,輸出改 試跑/ds/ 與 試跑/opus/);每事件一次執行;兩臂互不讀對方輸出;不讀 controls/population/entry_pool/data/。交回後主 agent 寫 試跑/觀察報告——十宗雙臂.md:每臂的 rows 解析合格率與欄位一致性違規數、每臂抽 3 張卡各 3 條出處核回包內或本地文件(捏造數)、「查不到/無法判斷」數、讀了哪些截止前文件(由子代理回報)、persistence 分佈、時間與 token/費用;不開結果、不評準確度;結論只寫「可觀察的差異」與建議的 84 宗模型安排(用戶裁)。含中文檔案只用 Read/Write/Edit;不 commit(主 agent commit)。

## 驗收條件

- [ ] 試跑/ds/rows/ 與 試跑/opus/rows/ 各 10 個單行 csv,event_id 一一對應;反例:任何一臂缺行或一事件兩行即該臂不合格
- [ ] 每臂 10 張卡含第一至八步;反例:出處指向包外來源或 T1 後資料,記入觀察報告的捏造/越界數
- [ ] 觀察報告含六項指標並附每臂時間與費用;明寫「不比較準確度、結果未開、輸出不入主考試」
- [ ] 兩臂互不讀對方輸出;不讀 controls/population/entry_pool/data/;不改 A/、A2/、A3/、strategy/;不 commit

## 結果

## 留言
