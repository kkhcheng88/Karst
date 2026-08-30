# OSAP 免費個股層面特徵值能否頂替 EDGAR 做基本面選股:覆蓋期、宇宙、識別碼、財報條數、時點口徑與代價

- 票號:KARST-098
- 日期:2026-08-30
- 用途:回答漏斗第一層(基本面選股)今日有沒有數據可用,以及 SEC EDGAR 數據線(D-041)應否押後。
- 性質:研究票。只查證與落檔,沒有改動任何既有程式,沒有寫入 `data/`。

---

## 摘要(先講結論)

1. **今日夠做基本面選股的第一輪實測,但只夠做到 2024 年 12 月為止的歷史測試,不夠做今日的實盤選股。** OSAP 最新一期是 2025 年 10 月釋出,官方明文寫住「數據到 2024 年 12 月」——即是今日(2026-08-30)手上最新的一個橫斷面,已經是 **20 個月前**的數字。
2. **識別碼這一關過到,但要靠我們自己接。** OSAP 只給 CRSP 的 `permno`,官方**沒有**提供 permno 對 ticker / CIK 的對照表(本票逐個位置查過,包括官方雲端硬碟的完整目錄)。本票用價格指紋反查,實跑把現役快照 **603 個代號對上了 546 個(90.5%)**,零重複配對,並用 8 隻已知答案的股票驗證無誤。
3. **對不上的 57 個當中,42 個是 OSAP 本身沒有收——以房地產信託(REIT)為主,再加一隻 ETF。** 這不是我們配錯,是 OSAP 的宇宙篩選(只收 CRSP 股份代碼 10/11/12)把 REIT(代碼 18)與 ETF(代碼 73)排走了。標普 500 裡面約 30 隻 REIT 因此拿不到基本面因子值。餘下 15 個是 2023 年後才上市/分拆的新公司,超出 OSAP 的數據邊界。
4. **財報與分析師類共 117 條**(會計 99 + 分析師 18),純價量類 55 條(價格 42 + 交易 13)。這 117 條就是第一層選股可以直接用的材料。
5. **最大的一項代價:這批數字不是「當年真正看得見的數字」。** OSAP 用的是已經重述過的標準 Compustat 年報檔,加一個機械式的 6 個月滯後。即是說,一間公司事後修訂過的帳目,會被當成當年就知道。歷史測試因此有機會偏樂觀,而且**這一項我們自己無法還原**——要真正的「當年口徑」,只有自己由 EDGAR 逐份申報去砌。
6. **建議:EDGAR 數據線不要取消,但可以押後。** 先用 OSAP 跑第一輪歷史實測(便宜、快、值是對方算好的),等實測證明基本面選股這條路真的有東西,再投資 EDGAR 去解決兩個 OSAP 解決不了的問題:實時性(20 個月滯後)與真正的知情時點口徑。

---

## 一、七問逐條答

### 問 1:`firm_char` 寬表的實際覆蓋期、更新頻率、最近一次更新日

