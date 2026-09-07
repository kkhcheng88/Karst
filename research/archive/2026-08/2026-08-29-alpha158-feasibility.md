# Alpha158 因子庫可行性調研

- 票號:KARST-062
- 日期:2026-08-29
- 用途:回應用戶 2026-08-29 提出「先掃 Alpha158 或 360」的建議,查清楚把 Alpha158 搬入 Karst 因子表要走哪條路、成本多大、缺什麼數據。

---

## 摘要(五句起)

1. **Alpha158 全部 158 條因子只需日線開高低收量(OHLCV)加一項成交量加權平均價(VWAP),不用任何額外數據源就算得出**——這對 Karst 現有數據管線是好消息。
2. **不裝 qlib 也能借到現成 pandas 實作,但不多。** 網上搜到的替代方案要麼不含 Alpha158(如 DoubleAdapt),要麼是把公式重寫成 C++ 求快(KunQuant)。最務實的做法是照抄 qlib 官方原始碼裡的**公式定義**(表達式是公開文字,不是要「裝」的軟件),自己用 pandas/numpy 把約 30 種運算子(Mean、Std、Corr、Rank 一類)寫成函數——這是抄公式,不是抄程式碼庫。
3. **算力與儲存都在小型筆電可承受的範圍。** 158 因子 × 500 隻股票 × 3,000 個交易日 ≈ 2.4 億格,存成 parquet 大約幾百 MB;逐因子用 pandas 向量化滾動運算,估計以分鐘計,不用分散式運算。
4. **免費來源可以避開存活者偏差,但要接兩個來源、不是一個。** 免費且維護中的標普 500 成分歷史 GitHub 數據集存在,但終止代號的日線價格,yfinance 覆蓋不完整,要另找退市股價格源或接受缺口。
5. **Karst 現有「因子檢視」畫面缺的是逐因子 IC 面板,不是整套 alphalens。** 建議自寫一個薄的 IC 計算層直接對接 Karst 的雙時間戳因子表,不整套引入 alphalens(它的輸入形狀假設單一時間戳,對不上 Karst 的知情時間/事件時間合約)。

**建議路徑一句可裁**:照抄 Alpha158 的公式定義自寫 pandas 版本(不裝 qlib),先在起步宇宙十二隻股票加一份標普 500 成分歷史數據源上落地驗證,IC 面板自寫對接因子表雙時間戳,退市股缺口在報告上明確標示、不假裝完整。

---

## 一、Alpha158 的 158 條表達式清單與分組

出處:[qlib `contrib/data/loader.py`](https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/loader.py)、[qlib `contrib/data/handler.py`](https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/handler.py)

Alpha158 由 `Alpha158DL` 這個載入器類別定義,分四組:

### 1.1 K 線形態組(9 條,固定不分窗口)

以開市價 `$open` 歸一化(部分再除以振幅 `$high-$low` 歸一化第二次):

| 代號 | 公式 | 意思 |
|---|---|---|
| KMID | `($close-$open)/$open` | 實體漲跌幅 |
| KLEN | `($high-$low)/$open` | 振幅 |
| KMID2 | `($close-$open)/($high-$low+1e-12)` | 實體佔振幅比例 |
| KUP | `($high-Greater($open,$close))/$open` | 上影線長度 |
| KUP2 | `($high-Greater($open,$close))/($high-$low+1e-12)` | 上影線佔振幅比例 |
| KLOW | `(Less($open,$close)-$low)/$open` | 下影線長度 |
| KLOW2 | `(Less($open,$close)-$low)/($high-$low+1e-12)` | 下影線佔振幅比例 |
| KSFT | `(2*$close-$high-$low)/$open` | 收市偏移量 |
| KSFT2 | `(2*$close-$high-$low)/($high-$low+1e-12)` | 收市偏移比例 |

九條全部只用 `$open $high $low $close` 四欄,日線 OHLCV 直接算得出。

### 1.2 價格組(以現時收市價歸一化)

