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
claimedBy: KARST-035-gateway
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

指定現役設定與登記共用風控規則自此都經唯一入口,而且 karst verify 核對得到:KARST-030 加了現役設定登記表、KARST-025 加了風控規則與策略引用兩表,三張表現時只能由 Python API 寫入,未有寫入者簽章,verify 掃不到——與 D-020 第 1、4 條「同一道門、繞過即揪得出」不符。範圍只是把既有登記接上命令列並納入治理清單,不改表結構、不改規則定義。

## 驗收條件

- [ ] karst params activate 一句命令指定某策略的現役設定(釘死參數集某一版),並印出生效序號
- [ ] karst risk 一類子命令列得出三條風控規則與各策略的引用
- [ ] 三張新表納入簽章治理清單,經入口寫入的列 karst verify 報清白,繞過入口直接塞入的列被揪出
- [ ] 不繞過 karst/store.py 開連線(D-027)

## 結果

## 留言
