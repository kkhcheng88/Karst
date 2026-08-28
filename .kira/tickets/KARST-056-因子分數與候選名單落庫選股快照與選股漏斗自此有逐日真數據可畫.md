---
id: KARST-056
title: 因子分數與候選名單落庫:選股快照與選股漏斗自此有逐日真數據可畫
type: task
createdAt: 2026-08-28
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-050, KARST-054]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

策略詳情頁的選股快照與選股漏斗自此畫得齊原型全貌。KARST-050 發現 factor_value 與 active_setup 零列,運行產物只有淨值/持倉/委託,逐股因子分數與「範圍 → 基本面關 → 技術關 → 持倉」各層候選名單無從填,現時只畫兩層並註明。範圍:引擎每次運行把各決策日的候選名單各層與逐股因子分數落到運行產物(parquet,與淨值同一目錄,入運行編號的產物清單),策略詳情頁改讀真數據;不改運行編號的組成;示例運行重跑後編號不變。

## 驗收條件

- [ ] 兩個示例運行重跑後產物多出候選名單各層與逐股因子分數,運行編號逐位不變
- [ ] 策略詳情頁選股快照顯示逐股因子分數,漏斗畫齊有數據的各層,不再顯示「未有逐日因子分數」
- [ ] 既有測試全過,karst verify 清白

## 結果

## 留言
