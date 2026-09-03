---
id: KARST-167
title: 免費路小型股宇宙試建第一張(用戶裁決 D-152「先走免費路試建」):宇宙名單與實體主鍵對照——以證監會申報人清單(company_tickers、submissions)為底,建全美上市普通股實體表(entity_id=CIK 為主鍵、代號帶時段別名、交易所、上市/首次申報日、退市/最後申報日、SIC),以封面頁股數乘現價作近似市值標記 50 億美元以下;輸出宇宙名單 v0 與規模盤點,並回報餘下三張票(日線 OHLCV 價格庫、面板擴容、覆蓋率驗證)的規模估算
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: universe-167
deliverable: KARST-D02
closed: 2026-09-03
---

## 工作內容

背景:KARST-162(research/2026-09-03-小型股宇宙研究.md)量到全美小型股(<50 億美元)宇宙可覆蓋七至八成十倍股起點;用戶裁先走免費路試建(D-152);D-153 定實驗線改用 entity_id 主鍵(生產線 karst/data/freeze.py 的 ensure_entities/_ensure_ticker_period/resolve_entity_ids 已有機制,生產庫 entity+entity_ticker 表是落地樣板,讀它但不寫它);D-134 單一原料庫。先讀 162 報告全文(特別是宇宙選項、免費來源限制、A-044)、165 報告(experiments/2026-09-03-ticker-reuse/REPORT.md,代號重用與嫌疑名單)、data/sec/ 下已有的 company_tickers.json、cik-lookup-data.txt、submissions/ 快取的範圍、CONTEXT.md 宇宙相關詞條。做法:①**實體表**:以 CIK 為 entity_id;從 submissions 快取(缺的按 EDGAR 每秒 ≤10、User-Agent `Casy Limited kaho.career@gmail.com` 補抓,只入 data/sec/submissions/ 單一快取連 manifest,抓前查已有)取每個申報人的代號歷史(former names、tickers、exchanges)、首次與最後申報日、SIC、州/國家;只收美國交易所上市普通股與 ADR(剔 ETF、基金、SPAC 殼、優先股、權證、債券;規則寫入 RULES.md);②**代號時段表**:每個代號每段屬哪個 entity_id(起訖日期),已知重用(CPWR/EP/PARA)與嫌疑(SUN/COV/MEE/RAI/RTN/WRK)人手核並註明;③**近似市值**:封面頁 dei:EntityCommonStockSharesOutstanding(或 EntityPublicFloat)乘最近價(yfinance 現價,只抓一次快照,不抓歷史),標 <50 億;沒有價的標「無價」不剔;④**規模盤點**:實體總數、現役/已停止申報數、按年首次申報數、<50 億家數、有價家數、按交易所與 SIC 分佈;⑤**誠實聲明**:免費路缺退市日正本(最後申報日是代理)、基本面回溯只到 2011、市值是近似、倖存者口徑;⑥回報餘下三張票的規模估算:抓多少家 OHLCV 日線(yfinance,估時間與失敗率)、companyfacts 要補多少家、覆蓋率驗證用什麼近似。產物 data/universe/(實體表 entities.parquet、代號時段表 ticker_periods.parquet、宇宙名單 universe_smallcap_v0.csv、manifest、RULES.md)—— data/ 被 .gitignore 擋,RULES.md 與腳本用 git add -f 納入;腳本落 experiments/2026-09-03-smallcap-universe-build/;報告 research/2026-09-03-小型股宇宙v0盤點.md。

## 驗收條件

- [x] data/universe/entities.parquet 與 ticker_periods.parquet:主鍵 entity_id=CIK;代號時段無重疊;CPWR/EP/PARA 三個重用代號各自拆段;RULES.md 寫明收錄/剔除規則
- [x] universe_smallcap_v0.csv:<50 億美元近似市值的美國上市普通股與 ADR 名單,附 entity_id、現行代號、交易所、SIC、首次/最後申報日、近似市值、有價旗標
- [x] 報告有規模盤點表與誠實聲明四項(缺退市正本、基本面回溯 2011、市值近似、倖存者口徑),並估算餘下三張票的規模
- [x] 新抓只入 data/sec/submissions/ 單一快取連 manifest;不抓價格歷史;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言

### agent:universe-167 · 2026-09-03 08:47
免費路小型股宇宙 v0 建成。報告 research/2026-09-03-小型股宇宙v0盤點.md;規則正本 data/universe/RULES.md(跑數前獨立 commit e8343bb,跑數後兩項更正記在第八節);收檔 commit 974b4c3。

