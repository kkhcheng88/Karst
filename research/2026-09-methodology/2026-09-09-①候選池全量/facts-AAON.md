# AAON, Inc.(NASDAQ: AAON)事實查核

- 查核範圍:KARST-188 候選池全量篩選之下 AAON 個股資料蒐集子任務,只列事實,不下投資結論。
- 截止日:2026-09-09;股價基準日:2026-09-08。凡發佈日期在 2026-09-09 或之後的資料一律不引用。
- 查核執行日:2026-09-09。
- 公司資料:CIK 0000824142;SIC 3585(冷凍與供暖設備)。
- 貨幣單位除特別註明外均為美元。

---

## 0. 對背景數字的一項重大更正(先講,因為會影響其他各節的解讀)

任務背景給出「淨負債僅 1710 萬美元,營運現金流 TTM 8654 萬美元,淨負債/OCF 0.20 倍(財務體質健康)」。

**經查 2026 年第二季 10-Q(SEC accession 0000824142-26-000055,申報日 2026-08-10,報表期 2026-06-30)原文資產負債表,此數字對不上:**

- 現金及現金等價物(Cash and cash equivalents):**13 千美元**(即 $13,000,幾乎是零,2025-12-31 同樣是 $13,000)。
- 循環信貸額度(Revolver)未償還餘額:**435,000 千美元**(即 $435.0 百萬)。
- 另有一筆短期 NMTC 相關義務(Short-term obligations of NMTC1):7,535 千美元。
- 淨負債(未償還債務 − 現金)≈ $435.0M + $7.5M − $0.013M ≈ **$442.5 百萬**,不是 $17.1 百萬。
- 營運現金流(六個月至 2026-06-30):$54,968 千美元;資本開支(同期):$97,282 千美元(自由現金流為負)。
- TTM 營運現金流(用四個季度加總,Q3'25 至 Q2'26,依 yfinance 季度現金流表核對)$86.542 百萬,與任務背景給出的數字一致——**這一項本身沒有錯**。
- 但「淨負債/OCF」用正確淨負債重算應為 ≈ $442.5M / $86.5M ≈ **5.1 倍**,不是 0.20 倍。
- 10-Q 亦披露槓桿契約(covenant)比率:「At June 30, 2026, we were in compliance with our financial covenants…leverage ratio was 1.46 to 1.0, which meets the requirement of not being above 3 to 1.」——即公司自己按信貸協議定義計算的槓桿率是 1.46 倍(這個口徑跟 net debt/OCF 不是同一把尺,但同樣說明公司並非近乎零負債)。
- 循環信貸總額度 $600.0M,已用 $435.0M,尚餘可動用額度 $163.7M(截至 2026-06-30)。

詳見第 8 節。這一項更正的實務意義:如果candidate ranking 用的是「淨負債 $17.1M」這個數字去給 AAON 的財務體質打分,這個分數的輸入本身是錯的——真實槓桿明顯高過「近乎零負債」的印象,雖然未到危險水平(仍在契約限制之內、有循環額度可用),但不是「淨現金/低槓桿」那一類公司。

---

## 1. 為什麼跌——2026-06-01 至 2026-09-08 逐項事件表

先講結構性結論,再列逐項事件:整段下跌不是單一壞消息造成的一次性重挫,而是持續約 14 星期的陰跌,中間夾雜兩個明顯加速下跌的節點——一次是 7 月 29 日對同業 Lennox 業績的「讀出效應」(read-through),另一次是 8 月 10 日自己公佈業績、營收超預期上調指引但毛利率指引被下調。**大部分跌幅發生在 AAON 自己業績公佈(8/10)之前**,這一點值得注意。