`OPEN HIGH LOW CLOSE VWAP` 五個欄位,各自的表達式為 `Ref($field, d)/$close`(過去第 d 日的值除以今日收市)。**VWAP(成交量加權平均價)不是原始 OHLCV 五欄裡的一欄**——多數日線數據源(yfinance 一類)不直接提供逐日 VWAP,要自己用 `(高+低+收)/3` 一類近似公式代算,或乾脆從清單剔走這一條。這是唯一一個超出「純 OHLCV」的缺口,影響小(158 條中頂多幾條)。

### 1.3 成交量組

`VOLUME` 一欄,表達式 `Ref($volume, d)/($volume+1e-12)`,只用 `$volume`。

### 1.4 滾動窗口組(28 種運算子 × 5、10、20、30、60 五個窗口)

| 代號 | 公式樣板 | 答什麼問題 | 只需 OHLCV? |
|---|---|---|---|
| ROC | `Ref($close,d)/$close` | d 日前價與今價比 | 是 |
| MA | `Mean($close,d)/$close` | d 日均價 | 是 |
| STD | `Std($close,d)/$close` | d 日波動度 | 是 |
| BETA | `Slope($close,d)/$close` | d 日價格斜率 | 是 |
| RSQR | `Rsquare($close,d)` | 斜率擬合優度 | 是 |
| RESI | `Resi($close,d)/$close` | 迴歸殘差 | 是 |
| MAX | `Max($high,d)/$close` | d 日高位 | 是 |
| MIN | `Min($low,d)/$close` | d 日低位 | 是 |
| QTLU | `Quantile($close,d,0.8)/$close` | 80 百分位價 | 是 |
| QTLD | `Quantile($close,d,0.2)/$close` | 20 百分位價 | 是 |
| RANK | `Rank($close,d)` | 今價在過去 d 日中的名次 | 是 |
| RSV | `($close-Min($low,d))/(Max($high,d)-Min($low,d)+1e-12)` | 隨機值(KDJ 的 RSV) | 是 |
| IMAX | `IdxMax($high,d)/d` | 高位距今幾日 | 是 |
| IMIN | `IdxMin($low,d)/d` | 低位距今幾日 | 是 |
| IMXD | `(IdxMax($high,d)-IdxMin($low,d))/d` | 高低位相隔幾日 | 是 |
| CORR | `Corr($close,Log($volume+1),d)` | 價量相關 | 是 |
| CORD | `Corr($close/Ref($close,1),Log($volume/Ref($volume,1)+1),d)` | 報酬與量變相關 | 是 |
| CNTP | `Mean($close>Ref($close,1),d)` | 上漲日佔比 | 是 |
| CNTN | `Mean($close<Ref($close,1),d)` | 下跌日佔比 | 是 |
| CNTD | CNTP − CNTN | 漲跌日淨佔比 | 是 |
| SUMP | `Sum(漲幅,d)/Sum(絕對變動,d)` | 上升動能佔比(近似 RSI) | 是 |
| SUMN | `Sum(跌幅,d)/Sum(絕對變動,d)` | 下跌動能佔比 | 是 |
| SUMD | SUMP − SUMN | 淨動能 | 是 |
| VMA | `Mean($volume,d)/($volume+1e-12)` | d 日均量 | 是 |
| VSTD | `Std($volume,d)/($volume+1e-12)` | 量的波動度 | 是 |
| WVMA | `Std(\|報酬\|×量,d)/Mean(\|報酬\|×量,d)` | 量價背離度 | 是 |
| VSUMP/VSUMN/VSUMD | 同 SUMP/SUMN/SUMD 但作用在成交量變動上 | 量的動能 | 是 |

28 種 × 5 個窗口 = 140 條,加上 K 線 9 條、價格與成交量若干條,官方湊出「158」這個數(具體條數在剔除重複後對齊;需要照抄時應直接以原始碼跑一次 `get_feature_config()` 核實實際欄數,而非手動數)。

**結論**:158 條中**只有 VWAP 相關的少數幾條**需要日線 OHLCV 以外的東西(而且可以用近似公式代替),其餘全部算得出。

**標籤(要不要一併抄)**:官方預設標籤是 `Ref($close,-2)/Ref($close,-1)-1`,即 T+1 收市到 T+2 收市的回報——這是 A 股 T+1 交易制度的產物(research/2026-08-25-factor-infrastructure.md 第 96–97 行已記)。Karst 若照搬,標籤位移量要按美股 T+0 可執行規則重新定義,不能照抄這條。

