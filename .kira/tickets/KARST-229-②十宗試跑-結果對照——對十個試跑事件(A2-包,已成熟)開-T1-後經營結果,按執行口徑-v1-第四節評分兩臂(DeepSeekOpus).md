---
id: KARST-229
title: ②十宗試跑 結果對照——對十個試跑事件(A2 包,已成熟)開 T1 後經營結果,按執行口徑 v1 第四節評分兩臂(DeepSeek/Opus)的兩季與四季收入增速預測,對照 C2 趨勢延續、C3 訊號持續、有資料的 C1;出預測誤差、區間命中、延續二值、分歧格;十宗只作方向觀察,不作能力宣稱;十宗自此列為主考試外的留出樣本
type: research
createdAt: 2026-09-13
risk: low
model: opus
fits: 用戶 2026-09-13 原話「Actually what is the quality of the result towards the objective?」與「Compare 10 first. And get the observation first」;執行口徑 v1 第四節評分規則;第四輪外評「全部落檔後才評分、評分者只讀機械版與其後財報」——試跑十宗兩臂已全部落檔;D-175 評分交 DeepSeek
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D06
---

## 工作內容

輸入:試跑/ds/rows/*.csv 與 試跑/opus/rows/*.csv(只讀機械版;DeepSeek 臂四行錯位的 E033/E041/E065/E073 按工人留言的還原方法讀回 27 欄,還原步驟寫入報告);A2/controls_operating.csv 的 C1/C2/C3(十個事件);A2/packets/<event_id>.json 的 1_事件識別(T1、fiscal_quarter、signal_q_end)與 4_財務數列(g0);T1 後的實際季度收入取 data/sec/companyfacts/CIK*.json.gz 首報值(照 A/finlib.py 體例),取訊號季之後 Q+1 至 Q+4 的按年收入增速;指引下修以 Q+1、Q+2 業績稿 EX-99.1 文字正則(lower/reduce/cut + guidance/outlook)判,抓不到標查不到。評分照執行口徑 v1 第四節:M1 = Q+1、Q+2 平均按年增速;M2 = Q+1 至 Q+4;延續(二值)= M1 ≥ 0.8×g0 且無指引下修(g0 為負的事件另標,並同時報以「M1 ≥ g0」為延續的替代定義);連續:每臂 pred_g2_point 對 M1 的絕對誤差、pred_g2_lo–hi 是否命中 M1、pred_g4 同;C2、C3(與有值的 C1)對 M1 的絕對誤差;每臂 persistence_overall 對延續二值的交叉表;分歧格(臂判高而 C2 判不延續、臂判低而 C2 判延續)的實際結果;敏感度 0.7/0.9。輸出 試跑/結果對照——十宗雙臂.md:逐事件表(十行:g0、M1、M2、指引下修、兩臂點值與區間、C1/C2/C3、誤差)、彙總表(每臂與每個基準的 MAE 中位/平均、區間命中率、延續交叉表、分歧格)、g0 為負四宗分開一段、明寫「十宗只作方向觀察、受記憶污染、不作能力宣稱」;另存 試跑/結果對照.csv。硬規矩:不改任何卡與 rows;不讀卡的人讀版;不讀 A3/;含中文檔案只用 Read/Write/Edit;PYTHONUTF8=1;不 commit。

## 驗收條件

- [ ] 結果對照檔含十行逐事件表與彙總表;反例:任何一個事件缺 M1 而未標原因(退市/資料不足/未成熟),即不合格
- [ ] 每臂與 C2/C3(及有值的 C1)的 MAE 與區間命中率齊;延續二值用 0.8×g0 與 M1 ≥ g0 兩個定義各報一次;g0 為負四宗分開一段
- [ ] DeepSeek 臂四行錯位的還原步驟寫明並可重現;沒有讀卡的人讀版;沒有改 ds/ opus/;沒有讀 A3/;不 commit

## 結果

## 留言
