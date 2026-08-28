---
id: KARST-053
title: 運行詳情頁修正:運行選單顯示策略與參數集而非編號、掃描格運行不入選單、圖例可點隱藏基準線、刪說明句
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-049]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶 2026-08-28 過目運行詳情頁後三點意見(原話:「Can not using randon number index?」「no need such description」「Is it possible to turn off the QQQ and SPY in the chart?」)。要做:(1) 運行選單每項顯示「策略名 · 參數集名與版本 · 期間 · 跑於日期」,運行編號只在明細內小字;掃描格產生的運行不入此選單(它們在參數掃描頁看),選單列正式運行,現有兩個示例運行必須在列;(2) 刪走圖表下那句「3 條線同以 2015-01-02 為基期 100・曲線上的箭嘴……」說明文字;(3) 圖例每項可點,點一下隱藏該線、再點顯示,QQQ/SPY/策略淨值皆可。如何區分「掃描格運行」與「正式運行」以定義庫現有欄位為準(例如是否由掃描運行器產生),若欄位不足在票上講明用了什麼判準,不改庫。

## 驗收條件

- [ ] 運行選單顯示策略·參數集·期間·日期,不顯示編號;兩個示例運行在列,掃描格運行不在列
- [ ] 圖表下說明句已刪
- [ ] 圖例可點隱藏/顯示 QQQ、SPY 與策略線
- [ ] 既有測試全過

## 結果

## 留言

### agent:主agent · 2026-08-28 21:14
用戶 2026-08-28 追問後定義收窄(依用戶原話「Is it like a monte carlo, and actually the 3000+ is counted as 1 run? But only the best outcome should be shown?」推出):運行清單只列正式運行(示例運行、用戶自行重跑);掃描格產生的運行一律不入運行清單。掃描不是蒙地卡羅,是參數格逐格真跑;作為一件事它是「一次掃描」。
