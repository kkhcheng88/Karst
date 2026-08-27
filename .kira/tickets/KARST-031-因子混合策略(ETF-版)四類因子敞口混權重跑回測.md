---
id: KARST-031
title: 因子混合策略(ETF 版):四類因子敞口混權重跑回測
type: task
createdAt: 2026-08-27
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-023, KARST-027]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

因子混合策略(factor-mix strategy)自此跑得出回測:質素、價值、動能、低波四類因子 ETF 按權重混成一個組合,而 ETF 與股票走同一條可投資對象路徑,平台不為 ETF 另開一條。範圍是 v1 那個直接買現成因子 ETF 混權重的版本;自算因子分數選股列日後版本,不入本票(D-012 第 2 條)。因子命名照因子族(factor family)規矩落在「族名·具體定義」一級——族名只是分類,不是因子,版本鏈與單一定義都落在具體定義那一級(規格 1.8)。

## 驗收條件

- [ ] 四類因子 ETF 按指定權重混成一個組合,跑得出一次完整回測並交得出逐日淨值(D-012)
- [ ] ETF 與股票走同一條可投資對象路徑,適配層無為 ETF 另設的分支(D-012)
- [ ] 落庫的因子名全部在「族名·具體定義」一級,查不到單以族名登記的因子(規格 1.8)
- [ ] 四類的權重是可掃描參數,不寫死在碼裡(D-008)

## 結果

## 留言
