# 年報全文快取(10-K full text)

倉內唯一一份 SEC 10-K 全文純文本副本。D-134 用戶定的黃金原則:同一份原料只准有一份副本,
有 manifest、有校驗、主鍵不會被代號重用污染。任何票要用 10-K 全文,一律讀這裡,不要另存一份。

- 位置:`C:\projects\Karst\data\sec\10k_text\`
- 檔案:`<TICKER>_<accession>.txt.gz`(gzip 壓縮的 UTF-8 純文本,由 EDGAR 的 primary
  document HTML 去掉 script/style 後抽出所有文字、空白壓成單一空格而成)
- 索引:`manifest.jsonl`(逐行一個 JSON,只准 append,不准整檔重寫)
- 校驗:`validate_manifest.py`(唯讀)
- 現況(2026-09-03 全量校驗):9,914 行、9,914 個 `.txt.gz`,約 1.19 GB

倉根的 `data/` 已被 `.gitignore` 擋住,所以 `.txt.gz` 與 `manifest.jsonl` 不入 git;
本 README 與校驗腳本是說明與工具,不是數據,已用 `git add -f` 納入版本控制。

---

## 一、manifest.jsonl 欄位表

每行一個 JSON 物件,欄位次序如下(2026-09-03 KARST-163 統一)。

| 欄位 | 必填 | 型別 | 意思 |
|---|---|---|---|
| `ticker` | 必填 | string | 代號,同時是檔名前半。同一份申報若有雙重股權代號(例 GOOGL/GOOG),會各出現一行 |
| `cik` | 必填 | string | SEC 的公司編號,10 位補零字串 |
| `accession` | 必填 | string | SEC 申報編號,18 位、沒有連字號 |
| `form` | 必填 | string | 表格類型,現時全部是 `10-K` |
| `filingDate` | 必填 | string | 申報日 `YYYY-MM-DD` |
| `reportDate` | 必填 | string | 財政年度結算日 `YYYY-MM-DD` |
| `url` | 必填 | string | EDGAR 上該份主文件的絕對網址 |
| `chars` | 必填 | int | 純文本字元數(解壓後 UTF-8 解碼後的長度) |
| `sha256` | 必填 | string | **解壓後純文本位元組**的 SHA256,不是 `.gz` 檔本身的雜湊 |
| `fetchedAt` | 必填 | string | 抓取時間,UTC ISO-8601,秒精度 |
| `fetchedBy` | 必填 | string | 是哪張票或哪一隊抓的,例 `KARST-153` |
| `primaryDoc` | 選填 | string | EDGAR 上的原始文件名,例 `goog-20181231.htm`。沒有的行可由 `url` 末段推得 |

### 這一版改了什麼(KARST-163)

KARST-157 寫入的 202 行本來用另一套欄位,已統一:

- `by` → 改名 `fetchedBy`(其餘 9,712 行本來就是這個名)
- `path` → 刪去。路徑由 `ticker` + `accession` 推得,存一份路徑只會在搬檔之後脫節
- `primaryDoc` → 保留,升為全庫的選填欄位

改動前的原檔備份在 `C:\Users\Kaho\.claude\backups\10k_manifest.2026-09-03.bak`。
年報 `.txt.gz` 一個都沒有改。

---

## 二、新增年報的規則

1. **抓之前先查 manifest。** 用 `ticker + accession` 查;查到而且檔案存在就直接讀快取,
   不要再打 EDGAR。這是單一副本原則落地的那一步。
2. **速率上限每秒 10 次**,並要帶 SEC 要求的 `User-Agent`(真實聯絡電郵)。超速會被封 IP。
3. **只 append,不整檔重寫。** 隨時可能有另一隊同時在寫同一個 manifest。真的要改既有行
   (例如本票這種欄位統一),先讀最新版、只改自己那些行、其餘行原樣寫回,寫回前再讀一次
   核對前綴沒有變過。
4. **`fetchedBy` 填票號或隊名**,不要留空、不要填人名。
5. **`sha256` 對解壓後的純文本取**,與兩支既有抓取腳本一致;寫入時順手填 `chars`。
6. **衍生物不放這裡。** 切節後的 Item 1、Item 7 之類放回各自的票目錄,靠 `accession`
   指回這裡的正本。

現有的兩支抓取腳本可作範本:

- `experiments/2026-09-02-lazy-prices/fetch_sections.py`(KARST-153,9,666 行)
- `experiments/2026-09-02-narrative-layers-v2/fetch_text.py`(KARST-157,202 行)

---

## 三、校驗方法

```
set PYTHONUTF8=1
cd C:\projects\Karst\data\sec\10k_text
python validate_manifest.py              # 全量,要解壓全部檔,約 4 分鐘
python validate_manifest.py --fast       # 只查欄位、檔案存在、重複,幾秒
python validate_manifest.py --sample 300 # 抽 300 行核 sha256
```

腳本是唯讀的:不會改 `manifest.jsonl`,不會改任何 `.txt.gz`。它查七件事——JSON 讀得通、
必填欄位齊全、沒有未登記的怪欄位、`<TICKER>_<accession>.txt.gz` 存在、`sha256` 對得上、
`chars` 對得上、`accession` 沒有重複、目錄裡沒有 manifest 未登記的孤兒檔。
結果寫入同目錄 `validate_report.json`(這是輸出,不是正本)。
發現對不上的行只會列出來,不會自動修——修法要人裁。

---

## 四、2026-09-03 全量校驗結果(KARST-163)

| 項目 | 數 |
|---|---|
| manifest 行數 | 9,914 |
| 目錄內 `.txt.gz` | 9,914 |
| JSON 讀不通的行 | 0 |
| 必填欄位缺漏 | 0 |
| 未登記的怪欄位 | 0 |
| 檔案缺失 | 0 |
| **sha256 對不上**(全部 9,914 行逐一解壓核對) | **0** |
| `chars` 對不上 | 0 |
| manifest 未登記的孤兒檔 | 0 |
| **accession 重複** | **21** |

抓取來源分佈:KARST-153 共 9,666 行、KARST-157 共 202 行、KARST-159 共 46 行。

### 那 21 行重複是什麼

不是壞資料,是**雙重股權代號**:同一家公司、同一個 CIK、同一份 10-K,兩個掛牌代號各存了一份。

- `GOOGL` / `GOOG`,CIK 0001652044,2 份申報
- `UAA` / `UA`,CIK 0001336917,19 份申報

兩邊的 `sha256` 完全相同,即內容一模一樣,只是檔名不同,多佔約 1.9 MB。
以 `ticker + accession` 為鍵則**沒有任何重複**(9,914 個組合全部唯一)。

這一格觸到單一副本原則:同一份原料現時有兩個副本。怎樣收,要人裁——是改用
`cik + accession` 做主鍵、正本存一份、代號做別名表,還是接受雙代號各存一份換取讀取方便。
已在 KARST-163 票上 `raise`,本票不自行修改。
