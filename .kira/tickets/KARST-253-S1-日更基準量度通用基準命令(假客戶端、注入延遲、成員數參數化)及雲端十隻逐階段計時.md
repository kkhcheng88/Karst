---
id: KARST-253
title: S1 日更基準量度:通用基準命令(假客戶端、注入延遲、成員數參數化)及雲端十隻逐階段計時
type: task
createdAt: 2026-09-23
risk: medium
model: opus
fits: 一程:karst 內一個基準入口、一份測試、一次雲端計時回執
dependsOn: []
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依 strategy/specs/日更規模化與架構加深-執行計劃-v1.md §三 1。在 karst/ 內加通用基準入口(成員數、每來源延遲、失敗率由參數傳入,用假客戶端,不連外網),逐階段量度 refresh_scope 的取源、序列重建、plan_update、checkpoint 耗時與記憶體;另以雲端現行 daily-monitoring 十隻實跑一次(只讀,不記 check、不推進窗口若工具允許;否則說明)取得逐階段真實耗時。結果寫 cards/runs/daily-scale-2026-09-23/baseline.json。程式只住 karst/,代號與日期由參數傳入,不寫一次性腳本(D-180)。

## 驗收條件

- [ ] 基準入口可用 N=10、50、200 假成員跑出逐階段耗時,並有一份定向測試
- [ ] 雲端十隻逐階段真實耗時入回執,註明哪些階段隨成員數線性增長
- [ ] 回執列出 200 隻的推算耗時及主要瓶頸排序

## 結果

## 留言