| 日期 | 事件 | 股價反應(收市價,美元) | 出處 |
|---|---|---|---|
| 2026-06-01 | 窗口基準日 | $138.39 | yfinance 收市價 |
| 2026-06-02 | AAON 透過 8-K(Item 7.01/9.01,accession 0000824142-26-000044,申報日 2026-06-08)發佈投資者簡報,重申 2026 全年指引:營收增長 40%-45%、毛利率 27%-28%、SG&A 佔營收 14%-15%、折舊攤銷 $95-100M | 簡報本身未見即日股價異動,同一週股價持續走弱 | SEC 8-K 及其附件 investorpresentation_jun.htm |
| 2026-06-04 → 06-05 | 查不到具體單一消息 | $143.37 → $132.45(-7.6%) | yfinance |
| 2026-06-09 → 06-10 | 查不到 AAON 自己有 8-K 或業績公佈與此日期直接對應;二手來源(GuruFocus)報導 6/10 收市 $121.12,單日跌 6.7%,一週跌 18.2%,一個月跌 13.2%,但未指出具體單一觸發事件。**注意**:2025 年同一週(2025-06-10)AAON 曾開「Investor Day」並下修三年目標,單日跌 16%;2026 年同期未見 AAON 提交對應的 Investor Day 8-K(最接近的是 6/2 那份重申指引的簡報),不應把 2025 年那次事件誤植為 2026 年的解釋——這點原始資料不足以完全確認,標記為「部分查不到」 | $129.49 → $120.96(-6.6%) | GuruFocus(2026-08 前後文章引述 6/10 數字);SEC 8-K 列表交叉核對 |
| 2026-06-16 | Sidoti 把評級由 Neutral 上調至 Buy,目標價 $95(仍遠低於當時股價區間,反映的是分析員認為賣壓過度而非看好估值) | 查不到當日即市反應 | Yahoo Finance/MarketBeat(二手,經 WebSearch) |
| 2026-07-01 → 07-02 | 查不到 AAON 有對應的 8-K 或公司公告;二手來源(GuruFocus,2026-07-01 文章)報導 7/1 收市 $116.42,單日跌 8.2%,文中引述市場評論指毛利率壓力(特別是 AAON Oklahoma 分部)及估值偏高(有評論給「軟性沽售」評級,指五月以來已跌 22%,但仍「被低估」)為由 | $126.70 → $107.48(兩日 -15.2%) | GuruFocus(二手) |
| 2026-07-28(事件日)/ 2026-07-30(申報日) | AAON 委任兩名新獨立董事:Robert L. Buttermore III(Rockwell Automation 供應鏈高級副總裁)、Patrick J. Jermain(Plexus Corporation 前 CFO),同時修訂細則(bylaws) | 本身屬治理性質消息,不足以解釋隨後兩日的大跌,判斷不是主因 | SEC 8-K accession 0000824142-26-000048 |
| **2026-07-29** | **行業讀出效應**:同業 Lennox International(LII)公佈 Q2 2026 業績,營收 $1.55B(+3% YoY)不及市場預期,並下修全年 GAAP EPS 指引至中位數 $23.50(低過市場預期 4.7%),主因住宅分部(Home Comfort Solutions)受房屋市場逆風拖累,住宅台數下跌 12%;LII 股價當日重挫約 20%。AAON 同日(尚未公佈自己業績)股價同步大跌 -9.5%,判斷屬同業讀出/情緒傳染,而非 AAON 自身基本面消息 | LII 同日 -20%;AAON $93.62 → $84.76(-9.5%) | Motley Fool "Why Lennox Stock Crashed Today"(2026-07-29);StockStory/Investing.com Q2 CY2026 報導(2026-07-29) |
| **2026-08-10** | **AAON 自己公佈 Q2 2026 業績**(8-K Item 2.02,accession 0000824142-26-000052):EPS $0.69 實際 vs $0.49 市場預期(+39.7% 驚喜,按 yfinance earnings_dates),營收 $627.0M(+101.2% YoY)超預期(市場預期約 $491.5M)。全年指引:**營收增長上調至 55%-60%(原 40%-45%)、但毛利率指引下修至 25%-26%(原 27%-28%)**。屬「營收超預期上調、毛利率下修」的組合 | $94.71(8/7)→ $89.13(8/10,-5.9%)→ $85.67(8/11,再跌 -3.9%) | SEC 8-K + 業績新聞稿(liveaaonpressreleaseexs.htm);yfinance earnings_dates |
| 2026-08-12(事件日)/2026-08-13(申報日) | AAON 宣佈 Q3 2026 每股 $0.10 現金股息(8-K accession 0000824142-26-000057) | $85.12(8/12)→ $87.56(8/13,+2.9%),小幅反彈 | SEC 8-K;二手新聞標題「AAON Shares Skyrocket」用詞誇張,實際只是溫和反彈 |
| 2026-08-10 至 2026-08-19 期間 | 多間券商在業績後維持正面評級但下調目標價:Baird(Outperform 維持,$150→$135)、Oppenheimer(Outperform 維持,$145→$125)、DA Davidson(Buy 維持,$125→$105)、另一輪 Baird 更新(Buy 維持,$102→$98)——個別下調的確實日期二手文章未逐一列明,只能確認發生在業績後一至兩星期內 | 8/18 收市 $81.95(-6.9% 單日,GuruFocus);8/19 $80.89 | Benzinga「Aaon Analysts Slash Their Forecasts Following Q2 Earnings」(2026-08 中,標題頁面本身因 403 未能直接讀取全文,轉引 WebSearch 摘要) |
| 2026-08-21(事件日)/2026-08-28(申報日) | AAON 宣佈新企業識別「The Aaon Group」,AAON 與 BASX 併列雙品牌架構,聲明不涉及分部、管理層、財務申報或股票代號變動 | 前後股價續跌但無法歸因於此則消息本身:$79.34(8/21)→ $76.00(8/24,-4.2%),查不到 8/24-25 具體單一觸發消息 | SEC 8-K accession 0000824142-26-000059(exhibit tag_investorpressrelease.htm) |
| 2026-08-28 | 內部人 Matthew Shaub(Executive Vice President)公開市場買入 457 股,均價 $76.42(見第 9 節) | 屬個人交易,規模小(約 $34,930),不足以解讀為市場訊號級事件 | Form 4,accession 0000824142-26-000061 |
| 2026-09-01 → 09-02 | 查不到具體消息(9/1 為勞動節休市) | $75.87(8/31)→ $74.52(9/2) | yfinance |
| 2026-09-03 → 09-04 | 反彈,與大盤(SPY)同期同步回升,查不到 AAON 個股獨有的正面消息 | $74.52 → $79.40(+6.5%) | yfinance |
| 截至 2026-09-04 | 二手綜合報導稱「過去一個月有 1 名分析員下調評級、0 名上調」,但查不到該分析員名稱、機構及確實日期(一手來源缺失,標記查不到) | — | AAII 文章(2026-09-04 前後,二手) |

