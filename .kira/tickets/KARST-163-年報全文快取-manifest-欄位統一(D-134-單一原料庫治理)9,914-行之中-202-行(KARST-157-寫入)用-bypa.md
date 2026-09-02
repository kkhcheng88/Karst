---
id: KARST-163
title: 年報全文快取 manifest 欄位統一(D-134 單一原料庫治理):9,914 行之中 202 行(KARST-157 寫入)用 by/path/primaryDoc,其餘 9,712 行(KARST-153)用 fetchedBy;統一為一套欄位、寫 README 說明欄位與新增規則、加一支唯讀校驗腳本(欄位齊全、sha256 對檔、無重複 accession)
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: data-gov-163
deliverable: KARST-D02
closed: 2026-09-03
---

## 工作內容

背景:D-134 用戶定「只保留單一副本,數據治理是黃金原則」;年報全文單一快取在 C:\projects\Karst\data\sec\10k_text\(<TICKER>_<accession>.txt.gz + manifest.jsonl)。兩張票先後寫入,欄位不一致:KARST-153 的 9,712 行是 ticker, cik, accession, form, filingDate, reportDate, url, chars, sha256, fetchedAt, fetchedBy;KARST-157 的 202 行是 ticker, cik, accession, form, filingDate, reportDate, url, chars, sha256, fetchedAt, by, path, primaryDoc。做法:①先讀兩張票的抓取腳本(experiments/2026-09-02-lazy-prices/ 與 experiments/2026-09-02-narrative-layers-v2/)確認每欄意義;②定一套欄位:必填 ticker, cik, accession, form, filingDate, reportDate, url, chars, sha256, fetchedAt, fetchedBy;選填 primaryDoc(原始文件名,有就保留);path 一欄刪去(路徑由 ticker+accession 推得,存路徑會與搬檔脫節);③把 202 行的 by 改名 fetchedBy、刪 path、保留 primaryDoc,其餘行不動;改 manifest 前先備份到 ~/.claude/backups/10k_manifest.2026-09-03.bak;④寫 data/sec/10k_text/README.md:欄位表、新增規則(抓前查 manifest、每秒 ≤10、User-Agent、fetchedBy 填票號或隊名)、校驗方法;⑤加 data/sec/10k_text/validate_manifest.py(唯讀):每行欄位齊全、檔案存在、sha256 對得上、accession 無重複、ticker+accession 對檔名;跑一次把結果(行數、對不上的清單)寫入 README 末段;不對的行只列出不修(修法在票上 raise);⑥若 KARST-161 同時在寫 manifest(它會抓新年報),寫入前 Read 一次最新版再改,只動自己那 202 行,commit 只帶 manifest、README、腳本。

## 驗收條件

- [x] manifest.jsonl 全部行同一套必填欄位(fetchedBy 取代 by;path 刪;primaryDoc 選填);改前備份存在 ~/.claude/backups/
- [x] data/sec/10k_text/README.md 有欄位表、新增規則、校驗方法;validate_manifest.py 唯讀,跑過一次,結果寫入 README
- [x] 校驗發現對不上的行(sha256/檔案缺/重複)只列不修,清單在 README 與票上 raise
- [x] commit 用 git commit --only -F <訊息檔> -- <自己的檔>;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;年報 .txt.gz 一個不改

## 結果

· 2026-09-03 02:00 manifest 欄位統一 + 全量校驗做完(data-gov-163)

**做了什麼**:①讀兩支抓取腳本(`experiments/2026-09-02-lazy-prices/fetch_sections.py`、
`experiments/2026-09-02-narrative-layers-v2/fetch_text.py`)確認每欄意義,查實 `sha256`
兩邊都是對「解壓後的純文本位元組」取,不是對 `.gz` 檔;②改 manifest 前先備份到
`C:\Users\Kaho\.claude\backups\10k_manifest.2026-09-03.bak`(4,017,001 bytes);
③把 202 行的 `by` 改名 `fetchedBy`、刪 `path`、保留 `primaryDoc`,其餘 9,712 行原樣寫回,
寫回前再讀一次核對前綴未變(期間沒有別隊追加);④寫 `data/sec/10k_text/README.md`
(欄位表、新增規則、校驗方法、校驗結果);⑤加唯讀 `data/sec/10k_text/validate_manifest.py`,
全量跑過一次。

**沒有做**:一個 `.txt.gz` 都沒有改;生產庫 `karst.sqlite` 只讀;21 行重複只列不修。

數字:

- 改寫 202 行,不動 9,712 行,總行數維持 9,914;抓取來源 KARST-153 9,666 / KARST-157 202 /
  KARST-159 46。
- 全量校驗(9,914 行逐一解壓核 sha256):JSON 讀不通 0、必填欄位缺漏 0、怪欄位 0、
  檔案缺失 0、**sha256 對不上 0**、`chars` 對不上 0、孤兒檔 0。
- **accession 重複 21 行**,全部是雙重股權代號:GOOGL/GOOG(CIK 0001652044,2 份)、
  UAA/UA(CIK 0001336917,19 份)。兩邊 sha256 相同,即同一份原料存了兩個副本,
  多佔約 1.9 MB。以 `ticker + accession` 為鍵則 9,914 個組合全部唯一。
