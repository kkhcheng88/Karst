# companyfacts 單一快取

倉內唯一一份 SEC XBRL `companyfacts` 副本。D-134 的黃金原則:同一份原料只准有一份副本、
有 manifest、有校驗、主鍵不會被代號重用污染。任何票要用 companyfacts,一律讀這裡。

- 建立票:KARST-172(2026-09-03)
- 位置:`C:\projects\Karst\data\sec\companyfacts\`
- 檔案:`CIK##########.json.gz`(gzip 壓縮的原始 JSON,一家一檔;**存的是位元原文,
  不是解析後的東西**)
- 索引:`manifest.csv`
- 主鍵:`cik`(十位補零)。這與 `data/universe/entities.parquet` 的 `entity_id` 同一個東西。
- 現況(2026-09-03):**5,257 個實體、5,236 個檔、gzip 後 732 MB、原始 JSON 10.4 GB**
- 倉根 `data/` 已被 `.gitignore` 擋住,`.json.gz` 不入 git;本 README 與 `manifest.csv`
  用 `git add -f` 納入版本控制。

---

## 一、manifest.csv 欄位

| 欄 | 意思 |
|---|---|
| `cik` | 證監會申報人編號,十位補零 |
| `entity_id` | 同上(宇宙表的主鍵名,刻意兩個名都留,免得讀的人要記住它們是同一樣東西) |
| `fetchedAt` | 抓取時間,UTC ISO-8601,秒精度 |
| `fetchedBy` | 票號 |
| `bytes` | **解壓後**原始 JSON 的位元組數 |
| `sha256` | **解壓後**原始 JSON 的 SHA256(不是 `.gz` 檔本身的雜湊) |
| `status` | `ok` / `empty` / `fail`,定義見下 |
| `http_code` | 200 或 404 |

### status

| 值 | 意思 | 數 |
|---|---|---|
| `ok` | 拿到 JSON,而且 `facts` 之下有 `dei` 以外的區塊 | 5,226 |
| `empty` | 拿到 JSON,但 `facts` 空白或只有 `dei` | 10 |
| `fail` | 拿不到(全部是 HTTP 404,即證監會沒有這個 CIK 的 companyfacts) | 21 |

**404 不重試**——它是永久答案(「這個 CIK 沒有這份文件」),不是暫時失敗。

---

## 二、新增的規則

1. **抓之前先查 manifest。** 用 `cik` 查;`status` 是 `ok` 或 `empty` 就直接讀快取,
   不要再打 EDGAR。這是單一副本原則落地的那一步。
2. **速率上限每秒 10 次**(本快取實跑用 8 次),並要帶證監會要求的 `User-Agent`
   (真實聯絡電郵)。**403 一出現就把全域間隔拉長並退讓重試,不停跑。**
   本次抓取 5,257 個請求、10.3 分鐘、**零次 403**。
3. **`fetchedBy` 填票號**,不要留空、不要填人名。
4. **`sha256` 對解壓後的原文取**,與 `data/sec/10k_text/` 那一份的做法一致。
5. **衍生物不放這裡。** 面板、切片、特徵表放各自的落點(面板在 `data/panel/`),
   靠 `cik` 指回這裡的正本。

抓取腳本:`experiments/2026-09-03-panel-v3/fetch_companyfacts.py`
(節流器 `sec_client.py` 沿用 KARST-146 那一份)。

---

## 三、與倉內其餘 companyfacts 副本的關係

本快取建立之前,倉內已有兩處實驗目錄各存一份 companyfacts:

| 位置 | 家數 | 判 |
|---|---|---|
| `experiments/2026-09-02-fundamentals-panel/data/secfacts/` | 698 | **已被本快取取代**(本快取是它的超集,而且是同一個端點) |
| `experiments/2026-09-03-tenbagger-safety/`(讀上面那份,無自己副本) | — | 不受影響 |

**舊副本沒有刪。** 刪檔屬另一張票的事(參照 KARST-174 清申報索引副本那一張的做法)。
新票要用 companyfacts 請讀本快取。

---

## 四、必須知道的兩件事

1. **companyfacts 只出標準分類體系。** KARST-146 掃過 698 份、本票掃過 5,236 份,
   出現過的只有 `dei` / `us-gaap` / `srt` / `ffd` / `invest` / `ecd` / `rxp` / `ifrs-full`,
   一個公司自訂命名空間都沒有。自訂標籤住在每份申報自己的 XBRL 實例檔,**不在這個端點**。
   所以任何「有幾多公司用自訂標籤」的統計在這份原料上是**量不出**,不是零。
2. **外國申報人的帳目在,但用本國貨幣。** 241 家交 20-F / 40-F 的公司有齊
   `Assets` / `Liabilities` / `CashAndCashEquivalents` / `Equity`(IFRS 標籤),
   但單位是 EUR / CAD / GBP / JPY 一類。**只收 USD 的讀法會把它們整批當成「沒有帳目」**
   ——那是讀法的問題,不是它們沒有數。面板 v3 為此逐格記低 `<欄>_unit`。
