---
id: KARST-167
title: 免費路小型股宇宙試建第一張(用戶裁決 D-152「先走免費路試建」):宇宙名單與實體主鍵對照——以證監會申報人清單(company_tickers、submissions)為底,建全美上市普通股實體表(entity_id=CIK 為主鍵、代號帶時段別名、交易所、上市/首次申報日、退市/最後申報日、SIC),以封面頁股數乘現價作近似市值標記 50 億美元以下;輸出宇宙名單 v0 與規模盤點,並回報餘下三張票(日線 OHLCV 價格庫、面板擴容、覆蓋率驗證)的規模估算
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: null
deliverable: KARST-D02
---

## 工作內容

背景:KARST-162(research/2026-09-03-小型股宇宙研究.md)量到全美小型股(<50 億美元)宇宙可覆蓋七至八成十倍股起點;用戶裁先走免費路試建(D-152);D-153 定實驗線改用 entity_id 主鍵(生產線 karst/data/freeze.py 的 ensure_entities/_ensure_ticker_period/resolve_entity_ids 已有機制,生產庫 entity+entity_ticker 表是落地樣板,讀它但不寫它);D-134 單一原料庫。先讀 162 報告全文(特別是宇宙選項、免費來源限制、A-044)、165 報告(experiments/2026-09-03-ticker-reuse/REPORT.md,代號重用與嫌疑名單)、data/sec/ 下已有的 company_tickers.json、cik-lookup-data.txt、submissions/ 快取的範圍、CONTEXT.md 宇宙相關詞條。做法:①**實體表**:以 CIK 為 entity_id;從 submissions 快取(缺的按 EDGAR 每秒 ≤10、User-Agent `Casy Limited kaho.career@gmail.com` 補抓,只入 data/sec/submissions/ 單一快取連 manifest,抓前查已有)取每個申報人的代號歷史(former names、tickers、exchanges)、首次與最後申報日、SIC、州/國家;只收美國交易所上市普通股與 ADR(剔 ETF、基金、SPAC 殼、優先股、權證、債券;規則寫入 RULES.md);②**代號時段表**:每個代號每段屬哪個 entity_id(起訖日期),已知重用(CPWR/EP/PARA)與嫌疑(SUN/COV/MEE/RAI/RTN/WRK)人手核並註明;③**近似市值**:封面頁 dei:EntityCommonStockSharesOutstanding(或 EntityPublicFloat)乘最近價(yfinance 現價,只抓一次快照,不抓歷史),標 <50 億;沒有價的標「無價」不剔;④**規模盤點**:實體總數、現役/已停止申報數、按年首次申報數、<50 億家數、有價家數、按交易所與 SIC 分佈;⑤**誠實聲明**:免費路缺退市日正本(最後申報日是代理)、基本面回溯只到 2011、市值是近似、倖存者口徑;⑥回報餘下三張票的規模估算:抓多少家 OHLCV 日線(yfinance,估時間與失敗率)、companyfacts 要補多少家、覆蓋率驗證用什麼近似。產物 data/universe/(實體表 entities.parquet、代號時段表 ticker_periods.parquet、宇宙名單 universe_smallcap_v0.csv、manifest、RULES.md)—— data/ 被 .gitignore 擋,RULES.md 與腳本用 git add -f 納入;腳本落 experiments/2026-09-03-smallcap-universe-build/;報告 research/2026-09-03-小型股宇宙v0盤點.md。

## 驗收條件

- [ ] data/universe/entities.parquet 與 ticker_periods.parquet:主鍵 entity_id=CIK;代號時段無重疊;CPWR/EP/PARA 三個重用代號各自拆段;RULES.md 寫明收錄/剔除規則
- [ ] universe_smallcap_v0.csv:<50 億美元近似市值的美國上市普通股與 ADR 名單,附 entity_id、現行代號、交易所、SIC、首次/最後申報日、近似市值、有價旗標
- [ ] 報告有規模盤點表與誠實聲明四項(缺退市正本、基本面回溯 2011、市值近似、倖存者口徑),並估算餘下三張票的規模
- [ ] 新抓只入 data/sec/submissions/ 單一快取連 manifest;不抓價格歷史;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言
