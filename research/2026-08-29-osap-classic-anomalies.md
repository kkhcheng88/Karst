# OSAP 經典價格效應調研:反轉、反轉減弱、成交量與波幅異常、動量、相對強弱——定義、公布量級、取數與授權

- 票號:KARST-075
- 日期:2026-08-29
- 用途:回應用戶 2026-08-29 裁決(對周度反轉、月度成交量/波幅異常、3–12 個月動量、相對強弱四類經典效應「still very interested」),並配合同日 D-033(因子線收斂為八類,前五類——反轉、反轉減弱、成交量與波幅異常、動量、相對強弱——先查,後三類基本面/行業/估值只列數據源方向)。

---

## 摘要(五問各一句起)

1. **OSAP 數據本身沒有獨立的正式授權聲明,只要求引用論文(Chen & Zimmermann 2022);209 個免費特徵(1.6GB 壓縮 csv)人人可下,另外 3 個(Price、Size、STreversal)要 WRDS/CRSP 訂閱**——本票已在 scratchpad 臨時 venv 實跑 `pip install openassetpricing` 並成功取數。
2. **反轉、成交量、波幅、動量、相對強弱五類在 OSAP 都有明確對應的訊號名與公式**,逐條列在下面第二節,附 OSAP 官網 Cat.Data 分類(判斷是否只需價量)、原始論文公布的多空回報/t 值,以及本票自己從 OSAP 的 `PredictorPortsFull`(212 條訊號的完整多空組合月度報酬)重新算出來的 1926–2024 全樣本年化回報與 t 值。
3. **JKP 153 個特徵裡,反轉、動量、波幅、成交量四類都有明確對應的變數名**(如 `ret_12_1`=Mom12m、`ret_1_0`=STreversal、`rvol_21d`=RealizedVol),但**沒有查到跟 IndMom(行業動量)直接對應的 JKP 變數**——JKP 的 153 條全是個股層級特徵,沒有做行業聚合動量;JKP 數據本身 **CC BY-NC 4.0(非商業)**,跟 OSAP 的無正式限制不同。
4. **Karst 現有月度節奏(`CADENCES` 已含 `"monthly"`)不用新增列舉值,但橫斷面分組多空組合回報這種量法現在完全沒有**——`karst/factorpredict.py` 只有逐日 IC/ICIR(`daily_ic`/`rolling_icir`/`summarize_ic`),沒有十分位/五分位多空組合回報的計算函式,是本輪要新增的量法;月度因子能否直接進因子表本票判斷可以(D-021/D-032 的雙時間戳與批次 parquet 設計跟頻率無關),但月度 K 線快照是否已備妥要另外核實。
5. **建議先算 10 條純價量訊號(逐條列在第五節),用 OSAP 自己公布的權重法(等權/市值加權)與分位數複製同一套多空組合方法核對**;建置票拆四張,每張一程;實測前的量級心理準備:OSAP 全樣本(1926–2024)最強的是 STreversal(年化 33.7%,t=13.95),最弱但仍顯著的是 High52(年化僅 0.46%,t≈0.2,幾乎不顯著)——**這批經典效應的公布量級普遍遠高於 Karst 自己在 Alpha158 標普 500 實測(KARST-066)測到的 IC 量級,但這是月度橫斷面多空組合報酬,不是逐日 IC,兩種量法本身不能直接比大小,只能當「別人聲稱多強」的參考起點**。

---

## 一、OSAP:授權、取數方式、免費部分有多少

