# 因子基建調研:業界因子定義與評估形態

- 票號:KARST-002
- 日期:2026-08-25
- 用途:為 KARST-003(因子合約)與 KARST-004(非結構化轉因子定義)墊底
- 前提:D-003(一切信號歸一為量化因子)、D-006(橫斷面選股為主體,不做日內)

---

## 摘要

三句話總結這次調研:

1. **業界對「因子」有共識,而且共識很窄。** 一個因子就是一張「(日期, 股票) → 一個數值」的表,再配一張同形狀的「未來回報」表。所有評估都建基於這兩張表的關係。三大工具(alphalens、qlib、vectorbt)分歧的是怎樣**產生**這張表,不是這張表**長什麼樣**。
2. **防止未來數據不是靠自律,是靠數據結構。** 通行做法是把「這件事發生於何時」與「我方何時知道這件事」分成兩個欄位,查詢一律以後者為準。qlib、Quantopian、以及 ML 界的 feature store 三邊獨立地收斂到同一個答案。
3. **非結構化材料轉因子有大量先例,但全部住在論文與商業數據商,不在開源框架裡。** 主流開源因子基建一律從「因子已經是一串數值」開始,沒有一個內建「文字 → 因子」這一層。這代表 KARST-004 沒有現成合約可以照抄,但有充足的形態可以參考。

---

## 一、業界怎樣正式定義一個因子

### 1.1 三種形態

| 工具 | 因子的表示法 | 數據形狀 | 適不適合橫斷面選股 |
|---|---|---|---|
| **alphalens** | 一個已算好的數值序列 | `pandas.Series`,MultiIndex:level 0 = 時間戳、level 1 = 股票 | **最貼** — 整個庫就是為橫斷面因子評估而寫 |
| **qlib** | 一條字串表達式 | 表達式在 `.bin` 欄位上求值,回傳同樣是 (instrument, datetime) 雙層索引 | **貼** — 內建橫斷面運算子與分層回測 |
| **vectorbt** | 一個 indicator 的輸出陣列 | 寬表:行 = 時間、列 = 資產或參數組合 | **不貼** — 逐列獨立計算,沒有橫斷面排序層 |

#### alphalens:因子 = MultiIndex Series

alphalens 的入口函數 `get_clean_factor_and_forward_returns` 對輸入形狀有硬性要求:

- `factor`:「A MultiIndex Series indexed by timestamp (level 0) and asset (level 1), containing the values for a single alpha factor.」——注意 **single**,一個 Series 只裝一個因子。
- `prices`:「A wide form Pandas DataFrame indexed by timestamp with assets in the columns.」文件另註明價格數據必須**超出因子期間**(否則算不出前瞻回報),而且應該反映「在該因子時間戳對應時點的買入價」。
- `periods`:`Sequence[int]`,要計算幾期的前瞻回報(例如 `(1, 5, 10)`)。
- `quantiles` / `bins`:分層方式,二選一,不可同時給。`quantiles` 是等量分桶(預設 5),`bins` 是等寬分桶。
- `max_loss`:允許丟棄的資料比例上限(0.00–1.00),超過就報錯。這是一道**靜默失敗防護**:如果因子與價格對不上而大量資料被丟掉,它會叫停而不是照樣出一份漂亮但無意義的報告。

輸出的 `factor_data` 是一張 DataFrame,欄位為:前瞻回報欄(以 `pd.Timedelta` 命名,例如 `1D`、`5D`)、`factor`(原值)、`group`(可選,例如行業)、`factor_quantile`(所屬分層)。

