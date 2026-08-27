---
id: KARST-034
title: 唯一入口加數據快照子命令:一句命令抓日線凍成快照並登記
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-027, KARST-022]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-28
---

## 工作內容

數據快照自此經唯一入口產生:一句 karst data snapshot 命令指定宇宙與窗口,即抓日線、凍成快照、登記編號並印出來。KARST-027 收檔時快照只能寫 Python 呼叫程式產生,不符 D-020「人手、本地 agent、日後內嵌 agent 同一道門」。範圍只是把既有管線接上命令列,不改管線本身;抓取時間(fetched_at)要在登記表查得到。

## 驗收條件

- [x] karst data snapshot 一句命令完成抓取、凍結、登記,並印出快照編號(真實抓取,離線自動略過)
- [x] 登記表直接查得到該快照的抓取時間與來源
- [x] karst data list 列得出庫內全部快照(編號、窗口、實體數、抓取時間)
- [x] 不繞過 karst/store.py 開連線(D-027)

## 結果

· 2026-08-28 00:41 數據快照自此有命令列那道門。管線本體(`karst/data/`)一個字未動——
唯一入口只是呼叫它,再把「幾時抓、抓的是哪一段窗口」記入新開的抓取登記附表。

- **驗收條件 1**:`karst data snapshot --ticker SPY --ticker QQQ --start … --end …`
  一句完成抓取、凍結、登記,印出快照編號連來源、抓取時間、窗口、宇宙、落點、內容雜湊。
  測試 `test_one_command_fetches_freezes_and_registers` 走 yfinance 真實抓取(本機連得通,
  已真跑一次;離線或未裝 yfinance 即自動 skip,沿用 KARST-027 的做法)。
- **驗收條件 2**:新增 `data_snapshot_fetch` 附表(SCHEMA_VERSION 5 → 6),存抓取時間、
  窗口起訖、實體數、列數、交易日數;來源刻意**不在附表再寫一次**,正本仍是
  `data_snapshot.source`(單一定義,無第二影像),`store.list_snapshots()` 兩表併讀一次過交齊。
  另開附表而不在原表加欄:快照登記落庫後不可改(trg_snapshot_no_update),舊庫已有的快照列
  亦不會憑空多出這幾格——附表只加不改,舊列一個字都不用動。
  測試 `test_registry_answers_when_and_from_where`。
- **驗收條件 3**:`karst data list` 逐行列出編號、窗口、實體數、抓取時間、來源。
  不是經入口凍的快照(例如直接呼叫管線的 Python 程式)照樣列得出,但明文寫「無抓取登記」,
  不冒充有值。測試 `test_list_shows_every_snapshot_in_the_store`。
- **驗收條件 4**:入口全層無一處自開 sqlite 連線,一律經 `karst/store.py`;
  測試 `test_gateway_opens_no_sqlite_connection_of_its_own` 逐個檔掃住這條護欄。

同一批數據重抓得回同一個編號時(KARST-033),抓取登記**沿用第一次凍結那刻的抓取時間**,
不覆寫——第一次落地是哪一刻是一件已經發生的事,不因為有人再抓一次而改變。

`--source csv --bars <檔>` 不是為測試開的後門,是 D-026 第 7 條講的適配器形態:
別的來源交得出同一套欄位(date、ticker、開高低收量)即經同一條管線入同一種快照;
順帶令命令列本身離線驗得到。宇宙代號只收起步名單上有的——一個代號是公司還是 ETF
決定了它以 SEC CIK 還是內部代碼為錨,命令列不猜。

改檔:`karst/gateway/{cli,service}.py`、`karst/schema.py`(追加附表)、
`karst/store.py`(追加 `record_snapshot_fetch` / `snapshot_fetch` / `list_snapshots`)、
新增 `tests/test_gateway_data.py`(4 passed;`tests/test_gateway.py`、
`test_definition_store.py`、`test_data_snapshot.py` 共 27 條照舊全綠)。

## 留言
