---
id: KARST-046
title: 「同名同值沿用舊版」收歸唯一入口一處,策略層兩份相同實作刪走
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-041]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

參數集「同名、同節奏、同取值即沿用舊版」這條規則自此全倉只有一份,住在唯一入口的登記服務;任何策略登記參數集都自動得到這個行為。KARST-041 指出趨勢波段與因子混合各抄了一份逐字相同的實作,違反單一定義;KARST-041 亦指出 karst/sweep/factor_mix.py 那道「先查一句」已多餘。範圍只是搬位與刪重複,不改行為。

## 驗收條件

- [ ] 唯一入口登記參數集時自動沿用同名同節奏同取值的舊版,策略層查不到第二份同樣邏輯
- [ ] karst/sweep/factor_mix.py 多餘的先查步驟刪走
- [ ] 既有測試全過,兩個示例運行編號不變

## 結果

## 留言
