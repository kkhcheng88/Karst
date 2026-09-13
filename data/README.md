# data/ —— 資料層地圖(2026-09-07 建;2026-09-14 重整後只餘原料層)

倉根 `data/` 整個目錄由 `.gitignore` 擋走(只有說明檔與清單入 git),因為裡面全部是**可以重抓或重算**的東西。資料層正本是 `strategy/資料來源.md`(含倉外接口與時點規則);本檔只管 `data/` 目錄。這一頁答三條問題:每一層由哪裡來、掉了要花多少功夫重建、有沒有入 git。

分兩層看:**原料**是外面抓回來的、我們改不了的事實;**衍生**是原料經本倉的程式算出來的東西,原料在就重得出。

## 一、原料層

| 目錄 | 是什麼 | 來源 | 大小 | 重建成本 | 入 git |
|---|---|---|---|---|---|
| `sec/` | 美國證監會申報快取(D-134):`submissions/` 申報索引、`companyfacts/` 財務標籤(5,335 家)、`10k_text/` 年報全文、`cik-lookup-data.txt` 與 `company_tickers.json` 代號對照 | EDGAR,免費 | 3.0 GB | 高:全宇宙重抓要一至兩日,受 EDGAR 速率限制;內容按申報日不變,重抓即得同一份 | 只有各層的 `README.md`、`manifest.csv`、`completeness.csv` 入 git |
| `prices/daily/` | 美股日線 | 供應商 API | 442 MB | 中:跑一次取數腳本即重生;歷史價格會因拆股與供應商修訂而有微差 | 只有 `README.md`、`manifest.csv`、`failed.csv` |
| `universe/` | 宇宙定義:`entities.parquet` 實體主檔、`ticker_periods.parquet` 代號分段、`universe_smallcap_v0/v1.csv` 小型股宇宙、`price_snapshot_*.csv` | 由 `sec/` 與 `prices/` 建成,但一經定版即當原料用(策略要按同一份宇宙比較) | 2.2 MB | 低:有腳本可重建,但**重建等於換宇宙**,不可在同一條實驗線中途做 | `RULES.md` 與 `universe_smallcap_v1.manifest.json` 入 git |

## 二、衍生層

2026-09-14 起沒有衍生層。工作台的取證包、索引與研究卡按 `strategy/specs/投研工作台-v1-規格書.md`(KARST-238)另定位置。

## 三、已刪除的

- **2026-09-14(D-177 根基重整,用戶原話「I think all can remove」)**:`runs/`(437 MB)、`snapshots/`(218 MB)、`panel/quarterly_v3.parquet`(23 MB)、`macro_snapshots/`(584 KB)、`vintage/`(板塊倍數與基金份額存檔 2 MB,不可再生,存檔在 tag `pre-reset-2026-09-13`)。引擎已刪,前四者無法亦無需重跑。

- `data/factors`(Alpha158 因子線的衍生數據,5.6 GB,六個快照目錄)**2026-09-07 用戶裁定刪除**(原話「因子表 5.7 GB 刪或留。 Delete」),沒有備份。該線已死(2026-08-29 全美股實測無單條訊號成立,用戶轉向 OSAP 學術因子庫),留着只佔位。**可由 `prices/` 日線重算**——因子全部是價量衍生,原料仍在。

**2026-09-07 併入**:`experiments/2026-09-02-fundamentals-panel/data/secfacts/` 曾另存 698 家的 companyfacts 原始下載,其中 99 家快取沒有。刪實驗目錄之前已壓成 `.json.gz` 併入 `sec/companyfacts/`,`manifest.csv` 補 99 行,`fetchedBy` 欄標 `merged-from-experiment-2026-09-02`。

## 四、不在 data/ 裡的資料源

- **DefeatBeta**(D-025/D-026 已收為來源,套件 `defeatbeta-api` v0.0.60 已裝):**沒有本機資料庫檔**。它是 HuggingFace 上的公開資料集 `defeatbeta/yahoo-finance-data`,由 DuckDB 的 httpfs 直接查遠端 parquet,本機只有一個 DuckDB 擴充與快取目錄 `C:\Users\Kaho\.duckdb`(約 55 MB,可刪可重建)。所以它既不在倉內、也不在 `data/` 下;要用就直接呼叫套件,不用先落檔。提供業績電話會逐字稿與逐季業績日曆。
- **富途 MCP**(用戶 2026-09-13 授權)與 **Longbridge**(plugin,D-165):現時報價、共識、評級、內部人、沽空、期權、業績公布時間等;清單見 `strategy/資料來源.md` §三。
- ~~生產庫 `karst.sqlite`~~ 與 ~~倍數版本存檔 `vintage/`~~:已於 2026-09-13/14 隨重整刪除。
