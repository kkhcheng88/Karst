# 數據源普查(非回測)—— 公開可得、機器可讀「早期訊號」fan-out census

**Date:** 2026-07-08  **性質:數據源普查,非回測**(本文件不含任何 IC/Sharpe 實測結果,
只係可得性 + 判讀分類 + top 5 pre-registered probe 規格;回測結果另開檔)。
**方法:** 5 個並行 subagent 各自 WebSearch/WebFetch 一個大類(能源/電力/物流、半導體+宏觀製造業、
信用+利率+預測市場、社交注意力、unknown-unknown),逐源核實免費 API 是否存在、更新頻率、歷史深度。

## 判讀紀律(照用戶指示,寫在最前避免誤讀)

Repo 已判死嘅係「**大市 regime 軸**」口徑:GEX 對 VIX 無增量(`2026-07-05_gex_test.md`)、
credit HYG/LQD 做大市風險軸 H1/H2 反號(`2026-07-05_market_regime_2d.md`)、breadth LEVEL
≈ VIX 冗餘(`2026-07-05_phase2_flow.md`)、~30 因子價量 IC 掃描 0/28(`2026-07-01_*.md` 系列)。
**同一數據換一個 mirror(答一個具體主題/板塊嘅問題)可能係另一回事,未判死**——本文件逐條標注
邊個屬於「同一已死家族」(T4)、邊個係「新 mirror、未測」。

**訊號分類法**:T1 實體經濟量(真領先)/ T2 定位注意力(多數滯後,倒轉用做 priced-in 閘)/
T3 事件機率條件器 / T4 已測死家族(標明,唔推薦)。

---

## 一、能源 / 電力 / 物流

| 源 | 分類 | 答邊條問題(主題/時鐘) | 領先/滯後 | 可得性 | 落地成本 | 建議 |
|---|---|---|---|---|---|---|
| EIA Weekly Petroleum Status Report(API v2 `petroleum/stoc/wstk`) | T1 | 原油/成品油短期供需驚喜,A(週頻) | 領先但已被算法交易吸收,edge薄 | 免費API v2(需key),週三發布,history深(1990s+) | 細 | probe |
| **3-2-1 Crack Spread**(EIA WTI+RBOB汽油+ULSD柴油自算) | T1 | **煉油股(VLO/MPC/PSX,oil-gas-energy 主題)獲利週期,B(也可A做價差交易)** | 領先——真正 fundamental leading indicator,領先 refiner 季度盈利1-2季 | 3條EIA免費series相減,daily,history深 | 細 | **probe(高優先)** |
| Baker Hughes 鑽機數 | T2 | 能源股資本支出週期,B | 滯後——反映6-12月前決策 | 免費Excel(週五),無官方API | 中 | priced-in閘用(cycle-stage確認器) |
| EIA Weekly Natural Gas Storage(API v2 `natural-gas/stor/wkly`) | T1 | 天然氣股/公用股,A(週頻) | 領先但薄 | 免費API,週四發布,history深 | 細 | probe |
| **EIA-930 Hourly Electric Grid Monitor**(API v2 `electricity/rto/region-data`) | T1 | **AI電力主題(數據中心用電需求,ai-power-grid)供給/需求脈搏,B(月頻趨勢)** | 領先——區域demand growth outlier領先utility/IPP(VST/CEG/NRG/GEV)資本支出週期 | 免費API(需key),history 2015/2018起,hourly | 細 | **probe(高優先)** |
| PJM Data Miner 2 / ERCOT Public API / CAISO OASIS | T1/T2混合 | 區域電網瓶頸(LMP即時A + interconnection queue較領先B) | 領先(queue)/同步(LMP) | 免費(需註冊key),格式分散笨拙 | 中 | probe(建議經 GridStatus.io 統一接) |
| GridStatus.io(聚合全美9個ISO+EIA) | T1 | 跨ISO電力供需綜合實作路徑 | 同上 | 開源python package免費;hosted API免費tier 500k rows/月 | **細**(大幅降低單獨接 PJM/ERCOT/CAISO 的成本) | probe(技術路徑首選) |
| LBNL "Queued Up" Interconnection Queue Database | T1 | AI電力供給瓶頸(電網互聯隊列),B(僅年度更新) | 領先但太慢做單一訊號 | 免費Excel,年度更新,無API | 中 | probe(需搭配高頻代理) |
| Baltic Dry Index(官方付費;免費鏡像 tradingeconomics/investing.com) | T1 | 散裝航運股+大宗商品海運需求,B | 領先3-6個月 | 無官方免費API,靠第三方爬(反爬風險) | 中 | probe |
| Freightos Baltic Index (FBX) | T1 | 全球貿易/零售商庫存成本,B(領先零售毛利率3-6月) | 領先,基於真實成交價 | 免費dashboard僅近期圖表,完整history需付費 | 中-大 | probe(如接受付費可升優先) |
| **Cass Freight Index**(FRED `FRGSHPUSM649NCIS`/`FRGEXPUSM649NCIS`) | T1 | **美國內陸物流/工業生產週期,B(月頻)** | 領先——公認早期衰退/復甦訊號 | **免費FRED API,穩定,`fredapi` package可直接接** | **細** | **probe(高優先)** |
| **Port of LA / Long Beach 月度TEU** | T1 | **美國零售商庫存/供應鏈備貨,B** | 領先——最大進口港吞吐量預示零售旺季備貨 | 免費CSV/Excel直接下載,官方穩定,次月中公布 | 細 | **probe(高優先)** |
| MPA Singapore Container Throughput | T1 | 全球貿易健康度補充(亞洲轉運樞紐),B | 領先 | 免費,data.gov.sg標準API | 細 | probe(拼圖用) |
| OPEC Monthly Report / Panama Canal Authority 統計 | T3 | 事件觸發(OPEC+ compliance、運河限航) | 條件器,非持續量測 | 免費PDF,無API | 中 | probe(僅作 event trigger 疊加) |

