---
id: KARST-035
title: 唯一入口治理補齊:現役設定指定與風控規則登記經入口並納入簽章核對
type: task
createdAt: 2026-08-28
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-025, KARST-030, KARST-022]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-28
---

## 工作內容

指定現役設定與登記共用風控規則自此都經唯一入口,而且 karst verify 核對得到:KARST-030 加了現役設定登記表、KARST-025 加了風控規則與策略引用兩表,三張表現時只能由 Python API 寫入,未有寫入者簽章,verify 掃不到——與 D-020 第 1、4 條「同一道門、繞過即揪得出」不符。範圍只是把既有登記接上命令列並納入治理清單,不改表結構、不改規則定義。

## 驗收條件

- [x] karst params activate 一句命令指定某策略的現役設定(釘死參數集某一版),並印出生效序號
- [x] karst risk 一類子命令列得出三條風控規則與各策略的引用
- [x] 三張新表納入簽章治理清單,經入口寫入的列 karst verify 報清白,繞過入口直接塞入的列被揪出
- [x] 不繞過 karst/store.py 開連線(D-027)

## 結果

· 2026-08-28 00:47 指定現役設定與登記風控規則自此都有命令列那道門,而且 `karst verify`
核對得到。表結構與規則定義一個字未動——只是把既有登記接上命令列,再納入治理清單。

- **驗收條件 1**:`karst params activate --strategy 趨勢波段 --name 現役 [--set-version N]
  [--note]` 印出「生效序號 第 N 次指定(seq_no=N)」,連釘死了哪一個 param_set_id、
  哪一版策略、指定時間與簽章。換一個 = 加一筆新指定,舊指定一字不變。
  測試 `test_params_activate_pins_one_param_set_and_prints_the_sequence`。
- **驗收條件 2**:`karst risk register`(登記三條正本,重覆跑回同一批)、`karst risk list`
  (三條規則連取值參數名)、`karst risk attach --strategy X --rule <程式名>`(記引用)、
  `karst risk refs [--strategy X]`(留空即逐套策略列引用,一條都沒有引用的照樣列出並註明
  「不引用不是錯」)。規則本體的正本仍然只住在 `karst/risk`,入口不另寫一份。
  測試 `test_risk_commands_list_the_three_rules_and_each_strategy_reference`。
- **驗收條件 3**:`active_setup`(主鍵 strategy_id + seq_no)、`risk_rule`、
  `strategy_risk_ref` 三張表納入 `GOVERNED_TABLES`。經入口寫入後 `karst verify` 報全庫清白;
  用庫層 API 直接指定一個現役設定(繞過入口)之後,同一句 verify 即報「未經唯一入口寫入:
  active_setup[…]」並回 3。測試 `test_the_three_tables_are_under_signature_governance`。
- **驗收條件 4**:入口全層無一處自開 sqlite 連線;三張表的 INSERT 一律住在 `karst/store.py`,
  入口只呼叫它的 API。測試 `test_gateway_writes_the_three_tables_only_through_the_store_api`
  逐個檔掃住這兩點。

三件登記與策略定義有一處不同:它們**重覆呼叫回同一批列**(三條規則的正本、同一個引用、
指同一個參數集兩次)。故 ledger 加了 `record_write_once`——同一列蓋過就算數,不再蓋第二次;
若庫內那一列的內容與當初簽的對不上,當場拋錯,不會用新內容蓋一個新簽章把痕跡蓋走。

**副作用(有意的)**:此後任何繞過入口寫這三張表的程式,`karst verify` 都會報「未經唯一入口
寫入」——包括直接呼叫 `store.set_active_setup()` 或 `karst.risk.register_risk_layer()` 的
Python 程式(現時 tests/test_risk_layer.py 與 karst/metrics 的說明例子屬此類,它們不跑 verify,
故無測試轉紅)。這正是本票要的效果,但日後那幾條路要改行入口,或明知會被 verify 點名。

改檔:`karst/gateway/{cli,service,ledger}.py`、`karst/store.py`(追加 `list_strategy_names`)、
新增 `tests/test_gateway_governance.py`(4 passed;全倉 `tests/` 68 條全綠)。

## 留言