---

## 2. 最近兩季業績要點

### Q1 2026(業績發佈日:2026-05-07,8-K accession 0000824142-26-000034)

- 淨銷售額:$496.9M,YoY +54.3%(去年同期 $322.1M)。分拆:BASX 品牌(數據中心冷卻)$228.6M,YoY +72.4%;AAON 品牌 $268.4M,YoY +41.6%。
- 毛利率:25.1%,對比去年同期 26.8%。公司解釋:「unabsorbed fixed costs associated with recent capacity investments, temporary outsourcing used to support accelerated growth, and transitory price and cost timing dynamics」。
- 營業利潤:$57.1M,營業利潤率約 11.5%(按損益表數字推算)。
- 淨利:$39.8M;攤薄每股盈利 $0.48,YoY +37.1%(去年同期 $0.35)。
- 指引:重申全年營收增長 40%-45%、毛利率約 27%-28%。
- 積壓訂單(backlog):$2.1B,YoY +107.4%,創新高。CEO Matt Tobolski:「Our backlog provides exceptional visibility, particularly across the BASX-brand」。
- CFO Andy Cheung:Q1 營運現金流 $34.0M,「the highest level since the third quarter of 2024」;資本開支 $52.9M。

### Q2 2026(業績發佈日:2026-08-10,8-K accession 0000824142-26-000052)

