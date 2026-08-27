# KarstETF 舊倉數據層事實盤點(2026-08-27)

> 唯讀盤點,只記倉內代碼與文件所載事實;未連網核實 defeatbeta-api 官方文檔。舊倉位置:`C:/projects/Investment/KarstETF`(2026-08-15 停案)。供 KARST-020 數據架構討論用。

## 1. defeatbeta 用法
- 套件 `defeatbeta-api` 0.0.60,只裝在 `bt/corpus_pilot/.venv`(主 venv `bt/.venv` 沒裝)。
- 只用了兩類數據:業績電話會逐字稿(`t.earning_call_transcripts()`)與季度/年度損益表(`quarterly_income_statement()` / `annual_income_statement()`)。沒有用它的分析師預測表格,沒有用它的價格數據。
- duckdb 是 defeatbeta-api 套件內部依賴,倉方代碼不直接呼叫。
- 逐字稿快取分散在四個目錄(`bt/{exp7_v2,exp6_basket,exp4_semiannual,corpus_pilot}/cache/raw/`),基本面在 `cache/fundamentals_{q,a}/`;抓取有「復用鏈」設計,逐層原位讀取不複製。規模約 6,530 份逐字稿、98 個現役代表(`docs/karst-handover.md`)。
- 主要調用檔:`bt/exp7_v2/fetch_data.py`(含四層復用鏈完整實作)、`bt/exp7_v2/config.py`。
- 基本面 `filing_date_approx` 是估算值(季度+75 天、年度+120 天),不是真申報日;倉方文件自認是踩過的坑。

## 2. yfinance 用法
- 日線,一律 `auto_adjust=True`(近似總回報),欄位 `Close/High/Low/Open/Volume`,`threads=False, actions=False`。
- 主模組 `bt/data.py`(53 隻主題 ETF);exp6/exp7/exp9/sa_tracker 各有自己的個股價格抓取腳本。
- 快取為 parquet,增量更新(重抓最後 5 天吸收後續修訂)。失敗時 fallback 打 `stockanalysis.com` 非官方 API(只有 Close,無 OHLV)。
- 以 SPY 交易日作主日曆,`align_to_calendar(ffill_limit=3)` 對齊。

## 3. 退市、除權除息、停牌
- 除權除息完全依賴 yfinance `auto_adjust=True`;沒有自建 corporate-action 表(`universe/corporate_actions.csv` 只是未落地草案)。
- 停牌靠 3 天 ffill 上限,超過留 NaN 不捏造。
- 退市沒有自動偵測:PARA/VRNA 兩隻除牌是人手發現「停了更新」才確認。
- 最大事故是**代號回收**:`GOLD` 被數據源長期指向 A-Mark(巴里克已改代號 `B`),整條 2018–2026 價格史用錯,直到判官讀稿才發現(KETF-034);修復後加 `test_ticker_not_recycled` / `test_no_foreign_transcripts` 兩個守門測試。另有 46 份外來公司逐字稿誤歸檔已清理。
- `docs/karst-handover.md` 明文列為新引擎硬性需求:「實體主鍵不准用交易代號,要 entity id + 代號歷史映射」。

## 4. 結構與痛點
- 數據抓取邏輯分散在 5 套獨立管線,價格快取有 5 條互相獨立目錄(`bt/engine_v18/cache_paths.py` 的 `PRICE_CACHE_DIRS`);正式引擎讀取「先撞先贏、同代號多處命中不報錯」。
- KETF-027:共用快取無鎖,同一個數重跑不同答案(已關但範圍收窄;exp7/6/4 各自快取未套用原子寫入);同票審計揪出 B/QQQ/SPY 多處命中且收市價不一致。
- KETF-017:`signals_v3` 快取 stale,同步機制未做,重建腳本依賴已刪除模組(票未關)。
- KETF-034:代號回收+逐字稿歸錯(已關)。
- 代碼內幾乎沒有 TODO/FIXME;痛點最完整清單在 `docs/karst-handover.md` 第四節「事故→工程需求」15 條表。
- `bt/data` 目錄現存寫入者缺失(git 未追蹤的歷史遺留),要重建暫無現成腳本。

## 引用檔案
`bt/data.py`、`bt/exp7_v2/fetch_data.py`、`bt/exp7_v2/config.py`、`research/inbox/data_inventory.md`、`docs/SYSTEM_LAYOUT.md`、`docs/karst-handover.md`、`.kira/tickets/KETF-027*.md`、`.kira/tickets/KETF-017*.md`、`.kira/tickets/KETF-034*.md`。