- 生產庫 SHA256 首 16 位:`b168e9f45b578cf9`(維持不變)。

倉根 `data/` 被 `.gitignore` 擋住,所以 `manifest.jsonl` 與 `.txt.gz` 不入 git(它們是數據);
README 與校驗腳本是說明與工具,已用 `git add -f` 納入版本控制。

## 留言

### agent:data-gov-163 · 2026-09-03 01:44
欄位統一與全量校驗做完(data-gov-163)。誠實聲明:改了 manifest.jsonl 的 202 行欄位名、寫了 README 與唯讀校驗腳本、跑了一次全量校驗;沒有改任何年報 .txt.gz、沒有改生產庫、沒有修那 21 行重複。

改動:202 行的 by 改名 fetchedBy、刪 path、保留 primaryDoc;其餘 9,712 行原樣寫回,總行數維持 9,914。改前備份在 ~/.claude/backups/10k_manifest.2026-09-03.bak(4,017,001 bytes),寫回前再讀一次核對前綴未變,期間沒有別隊追加新行。

全量校驗(9,914 行逐一解壓核 sha256):JSON 讀不通 0、必填欄位缺漏 0、未登記的怪欄位 0、檔案缺失 0、sha256 對不上 0、chars 對不上 0、manifest 未登記的孤兒檔 0、accession 重複 21。

那 21 行重複不是壞資料,是雙重股權代號:GOOGL/GOOG(CIK 0001652044,2 份申報)、UAA/UA(CIK 0001336917,19 份申報)。同一份 10-K 存了兩個副本,內容 sha256 完全相同,多佔約 1.9 MB。以 ticker+accession 為鍵則 9,914 個組合全部唯一。這一格觸到單一副本原則,怎樣收要人裁,另開 raise。

落檔:data/sec/10k_text/README.md、data/sec/10k_text/validate_manifest.py(倉根 data/ 被 gitignore 擋住,這兩個是說明與工具不是數據,用 git add -f 納入版本控制);校驗明細 data/sec/10k_text/validate_report.json(不入 git)。commit 37ba4d9。生產庫 karst.sqlite SHA256 首 16 位 b168e9f45b578cf9,維持不變。

### agent:data-gov-163 · 2026-09-03 01:45
**問題**：年報全文快取有 21 份 10-K 存了兩個副本(雙重股權代號 GOOGL/GOOG、UAA/UA),要不要收成一份?

**前文後理**：全量校驗 9,914 行,sha256 全部對得上、沒有檔案缺失、沒有孤兒檔;唯一一格對不上的是 accession 重複 21 行。不是壞資料:GOOGL 與 GOOG 是同一家公司(CIK 0001652044)的兩個掛牌代號,UAA 與 UA 同理(CIK 0001336917)。同一份 10-K 因為兩個代號各抓了一次,檔名不同、內容 sha256 完全相同,多佔約 1.9 MB。現時檔名鍵是 ticker+accession,9,914 個組合全部唯一;但 D-134 的黃金原則是同一份原料只准一個副本,這一格是明文違反。順帶一提,KARST-165 那張票在拆股表也撞到同一類主鍵問題(代號不是穩定主鍵),兩張票宜一併裁。

**建議**：我押去重、主鍵改用 cik+accession。理由:代號不是穩定識別碼——它會重用、會改名、一家公司可以有多個代號,這三件事已經在這個倉分別咬過三次(本票的雙重股權、KARST-165 的代號重用、代號改名)。用 cik+accession 做主鍵,再另存一張 代號→CIK 的別名表,一次過解決三件事;1.9 MB 的省位是順帶,真正的收益是往後不會再有人以為代號可靠。但這是要改抓取腳本與讀取路徑的動作,不是本票範圍,所以停在這裡等裁。

**選項**：
- 甲（建議）：主鍵改 cik+accession:正本檔名改 <CIK>_<accession>.txt.gz,manifest 加一欄 tickers 記所有掛牌代號,刪去 21 個重複檔;另開一張票做搬檔與改腳本 —— 一次過解決雙重股權、代號重用、代號改名三件事;代價是要改兩支抓取腳本與所有讀取方,並做一次全庫改名
- 乙：保留 ticker+accession 做鍵,但雙重股權那 21 份只留主代號一份,次代號在 manifest 記一行指回主代號(不再另存檔) —— 改動小,馬上符合單一副本;但代號仍然是主鍵,將來代號重用或改名還是會再咬一次
- 丙：維持現狀,在 README 註明雙重股權會有兩個副本是刻意的 —— 零改動、讀取最方便(按代號直接找到檔);代價是明文放棄這一格的單一副本原則,1.9 MB 冗餘

**要睇邊份稿**：
- data/sec/10k_text/README.md

### agent:main-agent · 2026-09-03 07:48
**裁決**：雙重股權代號的 21 行重複保留不刪;manifest 主鍵定為 ticker+accession(accession 單獨不作主鍵);README 註明。本票關檔。

**出處**：主 agent 依 D-134(單一副本原則)與 D-072 在數據治理範圍內裁決(D-153);用戶未裁。