出處:[openassetpricing.com](https://www.openassetpricing.com/)、[openassetpricing.com/data](https://www.openassetpricing.com/data/)、[PyPI openassetpricing](https://pypi.org/project/openassetpricing/)。

### 1.1 授權(官網條款原文)

- 官網首頁沒有獨立的正式「數據授權」條款頁,只寫明**引用要求**:"If you use the data, please cite our paper"，並附 BibTeX——出處為 **Chen, Andrew Y. and Tom Zimmermann (2022), *Open Source Cross-Sectional Asset Pricing*, Critical Finance Review 11(2): 207–264**。**判斷:數據可自由下載使用,唯一硬性要求是引用論文,沒有查到「非商業限定」或其他限制字眼**——這一點跟 JKP(見第三節)明確不同。
- 兩個下載套件的**程式碼**授權不一致,屬本票新查到、上一輪(KARST-074)未查清的細節:
  - Python 套件 `openassetpricing`(本票實跑用的正是它):**GPLv2**(出處:`pip show openassetpricing` 實跑輸出)。
  - R 套件 `OpenSourceAP.DownloadR`:**MIT**(出處:[CRAN](https://cran.r-project.org/web/packages/OpenSourceAP.DownloadR/index.html),KARST-074 已查)。
  - 兩者都是「下載工具程式碼」的授權,不是「數據本身」的授權——數據本身沿用上一句的引用要求判斷。

### 1.2 三種取數方式,本票實跑其中一種

- 三種:官網 Data 頁面直接下載、`pip install openassetpricing`(Python)、R 套件 `OpenSourceAP.DownloadR`。
- **本票實跑**:在 scratchpad 建立臨時 venv(`…/scratchpad/osap-venv`),`pip install openassetpricing` 成功(套件版本 0.0.2,作者 Peng Li、Andrew Chen、Tom Zimmermann),初始化 `oap.OpenAP(202510)`(最新一期釋出版本,套件內建 `release202510_url`/`release202410_url`/`release202408_url`/`release2023_url`/`release2022_url` 五個歷史版本可選,本票用最新一期)。**注意**:套件文件範例常寫 `OpenAP(2)` 之類的短寫法,實測會拋 `TypeError`(因為套件內部沒有 `release2_url` 這個屬性,`getattr` 拿到 `None` 之後才炸),**正確寫法要用完整釋出年月**(例如 `202510`),這是本票實跑才發現的一個文件與實作不一致的小坑,記在此供下一個要用這個套件的人參考。
- 成功後呼叫 `dl_signal_doc()` 拿到 `SignalDoc.csv`(331 行 × 29 欄的訊號說明表,含公式、公布回報、t 值、樣本期)與 `dl_port('op', predictor=[...])` 拿到 `PredictorPortsFull` 的長格多空組合月度報酬(本票只挑了 14 個目標訊號下載,7.5MB;若下載全部 212 條訊號的組合報酬,體量會是這個的十幾倍,估計上百 MB,未實際下載全量,**未核實**確切大小)。

### 1.3 免費下載的數據集清單、大小、是否需 WRDS/CRSP

實跑 `openap.name_id_map` 取得完整清單(10 個檔案):

| 下載名 | 內容 | 大小 / 覆蓋 | 需 WRDS/CRSP? |
|---|---|---|---|
| `firm_char`(`signed_predictors_dl_wide.zip`) | **209 個免費的橫斷面預測特徵**,寬表,已按「值愈高預期回報愈高」統一符號方向 | 官網標明 **1.6GB 壓縮 csv**(出處:openassetpricing.com/data) | **不需要**——這 209 條免費 |
| CRSP 三條(`Price`、`Size`、`STreversal`) | 從 CRSP 月度股票檔(`crsp.msf`)現場算,套件程式碼 `_dl_signal_crsp3()` 直接跑 `select permno, date, prc, ret, shrout from crsp.msf` 這條 SQL | 併入 `firm_char` 之外的 3 條,湊成官網講的「逾 200 個特徵」(免費 209 + CRSP 3 = 212) | **需要**——套件程式碼裡直接 `import wrds` 開 `wrds.Connection()`,沒有 WRDS 帳號這 3 條拿不到;本票 venv 沒有裝 WRDS 憑證,只下載了不需要 CRSP 的 209 條裡的部分,STreversal 剛好是這 3 條之一,但**本票取的是 OSAP 自己已經算好的 `PredictorPortsFull`(組合層,見下)**,不是 firm-level 原始 STreversal 特徵,兩者不同層——組合層不需要 WRDS,firm-level 原始值裡的 STreversal/Price/Size 三條才需要 |
| `deciles_ew`/`deciles_vw`/`ex_nyse_p20_me`/`nyse`/`ex_price5`/`quintiles_ew`/`quintiles_vw`(`PredictorAltPorts_*.zip`) | 7 種不同篩選/加權法的十分位組合報酬 | 未逐一下載核實大小,**未核實** | 不需要(這批是 OSAP 算好的組合層,不含原始個股特徵) |
| `op`(`PredictorPortsFull.csv`) | **全部 212 條訊號的多空組合月度報酬,單一檔**,本票已實跑下載(14 條訊號子集,1926–2024,7.5MB) | 全量未知,估計上百 MB,**未核實** | 不需要 |
| `signal_doc`(`SignalDoc.csv`) | **每條訊號的說明文件**——公式、作者、年份、樣本期、原始論文公布回報/t 值、OSAP 自己判定的可複現程度 | 331 行 × 29 欄,**本票已完整下載**,181KB | 不需要 |

**小結**:**免費部分(209 個特徵 + 全部組合層報酬)已足夠覆蓋本票要查的五類經典效應**——下面第二節逐條核對過,五類要用到的訊號(STreversal、Mom12m、Mom6m、IndMom、DolVol、VolumeTrend、MaxRet、RealizedVol、IdioVol3F、ReturnSkew 等)全部落在免費的 209 條 + 組合層裡,不需要 WRDS/CRSP。**唯一要 WRDS 的是 firm-level 原始的 Price/Size/STreversal 三條**,但 STreversal 的**組合層報酬**(多空組合已經算好的月度報酬序列)本身在免費的 `op`/`PredictorPortsFull` 裡就有,不受這個限制。

---

## 二、五類效應在 OSAP 的訊號名、定義、公布量級

方法說明:「原始論文公布量級」欄位取自 `SignalDoc.csv` 的 `Return`/`T-Stat`/`SampleStartYear`/`SampleEndYear`(OSAP 官方整理自各篇原始論文的複現目標數字);「OSAP 全樣本多空組合(本票實跑)」欄位是本票用 `PredictorPortsFull` 的 `LS`(long-short)欄位,對 1926–2024 全部可得月份**自己重新算**的月均報酬換算年化、樣本內 t 值(`mean/std*sqrt(n)`)——**這是 OSAP 用官方權重/分位數方法跑出來的組合報酬,不是原始論文本身的樣本期**,兩欄口徑不同,分開列出。「只需價量」按 OSAP 官方 `Cat.Data` 分類判斷(`Price`/`Trading` = 只需價量,`Accounting`/`Analyst`/`Options`/`13F`/`Event`/`Other` = 需要額外數據)。

### 2.1 反轉(Reversal,短期)

| 訊號 | 定義 | 只需價量? | 原始論文公布量級 | OSAP 全樣本多空組合(本票實跑,1926–2024) |
|---|---|---|---|---|
| **STreversal** | 前一個月的股票報酬(反向操作:買前月跌得多的、賣前月漲得多的) | **是**(`Cat.Data=Price`) | Jegadeesh (1990),樣本 1934–1987,等權十分位多空,月報酬 **1.99%**,t=**12.44** | **年化 33.74%**,t=**13.95**,1926-02 至 2024-12(1187 個月) |

出處:`SignalDoc.csv`(Acronym=STreversal)、本票 `PredictorPortsFull` 實跑。**這是本票查到量級最強、t 值最高的一條**——但要留意十分位多空(Quantile=0.1)、等權(EW)是它的官方複現方法,換其他權重法量級會不同。

### 2.2 反轉減弱(反轉效應隨窗口拉長而消退)

**OSAP 沒有一條叫「反轉減弱」的獨立訊號**——這一類描述的是「反轉效應強度隨持有窗口變化」這條曲線本身,不是單一橫斷面特徵。本倉 `research/2026-08-29-factor-horizon-evidence.md` 第 2.1 節已查證兩個端點:**周度**反轉最強(Lehmann 1990),**月度**反轉開始減弱、同時成交量/波幅異常接手(Jegadeesh 1990、Gervais et al. 2001)。OSAP 提供兩個可以量化「減弱到什麼程度」的間接對照:

| 訊號 | 定義 | 只需價量? | 原始論文公布量級 | OSAP 全樣本多空組合(本票實跑) |
|---|---|---|---|---|
| **LRreversal** | 第 t-36 個月到第 t-13 個月的累積報酬(反向操作)——**跟 STreversal 用同一個「過去報酬反向操作」邏輯,只是把窗口從 1 個月拉到 3 年前的一年**,是反轉效應的長端 | 是(`Price`) | De Bondt & Thaler (1985),樣本 1929–1982,月報酬 **0.105%**,t=**3.29** | 未下載進本票的 `op` 實跑清單,**未核實**(SignalDoc 有登記,Stock Weight=EW,可日後補跑) |
| **MomRev** | 二元指標:同時落在 Mom6m 最高五分位**且** Mom36m(等同長期反轉窗口)最低五分位記 1,反之記 0——**直接把「短期動量強」與「長期反轉深」兩個條件疊在一起,量的正是反轉/動量交接帶** | 是(`Price`) | Chan & Ko (2006),樣本 1965–2001,月報酬 **0.48%**,t=**4.29** | 未下載進本票的 `op` 實跑清單,**未核實** |

**對 Karst 的操作建議**:與其找一條叫「反轉減弱」的現成訊號,不如用 Karst 自己 `karst/factorpredict.py` 的 `horizon` 參數,把 STreversal(或用同一個「前 N 個月報酬反向」公式)分別在 1、3、6、12、36 個月的持有窗口都跑一次 IC/組合報酬,直接畫出「反轉強度隨窗口變化」的曲線——這是把 D-033 用戶原話「反轉減弱」翻成可執行量法最直接的做法,`LRreversal`/`MomRev` 可以當作曲線兩端的公開對照點。

### 2.3 成交量與波幅異常

| 訊號 | 定義 | 只需價量? | 原始論文公布量級 | OSAP 全樣本多空組合(本票實跑) |
|---|---|---|---|---|
| **DolVol** | 兩個月前的成交量 × 兩個月前的股價,取對數(過去交易量的代理) | 是(`Trading`) | Brennan, Chordia & Subra (1998),樣本 1966–1995,t=**2.86**(原文沒登記 Return 欄) | 年化 **8.47%**,t=**4.14**,1926-04 至 2024-12 |
| **VolumeTrend** | 過去 60 個月成交量對時間線性迴歸的斜率係數,除以 60 個月平均成交量做標準化 | 是(`Trading`) | Haugen & Baker (1996),樣本 1979–1993,t=**3.00** | 年化 **6.74%**,t=**5.57**,1928-07 至 2024-12 |
| **VolMkt** | 過去 12 個月月均成交金額,除以市值(需股價 > $5 過濾) | 是(`Trading`) | Haugen & Baker (1996),樣本 1979–1993,t=**4.00** | 年化 **3.09%**,t=**1.72**(本票實跑範圍內不顯著,1926-07 至 2024-12) |
| **MaxRet** | 上個月單日最大報酬 | 是(`Price`) | Bali, Cakici & Whitelaw (2011),樣本 1962–2005,月報酬 **1.03%**,t=**2.83** | 年化 **7.50%**,t=**2.93**,1926-02 至 2024-12 |
| **RealizedVol** | 上個月日報酬對 CAPM 迴歸殘差的標準差(市值加權) | 是(`Price`,但公式要市場報酬做迴歸基準,見下面附註) | Ang et al. (2006),樣本 1963–2000,月報酬 **0.97%**,t=**2.86** | 年化 **5.16%**,t=**2.07**,1926-08 至 2024-12 |
| **IdioVol3F** | 上個月日報酬對 Fama-French 三因子迴歸殘差的標準差(市值加權) | 是(`Price`,同上附註) | Ang et al. (2006),樣本 1963–2000,月報酬 **1.06%**,t=**3.10** | 年化 **6.15%**,t=**2.75**,1926-08 至 2024-12 |
| **ReturnSkew** | 上個月日報酬的偏度 | 是(`Price`) | Bali, Engle & Murray (2015),樣本 1963–2012,月報酬 **0.47%**,t=**4.01** | 年化 **5.83%**,t=**7.96**,1926-02 至 2024-12 |
| **High52** | 股價除以過去 12 個月最高價 | 是(`Price`) | George & Hwang (2004),樣本 1963–2001,月報酬 **0.45%**,t=**2.00** | 年化僅 **0.46%**,t≈**0.20**(本票全樣本實跑幾乎不顯著,1926-07 至 2024-12) |

**附註(RealizedVol/IdioVol3F 的「只需價量」要打折扣說明)**:這兩條的公式要對「市場報酬」或「Fama-French 三因子」做迴歸取殘差,嚴格講需要一條額外的市場/因子基準報酬序列,不是單純這隻股票自己的 OHLCV——但這條基準序列(大盤指數報酬,或簡化為只用市場一條而非三因子)本身也是價量數據,不涉及財務報表,OSAP 官方仍把它們分類為 `Cat.Data=Price`,本票採用 OSAP 這個分類口徑。

**票上提到但 OSAP 用不同名字的兩條**:「IdioRisk」在 OSAP 沒有精確同名項,對應的是 `IdioVolAHT`(Ali, Hwang & Trombley 2003)、`IdioVolCAPM`、`IdioVolQF` 這一族,`IdioVol3F` 是其中複現品質最好、樣本最完整的一條,本票以它為代表,其餘三條本票未逐一查證量級(**未核實**)。

### 2.4 動量(3–12 個月)

| 訊號 | 定義 | 只需價量? | 原始論文公布量級 | OSAP 全樣本多空組合(本票實跑) |
|---|---|---|---|---|
| **Mom12m** | 第 t-12 個月到第 t-1 個月的累積報酬 | 是(`Price`) | Jegadeesh & Titman (1993),樣本 1964–1989,月報酬 **1.31%**,t=**3.74** | 年化 **10.80%**,t=**3.77**,1927-01 至 2024-12 |
| **Mom6m** | 第 t-6 個月到第 t-1 個月的累積報酬 | 是(`Price`) | Jegadeesh & Titman (1993),樣本 1964–1989,月報酬 **0.84%**,t=**2.44** | 年化 **7.78%**,t=**2.96**,1926-07 至 2024-12 |

### 2.5 相對強弱(對大市/對行業)

| 訊號 | 定義 | 只需價量? | 原始論文公布量級 | OSAP 全樣本多空組合(本票實跑) |
|---|---|---|---|---|
| **IndMom** | 過去 6 個月個股買入持有報酬,按二位數產業分類、市值加權取產業平均——**個股回報相對所屬產業的動量**,是「相對強弱」裡跟行業掛鉤最直接的一條 | 是(`Price`),**但要有二位數產業分類這個額外輸入**,見下面對 Karst 的意義 | Grinblatt & Moskowitz (1999),樣本 1963–1995,月報酬 **0.43%**,t=**4.65** | 年化 **4.30%**,t=**3.84**,1926-07 至 2024-12 |
| **ResidualMomentum** | 過去 36 個月滾動迴歸(對市場、規模、價值三因子)算特異報酬,取過去 11 個月特異報酬均值除以標準差——**扣掉大市與風格因子暴露之後剩下的動量,是「相對於模型/大市」的相對強弱**,不是相對行業 | 是(`Price`,同 2.3 節附註,需市場/風格因子基準序列) | Blitz, Huij & Martens (2011),樣本 1930–2009,月報酬 **0.93%**,t=**8.22** | 未下載進本票的 `op` 實跑清單,**未核實**(SignalDoc 有登記,Stock Weight=EW、十分位) |

**對 Karst 的意義**:`IndMom` 需要「二位數產業分類」這項 Karst 現有數據管線目前沒有的輸入——上一輪 KARST-074(101 Alphas 調研)已經點出同一個缺口(26 條 indneutralize 公式一樣卡在沒有免費美股行業分類),兩票疊加起來看,**行業分類數據源調研應該提前優先度**,不只是 101 Alphas 那條線要,相對強弱這一類經典效應也要;`ResidualMomentum` 不需要行業分類,只需要市場/風格因子的基準報酬序列(可以用簡化的大盤指數報酬近似,不必是正式 Fama-French 三因子),門檻比 `IndMom` 低,**可以優先做這條,`IndMom` 排在行業分類數據源票確認之後**。

---

## 三、JKP 同名因子對照(CC BY-NC)

出處:[jkpfactors.com](https://jkpfactors.com/)、[GitHub bkelly-lab/ReplicationCrisis — Cluster Labels.csv](https://github.com/bkelly-lab/ReplicationCrisis/blob/master/GlobalFactors/Cluster%20Labels.csv)(本票已完整取得這份 153 行的特徵×群組對照表)、Jensen, Kelly & Pedersen (2023),*Is There a Replication Crisis in Finance?*,Journal of Finance。

**授權提醒(沿用 KARST-074 已查結論,本票不重查)**:JKP **數據本身 CC BY-NC 4.0(僅限非商業使用)**,分析程式碼另外 MIT——跟 OSAP(只要求引用、沒有非商業限制)不同,Karst 若日後有商業化路徑,兩套的可用範圍不對等。

| 效應類別 | OSAP 訊號 | JKP 對應變數 | JKP 分群(Cluster) | 備註 |
|---|---|---|---|---|
| 反轉(短期) | STreversal | **`ret_1_0`** | Short-Term Reversal | 前一個月報酬,定義與 OSAP 幾乎一致 |
| 反轉減弱/長期端 | LRreversal | **`ret_60_12`** | (JKP 官方分群列為 Investment,非 Momentum/Reversal,命名與分群不一致,**未進一步查證原因**) | 60 個月減 12 個月窗口的報酬,窗口設計跟 LRreversal 的邏輯相近但不完全相同(OSAP 是 t-36 到 t-13,JKP 是更長的 t-60 到 t-12),**未核實**兩者是否算同一件事 |
| 波幅(偏度) | ReturnSkew | **`rskew_21d`** | Short-Term Reversal(JKP 把偏度類特徵歸入反轉群,不是波幅群) | 21 日日報酬偏度,定義相近 |
| 波幅(特異) | IdioVol3F | **`ivol_ff3_21d`**(以及 `ivol_capm_21d`/`ivol_hxz4_21d` 其他基準模型版本) | Low Risk | JKP 用 21 日窗口,OSAP 用「上個月」(約等於 21 個交易日),量級口徑接近 |
| 波幅(極值) | MaxRet | **`rmax1_21d`**(以及 `rmax5_21d`——過去 21 日前 5 大單日報酬均值,OSAP 沒有直接對應) | Low Risk | 定義一致 |
| 波幅(整體) | RealizedVol | **`rvol_21d`** | Low Risk | 21 日日報酬標準差,OSAP 版本額外做了 CAPM 殘差化,JKP 這條看起來更接近原始波動度(**未逐字核對 JKP 文檔確認是否也殘差化,未核實**) |
| 成交量 | DolVol | **`dolvol_126d`** | Size(JKP 把成交金額歸入規模群,不是成交量群) | 126 日成交金額均值,窗口比 OSAP 的兩個月長 |
| 成交量趨勢 | VolumeTrend | 沒有查到直接同名項,較接近的是 **`dolvol_var_126d`**(126 日成交金額的變異度) | Profitability(分群名稱跟內容明顯不搭,**JKP 這條分群疑似有誤或本票理解有誤,未核實**) | 不是同一個公式(變異度 vs 線性趨勢係數),只能算方向相近,不算同名對照 |
| 動量(12 個月) | Mom12m | **`ret_12_1`** | Momentum | 定義一致(t-12 到 t-1) |
| 動量(6 個月) | Mom6m | **`ret_6_1`** | Momentum | 定義一致,JKP 另有 `ret_3_1`/`ret_9_1` 補中間窗口,OSAP 沒有對應的 3/9 個月版本 |
| 相對強弱(行業) | IndMom | **沒有查到對應項** | — | JKP 153 條全部是個股層級特徵,**沒有做行業聚合的動量**;JKP 有 `qmj`(quality-minus-junk)一類複合指標但性質不同,不能當替代;這是本節查到最明確的一個空缺 |
| 相對強弱(對模型) | ResidualMomentum | **`resff3_12_1`**(以及 `resff3_6_1`) | Momentum | 定義吻合(FF3 殘差動量),JKP 額外提供 6 個月窗口版本 |

**小結**:反轉、動量、波幅三類 JKP 都有清楚對應,命名慣例是「變數名前綴+回看窗口」(`ret_12_1`、`rvol_21d` 這種),方便日後程式化對照;**成交量趨勢與行業相對強弱兩項在 JKP 沒有查到乾淨的同名對應**,若要做「兩套對照庫互相印證」,這兩項只能靠 OSAP 單邊,或者自己另外定義。JKP 的分群(Cluster)欄位有幾處跟本票直覺分類對不上(例如把偏度歸入 Short-Term Reversal、成交量歸入 Size),**本票沒有查證 JKP 論文正文對這個分群邏輯的解釋,標示未核實,只依字面對照公式**。

---

## 四、Karst 要補什麼

出處:`karst/engine/contracts.py`、`karst/factorpredict.py` docstring、`.kira/decisions.md` D-021/D-022/D-032、`CONTEXT.md` 相關詞條、`experiments/2026-08-29-factor-ic/README.md`。

1. **月度節奏**:`karst/engine/contracts.py` 第 22 行 `CADENCES: Final[frozenset[str]] = frozenset({"daily", "weekly", "monthly", "quarterly"})`——**月度換倉這個型別已經存在,不用新增列舉值**。但這只是「引擎接受這個字串」,**月度數據快照(K 線月度重採樣,或原生月度股價)是否已經在 Karst 數據管線裡備妥,本票未查證,標示未核實**——建置票要先確認這一步,不能假設 CADENCES 有登記就代表整條管線已經打通。
2. **橫斷面分組多空組合回報這種量法,現在完全沒有**——`karst/factorpredict.py` 現有的是 `align_factor_to_forward_returns`(對齊)、`daily_ic`(逐日 Spearman 等級相關)、`rolling_icir`(滾動 ICIR)、`summarize_ic`(彙總),四個函式全部圍繞「IC」這一種量法,**沒有「按因子值分十分位/五分位、算每組未來報酬、做多空價差」這種量法**——這正是本票第二、三節逐條列的 OSAP/JKP 公布數字用的量法,兩者不是同一件事:IC 量的是「排名相關度」,多空組合報酬量的是「真的按這個訊號分組交易會賺多少」。要跟 OSAP/JKP 公布的量級做蘋果對蘋果核對,**必須新增這種量法**,不能拿現有的 IC 結果硬套。
3. **因子表能否直接承載月度因子(雙時間戳照舊)**——按 D-021 的三個時點(事件時點/知情時點/可執行時點)與 D-032 的批次 parquet 設計,結構本身跟頻率無關(一批因子值 = 數據快照 × 因子版本,不限定日線),**本票判斷可以直接承載月度因子,不用改架構**,但這是根據合約文字推論,**沒有實際跑一次月度因子入庫核對,標示未核實**,建置票要補一次實測驗證這個推論。
4. **宇宙**:標普 500 歷史成分 625 隻(KARST-065)夠不夠——本票查到的四類效應原始論文(Jegadeesh 1990、Jegadeesh & Titman 1993、De Bondt & Thaler 1985、Grinblatt & Moskowitz 1999 等)**全部用的是 CRSP 全市場樣本,含大量中小盤股,不是只有大盤股**。標普 500 是市值最大的 500 家,系統性排除了小盤股;學術文獻裡不少經典異常(尤其反轉、動量)在小盤股的強度明顯高於大盤股(這是資產定價文獻常見的模式,但本票沒有專門查一篇「逐一比較這五類效應在大盤股 vs 全市場強度差幾多倍」的論文,**標示未核實,只是提醒這個系統性落差存在**)。**建議**:第一輪先在標普 500 上跑(數據已備妥、成本低),但交代結果時要明講「若在全市場(含小盤股)上跑,量級可能比這裡看到的更強」,不能讓標普 500 的結果被誤讀成「這批效應的真實強度上限」。

---

## 五、結語:建議路徑與建置票拆法

### 5.1 建議先算的 10 條純價量訊號

| 序 | 訊號 | 對應效應類別 | 只需價量 | OSAP 全樣本年化(本票實跑) | t 值 |
|---|---|---|---|---|---|
| 1 | STreversal | 反轉 | 是 | 33.74% | 13.95 |
| 2 | Mom12m | 動量 | 是 | 10.80% | 3.77 |
| 3 | Mom6m | 動量(輔助窗口) | 是 | 7.78% | 2.96 |
| 4 | IndMom | 相對強弱(行業) | 是(**要行業分類,見第四節第 4 點缺口**) | 4.30% | 3.84 |
| 5 | DolVol | 成交量異常 | 是 | 8.47% | 4.14 |
| 6 | VolumeTrend | 成交量異常 | 是 | 6.74% | 5.57 |
| 7 | MaxRet | 波幅異常(極值) | 是 | 7.50% | 2.93 |
| 8 | RealizedVol | 波幅異常 | 是(需市場基準序列) | 5.16% | 2.07 |
| 9 | IdioVol3F | 波幅異常(特異) | 是(需 FF3 基準序列) | 6.15% | 2.75 |
| 10 | ReturnSkew | 波幅異常(偏度) | 是 | 5.83% | 7.96 |

**反轉減弱不獨立成一條**——按第 2.2 節建議,用 STreversal 本身在多個持有窗口(1、3、6、12、36 個月)重跑一次,觀察強度曲線,`LRreversal`/`MomRev` 留作日後補跑的對照點(不進首輪 10 條,避免超出建議條數上限)。`ResidualMomentum`(相對強弱、對模型)可以列為第 11 條候補,門檻比 `IndMom` 低(不需要行業分類),若行業分類數據源遲遲確認不了,可以先頂上。

### 5.2 用 OSAP 公布回報核對的做法

`SignalDoc.csv` 的 `Stock Weight`(EW=等權/VW=市值加權)與 `LS Quantile`(0.1=十分位、0.2=五分位、0.3=三分位)兩欄,是 OSAP 官方複現原始論文時用的權重與分組方法,本票已逐條查出(第二節表格未逐一列這兩欄,匯總如下,供建置票直接照抄):STreversal/Mom12m/Mom6m/DolVol/VolumeTrend/IndMom 用**等權**,MaxRet/RealizedVol/IdioVol3F 用**市值加權**;分位數上 Mom12m/Mom6m/STreversal/MaxRet 用十分位、IdioVol3F/RealizedVol/VolumeTrend/ReturnSkew 用五分位、IndMom 用三分位。**核對做法**:Karst 自己算出因子值後,按同一個權重法與同一個分位數切法做多空組合,月報酬序列跟 OSAP 的 `PredictorPortsFull` 同一條訊號的 `LS` 序列對齊比較——如果同一個月份、同一個方向,量級差幾倍以上,大機率是公式或對齊時點寫錯,不是市場結構差異;如果方向一致、量級差在合理範圍(幾成上下),才進一步討論是宇宙不同(標普 500 vs 全市場)還是樣本期不同的解釋。

### 5.3 建置票拆法(每張一程)

0. **行業分類數據源調研票**(先於 IndMom 相關票)——跟 KARST-074(101 Alphas)第 0 項是同一個缺口,兩條線可以合併成一張票一次查清:美股大盤股有沒有免費、覆蓋 12 年以上的行業分類(GICS 或 SIC),沒有的話 IndMom 這條先跳過,改先做 ResidualMomentum。
1. **橫斷面多空組合回報量法實作票**——在 `karst/factorpredict.py` 旁邊新增分位分組、等權/市值加權多空組合報酬的計算函式,對接現有 `karst.factorstore` 長表與 `karst.data.snapshots` 面板,介面設計參考現有 `daily_ic`/`summarize_ic` 的形狀。
2. **10 條經典訊號 pandas 實作票**——照第二節公式清單自寫,不裝任何現成套件(沿用「業務先行、不預設自建」原則,公式本身是公開發表的定義,照抄即可);月度重採樣(如尚未備妥)一併在這張票確認。
3. **標普 500 × 10 條訊號多空組合實測票**——用第 5.2 節的核對做法,跟 OSAP 公布數字對齊比較,產出一份跟 KARST-066 同等級的實測結語。

### 5.4 實測前要向用戶交代的預期量級(逐條數字與出處)

**全部十條的公布量級已經整理在第 5.1 節表格,出處是本票自己從 OSAP `PredictorPortsFull` 實跑算出的 1926–2024 年化報酬與 t 值**(方法見本文開頭「方法說明」)。心理準備要點:(1) 這批數字是**近百年的全樣本、全市場(CRSP)**多空組合報酬,Karst 若第一輪在**標普 500、較短樣本期**上跑,量級大機率會低於這裡列的數字(方向沿用第四節第 4 點的判斷:標普 500 排除小盤股,而小盤股通常是這類異常的主要來源);(2) 十條裡強弱差很遠——STreversal 一枝獨秀(年化 33.7%),High52 幾乎不顯著(t≈0.2,本票決定不列入首輪 10 條的原因之一,已在第二節表格點出但未列入 5.1 建議清單);(3) 這是**月度多空組合報酬**,跟 Karst 自己在 Alpha158 測到的**逐日 IC**(KARST-066,標普 500 上 158 條無一達 0.02)是兩種不同的量法,**不能直接放在同一把尺上比大小**,只能各自參考。

---

## 六、六至八類(基本面、行業、估值)——只列數據源方向,不深查

按 D-033 用戶裁決,這三類本票只帶一句:

- **月度基本面量化**:OSAP `SignalDoc.csv` 裡 `Cat.Data=Accounting` 的訊號有 **196 條**(佔 331 條裡的多數),涵蓋估值比率、應計項目、投資成長率等一大批財報衍生特徵——這是免費 209 條特徵裡的主力,數據源已經在手(OSAP 本身),只是需要另開票逐條篩選跟 Karst 現有財報數據對得上的部分。
- **行業量化**:OSAP/JKP 本身沒有提供行業分類這項數據(兩者的訊號都是「用了行業分類做輸入」,不是「提供行業分類數據本身」)——這是本票第四節已點出的缺口,要另開數據源調研票(GICS/SIC 是否有免費美股來源),跟 KARST-074 第 0 項合併處理。
- **估值模型(DCF 一類)量化**:OSAP `Cat.Economic=valuation` 有 **30 條**訊號(如 `fcf_me`、`ebitda_mev` 一類財報衍生的估值比率),但這批是「用會計數字算出來的估值比率」,不是「跑一個完整 DCF 模型算出隱含價值再跟市價比」這種嚴格意義的 DCF——OSAP/JKP 都沒有現成的 DCF 隱含價值數據,若要做嚴格的 DCF 量化,需要另外找分析師預測(Analyst 類,OSAP 有 21 條)或自建現金流預測模型,超出本票查證範圍。

---

## 未完全核實事項清單

- OSAP 官網「數據本身」授權判斷以「只要求引用、沒查到非商業限制字眼」為準,沒有查到一頁專門的正式法律條款文字,建議實際引用前人手再上網站頁腳確認一次。
- `PredictorPortsFull.csv` 全量(212 條訊號)的檔案大小未實際下載核實,本票只下載了 14 條訊號的子集(7.5MB)。
- `deciles_ew`/`deciles_vw`/`ex_nyse_p20_me`/`nyse`/`ex_price5`/`quintiles_ew`/`quintiles_vw` 七個替代組合檔的大小未逐一下載核實。
- LRreversal、MomRev、ResidualMomentum 三條的 OSAP 全樣本多空組合報酬(本票自己實跑那一欄)未下載,只有原始論文公布的數字,原因是本票下載 `op` 時只挑了 14 個目標訊號的子集,未涵蓋這三條。
- IdioVolAHT、IdioVolCAPM、IdioVolQF 三條(ticket 原文「IdioRisk」對應的候選)本票未逐一查證量級,只確認了 IdioVol3F 一條。
- JKP 的 Cluster 分群邏輯(例如把偏度歸入 Short-Term Reversal、成交量歸入 Size)本票沒有查證 JKP 論文正文的解釋,只依字面公式對照,標示為未核實的分群疑點。
- `ret_60_12`(JKP)是否真的等同 LRreversal(OSAP)的長期反轉概念,兩者窗口定義不完全一樣(t-60至t-12 vs t-36至t-13),未逐字核對 JKP 官方文檔確認。
- Karst 月度 K 線快照是否已備妥、因子表月度入庫是否實際跑得通,本票只按合約文字推論「應該可以」,未實跑驗證。
- 標普 500 vs 全市場,這五類效應強度差幾倍,沒有查到一篇專門逐一比較的論文,只是按資產定價文獻常見模式(小盤股異常通常更強)做提醒,非直接出處。

## 出處總表

- [openassetpricing.com](https://www.openassetpricing.com/)、[openassetpricing.com/data](https://www.openassetpricing.com/data/)
- [PyPI openassetpricing](https://pypi.org/project/openassetpricing/)
- [CRAN OpenSourceAP.DownloadR](https://cran.r-project.org/web/packages/OpenSourceAP.DownloadR/index.html)
- Chen, Andrew Y. and Tom Zimmermann (2022), *Open Source Cross-Sectional Asset Pricing*, Critical Finance Review 11(2): 207–264(OSAP 官方引用要求)
- [jkpfactors.com](https://jkpfactors.com/)
- [GitHub bkelly-lab/ReplicationCrisis — Cluster Labels.csv](https://github.com/bkelly-lab/ReplicationCrisis/blob/master/GlobalFactors/Cluster%20Labels.csv)
- Jensen, Theis Ingerslev, Bryan Kelly, and Lasse Heje Pedersen (2023), *Is There a Replication Crisis in Finance?*, Journal of Finance 78(5): 2465–2518
- Jegadeesh, N. (1990), *Evidence of Predictable Behavior of Security Returns*, Journal of Finance 45(3): 881–898(STreversal)
- De Bondt, W. and R. Thaler (1985), *Does the Stock Market Overreact?*, Journal of Finance 40(3): 793–805(LRreversal)
- Chan, K. and K. Ko (2006)(MomRev)——本票僅依 `SignalDoc.csv` 轉引,未查原文期刊出處
- Brennan, M., T. Chordia, and A. Subrahmanyam (1998), *Alternative factor specifications, security characteristics, and the cross-section of expected stock returns*, Journal of Financial Economics 49(3): 345–373(DolVol)
- Haugen, R. and N. Baker (1996), *Commonality in the determinants of expected stock returns*, Journal of Financial Economics 41(3): 401–439(VolMkt、VolumeTrend)
- Bali, T., N. Cakici, and R. Whitelaw (2011), *Maxing out: Stocks as lotteries and the cross-section of expected returns*, Journal of Financial Economics 99(2): 427–446(MaxRet)
- Ang, A., R. Hodrick, Y. Xing, and X. Zhang (2006), *The Cross-Section of Volatility and Expected Returns*, Journal of Finance 61(1): 259–299(RealizedVol、IdioVol3F)
- Bali, T., R. Engle, and S. Murray (2015)(ReturnSkew)——本票僅依 `SignalDoc.csv` 轉引
- George, T. and C. Hwang (2004), *The 52-Week High and Momentum Investing*, Journal of Finance 59(5): 2145–2176(High52)
- Jegadeesh, N. and S. Titman (1993), *Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency*, Journal of Finance 48(1): 65–91(Mom12m、Mom6m)
- Grinblatt, M. and T. Moskowitz (1999), *Do industries explain momentum?*, Journal of Finance 54(4): 1249–1290(IndMom)
- Blitz, D., J. Huij, and M. Martens (2011), *Residual momentum*, Journal of Empirical Finance 18(3): 506–521(ResidualMomentum)
- 本倉背景:`research/2026-08-29-us-factor-sets.md`(KARST-074)、`research/2026-08-29-factor-horizon-evidence.md`(KARST-069)、`experiments/2026-08-29-factor-ic/README.md`(KARST-066)、`karst/factorpredict.py`、`karst/engine/contracts.py`、`.kira/decisions.md` D-021/D-022/D-032/D-033