**官方說法**(出處:[openassetpricing.com/data](https://www.openassetpricing.com/data/)):

> "209 predictive firm-level characteristics in wide format, signed so future mean returns increase in characteristics (1.6 GB zipped csv)"

> "Note that most of the current data run through **December 2024**. Predictors based on option-implied volatility currently only run through December 2022 (and are taken from the 2023 release) due to revisions to the underlying data."

官方釋出說明正本(本票實際下載並讀出全文,`Release Notes 2025.10.docx`,Google Drive 檔案 id `18b77C1ZfdTVvhOES0Pf45jx6lyeJNJ4l`):

> "Documentation for Open Source Cross-Sectional Asset Pricing Data … **Data Release: October 2025** … Created with Code Version: 2.0.0"
> "New data relative to the October 2024 release: **Data through December 2024**."
> 例外三項:
> - OptionMetrics 隱含波幅類 7 條(CPVolSpread、dCPVolSpread、dVolCall、dVolPut、RIVolSpread、skew1、SmileSlope)沿用 2023 年 8 月版本,**只到 2022 年 12 月**;
> - Gompers-Ishii-Metrick 治理指數三條(Activism1、Activism2、Governance)**只到 2007 年**,因為上游數據已停止更新;
> - ProbInformedTrading 依賴 Duarte et al. 數據,**只到 2012 年**。

**最近一次更新日:2025-10-22。** 出處:官網首頁 News 最頂一則「2025-10-22: Data update (October 2025)」;GitHub Releases API 交叉核對,最新 tag `v2.0.0`,`published_at` = `2025-10-22T07:29:08Z`,之後無新版。Python 套件 `openassetpricing` 0.0.2 內建的最新版本正是 `release202510_url`,**沒有落後於官網**。

**更新頻率:官方沒有承諾任何週期。** 查不到「每年一次」之類的明文;最接近的官方用詞是釋出標題自稱「Annual improvements」。官網列出的歷史節奏是 2020-05、2020-07、2021-03、2021-04、2022-03、2023-08、2024-08、2024-10、2025-10——2022 年之後大致一年一次。按此節奏下一期本應在 2026 年出現,但截至今日官網未見公告。

**最早年份:官方沒有寫,本票實跑量出來。** 官網、FAQ、釋出說明、GitHub `Docs/`、`SignalDoc.csv` 全部 29 個欄位都沒有寫出寬表的起點(`SignalDoc.csv` 的 `SampleStartYear` 是**原論文的樣本期**,不是 OSAP 數據本身的覆蓋期,不可以當起點用)。本票實跑下載 7 條訊號量出實際範圍:

| 訊號 | 類別 | 最早 | 最晚 | 觀測數 | 涵蓋 permno 數 |
|---|---|---|---|---|---|
| Mom12m | Price | **1926-11** | 2024-12 | 3,705,938 | 28,065 |
| EntMult | Accounting | 1950-12 | 2024-12 | 2,408,518 | 18,436 |
| BM | Accounting | 1950-12 | 2024-12 | 2,715,244 | 22,164 |
| AssetGrowth | Accounting | 1951-12 | 2026-10 | 3,312,711 | 24,301 |
| TotalAccruals | Accounting | 1951-12 | 2026-10 | 3,158,493 | 23,434 |
| roaq | Accounting | 1966-06 | 2024-12 | 2,490,920 | 21,826 |
| AbnormalAccruals | Accounting | 1971-12 | 2026-11 | 2,686,371 | 20,736 |

七條合計涵蓋 **30,298 個不同 permno、1,201 個不同月份(1926-11 至 2026-11)**。

**要留意「2026 年」那條尾巴不是新數據。** AssetGrowth 一類純 Compustat 年度訊號的月度密度顯示:2026-05 之前每月仍有約 4,300–5,000 隻股票,2026-06 突然跌到 375 隻,再跌到 28 隻。這是**年度會計數字向前填充**造成的尾巴——同一個財年數字沿用 12 個月,填到 2026 年年中,不代表有 2026 年的新財報。凡是需要 CRSP 市值或股價的訊號(BM、EntMult、roaq、Mom12m)一律**硬停在 2024-12**,與官方「Data through December 2024」完全一致。

> **對決策的意思**:估值類因子(市帳率、企業倍數)這些第一層選股最常用的東西,最新一個可用的橫斷面是 **2024 年 12 月**,距今 20 個月。

### 問 2:觀測頻率是月度還是日度

**月度。** 論文明文(Chen & Zimmermann §2.2.1):

> "All characteristics are computed at a **monthly frequency**. For variables that are updated at a lower frequency, the monthly value is the most recently observed value."

官方釋出說明對每個個別訊號檔的欄位定義:

> "Each csv in this folder has columns: **permno, yyyymm, [signalname]**"

本票實跑核實:下載回來的表就是 `permno` + `yyyymm` + 訊號欄,`yyyymm` 12 個月份全部出現,無日度欄位。日度數據只存在於**組合報酬**那一邊(Drive 的 `DailyPortfolios` 資料夾),不是個股層面因子值。

日期口徑(FAQ 明文,對回測對齊很關鍵):

> "Data are always **end-of-month**, i.e. you are able to trade on a signal by the end of the month in the year-month column." — [openassetpricing.com/faq](https://www.openassetpricing.com/faq/)

**本票另外實跑核對出一個更保守的事實**:以 Mom12m 為例,標示為 `yyyymm = t` 的值,實測等於「第 t-11 至 t-1 月的累積報酬」——即是**只用到第 t-1 月月底為止的資訊,連當月都沒有用**。這與 `SignalDoc.csv` 的定義「Stock return between months t-12 and t-1」吻合,亦即價量這一側**沒有前視偏差**。(會計那一側是另一回事,見問 6。)

### 問 3:宇宙範圍,以及現役快照 603 個代號對得上多少

**官方沒有一句話式的宇宙定義,但程式碼寫得很白**(出處:[SignalMasterTable.py](https://github.com/OpenSourceAP/CrossSection/blob/master/Signals/pyCode/SignalMasterTable.py)):

> `df = df[(df['shrcd'].isin([10, 11, 12])) & (df['exchcd'].isin([1, 2, 3]))].copy()`

即 CRSP 股份代碼 10/11/12(美國普通股 + 外國註冊普通股),交易所代碼 1/2/3(紐交所 / 美交所 / 納斯達克)。**沒有市值或股價下限**——論文明文說這些篩選刻意不放進因子檔:

> "We try to put off this subsetting until the portfolio generation step. Thus, the characteristics code and data omit price and exchange filters, which are instead imposed in portfolio generation."

意思是寬表**包含微型股與低價股**,任何「股價 > $5」「市值 > 紐交所 20 百分位」的篩選要自己加(官方在組合層另出這些版本)。

**這個篩選有一個對我們很重要的後果:房地產信託(REIT,股份代碼 18)與 ETF(代碼 73)不在宇宙內。**

**603 個代號的實測對應結果**(方法見第三節):

| 分類 | 數目 | 佔比 | 說明 |
|---|---|---|---|
| **對得上(嚴格)** | **537** | 89.1% | 平均絕對誤差 < 0.01,且次佳候選差 5 倍以上;零重複配對 |
| **對得上(相關係數 > 0.99)** | **9** | 1.5% | 同一隻股票,只是股息/公司行動口徑差 1–2%(AT&T、Dell、Linde、Charter、Cencora、Gen Digital、Ingersoll Rand、Match、Nabors) |
| **合計對得上** | **546** | **90.5%** | |
| OSAP 根本沒有收 | 42 | 7.0% | 最高相關係數只得 0.80–0.99,即數據庫裡不存在對應證券 |
| 無法判斷 | 15 | 2.5% | 我們自己的價格歷史與 OSAP 窗口重疊不足 |

**驗證**:八隻已知答案的股票全部配中,誤差在 1e-6 至 1e-3 量級,次佳候選差 60 倍至 20 萬倍:

| 代號 | 配到的 permno | 平均絕對誤差 | 領先次佳倍數 |
|---|---|---|---|
| AMZN | 84788 | 0.00000075 | 203,529× |
| TSLA | 93436 | 0.0000021 | 57,551× |
| NVDA | 86580 | 0.000105 | 3,902× |
| AAPL | 14593 | 0.000305 | 368× |
| KO | 11308 | 0.000306 | 193× |
| MSFT | 10107 | 0.000328 | 316× |
| IBM | 12490 | 0.000917 | 81× |
| JPM | 47896 | 0.000963 | 67× |

**對不上的 42 個,絕大部分是 REIT**:PLD、AMT、CCI、SBAC、EQIX、DLR、PSA、SPG、O、WELL、VTR、EXR、ESS、MAA、UDR、CPT、ARE、BXP、FRT、KIM、REG、HST、IRM、VNO、SLG、DOC、MAC、INVH、VICI、FCPT、WY,再加 SPY(這是快照裡唯一一隻 ETF)。本票用相關係數做了決定性測試:這批股票在整個 OSAP 數據庫裡,最相似的一條序列相關係數只得 0.80–0.96(對照:真正對得上的是 0.999+),即**不是配錯,而是數據庫裡根本沒有這隻證券**——與上面的股份代碼篩選完全吻合。另有 DHR(Danaher)、CCL(Carnival)、CRH、SW 幾隻因為分拆或合併令價格序列口徑不同而落入此類,這幾隻**未逐一查證**是真的沒收還是我們的價格序列對不上。

**無法判斷的 15 個**:AMTM、GEV、RDDT、SOLV、VLTO、KVUE、GEHC(全部 2022 年底之後上市或分拆,與 OSAP 到 2024-12 的窗口重疊不足 24 個月)、HOT(2017 年已除牌)、以及 AVB、EA、FDXF、HONA、Q、SNDK、SOLS 七隻在我們自己的快照裡 2016–2024 段沒有實際 K 線(其中 FDXF、HONA、Q、SNDK、SOLS 是 2025–2026 年新上市/分拆,合理;**AVB 與 EA 兩隻是老公司卻沒有歷史實際 K 線,這是我們自己快照的一個缺口,與 OSAP 無關,本票只作記錄,未追查**)。

**最要緊的一問是:對得上之後,真的有基本面數字嗎?** 實測 537 隻嚴格配對的股票在 2024-12 這個月份:

| 因子 | 有值 / 537 | 備註 |
|---|---|---|
| AssetGrowth(資產增長) | 527 | 98% |
| Mom12m(12 個月動量) | 527 | 98% |
| TotalAccruals(總應計) | 526 | 98% |
| roaq(季度資產回報率) | 524 | 98% |
| AbnormalAccruals(異常應計) | 501 | 93% |
| EntMult(企業倍數) | 479 | 89% |
| **BM(市帳率)** | **320** | **60%——明顯偏低** |
| 六條全部齊備 | 286 | 53% |
| 至少一條有值 | 527 | 98% |

BM 只得六成,原因很可能是 `SignalDoc.csv` 為 BM 登記的篩選條件 `exchcd %in% c(1,2)`(只收紐交所與美交所,排除納斯達克)——標普 500 大約四成成分股在納斯達克,比例正好對得上。**此項為推論,未逐字向官方文檔核實。**

### 問 4:識別碼對應(本票最可能卡住的一環)

**結論:OSAP 官方沒有提供任何 permno → ticker / CUSIP / CIK 的對照表。查不到。**

本票查過以下位置,全部沒有:

- **官方 Google Drive 的完整目錄**——本票沒有靠 Python 套件那個過濾過的清單(套件只保留 10 個已知檔名,其餘一律丟棄),而是自己遞歸列出整個資料夾樹,42 個項目逐個看過:只有特徵值檔、組合報酬檔、`SignalDoc.csv`、釋出說明、儲存檢查記錄。**沒有任何對照檔。**
- 官網 Data 頁、FAQ 頁、Code 頁
- 官方釋出說明的 Directory 全節
- GitHub repo 根目錄與 `Docs/` 全部內容
- `SignalDoc.csv` 全部 29 個欄位(無識別碼欄)
- 論文正文與附錄(全文搜 "permno" 零命中)

打包腳本本身寫得很清楚,寬表只由兩個 key 併成([1_pack_signals.r](https://github.com/OpenSourceAP/CrossSection/blob/master/Shipping/Code/1_pack_signals.r)):

> `signals <- read_csv(...) %>% select(permno, yyyymm) %>% as.data.table()`

反證更直接:OSAP 自己那份「補回 CRSP 三條因子」的示範腳本,一開頭就要你登入 WRDS 才拿得到 ticker 那一側([CrossSectionDemos](https://github.com/OpenSourceAP/CrossSectionDemos/blob/main/dl_signals_add_crsp.R)):

> `user = getPass('wrds username: ')` … `from crsp.msf as a left join crsp.msenames as b`

**免費、非 WRDS 的第三方對照來源,逐個查過,沒有一個是乾淨可用的**:

| 候選 | 內容 | 判斷 |
|---|---|---|
| [Wenzhi-Ding/Std_Security_Code](https://github.com/Wenzhi-Ding/Std_Security_Code)(GPL-3.0) | `gvkey_permco_permno.pq`,117,005 行,34,171 個 permno,帶生效起訖日 | **實質上是 WRDS `crsp.ccmxpf_lnkhist` 的傾印**。作者自己警告:「Mostly from WRDS. Please make sure you have rights to access the corresponding link table」、「not recommended for direct use in published research or formal reports without independent verification」。**商業使用有版權風險**;而且它的 ticker 那一段只覆蓋 2003 年之後,配不上 OSAP 的長歷史 |
| [leoliu0/cik-cusip-mapping](https://github.com/leoliu0/cik-cusip-mapping) 等 | 由 SEC EDGAR 13D/13G 申報抽出的 CIK↔CUSIP | 來源公開合法,但**鏈條斷在 CUSIP → permno**,那一步仍然只有 CRSP 有 |
| [紐約聯儲 CRSP-FRB Link](https://www.newyorkfed.org/research/banking_research/datasets) | 官方免費 | 是 **PERMCO**(公司層)不是 PERMNO(證券層),無 ticker 欄,而且只涵蓋銀行與銀行控股公司。對一般股票宇宙無用 |

**但本票證明了第四條路可行:價格指紋反查。** OSAP 免費的 209 條裡面本身就有純價量訊號(例如 Mom12m),而我們自己有同一批股票的日線。把兩邊的 12 個月動量序列逐月對比,誤差最小的那個 permno 就是答案。實測結果已列在問 3:**603 個對上 546 個,零重複配對,八個已知答案全中,誤差 1e-6 量級**。這條路不需要 WRDS、不需要來源存疑的第三方傾印、不涉及任何授權問題(用的是 OSAP 自己免費發佈的數值加我們自己的價格)。

**這條路的限制要講清楚**:(a) 只對「我們有足夠價格歷史、而且 OSAP 窗口有重疊」的股票有效——新上市與已除牌的配不上;(b) 每次 OSAP 出新版都要重跑一次(permno 本身不變,但新股票要補);(c) 對股息/公司行動口徑敏感,有 9 隻要靠相關係數而非絕對誤差才確認得到;(d) 這是**我們自己砌的**對照表,不是權威來源,**每次用之前應該重跑那八個已知錨點做自檢**。

### 問 5:209 條按官方 `Cat.Data` 分類的條數

先修正一個上一張票的數字。`research/2026-08-29-osap-classic-anomalies.md` 第六節寫「`Cat.Data=Accounting` 的訊號有 196 條(佔 331 條裡的多數)」——**這個 196 把安慰劑訊號一齊數了進去**。`SignalDoc.csv` 的 331 行實際組成是:**Predictor 212 條 + Placebo 114 條 + Drop 5 條**。可下載的免費 209 條**全部都是 Predictor,一條安慰劑都沒有**(212 條 Predictor 減去要 WRDS 的 Price、Size、STreversal 三條 = 209)。

**免費 209 條的官方分類**(本票實跑,把個別訊號清單與 `SignalDoc.csv` 對接):

| `Cat.Data` | 條數 | 中文 |
|---|---|---|
| **Accounting** | **99** | 財報會計 |
| Price | 42 | 價格 |
| **Analyst** | **18** | 分析師 |
| Trading | 13 | 成交 |
| Other | 12 | 其他 |
| Options | 9 | 期權 |
| 13F | 8 | 13F 持倉 |
| Event | 8 | 事件 |
| 合計 | 209 | |

- **財報與分析師類(Accounting + Analyst)= 117 條**
- **純價量類(Price + Trading)= 55 條**

117 條的複現品質分佈(OSAP 官方自評):`1_good` 86 條、`2_fair` 22 條、`3_distant` 3 條、`4_lack_data` 6 條;可預測性自評:`1_clear` 95 條、`2_likely` 22 條。

**財報與分析師類前 20 條(按原始論文公布 t 值排序)**:

| # | 訊號 | 類別 | 中文 | 作者(年份) | 公布月報酬 | 公布 t 值 | 論文樣本期 | 複現品質 |
|---|---|---|---|---|---|---|---|---|
| 1 | ChTax | Accounting | 稅項變動 | Thomas & Zhang (2011) | 1.30% | 11.26 | 1977–2006 | good |
| 2 | CredRatDG | Analyst | 信貸評級下調 | Dichev & Piotroski (2001) | 1.32% | 11.04 | 1986–1998 | lack_data |
| 3 | EarningsStreak | Accounting | 盈利驚喜連續期 | Loh & Warachka (2012) | 0.96% | 9.51 | 1987–2009 | good |
| 4 | MS | Accounting | Mohanram G 分數 | Mohanram (2005) | 1.58% | 9.14 | 1978–2001 | fair |
| 5 | EarnSupBig | Accounting | 大型公司盈利驚喜 | Hou (2007) | 未登記 | 8.91 | 1972–2001 | good |
| 6 | dNoa | Accounting | 淨營運資產變動 | Hirshleifer, Hou, Teoh, Zhang (2004) | 未登記 | 8.85 | 1964–2002 | good |
| 7 | DelCOA | Accounting | 流動營運資產變動 | Richardson et al. (2005) | 未登記 | 8.71 | 1962–2001 | good |
| 8 | CompositeDebtIssuance | Accounting | 綜合債務發行 | Lyandres, Sun & Zhang (2008) | 0.52% | 8.59 | 1970–2005 | good |
| 9 | AssetGrowth | Accounting | 資產增長 | Cooper, Gulen & Schill (2008) | 1.73% | 8.45 | 1968–2003 | good |
| 10 | NOA | Accounting | 淨營運資產 | Hirshleifer et al. (2004) | 1.48% | 8.45 | 1964–2002 | good |
| 11 | AbnormalAccruals | Accounting | 異常應計 | Xie (2001) | 0.92% | 8.43 | 1971–1992 | fair |
| 12 | DelFINL | Accounting | 金融負債變動 | Richardson et al. (2005) | 未登記 | 8.01 | 1962–2001 | good |
| 13 | InvestPPEInv | Accounting | 廠房設備與存貨投資/資產 | Lyandres, Sun & Zhang (2008) | 0.57% | 7.13 | 1970–2005 | good |
| 14 | ShareIss1Y | Accounting | 一年股份發行 | Pontiff & Woodgate (2008) | 未登記 | 7.08 | 1970–2003 | good |
| 15 | NetDebtFinance | Accounting | 淨債務融資 | Bradshaw, Richardson & Sloan (2006) | 0.68% | 6.91 | 1971–2000 | good |
| 16 | ExclExp | Analyst | 被剔除的費用 | Doyle, Lundholm & Soliman (2003) | 未登記 | 6.78 | 1988–1999 | good |
| 17 | InvGrowth | Accounting | 存貨增長 | Belo & Lin (2012) | 0.89% | 6.64 | 1965–2009 | good |
| 18 | EntMult | Accounting | 企業倍數 | Loughran & Wellman (2011) | 0.95% | 6.54 | 1963–2009 | good |
| 19 | roaq | Accounting | 季度資產回報率 | Balakrishnan, Bartov & Faurel (2010) | 0.84% | 6.45 | 1976–2005 | good |
| 20 | TotalAccruals | Accounting | 總應計 | Richardson et al. (2005) | 未登記 | 6.38 | 1962–2001 | good |

「公布月報酬」與「公布 t 值」取自 `SignalDoc.csv` 的 `Return` / `T-Stat` 欄(OSAP 官方整理自各篇原始論文的複現目標數字),部分論文只登記 t 值沒有登記報酬,標「未登記」。全部 20 條的官方組合構造都是**等權**;分位數切法各異(`LS Quantile` 欄,0.1 = 十分位、0.2 = 五分位、0.333 = 三分位,空白者原論文沒有用分位數法)。

**心理準備要點(沿用「實測前先講文獻結論」的規矩)**:這批公布數字是 1960–2000 年代、CRSP 全市場(含大量小型股)、等權多空組合的月報酬。我們第一輪如果在標普 500(全部是大型股)、較短樣本期上跑,量級大機率明顯低於這裡列的數字。而且 OSAP 官方釋出說明自己的統計顯示,全套 Predictor 組合的平均月度多空報酬,**論文樣本期內是 0.69%,論文發表之後跌到 0.30%,2024 年單年只得 0.23%**——即是這批效應在近年已經明顯衰減。這一點在向用戶交代預期時要一併講。

### 問 6:時點口徑——有沒有前視偏差

**分兩側講,結論不同。**

**價量側:沒有前視偏差,本票實測核實過。** 如問 2 所述,標示為 `yyyymm = t` 的 Mom12m,實測只用到第 t-1 月月底的資訊。FAQ 亦明文「you are able to trade on a signal by the end of the month in the year-month column」。

**會計側:有一個結構性的前視風險,而且官方文檔完全沒有正面討論過。**

官方明文的滯後規則(論文 §2.2.1):

> "For almost all characteristics, we use the **standard six-month lag for annual accounting data availability** and a **one-quarter lag for quarterly accounting data availability**. In a couple cases, we use the earnings reporting date (RDQ) to indicate availablility of quarterly data in order to more closely match the original papers."

FAQ 講得最白,連「用足 12 個月」那一層都交代:

> "We follow the Fama-French (1992) convention of being very conservative in assumptions about data availability. We implement FF's convention by **lagging annual accounting data by 6 months past the datadate, and then using the variable for 12 months after that**, implying that an accounting number released today (April 2021) could be used to predict returns 18 months from today (October 2022)."

論文並提醒:這個滯後**不在因子腳本裡,而在下載步驟裡**,看因子檔本身看不出來:

> "For users of the code: the accounting data lag is imposed in the data download step, and is not visible in the files that generate characteristics."

**問題在於「重述」這一層。** 官方文檔(論文兩個版本全文、官網四頁、釋出說明)搜過 `restate`、`unrestated`、`point-in-time`、`vintage`、`snapshot`,**零命中**——官方從來沒有討論過這件事。但程式碼給出決定性答案([CompustatAnnual.py](https://github.com/OpenSourceAP/CrossSection/blob/master/Signals/pyCode/DataDownloads/CompustatAnnual.py)):

> `FROM COMP.FUNDA as a WHERE a.consol = 'C' AND a.popsrc = 'D' AND a.datafmt = 'STD' AND a.curcd = 'USD' AND a.indfmt = 'INDL'`
> `# Add 6-month reporting lag to determine data availability date`
> `annual_data['time_avail_m'] = (annual_data['datadate'].dt.to_period('M') + 6).dt.to_timestamp()`

`comp.funda` 配 `datafmt='STD'` 是**標準的、當前口徑的** Compustat 年度檔,即**已經重述過**的數值,不是 WRDS 的 point-in-time 快照庫。

**用白話講**:一間公司 2019 年公布的盈利,如果 2021 年因為會計調整而修訂過,OSAP 用的是修訂後那個數字,但把它當成 2019 年就知道。回測會因此偏樂觀——策略「看到」了當年沒有人看得到的更正。**這一項無法靠我們自己還原**:要真正的當年口徑,只有逐份翻當年的原始申報,亦即 EDGAR 那條路。

一個相關佐證,說明這類問題確實會漏網:官網 News 記錄 2024-10-14 那一期的更新內容是「Fixes lookahead bug in AnnouncementReturn」——他們自己修過前視 bug。

### 問 7:用對方算好的值 vs 自己由 EDGAR 算,代價逐項

| # | 代價 | 具體是什麼 | 嚴重度 |
|---|---|---|---|
| 1 | **更新滯後 20 個月** | 最新一期 2025-10 釋出,數據只到 2024-12;今日是 2026-08。做歷史測試無妨,**做今日的實盤選股完全不夠**。而且官方沒有承諾更新週期,下一期何時出無人知 | **高——這一項單獨就否決了實盤用途** |
| 2 | **無法自訂知情時點還原** | 用的是重述後的 Compustat + 機械 6 個月滯後,不是當年口徑。回測結果可能偏樂觀,而我們**無法從 OSAP 這一側修正** | **高——這是 EDGAR 唯一無可替代的價值** |
| 3 | **覆蓋斷點:REIT 與 ETF 缺席** | 股份代碼篩選排除 REIT(代碼 18)與 ETF(代碼 73)。標普 500 裡約 30 隻 REIT 拿不到值;要做全指數選股必須為這批另想辦法,或者明文把 REIT 排除出策略宇宙 | 中 |
| 4 | **識別碼要自己接,而且要維護** | 官方無對照表。本票證明價格指紋反查可行(546/603),但這是我們自己砌、每次新版要重跑、對新上市股票無效的一張表 | 中 |
| 5 | **不能自訂變體** | 只能用 OSAP 定義好的 209 條。想改一條的計算窗口、換一個分母、加一個行業中性化——做不到,因為原始財報數字不在我們手上,只有算好的最終值 | 中 |
| 6 | **個別訊號有各自的提早斷點** | 期權類 7 條只到 2022-12;治理指數 3 條只到 2007;ProbInformedTrading 只到 2012。用之前要逐條確認,不能假設全部到 2024-12 | 中 |
| 7 | **個別訊號有各自的宇宙篩選** | 例如 BM 只覆蓋我們 537 隻裡的 320 隻(疑似紐交所/美交所限定)。同一個組合裡混用不同訊號,實際可用股票數會被最窄那一條拖低 | 中 |
| 8 | **授權與引用** | 數據本身查不到明文授權條款,亦**查不到任何非商業限定字眼**;唯一硬性要求是引用論文(Chen & Zimmermann 2022, *Critical Finance Review* 11(2): 207–264)。下載程式碼是 GPL-2.0。**但要留意**:上游的 CRSP / Compustat / IBES / OptionMetrics 本身有各自授權,OSAP 只發佈衍生值,上游條款不在 OSAP 文檔範圍內——真要商業化,這一格要另外查清楚 | 中(商業化前必須釐清) |
| 9 | **近年效應衰減** | 官方自己的統計:全套 Predictor 平均月度多空報酬,論文樣本期內 0.69%,發表後 0.30%,2024 年 0.23% | 低(不是 OSAP 的缺陷,是市場事實,但影響預期) |
| 10 | 引用一致性小坑 | 官網首頁的 BibTeX 把 volume 寫成 27,GitHub README 寫 11。正確是 11(2): 207–264,抄引用用 GitHub 那份 | 極低 |

**相對地,自己由 EDGAR 算的代價**(對照用,本票沒有深查,只列已知方向):要自建財報解析、要處理申報修訂與重述、要自己決定每條因子的定義並承擔「我們有沒有算錯」的風險、要建立自己的知情時點記錄——工作量以月計,而且第一輪根本未知基本面選股這條路有沒有東西。

---

## 二、結論

**問:今日夠不夠做基本面選股的第一輪實測?**

**夠。** 三個條件全部滿足:

1. **有數據**——117 條財報與分析師類因子,免費、值是對方算好的、方向已統一,不需要 WRDS。
2. **對得上我們的股票**——603 個現役代號對上 546 個(90.5%),而且對上之後 98% 真的有基本面數字。
3. **樣本期夠長**——1950 年代至 2024-12,近 900 個月的月度橫斷面,遠超做一輪像樣實測所需。

**但有三個前提要在建置票上寫死:**

- 實測窗口的終點是 **2024-12**,不是今日。任何「這條策略現在會揀邊幾隻」的問題,OSAP 答不到。
- 結果要標明「建基於重述後的會計數字」,即實際可實現的績效大機率低於測出來的數字。這不是可以事後補救的細節,是解讀結果的前提。
- REIT 要明文排除出第一輪的策略宇宙(或者另行處理),不要讓 42 隻缺值股票靜靜地變成偏差來源。

**問:SEC EDGAR 數據線應否押後?**

**應該押後,但不應取消。** 理由:

- **押後的理由**:EDGAR 那條線是為了解決「自己算」的問題,但第一輪實測要回答的根本不是「我們算得準不準」,而是「基本面選股這條路在標普 500 上有沒有東西」。用 OSAP 可以用**近乎零的數據建置成本**先回答後面那條問題。若答案是「沒有東西」,EDGAR 那幾個月的工就慳返了。
- **不應取消的理由**:OSAP 有兩件事永遠做不到——**實時性**(20 個月滯後,而且沒有更新承諾)與**真正的知情時點口徑**(重述問題無法從這一側修正)。這兩件事正好是 EDGAR 的核心價值。所以 EDGAR 不是「OSAP 的替代品」,是「OSAP 證明方向有價值之後的下一步」。
- **建議排序**:(1) 用 OSAP 跑基本面選股第一輪實測 →(2) 若有效,才啟動 EDGAR,目標明確定為「補實時性與知情時點」,不是重造 OSAP 已經算好的 117 條。

---

## 三、實跑方法與可重跑的檔案

全部臨時檔留在 scratchpad,沒有寫入 `data/`,沒有下載 1.6GB 全量寬表。

**關鍵發現(對下一個要用這個套件的人有用)**:`openassetpricing` 套件的 `dl_signal(backend, [訊號名], signed=True)` 走的是 Google Drive 上**逐條訊號的獨立 CSV**,不需要下載 1.6GB 的寬表。要全量才用 `dl_all_signals()`。另外,套件的檔案清單 `name_id_map` **有過濾**(只保留 10 個已知檔名),要看官方雲端硬碟的真實內容,必須自己呼叫 `gdrive_parse` 的遞歸列目錄函式。

腳本(scratchpad,`k098_*.py`):

| 腳本 | 做什麼 |
|---|---|
| `k098_explore.py` | 列出釋出版本的檔案清單與 209 條個別訊號清單 |
| `k098_drive_raw.py` | 遞歸列出官方 Google Drive 完整目錄(不過濾),用來確認沒有對照表檔 |
| `k098_classify.py` | 把 209 條與 `SignalDoc.csv` 對接,做 `Cat.Data` 分類統計 |
| `k098_pull.py` | 實際下載 7 條訊號,量覆蓋期、頻率、宇宙 |
| `k098_releasenotes.py` | 下載並讀出官方釋出說明 docx 全文 |
| `k098_permno_match.py` | 價格指紋反查 permno(四種時點對齊變體) |
| `k098_match_diag.py` / `k098_corrtest.py` / `k098_tally.py` | 失配診斷、相關係數決定性測試、最終計數 |

產出的對照表:`k098_recovered_crosswalk.csv`(537 條嚴格配對,含誤差與領先倍數),`k098_final_tally.csv`(603 個代號逐個判定)。**這張表是本票自己砌的,不是權威來源;要進生產必須另開票,並且每次重跑都要用那八個已知錨點自檢。**

---

## 未完全核實事項清單

- **OSAP 寬表的官方起始年月查不到。** 官網、FAQ、釋出說明、GitHub `Docs/`、`SignalDoc.csv` 全部沒有寫。本票報的 1926-11 是自己下載 7 條訊號量出來的實際最早月份,不是官方聲明,而且只覆蓋這 7 條,其餘 202 條未逐條量。
- **官方沒有公布股票總數與 firm-month 觀測總數。** 本票報的 30,298 個 permno 只是所取 7 條訊號的併集,不是全庫數字。
- **BM 只覆蓋 320/537 的原因是推論。** 依據是 `SignalDoc.csv` 為 BM 登記的 `exchcd %in% c(1,2)`,加上比例與標普 500 的紐交所佔比吻合;未逐字向官方文檔核實這個篩選是否真的施加在個股層面的特徵檔上(官方論文說篩選應該留在組合構造階段,與觀察到的現象不完全一致)。
- **DHR、CCL、CRH、SW 四隻落入「OSAP 沒有收」一類,未逐一查證真正原因。** 這幾隻涉及分拆或跨境合併,有可能是 OSAP 真的沒收,亦有可能是我們的價格序列因公司行動而對不上。REIT 那 30 多隻的判定則有股份代碼篩選的程式碼佐證,可信度高得多。
- **AVB 與 EA 兩隻在我們自己的快照裡 2016–2024 段沒有實際 K 線**,本票只作記錄,未追查原因;這是我們自己數據的問題,與 OSAP 無關。
- **價格指紋反查的 546 個配對,只驗證了 8 個已知錨點。** 其餘 538 個靠誤差與領先倍數判定,沒有逐個對外部權威來源核實。用作生產前應該擴大驗證樣本。
- **209 條逐條的實際結束月份未逐一量度。** 本票只量了 7 條,並依官方釋出說明列出三組已知例外(期權類到 2022-12、治理指數到 2007、ProbInformedTrading 到 2012);其餘訊號是否另有提早斷點,未逐條核實。
- **上游數據(CRSP / Compustat / IBES / OptionMetrics)的授權條款如何影響 OSAP 衍生值的商業使用,本票沒有查。** OSAP 自己的文檔不涵蓋這一格。商業化之前必須另外查清楚。
- **OSAP 下一期釋出的時間表查不到。** 官方沒有承諾任何更新週期;按 2022 年後一年一次的節奏推算 2026 年應該有一期,但截至今日官網未見公告——這只是按過往節奏推測,不是官方聲明。
- **「重述數據導致回測偏樂觀」的量級沒有測。** 本票只確認了機制(`datafmt='STD'` = 重述後數據),沒有量度這會令績效高估多少;要量度需要 point-in-time 數據做對照,而我們現時沒有。

---

## 出處總表

- [openassetpricing.com](https://www.openassetpricing.com/)、[/data](https://www.openassetpricing.com/data/)、[/faq](https://www.openassetpricing.com/faq/)、[/code](https://www.openassetpricing.com/code/)
- 官方釋出說明正本:`Release Notes 2025.10.docx`(Google Drive id `18b77C1ZfdTVvhOES0Pf45jx6lyeJNJ4l`,本票已下載並讀出全文)
- [GitHub OpenSourceAP/CrossSection](https://github.com/OpenSourceAP/CrossSection) — [SignalMasterTable.py](https://github.com/OpenSourceAP/CrossSection/blob/master/Signals/pyCode/SignalMasterTable.py)(宇宙篩選)、[CompustatAnnual.py](https://github.com/OpenSourceAP/CrossSection/blob/master/Signals/pyCode/DataDownloads/CompustatAnnual.py)(重述數據與 6 個月滯後)、[1_pack_signals.r](https://github.com/OpenSourceAP/CrossSection/blob/master/Shipping/Code/1_pack_signals.r)(只有 permno + yyyymm 兩個 key)、[LICENSE](https://github.com/OpenSourceAP/CrossSection/blob/master/LICENSE)(GPL-2.0)
- [GitHub OpenSourceAP/CrossSectionDemos — dl_signals_add_crsp.R](https://github.com/OpenSourceAP/CrossSectionDemos/blob/main/dl_signals_add_crsp.R)(要 WRDS 才拿到 ticker 一側)
- [PyPI openassetpricing](https://pypi.org/project/openassetpricing/)、[GitHub mk0417/open-asset-pricing-download](https://github.com/mk0417/open-asset-pricing-download)
- Chen, Andrew Y. and Tom Zimmermann (2022), *Open Source Cross-Sectional Asset Pricing*, **Critical Finance Review 11(2): 207–264**。公開 PDF:[CFR 版](https://cfr.ivo-welch.info/published/papers/chen2021open.pdf)、[FEDS 版](https://www.federalreserve.gov/econres/feds/files/2021-037pap.pdf)
- 第三方對照表候選:[Wenzhi-Ding/Std_Security_Code](https://github.com/Wenzhi-Ding/Std_Security_Code)、[leoliu0/cik-cusip-mapping](https://github.com/leoliu0/cik-cusip-mapping)、[紐約聯儲 CRSP-FRB Link](https://www.newyorkfed.org/research/banking_research/datasets)
- 本倉背景:`research/2026-08-29-osap-classic-anomalies.md`(KARST-075,本票修正其第六節的 196 條數字)、`data/snapshots/2026-08-28-3bf7ab0a522a/`(現役快照,603 個代號)
