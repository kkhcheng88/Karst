---
id: KARST-032
title: 本機網頁殼 v0:讀真實運行畫淨值圖與蠟燭圖
type: task
createdAt: 2026-08-27
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-026, KARST-030]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-28
---

## 工作內容

瀏覽器開一個本機網址,自此睇得到真實回測結果:淨值圖與蠟燭圖畫得出,進出場點落在蠟燭圖對應的日子上——回測結果要在蠟燭圖上看得到出入場點,體驗對標 TradingView/Futu(D-002 第 2 條)。範圍是網頁殼與一層薄 REST:數據來自一次真實運行,不是假數據;圖表用 lightweight-charts(D-019),樣式取 design-system.md 的 token。這是把 KARST-015 原型第十版那個已核准基線接上真數據的第一步,畫面決定不在本票重開(D-023 第 1 條)。

## 驗收條件

- [x] 瀏覽器開本機網址睇得到淨值圖與蠟燭圖,進出場標記落在對應日期的蠟燭上(D-002 第 2 條、D-020 第 2 條)
- [x] 圖上數據經薄 REST 層來自一次真實回測運行,頁面內查不到寫死的假數據(規格 8.7)
- [x] 圖表用 lightweight-charts 畫,顏色與字級取 design-system.md 的 token,無自定色值(D-019)
- [x] 換一次運行,整頁的圖跟住換,該次運行的編號在頁面上顯示得到(規格 7.4、詞彙表 view run)

## 結果

· 2026-08-28 01:30

本機網頁殼 v0 已經開得到,讀的是庫內真實運行。

**啟動命令**:專案根執行 `python -m karst.web`(加 `--open` 可順手開瀏覽器)。
**網址**:`http://127.0.0.1:8765/`;指名某一次運行用 `http://127.0.0.1:8765/?run=<運行編號>`。
**所用運行編號**:主要對住 `run-728a01087531258f`(趨勢波段,快照 2026-08-27-61e284eaa998,2929 個交易日、487 張成交、242 筆已平倉交易);換運行那條驗收另用 `run-f44f765ef0befd61`(因子混合(ETF 版),快照 2026-08-27-91a5d51339d9)。
**截圖**:`karst/web/screenshots/` 三幅,全部由真實 Chrome 在 1440×700 拍下——`01-淨值圖-成交浮層.png`、`02-蠟燭圖-出入場標記.png`、`03-換運行-整頁跟住換.png`。

**選型**(票上要求寫明):
- 後端用 **Python 標準庫 `http.server`**(`ThreadingHTTPServer`),不用 FastAPI/uvicorn。這一層只有四個 GET 端點,標準庫夠用;而且不必為一個本機檢視器把 starlette/pydantic 塞進 `pyproject.toml` 的正式依賴,令只想用引擎的人也要一併安裝。**本票沒有新增任何第三方依賴。**
- **lightweight-charts v4.2.3 以本地檔引入**,不經 CDN:`karst/web/static/vendor/lightweight-charts.standalone.production.js`,由 `prototype/vendor/` 逐位元複製過來(Apache-2.0)。頁面全程不向外取任何東西。
- **入口是 `python -m karst.web`,不是 `karst web`**。`karst/gateway/cli.py` 的子命令是 `build_parser()` 內寫死的 if-chain,外面掛不到新子命令,而本票不准動那個檔;照 `karst/gateway/__main__.py` 同一個模式自成一道門。

**REST 面**(四個 GET,全部只讀):
`/api/meta`、`/api/runs?limit=N`、`/api/runs/<run_id>`、`/api/runs/<run_id>/candles?symbol=<代號>`。

**逐項剔驗收**:

1. **淨值圖與蠟燭圖,標記落在對應日期的蠟燭上** — 成立。淨值圖三條線(策略 `#26a69a` 粗 2、QQQ `#b07de0`、SPY `#7d869c`),曲線上按成交記錄標出有買賣的交易日,滑過即出成交浮層。點一筆交易鑽入該實體蠟燭圖,買箭在下、沽箭在上、帶文字,成交量柱按升跌上色。測試 `test_進出場標記落在對應日期的蠟燭上` 逐個核對:全部標記日期都有對應蠟燭,零個落空;點中那筆的進場日與出場日兩日都標得出。
2. **數據來自真實運行,頁內無寫死假數據** — 成立。REST 出的淨值序列同 `RunStore.window_stats()` 由 parquet 讀回那條逐點對得上;成交日標記的日子同 `orders.parquet` 的成交日完全相同。人手抽驗兩筆:2018-09-25 買 XOM 5361.79 股 @61.0047、2024-07-16 沽 META 681.75 股 @489.107,頁面顯示「5362 股 61.00」「682 股 489.11」,對得住源檔。原型那兩個假數據檔 `data.js` / `data-ext.js` **沒有**複製過來,靜態檔內查不到 `window.KARST`,亦沒有任何寫死數列;原型徽章與斜紋條照 design-system 3.15 移除。
3. **lightweight-charts + token,無自定色值** — 成立。測試把 `app.js` 與 `run-view.js` 內每一個色值字面值抽出來,逐個比對 design-system 1.7「圖表專用色」連 1.5 那兩格蠟燭成交量柱底色的全集,**零個例外**。`style.css` 由 `prototype/assets/style.css` 逐字複製(那份正是設計系統抽取的來源),測試另外核對十個 token 的值同 `design-system.md` 一致。圖表字級 11 = `--fs-xs`。
4. **換運行整頁跟住換,運行編號顯示得到** — 成立。頁頂「檢視運行」按鈕列(design-system 3.6)揀一次,整頁的圖、八項指標、逐筆交易、導航列的運行身份晶片、數據快照、頁尾一齊換,網址同步寫成 `?run=<編號>`,重新整理後仍是同一次。運行編號以等寬字顯示在頁頭 `h1` 旁邊,晶片浮層內另有一行。實測由 `run-728a01087531258f` 揀去 `run-f44f765ef0befd61`,連數據快照都由 61e284 換成 91a5d5。