## 二、半導體供應鏈 + 宏觀製造業領先指標

| 源 | 分類 | 答邊條問題(主題/時鐘) | 領先/滯後 | 可得性 | 落地成本 | 建議 |
|---|---|---|---|---|---|---|
| SEMI Billings Report | T1 | 半導體資本支出週期(semicap-equipment),B | 領先 | 免費新聞稿摘要;完整序列付費 | 中 | probe(用YoY%粗代理) |
| WSTS Blue Book historical billings | T1 | 全球半導體出貨景氣,B | 領先偏同步 | **免費下載,40年history,無需登入** | 小 | probe |
| DRAMeXchange/TrendForce DRAM現貨價 | T1 | **DRAM/NAND記憶體週期(memory-supercycle),A(現貨價日更)** | 領先2-3個月 | 首頁摘要免費,完整history需付費會員 | 大 | 跳過(付費牆)/priced-in閘用(免費頁粗判) |
| **台灣上市公司月度營收(TWSE OpenAPI `t187ap05_L`)+ TSMC月度營收官方公告** | T1 | **台灣半導體供應鏈(memory-supercycle 供應端)實際出貨,B(每月10號前)** | 同步偏領先(guidance含前瞻) | **完全免費、免key JSON API,即日更新** | 小 | **probe(高優先)** |
| 費城半導體指數 SOX(FRED `NASDAQSOX`) | T2 | 半導體股價已price-in預期,A | 滯後於基本面 | 免費FRED,2004+ | 小 | 跳過(當校準對照組) |
| **ISM Manufacturing Supplier Deliveries(FRED `NAPMSDI`)+ Customer Inventories(ISM官網,FRED未收錄)** | T1 | 整體製造業/半導體供應鏈緊俏度,B | 領先——公認ISM五分項中最領先者 | FRED免費;Customer Inventories歷史需ISM訂閱 | 小-中 | probe |
| **ISM New Orders − Inventories(FRED `NAPMNOI`/`NAPMII`)** | T1 | **整體製造業景氣衰退/復甦領先指標,B** | 領先——連續3月負值歷史上準確預示衰退(1970起文獻) | **免費FRED API,現成可自動化** | 小 | **probe(高優先)** |
| Philly Fed / Empire State 製造業調查 Delivery Time & Backlog(FRED `DTCDFSA066MSFRBPHI`等) | T1 | 東岸/紐約區供應鏈緊俏度,對全國ISM有1-2週時效領先 | 領先(公布早於全國ISM) | 免費FRED API,history深 | 小 | probe(全國PMI「早知道」代理) |
| Richmond/Dallas/Kansas City Fed 製造業調查 | T1 | 區域補充樣本 | 領先性同上 | 免費(各聯儲網站CSV),FRED收錄不全 | 中 | probe(低優先,邊際貢獻小) |
| NFIB 資本支出計劃/招聘計劃分項 | T1(分項)/T2(綜合) | 中小企業資本開支/招聘意願,B | 招聘分項領先非農1-2月(文獻) | 免費月報PDF,分項歷史需訂閱 | 中 | probe(分項優先於綜合) |
| 韓國海關「前20天出口」半導體項 | T1 | **全球記憶體/晶片需求即時脈搏(memory-supercycle),A~B(月結前10天已知)** | **強領先**——業界視為memory cycle最快指標 | 原始關稅廳可能免費(韓文),CEIC/MacroMicro轉載需查 | 中 | probe(需找到真正免費原始源) |
| 台灣外銷訂單(MOEA/財政部)電子零組件分項 | T1 | 台灣供應鏈訂單能見度,領先實際出貨1-2季 | 領先 | 免費中文PDF/Excel,無API | 中 | probe(工程成本中等) |
| SEMI Book-to-Bill(北美設備) | **T4** | — | 已停發布(2016年12月起) | 免費歷史檔止2016 | — | 跳過(數據源已死) |

