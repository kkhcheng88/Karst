---
id: KARST-038
title: 共用風控層與現役設定的程式路徑改行唯一入口,全庫核對清白
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-035, KARST-028]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

策略程式登記風控規則、引用風控規則、指定現役設定,自此全部經唯一入口的服務層而非直接呼叫庫層 API,令真實策略跑完後 karst verify 報全庫清白。KARST-035 把三張表納入簽章核對後,KARST-028 趨勢波段跑完即報 6 條未簽章列,全部來自共用風控層直接寫庫;karst/risk/registry.py、karst/metrics 說明例子與 tests/test_risk_layer.py 亦屬同類路徑。範圍只是改呼叫路徑,不改表結構、不改規則定義、不改任何取值。

## 驗收條件

- [ ] 趨勢波段與因子混合策略各重跑一次示例運行後 karst verify 報全庫清白,運行編號與成績不變
- [ ] karst/ 內查不到繞過入口直接寫 active_setup、risk_rule、strategy_risk_ref 三表的程式路徑(測試除外須經入口)
- [ ] 既有測試全部照過

## 結果

## 留言