**測試**:`tests/test_web.py` 四個測試對住四條驗收,`python -m pytest tests/test_web.py` 全部通過(4 passed)。測試打的是本機庫內真實運行——這正是要驗那件事;庫或運行不在就跳過,不捏一組數頂上。

**改動檔案**:新增 `karst/web/`(`__init__.py`、`__main__.py`、`server.py`、`data.py`、`static/`)、`tests/test_web.py`;`pyproject.toml` 加 `karst.web` 入 packages 並登記靜態檔 package-data。沒有碰 `karst/engine/`、`runs/`、`metrics/`、`data/`、`strategies/`、`gateway/`、`store.py`、`schema.py`。

## 留言

· 2026-08-28 01:30 KARST-032-web

**缺接口(擋住檢視視窗,本票內繞過)**:`karst.metrics.report.run_metrics()` 一給 `start`／`end` 就必拋 `ContractViolation`。成因在 `karst/metrics/report.py` 第 131-136 行:視窗只截 orders,不承接視窗**之前**已開的倉,FIFO 配對於是遇到「賣出實體 N 但手上沒有貨」,拋錯點在 `karst/metrics/trades.py` 第 105 行。兩次運行 × 兩個視窗,四次全失敗。全期(不給 start/end)完全正常。

後果:design-system 3.7 那個**檢視視窗**(重看不重跑)做不到八項指標,只做得到 `RunStore.window_stats()` 那三個數(累計回報、年化、最大回撤)——因為它不碰 orders,任何視窗都行得通。**本票不做檢視視窗**(不在範圍),所以只用全期,繞過了這條;但下一張要做檢視視窗的票會即刻撞上。`karst/metrics/` 不在本票可動範圍,未修。

**現況兩則,不是缺陷,只是下一手要知**:

1. **庫內兩套策略都未指定現役設定**,`store.get_active_setup()` 兩者皆拋 `NotFound`,所以 `facade_metrics()` 現時用不到,而頁面上沒有一個運行掛得到「現役」小籤。頁面走的是 `run_metrics(runs, run_id, ...)`,不受影響;現役設定一經指定,按鈕列就會自動標出來(程式已經接好,不用改)。
2. **運行數目已經上千**(本票收工時庫內 3544 次,KARST-029 參數掃描仍在寫)。design-system 3.6 那個按鈕列是為「歷次運行」十幾個設計的,擺不下上千個。**本票的處置**:按鈕列收到最近 8 次,旁邊照實寫「最近 8 次・庫內共 N 次(其餘經網址 ?run= 開)」,任何一個運行都可經 `?run=<編號>` 直接開。元件、狀態、樣式全部照原稿,只是數目封了頂。**這是我按實況定的一個界,不是用戶裁決**;真正的做法(分頁?按策略分組?搜尋?)是一個畫面決定,要人揀,值得另開一張票。

**兩處對不齊原稿、已按實情修正**(都在「修壞掉或對不齊的東西」之內,非設計改動):

- `app.js` 的 `minBarSpacing` 由原型的 `0.4` 放寬到 `0.02`。原型假數據點數少,`0.4` 撐得住;真實運行是十一年 2929 個交易日,`0.4` 之下 `fitContent()` 壓不進面板闊度,左邊 2015-2018 會被靜靜切走——圖例寫住「基期 100 ＝ 2015-01-02」而圖上根本見不到那一年。
- 換手率那一磚的單位。原型假數據當它是百分比(`3.66%`),`karst.metrics.turnover()` 的真實口徑是**每年換足幾轉**(1.0 = 一年一轉),所以顯示為 `3.66 轉／年`,第三行註「約每 69 個交易日換足一轉」。磚的三行結構(標籤／數值／口徑)不變。

**兩處按實情落檔,不是改設計**:

- 導航列只列已建成的那一頁,不掛其餘三頁的死連結。四頁建齊即回到原稿的四個連結。
- 右欄兩個分頁(指標、逐筆交易),沒有原型那個「因子檢視」分頁——逐日因子分數不在本票範圍,亦未見有現成接口讀得到;寧可沒有那一格,都不放一格假數據。

**一個口徑寫死在網頁層,已在畫面上交代**:Sortino 要無風險利率才算得出,而 `karst.metrics` 刻意不設預設值(逼呼叫方講明口徑)。網頁層在 `karst/web/data.py` 明文定 `DEFAULT_RISK_FREE_RATE = 0.04`,並把它隨指標一齊送到頁面,那一磚的第三行寫住「無風險利率 4.0%」——畫面上那個數字永遠交代得出它按什麼算。可經 `--risk-free-rate` 改。

**唯讀開庫**:網頁殼以 `sqlite3.connect("file:...?mode=ro", uri=True)` 開連線再餵給 `DefinitionStore`(仍然經 `karst/store.py`,D-027),不走 `DefinitionStore.open()`。兩個原因:`open()` 會執行建表 DDL 並 commit,一個檢視器不應該寫庫;而且同一個庫正被別的工序寫住(KARST-029/037),唯讀連線不會跟它爭鎖。
