---
id: KARST-071
title: 選股引擎改讀因子值批次:latest_known_values 一路接上 karst.factorstore,Alpha158 值可供策略取用
type: task
createdAt: 2026-08-29
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-068, KARST-070]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

KARST-068 把 Alpha158 值遷出 factor_value 表後,選股引擎 karst/engine/selection.py 經 latest_known_values 由庫內取值那一路取不到 Alpha158;策略若要用這批因子作評分或門檻,現時接不上。範圍:把「按知情時點取最新已知因子值」這一路改為同時涵蓋 factor_value 表(小批人手值)與因子值批次(Parquet),對外介面不變;禁前視規則不變(只取知情時點 ≤ 決策時點的值,成交按可執行時點)。以現有示例運行重跑核對:兩個示例運行成績逐位不變。不改策略、不加參數預設值;只跑所涉測試檔。

## 驗收條件

- [ ] 策略經現有介面可取到 Alpha158 值(測試:一條因子在某決策日的最新已知值與 Parquet 內一致,且不取到知情時點之後的值)
- [ ] 兩個示例運行重跑成績逐位不變;karst verify 清白
- [ ] 只跑所涉測試檔

## 結果

## 留言
