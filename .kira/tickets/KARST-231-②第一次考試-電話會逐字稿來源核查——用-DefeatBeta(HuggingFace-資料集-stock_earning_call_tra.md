---
id: KARST-231
title: ②第一次考試 電話會逐字稿來源核查——用 DefeatBeta(HuggingFace 資料集 stock_earning_call_transcripts)查 A3 主 84 + 後備 44 事件的訊號季逐字稿有沒有、日期是否 ≤ T1、文本是否完整;另查 stock_news 表的日期覆蓋;把可用逐字稿存到 A3/transcripts/ 並寫注入腳本(不動 A3/packets/,注入待主 agent 派);只報數量,不列公司名
type: research
createdAt: 2026-09-13
risk: low
model: opus
fits: 用戶 2026-09-13 問「電話會逐字稿拿不到?Defeatable?」;提示詞 v1.1 輸入第 2 項「已公開的電話會逐字稿(有則入,無則標查不到)」;A-012 記 DefeatBeta 財報只到 2019/2022,但逐字稿表另計,未核;D-175 取數交 DeepSeek
dependsOn: []
claimedBy: transcripts-ds
epic: 方法論期(D-166)
deliverable: KARST-D06
---

## 工作內容

先查倉內有沒有 defeatbeta-api(pip show)或 KARST-076 的讀法(research/ 下 2026-08-29 或 2026-08-30 有關 DefeatBeta 的腳本);無則 pip install defeatbeta-api 或直接讀 HuggingFace 資料集 defeatbeta/yahoo-finance-data 的 stock_earning_call_transcripts 分區(記下實際用了哪條路)。對 A3/picks_before_results.md 的 128 個事件(只讀 cik/ticker/反應日/fiscal_quarter,不讀其他),逐宗查:有沒有該訊號季的逐字稿(fiscal_year、fiscal_quarter 對應 A3 packets 1_事件識別.fiscal_quarter,注意財年季與曆季的對應要用 report_date 校)、report_date 是否 ≤ T1(反應日)、段數與字數、是否含 Q&A;存到 A3/transcripts/<event_id>.json(segments 原樣 + 來源與抓取時間),report_date > T1 者不存、記為越界。另查 stock_news 表:總列數、最早與最晚日期、A3 事件 T1 前 30 日內有新聞的事件數(只計數,不存文本)。寫 A3/transcripts/覆蓋核查——逐字稿與新聞.md:逐年覆蓋率(主 84 / 後備 44 分開)、越界數、缺的原因分類、資料來源版本與抓取時間、注入建議(把 segments 放入 packet 2_觸發資料.earnings_call_transcript,masking_check 加 transcript_date)。寫 A3/inject_transcripts.py(只寫不跑:讀 A3/transcripts/*.json 注入對應 packet,並更新 masking_check;跑前先備份 packets/ 到 A3/cache/packets_before_transcripts/)。硬規矩:不改 A3/packets/ 與其他既有檔;不列公司名或代號;含中文檔案只用 Read/Write/Edit;PYTHONUTF8=1;不 commit;網絡只用於 HuggingFace/DefeatBeta 取數。

## 驗收條件

- [ ] 覆蓋核查檔有主 84 與後備 44 分開的逐年覆蓋率、越界數、缺的原因分類、來源版本;反例:任何一宗有逐字稿而 report_date 未核對 T1,即不合格
- [ ] A3/transcripts/ 內每個有逐字稿的事件一個 json,含 segments、report_date、來源、抓取時間;report_date > T1 者不存
- [ ] inject_transcripts.py 存在且只寫不跑;A3/packets/ 未被改動(git status 乾淨);全檔無公司名或代號;不 commit

## 結果

## 留言