- 淨銷售額:$627.0M,YoY +101.2%。上半年累計 $1,123.9M,YoY +77.4%。
- 毛利率:24.3%,對比去年同期 26.6%;上半年累計 24.7%,對比去年同期 26.7%。
- 營業利潤:$68.9M,營業利潤率 11.0%,YoY +192.1%(利潤金額增速,非利潤率本身)。上半年累計營業利潤 $125.9M,利潤率 11.2%。
- 淨利:$56.7M;Q2 攤薄每股盈利 $0.68,YoY +257.9%;上半年累計攤薄每股盈利 $1.15。
- 指引變動:**營收增長指引上調**至 55%-60%(原 40%-45%);**毛利率指引下調**至 25%-26%(原 27%-28%);SG&A 佔比指引改善至 13%-14%(原 14%-15%)。
- CEO Matt Tobolski 論毛利率:「The pace of growth and capacity ramp is creating near-term margin pressure, but drivers are known...path to improvement is clear.」
- CFO 論現金流:「Operating cash flow totaled $55.0 million for the six-month period, a significant improvement compared with a $31.0 million use of cash」(去年同期)。

### 兩季合觀的重點

- 營收增速在加快(Q1 +54.3% → Q2 +101.2%),不是放緩,主要由 BASX(數據中心冷卻)分部帶動,同時 AAON 本品牌也有雙位數增長。
- 毛利率連續兩季按年下滑(Q1 26.8%→25.1%,Q2 26.6%→24.3%),公司給出的解釋一致:產能爬坡(尤其 Memphis 新廠)未完全攤薄固定成本、暫時外判產能、通脹成本壓力。
- 全年指引方向是「營收愈開愈高、毛利率愈開愈低」——這正正是股價在兩次業績日附近繼續下跌而非受業績帶動反彈的核心線索(見第 1、5 節)。
- **BASX 併購背景澄清**:BASX 於 2021 年底已併入 AAON(交易方於 2021 年 11 月/12 月達成,對應 8-K 已於 2021-12 提交),即 2025、2026 兩年的 YoY 比較基期都已包含 BASX,並非「今年新併購拉高基期」的效應。101.2% 的按年增速主要反映(a)BASX 業務本身受惠 AI 數據中心冷卻需求真實加速擴張,及(b)2025 年同期基數偏低(2025 Q1 營收 $322.1M 與 2025 Q2 營收約 $311.6M 幾乎持平,顯示 2025 年本身是偏弱的一年)兩者疊加,不是單純的併購並表效應。

---

## 3. 同業有沒有一齊跌(2026-06-01 至 2026-09-08,yfinance 收市價)

| 代號 | 公司 | 窗口報酬率 |
|---|---|---|
| AAON | AAON | **-42.1%** |
| LII | Lennox International | -21.6% |
| CARR | Carrier Global | -8.3% |
| TT | Trane Technologies | +0.3% |
| SPY | (大盤對照) | +1.5% |
| JCI | Johnson Controls | +9.1% |
| WTS | Watts Water Technologies | +18.5% |

**結論:不是全行業齊跌。** 只有 AAON 和 LII(兩間都是以住宅/輕商用屋頂機組 rooftop unit 為主力產品線的廠商)明顯下跌,而 Trane、Johnson Controls、Watts Water 這段期間反而上漲,Carrier 只是溫和下跌。任務背景把 AAON 標為「行業殺」,按這組數據看不成立——更準確的描述是「AAON + LII 這一小撮(住宅/輕商用線 + AAON 額外疊加數據中心冷卻執行風險)在跌,大型多元化 HVAC 廠(TT/JCI)及水務科技(WTS)這段期間表現不差」。第 1 節已確認 7/29 LII 業績確實對 AAON 造成同日讀出式下跌,但 AAON 自己 -42.1% 遠超 LII 的 -21.6%,即 AAON 除了分享 LII 那部分行業性(住宅需求)風險外,還疊加了自己獨有的因素(毛利率指引下修、產能爬坡執行風險)。