---

## 二、不裝 qlib 的現成 pandas 實作

搜尋詞:「alpha158 pandas」「qlib alpha158 without qlib」「alpha158 implementation」

| 專案 | 內容 | 星數 | 授權 | 最後動態 | 可否直接借用 |
|---|---|---|---|---|---|
| [microsoft/qlib](https://github.com/microsoft/qlib) 官方原始碼 | 公式定義的正本 | 主庫 | MIT | 持續維護 | **公式抄,程式不裝**——這是最務實的路(見下) |
| [Menooker/KunQuant](https://github.com/Menooker/KunQuant) | 把 Alpha101/Alpha158 表達式編譯成 C++,聲稱比原生 pandas 快 170 倍 | 有一定關注度 | 需查證(調研未取得明確授權文字) | 有維護 | 方向不合——Karst 現階段要的是「算得出、可審計」,不是「算得快」;C++ 編譯層增加維護負擔,不建議引入 |
| [SJTU-DMTai/DoubleAdapt](https://github.com/SJTU-DMTai/DoubleAdapt) | 號稱不依賴 qlib 的增量學習框架 | 117 | 未列明 | 有維護(31 次提交) | **不可用**——查證後它本身不含 Alpha158 的 pandas 實作,只是建議使用者自行接新的 data adapter |

**結論(依「業務先行、不預設自建」原則覆核)**:網上沒有一個「開箱即用、授權清楚、脫離 qlib」的 Alpha158 pandas 套件。但這不代表要自建一切——**表達式本身是公開發表的公式**(qlib MIT 授權下的原始碼本來就可以照抄邏輯,不裝整個 qlib 套件),真正要自己寫的只是約 20–25 個運算子函數(`Mean`、`Std`、`Slope`、`Rsquare`、`Resi`、`Rank`、`IdxMax`、`Corr` 一類滾動窗口函數),這些全部是 pandas `.rolling()` 能直接覆蓋的標準統計運算,不是要重新發明的東西。工作量估計是「抄清單 + 寫一層運算子函數 + 單元測試對照 qlib 官方輸出」,不是研究級工作。

---

## 三、算力與儲存估計

**規模**:158 因子 × 500 實體 × 3,000 個交易日(約 12 年)≈ 2.37 億格。

**儲存**:
- 以 float64(8 bytes)計,原始數值約 1.9 GB;實務上因子值多數在有限精度內,轉 float32 可減半至約 950 MB。
- parquet 用列式壓縮,對這類有規律的浮點數列,壓縮比常見在 2–4 倍,估計最終落地約 300–700 MB。與 Karst 現有 `factor_value` 表(日期 × 實體 × 因子版本,雙時間戳)的形狀相容,只是列數會由現在的個位數因子暴增至 158 條,索引與查詢量隨之放大約兩個數量級,但仍在 SQLite/parquet 這類單機儲存的正常負載範圍內。

**計算時間量級**:
- pandas 的 `.rolling()` 系列運算對單一欄(3,000 列)是毫秒級;500 隻股票逐一算一次,每個因子類型估計數秒至十餘秒(視乎是否用 `groupby` 向量化或逐股票迴圈,迴圈版本慢一個數量級)。
- 158 條全部算完,合理估計落在**幾分鐘到十餘分鐘**這個量級(用 `groupby().rolling()` 或按股票分組的向量化寫法),不需要分散式運算或 GPU。若逐股票逐因子雙重 Python 迴圈(最笨的寫法),則可能拉長到半小時以上——這是實作階段要留意的效能陷阱,不是不可行,是寫法要對。

（本節為工程量級估計,非實測基準;真實數字要在 KARST-062 之後的建置票跑一次小規模基準才能定案,不在本票範圍內。）

---

## 四、宇宙擴至標普 500 的數據源

### 4.1 標普 500 成分歷史(避免存活者偏差)

- [teddykoker/survivorship-free-spy](https://github.com/teddykoker/survivorship-free-spy)——公開免費倉庫,提供含退市股的標普 500 成分歷史,120 星、71 個分支,方法論見作者[部落格文章](https://teddykoker.com/2019/05/creating-a-survivorship-bias-free-sp-500-dataset-with-python/)(以 Wikipedia 變動記錄為底重建每個時點的成分名單)。調研未能核實其覆蓋的具體起訖年份與更新頻率,引用前建議先拉一次查實際年份範圍。
- 補充做法:Wikipedia「S&P 500 companies」頁面本身留有納入/剔除變動表,可作交叉核對或自行重建的第二來源。
- 出處:[robotwealth 教學](https://robotwealth.com/how-to-get-historical-spx-constituents-data-for-free/)、[riazarbi 方法說明](https://riazarbi.github.io/quant/backtesting-sp500-constituent-history/)

### 4.2 yfinance 對退市代號的覆蓋限制

查證結果:**yfinance 對已退市代號的覆蓋不穩定,不是「查不到」與「查得到」二選一,而是常見報「symbol may be delisted」等錯誤,即使代號本身仍有歷史數據存在**。已知成因之一是 Yahoo Finance 近年收緊了部分歷史數據的存取(部分場景需要 Yahoo 的付費方案才能下載)。這代表:即使拿到成分歷史名單,退市那批股票的日線價格未必能用 yfinance 直接補齊。

- 出處:[ranaroussi/yfinance issue #2340](https://github.com/ranaroussi/yfinance/issues/2340)、[issue #2453](https://github.com/ranaroussi/yfinance/issues/2453)、[issue #359](https://github.com/ranaroussi/yfinance/issues/359)

**對 Karst 的意義**:與 D-026 第 6 條(免費來源不含退市股,快照連同宇宙名單一併凍結、此前回測標明「未含退市股」)完全吻合——這條限制不是新發現,是已知取捨的延續。標普 500 擴容這一步,實際能免費做到的是「用今日或近日成分名單的日線」,退市股的歷史缺口依然存在,報告要照 D-026 誠實標示。

### 4.3 CONTEXT.md 對照

`karst/data/universe.py` 現有 `STARTER_UNIVERSE`(十二隻)與 `FACTOR_ETF_UNIVERSE`(四隻因子 ETF),`UNIVERSE_REGISTRY` 是登記清單、不等於預設抓取批次。標普 500 擴容應該是往 `UNIVERSE_REGISTRY` 加一批新登記,不改動起步名單的預設行為——這與現有設計(登記與預設分開)相容,不需要改架構。

---

## 五、因子檢視 IC 計算要補什麼

### 5.1 現有機制

`CONTEXT.md` 詞彙表(第 29 行)已定義「因子檢視」為個股層解釋畫面(某股逐日各因子分數與入選狀態),原型見 KARST-015。目前**沒有**逐因子跨股票的 IC / Rank IC / ICIR 面板。

### 5.2 alphalens 能不能直接搬

查證:[alphalens-reloaded](https://github.com/stefan-jansen/alphalens-reloaded)(Apache-2.0 授權,638 星,持續維護,支援 pandas 2.2.2+/numpy 2.0+)是目前活躍度最高的 alphalens 分支。它的 IC 計算是標準 Spearman 等級相關,`get_clean_factor_and_forward_returns()` 的輸入是一個以**單一時間戳**(level 0)+ 資產(level 1)為索引的 MultiIndex Series。

**問題**:Karst 的 `factor_value` 表主鍵是 `(factor_version_id, entity_id, event_time, knowledge_time)`——**兩個時間戳**,alphalens 的輸入形狀天生只認一個。要接上去,必須先決定「用哪個時間戳當 alphalens 的索引軸」(答案顯然是 knowledge_time,因為評估要按「幾時可以用這個值」對齊未來回報,不能用 event_time,否則會製造假成績——這正是 D-021、D-017 反覆強調的前視陷阱)。

### 5.3 建議:自寫薄層,不整套引入 alphalens

理由:
1. **alphalens 的強項(分層回報、多空價差、tear sheet 視覺化)Karst 現階段用不到**——因子檢視要的是「這個因子準不準」的一個 IC 數字與時序圖,不是完整的因子研究報告工具。
2. **輸入形狀要先轉換**才餵得到 alphalens,轉換這一步本身已經是要寫的程式碼,而且轉換邏輯(選 knowledge_time、按因子版本分組)是 Karst 特有的,alphalens 學不到、也不驗證這一步做對了沒有。
3. Spearman 等級相關本身是 `scipy.stats.spearmanr` 或 `pandas.DataFrame.corr(method="spearman")` 一行可達,自寫一個「按日期分組、算因子值與未來 N 日回報的等級相關」的函數,工作量遠小於接 alphalens 的形狀轉換層。

**要補的東西(建置票範圍)**:
1. 一個從 `factor_value` + 價格面板(K 線面板,已有)組出「(knowledge_time, entity) → 因子值」與「(knowledge_time, entity) → 未來 N 日回報」兩張對齊表的函數,回報計算要用可執行時點(D-021 定義)而非知情時點當日價。
2. 逐日 Spearman IC、滾動 IC 均值/標準差(即 ICIR)兩個指標,按因子版本分組。
3. 因子檢視畫面加一個「IC 時序圖」分頁,與現有個股逐因子分數畫面並列——這是新畫面/改既有設計決定的範圍,依 Kira 規矩要先出變體停下等用戶選,不在本研究票內處理。

---

## 六、建議路徑與建置票拆法

**建議路徑(一句可裁)**:照抄 Alpha158 公式定義、自寫 pandas 版本(不裝 qlib),先在現有起步宇宙驗證,標普 500 擴容另接一個免費成分歷史源並照 D-026 標示退市股缺口,IC 面板自寫薄層對接因子表雙時間戳,不整套引入 alphalens。

**建置票拆法(每張一程)**:

1. **Alpha158 pandas 實作票**——抄公式清單、寫約 20–25 個滾動運算子函數、對照 qlib 官方輸出做單元測試(小樣本、幾隻股票、抽查十條因子數值是否吻合),不含入庫。
2. **因子入庫與版本登記票**——把第 1 張的輸出接上唯一入口,158 條因子各自登記 `factor`/`factor_version`,按 D-021 合約補齊可執行時點、產生程序版本等必填欄位,批量寫入 `factor_value`。
3. **標普 500 宇宙擴容票**——接入免費成分歷史源(先核實其覆蓋年份),擴充 `UNIVERSE_REGISTRY`,退市股缺口照 D-026 在快照說明檔標示;不強求補齊退市股價格(留白比造假數據安全)。
4. **因子檢視 IC 面板票**——第 5 節列的三項(對齊表函數、IC/ICIR 計算、畫面新分頁);畫面部分先出變體停下等用戶選,不與前三張並行動工。

---

## 七、出處總表

- [qlib `contrib/data/loader.py`(Alpha158DL 表達式定義)](https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/loader.py)
- [qlib `contrib/data/handler.py`(Alpha158 handler 設定)](https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/handler.py)
- [Menooker/KunQuant](https://github.com/Menooker/KunQuant)
- [SJTU-DMTai/DoubleAdapt](https://github.com/SJTU-DMTai/DoubleAdapt)
- [teddykoker/survivorship-free-spy](https://github.com/teddykoker/survivorship-free-spy)
- [Teddy Koker — Creating a Survivorship Bias-Free S&P 500 Dataset with Python](https://teddykoker.com/2019/05/creating-a-survivorship-bias-free-sp-500-dataset-with-python/)
- [robotwealth — How To Get Historical SPX Constituents Data For Free](https://robotwealth.com/how-to-get-historical-spx-constituents-data-for-free/)
- [riazarbi — Survivorship-bias free S&P 500 constituent lists](https://riazarbi.github.io/quant/backtesting-sp500-constituent-history/)
- [ranaroussi/yfinance issue #2340](https://github.com/ranaroussi/yfinance/issues/2340)
- [ranaroussi/yfinance issue #2453](https://github.com/ranaroussi/yfinance/issues/2453)
- [ranaroussi/yfinance issue #359](https://github.com/ranaroussi/yfinance/issues/359)
- [stefan-jansen/alphalens-reloaded](https://github.com/stefan-jansen/alphalens-reloaded)
- 本倉背景:`research/2026-08-25-factor-infrastructure.md`、`.kira/decisions.md` D-021/D-022/D-026、`karst/schema.py`、`karst/data/universe.py`、`CONTEXT.md` 詞彙表
