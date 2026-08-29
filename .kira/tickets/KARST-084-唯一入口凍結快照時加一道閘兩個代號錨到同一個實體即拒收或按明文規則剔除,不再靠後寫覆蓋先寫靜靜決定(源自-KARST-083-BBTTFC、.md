---
id: KARST-084
title: 唯一入口凍結快照時加一道閘:兩個代號錨到同一個實體即拒收或按明文規則剔除,不再靠後寫覆蓋先寫靜靜決定(源自 KARST-083 BBT/TFC、EQR/VMRK)
type: task
createdAt: 2026-08-30
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-083]
claimedBy: null
closed: 2026-08-30
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

源自 KARST-083 舉手:`data snapshot` 現只擋「一個代號錨到兩個實體」,不擋「兩個代號錨到同一個實體」,後者由後寫覆蓋先寫靜靜決定留哪條,宇宙表列數與實際實體數對不上(BBT/TFC、EQR/VMRK 各撞同一實體而序列不是同一批數字)。完成後:(1) 凍結時同一實體收到多於一條代號序列即觸發明文規則——生效期未結束的優先 → 日線較多的優先 → 分不出就兩條都剔,並把每次觸發逐條寫入快照說明檔(哪個實體、哪幾個代號、留了誰、為什麼);(2) 該規則只住唯一入口一處,KARST-083 重凍腳本 refreeze083.py 內那份臨時規則改為呼叫入口的同一函數,不留第二份;(3) 快照說明檔加「宇宙表代號數 / 實體數 / 剔除數」三個數並保證相加對得上,`karst verify` 核這條等式;(4) 對現有三代標普 500 快照跑一次核對(不重凍),結果落 experiments/2026-08-29-ticker-history/README.md 一節。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不遞歸刪除倉外目錄。

## 驗收條件

- [x] 兩個代號錨到同一實體時凍結有明文結果並寫入說明檔;規則只有一份正本
- [x] verify 核「代號數 = 實體數 + 剔除數」;三代快照核對結果落檔
- [x] 有測試(至少:兩代號同實體、一條生效期未結束;兩條都結束但日線數不同;完全分不出);只跑所涉測試檔

## 結果

四項全做完。

**一、閘住進唯一入口,每次觸發逐條落檔。** 規則正本 `resolve_alias_collisions` 住
`karst/data/ticker_history.py`,次序寫死:生效期未結束優先 → 真實日線較多優先 →
分不出兩條都剔。凍結管線 `karst/data/pipeline.py` 的 `apply_alias_gate` 行在**登記實體
之前**呼叫它(登記那一層兩個代號會回同一個實體編號,行在之後就已經蓋走了),每次觸發
寫入 `manifest.json` 的 `alias_verdicts` 與 `說明.md` 新增的「五之三、同實體別名裁決」
一節:哪個實體、哪幾個代號、留了誰、為什麼。帶生效期的對照表由
`valid_to_for_window` 交出生效訖(與挑錨用同一條規矩,新的 `anchors_for_window` 是那份
正本),`karst data snapshot --anchors` 一路傳到管線。

**二、不留第二份。** `refreeze083.py` 內那 70 行臨時規則已刪,改為呼叫同一個函數。把
083 當時那批材料重新餵給搬家後的函數,判詞一模一樣:留 `TFC`(剔 `BBT`)、留 `VMRK`
(剔 `EQR`)——行為沒有變。

**三、三數等式。** 說明檔身分表新增「宇宙表代號數 / 實體數 / 同實體別名剔除數」,
並當場報等式對不對得上;`manifest.json` 同時存三個數。`karst verify` 逐個快照核
「代號數 = 實體數 + 剔除數」,讀不到檔的快照略過不報(「這部機沒有這份檔」與「這個
快照對不上」是兩件事)。

**四、三代快照核對(唯讀,不重凍):三代全部對得上。**

| 代 | 快照編號 | 代號數 | 實體數 | 剔除數 | 等式 |
|---|---|---|---|---|---|
| 第一代 | `2026-08-28-493fd1df1cb9` | 625 | 625 | 0 | 對得上 |
| 第二代 | `2026-08-28-c442236133d4` | 607 | 607 | 0 | 對得上 |
| 第三代 | `2026-08-28-3bf7ab0a522a` | 603 | 603 | 0 | 對得上 |