---

## 4. 護城河四項證據(只列證據,不評級;找不到寫查不到)

出處:AAON FY2025 10-K(SEC accession 0000824142-26-000005,申報日 2026-03-02,報表期 2025-12-31)Item 1 業務及 Item 1A 風險因素章節。

**無形資產/品牌**
- 自我定位:「leader in heating, ventilation, air conditioning, and liquid cooling solutions」,但未披露具體市佔率百分比(查不到量化市佔率)。
- 商標:AAON Alpha Class™、VCCX Controller 等,10-K 稱「certain of which are material to its business」。
- 專利:「several patents that relate to the design and use of our products」,但公司自己承認「no single patent is material to the overall conduct of our business」,專利年期 20 年,到期日介乎 2032 至 2039 年。

**轉換成本**
- 訂單模式為「build to order」,每台機組出廠前已按客戶規格預先設定,交貨期(AAON 品牌)18-26 星期,BASX 訂單須提前數月下單——訂單前置期本身構成一定程度的客戶黏性/轉換摩擦。
- 保養/保用期:零件與控制器 1 年(或出貨後 18 個月);壓縮機 5 年;鋁化鋼熱交換器 15 年;不鏽鋼熱交換器 25 年;另有 6 個月至 10 年不等的延長保用可供選購。
- 未見任何披露顯示客戶簽有長期採購合約鎖定(查不到合約年期式的轉換成本證據);與供應商的合約反而較明確——「cancellable and non-cancellable contracts with our major suppliers for periods of six to 18 months」。

**網絡效應**
- 查不到——業務模式(獨立銷售代表網絡)不構成典型網絡效應(即用戶增加不會令產品對其他用戶更有價值),10-K 本身也沒有以網絡效應語言描述其業務。

**成本優勢/規模經濟**
- 公司自我定位是「mass semi-customization」,即「the cost efficiency of scaled production with the precision of individual customization」。
- 生產基地:Tulsa(主要)、Memphis、Parkville(MO)、Longview(TX,AAON Coil Products)、Redmond(OR,BASX)。
- 垂直整合:自製鈑金加工、控制器、盤管;外判壓縮機、馬達等主要零件,10-K 稱「not dependent upon any one source for raw materials or the major components」。
- 研發投入:2025 年 $58.2M、2024 年 $47.3M、2023 年 $43.7M,持續上升。
- **但用實際毛利率/營業利潤率跟同業比較,AAON 目前(TTM,yfinance)並不佔優**:AAON 毛利率 25.6%、營業利潤率 11.0%,而 LII 33.3%/22.9%、TT 35.4%/19.3%、JCI 36.7%/15.9%、WTS 48.9%/20.9%,只有 CARR 24.7%/13.1% 跟 AAON 相若。即現階段(受產能爬坡拖累)AAON 是同業當中毛利率最低的一員之一,跟「成本優勢」的敘事現時對不上——這是否只是暫時性(公司自己說是產能爬坡的過渡期)還是結構性,10-K 本身未能證明,需留待後續季度毛利率是否如指引所講回升去驗證。

**客戶集中度**(額外查到,原十項未明確要求但屬護城河相關證據)
- 2025 年有 3 名客戶佔營收 ≥10%,2024 年 2 名,2023 年 3 名(10-K 披露,未寫出客戶名稱及具體百分比)。
- 10-K 自己承認的風險:「Certain competitors with greater financial resources than us have targeted some of our third-party representatives for exclusive sales channels」——即獨立代表網絡本身是有被競爭對手挖角風險的,不是穩固的護城河來源。

---

## 5. 市場現在最擔心哪一項

集中在**毛利率能否隨產能爬坡完成而回升**,而不是需求本身。具體引用:

