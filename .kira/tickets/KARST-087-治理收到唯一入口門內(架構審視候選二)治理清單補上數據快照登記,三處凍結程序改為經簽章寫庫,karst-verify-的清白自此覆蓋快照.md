---
id: KARST-087
title: 治理收到唯一入口門內(架構審視候選二):治理清單補上數據快照登記,三處凍結程序改為經簽章寫庫,karst verify 的清白自此覆蓋快照
type: task
createdAt: 2026-08-30
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-084]
claimedBy: agent-087
epic: V1 建置
deliverable: KARST-D03
closed: 2026-08-30
---

## 工作內容

源自 research/2026-08-30-architecture-review-backend.md 候選二(用戶 2026-08-30 授權:技術性候選全部做)。完成後:(1) 治理清單(D-020 第 4 條)收入數據快照登記(data_snapshot 與其抓取登記),與現有的快照除名一致;(2) 現時繞過簽章直接寫庫的三處凍結程序(價格線、宏觀線、重凍腳本)一律改為經唯一入口的簽章寫入,定義庫本身不再接受無簽章的快照登記;(3) 既有已登記的快照補簽(經唯一入口的補簽命令,留補簽痕跡:誰、幾時、為什麼),補簽後 karst verify 對全部快照核簽章;(4) verify 報告分開列「定義、因子批次、快照」三類各自清白與否。動庫前備份到 C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-087.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 karst/web/static/ 與 prototype/。

## 驗收條件

- [x] 治理清單含數據快照登記;三處凍結程序無一繞過簽章(測試:直接寫庫的快照登記被 verify 點名)
- [x] 既有快照已補簽並留痕;verify 三類分列且全部清白
- [x] 只跑所涉測試檔;備份已做

## 結果

治理由此覆蓋取數的源頭。`data_snapshot` 與 `data_snapshot_fetch` 入治理清單,定義庫不再
受理無簽章的快照登記(寫入層檢查,見留言),三處凍結程序一律經唯一入口簽章寫庫。倉根
karst.sqlite 內 21 列收窄之前落庫的舊登記已補簽並逐列留痕;`karst verify` 現時分定義、
因子批次、快照三類分列,三類全部清白。

## 留言

### agent:agent-087 · 2026-08-30 05:20
做完,待收貨。

**做成了什麼** —— 以前 `karst verify` 報「全庫清白」時,取數的源頭根本不在核對範圍內:價格線、宏觀線、重凍腳本三處各自拎住定義庫直接寫一列快照登記,一列簽章都沒有。現在那一列(連同抓取登記)入了治理清單,而且定義庫本身不再受理無簽章的快照登記。

**改了哪些檔**

生產碼:
- `karst/schema.py` —— 第 13 版:加補簽留痕表 `gateway_countersign`(只加不改不刪,兩道 trigger)。舊庫重開時 DDL 自動補建,既有登記一列不動,不需要另寫遷移。
- `karst/gateway/ledger.py` —— 治理清單加 `data_snapshot`、`data_snapshot_fetch`;加三類分類表 `TABLE_CATEGORIES` 與 `category_of()`;加 `unsigned_rows()`、`countersign()`、`countersigned_rows()`;`Finding` 加 `category`。
- `karst/store.py` —— 快照登記那道閘:`attach_snapshot_signer()` / `_require_snapshot_gate()` / `_sign_snapshot_row()`;`register_snapshot` 與 `record_snapshot_fetch` 兩句在寫之前先要簽章手,寫完即簽,同一次寫入落地。
- `karst/gateway/service.py` —— `Gateway.__init__` 裝上簽章手;加 `countersign_snapshots()`、`verify_report()`、`Countersign`、`CategoryVerdict`。
- `karst/gateway/cli.py` —— 加 `karst data countersign-snapshots --reason`;`karst verify` 改為三類分列。
- `karst/gateway/__init__.py`、`karst/batches.py`、`karst/data/__init__.py` —— 匯出與說明同步(後兩者的用法示例本來教人拎裸庫身去凍)。
- `experiments/2026-08-29-ticker-history/refreeze.py`、`refreeze083.py` —— 庫身改由唯一入口開出,重凍之前先放手,不再同時有兩條連線壓住同一個庫檔。

測試:
- 新增 `tests/test_snapshot_governance.py`(17 項)。
- 13 個測試檔的庫身由 `DefinitionStore.open(...)` 改為 `Gateway.open(...).store`,共 34 處:test_engine_audit、test_selection_trace、test_runs、test_definition_store、test_alias_collision、test_data_snapshot、test_data_yfinance、test_web_series_missing、test_web_holdings、test_macro_completeness、test_macro_snapshot、test_macro_yfinance、test_snapshot_fetch_alerts。
- `tests/test_gateway_governance.py`、`tests/test_cadence_weekly.py` —— 核對報告的字眼由「全庫清白」改為「三類全部清白」。
- `tests/test_factor_parquet.py` —— 順手修一個**本票之前已經紅了的**斷言:它寫死 schema_version 等於 "11",而庫身第 12 版起就已經對不上。改為核 `str(SCHEMA_VERSION)`,核的是「舊庫重開之後版本印記跟上庫身」而不是某一個數字。

