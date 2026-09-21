# data/ —— 資料層地圖(2026-09-07 建;2026-09-14 重整後只餘原料層)

倉根 `data/` 整個目錄由 `.gitignore` 擋走(只有說明檔與清單入 git),避免把大量原料放入 git;這不代表每個舊版本都能原樣重抓。已用於發布判斷的輸入快照、清單與解析版本須另行備份,不能以供應商今日可下載取代。資料層正本是 `strategy/資料來源.md`(含倉外接口與時點規則);本檔只管 `data/` 目錄。這一頁答三條問題:每一層由哪裡來、掉了要花多少功夫重建、有沒有入 git。

分兩層看:**原料**是來源在某一時點提供的內容,其中可有陳述、預測及錯誤,不等於已核事實;**衍生**是本倉從指定原料版本產生的結果。重建還需相同解析／計算版本;LLM 生成結果不保證重新執行會逐字相同。

## 一、原料層

| 目錄 | 是什麼 | 來源 | 大小 | 重建成本 | 入 git |
|---|---|---|---|---|---|
| `sec/` | 美國證監會申報快取(D-134):`submissions/` 申報索引、`companyfacts/` 財務標籤(5,335 家)、`10k_text/` 年報全文、`cik-lookup-data.txt` 與 `company_tickers.json` 代號對照 | EDGAR,免費 | 3.0 GB | 高:全宇宙重抓要一至兩日,受 EDGAR 速率限制;特定 accession 的文件可重取,但 companyfacts 聚合回傳與抽取器可改版;已採用的內容／解析版本須保留,重抓後核指紋 | 只有各層的 `README.md`、`manifest.csv`、`completeness.csv` 入 git |
| `prices/daily/` | 美股日線 | 供應商 API | 442 MB | 中:跑一次取數腳本即重生;歷史價格會因拆股與供應商修訂而有微差 | 只有 `README.md`、`manifest.csv`、`failed.csv` |
| `universe/` | 宇宙定義:`entities.parquet` 實體主檔、`ticker_periods.parquet` 代號分段、`universe_smallcap_v0/v1.csv` 小型股宇宙、`price_snapshot_*.csv` | 由 `sec/` 與 `prices/` 建成,但一經定版即當原料用(策略要按同一份宇宙比較) | 2.2 MB | 低:有腳本可重建,但**重建等於換宇宙**,不可在同一條實驗線中途做 | `RULES.md` 與 `universe_smallcap_v1.manifest.json` 入 git |

## 二、衍生層

2026-09-14 起沒有衍生層。工作台的取證包、索引與研究卡按 `strategy/specs/投研工作台-v1-規格書.md`(KARST-238)另定位置。

## 三、已刪除的

- **2026-09-14(D-177 根基重整,用戶原話「I think all can remove」)**:`runs/`(437 MB)、`snapshots/`(218 MB)、`panel/quarterly_v3.parquet`(23 MB)、`macro_snapshots/`(584 KB)、`vintage/`(板塊倍數與基金份額存檔 2 MB,不可再生,存檔在 tag `pre-reset-2026-09-13`)。引擎已刪,前四者無法亦無需重跑。

- `data/factors`(Alpha158 因子線的衍生數據,5.6 GB,六個快照目錄)**2026-09-07 用戶裁定刪除**(原話「因子表 5.7 GB 刪或留。 Delete」),沒有備份。該線已死(2026-08-29 全美股實測無單條訊號成立,用戶轉向 OSAP 學術因子庫),留着只佔位。**可由 `prices/` 日線重算**——因子全部是價量衍生,原料仍在。

**2026-09-07 併入**:`experiments/2026-09-02-fundamentals-panel/data/secfacts/` 曾另存 698 家的 companyfacts 原始下載,其中 99 家快取沒有。刪實驗目錄之前已壓成 `.json.gz` 併入 `sec/companyfacts/`,`manifest.csv` 補 99 行,`fetchedBy` 欄標 `merged-from-experiment-2026-09-02`。

## 四、不在 data/ 裡的資料源

- **DefeatBeta**(D-025/D-026 已收為來源,套件 `defeatbeta-api` v0.0.60 已裝):**沒有本機資料庫檔**。它是 HuggingFace 上的公開資料集 `defeatbeta/yahoo-finance-data`,由 DuckDB 的 httpfs 直接查遠端 parquet,本機只有一個 DuckDB 擴充與快取目錄 `C:\Users\Kaho\.duckdb`(約 55 MB,可刪可重建)。所以它既不在倉內、也不在 `data/` 下;可直接呼叫套件作查詢;凡用於發布卡的逐字稿與數據必保存實際採用內容的版本及清單,不把 DuckDB 快取當可追溯的正式證據快照。提供業績電話會逐字稿與逐季業績日曆。
- **富途 MCP**(用戶 2026-09-13 授權)與 **Longbridge**(plugin,D-165):現時報價、共識、評級、內部人、沽空、期權、業績公布時間等;清單見 `strategy/資料來源.md` §三。
- ~~生產庫 `karst.sqlite`~~ 與 ~~倍數版本存檔 `vintage/`~~:已於 2026-09-13/14 隨重整刪除。

## 五、工作台取數的現行口徑(2026-09-14 審查補充)

日常用截至分析時可取得的最新適用修正資料;②歷史考試的首報值只用於原協議,不套到日常。未知公開時刻不由檔名或未來／過去日期猜成精確時間;截止前已發出的未來指引可以入包。日週月價量與 200 日 SMA 使用一致交易日曆、價格調整與收市確認。詳細規則及共識 C4 的可比條件以 `strategy/資料來源.md` §四為準。

## 2026-09-21 日常新聞發現

公司證據倉新增 Yahoo Finance／Google News RSS 快照與逐源覆蓋回執；只作發現線索，原文仍須另讀。refresh_daily 預設價格＋新聞，沿用未受影響的經營模型；新聞失敗不當無變。CIK 格式歸一及 gzip 無損封裝差異不再當作新經營事件，原始快照仍保留。詳見 strategy/資料來源.md。