- Simply Wall St,標題「AAON (AAON) Stock Faces Margin Reset After Breakneck Revenue Growth」,發佈日 2026-08-11。文中原話:「consolidated gross margin slipped to 24.3% and full year margin guidance was cut to 25% to 26%」,並引述看淡一方觀點:「record backlog and data center growth fail to translate into clean margins and strong cash generation」。
- Barchart,標題「AAON's Data Center Windfall Could Rewrite What HVAC Margins Are Supposed to Look Like」(發佈日期經 WebFetch 未能穩定讀取,標題本身已反映同一主題,列作輔證,不作為獨立日期來源)。
- Benzinga,標題「Aaon Analysts Slash Their Forecasts Following Q2 Earnings」——多間券商(Baird、Oppenheimer、DA Davidson)在維持正面評級(Outperform/Buy)之下集體下調目標價,反映的是「方向仍看好,但估值錨要降」而非「基本面轉差」的態度(細節見第 1 節表格)。
- 交叉印證:10-Q 本身在流動性章節主動披露槓桿契約比率 1.46 倍(見第 0、8 節),顯示公司自己也意識到市場對槓桿/現金流有疑慮,主動在文件中強調「in compliance」。

---

## 6. 下一項能改變估值的證據

| 項目 | 預期日期 | 出處 |
|---|---|---|
| Q3 2026 業績 | **2026-11-05**(盤前) | yfinance calendar(Earnings Date: [2026-11-05];EPS 市場預期 $0.56,收入預期區間 $584.1M-$606.9M) |
| 除息日/派息日 | 除息 2026-09-04;派息 2026-09-25,每股 $0.10 | yfinance calendar;SEC 8-K accession 0000824142-26-000057 |
| A2L 冷媒法規落地進度 | 屬全行業持續過渡,非單一裁決日期——查到的是「2026 年超過 90% 新裝住宅系統已用 A2L(R-454B)冷媒,新規令設備成本上升約 15%-30%」的行業性描述,無法定位到單一「裁決日」(查不到 AAON 個股層面的單一法規日期,只有行業性、持續性的描述) | 二手行業報導(ACHR News、Contracting Business、HVAC Know It All 等,經 WebSearch 綜合,非 SEC 一手來源) |
| BASX 液冷 vs 風冷訂單組合披露 | 沒有固定日期,通常隨季度業績新聞稿或投資者簡報不定期披露(下一次較可能在 11/5 Q3 業績或年度投資者簡報中出現) | 見第 10 節 |
| 年度 Investor Day | 歷史上約在每年 6 月上旬舉行(2025-06-10 曾舉辦並下修三年目標;2026 年 6 月是否有同等規模活動查不到明確一手確認,只查到 6/2 一份重申指引的簡報),若循歷史模式,下一次應在 2027 年 6 月前後,不屬「下一個」近期催化劑 | 二手報導(Seeking Alpha 談 2025 年那次) |
| 住宅開工/建築許可等宏觀數據 | 美國人口普查局「新屋開工」報告例行每月中旬發佈(約每月 17-19 日),下一次落在窗口截止日後,屬持續性數據源,非單一事件 | 一般公開發佈時間表(未逐月核對具體日子,查不到 AAON 個股對應的單一日期) |

---

## 7. 資本週期(同業資本是否在退出)

**數據中心冷卻這一段(BASX 所在市場):資本在明顯流入,不是退出。**

- Vertiv:2026 年宣佈擴大意大利 Tognana 廠產能,目標年底前將該地區冷卻器產能翻倍,並預計 2027 年在美國增加液冷產能。
- Modine:一名策略客戶簽署涵蓋 2027-2029 年、逾 $4B 規模的 Airedale 冷卻產品長期產能協議,並支付 $165M 前期款以支持產能擴充;2026 財年第三季數據中心銷售按季增長 31%。
- Munters:SEK 2.0B 規模的模組化 AI 冷卻訂單,預計 2027 年初開始交付。

以上三間都是在**擴產、加碼**,不是退出或破產,反映數據中心冷卻這一段的競爭強度正在上升(進入的資本增加),而不是「同業退場、AAON 撿到剩餘市場」的敘事。