**誠實聲明四項**:①缺退市正本——名單由今日的證監會代號對照表建成,5,257 家之中 5,255 家仍在申報、只有 2 家已停止,不是市場沒有死人,是這個來源根本不列死人;「最後申報日」是停止申報日不是除牌日。②基本面只回溯 2011(XBRL 分階段實施)。③市值是近似值:封面頁在外股數 × 2026-09-03 一個現價快照,答「今日有多大」,不是任何歷史時點的市值。④倖存者口徑:由這份名單算出來的任何基礎率不與文獻或付費口徑比較(D-152 第 2 條)。

**規模**:起點 8,001 個 CIK / 10,391 個代號 → 收錄 5,257 家實體(納斯達克 3,100、紐交所 2,138、CBOE 19);現役 5,255 / 停止申報 2;取得到封面頁股數 4,368(83.1%)、取得到現價 5,251(99.9%)、算得出近似市值 4,365;**近似市值 < 50 億美元 3,188 家**(剔走信託型 ETP 之後 3,114)。近似市值中位 9.54 億美元;小型股名單自己的中位 3.47 億、四分一在 6,400 萬以下——與 KARST-162 量到的十倍股起點分佈形狀相似。

**代號主鍵(D-153)**:entities.parquet 5,257 列以 CIK 作 entity_id;ticker_periods.parquet 5,952 段,**重疊 0**。CPWR/EP/PARA 三宗確證重用各自拆兩段,SUN 一宗嫌疑同樣切斷。**EP 與 PARA 不可以用「前手最後申報日」作切斷點**——那兩個 CIK 至今仍在申報(El Paso 以債券發行人身分、Paramount 舊實體合併後未收檔),照用會把切斷點推到 2026 年;改用 KARST-165 記的成分期離場日。嫌疑六宗之中 COV/MEE/RAI/RTN/WRK 今日已無持有人,不入本宇宙,無段可拆。後手那一段的生效起是**下限**(前手釋出那日),真正接手日沒有免費正本。

**兩項規則更正(跑數之後改的,不是調參)**:①I4 由「只收 entityType=operating」放寬到「收 operating 與 other」——證監會給外國私人發行人的 entityType 是 other,原規則等於把全部 ADR 一次過剔走,與票面「收美國交易所上市普通股與 ADR」直接衝突;改後實體由 4,153 升到 5,257,外國申報人由 129 升到 1,233。②信託型 ETP(SPDR Gold、iShares Silver、USO、Bitwise Dogecoin 一類)的 SIC 是 6221,不在 E1 剔除之列,而且它們真的交 10-K 所以 I3 攔不住;規則已凍結,v0 只加 etp_suspect 標旗不剔(91 家,小型股 73 家),**建議 v1 把 6221 加入 E1**。

**收窄 KARST-162 一句**:外國申報人不是「由證監會免費資料建的宇宙系統性看不見」,是「看得見但算不出市值」——1,233 家全部入得到名單,但只有 68.2% 取得到封面頁股數(美國本土 87.6%)。

**138 家十倍股有 135 家在名單內**(缺 CPWR、FMCC、FNMA,三個都有明確理由)。**這不是覆蓋率**:那 138 家全部活到今日,而名單就是由今日仍然掛牌的公司建成,兩邊是同一個倖存者池。真正的覆蓋率要用 t0 市值答,KARST-162 已量過 U2 是 70.3%–85.5%。

**原料治理(D-134)**:申報索引現時全部住在 data/sec/submissions/ 單一快取,8,012 份、663 MB、逐份有 SHA256 與 manifest 一行。本票新抓 7,376 份(每秒 8 個請求、15.4 分鐘、零失敗),由其他實驗目錄複製回 513 份,補寫 119 份從未登記過的 manifest。**順帶記一筆**:申報索引這一格的 D-134 從來沒有落地過——五個實驗目錄各存一份副本(silent-revisions 334 MB);本票沒有動別人的檔,已落運作觀察簿。本票**沒有抓任何價格歷史**。

**餘下三張票的規模估算**(報告第七節):日線 OHLCV 5,947 個代號、45–90 分鐘、失敗率 1–3%、落地 300–600 MB(**必須小批加退讓**:本票第一次用 200 個一批無退讓,成功率只有 32%;改 40 個一批加 1.2–2 秒退讓升到 99.3%)。companyfacts 補抓 4,649 家、10–15 分鐘、失敗率近零、落地 7–16 GB(注意 1,233 家外國申報人的 companyfacts 多數是空的)。覆蓋率驗證零新抓、幾分鐘,用 KARST-162 已算好的 t0 市值。

**新記假設 A-045**:封面頁股數乘一次現價的近似市值,足以劃準 50 億這條線;若假則小型股名單要重出、覆蓋率驗證的數字不可信。**CONTEXT.md 新增詞條**「停止申報日 / last filing date」。

生產庫 karst.sqlite 全程只讀,SHA256 首 16 位開工與收工皆為 b168e9f45b578cf9。
