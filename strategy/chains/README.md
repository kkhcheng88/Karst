# strategy/chains —— 價值鏈(鏈層)名冊與量度結果

2026-09-07 倉重整,刪除已收線實驗目錄之前,把鏈層相關的資料表全部搶救到這裡(用戶明令:「價值鏈表是要留的資產」)。原實驗目錄已刪,**這裡是唯一正本**——已 grep 過 `data/`(含 `data/universe/`)與 `karst/`,別處沒有第二份。

四個來源實驗全部在 2026-09-02 至 09-03,收案裁決見 `.kira/decisions.md` D-157/D-161/D-163 與 KARST-159/161/175。詳細結論在 `research/archive/2026-09/2026-09-02-敘事鏈層存在性*.md`、`2026-09-03-敘事鏈層*.md`。

## 一、鏈位名冊(核心資產)

`2026-09-02-chain-layers/` —— 人手編纂、附申報證據的鏈位名冊,四個版本逐次收窄。欄位包括 `theme`(鏈)、`ticker`、`valid_from`/`valid_to`(鏈位有效期)、`role`(核心/邊緣)、`position`(上中下游位置)、`purity`(純度)、`source_url` 與 `evidence_10k`(申報原文佐證)、`switch_date_basis`(換鏈日期依據)。

| 檔 | 版本 | 鏈數 | 行數(公司-鏈位) | 一句 |
|---|---|---|---|---|
| `chain_membership_v0.csv` | v0 | 33 | 143 | 起始名冊,沿用舊倉 ADR-0039 鎖死名單 |
| `chain_membership_v1.csv` | v1 | 52 | 309 | 第一次擴充(KARST-159) |
| `chain_membership_v2.csv` | v2 | 65 | 347 | 純度欄與逐位申報佐證加入(KARST-161) |
| `chain_membership_v2_1.csv` | v2.1 | 65 | 349 | 加換鏈日期依據欄(`v21_change`、`switch_date_basis`、`switch_evidence`) |
| `chain_membership_v2_2.csv` | v2.2 | 65 | 353 | 換鏈證據補全(`v22_*` 三欄);**最新版** |
| `removed_v2.csv` / `removed_v2_1.csv` / `removed_v2_2.csv` | — | — | 23 / 21 / 21 | 各版剔走的公司與理由 |
| `chain_stories_v1/v2/v2_1/v2_2.md` | — | — | — | 逐鏈的敘事說明(人手寫,配對同版名冊) |
| `README.md` | — | — | — | 原實驗說明 |
| `out_v2_2/evidence_index.json`、`filing_index.json`、`evidence_raw/*.txt` | — | — | — | v2.2 換鏈證據的申報原文摘錄(13 份 8-K/6-K/20-F) |

## 二、鏈層存在性量度(結果表)

| 檔 | 來自 | 行數 | 一句 |
|---|---|---|---|
| `2026-09-02-narrative-layers/out/layers_table.csv` | 敘事鏈層存在性 v1(標普 500 級宇宙) | 540 | 由 10-K Item 1 文本自動分組出的鏈位表 |
| `2026-09-02-narrative-layers/out/layers.json`、`exemplar_layers.json`、`manual_layers_detail.json` | 同上 | — | 分組結果、樣板鏈、人手鏈位明細 |
| `2026-09-02-narrative-layers/out/results.json`、`posthoc_layer_size_split.json` | 同上 | — | 量度結果與事後鏈大小拆分 |
| `2026-09-02-narrative-layers-v2/out/layers_v2.csv` | v2(擴至敘事股宇宙) | 305 | 第二版鏈位表 |
| `2026-09-02-narrative-layers-v2/out/results_v2.json`、`posthoc_v2.json`、`universe_v2.json` | 同上 | — | 結果、事後拆分、宇宙定義 |
| `2026-09-03-narrative-layers-v3/out/layers_v3.csv` | v3 | 273 | 第三版鏈位表 |
| `2026-09-03-narrative-layers-v3/out/layers_rerun.csv` | v3 甲版補缺重跑(KARST-175) | 98 | 重跑版鏈位表;結論見 D-163 |
| `2026-09-03-narrative-layers-v3/out/results_v3.json`、`results_rerun.json`、`census.json` | 同上 | — | 兩次量度結果與普查 |
| `2026-09-03-narrative-layers-v3/out/adj_factor_audit.csv` | 同上 | 341 | 復權因子核對表(價格庫換源後的驗證) |
| `2026-09-03-narrative-layers-v3/out/industry_fill.csv` | 同上 | 85 | 行業補值表 |

每個目錄的 `CRITERIA.md`(v3 另有 `CRITERIA_rerun.md`)一併帶了過來——那是跑數前寫死的判準,沒有它結果讀不了。

## 三、沒有帶過來的

原實驗目錄的 Python 腳本、`data/item1/*.txt.gz`(10-K Item 1 文本語料,數千份,可由 `data/sec/10k_text/` 或 EDGAR 重抓)、`data/submissions/*.json`(SEC 申報索引,`data/sec/submissions/` 已有正本)、`data/new_close.parquet`(價格,可由 `data/prices/` 重取)、日誌檔。

## 四、狀態

鏈層線的裁決停在 D-163:置信區間過零,判「存在」但**只限事後表**;增量全部來自最純的主題鏈。要把鏈層用作③④類注的敘事共識度量器,先要答 KARST-175/170 留下的舉手。名冊本身(v2.2)是人手加申報證據砌成、不可再生的資產,所以留倉。