出處:[alphalens `utils.py` 原始碼](https://raw.githubusercontent.com/quantopian/alphalens/master/alphalens/utils.py)、[Alphalens API 文件](https://alphalens.ml4trading.io/api-reference.html)

**值得抄的一點**:alphalens 把「因子值」與「前瞻回報」在同一張表對齊,而且對齊這件事由庫負責、不由使用者負責。這正是最容易出錯的地方(見第二節)。

#### qlib:因子 = 表達式

qlib 不要求你先算好因子,它要求你**描述**因子。資料層分三部分:

- `calendars/`:交易日曆(`day.txt`)
- `instruments/`:股票池(`all.txt`、`csi500.txt` 等)
- `features/`:每支股票每個欄位一個 `.bin` 檔,按頻率分開

因子用字串表達式宣告,由表達式引擎求值:

- `Ref($close, -1)` — 前一日收市價
- `Mean($close, 5)` — 5 日平均
- `Ref($close, 60) / $close` — 60 日回報,**中間結果不落地**

出處:[Qlib Data Layer 文件](https://qlib.readthedocs.io/en/stable/component/data.html)

qlib 的 `DataHandlerLP` 把處理分成三條流,這一點與 KARST-003 直接相關:

| 代號 | 內容 | 用途 |
|---|---|---|
| `DK_R` | 原始載入,未處理 | 除錯、查源 |
| `DK_I` | 經 `infer_processors` | **推論用**(生產出信號) |
| `DK_L` | 經 `infer_processors + learn_processors` | **訓練用** |

分開的理由是訓練與推論的合法處理不同:訓練時可以丟 NaN 列(神經網絡需要),推論時不可以丟——生產環境不能因為某支股票某日缺值就當它不存在。這是「單一定義、兩種視圖」的一個具體實作,對照 D-002 的「單一定義、無第二影像」。

出處:[Qlib Data Layer 文件](https://qlib.readthedocs.io/en/stable/component/data.html)

**外部因子怎樣入 qlib**:`scripts/dump_bin.py` 把 CSV 或 Parquet 轉成 `.bin`。文件明言:「If you want to use your own alpha-factor which can't be calculated by OCHLV, like PE, EPS and so on, you could add it to the CSV or Parquet files with OHCLV together and then dump it to the Qlib format data.」——**這就是非結構化因子入 qlib 的門**:先在外面算成 (日期, 股票, 數值) 三欄表,再 dump 進去,之後與價量因子平起平坐。

出處:[Qlib Data Layer 文件](https://qlib.readthedocs.io/en/stable/component/data.html)

#### vectorbt:沒有因子層,只有信號層

vectorbt 的 `IndicatorFactory` 把一個指標定義為三件事:輸入陣列(OHLCV 一類)、參數陣列(窗口大小一類)、輸出陣列。資料慣例是**行為時間、列為資產或回測實例**,每一列是一個獨立計算單位。給多個參數值時,工廠自動把參數組合疊成 MultiIndex 的額外列層級。輸出經比較方法(如自動生成的 `price_crossed_above()`)變成布林信號陣列,再餵給 `Portfolio.from_signals()`。

出處:[vectorbt IndicatorFactory 文件](https://vectorbt.dev/api/indicators/factory/)、[vectorbt Portfolio 文件](https://vectorbt.dev/api/portfolio/base/)

**關鍵發現(對 D-006 有直接影響)**:vectorbt 的指標工廠文件**完全沒有提及橫斷面排序或因子評估層**。它逐列獨立計算,每一列是一支股票或一組參數,列與列之間不互相排名。換言之,vectorbt 天然是「單標的擇時 + 參數掃描」的工具,不是選股工具。要用它做橫斷面選股,橫斷面那一層要自己在外面寫。這與 D-006「不做單股擇時、做選股」有結構性張力,應該在 KARST-001(回測框架調研)的評估表上明確記一筆。

### 1.2 因子與標籤是一對,不是一個

三個工具都反映同一件事:**光有因子值,評估不了任何東西**。因子必須配一個「未來回報」定義才成立。

- alphalens:由 `prices` + `periods` 自動生成前瞻回報欄。
- qlib:標籤與特徵一樣是表達式,在 handler 裡宣告。Alpha158 的預設標籤是 `Ref($close, -2)/Ref($close, -1) - 1`。

這條標籤公式值得逐字看。它算的是 **T+1 收市到 T+2 收市**的回報,不是 T 到 T+1。理由文件寫得很白:「when getting the T day close price of a china stock, the stock can be bought on T+1 day and sold on T+2 day」——T 日收市才拿到收市價,最快 T+1 才買得到,T+2 才賣得到。

出處:[Qlib Data Layer 文件](https://qlib.readthedocs.io/en/stable/component/data.html)、[microsoft/qlib issue #1514](https://github.com/microsoft/qlib/issues/1514)

**對 Karst 的意義**:標籤的位移量不是一個技術細節,而是**市場規則與策略執行方式的編碼**。qlib 那條 `-2/-1` 是 A 股 T+1 制度的產物;美股可以 T 日收市信號、T+1 開市買,位移量不同。KARST-003 的因子合約應該把「這個因子的信號在何時可以被執行」列為一個**必填欄位**,而不是留給回測引擎預設。

### 1.3 表達式派 vs 已算好派

業界對「因子應該是一條公式還是一串數值」有兩派,兩派各有代表作:

- **公式派**:WorldQuant 的《101 Formulaic Alphas》(Kakushadze, 2016)把 101 個真實使用中的 alpha 寫成明文公式,運算子同時涵蓋時序與橫斷面兩類。`delay(x, d)` 是時序落後,`rank(x)` 是**橫斷面百分位排名**(對一張「列為股票、行為日期」的表逐行排名)。這些 alpha 的平均持倉期約 0.6 至 6.4 日。
  出處:[arXiv 1601.00991](https://arxiv.org/pdf/1601.00991)
- **數值派**:alphalens 完全不管因子怎樣來,它只收數值。

qlib 是公式派,alphalens 是數值派。**兩派可以並存**:公式派負責可審計、可重算、可自動搜索;數值派負責容納那些算不出公式的因子(外部數據、模型輸出、非結構化因子)。

**對 Karst 的意義**:樽頸因子(D-004)不可能寫成 OHLCV 的公式。所以 Karst 的因子合約**必須容納數值派**,但可以要求數值派因子額外交代「這串數值由什麼程序、什麼版本、什麼輸入產生」——即用元數據補回公式派天然具備的可審計性。這是 KARST-003 的核心設計問題。

### 1.4 儲存與版本

這一格業界做法最鬆散,沒有一個公認標準。觀察到的做法:

| 層次 | 做法 | 代表 |
|---|---|---|
| 因子數值儲存 | 每股票每欄位一個二進制檔,按頻率分目錄 | qlib `.bin` |
| 因子數值儲存 | 直接用 DataFrame / Parquet,不設專門格式 | alphalens、vectorbt |
| 版本與可重現 | 掛在**實驗管理**上,不是掛在因子上 | qlib `QlibRecorder` / `MLflowExpManager` |

qlib 的做法是:一個 `Recorder` 對應一個 MLflow run,`qrun` 由設定檔跑完整流程,把訓練、推論、評估階段產生的全部資訊與 artifacts 記錄下來,IC、Sharpe 一類指標作為 MLflow metrics 記錄。

出處:[Qlib Recorder 文件](https://qlib.readthedocs.io/en/stable/component/recorder.html)、[Qlib Workflow 文件](https://qlib.readthedocs.io/en/stable/component/workflow.html)

**誠實的結論**:業界沒有「因子版本控制」的成熟標準。有的是「實驗版本控制」——記錄某次跑動用了哪個設定檔。因子定義本身的版本,大家靠 git 管設定檔。

**對 Karst 的意義**:D-002 要求「所有定義單一正本、無第二影像」。業界現成方案答不到這條——qlib 的因子定義散在 handler 設定檔裡,alphalens 根本不管。這是 Karst 有理由自建的一格,而不是照抄的一格。

---

## 二、時點紀律(point-in-time)

這是本次調研最有收穫的一節。多個互不相干的領域獨立收斂到同一個答案。

### 2.1 通行做法的核心:兩個時間戳,不是一個

**每一筆數據要有兩個時間:它描述的時點,以及我方知道它的時點。查詢一律以後者為閘。**

四個獨立來源都是這個結構:

#### (a) qlib 的 PIT 資料庫

qlib 為財務報表數據另建一套儲存格式。理由文件寫得很直白:財務數據會被事後修訂,「If we only use the latest version for historical backtesting, data leakage will happen.」

每個特徵每一行四個欄位:

| 欄位 | 意思 |
|---|---|
| `date` | 該報表**公佈**的日期(我方何時知道) |
| `period` | 該數據所屬**報告期**(年度為年份整數,季度為 `YYYYQ`) |
| `value` | 數值 |
| `_next` | 指向該欄位下一次出現的位元組索引 |

檔名以 `_a.data`(年度)、`_q.data`(季度)區分,另有 `.index` 檔存每個報告期首次出現的位元組偏移量以加速查詢。

已知限制(文件自述):目前只為季度或年度因子而設。

出處:[Qlib PIT Database 文件](https://qlib.readthedocs.io/en/stable/advanced/PIT.html)

**注意 `_next` 這個欄位的設計意圖**:同一個報告期(例如 2024Q1)的數值可能出現多次——原始公佈一次、事後修訂再一次。`_next` 把同一報告期的多個版本串成鏈,查詢時可以問「在 X 日,2024Q1 的數字當時是多少」,而不是「2024Q1 的數字最終是多少」。**這正是「無第二影像」與「保留修訂史」兩個要求的調和方案**:正本只有一份(這條鏈),但這份正本本身記錄了時間維度。

#### (b) Quantopian 的 `asof_date` / `timestamp`

Quantopian 的 Pipeline 對所有數據集強制兩個時間欄位:

- `asof_date`:這筆數據**適用**於哪一日
- `timestamp`:Quantopian **系統何時知道**這筆數據

規則:「Pipeline does not surface data until the simulation date is after its timestamp.」

更值得注意的是它對歷史數據的誠實處理。以 PsychSignal(社交媒體情緒數據)為例:2016 年 1 月起,數據以真正 point-in-time 的方式每晚抓取儲存;**2016 年 1 月之前的歷史數據,`timestamp` 是用 `asof_date` 加 24 小時估算出來的**,並在文件上明確標示了一個「Point-In-Time Start」日期。

出處:[Quantopian PsychSignal 數據參考](https://www.quantopian.com/docs/data-reference/psychsignal)、[Quantopian Partner Data 說明](https://www.quantopian.com/posts/quantopian-partner-data-how-is-it-collected-processed-and-surfaced)
(註:Quantopian 已於 2020 年結業,原站文件多數不再可訪問;上述內容取自搜尋索引與 [社群存檔鏡像](https://quantopian-archive.netlify.app/)。)

**這是本報告最直接可以搬去 KARST-004 的一項。** 它是唯一一個把**非結構化衍生數據**(社交媒體情緒)當作一等公民、並為它訂明時點合約的公開平台先例。而且它示範了一個誠實的做法:**回填的時間戳要標明是回填的**,並公佈由哪一日起是真貨。

#### (c) ML 界的 feature store:as-of join

Feast(開源 feature store)的 `get_historical_features` 對每一筆「實體行」(帶 `event_timestamp`)做 AS OF join:回傳**有效時間戳小於或等於該實體行時間戳**的最新特徵值。另有 `ttl` 參數限制向後掃描的距離,且「the TTL time is relative to each timestamp within the entity dataframe」,不是相對於查詢當下。

文件的示範例子刻意展示兩種落空:一行因為早於所有特徵而落空,一行因為距最近特徵超過 TTL 而落空——**落空是正確行為,不是 bug**。

出處:[Feast Point-in-time joins 文件](https://docs.feast.dev/getting-started/concepts/point-in-time-joins)

`ttl` 這個概念對 Karst 有用:非結構化因子天然是**稀疏**的(一份分析員報告不是每日出),需要一條「一個舊值可以沿用多久」的規則。TTL 就是這條規則的形式化,而且它把「沿用」與「無限期沿用」分開了。

#### (d) 學術界的鈍器:固定落後期

Fama-French 的傳統做法:年度財務報表假定在**財政年度結束後六個月**才可投資,即以 `DATADATE + 6 個月` 為可得日期。由此推論,帳面市值比可能建基於**長達 18 個月前**的會計資訊。

出處:[Tidy Finance — Replicating Fama-French Factors](https://www.tidy-finance.org/python/replicating-fama-and-french-factors.html)、[Fama & French (1993), JFE 33:3-56](https://www.bauer.uh.edu/rsusmel/phd/Fama-French_JFE93.pdf)

這是刻意的過度保守:寧願浪費幾個月的資訊優勢,也不冒未來數據污染整個研究結論的風險。**當真正的 PIT 數據拿不到時,固定落後期是公認的退路。**

### 2.2 第二層防線:標籤位移

除了數據層的 PIT,標籤定義本身是第二道閘。前述 qlib 的 `Ref($close, -2)/Ref($close, -1) - 1` 是最清楚的示範:即使數據層完全乾淨,如果標籤算的是「T 日收市買、T+1 收市賣」,而現實上 T 日收市信號要 T+1 才買得到,回測依然是假的。

alphalens 的對應機制是 `prices` 參數的語義約定:文件要求 prices「should reflect the buy price at the time corresponding to each factor timestamp」——即使用者要自己保證傳入的價格是**可執行**的價格,而不是產生因子那一刻的價格。

出處:[alphalens `utils.py`](https://raw.githubusercontent.com/quantopian/alphalens/master/alphalens/utils.py)

**這是一個約定,不是一個檢查。** alphalens 沒法驗證你有沒有遵守。這正是 KARST-003 應該收緊的地方:把它由約定變成合約欄位。

### 2.3 第三層:LLM 特有的時點洩漏

這一層是傳統因子研究沒有的,對 KARST-004 直接相關。

**問題**:當因子由 LLM 產生,LLM 的訓練數據本身可能已經包含了它被要求預測的結果。這是一種數據層 PIT 完全防不到的洩漏——洩漏藏在模型權重裡,不在數據表裡。

**已有的檢測方法**:Gao、Jiang、Yan 提出 **Lookahead Propensity (LAP)** 指標:只給 LLM 日期與公司名(不給任何內容),估計它「已內化實際結果」的可能性,再檢驗 LAP 是否與預測準確度正相關。實證結果:「LAP is materially positive throughout the in-sample period and collapses essentially to zero right after the training-data cutoff.」——即訓練截止日之前,模型確實在偷看;截止日之後,偷看能力歸零。

出處:[arXiv 2512.23847 — Detecting Lookahead Bias in LLM Forecasts](https://arxiv.org/abs/2512.23847)

**已有的迴避做法**:Lopez-Lira 與 Tang 的研究刻意使用**訓練截止日之後**的新聞標題來評估 GPT-4,以繞開這個問題。

出處:[arXiv 2304.07619](https://arxiv.org/abs/2304.07619)

**對 Karst 的意義(必須進 KARST-004)**:非結構化因子若用 LLM 產生,回測的有效期上限**受制於模型的訓練截止日**。在截止日之前的回測結果,無論數據管道多乾淨,都要當作被污染。這不是一個可以靠工程解決的問題,只有三條路:(a) 只信截止日之後的樣本外表現;(b) 用不含世界知識的抽取式方法(例如詞典法、微調小模型);(c) 明確標示這段回測不可信並照樣做,但不用它作決策依據。**這一條值得考慮登記為假設**,因為它若成立,樽頸策略的歷史回測價值會大幅低於直覺預期。

---

## 三、評估形態(橫斷面選股因子)

業界的評估分兩段,順序不可倒:**先看因子本身有沒有預測力(信號層),再看拿它去建組合賺不賺錢(組合層)。**

qlib 把這兩段做成兩個獨立的 record 類:

- `SigAnaRecord` — 產出 IC、ICIR、Rank IC、Rank ICIR
- `PortAnaRecord` — 產出回測結果(含成本模型)

出處:[Qlib Recorder 文件](https://qlib.readthedocs.io/en/stable/component/recorder.html)、[qlib `record_temp.py`](https://github.com/microsoft/qlib/blob/main/qlib/workflow/record_temp.py)

### 3.1 信號層指標

| 指標 | 定義 | 答什麼問題 |
|---|---|---|
| **IC** | 因子值與 N 期前瞻回報的**Spearman 等級相關**,逐期計算 | 這個因子的排序,預不預測得到未來回報的排序? |
| **Rank IC** | 同上(qlib 把 Pearson IC 與 Rank IC 分開列) | 同上,對極端值不敏感的版本 |
| **ICIR** | IC 的平均值除以標準差 | 這個預測力**穩不穩定**?偶爾很準不算數 |
| **factor_rank_autocorrelation** | 因子排名在相鄰期之間的自相關 | 這個因子**轉得多快**?自相關低 = 高換手 = 高成本 |
| **quantile_turnover** | 某一分層中,上期不在該層的名字所佔比例 | 同上,分層視角 |

alphalens 的 `factor_information_coefficient` 明確定義為「Spearman Rank Correlation based Information Coefficient (IC) between factor values and N period forward returns」。

出處:[alphalens `performance.py`](https://raw.githubusercontent.com/quantopian/alphalens/master/alphalens/performance.py)

**IC 的量級**:等級相關,理論範圍 -1 至 1。業界對股票日頻因子的通行認知是 0.02–0.05 的 IC 已經是可用因子,0.1 以上要先懷疑數據有問題再高興。(此為業界常識,本次調研未取得權威出處,KARST-003 若要寫入門檻應另行查證。)

### 3.2 分層與組合層指標

| 指標 | 定義 | 答什麼問題 |
|---|---|---|
| **mean_return_by_quantile** | 各分層在各前瞻期的平均回報(附標準誤) | 因子與回報是不是**單調**的?第 5 層真的比第 1 層好? |
| **compute_mean_returns_spread** | 兩個分層平均回報之差 | 多空價差有多大,統計上顯不顯著 |
| **factor_returns** | 以因子值加權的組合逐期回報;可 demean 做**美元中性**,可按 group 調整做**行業中性** | 直接當一個組合來看,賺多少 |
| **factor_alpha_beta** | 對股票池平均回報做迴歸,得 alpha、alpha t 值、beta | 這個因子是真 alpha,還是只是市場暴露的變形? |

出處:[alphalens `performance.py`](https://raw.githubusercontent.com/quantopian/alphalens/master/alphalens/performance.py)

**兩點對 Karst 特別重要**:

1. **單調性比多空價差更重要。** 只看第一層減第五層,一個「只有極端兩層有效、中間亂七八糟」的因子看起來與一個真正單調的因子一樣好。分層圖是照妖鏡。這對樽頸策略尤其相關——如果樽頸因子只在極端值有效,那它是一個**事件觸發器**而不是一個**排序因子**,兩者的組合建構方式完全不同。
2. **中性化是評估的一部分,不是事後修飾。** alphalens 把 demean(美元中性)與 group adjust(行業中性)做成參數,意思是「這個因子扣除行業暴露之後還剩多少」是一個要當場回答的問題。一個科技股偏重的因子在科技牛市看起來很強,中性化之後可能什麼都不剩。

### 3.3 一個空白:非結構化因子的專屬評估指標

調研未發現任何工具為非結構化/稀疏因子提供專門指標。IC 一類指標假設**每期每股票都有值**;一個「只在有分析員報告出街時才有值」的因子,逐期 IC 的樣本數會極不穩定,把它們平均起來的 ICIR 意義存疑。這是一個 KARST-004 需要自己想清楚的問題,沒有現成答案可抄。

---

## 四、非結構化來源轉因子的先例

### 4.1 結論先講

**先例很多,但分佈極不平均:**

| 層次 | 有沒有先例 | 說明 |
|---|---|---|
| 學術論文 | **大量,方法成熟** | 由詞典法到 LLM,二十年累積 |
| 商業數據商 | **有,且已產品化** | RavenPack 等已把「文字 → 帶時間戳的因子」當商品賣 |
| 已結業的平台 | **有,且有正式時點合約** | Quantopian 的 PsychSignal |
| **現行開源框架** | **沒有** | qlib、alphalens、vectorbt 全部不含此層 |

**最重要的一項發現**:2025 年那一批「LLM alpha mining」開源專案(AlphaAgent、RD-Agent、QuantAgent 等)**名字有誤導性**。它們是用 LLM **生成公式**,公式的輸入依然是 OHLCV;它們不是把文字當因子輸入。詳見 4.4。

### 4.2 學術先例(方法論)

#### (a) SESTM — Ke、Kelly、Xiu

最完整的「新聞文字 → 橫斷面選股因子」方法論。三步:

1. 用**預測性篩選**挑出一批有情緒含意的詞
2. 用**主題模型**為這些詞分配情緒權重
3. 用**罰似然**把詞聚合成文章層級的情緒分數

實證用道瓊通訊社(Dow Jones Newswires)。結果值得注意:SESTM 情緒策略對標準風險因子的暴露極低——多空價差組合對 Fama-French 因子迴歸的日度 R² 最高只有 10%,「the average return of the strategy is almost entirely alpha」。

出處:[NBER Working Paper 26186](https://www.nber.org/papers/w26186)、[全文 PDF](https://www.nber.org/system/files/working_papers/w26186/w26186.pdf)、[AQR 版本](https://www.aqr.com/Insights/Research/Working-Paper/Predicting-Returns-with-Text-Data)

**形態上的關鍵**:它是**監督式**的——情緒詞表由「哪些詞預測得到回報」訓練出來,不是由人手預先定義。這與詞典法(見 (d))是根本分別。

#### (b) ChatGPT 標題評分 — Lopez-Lira、Tang

形態最接近 Karst 想做的事:**用通用 LLM 直接把文字打分,分數當因子用**。

做法:要 ChatGPT 判斷一則標題對該公司股價是好消息、壞消息還是無關,轉成數值分數,再與次日回報對照。結果:GPT-4 分數與後續日回報正相關;用訓練截止日之後的標題測試,對「不可交易的初始反應」達到約 90% 的組合-日命中率;GPT-4 分數亦顯著預測後續漂移,**在小型股與負面消息上尤其明顯**。GPT-1、GPT-2、BERT 做不到,顯示回報預測力是複雜模型的**湧現能力**。

出處:[arXiv 2304.07619](https://arxiv.org/abs/2304.07619)、[SSRN 4412788](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4412788)

#### (c) 逐字稿衍生的公司層指標 — Hassan、Hollander、van Lent、Tahoun

與樽頸策略(D-004,以逐字稿為主要輸入)形態最接近的學術先例。

做法:以季度業績電話會議逐字稿的文本分析,構造公司層級的政治風險指標,定義為**該次電話會議中用於討論政治風險的篇幅比例**(具體是「接近風險/不確定性用詞的政治性對話所佔百分比」)。

驗證方式值得抄:作者不只報告預測力,而是先證明該指標(i) 正確識別出確實大量討論政治風險的會議、(ii) 隨時間與行業的變化符合直覺、(iii) 與公司行動及股價波動的相關性符合政治風險的理論預期。

發表於 QJE 2019, 134(4): 2135-2202;數據集公開發佈。

出處:[NBER Working Paper 24029](https://www.nber.org/papers/w24029)、[數據集](https://www.policyuncertainty.com/firm_pr.html)、[SSRN 2838644](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2838644)

**對 KARST-004 最有用的一課**:這個指標的定義是**一個比例**——分子分母都講得清楚,可以由第三方在同一份逐字稿上重算並得到相同結果。這是「clear definition」(D-004 用戶原話)的一個具體標準:**別人拿著你的定義與同一份原材料,應該算得出同一個數。** 一個「叫 LLM 給樽頸程度打 1 至 10 分」的因子過不了這一關(LLM 每次跑分數會漂),一個「計算逐字稿中提及供應限制的段落佔比」的因子過得了。

#### (d) 詞典法 — Loughran-McDonald

金融文本情緒分析的基線方法:人手編製的金融領域情緒詞表。仍然是所有新方法的對照組。實務上常與 FinBERT 並用作雙軌對照。

出處:見 4.3 (b) 的開源實作

### 4.3 工具與開源實作

#### (a) FinBERT

金融領域微調的 BERT,做金融文本情緒分類。至少兩個獨立實作在用:

- [ProsusAI/finBERT](https://github.com/ProsusAI/finBERT) — 在金融語料上續訓 BERT 再微調做情緒分類
- [yya518/FinBERT](https://github.com/yya518/FinBERT) — 為金融通訊(financial communications)預訓練,[arXiv 2006.08097](https://arxiv.org/abs/2006.08097)

模型在 Hugging Face model hub 可直接取用。

#### (b) 端到端小型範例

[rj694/earnings-sentiment](https://github.com/rj694/earnings-sentiment) — 目前找到唯一一個公開的、完整的「逐字稿 → 情緒分數 → 與回報對照」管道,用 Loughran-McDonald 詞典 + FinBERT 雙軌,pandas + HuggingFace transformers + yfinance。

**結論值得正視**:找到 1 日約 ρ≈0.3 的信號,**到第 5 日消失**。

**但這個結論不可靠**:樣本只有 7 家大型股的 56 份逐字稿。這個規模下 ρ≈0.3 的標準誤很大,而且完全沒有橫斷面選股的意義(7 支股票排不出有意義的分層)。**引用時應標明為形態參考,不是證據。**

#### (c) 商業數據商 — RavenPack

已產品化的「文字 → 因子」流水線,其產品結構本身就是一份現成的規格藍圖:

- **Event Relevance Score (REL)**:0–100,按事件在新聞中出現的位置評分——越靠前分越高
- **Event Similarity Days (SIM)**:距上次偵測到相似事件的日數,即**新穎度**
- 為每家公司構造**兩類**因子:
  - **文件層因子** — 聚合所有以足夠相關度與新穎度提及該公司的文件
  - **事件層因子** — 只聚合該公司足夠相關且新穎的**已偵測事件**
- 記錄為 point-in-time,附情緒與媒體關注度分數

出處:[RavenPack Company News Factors](https://www.ravenpack.com/products/edge/factors/company-news)、[RavenPack News Analytics](https://www.ravenpack.com/products/edge/data/news-analytics)、[RavenPack NLP in Quant Investing](https://www.ravenpack.com/blog/natural-language-processing-quant-investing/)

**三個可以直接搬去 KARST-004 的概念**:

1. **相關度分數** — 一份材料提到某公司,不代表這份材料是關於該公司的。需要一個相關度閘。
2. **新穎度分數** — 同一件事被十家媒體轉載,不等於十個信號。沒有去重機制的文字因子會系統性高估。這對樽頸策略是致命的:一個供應短缺故事會在多份分析員報告中重複出現。
3. **文件層 vs 事件層的分工** — 前者是連續的「氛圍」量度,後者是離散的「發生了什麼」。兩者的稀疏度、TTL、評估方式都不同,不應混為一個因子。

### 4.4 LLM 驅動的因子挖掘 — 一個必須澄清的誤會

2025 年前後出現一批 LLM alpha mining 專案。**逐個查證後,它們與「非結構化材料轉因子」是兩件事。**

| 專案 | 實際做什麼 | 因子的輸入是什麼 |
|---|---|---|
| **AlphaAgent** | LLM 生成公式化 alpha,以 AST 表示,葉節點是原始特徵引用 | **OHLCV**,不是文字 |
| **RD-Agent(Q)** | LLM **讀研究報告與論文**,抽出數學式,譯成 qlib 因子語言,再 A/B 測試 | 報告是**因子想法**的來源,計算輸入仍是行情數據 |
| **QuantAgent** | writer agent 由交易員想法寫腳本,judge agent 給回饋,內外雙迴圈 | 同上 |

AlphaAgent 的細節值得記:因子評估用 IC、RankIC、IR、ICIR + qlib 回測(CSI 500 與 S&P 500,2015–2024);三項正則化約束是**原創性**(以子樹同構偵測量度與既有 alpha 的相似度)、**複雜度**(符號長度與自由參數個數)、**假說一致性**(LLM 評分市場假說、因子描述與數學式三者的語義一致性)。報稱在 CSI 500 年均超額回報 11.0%(IR=1.5)、S&P 500 為 8.74%(IR=1.05),扣除交易成本後。

出處:[arXiv 2502.16789](https://arxiv.org/html/2502.16789v2)、[GitHub RndmVariableQ/AlphaAgent](https://github.com/RndmVariableQ/AlphaAgent)、[microsoft/RD-Agent](https://github.com/microsoft/rd-agent)、[R&D-Agent-Quant 論文頁](https://www.microsoft.com/en-us/research/publication/rd-agent-quant-a-multi-agent-framework-for-data-centric-factors-and-model-joint-optimization/)、[LLM-based alpha mining 綜述 (FITEE)](https://link.springer.com/article/10.1631/FITEE.2500386)

**兩點可借的**(即使方向不同):

1. **RD-Agent(Q) 的「譯成 qlib 因子語言再 A/B 測試」是一個可抄的骨架**:LLM 負責提出,確定性的引擎負責裁決。LLM 不參與評分。
2. **AlphaAgent 的原創性正則化指出一個 Karst 會撞到的問題**:當因子可以被自動大量生成,「這個因子與已有因子是不是同一回事」變成必須形式化的問題。樽頸因子若做成一族而非一個,會立即需要這個。

### 4.5 明確講:查不到什麼

以下項目經搜尋後**未能找到**,列明以免下一個人重複查:

1. **沒有任何主流開源因子基建把「非結構化材料 → 因子」內建為一層。** qlib、alphalens、vectorbt 的文件與 API 全部從「因子已經是一串數值」開始。qlib 的 `dump_bin` 提供了入口,但入口之前的一切要自建。
2. **沒有找到一份公開的「非結構化因子合約」規格。** RavenPack 的產品文件最接近,但那是產品說明不是規格;Quantopian 的 `asof_date`/`timestamp` 是通用數據集規則,不是非結構化專屬。
3. **沒有找到針對稀疏/事件驅動因子的標準評估指標。** IC/ICIR 假設面板稠密,調研未見公認的稀疏版本。
4. **沒有找到 LLM 生成因子的可重現性(determinism)處理慣例。** 同一份材料同一個提示,LLM 兩次輸出可能不同——調研未見任何工具或論文為此訂明標準做法。這是 KARST-004 的一個真空區。
5. **IC 的「可用門檻」數值沒有取得權威出處。** 業界口耳相傳的 0.02–0.05 未能追溯到可引用的原始來源。

**查過的地方**:qlib 官方文件(readthedocs,stable 與 latest)、alphalens 原始碼與 API 文件、vectorbt 官方文件、Feast 文件、GitHub(microsoft/qlib、microsoft/RD-Agent、quantopian/alphalens、polakowo/vectorbt、AlphaAgent、FinBERT 諸實作)、arXiv、NBER、SSRN、Quantopian 存檔鏡像、RavenPack 產品文件、Tidy Finance。

---

## 五、對 KARST-003 / KARST-004 的具體提示

以下**不是決策**,是把調研結果整理成兩張票需要拍板的問題清單。

### 給 KARST-003(因子合約)

調研顯示一份因子合約至少要答這幾條:

| 欄位 | 業界依據 | Karst 的難處 |
|---|---|---|
| 數據形狀 | 全業界一致:(日期, 股票) → 數值 | 無爭議,直接採用 |
| 頻率 | qlib 按頻率分目錄 | 樽頸因子不是日頻,要處理混頻 |
| **可執行時點** | qlib 標籤位移、alphalens `prices` 語義約定 | **必填,不可留給引擎預設** |
| **知悉時點** | qlib PIT `date`、Quantopian `timestamp` | 每筆數值兩個時間戳 |
| 有效期 / TTL | Feast `ttl` | 稀疏因子必須有這條 |
| 稀疏度處理 | 無先例 | 要自己定 |
| 產生程序與版本 | qlib Recorder / MLflow(掛在實驗上,不掛在因子上) | D-002 要求單一定義,業界方案答不到 |
| 中性化要求 | alphalens `group_adjust` / demean | 決定是因子的屬性還是評估的參數 |

另一條需要拍板的分岔:**公式派 vs 數值派並存怎樣管**(見 1.3)。樽頸因子註定是數值派,價量因子可以是公式派。合約要不要一份還是兩份?

### 給 KARST-004(非結構化轉因子)

調研顯示這張票要正面回答的問題:

1. **可重現性標準是什麼?** Hassan 等人的政治風險指標定為「一個比例」,第三方可重算得同一數。LLM 打分做不到。要選:抽取式(可重算)還是判斷式(不可重算但更貼近人類理解)?若選後者,可重現性怎樣定義?(見 4.2(c)、4.5 第 4 點)
2. **LLM 訓練截止日怎樣處理?** 回測有效期上限受制於此,無工程解。(見 2.3)
3. **去重與新穎度怎樣做?** 同一個供應短缺故事出現在五份報告中,是五個信號還是一個?(見 4.3(c))
4. **相關度閘怎樣定?** 一份報告提到某公司不等於是關於該公司。(見 4.3(c))
5. **「氛圍」與「事件」要不要分開成兩種因子?** RavenPack 分開了,而且兩者的稀疏度與評估方式不同。(見 4.3(c))
6. **稀疏因子怎樣評估?** IC/ICIR 的假設不成立,無現成答案。(見 3.3、4.5 第 3 點)

### 給 KARST-001(回測框架調研)—— 一項應該轉告的發現

vectorbt 的 IndicatorFactory 沒有橫斷面排序或因子評估層,天然是單標的擇時 + 參數掃描工具。這與 D-006「做選股不做單股擇時」有結構性張力。建議在 KARST-001 的評估表上明確記一筆(見 1.1)。

### 一項建議登記的假設

**「非結構化因子的歷史回測結果可信」** —— 若 LLM 訓練截止日污染成立(見 2.3,已有 LAP 指標的實證支持),則樽頸策略在截止日之前的全部回測都不足以支撐決策,只有截止日之後的樣本外表現算數。**它若是假,樽頸策略的歷史驗證工作會白做。** 建議由 KARST-004 判斷是否正式登記入 `.kira/assumptions.jsonl`(本研究票不代為登記)。

---

## 六、出處總表

### 工具文件與原始碼
- [Qlib — Data Layer: Data Framework & Usage](https://qlib.readthedocs.io/en/stable/component/data.html)
- [Qlib — (P)oint-(I)n-(T)ime Database](https://qlib.readthedocs.io/en/stable/advanced/PIT.html)
- [Qlib — Recorder: Experiment Management](https://qlib.readthedocs.io/en/stable/component/recorder.html)
- [Qlib — Workflow Management](https://qlib.readthedocs.io/en/stable/component/workflow.html)
- [qlib `record_temp.py`](https://github.com/microsoft/qlib/blob/main/qlib/workflow/record_temp.py)
- [qlib `contrib/data/handler.py`(Alpha158/Alpha360)](https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/handler.py)
- [microsoft/qlib issue #1514 — Alpha158 標籤為何用兩日後收市價](https://github.com/microsoft/qlib/issues/1514)
- [alphalens `utils.py`](https://raw.githubusercontent.com/quantopian/alphalens/master/alphalens/utils.py)
- [alphalens `performance.py`](https://raw.githubusercontent.com/quantopian/alphalens/master/alphalens/performance.py)
- [Alphalens API Reference](https://alphalens.ml4trading.io/api-reference.html)
- [vectorbt — IndicatorFactory](https://vectorbt.dev/api/indicators/factory/)
- [vectorbt — Portfolio](https://vectorbt.dev/api/portfolio/base/)
- [Feast — Point-in-time joins](https://docs.feast.dev/getting-started/concepts/point-in-time-joins)
- [Quantopian — PsychSignal 數據參考](https://www.quantopian.com/docs/data-reference/psychsignal)(站已結業,經搜尋索引取得)
- [Quantopian 存檔鏡像](https://quantopian-archive.netlify.app/)

### 論文
- [Ke, Kelly, Xiu — Predicting Returns with Text Data (NBER w26186)](https://www.nber.org/papers/w26186)
- [Lopez-Lira, Tang — Can ChatGPT Forecast Stock Price Movements? (arXiv 2304.07619)](https://arxiv.org/abs/2304.07619)
- [Hassan, Hollander, van Lent, Tahoun — Firm-Level Political Risk (NBER w24029 / QJE 2019)](https://www.nber.org/papers/w24029)
- [Firm-Level Political Risk 數據集](https://www.policyuncertainty.com/firm_pr.html)
- [Kakushadze — 101 Formulaic Alphas (arXiv 1601.00991)](https://arxiv.org/pdf/1601.00991)
- [Gao, Jiang, Yan — Detecting Lookahead Bias in LLM Forecasts (arXiv 2512.23847)](https://arxiv.org/abs/2512.23847)
- [AlphaAgent (arXiv 2502.16789, KDD 2025)](https://arxiv.org/html/2502.16789v2)
- [R&D-Agent-Quant (Microsoft Research)](https://www.microsoft.com/en-us/research/publication/rd-agent-quant-a-multi-agent-framework-for-data-centric-factors-and-model-joint-optimization/)
- [A survey on large language model-based alpha mining (FITEE)](https://link.springer.com/article/10.1631/FITEE.2500386)
- [Fama & French (1993), JFE 33:3-56](https://www.bauer.uh.edu/rsusmel/phd/Fama-French_JFE93.pdf)
- [Tidy Finance — Replicating Fama-French Factors](https://www.tidy-finance.org/python/replicating-fama-and-french-factors.html)

### 開源專案與商業產品
- [microsoft/RD-Agent](https://github.com/microsoft/rd-agent)
- [RndmVariableQ/AlphaAgent](https://github.com/RndmVariableQ/AlphaAgent)
- [ProsusAI/finBERT](https://github.com/ProsusAI/finBERT)
- [yya518/FinBERT](https://github.com/yya518/FinBERT)
- [rj694/earnings-sentiment](https://github.com/rj694/earnings-sentiment)
- [RavenPack — Company News Factors](https://www.ravenpack.com/products/edge/factors/company-news)
- [RavenPack — News Analytics](https://www.ravenpack.com/products/edge/data/news-analytics)
- [RavenPack — NLP in Quant Investing](https://www.ravenpack.com/blog/natural-language-processing-quant-investing/)
