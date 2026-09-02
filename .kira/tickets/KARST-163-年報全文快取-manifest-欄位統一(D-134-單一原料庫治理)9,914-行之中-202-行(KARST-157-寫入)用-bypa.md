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
---

## 工作內容

背景:D-134 用戶定「只保留單一副本,數據治理是黃金原則」;年報全文單一快取在 C:\projects\Karst\data\sec\10k_text\(<TICKER>_<accession>.txt.gz + manifest.jsonl)。兩張票先後寫入,欄位不一致:KARST-153 的 9,712 行是 ticker, cik, accession, form, filingDate, reportDate, url, chars, sha256, fetchedAt, fetchedBy;KARST-157 的 202 行是 ticker, cik, accession, form, filingDate, reportDate, url, chars, sha256, fetchedAt, by, path, primaryDoc。做法:①先讀兩張票的抓取腳本(experiments/2026-09-02-lazy-prices/ 與 experiments/2026-09-02-narrative-layers-v2/)確認每欄意義;②定一套欄位:必填 ticker, cik, accession, form, filingDate, reportDate, url, chars, sha256, fetchedAt, fetchedBy;選填 primaryDoc(原始文件名,有就保留);path 一欄刪去(路徑由 ticker+accession 推得,存路徑會與搬檔脫節);③把 202 行的 by 改名 fetchedBy、刪 path、保留 primaryDoc,其餘行不動;改 manifest 前先備份到 ~/.claude/backups/10k_manifest.2026-09-03.bak;④寫 data/sec/10k_text/README.md:欄位表、新增規則(抓前查 manifest、每秒 ≤10、User-Agent、fetchedBy 填票號或隊名)、校驗方法;⑤加 data/sec/10k_text/validate_manifest.py(唯讀):每行欄位齊全、檔案存在、sha256 對得上、accession 無重複、ticker+accession 對檔名;跑一次把結果(行數、對不上的清單)寫入 README 末段;不對的行只列出不修(修法在票上 raise);⑥若 KARST-161 同時在寫 manifest(它會抓新年報),寫入前 Read 一次最新版再改,只動自己那 202 行,commit 只帶 manifest、README、腳本。

## 驗收條件

- [ ] manifest.jsonl 全部行同一套必填欄位(fetchedBy 取代 by;path 刪;primaryDoc 選填);改前備份存在 ~/.claude/backups/
- [ ] data/sec/10k_text/README.md 有欄位表、新增規則、校驗方法;validate_manifest.py 唯讀,跑過一次,結果寫入 README
- [ ] 校驗發現對不上的行(sha256/檔案缺/重複)只列不修,清單在 README 與票上 raise
- [ ] commit 用 git commit --only -F <訊息檔> -- <自己的檔>;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;年報 .txt.gz 一個不改

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
