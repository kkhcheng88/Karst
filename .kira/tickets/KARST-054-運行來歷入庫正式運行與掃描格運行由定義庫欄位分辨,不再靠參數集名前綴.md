---
id: KARST-054
title: 運行來歷入庫:正式運行與掃描格運行由定義庫欄位分辨,不再靠參數集名前綴
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-049, KARST-044]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

「這次運行是正式運行還是掃描格」自此由定義庫講,不再靠參數集名字有沒有「掃描」二字。KARST-049 登記的假設 A-006 指出:庫內沒有欄位記運行來歷,畫面靠名字前綴分辨,前綴一改掃描格就會扮成門面成績且錯得無聲。範圍:backtest_run 加一格來歷(正式／掃描格,掃描格連所屬掃描的編號),掃描運行器落庫時自動填,唯一入口登記正式運行時填正式;舊庫按現行前綴判準回填一次並在遷移記錄講明;網頁殼三頁改讀這一格;A-006 收口。表結構改動照 KARST-044 做法(SCHEMA_VERSION 遞增、就地遷移、運行編號不變、karst verify 清白)。

## 驗收條件

- [ ] backtest_run 有來歷欄位,掃描運行器與唯一入口落庫時自動填,無預設
- [ ] 舊庫回填後 4,085 格掃描與 2 次正式運行分辨正確,運行編號逐位不變,karst verify 清白
- [ ] 網頁殼分辨正式運行改讀此欄,is_sweep_run 名前綴判準刪走,A-006 收口
- [ ] 既有測試全過

## 結果

## 留言