**傳統住宅/輕商用 HVAC(AAON 品牌本身所在的核心市場)這一段:資料不足。** 只查到 Carrier、Trane、Lennox 2026 年產品加價 6%-10% 不等的價格行動報導,查不到具體的產能擴張/退出或破產訊息,不足以判斷這一段的資本週期方向,標記「資料不足」,不強行用印象填空。

---

## 8. 負債與現金(以 10-Q/10-K 為準,交叉核對 yfinance TTM)

一手來源:2026 年 Q2 10-Q(SEC accession 0000824142-26-000055,報表期 2026-06-30)。

| 項目 | 2026-06-30 | 2025-12-31(對照) |
|---|---|---|
| 現金及現金等價物 | $13 千 | $13 千 |
| 循環信貸(長期債務)未償還餘額 | $435,000 千 | $398,320 千 |
| 短期 NMTC 相關義務 | $7,535 千 | $7,535 千 |
| 經營租賃負債(流動部分,計入應計負債) | $3,385 千 | $3,262 千 |
| 經營租賃負債(非流動部分,計入其他長期負債) | $13,699 千 | $15,529 千 |
| 融資租賃負債 | 10-Q 未見獨立披露(查不到) | 同左 |

- 循環信貸總額度:$600.0M;已動用 $435.0M;尚餘可動用 $163.7M(截至 2026-06-30);另有備用信用證 $1.308M 佔用額度。
- 槓桿契約比率(公司按信貸協議定義自行計算):1.46 倍,「meets the requirement of not being above 3 to 1」。
- 近四季(TTM,Q3'25-Q2'26)營運現金流,按 10-Q/10-K 逐季數字加總:Q3'25 $12.256M + Q4'25 $19.318M + Q1'26 $33.994M + Q2'26 $20.974M = **$86.542M**(與任務背景給出的 TTM OCF 數字一致)。
- 六個月至 2026-06-30 資本開支:$97.282M(對比去年同期 $82.515M),自由現金流為負。
- **淨負債重算:≈ $442.5M(見第 0 節),淨負債/TTM OCF ≈ 5.1 倍**,與任務背景給出的「0.20 倍、財務體質健康」的描述有重大出入,以 10-Q 一手數字為準。

---

## 9. 內部人買賣(近六個月,約 2026-03-09 至 2026-09-09,SEC Form 4,CIK 0000824142)

查核方法:逐份下載並解析窗口內全部 41 份 Form 4 申報(申報日 2026-03-09 至 2026-09-09)之原始 XML,篩選交易代碼(Transaction Code)。

**唯一一筆公開市場買入(Transaction Code = P):**

| 姓名 | 職銜 | 交易日 | 股數 | 價格 | 申報日 | Accession |
|---|---|---|---|---|---|---|
| Matthew Shaub | Executive Vice President | 2026-08-28 | 457 股 | $76.42 | 2026-08-31 | 0000824142-26-000061 |

金額約 $34,930,規模不大。

**窗口內其餘全部交易均非公開市場買入**,分類如下(不逐筆重複列出,已於原始資料存檔):
- 期權行使(Code M):多筆,涉及 Rebecca Thompson(CAO/CFO)、Gary D Fields、Casey Kidwell、Gordon Douglas Wichman 等,行使後多數同日以 Code S 賣出對沖。
- 稅務代扣賣出(Code F):多筆,金額較小,屬股票獎勵歸屬時的預扣稅款處理,不計入「買賣」。
- 股票獎勵/歸屬(Code A):多筆,主要是董事會成員(Norman H Asbjornson、Bruce Ware、David Raymond Stewart、A H McElroy II、Stephen O LeClair、Caron A Lawhorn、Angela Kouplen 等)例行的董事酬金股份發放,非公開市場買入。
- 贈與(Code G):Norman H Asbjornson 兩筆,2026-05-29 及 2026-09-01。

按 yfinance,內部人合計持股比例約 16.73%(heldPercentInsiders),機構持股約 82.05%。

---

## 10. 「技術替代」爭議

**適用**——爭議點在數據中心冷卻這一段:液冷(liquid cooling)對風冷(air cooling)的替代。

