# 2026-08-29 因子值搬出定義庫(KARST-068)

KARST-064 把 Alpha158 的 555 萬個因子值逐列寫進 `karst.sqlite`,庫檔由 40 MB 漲到
1.5 GB。D-032 裁決:**值不再逐列住定義庫**,按「數據快照 × 因子庫批次」一批一個
壓縮檔,庫內只留登記與內容雜湊。本目錄記的是搬那一次。

    set PYTHONUTF8=1
    python experiments/2026-08-29-factor-parquet/migrate_factor_values.py ^
        --store karst.sqlite --snapshot 2026-08-28-a508d635a5fa ^
        --writer KARST-068-factor-parquet

腳本本身**不另寫一套遷移邏輯**,四步都是叫現成那幾道門:重新入庫(值今次落
Parquet)→ 關庫再開(第 11 版遷移在這一刻行)→ `VACUUM` → `karst verify`。

## 搬完之後

| | 搬之前 | 搬之後 |
|---|---|---|
| **定義庫 `karst.sqlite`** | **1,520.1 MB** | **37.3 MB** |
| `factor_value` 表內行數 | 5,550,924 | 0 |
| 值住在哪 | 庫內逐列 | `data/factors/2026-08-28-a508d635a5fa/alpha158.parquet` |
| **因子值檔** | — | **39.4 MB**(41,269,221 bytes,zstd) |
| 庫內留下什麼 | — | 一列批次登記(落點、內容雜湊、行數)+ 158 列「載住哪個因子版本、幾多行」 |
| 入庫用時 | 76.8 秒 | 5.9 秒 |

庫 + 檔合共 76.7 MB,對比原本 1,520.1 MB,是 **1/20**。庫檔回到 40 MB 量級,而且
**以後不會再因為多入一批因子而漲**——漲的是旁邊那個 Parquet 檔。

## 行數與 KARST-064 逐條對照

| | KARST-064 | 本次 | |
|---|---|---|---|
| 入庫行數 | 5,550,924 | 5,550,924 | 一樣 |
| 缺值比例 | 0.0443%(2,460 格) | 0.0443%(2,460 格) | 一樣 |
| 可執行時點留空 | 1,896 | 1,896 | 一樣 |
| 逐條因子行數 | — | — | **158 條全部一樣** |
| `karst verify` | 清白 | 清白(連因子值檔雜湊) | |

逐條數字在 `summary.json` 的 `rows_per_factor`,與 064 那份逐個 key 比較過,
`factors_differing_from_baseline` 是空的。ROC 族的暖身缺口、BETA/RSQR/RESI/CORR
的常數段留空,全部原封不動——**搬的只是載體,不是內容**(D-032:D-021 那三個時點
與 D-022 的語意一個字都沒有改)。

## 清空舊值那一步為什麼敢清

第 11 版遷移在開庫那一刻行,**三項齊備才清**,任何一項對不上就一列都不動:

1. 每一個「表內有值」的因子版本,都在某個批次檔的名單上;
2. 該因子版本在檔上登記的行數,與表內的行數**逐個相等**;
3. 每一個登記過的批次檔,真的在登記的落點上。

清的做法是 `DROP TABLE factor_value` 再照 DDL 起回一張空表(連索引與那四道
不准改不准刪的守閘),不是逐列 DELETE——555 萬列逐列刪會寫爆日誌檔。因子、
因子版本、實體三張表**一個編號都沒有動**,舊的因子版本編號照樣指得到。

跑過即在 `schema_meta` 留一筆(`migration_011_factor_values_to_files`),不會數第
二次。`factor_value` 這張表**保留**,留給小批人手登記的值(`store.write_factor_values`
那條路,選股引擎的 `latest_known_values` 仍然行它)。

## `VACUUM` 那一步不能省

清空只是把頁面標成「可以再用」,庫檔本身不會縮——不 `VACUUM` 的話 1.5 GB 那個檔
會一直佔住 1.5 GB。`VACUUM` 把庫重寫一次,37.3 MB 是重寫之後的實數。

## 檔案長什麼樣

一個 Parquet 檔六欄,型別揀到最緊:

| 欄 | 型別 |
|---|---|
| `factor_version_id` | int32 |
| `entity_id` | int32 |
| `event_time` / `knowledge_time` / `executable_time` | datetime64[us](可執行時點准留空) |
| `value` | float64(不縮 float32——值要原封不動) |

讀的一邊是 `karst.factorstore.FactorValueStore`:`read_long`(快照 × 因子 × 日期
窗口 → 長表)、`read_panel`(→ 日期 × 實體的闊表)。只讀要的那幾個因子版本
(pyarrow 下推 `factor_version_id in [...]`),不用把 555 萬列全部讀出來。

`karst verify` 逐個批次檔重讀再算一次雜湊,對不上就報「因子值檔落檔後被改動」,
檔不在落點就報「因子值檔不在登記的落點」。本次:清白。

## 給下一批人的數

`data/` 不入 git(`.gitignore`),Parquet 檔與價格快照一樣靠快照編號重造得返。
標普 500 擴容按本次比例推:500 隻約是 12 隻的 40 倍,即因子值檔約 1.6 GB,
而**定義庫仍然是 40 MB 量級**——這正是 D-032 要買的東西。

跑之前的庫檔備份:`C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-29-068.bak`
(1,593,966,592 bytes)。