剔除數讀出 0 不是「沒有剔過」:三代都凍結於這道閘之前,說明檔沒有那一格,以 0 核;
083 剔走的 `BBT`/`EQR` 是在呼叫入口**之前**由腳本篩走的,從未進過那份宇宙名單。
第一代與第二代撞不到這道閘,是因為當時 `BBT` 錨到另一家公司、`EQR` 是佔位錨——
**撞車要等錨改對了才浮出來**,所以這道閘不能只靠一次重凍解決。

落檔:`experiments/2026-08-29-ticker-history/README.md` 最後一節,連跑法
`check_balance_084.py`。

測試 `tests/test_alias_collision.py` 10 個全過;既有 `test_data_snapshot`、
`test_gateway_data`、`test_gateway_governance`、`test_gateway`、`test_alpha158_ingest`
共 43 個全過。

· 2026-08-30 18:05 善後做完:`2026-08-28-d506871935cd` 已由登記冊除名。它是本閘第一次
上工抓到的真個案(605 個代號只得 603 個實體)。「由庫內除名」照字面做不到——
`data_snapshot_fetch`、`factor_value_batch`、`factor_value_batch_member` 三張表各有一道
`BEFORE DELETE` 閘寫明「登記不可刪,追溯要指得回」;舉手後主 agent 裁定不拆閘,除名
改為**加一列**(主 agent 依 D-020 第 4 條、D-026 第 2 條推出,非用戶新裁決)。

- 庫身第 12 版加只加不改不刪的 `data_snapshot_retraction`(快照編號、理由、被哪個快照
  取代、除名者、除名時間),入 `GOVERNED_TABLES` 蓋簽章——有人繞過唯一入口靜靜除掉
  一個快照,`verify` 一掃就見到它沒有簽章。
- 唯一入口 `karst data retract-snapshot --snapshot … --reason … --superseded-by …`;
  有回測運行掛住即拒收(運行要講得出自己跑的是哪一批數),同一個快照不准除名兩次。
- `list_snapshots`、三數等式核對與畫面選單一律略過已除名快照;`get_snapshot` 與說明檔
  照樣讀得到,快照目錄與 parquet 一個字都沒有動(D-026 第 3 條)。
- d506 那 15 個 Alpha158 因子批次不另除名:批次登記本身指得回快照就夠,而且同名同行數
  的 15 個批次早已在正式第三代上重入。
- `karst verify` 現已回清白(exit 0),六個可回測快照三數全部對得上。
- 新測試 `tests/test_snapshot_retraction.py` 8 個全過;連同上述共 51 個全過。
- 詞彙表加「除名快照 / retired snapshot」;`experiments/2026-08-29-ticker-history/README.md`
  三處提到 d506 的地方補上「已除名」。

## 留言

· 2026-08-30 **新加的等式在實庫上抓到一個真個案,已按裁決處置。**(主 agent 依 D-020
第 4 條與 D-026 第 2 條推出,非用戶新裁決。)

`karst verify` 第一次跑就在庫內第四個快照上報一處不合格:

    2026-08-28-d506871935cd:宇宙表代號數 605 = 實體數 603 + 剔除數 0;對不上
      實體 547 收到 2 個代號:BBT、TFC
      實體 591 收到 2 個代號:EQR、VMRK

那是 KARST-083 加規則**之前**凍出來的第三代初版:605 個代號只得 603 個實體,兩條價格
序列被靜靜蓋走——正是本票要防的那件事,亦即這道閘第一次上工就抓到真貨。它已被正式
第三代 `2026-08-28-3bf7ab0a522a` 取代,零回測運行掛住。

**中途舉手的一格:「由庫內除名」照字面做不到。** `data_snapshot_fetch`、
`factor_value_batch`、`factor_value_batch_member` 三張表各有一道 `BEFORE DELETE` 閘,
寫明「登記不可刪,追溯要指得回」;刪走等於把一件發生過的事由帳上抹掉。舉手之後主
agent 裁定:不拆閘,除名改為**加一列**。

已照此做完:新開只加不改不刪的 `data_snapshot_retraction`(庫身第 12 版),入治理清單
蓋簽章;`karst data retract-snapshot` 是它的唯一入口;`list_snapshots`、三數等式核對與
畫面選單一律略過已除名快照,`get_snapshot` 與說明檔照樣讀得到,快照目錄與 parquet
一個字都沒有動。d506 那 15 個 Alpha158 因子批次不另除名——批次登記本身指得回快照就
夠,而且同名同行數的 15 個批次早已在正式第三代上重入。`karst verify` 現已回清白
(exit 0)。