## 三、分行業信用利差 + 利率期貨隱含機率 + 預測市場

| 源 | 分類 | 答邊條問題(主題/時鐘) | 領先/滯後 | 可得性 | 落地成本 | 建議 |
|---|---|---|---|---|---|---|
| FRED `BAMLH0A0HYM2`(大市 HY OAS) | **T4** | 大市 risk regime,已同「credit軸判死」同家族 | 滯後(已驗證H1/H2反號) | 免費FRED | 細 | **跳過(重覆已死結論)** |
| **FRED `BAMLH0A1HYBB`/`BAMLH0A2HYB`/`BAMLH0A3HYC`(BB/B/CCC quality spread)** | T2(新mirror,非大市軸) | **「風險偏好正在往邊度輪動」而非大市方向,A** | CCC-BB利差走闊常早於大市drawdown數週 | 免費FRED,日更,BB/B history深(1996+)、CCC較短(2023+) | 細 | **probe(新問題,同已死大市軸唔同)** |
| FRED IG分級 OAS(`BAMLC0A1CAAA`…`BAMLC0A4CBBB`) | T1/T2 | IG內部評級輪動(BBB-A,墮落天使早期訊號),A | 領先(利差走闊早於評級調降) | 免費FRED,日更,history深 | 細 | probe |
| **分行業(能源業/地產業)HY OAS** | — | 用戶原始假設(能源業息差做週期溫度計) | — | **已實查:FRED 冇呢層切法**(只有評級/地區,無產業別)。產業別OAS存在於付費終端(ICE/Markit/Bloomberg) | 大 | **跳過(gap記錄——唔好假設有免費源)** |
| CDX(North America IG/HY)/ iTraxx | T1/T4交界 | CDX是否領先現金債利差(未測,非大市軸家族) | 理論領先,未驗證 | 冇免費官方API,唯一免費法係二手圖表(不可程式化) | 大 | 跳過(落地成本大) |
| SIFMA US Corporate Bonds Statistics(新發行量) | T1 | 企業融資窗口開關(供給壓力訊號,非利差方向),B | 領先——發行窗關閉常早於信用壓力顯現數週 | 免費下載,月/季更,history深 | 細 | probe(新mirror) |
| CME FedWatch API | T3 | FOMC會議機率,A(EOD)/近即時(intraday) | 前瞻條件器 | 要月費(~$25/月起) | 中 | probe |
| **Fed Funds Futures(ZQ)原始結算價 DIY反推機率** | T3 | 同上,免費替代 | 前瞻 | 免費CME延遲報價,公式公開 | 中 | **probe(FedWatch免費替代,優先)** |
| FRED `T10Y2Y`/`T10Y3M` | T1(但極度priced-in) | 衰退機率大方向,B | 領先但雜訊大、人盡皆知 | 免費FRED | 細 | priced-in閘用(非alpha源) |
| NY Fed 衰退機率模型 | T1 | 現成機率輸出 | 領先 | 免費NY Fed月更CSV | 細 | probe |
| **Kalshi 公開市場數據API**(免登入免KYC) | T3 | **經濟數據/Fed決策/公司事件機率,A(受監管、資料品質較穩)** | 前瞻條件器 | **讀取完全免費,免帳號免KYC,限速~30 req/s** | 細 | **probe(優先)** |
| Polymarket Gamma/CLOB API | T3 | 同上,官方API無歷史endpoint | 前瞻 | 免費免登入(即時);歷史要靠第三方(Bitquery等) | 細(即時)/中(歷史) | probe |
| Metaculus API | T3 | 經濟類群眾預測,覆蓋面廣 | 前瞻但非真金錢(cheap talk風險) | 完全免費公開API | 細 | probe(交叉檢查用,唔單獨依賴) |