文件:`CONTEXT.md` 詞彙表加「快照補簽 / snapshot countersign」,並收窄「治理清單」那一條(講明分三類、快照自本票起入清單)。

**新命令名** —— `karst data countersign-snapshots --reason "…"`;詞彙表中英各一:快照補簽 / snapshot countersign。

**用寫入層檢查而不是觸發器,理由** —— 簽章是**寫完那一列之後**才算得出的(內容雜湊要讀回整列),所以 sqlite 的 BEFORE INSERT 觸發器在那一刻根本無從知道這一列將來簽不簽得到;要用觸發器就得先另寫一張「意向表」再由觸發器查它,等於為了避開一句 Python 檢查而在庫身多鋪一層人人都要記得去填的機關。寫入層那句反而做得到觸發器做不到的事:它在寫之前就攔住(拒收時庫內一個字都沒有),而且寫入與蓋簽章包在同一個交易之內——簽章手不做事,剛寫的那一列一併回滾。閘本身裝在庫身,鑰匙與寫入者身分只有唯一入口拿得到,所以一個不是由那道門開出來的庫身,凍不出快照登記;凍結管線(價格線、宏觀線)一句都不必改,分別只在**那個庫身是不是由那道門開出來的**。

**補簽了幾多個快照** —— 倉根 `karst.sqlite` 共 21 列:12 列 `data_snapshot` + 9 列 `data_snapshot_fetch`。補簽者 KARST-087-agent,理由逐列落 `gateway_countersign`。補簽只擔保「由那一刻起這幾列沒有再被改過」,擔保不了它們當日是經唯一入口寫的——補簽冊逐列留住這個分別。

**有沒有發現不一致** —— 沒有。補簽之前先核一次:快照那一類 21 處全部是「未經唯一入口寫入」,**零處**「落庫後被改動」或「簽章對不上」,所以票上那條停手規則沒有觸發。(補簽命令本身亦寫死了這條規矩:快照類只要有一處簽章對不上,整道命令一列都不補。)

順帶查到、但不是不一致的一件事:12 個快照之中有 3 個(2026-08-27-61e284eaa998、2026-08-27-91a5d51339d9、2026-08-28-3b2de5c59740)的快照目錄已經不在 `data/` 底下——那是 2026-08-28 數據目錄被誤清那一次的遺留,登記那一列本身完好。補簽照簽(簽的是登記那一列,不是檔案),三數等式核對本來就會略過讀不到檔的快照。要不要把這 3 個除名,不在本票範圍,留給主腦裁。

**verify 三類結果**(倉根 karst.sqlite,補簽之後)
```
  分三類:
    定義:清白(50799 列)
    因子批次:清白(997 列)
    快照:清白(22 列)
  三類全部清白
```
補簽之前那一次是「快照:揪到 21 處不合格(22 列)」,定義與因子批次兩類當時已經清白。

**跑了哪些測試檔及結果** —— 分三批跑所涉檔案,共 44 個檔:
- 第一批 16 檔:129 passed,2 failed(見下)
- 第二批 15 檔:129 passed
- 第三批 17 檔:117 passed,4 failed(見下)
- 修正後重跑 test_cadence_weekly、test_gateway_governance、test_factor_parquet、test_snapshot_governance:38 passed

收工時仍然紅的只餘 2 項,**兩項都與本票無關,亦不是本票弄紅的**:
1. `test_web.py::test_圖用lightweight_charts且色值字級取自設計系統` —— 前端有兩個色值 `#06121f`、`#dfe4ee` 不在設計系統內。屬未收的原型/前端改動(倉內 prototype/ 與 style.css 現時未 commit),本票明文不碰前端。
2. `test_web.py::test_運行選單只列正式運行且認得出是哪一次` —— 測試要求 `run-7e3b498e086bdb88` 出現在 `limit=8` 的正式運行清單內,但庫內正式運行已累積到 13 條,它排第 11。是清單長大之後的舊斷言失準,與簽章、快照全無關係。

**順帶交低一件事**(已同時落運作觀察簿) —— 六個 `test_web*.py` 直接對**倉根那個生產庫** `karst.sqlite` 跑,其中 `test_web_jobs.py` 每跑一次就在生產庫多寫一條正式運行(這一次多了 `run-47479e5b36fed94a`)。跑測試會改動生產庫,這件事本身值得另開一票處理,不在本票範圍。

**紀律** —— 動庫之前已備份到 `C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-087.bak`(40MB,整檔複製)。沒有加任何參數預設值。沒有 commit。沒有碰 `karst/web/static/`、`prototype/`,沒有建任何目錄連結,沒有用 worktree,沒有起服務。
