---
id: KARST-018
title: LLM 訓練截止日圍堵選項調研:可用模型截止日、成本、前向驗證替代
type: research
createdAt: 2026-08-27
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: KARST-018-researcher
epic: V1 藍圖
deliverable: KARST-D01
---

## 工作內容

要答的事實問題:人物判官在回測期出判斷時,如何避免模型「已知結局」(A-002)。要查:(1) 現時可經 API 取用的主要 LLM(Anthropic、OpenAI、Google、開源)各自的訓練截止日與是否仍可調用,列表附出處;(2) 截止日最早而仍可用的模型有哪些,能否覆蓋 2023–2025 各段回測期;(3) 學界/業界對「LLM 回測前視偏差」的既有做法(遮蔽實體名、只餵時點前文本、用早期模型、只做前向)各自的效果與局限,附文獻或實作出處;(4) 每次判斷的粗略成本量級(以典型 3–5k token 輸入估),供 KARST-017 定成本上限。只查事實不代拍板。

## 驗收條件

- [ ] 模型截止日對照表落檔,每列附出處與查證日期
- [ ] 四種圍堵做法各有一段效果/局限與出處
- [ ] 每次判斷成本量級有估算與假設
- [ ] 報告落檔 research/ 並在票的結果引用路徑

## 結果

## 留言
