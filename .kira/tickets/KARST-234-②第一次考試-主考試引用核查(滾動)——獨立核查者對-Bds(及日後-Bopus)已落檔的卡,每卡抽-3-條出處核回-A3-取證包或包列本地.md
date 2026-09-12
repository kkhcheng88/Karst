---
id: KARST-234
title: ②第一次考試 主考試引用核查(滾動)——獨立核查者對 B/ds/(及日後 B/opus/)已落檔的卡,每卡抽 3 條出處核回 A3 取證包或包列本地文件(存在/數字相符/T1 前),另核 csv 28 欄解析、取值集合、pred 欄尺度(小數 0.12 而非 71.0)、卡與 csv 一致;分批交回彙總,不評內容、不開結果、不列公司名
type: research
createdAt: 2026-09-13
risk: low
model: opus
fits: ②第四輪外評「記引用錯誤、漏答」與「Opus 不擔任 DeepSeek 的裁判」;執行口徑 v1.2 修訂頁「判斷層雙臂」額外記錄列;十宗試跑 KARST-228 同法;主考試首批 12 宗已落檔(E001–E010、E043、E044)
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D06
---

## 工作內容

輸入:B/ds/卡-*.md 與 B/ds/rows/*.csv(本批:已落檔者;日後每批由主 agent 留言指定);取證包 A3/packets/<event_id>.json;本地文件 A/edgar_cache/<local_gz>。做法照 KARST-228:每卡以種子 20260913 隨機抽 3 條帶出處的判斷句,逐條核(一)出處在包內或包列本地文件(否=包外);(二)引用的數字或事實在該文件找得到(找不到=捏造;數字不符=錯引;相符=正確);(三)文件申報日 ≤ T1(否=越界);另核逐字稿引用是否指向包內 earnings_call_transcript 段落。格式:csv 標準解析恰 28 欄;persistence/supply/driver 取值在允許集合(驅動八類);pred_g2/g4 六欄為小數且 lo ≤ point ≤ hi,絕對值 > 5 者列為尺度違規;p_continue 在 0–1 且與 persistence 帶一致;卡含第一至八步、contamination_note、執行紀錄節含 date -u 原始輸出;csv 的 persistence_overall/p_continue/pred_g2_point 與卡第八步/第三步一致。輸出 B/核查——引用與一致性(滾動).md:每批一節(逐條表、彙總五類計數、格式與一致性違規清單);不寫哪臂較好、不評內容對錯、不開 T1 後結果、不列公司名。硬規矩:只讀上述輸入;禁網;不改任何卡與 csv;含中文檔案只用 Read/Write/Edit;PYTHONUTF8=1;不 commit。

## 驗收條件

- [ ] 本批每卡 3 條出處逐條列 event_id、出處、找到的位置、結果;反例:任何一條只寫「正確」而無位置,即不合格
- [ ] 本批彙總五類計數、csv 解析合格數、取值與尺度違規清單、一致性違規清單、缺節清單;反例:出現內容判詞或公司名,即不合格
- [ ] 沒有改動 B/ 任何卡與 csv;沒有讀 controls/population/entry_pool/data/;不 commit

## 結果

## 留言