- 背景:AAON 透過 BASX 品牌參與數據中心冷卻市場,歷史上以風冷(air-side)方案為主。隨 AI 運算晶片功耗上升,高密度機櫃愈來愈需要液冷(direct-to-chip 或浸沒式)方案,若 AAON/BASX 在液冷產品上落後,存在被液冷專門廠商(例如 Vertiv)蠶食市佔的風險。
- 查到一項二手綜合陳述(經 WebSearch,引述 AAON 投資者簡報內容,非我直接於一手 PDF 中讀出):AAON 預期數據中心冷卻整體市場到 2028 年液冷與風冷佔比將達到約 60% 液冷 / 40% 風冷(歷史上以風冷佔絕大多數)。**這項數字未能一手核實**——嘗試直接讀取 AAON 於 2025-09-18 向 DA Davidson 提交的投資者簡報 PDF(investors.aaon.com/hubfs/Documents/IR%20Documents/IR%20Presentations/2025/DA%20Davidson%20September%202025.pdf),但該檔案是圖片掃描格式,無法擷取文字內容核對,標記為「二手來源、未能一手核實」。
- 已一手核實的背景證據(非窗口內事件,屬歷史脈絡):AAON 曾於 2024-10-25 發佈新聞稿,宣佈獲得單一數據中心客戶約 $174.5M 的液冷相關訂單(prnewswire.com,發佈日期已核實)。這證明 AAON 並非純風冷廠商、確實有液冷產品線在出貨,但無法從這一則新聞判斷液冷佔其數據中心業務的比重趨勢。

**能區分「替代尚未反映」與「實際替代有限」的可觀察指標**:BASX 分部液冷訂單/積壓訂單佔比隨季度變化的趨勢。若這個比例持續上升且與管理層披露的產能擴張(例如新廠專門產能)同步,代表 AAON 正在成功參與替代(即「替代對 AAON 是機會,不是威脅」);若液冷訂單佔比長期停滯在低位而風冷仍佔絕大多數,則代表「市場擔心的替代」尚未在 AAON 的訂單結構中兌現,存在被純液冷廠商取代的風險尚未證偽。

**披露位置與頻率**:目前未見 AAON 有固定格式或固定頻率披露液冷/風冷訂單分拆比例,多數是在個別客戶訂單新聞稿(如上述 2024-10-25 那則)或投資者簡報中間歇性提及,不是每季度業績新聞稿的固定欄目。下一次較可能出現披露的時點是 2026-11-05 Q3 業績或伴隨的投資者簡報,但不確定是否會包含這項細分數據(查不到公司對此的固定披露承諾)。

---

## 附註:資料來源與限制

- SEC 一手文件全部經 `data.sec.gov` 及 `www.sec.gov/Archives` 直接下載,HTTP header 帶 `User-Agent: Karst Research (VANESSALAU@vl-lawyers.com)`(Python urllib)或透過 WebFetch 工具讀取(WebFetch 本身無法自訂 header,但對 www.sec.gov/Archives 靜態文件未見被拒)。
- Form 4 原始資料已存檔於 `C:\Users\Kaho\AppData\Local\Temp\claude\C--projects-Karst\d2e5d32d-fb0a-455e-a4f0-b5414e1a7c69\scratchpad\form4_transactions.csv`(41 份申報、83 筆交易明細),供覆核之用,不屬正式研究倉一部分。
- 部分二手新聞(GuruFocus、Simply Wall St、Benzinga 等)因原始頁面無法穩定用 WebFetch 完整讀取(例如 Benzinga 回應 403),改以 WebSearch 摘要轉引,已在對應段落註明,查核強度低於一手 SEC 文件,使用時應留意。
- 本次 WebSearch 額度已在查核尾段用盡(單一 session 上限 200 次),第 10 節「$174.5M 訂單」的液冷/風冷佔比投資者簡報這一項因額度耗盡未能再深挖確認,已如實標記查不到/未能一手核實,沒有用訓練資料填補。
