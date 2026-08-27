---
id: KARST-022
title: 唯一入口 CLI v0:定義與運行一律經同一道門入庫
type: task
createdAt: 2026-08-27
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-021]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-27
---

## 工作內容

策略定義、參數與因子定義自此只有一條入庫的路:一套命令,由它查合約、蓋版本時間戳、留血統;繞過它直接改庫的寫入,不是被擋住就是被偵測得到,不會靜靜生效。範圍是這條寫入通道本身與它的合約檢查,不含任何策略內容,亦不含因子計算。依 D-020 第 4 條唯一入口(single gateway)——治理住在唯一入口,不住在對話,人手與 agent 同一道門;依 D-002 第 4 條單一定義(single definition),每項定義全庫只有一個正本、無第二影像;版本照 D-021 第 9 條 git 式父版本鏈。

## 驗收條件

- [x] 經命令寫入一個策略定義與一個因子定義皆成功,兩者自動蓋齊版本、時間戳與父版本(D-020 第 4 條、D-021 第 9 條)
- [x] 合約不合格者(例:因子缺刻度型、缺知情時間)被命令拒收,庫內一個字都寫不入(D-021 第 2、3 條)
- [x] 繞過命令直接改庫之後,命令下次讀庫時報得出該處不合格,不會當作正常內容用落去(D-020 第 4 條)
- [x] 同一項定義在庫內只有一個正本,命令講得出它的唯一落點,查不到第二份影像(D-002 第 4 條)

## 結果

· 2026-08-27 23:45 唯一入口 CLI v0 落地。策略定義、參數集、因子定義自此只有一條入庫的路:`karst` 命令。它查合約、蓋版本時間戳、留寫入者簽章;繞過它直接塞入庫的內容,下次核對即現形。

**做了什麼(路徑)**

- `karst/gateway/`(全新):`cli.py`(argparse,只用標準庫)、`service.py`(Gateway 門面,查合約→寫入→蓋簽章)、`ledger.py`(寫入者簽章與全庫核對)、`__main__.py`(`python -m karst.gateway`)。
- `karst/schema.py`(只追加,不改既有表):`strategy`、`strategy_version`、`strategy_factor_ref`、`param_set`、`param_value`、`gateway_write` 六張表,連「不可改、不可刪」trigger;`SCHEMA_VERSION` 1 → 2(舊庫重開自動補建新表)。
- `karst/store.py`(只追加,不改既有函數簽名):策略與參數集的登記、版本鏈、查詢 API;`locate_definition`(唯一落點)、`find_name_occurrences`(全庫掃第二影像)、`connection` 屬性(供簽章用)。
- `pyproject.toml`:只加 `[project.scripts] karst = "karst.gateway.cli:main"`。
- `tests/test_gateway.py`(全新):5 個測試,每個對住一項驗收條件。

**命令面(v0)**

`init` / `factor register|new-version|show|write-values` / `strategy register|new-version|show` / `params add|show` / `where` / `verify`。回傳碼:0 寫得入或核對清白、1 合約拒收、2 命令用法錯、3 核對揪到不合格。

**策略定義的最低合約**:名稱(全庫唯一)、類型(策略總覽八類之一:fundamental / technical / multifactor / event / meanrev / follow / macro / options)、引用因子(釘死在「具體定義 × 版本」那一級,寫 `名稱@版本號`,留空即釘死當下最新版)、參數集(名稱→值,必帶換倉節奏 daily/monthly/quarterly,**無預設值**,缺就拒)。策略與參數集皆有 git 式版本鏈(版本號 + 父版本 + 落庫時間)。

**繞過的兩道防線**:一,庫檔的 sqlite trigger 擋改寫與刪除(既有的因子/快照四個,今次補上策略、參數集、簽章共十個);二,`gateway_write` 寫入者簽章擋「直接 INSERT 一行新定義」——簽章鑰匙住在庫檔以外(`<庫檔>.gateway-key`,或環境變數 `KARST_GATEWAY_KEY`),拿到庫檔不等於簽得出章。`karst verify` 逐列核對受治理的七張表,分得出三種病:未經唯一入口寫入、落庫後被改動、簽章在案但庫內查無此列。

**測試命令與結果**

```
PYTHONUTF8=1 python -m pytest tests/test_gateway.py tests/test_definition_store.py -q
→ 11 passed(新增 5 個 + KARST-021 原有 6 個全綠,無回歸)
```

另在本機實跑一次命令(`init` → 登記因子 → 登記策略連參數集 → `verify`),輸出與核對皆如預期。

**逐項驗收**

1. **寫得入、蓋齊版本時間戳父版本** —— `test_cli_stamps_version_timestamp_and_parent`:經命令登記因子第 1 版、出第 2 版(父版本指回第 1 版)、登記策略連參數集;回讀確認版本號、父版本、落庫時間齊備,策略引用釘死因子第 1 版。
2. **不合格者拒收、庫內一個字都寫不入** —— `test_cli_rejects_incomplete_contracts`:缺刻度型、缺產生程序、類型不在八類之內、知情時間早過事件時間(前視),四樣皆回傳 1;回讀確認庫內查無該因子、該策略、該值。
3. **繞過即揪得出** —— `test_verify_catches_writes_that_bypass_the_gateway`:直接開庫檔 INSERT 一套策略後 `verify` 回傳 3,明文報「未經唯一入口寫入」;同一條路試改已落庫的因子定義,連 trigger 那一關都過不到。
4. **唯一正本、無第二影像** —— `test_definition_has_exactly_one_home`:`karst where` 講出正本落點(庫檔 → `factor(factor_id=1)`)、版本鏈同表不是第二份定義;全庫逐表逐欄掃描,該名稱只出現在正本那一欄(引用它的策略只存編號)。

## 留言

· 2026-08-27 23:45 KARST-022-builder:三項留給後續票,連同一個要補的小手尾。

1. `pyproject.toml` 的 `[tool.setuptools] packages` 一行**未加** `karst.gateway` —— KARST-023 同時在改同一個檔,避免撞車故不碰。未裝套件時 `python -m karst.gateway` 照行,測試亦是走這條;但日後 `pip install .` 之前要補上 `karst.gateway`(連 `karst.engine`)。
2. 策略八類取自 KARST-015 原型的 `prototype/assets/data-ext.js`(`K.strategyTypes`),用戶未明文裁決它同時是庫層合約。若日後改分類法,`strategy` 表的 CHECK 與已登記策略的類型要一併遷移。
3. 兩處刻意留在 v0 範圍以外:(一)因子值不逐列蓋簽章——行數與定義不同一個量級,它靠寫入時的合約檢查、trigger 鎖死、以及所掛因子版本已有簽章三重防線;(二)**回測運行登記**(運行 = 策略版本 × 參數 × 期間 × 數據快照,規格第 7.4 節)未做,參數集與策略版本已備妥它所需的兩格,留待引擎票接上。
4. 新詞兩個,按派工指示不自行入詞彙表,在此列明待裁:**寫入者簽章(writer signature)**、**參數集(param set)**。
