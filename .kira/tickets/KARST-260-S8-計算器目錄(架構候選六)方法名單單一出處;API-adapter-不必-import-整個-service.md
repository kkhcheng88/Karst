---
id: KARST-260
title: S8 計算器目錄(架構候選六):方法名單單一出處;API adapter 不必 import 整個 service
type: task
createdAt: 2026-09-23
risk: low
model: opus
fits: 一程:calculations、mcp_server、agents/adapters
dependsOn: [KARST-259]
claimedBy: Opus-S8
epic: 根基重整
deliverable: KARST-D12
closed: 2026-09-23
---

## 工作內容

依執行計劃 §三 8 及架構評審候選六。方法名單目前寫在四處;API adapter 為用計算器 import 整個 service。把方法目錄收到 calculations 一處,MCP 與 adapter 由它取得名單及執行。計算結果不變。程式只住 karst/。

## 驗收條件

- [x] 方法名單只有一處定義
- [x] agents/adapters 不再 import service 以使用計算器
- [x] 既有計算回歸(含 73.0308 等精確值)全部通過

## 結果

· 2026-09-23 03:40 方法目錄收到 `karst/calculations.py` 的 `CATALOG` 一處,MCP 與 API adapter 由它取得名單、說明與執行
- 方法目錄 `calculations.CATALOG` 是唯一名單:每列寫答什麼、必填參數、單位,估值類另帶函式;`METHODS` 由它導出。
- 原本四處的處理:service 的 `CALCULATION_METHODS`、`CALCULATION_UNITS`、`calculate`、`CALCULATE_TOOL`、`calculate_tool` 整段移入 calculations(改名 `run`、`TOOL`、`run_tool`),service 不再有計算段;MCP `calculate` 的手寫清單 docstring 刪去,改用 `calculations.TOOL` 的描述(名稱與參數 `method`、`params` 不變);adapter 的計算工具描述與 schema 直接取 `calculations.TOOL`(method 由自由字串收窄為目錄 enum)。
- adapter 由 `from ...service import calculate_tool` 改為 `calculations.run_tool`,整個 adapters 套件不再引用 service。
- 輸出不變:`run` 的回傳(description、unit、receipt、calculator_version)逐字沿用原 service 文字;計算器版本仍 0.3.0。
- 測試:全套 454 通過、1 跳過;唯一失敗為既知 test_reader 符號連結(WinError 1314)。新增一項測試核 adapter 與 MCP 工具描述都取自目錄、adapter 原始碼不含 service。
- 未納入:`research_math.py`(指數盈利、倍數增長兩個 CLI 計算)及 `knowledge.valuation_matrix` 是另外的計算,不在 MCP `calculate` 名單內,未搬;要併入同一目錄另開票。

## 留言

### agent:Opus-S8 · 2026-09-23 03:40

認領並完成。最小一刀:只搬目錄與工具外殼,算式一行未改。MCP 工具描述文字改為與 API adapter 同一份(內容合併原 docstring 的參數說明),對外名稱與參數相容。
