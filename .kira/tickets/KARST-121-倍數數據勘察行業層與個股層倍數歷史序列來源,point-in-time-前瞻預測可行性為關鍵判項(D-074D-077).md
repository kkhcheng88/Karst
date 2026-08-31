---
id: KARST-121
title: 倍數數據勘察:行業層與個股層倍數歷史序列來源,point-in-time 前瞻預測可行性為關鍵判項(D-074/D-077)
type: research
createdAt: 2026-08-31
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: scout-121
deliverable: KARST-D02
---

## 工作內容

落實 D-077 先決條件與 D-074 待辦:勘察「倍數情緒儀」要用的數據來源,不落任何策略結論,純數據勘察。要查三類序列:(1) 板塊層倍數歷史(九隻 SPDR 板塊或 GICS 板塊的 trailing P/E、forward P/E、EV/Sales 月度或週度序列,愈長愈好,目標 15 年以上);(2) 個股層倍數(S&P 500 成份股 trailing 與 forward 倍數歷史);(3) 關鍵判項:forward 分母是否 point-in-time——即「當時市場知道的預測」而非事後修正版;冇 point-in-time 的 forward 序列用於回測即前視,要明判每個來源屬邊種。候選來源(不限於此):Yardeni Research 公開圖表/數據、S&P Dow Jones 公開刊物、Damodaran 年度數據、FMP/EODHD/Tiingo 一類 API、FRED、multpl.com、WRDS/IBES(記明費用門檻)。逐源記:覆蓋層級(板塊/個股)、指標、頻率、起始年份、point-in-time 與否、知情滯後、費用、取數方式(API/爬/人手)。收尾要答三條:(a) 板塊層倍數情緒儀最遠可以誠實回測到幾多年前、用邊個來源;(b) 個股層做唔做得成、代價幾多;(c) 建議接入路線(先接邊個、點驗證)。只讀外部資料與本倉文件,不改動策略碼;下載的樣本數據放 experiments/2026-08-31-multiple-data-scout/,大檔不入 git(照 KARST-113 先例)。

## 驗收條件

- [ ] 來源對照表齊:每個來源記層級、指標、頻率、起始年份、point-in-time 與否、知情滯後、費用、取數方式
- [ ] point-in-time 判項每源明判,冇 point-in-time 的來源明寫「只可用於近年或需另補 vintage」
- [ ] 收尾三問有明確答案:板塊層最遠誠實回測年期與來源、個股層可行性與代價、建議接入路線
- [ ] 結論落檔 research/2026-08-31-倍數數據勘察.md

## 結果

## 留言
