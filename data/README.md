# data/ —— 資料層地圖(2026-09-07)

倉根 `data/` 整個目錄由 `.gitignore` 擋走(只有八份說明檔與清單入 git),因為裡面全部是**可以重抓或重算**的東西。這一頁答三條問題:每一層由哪裡來、掉了要花多少功夫重建、有沒有入 git。

分兩層看:**原料**是外面抓回來的、我們改不了的事實;**衍生**是原料經本倉的程式算出來的東西,原料在就重得出。

## 一、原料層

| 目錄 | 是什麼 | 來源 | 大小 | 重建成本 | 入 git |
|---|---|---|---|---|---|
| `sec/` | 美國證監會申報快取(D-134):`submissions/` 申報索引、`companyfacts/` 財務標籤(5,335 家)、`10k_text/` 年報全文、`cik-lookup-data.txt` 與 `company_tickers.json` 代號對照 | EDGAR,免費 | 3.0 GB | 高:全宇宙重抓要一至兩日,受 EDGAR 速率限制;內容按申報日不變,重抓即得同一份 | 只有各層的 `README.md`、`manifest.csv`、`completeness.csv` 入 git |
| `prices/daily/` | 美股日線 | 供應商 API | 442 MB | 中:跑一次取數腳本即重生;歷史價格會因拆股與供應商修訂而有微差 | 只有 `README.md`、`manifest.csv`、`failed.csv` |
| `universe/` | 宇宙定義:`entities.parquet` 實體主檔、`ticker_periods.parquet` 代號分段、`universe_smallcap_v0/v1.csv` 小型股宇宙、`price_snapshot_*.csv` | 由 `sec/` 與 `prices/` 建成,但一經定版即當原料用(策略要按同一份宇宙比較) | 2.2 MB | 低:有腳本可重建,但**重建等於換宇宙**,不可在同一條實驗線中途做 | `RULES.md` 與 `universe_smallcap_v1.manifest.json` 入 git |
| `macro_snapshots/` | 宏觀序列快照(按日期加雜湊命名) | 外部宏觀資料源 | 584 KB | 低 | 否 |

## 二、衍生層

| 目錄 | 是什麼 | 由什麼算出 | 大小 | 重建成本 | 入 git |
|---|---|---|---|---|---|
| `panel/quarterly_v3.parquet` | 季度基本面面板 v3(帳目面板,KARST-146/D-146 一線) | `sec/companyfacts/` + `universe/` | 23 MB | 低至中:一支腳本重跑 | 否 |
| `snapshots/` | 回測用的價格與因子快照(按日期加雜湊命名) | `prices/` + `universe/` | 218 MB | 低,但**編號不保證重現**(A-007):重抓會得到新的快照編號,舊運行的編號從此對不上 | 否 |
| `runs/` | 歷史回測運行結果(每個 `run-<雜湊>` 一個目錄) | 引擎跑 `snapshots/` 而成 | 437 MB | 名義上可重跑,但要配同一份快照;快照重抓後**成績重現不了原編號** | 否 |

## 三、已刪除的

- `data/factors`(Alpha158 因子線的衍生數據,5.6 GB,六個快照目錄)**2026-09-07 用戶裁定刪除**(原話「因子表 5.7 GB 刪或留。 Delete」),沒有備份。該線已死(2026-08-29 全美股實測無單條訊號成立,用戶轉向 OSAP 學術因子庫),留着只佔位。**可由 `prices/` 日線重算**——因子全部是價量衍生,原料仍在。

**2026-09-07 併入**:`experiments/2026-09-02-fundamentals-panel/data/secfacts/` 曾另存 698 家的 companyfacts 原始下載,其中 99 家快取沒有。刪實驗目錄之前已壓成 `.json.gz` 併入 `sec/companyfacts/`,`manifest.csv` 補 99 行,`fetchedBy` 欄標 `merged-from-experiment-2026-09-02`。

## 四、不在 data/ 裡的資料源

- **DefeatBeta**(D-025/D-026 已收為來源,套件 `defeatbeta-api` v0.0.60 已裝):**沒有本機資料庫檔**。它是 HuggingFace 上的公開資料集 `defeatbeta/yahoo-finance-data`,由 DuckDB 的 httpfs 直接查遠端 parquet,本機只有一個 DuckDB 擴充與快取目錄 `C:\Users\Kaho\.duckdb`(約 55 MB,可刪可重建)。所以它既不在倉內、也不在 `data/` 下;要用就直接呼叫套件,不用先落檔。提供業績電話會逐字稿與逐季業績日曆。
- **生產庫** `karst.sqlite`(倉根,40 MB)與其簽章鑰匙 `karst.sqlite.gateway-key`:兩者都不入 git(D-020 第 4 條:鑰匙刻意住在庫檔以外)。
- **倍數版本存檔** `vintage/`:存檔正本 `readings.csv` **要入 git**(不可再生,今日不抄以後補不回);原始頁面 `vintage/*/raw/` 擋走。
