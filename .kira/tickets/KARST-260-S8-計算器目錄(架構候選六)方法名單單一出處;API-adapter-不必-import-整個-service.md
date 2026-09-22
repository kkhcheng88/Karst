---
id: KARST-260
title: S8 計算器目錄(架構候選六):方法名單單一出處;API adapter 不必 import 整個 service
type: task
createdAt: 2026-09-23
risk: low
model: opus
fits: 一程:calculations、mcp_server、agents/adapters
dependsOn: [KARST-259]
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依執行計劃 §三 8 及架構評審候選六。方法名單目前寫在四處;API adapter 為用計算器 import 整個 service。把方法目錄收到 calculations 一處,MCP 與 adapter 由它取得名單及執行。計算結果不變。程式只住 karst/。

## 驗收條件

- [ ] 方法名單只有一處定義
- [ ] agents/adapters 不再 import service 以使用計算器
- [ ] 既有計算回歸(含 73.0308 等精確值)全部通過

## 結果

## 留言