## 四、社交聲量/搜尋量/散戶定位/資金流(注意力類,T2為主)

**判讀紀律:此類絕大多數係T2(滯後/擁擠度),同 repo 已判死「breadth LEVEL≈VIX冗餘」「價量因子0/28」同一系譜,唔建議當領先alpha,建議走priced-in閘路線。**

| 源 | 分類 | 領先/滯後 | 可得性 | 建議 |
|---|---|---|---|
| Google Trends(pytrends,非官方) | T2 | 滯後 | 免費但**已停維護(2025-04 archived)**,429限流 | priced-in閘用,唔優先 |
| Reddit官方API/Pushshift | T2/已死 | 滯後 | 2023起收費(商用$12,000+/年);Pushshift已斷 | 跳過 |
| StockTwits API | T2 | 滯後 | 有免費層但**目前暫停新註冊(審批中)** | priced-in閘候補 |
| X/Twitter API | T2 | 滯後 | 2026已無真正免費層,付費按量或$42,000/月 | 跳過 |
| VandaTrack(散戶現金流) | T2 | 滯後(業界公認反向) | 付費,無免費替代 | 跳過 |
| Robintrack(散戶持股) | — | — | **已於2020停止更新**(Robinhood斷供底層feed) | 跳過 |
| **Wikipedia Pageviews API** | T2(學界有例外主張) | 官方判滯後,但2016 Oxford study稱有正報酬(未獨立驗證) | **完全免費官方,免key,history回溯2015,日級** | probe(需獨立驗證,唔可直接採信單篇論文) |
| ETF.com/ETFDB 資金流工具 | T2 | 滯後 | 網頁工具非公開API,程式化需付費 | priced-in閘(細規模爬網頁版) |
| SEC 13F | T2 | 明確滯後(45天延遲,官方自認非即時) | 免費官方 | priced-in閘用 |
| CBOE Put/Call未平倉量 | T2(反向情緒) | 滯後 | 免費官方,history齊全 | priced-in閘(成本低值得驗證) |
| Quiver Quantitative(WSB/國會交易/政府合約聚合) | T2 | 滯後 | 有免費層 | priced-in閘(一站式,性價比高) |

## 五、Unknown-unknown(招聘/衛星/專利/標案/天氣/航運/航空/供應鏈/司法/監管)

