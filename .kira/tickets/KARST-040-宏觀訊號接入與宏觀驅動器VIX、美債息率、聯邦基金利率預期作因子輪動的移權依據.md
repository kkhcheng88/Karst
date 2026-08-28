---
id: KARST-040
title: 宏觀訊號接入與宏觀驅動器:VIX、美債息率、聯邦基金利率預期作因子輪動的移權依據
type: task
createdAt: 2026-08-28
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-036, KARST-027]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

因子輪動的驅動器自此可以用價格以外的宏觀訊號:VIX、美國國債息率(2/5/10/30 年與曲線斜度)、聯邦基金利率與市場預期(FedWatch 的免費替代:聯邦基金期貨或 FRED 有效利率/預期序列),按知情時間接入同一套數據快照,並以矩陣式掃描這些宏觀驅動器對四隻因子 ETF 的移權效果,與 KARST-036 的價格驅動器同一張成績表比較。用戶 2026-08-28 原話「if the quant factor like qlib is not enough, you can even consider to introduce VIX, FedWatch, 美元國債 or else which could have a correlations」。範圍:一個宏觀來源適配器(yfinance 指數代號或 FRED,免費優先)、宏觀序列入快照、至少三個宏觀驅動器、報告。不裁取值。

## 驗收條件

- [ ] VIX 與至少三條美債息率序列經來源適配器入數據快照,知情時間處置寫明(收市後可得),快照編號可引用
- [ ] FedWatch 的免費替代來源列明並接入(或明文寫出為何暫不可得),不用付費數據
- [ ] 至少三個宏觀驅動器各連參數格出穩健平原報告,與價格驅動器及固定權重對照格同表比較,分三段時期列對 SPY 超額
- [ ] 驅動器仍是策略層可換件,引擎與目標比重路徑不改

## 結果

## 留言
