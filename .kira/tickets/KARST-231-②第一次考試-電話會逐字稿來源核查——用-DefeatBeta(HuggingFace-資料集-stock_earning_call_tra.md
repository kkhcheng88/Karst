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
closed: 2026-09-13
---

## 工作內容

先查倉內有沒有 defeatbeta-api(pip show)或 KARST-076 的讀法(research/ 下 2026-08-29 或 2026-08-30 有關 DefeatBeta 的腳本);無則 pip install defeatbeta-api 或直接讀 HuggingFace 資料集 defeatbeta/yahoo-finance-data 的 stock_earning_call_transcripts 分區(記下實際用了哪條路)。對 A3/picks_before_results.md 的 128 個事件(只讀 cik/ticker/反應日/fiscal_quarter,不讀其他),逐宗查:有沒有該訊號季的逐字稿(fiscal_year、fiscal_quarter 對應 A3 packets 1_事件識別.fiscal_quarter,注意財年季與曆季的對應要用 report_date 校)、report_date 是否 ≤ T1(反應日)、段數與字數、是否含 Q&A;存到 A3/transcripts/<event_id>.json(segments 原樣 + 來源與抓取時間),report_date > T1 者不存、記為越界。另查 stock_news 表:總列數、最早與最晚日期、A3 事件 T1 前 30 日內有新聞的事件數(只計數,不存文本)。寫 A3/transcripts/覆蓋核查——逐字稿與新聞.md:逐年覆蓋率(主 84 / 後備 44 分開)、越界數、缺的原因分類、資料來源版本與抓取時間、注入建議(把 segments 放入 packet 2_觸發資料.earnings_call_transcript,masking_check 加 transcript_date)。寫 A3/inject_transcripts.py(只寫不跑:讀 A3/transcripts/*.json 注入對應 packet,並更新 masking_check;跑前先備份 packets/ 到 A3/cache/packets_before_transcripts/)。硬規矩:不改 A3/packets/ 與其他既有檔;不列公司名或代號;含中文檔案只用 Read/Write/Edit;PYTHONUTF8=1;不 commit;網絡只用於 HuggingFace/DefeatBeta 取數。

## 驗收條件

- [x] 覆蓋核查檔有主 84 與後備 44 分開的逐年覆蓋率、越界數、缺的原因分類、來源版本;反例:任何一宗有逐字稿而 report_date 未核對 T1,即不合格
- [x] A3/transcripts/ 內每個有逐字稿的事件一個 json,含 segments、report_date、來源、抓取時間;report_date > T1 者不存
- [x] inject_transcripts.py 存在且只寫不跑;A3/packets/ 未被改動(git status 乾淨);全檔無公司名或代號;不 commit

## 結果

## 留言

### agent:transcripts-ds · 2026-09-13 04:36
\## 結論
逐字稿拿得到。128 宗之中 114 宗(89%)已按 report_date ≤ T1 校對後存檔:主 84 有 72(86%)、後備 44 有 42(95%)。越界 8 宗(有稿但收錄日晚於 T1,其中 6 宗只遲 1–4 日,屬 Yahoo 收錄滯後而非會後才開),真缺 6 宗(全在主清單,皆「公司有逐字稿歷史但該季未收錄」,無一宗是公司整體無稿)。
新聞表 stock_news 只有 2025-03-11 之後的貨:128 宗中僅 4 宗 T1 落在覆蓋期內,該 4 宗全部在 T1 前 30 日內有新聞(最多 11 宗、中位 6 宗);其餘 124 宗是表沒蓋到,不是當時沒有新聞。
注入腳本已寫未跑;實算 72 宗全部可 inline(包大小中位由 37 KB 升至 89 KB,最大 138 KB),無一宗需走路徑模式。

\## 證據
- 覆蓋核查:`A3/transcripts/覆蓋核查——逐字稿與新聞.md`(主 84 與後備 44 分開的逐年覆蓋率、越界數、缺的分類、來源版本與抓取時間、新聞表統計、注入建議、跑不通之處)
- 逐宗結果:`A3/transcripts/coverage.csv`(128 列)+ `_fetch_log.jsonl`
- 日期校對:114 宗 report_date 相對 8-K 公布日為 −1 日 20 宗、0 日 79 宗、+1 日 15 宗,全部落在一日內 —— 財年口徑對應正確的實證(財季若對錯會差一整個季度)
- 自核:`verify_outputs.py` 跑出 `FAILS: 0`(逐檔核 report_date ∈ (signal_q_end, T1];欄位齊;n_segments/n_chars 與 segments 實長一致;coverage.csv 與檔案雙向一致;128 宗齊;檔內無代號)
- 去識別:`leak_check.py` 掃 10 個控制檔 + 本檔,零代號零公司名
- 範圍:`A3/packets/` git status 0 行改動;本票全程未執行任何 git 指令(不 add、不 commit)
- 來源:defeatbeta-api 0.0.60 / HuggingFace `defeatbeta/yahoo-finance-data` 的 `stock_earning_call_transcripts`(更新時間 2026-09-12T05:17:03Z);抓取 2026-09-12T20:23Z–20:31Z

\## 產物
- `A3/transcripts/<event_id>.json` × 114(segments 原樣 + report_date + 來源 + 抓取時間 + 段數字數 + Q&A 兩欄)
- `A3/transcripts/coverage.csv`、`_fetch_log.jsonl`、`news_coverage.json`、`覆蓋核查——逐字稿與新聞.md`
- `A3/inject_transcripts.py`(只寫不跑;不加 `--apply` 只印報告不動檔;跑前自動把 packets/ 複製到 `A3/cache/packets_before_transcripts/`;後備 44 無包自動略過)
- 輔助腳本:`fetch_transcripts.py`、`news_coverage.py`、`diag_qna.py`、`inject_preview.py`、`summarize.py`、`verify_outputs.py`、`leak_check.py`

\## 未解與風險
1. **平行 commit 事件(須主 agent 知悉)**:本票進行期間 2026-09-12T20:28:10Z,另一隊的 commit `636be97`(KARST-230 收檔)把本票**尚未完成的** `A3/transcripts/` 86 個檔一併 commit 了。該 commit 內有本票產出的逐字稿 JSON,但**沒有** `inject_transcripts.py` 與覆蓋核查檔(當時未寫),即它是本票的中途快照,不是任何人的完成品。本票沒做任何 git 動作,但倉內現有一個含本票半成品的 commit。
2. **越界 8 宗是否算「有稿」待裁**:6 宗只遲 1–4 日,電話會幾乎肯定在 T1 當日/前一日已開完,遲的是 Yahoo 收錄日。票面判準是收錄日 ≤ T1,故一律不存;要補回需另立判準(以電話會實際日期而非收錄日入包),本票不自行放寬。
3. **stock_news 起點 2025-03-11**,對 2015–2024 的事件完全無用;若要新聞證據需另找來源,或接受該批事件新聞欄一律「查不到」。
4. **逐字稿是 Yahoo 轉包、整批重建不存版本**,只能記 `update_time`,做不到「當日看到什麼」的版本回溯;`report_date` 只到日、無時刻,判不出 T1 當日的會是收市前還是收市後(本票 79 宗同日)。
5. **13 宗逐字稿既無問答段標記亦無分析員發言段**(只有管理層預備發言),判斷時不可當作管理層沒有被追問。
6. `has_qna` 原以講者標籤判,114 宗全中無分辨力,已改為 `has_qna_section`(文字標記,97 宗)與 `n_analyst_segs`(分析員段數,39 宗)兩欄,`has_qna` 保留為兩者取或。
7. 逐字稿本文必然含公司名與管理層姓名(資料本身如此),與「全檔不列公司名」字面衝突;已按票面要求原樣存 segments,控制檔與本留言則零公司名零代號。
