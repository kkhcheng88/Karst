---
id: KARST-066
title: 因子檢視預測力面板:逐因子逐日等級相關(IC)與滾動 ICIR,按知情時點對齊未來回報;畫面分頁先出變體等用戶揀
type: task
createdAt: 2026-08-29
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-064]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

依 research/2026-08-29-alpha158-feasibility.md 第五節與用戶 2026-08-29 裁決。範圍:(1) 一個對齊函數:由因子表與 K 線面板組出「(知情時點, 實體) → 因子值」與「(知情時點, 實體) → 未來 N 日回報」兩張表,回報起點用可執行時點(D-021)而非知情當日價;N 是參數,無預設;(2) 逐日 Spearman 等級相關(IC)、滾動 IC 均值 / 標準差(ICIR),按因子版本分組,結果可由唯一入口輸出成表;(3) 對 KARST-064 入庫的 Alpha158 真數據跑一次,結果落 experiments/(每因子 IC 均值、ICIR、樣本日數);(4) 因子檢視畫面加「預測力」分頁——這是新畫面,必須先出至少兩個版面變體並列齊畫面狀態(無數據、計算中、有結果),在票上舉手等用戶揀,落檔後才實作。不引入 alphalens。只跑自己改動所涉的測試檔。

## 驗收條件

- [ ] 對齊函數與 IC / ICIR 計算有測試(小樣本手算對照),回報起點是可執行時點
- [ ] Alpha158 真數據跑一次,experiments/ 落檔每因子 IC 均值、ICIR、樣本日數
- [ ] 畫面變體已出並舉手等用戶揀;用戶揀定後照稿實作並接真數據

## 結果

## 留言
