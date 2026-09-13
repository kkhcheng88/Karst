---
id: KARST-223
title: ②第一次考試 票 B——Opus 5 用凍結提示詞 v1 對票 A 的 84 個遮蔽取證包逐事件判斷改善驅動可持續性(每事件一次執行,只用 T1 前資料),交 84 張人讀卡與 84 行機械版判-②;不開任何 T1 後結果、不讀對照預測
type: research
createdAt: 2026-09-12
risk: low
model: opus
fits: ②對帳單 §十二 第 5 條(用戶以第二輪外評全文作答,同意 84 個公司事件作探索性第一場);執行口徑——②第一次考試-v1.md 第三節「判斷(票 B,Opus)」與第一節「判斷模型」列;D-175:判斷層至少 Opus high
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D06
closed: 2026-09-13
---

## 工作內容

輸入:research/2026-09-methodology/2026-09-12-②第一次考試/A/packets/E001–E084.json(T1 遮蔽取證包;截止前文件只留本地路徑於 A/edgar_cache/,由判斷者按需讀)。方法正本一字不改:strategy/specs/提示詞——改善驅動可持續性判斷-v1.md 第三步至第八步(第九步熊方屬票 C);能力卡 strategy/specs/能力卡——改善驅動可持續性判斷-v1.md。每事件由 Anthropic Opus 5(Agent 工具 model: opus)一次執行,不重跑挑好;每個子代理最多三個事件,順序照鎖定清單。輸出落 research/2026-09-methodology/2026-09-12-②第一次考試/B/:卡-<event_id>-<ticker>-<signal_date>.md(第一至八步)、rows/<event_id>.csv(一行,欄位照能力卡 v1 格五)、執行紀錄——B.md(模型、日期、每子代理事件清單、失敗與重跑紀錄——重跑只准在子代理未產出任何檔時)。硬界線:只用取證包與包內列出的本地文件;禁 WebSearch/WebFetch;禁讀 A/population.csv、entry_pool.csv、controls_operating.csv、data/ 之下任何價格或財報;禁讀其他事件的卡;每卡末必附 contamination_note。判斷模型不得改提示詞;主 agent 收齊後合併 rows 為 判-②.csv 並抽查五張卡的出處。含中文檔案只用 Read/Write/Edit;不 commit。

## 驗收條件

- [x] B/rows/ 有 84 個單行 csv,event_id 與 A/picks_before_results.md 主清單(含補位後)一一對應;反例:任何一個 event_id 出現兩行、或缺行,即不合格
- [x] 每張卡含第一至八步全部節,第三步的兩季與四季點值與區間為數字;反例:persistence_overall 為「高」而 pred_g2_point < 0.8 × g0 且無解釋,即該卡退回
- [x] 每張卡引用的出處全部指向取證包或包內列出的本地文件;反例:出現 T1 之後日期的資料、分析員預期數字、或包外來源,即該卡作廢並記入執行紀錄
- [x] 執行紀錄——B.md 記模型名(claude-opus-5)、每子代理的事件清單、一次執行原則的落實、任何重跑與原因
- [x] 沒有讀 controls_operating.csv / population.csv / entry_pool.csv / data/;沒有改 strategy/ 與 A/;不 commit

## 結果

## 留言

### agent:fable-main · 2026-09-13 00:33
輸入改為 A2/(執行口徑 v1.1,成交額門檻 1,000 萬美元,D-176;KARST-225 已收檔):取證包 research/2026-09-methodology/2026-09-12-②第一次考試/A2/packets/(84 包:E001–E084 之中 81 個 + 補位 B011/B029/B034),鎖定清單 A2/picks_before_results.md(2026-09-13 00:19:19),截止前文件本體仍在 A/edgar_cache/。A/ 的 v1 輸出已作廢,不得讀 A/packets/。票面「票 A」字樣一律讀作 A2。派工仍待 DeepSeek 工人開關關閉(Kira 閘擋 Agent 工具),用戶未答。
