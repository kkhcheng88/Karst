---
id: KARST-067
title: 策略頁與抓取登記收尾:宏觀驅動器參數區顯示序列齊全度、抓取登記加警報欄、策略頁網址只帶運行編號時身份對不上
type: task
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-056, KARST-061]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
closed: 2026-08-29
---

## 工作內容

三件細小收尾,全部源自 KARST-056 與 061 同時在改同一批檔而留下。(1) KARST-061 已備好齊全度端點(GET /api/macro/completeness),策略詳情頁宏觀驅動器參數區補「序列齊全度」一行(strategy.js 取數掛上,照 061 票上寫法,不改設計);(2) 抓取登記表加兩格:齊全度警報條數、警報摘要(KARST-061 留言建議),原地遷移保留既有編號,schema 版本加一,karst data list 可見;(3) 策略詳情頁網址只帶 ?run= 不帶 ?id= 時,上半部策略身份與歷次運行取了預設策略,與正在看的運行對不上(KARST-056 順帶發現)——由運行反查策略,令兩種寫法一致。不加參數預設值;只跑所涉測試檔。

## 驗收條件

- [x] 策略詳情頁宏觀驅動器參數區顯示序列齊全度一行,真數據
- [x] 抓取登記新增警報兩格,karst data list 可見,既有登記保留;karst verify 清白
- [x] 只帶 ?run= 的網址與帶齊 ?id=&run= 的顯示一致(測試證明);只跑所涉測試檔

## 結果

三件全部落地,兩個測試檔共 12 項全綠,`karst verify` 全庫清白。

**(1) 序列齊全度一行。** `strategy.js` 的 `renderConfig()` 在驅動器那組晶片之後、換倉節奏之前,
當參數帶 `macro_snapshot` 時多出一枚「序列齊全度」晶片,值先寫「讀取中……」,再向
KARST-061 的 `GET /api/macro/completeness` 取數填成「14 條・尾段貼齊主日曆」或
「14 條・1 條尾段落後最多 28 日」;取不到寫「讀不到」,不留空白。快照編號放在晶片的
`title`,沒有另開一處顯示身份(守 design-system §5.3)。切運行時用 `S.seq` 序號擋住舊請求
覆蓋新畫面。瀏覽器實測 `/strategy?id=1&run=run-7e2af2aa21acc1ca` 見到
「序列齊全度 14 條・1 條尾段落後最多 28 日」——那 28 日是 VIX_3M 在換源前那個快照真有的尾段缺口,
不是砌出來的數。

**未解(要如實記住):庫內目前沒有一次正式運行帶 `macro_snapshot`。** 帶宏觀快照的只有
「因子輪動(ETF 版)」的掃描格,而該策略正式運行數為 0,所以 `/strategy?id=3` 現在是空狀態,
這枚晶片今日只能靠上面那條「策略編號與運行編號各自指向不同策略」的網址催出來。等有一次
宏觀策略的正式運行入庫,它就會在正路上自然出現。這不是本票的缺失,是庫內還沒有那筆數據。

**(2) 抓取登記兩格。** `data_snapshot_fetch` 加 `alert_count`、`alert_summary`,
SCHEMA_VERSION 加一(當時 8→9;其後 KARST-064 再疊到 10)。**原地遷移用
`ALTER TABLE ADD COLUMN`,不重建表**——重建會動到既有 4 筆登記的 `fetched_at`,那個時刻補不回。
兩格皆可空,而且空與零意思不同:NULL ＝ 沒有核對過(價格快照、以及本次遷移之前就在庫內的登記),
0 ＝ 核對過而零警報。DDL 用一條跨欄 CHECK 迫兩格同生同滅。
`record_snapshot_fetch` 兩個參數**必填、無預設值**,只給一格會被 `ContractViolation` 頂回。
凍結宏觀快照時由 `gateway/service.py` 的 `completeness_summary()` 寫入摘要;價格快照照舊留空。
`karst data list` 見到「齊全度 警報 N 條・……」一行。真庫遷移後 4 筆舊登記逐格原樣不變、
全部 NULL,`data list` 對它們的輸出一字沒變;`schema_meta` 有
`migration_009_snapshot_fetch_alerts` 一筆。`data_snapshot_fetch` 本來就不在 `GOVERNED_TABLES`,
所以加欄動不到任何內容雜湊,`karst verify` 前後同樣清白。改 schema 前已將整個 40 MB 庫
位元複製到 `~/.claude/backups/karst.sqlite.2026-08-29-067.bak`。

**(3) 只帶 ?run= 的網址。** `api_strategy.py` 加 `_resolve(reader, wanted, run_id)`:沒有
`?id=` 而有 `?run=` 時,由 `runs.get_run(run_id).strategy_name` 反查策略,`/api/strategy` 與
`/api/strategy/runs` 兩個端點都走同一條路。運行編號不存在時直接 404,**不再靜靜退回預設策略**
——原本的毛病正是這個無聲的退路。`strategy.js` 的 `boot()` 把 `run` 一併帶落 API。
實測 `/strategy?run=run-024df83fb4891c89` 出「因子混合(ETF 版)」,與帶齊
`?id=1&run=…` 的回應逐欄相同;不帶任何參數仍是預設策略「趨勢波段」,舊行為沒被改掉。

**動到別人正在改的檔:** `karst/gateway/cli.py` 只改 `_data_list` 一段(印齊全度那兩行),
改前重讀最新版;KARST-065 的快照命令一段沒碰。

**新詞建議(未自行改 CONTEXT.md):** 序列齊全度 / series completeness;尾段落後 / stale tail。

**測試:** `tests/test_snapshot_fetch_alerts.py`(新,6 項:v9 原地遷移逐格保留舊列、兩參數必填無預設、
只給一格被拒、尾段落後的快照入登記並在 `data list` 見到、乾淨凍結記成「警報 0 條」、
價格快照永不核對也不印那行);`tests/test_web_strategy.py`(補 2 項:兩種網址寫法回應相同 ＋ 假運行編號 404;
齊全度晶片的數由端點真數據填,並與從磁碟重算的結果對得上)。只跑這兩個檔,沒跑全庫。

## 留言