| 源 | 分類 | 答邊條問題(主題/時鐘) | 領先/滯後 | 可得性 | 落地成本 | 建議 |
|---|---|---|---|---|---|---|
| Indeed Hiring Lab(鏡像 FRED `IHLIDXUS`) | T1 | 行業/地區擴張強度,B | 領先但主指數已部分priced-in(FRED廣泛引用) | 免費CC BY 4.0,日頻,2020-02起 | 細 | probe(用行業拆分粒度) |
| Revelio Labs 免費研究集 | T1 | 個股workforce流動,B | 領先(員工異動早於財報) | 免費研究層有限;完整API付費 | 中 | probe |
| **H-1B LCA Disclosure Data**(DOL/flcdatacenter) | T1 | 科技行業擴張意圖(提前於headcount數月),B | 領先 | **完全免費,Excel下載,季度,history多年** | 細 | **probe** |
| WARN Act 大規模裁員通知 | T1 | 收縮訊號(法定提前~60天),A | 領先(負向) | 大多免費(第三方彙整),需跨49州整併 | 中 | probe |
| Census Weekly Business Formation Statistics(FRED rid=468) | T1 | 總體/行業創業景氣,B | 領先 | **完全免費FRED API,週頻,2006起** | 細 | probe |
| 浮頂油罐陰影分析(衛星) | T3 | 原油庫存領先EIA週報數天 | 領先但**免費影像解析度不足**(需商業影像) | 方法免費、數據不免費 | 大 | 跳過 |
| NASA VIIRS夜間燈光 | T1 | 區域經濟活動強度(補缺官方統計地區),B | 滯後於實時但領先官方統計公布 | 完全免費,月頻,2012起 | 中 | probe(非美股核心用途) |
| USPTO PatentsView / Google Patents(BigQuery) | T3 | 公司研發方向轉移,B | **滯後18個月**(申請到公開)但仍領先商品化 | 完全免費(BigQuery極低費用) | 中 | probe(中長期主題輪動用) |
| **USASpending.gov API** | T1 | **國防/基建承包商訂單流,A(合約簽署即時登錄)** | 領先(合約授予早於營收確認) | **完全免費,無需認證,即時更新** | 細-中 | **probe** |
| NWS api.weather.gov / NOAA CDO | T1 | 短期電力/天然氣需求預測(冷暖度日),A | 領先(未來需求預測) | 完全免費,無需key | 細 | probe(能源需求短期預測) |
| AISstream.io(免費WebSocket AIS) | T1 | 油輪/散裝船流向,A | 領先(船舶動向早於到港/庫存) | 免費層,即時WebSocket,門檻低於AISHub | 中 | probe |
| OpenSky Network | T2 | 商務出行復甦代理,A | 滯後(即時活動非預測) | 免費(非商業),2026年3月起OAuth2 | 中 | probe |
| ADS-B Exchange(私人飛機追蹤) | T3 | 高管私人飛機→M&A前置訊號 | **爭議領先**(文獻指窗口窄,「飛機起飛時謠言已散布」) | 免費,含FAA封鎖尾號 | 中 | probe(小倉位驗證,期望值可能已priced-in) |
| Census國際貿易API | T1 | 進出口實物流量,B | 滯後但快於企業財報 | 完全免費,月更,2010起 | 中 | probe |
| **AAR週度鐵路貨運量**(鏡像 FRED `RAILFRTCARLOADSD11`) | T1 | 大宗商品/工業產出實物代理,A(週更) | 領先(比工業生產月度數據快) | 官方僅公開最近2週,FRED補齊history | 細 | probe |
| SEC EDGAR全文檢索+8-K即時feed | T3 | 事件觸發(重大合約/供應商變更),A | 領先(填報即公開) | 完全免費,無需key(需守UA+限流) | 中 | probe |
| RECAP Archive(破產申請) | T3 | 企業信用惡化事件,A | 領先(申請日即公開) | 免費但**覆蓋不完整**(非100%,抽樣偏差) | 中 | probe(需驗證覆蓋率) |
| FCC設備認證資料庫 | T3 | 消費電子/通訊硬體上市前置,B | 領先(認證早於上市數週~數月) | 完全免費,無官方API(需爬) | 中 | probe |
| ClinicalTrials.gov API v2 | T3 | 生技管線進展,B | 領先但**生技圈已高度使用**(priced-in風險中高) | 完全免費,結構化API v2 | 中 | probe(謹慎,可能已擠) |

