# MTUM 與 SPMO:資產規模(AUM)及成交金額研究

研究日期:2026-08-28

## 一、資產規模(AUM)

| 項目 | MTUM(iShares MSCI USA Momentum Factor ETF) | SPMO(Invesco S&P 500 Momentum ETF) |
|---|---|---|
| 最新 AUM(發行商事實表) | 約 290.47 億美元(截至 2026-06-30,官方 Fact Sheet) | 未取得官方最新 Fact Sheet 數字;第三方彙總(GuruFocus)顯示約 199.4 億(總資產)/198.9 億(淨資產)美元,惟未列明確切日期,另有彙總網站報約 221.9 億美元(2026-08) |
| 2025 財政年度末淨資產(SEC 年度股東報告,經審計) | 175.76 億美元(截至 2025-07-31) | 121.70 億美元(截至 2025-08-31) |
| 2021–2024 年末 AUM | 未取得(需逐年下載 SEC 大型合併申報文件,受時間所限未能完成) | 未取得(同上) |

備註:兩隻基金財政年度結算日不同——MTUM 為 7 月 31 日,SPMO 為 8 月 31 日(已在 SEC N-CSR 申報中核實)。故「最新 AUM」與「財政年度末淨資產」並非同一時點,不能直接比較增長率。

## 二、近五年日均成交金額(Average Daily Dollar Volume)

計算方法:取雅虎財經(Yahoo Finance)每日收市價(Close)乘以每日成交股數(Volume),按年(以美東時間交易日曆年劃分)取平均值。2021 年數據只涵蓋 8 月30日起(數據源限制,SPMO 亦於 2021 年 3 月才上市,故 2021 年數字僅反映下半年情況,不具全年代表性)。

| 年度 | MTUM 日均成交金額(美元) | SPMO 日均成交金額(美元) |
|---|---|---|
| 2021(部分年度,8/30 起) | 190,927,238 | 892,199 |
| 2022 | 177,626,272 | 2,110,214 |
| 2023 | 68,704,837 | 2,304,842 |
| 2024 | 148,929,396 | 54,148,912 |
| 2025 | 228,448,316 | 180,540,580 |
| 2026 年初至今(截至 8/28) | 351,602,066 | 265,194,403 |
| 最近 30 個交易日(2026-07-20 至 2026-08-28) | 430,487,378 | 284,992,359 |

最新收市價(2026-08-28):MTUM $303.06;SPMO $148.49。

## 三、資料來源

- MTUM Fact Sheet(截至 2026-06-30,官方 PDF):https://www.ishares.com/us/literature/fact-sheet/mtum-ishares-msci-usa-momentum-factor-etf-fund-fact-sheet-en-us.pdf
- MTUM 2025 財政年度股東年報(SEC N-CSR 內嵌之 Annual Shareholder Report,截至 2025-07-31):https://www.blackrock.com/us/individual/literature/annual-report/ar-mtum-en.pdf ,原始 SEC 申報:https://www.sec.gov/Archives/edgar/data/1100663/000110066325000020/primary-document.htm(iShares Trust,CIK 0001100663)
- SPMO 2025 財政年度股東年報(SEC N-CSR,截至 2025-08-31):https://www.sec.gov/Archives/edgar/data/1378872/000119312525271078/8de1d4c72fc4364.htm(Invesco Exchange-Traded Fund Trust II,CIK 0001378872)
- SPMO 第三方 AUM 彙總數字(GuruFocus,擷取日 2026-08-28):https://www.gurufocus.com/etf/SPMO/summary
- 每日收市價與成交量:Yahoo Finance Chart API(https://query1.finance.yahoo.com/v8/finance/chart/MTUM 及 .../SPMO ,range=5y, interval=1d),擷取日 2026-08-28

## 四、結論

1. 就經審計的財政年度末數字而言,MTUM(175.76 億美元,2025-07-31)的資產規模大於 SPMO(121.70 億美元,2025-08-31),惟兩者財政年度結算日不同,不宜直接比較同一時點。以最新彙總數字看,兩隻基金規模已收窄至同一量級(約 200 億至 290 億美元之間),反映 SPMO 近年資金流入速度明顯快過 MTUM。
2. 成交活躍度方面,MTUM 明顯較 SPMO 活躍——2021 至 2023 年 MTUM 日均成交金額為 SPMO 的 30 倍至 200 倍不等;但差距正急速收窄:2025 年僅餘約 1.3 倍,2026 年至今兩者已幾乎相若(MTUM 3.52 億美元對 SPMO 2.65 億美元)。
3. 兩隻基金的 AUM 與成交金額同步大幅增長,主因是動量因子策略在近兩年跑贏大市帶動資金流入;惟 2021–2024 年逐年年末 AUM 因時間所限未能從 SEC 原始申報逐一核實,現階段只能提供最新及 2025 財政年度末兩個時點的官方數字,其餘年度標註「未取得」,如需完整五年 AUM 走勢建議另行安排時間深入查核。
