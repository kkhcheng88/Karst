---
id: KARST-232
title: ②第一次考試 A3 取證包補強(判斷層派出前最後一步)——按 picks_after_guidance_check.md 換位後清單再剔十宗試跑重疊 1 宗補位,為換入者建包;全部包重建同業節(SIC 四位數同桶、不足退三位數、兩大同業資本開支摘錄非空)、加自家八季存貨/應收/遞延收入/資本開支/折舊/現金/總債務/淨利/攤薄 EPS/股數、加上一份業績稿的指引句、加 preliminary_release 標籤、補抓兩包截短文件、注入已核的逐字稿(A3/transcripts/ 有則注);全部 T1 前過濾;重跑遮罩檢查;不動鎖定檔;只報數量
type: research
createdAt: 2026-09-13
risk: low
model: opus
fits: KARST-230 核查結果(同業規則未實作 54 包不合、兩包文件截短、指引換位 2 宗待建包、十宗重疊 1 宗);用戶 2026-09-13 問「any other figures from the fundamentals?」與逐字稿可取(KARST-231);提示詞 v1.1 輸入表;執行口徑 v1.2 補充四;D-175 取數交 DeepSeek
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D06
---

## 工作內容

清單:以 A3/picks_after_guidance_check.md 的換位後主 84 為準;再讀 A3/入口抽查與取證包品質——A3.md 第三部,把與十宗試跑重疊的那 1 宗(其結果已在試跑被打開,屬留出樣本)按後備清單同年同桶優先補位(略過已用的 B028/B034),寫 A3/picks_final.md(84 宗 event_id、換位紀錄、SHA-256;原兩份鎖定檔不改)。建包:換入的 3 宗(B028、B034、新補位者)用 A3/s9_packets.py 體例建包。全部 84 包補強(先把 packets/ 整個複製到 A3/cache/packets_before_enrich/):(1) 同業節重建——同 SIC 四位數且同行業桶(buckets.py),不足 5 家退三位數,仍不足標「同業資料不足」;兩大同業(按 60 日成交額)最近年報(申報日 ≤ T1)資本開支節摘錄,不得為空,抓不到標查不到;(2) 4_財務數列 加八季:存貨、應收帳、遞延收入(合約負債)、資本開支、折舊攤銷、現金及等價物、總債務(長短期借款合計)、淨利潤、攤薄 EPS、攤薄股數——全部 XBRL 首報值且來源申報日 ≤ T1,缺者標查不到;訊號季一行只准用 EX-99.1 稿內有的項目(稿內無的標查不到);(3) 2_觸發資料 加 prior_release_guidance:上一份業績稿(訊號季前一季的 8-K EX-99.1,申報日 ≤ T1)的指引句原文(用 A3 解析器找出的句子,原句照抄,不給解析結果),抓不到標查不到;(4) preliminary_release 標籤(只對稿頭即初步業績者為真;E044 類);(5) 補抓 KARST-230 指出截短的兩包文件;(6) 若 A3/transcripts/<event_id>.json 存在且 report_date ≤ T1,注入 2_觸發資料.earnings_call_transcript(照 A3/inject_transcripts.py),masking_check 加 transcript_date;沒有的保持查不到;(7) 每包 masking_check 重算:全文掃 ISO 日期,T1 之後只准 T2 與凍結日;越界即該包不合格並修。輸出:A3/packets/ 就地更新(84 包對 picks_final)、A3/補強紀錄——A3.md(逐項數量:同業重建後合格數、各新增欄位覆蓋率、prior 指引句覆蓋、逐字稿注入數、preliminary 數、遮罩重核 84/84、換位紀錄)、A3/controls_operating.csv 補換入 3 宗的 C1/C2/C3。硬規矩:不改 picks_before_results.md 與 picks_after_guidance_check.md;不列公司名或代號;含中文檔案只用 Read/Write/Edit;PYTHONUTF8=1;單線程逐包;申報原文不入庫;不 commit。

## 驗收條件

- [ ] A3/picks_final.md 存在:84 宗、換位紀錄(指引 2 + 重疊 1)、SHA-256;反例:任何換位不按同年同桶優先、或用了已用的後備,即不合格
- [ ] 84 包(對 picks_final)全部含同業節(四位數規則或「同業資料不足」)、新增八季十項(缺者標查不到)、prior_release_guidance、preliminary_release、masking_check 重算;反例:任何一包出現 T1 之後日期(T2 與凍結日除外)、或新增欄位的來源申報日 > T1,即整批不合格
- [ ] 補強紀錄含各項覆蓋率與數量;A3/cache/packets_before_enrich/ 有補強前備份;controls_operating.csv 含換入 3 宗;無公司名或代號;不 commit

## 結果

## 留言