---

## 收斂:Top 5 值得 Probe(判準:真領先 + 免費機器可讀 + 對應現有主題/時鐘)

判準優先序:(1)T1實體量、(2)免費穩定API(非爬蟲)、(3)對應 repo 現有 `thesis/themes.yaml`
主題(memory-supercycle / ai-power-grid / oil-gas-energy / semicap-equipment)或現有機制(A型危機
救援/宏觀閘),(4)落地成本細。

### #1 — 3-2-1 Crack Spread(EIA WTI+RBOB+ULSD,oil-gas-energy 主題)

- **測乜**:每日 crack spread(3×RBOB+2×ULSD−5×WTI,標準化每桶)相對其自身 rolling
  過去 N 日(N∈{63,126,252})分位數,forward IC 對煉油股籃(VLO/MPC/PSX/HFC 等,4類覆蓋——
  含 XLE 大盤腿 + 板塊ETF腿)未來 21/63d 報酬。
- **點算命中**:spearman forward-IC(21d 及 63d horizon)在 2016+ 全期 + H1/H2 兩半皆同號、
  |IC| 中位數 ≥ 0.05,且 Bonferroni-adjusted p < 0.05(對照現有 `backtest-testing-standard`
  跨股種/two-halves 要求)。
- **成功標準**:IC 穩健兩半 → 升級做 oil-gas-energy 主題「補倉/減倉」條件層(非直接擇時 SPY/QQQ);
  IC 單邊或不顯著 → 記錄 negative,不建。

### #2 — EIA-930 Hourly Electric Grid Monitor(ai-power-grid 主題)

- **測乜**:區域(PJM/ERCOT/CAISO/MISO 等主要 BA)月度 demand YoY growth outlier(相對
  全美中位數的 z-score)作為 ai-power-grid 籃(URA/GRID/UTES/VST/CEG/NRG/GEV,複用
  `exp_power_etf_basket.py` 已建立的籃子)forward 1-3個月報酬的領先訊號。
- **點算命中**:月度 demand-growth z-score 分位數(top quartile)區域對應籃內權重股 forward
  21-63d 報酬,vs 中位數區域對照組(增量測試,非絕對報酬),用資本效率量度(部署回報/曝險)。
- **成功標準**:top-quartile 區域關聯股 forward 報酬顯著優於底組(t > 2,兩半皆同號)→ 升級做
  ai-power-grid 主題 timing 層;否則記錄 negative(電網數據滯後於股價已price-in AI敘事)。

### #3 — ISM New Orders − Inventories(FRED `NAPMNOI` − `NAPMII`,總體宏觀閘)

- **測乜**:月度 New Orders − Inventories 價差(連續為負判定為收縮訊號)對 SPY/QQQ 未來
  1-6個月報酬的條件分佈,對照現行 200SMA 趨勢閘(`exp_trend_vix_axis.py` 已判定的閘)看
  是否有增量(唔重覆已判死嘅「總經宏觀軸」,呢個係新輸入變數)。
  **注意**:此為總經閘類,需檢查是否與現有已判死的 credit/breadth 軸同質——若條件分佈同
  200SMA 高度共線,則屬冗餘,記錄之。
- **點算命中**:負值持續 ≥3個月 vs 200SMA-only 閘,兩者切分出的 regime 是否有實質差異
  (confusion matrix 交叉表),以及負值 regime 下 forward 報酬/MaxDD 是否顯著劣於正值 regime。
- **成功標準**:若與200SMA閘高度重疊 → negative(冗餘,不建);若能提前1-2個月捕捉200SMA
  未捕捉到的轉折 → 升級做總經閘的補充輸入。

