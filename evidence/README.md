# evidence/ —— 證據層(工作台 v1;2026-09-14 建,KARST-240)

只准追加,內容定址;除本 README 與 `manifest.jsonl` 外不入 git。每份證據一個檔,每檔在 `manifest.jsonl` 一行。

## 目錄

```
evidence/
  manifest.jsonl                 每份證據一行(欄位見下)
  sec/<CIK>/<accession>.<form>.txt     申報純文本(8-K 的 EX-99.1、10-Q、10-K;HTML 去標籤)
  transcripts/<CIK>/<call_date>.json   DefeatBeta 逐字稿(含 prepared remarks 與 Q&A 段落、report_date、取得時間)
  financials/<CIK>/<source>-<UTC>.json DefeatBeta 或券商回傳的報表、收入拆分、股數
  broker/<TICKER>/<source>-<tool>-<UTC>.json   富途 / Longbridge 每次呼叫的原始回傳
  prices/<TICKER>-daily-<UTC>.csv      日線(來源欄標 local 或 defeatbeta 或 futu)
  docs/<UTC>-<slug>.<ext>              用戶由 inbox 放進來的檔案(解析後文字另存 .txt)
  packets/<TICKER>-<UTC>.json          一次分析的取證包索引:按類別列 ev_id、期間、截至時間
```

## manifest.jsonl 欄位

`ev_id`(`ev:<source>:<sha256 前 12 位>`)、`source`(edgar / defeatbeta / futu / longbridge / local-prices / user)、`kind`(10-K / 10-Q / 8-K-EX99.1 / transcript / consensus / …)、`cik`、`ticker`、`accession`(申報才有)、`published_at`(來源公開時間,含時區;未知留空並在 `published_at_basis` 寫依據或「未知」)、`fetched_at`(我們取得,UTC)、`period_start` / `period_end`(所述期間)、`data_as_of`(資料本身截至)、`sha256`、`bytes`、`path`、`tool`(MCP 工具名或函式名)、`note`。

## 規矩

- 同一份內容只存一次(sha256 相同即跳過,manifest 記一次);修訂版另存並在 `note` 指向前一版 `ev_id`。
- 取得時間與公開時間分開;推斷的公開時間標「推斷」。
- 抓 EDGAR 前先查 `data/sec/10k_text/` 與 `data/sec/submissions/`(D-134);抓到的 8-K 與 10-Q 純文本存這裡,不另建第二份。
- 不入 git 的原因:體積與版權;備份由用戶隨機器備份。
