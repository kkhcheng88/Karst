---
id: KARST-027
title: 行情數據接入與數據快照
type: task
createdAt: 2026-08-27
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-021, KARST-020]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-28
---

## 工作內容

回測自此跑在真實美股日線之上,而且引用的是一個有編號、凍得住的數據快照:同一個快照重算,結果一字不差。數據來源與儲存形態待 KARST-020 裁決,本票只做接入與快照——照該票裁出來的來源與形態接一次真實日線落庫、凍成有版本的快照、讓運行記錄引用得到它的編號。除權除息與停牌的處置須明文寫低(規格 10.4)。依 D-021 第 8 條追溯深度(lineage depth):公式因子追到批次=因子版本 × 數據快照 × 產生程序版本,可一字不差重算。

## 驗收條件

- [x] 同一個數據快照編號重算兩次,結果一字不差(D-021 第 8 條)
- [x] 除權除息與停牌各有一條明文處置,寫低在快照說明並在數據上驗得到(規格 10.4)
- [x] 快照有唯一編號,一次回測運行的記錄引用得到該編號(規格 7.4、D-021 第 8 條)
- [x] 接入的是真實美股日線而非合成數據,查得出來源與抓取時間

## 結果

· 2026-08-28 00:15 KARST-027-data 落成 `karst/data/` 一條管線,由抓取到凍結五步:抓(來源適配器)→ 定主日曆(SPY)→ 按日期把代號解析成實體編號 → 對齊主日曆(停牌處置)→ 原子寫入並經 `karst/store.py` 登記快照。沒有改動 `store.py` / `schema.py`,快照登記與實體代號映射全用現有 API;D-027 兩條護欄守住(不自開 sqlite 連線、無 sqlite 專有語法)。

**路徑**(全部新增):`karst/data/__init__.py`(對外 API)、`sources.py`(來源適配器:`YFinanceSource` 一律 `auto_adjust=True`;`StaticSource` 供離線重放)、`cik.py`(SEC `company_tickers.json` 取 CIK,取不到用佔位錨 `PLACEHOLDER-<代號>` 並在快照註記)、`universe.py`(起步宇宙名單)、`calendar.py`(主日曆與停牌對齊)、`manifest.py`(說明檔範本與兩條處置的正本文字)、`snapshots.py`(原子寫入、讀回、重算雜湊核對)、`pipeline.py`(端到端);測試 `tests/test_data_snapshot.py`(離線 11 項)、`tests/test_data_yfinance.py`(真實抓取 4 項);`pyproject.toml` 加 `yfinance` 與 `karst.data`;`.gitignore` 加 `data/` 與 `karst.sqlite`(數據可重抓,不入 git;說明檔範本住在 `karst/data/manifest.py`,單一定義無第二影像)。

**真實抓取**:快照編號 `2026-08-27-61e284eaa998`,來源 yfinance,抓取時間 2026-08-27T16:07:32+00:00,期間 2015-01-02 ~ 2026-08-26,主日曆 SPY 共 2,929 個交易日,12 個實體(SPY、QQQ 加十隻大型股)35,148 根日線,落 `data/snapshots/2026-08-27-61e284eaa998/`(prices/calendar/universe 三個 parquet + manifest.json + 說明.md),登記在 `karst.sqlite`。十隻公司全部取到真 SEC CIK,無一用佔位錨。

**測試**:`python -m pytest tests/test_data_snapshot.py tests/test_data_yfinance.py -q` → 15 passed(離線 11、真實抓取 4;離線環境下後者自動 skip)。全倉 `python -m pytest -q` → 39 passed、1 failed,唯一那條紅燈是 `tests/test_engine_rules.py`(KARST-023/024 引擎票在建中,與本票無關)。

**逐項驗收**
- 同一編號重算一字不差:`test_same_snapshot_id_reads_identical` 讀兩次比內容雜湊;`verify_snapshot()` 由目錄裡的檔案重算雜湊,對得上登記那個才過關。同一批內容重跑落回同一個編號、目錄原封不動(`test_same_content_falls_back_to_same_snapshot_id`);內容變一格即另一個編號、舊快照不動(`test_changed_content_gets_another_snapshot_id`)。
- 兩條處置:除權除息=只存已調整價、不自建事件表,停牌=缺日不填補、對齊主日曆時最多前值填補 3 個交易日、超過留 NaN,兩條寫在每個快照的 `說明.md` 與 `manifest.json`。數據上驗得到——每根日線有 `bar_status` 欄自報身分(actual / filled / missing):`test_halt_fills_three_days_then_leaves_empty` 證 3 日之後留空、`test_filled_bar_is_flat_with_zero_volume` 證填補那根 O=H=L=C、成交量 0;除息那條由 `test_prices_are_dividend_adjusted` 在真實 JNJ 數據上證已調整價低於未調整價。
- 唯一編號查得到:編號=快照日期+內容雜湊前 12 位,經 `store.register_snapshot` 落登記表,`store.get_snapshot()` 查得回來源、期間、路徑與**當時的宇宙名單**(`test_snapshot_is_registered_with_universe`)。運行記錄引用的就是這個字串;運行那一端的欄位屬 KARST-026。
- 真實日線:`test_real_snapshot_is_daily_bars_from_yfinance` 真連網抓 2024 年 1 月的 SPY/AAPL,核對交易日數與價格水位;來源名記在快照與登記表,抓取時間(帶時區)記在 `manifest.json`。抓取失敗一律拋 `DataFetchFailed`,不靜靜跳過(`test_missing_ticker_raises_instead_of_skipping`、`test_unknown_ticker_raises_instead_of_skipping`)。

## 留言

· 2026-08-28 00:20 fable-main KARST-020 已裁(D-026):yfinance 管價格與日曆、只存已調整價;defeatbeta 管基本面與逐字稿;parquet 存快照(每次拉數一個編號=日期+內容雜湊,舊快照不動)、sqlite 存登記;實體編號主鍵連代號歷史映射(入庫按日期解析代號);單一管線單一快取根、原子寫入;快照連同當時宇宙名單一併凍結,報告標明未含退市股;新來源以適配器接入。另 D-027 護欄:只用 sqlite/Postgres 通用 SQL,任何模組不得直接開 sqlite 連線,一律經 karst/store.py。本票可開工。

· 2026-08-28 00:25 KARST-027-data 實測發現一件影響「重抓去重」的事,留低待裁:**同一個窗口相隔十幾秒抓兩次,yfinance 回來的已調整價不是逐位相同**,故落成兩個不同的快照編號。已量度:差異只出現在派過息的股票(AMZN、TSLA 兩隻不派息的完全逐位相同),相對誤差上限約 1e-6(NVDA 2017 年那根 4.444352 對 4.444347),成交量與日期完全無差。成因是 yfinance 用累計派息因子回頭調整整條歷史,那段除數運算每次回來的尾數不同。後果:**每抓一次就是一個新快照,內容雜湊做去重實務上永不命中**,快取會隨抓取次數線性長大(本票那個快照 1.6MB,即每次約 1.6MB)。設計上沒有出錯——D-026 第 3 條本來就是「每次拉數一個新編號、舊的不動」,而 D-026 第 4 條也早已明令不同快照之間價格不可直接比較,故下游不受影響。要收窄的話有一個選項:凍結之前把價格統一四捨五入到固定有效位數(約 5 至 6 位可蓋過這級噪音),代價是極低價的已調整舊價會損失精度。這是改變數據本身的決定,不代裁,留給用戶。另:窗口收在未收市的當日會令最後一根日線持續變動,管線現時會在快照註記提醒,建議一律收在上一個已收市的交易日。
