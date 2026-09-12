---
id: KARST-228
title: ②十宗試跑 引用核查——獨立核查者對 DeepSeek 臂與 Opus 臂各 10 張卡逐張抽 3 條出處,核回取證包或包內本地文件原文(是否存在、數字是否相符、是否 T1 前),出每臂捏造數與錯引數;另核每臂 csv 與卡的一致性;不評判斷好壞、不開結果
type: research
createdAt: 2026-09-13
risk: low
model: opus
fits: ②第四輪外評(兩臂互不作裁判;記引用錯誤、漏答);執行口徑 v1.2 修訂頁「判斷層雙臂」額外記錄列;KARST-227 觀察報告需要的兩項指標(引用捏造數、漏答數);D-175 機械核查交 DeepSeek
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D06
---

## 工作內容

輸入:research/2026-09-methodology/2026-09-12-②第一次考試/試跑/ds/ 與 試跑/opus/ 各 10 張卡與 rows/*.csv;取證包 A2/packets/<event_id>.json;本地文件 A/edgar_cache/<local_gz>(gzip 純文字)。做法:每張卡以固定種子(20260913)隨機抽 3 條帶出處的判斷句(出處=申報類型+accession+節名或包內欄位),逐條核:(一)出處指向的文件是否在包內或包列本地文件之中(不在=包外來源);(二)引用的數字或事實在該文件中是否找得到(找不到=捏造;找到但數字不符=錯引;找到且相符=正確);(三)文件申報日是否 ≤ T1(否=越界)。另核每臂:csv 可否用標準 csv 解析為 27 欄、persistence/supply/driver 取值是否在允許集合、卡是否含第一至八步與 contamination_note、csv 的 persistence_overall 與 pred_g2_point 是否與卡第八步/第三步一致。輸出 試跑/核查——引用與一致性.md:每臂一表(30 條出處逐條:event_id、出處、核查結果、備註)、每臂彙總(正確/錯引/捏造/包外/越界各多少;csv 解析合格數;一致性違規數),不寫任何「哪臂較好」的判詞,不評內容對錯,不開 T1 後結果。硬規矩:只讀上述輸入;禁網;不改任何卡與 csv;含中文檔案只用 Read/Write/Edit;PYTHONUTF8=1;不 commit。

## 驗收條件

- [ ] 核查檔存在,兩臂各 30 條出處逐條列結果;反例:任何一條只寫「正確」而無指出文件與位置(行號或節名),即不合格
- [ ] 每臂彙總五類計數(正確/錯引/捏造/包外/越界)與 csv 解析合格數、一致性違規數;反例:出現「哪臂較好」或內容判詞,即不合格
- [ ] 沒有改動 ds/ 與 opus/ 任何檔;沒有讀 controls/population/entry_pool/data/;不 commit

## 結果

## 留言