### #4 — Cass Freight Index + AAR 週度鐵路貨運量(工業/物流實物代理,總體閘 + 板塊)

- **測乜**:兩個免費FRED/官方序列的 YoY% 變化,對(a)工業板塊ETF(XLI)、(b)SPY/QQQ 整體
  forward 1-3個月報酬的 forward IC;與 Port of LA/LB TEU 交叉驗證(三源一致性)。
- **點算命中**:三源(Cass/AAR/Port TEU)同向轉折時點的一致性(需 ≥2/3 同向才算訊號),
  forward IC 在 2016+ 全期 + two-halves 穩健同號。
- **成功標準**:IC穩健且三源一致轉折 → 升級做工業板塊/總經閘輸入;否則 negative。

### #5 — 台灣上市公司月度營收(TWSE OpenAPI `t187ap05_L`,memory-supercycle 主題)

- **測乜**:台積電 + 記憶體/封測供應鏈(日月光、南亞科等)月度營收 YoY%,對 memory-supercycle
  主題股(MU/WDC/STX 等,複用 `exp_memory_cycle.py`/`exp_constraint_language.py` 已建立的
  ticker 清單)forward 1-2個月報酬 IC。此為法定披露、免費、每月10號前即出,時效比美股財報季快。
- **點算命中**:台灣供應鏈月營收轉折(YoY% 由負轉正或反之)領先 memory-supercycle 股價
  反應的天數(event study,對照 `exp_constraint_language.py` 已發現嘅「MU 訊號提前於
  gooptions 敘事 ~8-17個月」找互補/加速訊號)。
- **成功標準**:台灣營收轉折能在美股反應**之前**(非同步)出現且統計顯著 → 升級做
  memory-supercycle 主題早期偵測層(與 transcript 語言訊號互補);若僅同步或滯後 → negative。

---

## 最大驚喜發現(fan-out 過程中冇預期到嘅)

1. **「分行業 HY OAS」呢個用戶原始假設在免費源查唔到**——FRED 只公開 ICE BofA 嘅
   「評級」(BB/B/CCC)+「地區」(US/Euro/EM)切法,唔公開「產業別」(如能源業/地產業)
   切法。呢個 gap 值得記低,避免下次假設佢存在。但**quality spread(CCC-BB)**係一個
   合法、未測過嘅新 mirror,同已死嘅「大市 HY OAS 做 regime 軸」係唔同問題。
2. **社交/散戶注意力類數據源 2023 年後大幅收費化/死亡**:Reddit API($12,000+/年)、
   X API(無真正免費層)、Pushshift(已斷)、Robintrack(2020已停更)——傳統「散戶情緒」
   替代數據嘅免費路徑已幾乎消失,剩低 Quiver Quantitative(免費層)同 Wikipedia
   Pageviews(完全免費但需獨立驗證學術文獻)做為僅存缺口。
3. **Kalshi 讀取完全免費、免帳號、免KYC**——比 Polymarket(即時免費、歷史要靠第三方)
   同 CME FedWatch(要月費)更容易落地,且受 CFTC 監管資料品質較穩,值得優先評估。
4. **台灣月度營收(TWSE OpenAPI)係完全免費、免key、即日更新嘅法定披露**,對
   memory-supercycle 主題係目前為止落地成本最低嘅供應鏈早期偵測候選,同 repo 已有嘅
   `exp_constraint_language.py`(transcript 語言訊號)可能互補(前者是硬數字、後者是
   管理層敘事,時鐘可能唔同)。
5. **SEMI Book-to-Bill 早於 2016 年 12 月已停止發布**——呢個係一個經典教科書級「半導體
   領先指標」,但實際上已死十年,普查前未有人再三確認,值得列入 T4 存檔以免日後誤引用。

---

## 索引更新

已在 `backtest/experiments/README.md` 索引表加入一行(無對應 exp_ 腳本,純研究筆記,
標注「數據源普查」而非回測結果)。
