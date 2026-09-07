# 量價因子在小型股、行業 ETF、因子 ETF 上的預測力——文獻預期與量級

- 票號:KARST-072
- 日期:2026-08-29
- 用途:回應用戶 2026-08-29 裁決(原話「Next I want to test 1) The small stocks, and XLK
  and related series of industrial ETF, and the 4 S&P factor ETF」),並依用戶明令
  「before we run any academic stuff ourselves, let me know the research insight here」,
  在實測前把三個新宇宙(小型股、SPDR 十一隻行業 ETF、四隻因子 ETF)的文獻預期、量級、
  可信度落檔,格式照 `research/2026-08-29-factor-horizon-evidence.md`。

---

## 摘要(先講結論)

三個宇宙的訊號預期不是同一個級別。**小型股**是量價/技術異常文獻裡訊號最集中的地方(異常
報酬集中在小型股與微型股,大型股上多數異常消失或微弱),量級上比 KARST-066 已測的標普
500(0 條因子達標)高出不止一截,是三者中最值得抱樂觀預期的一格,但流動性限制也最重(交易
成本會吃掉部分紙上優勢)。**行業 ETF**十一隻橫斷面太窄,不適合套用 KARST-066 那種「逐日跨
資產排名求 IC」的量法,文獻(行業動量、均線輪動)講的是「每隻自己的因子值對自己未來回報」
這種時間序列預測力,量級上歷史文獻顯示有效但屬於中低頻(月度換手)的動能與趨勢訊號,不是
日線量價因子的甜蜜區。**因子 ETF**只有四隻,學術界對「用技術訊號擇時因子」本身有公開爭論
(Asness 對 Arnott),多數機構級證據傾向「擇時難、且失敗代價大於收益」,四隻的樣本數也小到
連統計檢定力都成問題,三者之中預期訊號最弱、可信度最低。

---

## 一、小型股:量價/技術異常的集中度與免費成分歷史來源

### 1.1 異常報酬在小型股/微型股集中——文獻量級

- **Hou, Xue & Zhang (2020)**,*Replicating Anomalies*,The Review of Financial Studies
  33(5): 2019–2133。用 NYSE 分界點與市值加權法覆核 452 個已發表異常,65% 未能通過
  |t| ≥ 1.96 的單一檢定門檻,提高到多重檢定門檻 2.78 後失敗率升到 82%。**微型股只佔
  總市值 3.28%,但等權法下微型股月均報酬 1.32%,對比大型股 1.03%**——異常在小型股/
  微型股的等權組合中比市值加權組合明顯更強,是本文獻最直接支持「技術異常在小型股較強」
  的量化數字。文中亦強調:即使異常在覆核後仍成立,經濟量級普遍比原論文報的小。
  出處:[Oxford Academic(摘要)](https://academic.oup.com/rfs/article-abstract/33/5/2019/5236964)、
  [NBER 工作論文全文](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf)、
  [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2961979)

- **Fama & French (2008)**,*Dissecting Anomalies*,Journal of Finance 63(4): 1653–1678。
  按微型股、小型股、大型股三組分別做橫斷面迴歸與分組排序(1963–2005,美股全樣本)。
  淨股票發行、應計項目、動量三類異常在三個規模組都出現、且在極端分組上都強;但**資產
  成長異常只在微型股與小型股出現、大型股上消失**——這條是本文獻裡「異常隨規模遞減」最
  乾淨的一個對照。多數異常改用市值加權(而非等權)後會變弱或消失,而市值加權下的權重
  又集中在大型股身上,間接說明**多數已發表異常的統計顯著性主要由小型股/微型股撐起**。
  出處:[Wiley(摘要)](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2008.01371.x)、
  [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=911960)

### 1.2 流動性限制:紙上優勢與可執行優勢有落差

- **Novy-Marx & Velikov (2016)**,*A Taxonomy of Anomalies and Their Trading Costs*,
  The Review of Financial Studies 29(1): 104–147。研究扣除交易成本後的異常表現,發現
  **異常報酬集中在小型、難以交易的資產上**,月換手率低於 50% 的異常在扣成本後多數仍有
  顯著淨價差,換手率高的則多數扣成本後消失。新增資金對策略獲利的侵蝕程度與換手率成反比
  ——規模、價值、獲利能力這類低換手策略容納資金的能力最強。**對 Karst 的意思**:小型股
  上測到的紙上 IC 即使比大型股高,真正能兌現的部分要打折——這是文獻本身的量級估計,不是
  Karst 特有的顧慮。
  出處:[RFS(摘要)](https://academic.oup.com/rfs/article/29/1/104/1844518)、
  [NBER 工作論文全文](https://www.nber.org/papers/w20721)、
  [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2535173)

**三條文獻疊起來的量級判斷**:小型股/微型股是技術異常訊號**最集中**的地方(Hou-Xue-Zhang
的微型股等權溢價、Fama-French 的規模遞減異常),方向與 KARST-066 已測的「起步十二隻(較集中
的小樣本)訊號比標普 500(625 隻大盤股)強 7 倍」完全吻合——小型股擴容預期會延續、甚至放大
這個「宇宙越集中/越小,訊號越強」的模式,但流動性限制(Novy-Marx & Velikov)提醒紙上 IC 不
等於可執行報酬,量級上要打折看待。

### 1.3 小型股免費成分歷史來源:授權、覆蓋年份、退市覆蓋

| 來源 | 內容 | 授權 | 覆蓋年份 | 備註 |
|---|---|---|---|---|
| Wikipedia「List of S&P 600 companies」/「S&P 500 companies」變動表 | 頁面本身留有加入/剔除變動記錄 | CC BY-SA(Wikipedia 通用授權) | 依頁面編輯歷史回溯,無官方保證的起訖年份 | 適合作交叉核對的第二來源,不建議作唯一正本 |
| [teddykoker/survivorship-free-spy](https://github.com/teddykoker/survivorship-free-spy) | 標普系列(以 SPY/S&P 500 為主)含退市股的成分歷史重建方法論 | 未在 KARST-062 查得明確 license 檔——沿用 KARST-062 既有「未核實授權細節」標示 | KARST-062 已標示「未能核實具體起訖年份」 | 這是 S&P 500,不是 S&P 600;可作方法論參考(以 Wikipedia 變動記錄重建),不能直接當小型股數據源 |
| iShares 官方持倉頁(IWM=羅素 2000、IJR=標普小型股 600) | 官方每日持倉快照,可下載當日 CSV | iShares 網站使用條款(免費瀏覽/下載當日快照,非開放數據授權) | **只有「現在」這一天的快照,官方頁面不提供歷史持倉下載** | 要拉歷史持倉,只能靠第三方逐日存檔或付費源 |
| [talsan/ishares](https://github.com/talsan/ishares) | 爬蟲工具,定期抓取 iShares 官網持倉頁並存成逐日 CSV(含可選 AWS S3/Athena 整合) | 開源工具本身(需查證其倉庫 license),抓取內容仍受 iShares 使用條款約束 | 取決於使用者自己開始跑的時間點起——**不是現成的歷史數據集,是一支要自己長期運行的爬蟲** | 這是「工具」不是「數據」,若要用,Karst 要自己長期運行才能累積歷史,不能一次性下載到位 |
| Barchart / Intrinio / stockanalysis.com 等第三方數據站 | IWM、IJR 持倉列表,部分提供歷史下載 | 多數為付費方案,免費層級每日下載次數受限(如 Barchart 每日 1 檔) | 視方案而定 | 免費層級不足以支撐一次性歷史回溯,只適合日後定期小量補數 |

**結論(依「業務先行、不預設自建」原則)**:網上沒有查到一個「開箱即用、授權清楚、含退市股、
覆蓋標普 600 或羅素 2000 完整歷史」的免費現成數據集——這一格比 KARST-062 查到的標普 500
(teddykoker 倉庫)更弱,S&P 500 尚有一個現成的存活者偏差修正重建方法論可抄,**小型股指數
目前查不到對應的等價現成品**。務實路徑是:(a) 用 Wikipedia 的 S&P 600 變動表自行重建成分
歷史(方法論可抄 teddykoker 的做法,但要另外做,不是現成可下載檔);或 (b) 接受「只用近期
成分名單」的簡化(如 D-026 第 6 條既有做法),在報告上明確標示「不含退市股、只含當前入選
名單回溯」。這一點與 D-026 第 6 條的既定取捨一致,不是新問題。

### 1.4 yfinance 對小型股退市代號的覆蓋限制

沿用 `research/2026-08-29-alpha158-feasibility.md` 第 4.2 節已查證的結論並延伸:yfinance
對已退市代號的覆蓋本身就不穩定(常見報「symbol may be delisted」錯誤,即使代號歷史數據仍
存在),小型股/微型股退市率遠高於大型股(小型公司更容易被收購下市、破產下市、或因市值太
小被交易所摘牌),**這代表小型股宇宙的「未含退市股」缺口,量級上會比標普 500 那個缺口更
嚴重**——沒有查到專門量化「小型股退市代號在 yfinance 缺口比例」的數字,標示為**未核實
量級,方向可信**。
出處:[yfinance issue #2340](https://github.com/ranaroussi/yfinance/issues/2340)、
[issue #359](https://github.com/ranaroussi/yfinance/issues/359)

---

## 二、SPDR 十一隻行業 ETF:量法轉換與行業輪動文獻

### 2.1 為什麼橫斷面 IC 對十一隻不適用

KARST-066 用的「逐日 IC」量法,是在同一日把宇宙內所有實體按因子值排名、跟各自其後 N 日回報
排名做 Spearman 相關——這個量法需要足夠多的橫斷面樣本(標普 500 的 625 隻、起步宇宙的 12
隻)才有統計檢定力。**十一隻行業 ETF 同一日只有 11 個排名位,樣本量太薄,逐日橫斷面 IC 在
統計上不可靠**(單日 11 個點的等級相關,置信區間極寬)。應改用**時間序列預測力**:對每隻
ETF 分別算「自己的因子值」與「自己其後 N 日回報」的時間序列相關(或按因子值高低分組後看
未來回報的分組差),十一隻各自出一個數字,不跨 ETF 排名。

### 2.2 行業輪動/動量文獻與量級

- **Moskowitz & Grinblatt (1999)**,*Do Industries Explain Momentum?*,Journal of Finance
  54(4)。用 CRSP/COMPUSTAT 按二位數 SIC 代碼組 20 個市值加權行業組合(1963–1995 年
  7 月),發現**行業層面存在強烈且普遍的動量效應,個股動量異常有相當一部分可以由行業動量
  解釋**——控制行業動量後,傳統個股動量策略的獲利顯著減弱、統計上多數不顯著;行業動量
  策略本身比個股動量策略更賺錢。**這條直接支持:對行業 ETF(本質上就是行業組合)用動量
  類技術訊號,文獻基礎比對個股更紮實**。
  出處:[Wiley(摘要)](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00146)、
  [AQR 轉載](https://www.aqr.com/Insights/Research/Journal-Article/Do-Industries-Explain-Momentum)、
  [全文 PDF](http://www-stat.wharton.upenn.edu/~steele/Courses/956/Resource/Momentum/MoskowitzGrinblatt99.pdf)

- **Faber (2007)**,*A Quantitative Approach to Tactical Asset Allocation*,Journal of
  Wealth Management, Spring 2007。用 10 個月簡單移動平均線作買賣訊號,對標普 500 及
  多個資產類別回測百年數據,發現**均線擇時策略相對買入持有,報酬相近或更高、但波動度與
  最大回撤明顯更低**——這是月度換手頻率的趨勢跟蹤訊號,不是日線量價因子。
  出處:[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461)、
  [作者網站 PDF](https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf)

- **Faber (2010)**,*Relative Strength Strategies for Investing*。用 Fama-French 美股
  行業數據回溯至 1920 年代,按 1–12 個月滾動報酬對行業排名、買入相對強勢行業。**相對強勢
  行業輪動組合在約 70% 的年份跑贏買入持有基準,疊加均線擇時後波動度與回撤進一步下降**。
  這篇直接針對「行業輪動」用的就是動量/相對強弱這種技術訊號,量級上是「多數年份跑贏、非
  每年跑贏」的中等強度,不是異常穩定的訊號。
  出處:[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1585517)、
  [Cambria 版全文 PDF](https://www.cambriainvestments.com/wp-content/uploads/2018/01/Relative-Strength-Strategies-for-Investing.pdf)

- **Moskowitz, Ooi & Pedersen (2012)**,*Time Series Momentum*,Journal of Financial
  Economics 104(2): 228–250。對 58 種期貨/遠期合約(股指、匯率、商品、主權債)驗證「自己
  過去 12 個月報酬能顯著正向預測自己未來報酬」,效應持續約一年後部分反轉。**這是「時間序列
  預測力」這個量法的學術正本出處**——用於行業 ETF 時,對應的做法是:每隻 ETF 各自算自己的
  因子值(如過去 12 個月報酬)對自己未來報酬的預測力,不做跨 ETF 橫斷面排名。
  出處:[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2089463)、
  [NYU Stern 全文 PDF](https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf)、
  [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0304405X11002613)

**量級判斷**:行業輪動類文獻(Moskowitz & Grinblatt 行業動量、Faber 均線與相對強弱)驗證的
是**月度換手、3–12 個月動量窗口**的訊號,跟 Alpha158 這批日線量價因子的核心設計窗口(1、5
個交易日)不是同一個時間尺度——這與 `research/2026-08-29-factor-horizon-evidence.md` 第
2.2 節「動量因子要 3–12 個月才顯現、跟量價因子完全是兩個時間尺度」的既有結論一致。**預期
Alpha158 在十一隻行業 ETF 上,短窗口(1、5 日)的時間序列預測力會偏弱,21 日窗口若含動量/
趨勢類因子(ROC、MA 一類)有機會出現比短窗口更明顯的訊號,但仍要留意樣本只有十一條時間序列、
統計檢定力天生受限**,結論的可信度上限比大樣本橫斷面 IC 低。

---

## 三、四隻因子 ETF(QUAL、VLUE、MTUM、USMV):因子擇時文獻與爭論

D-031 已定四隻維持 MSCI 套,本節查因子擇時(用技術訊號判斷幾時該持有哪個因子 ETF)本身的
文獻證據。

### 3.1 Asness 對 Arnott 的爭論——機構級的正面交鋒

- **Arnott, Beck, Kalesnik & West (2016)**,*How Can "Smart Beta" Go Horribly Wrong?*,
  Research Affiliates,2016 年 2 月。主張:近年 smart beta/因子策略的亮眼表現,部分來自
  估值被追捧推高(策略越紅、資金越搶進、估值越貴),**扣除估值變動後的因子淨報酬遠低於
  近年帳面表現**,存在「均值回歸可能重創 smart beta」的風險,暗示投資人應該按估值水平擇時
  進出因子暴露(貴的時候減,便宜的時候加)。
  出處:[Research Affiliates](https://www.researchaffiliates.com/publications/articles/1076-how-can-smart-beta-go-horribly-right)

- **Asness (2016)**,*The Siren Song of Factor Timing*,Journal of Portfolio Management
  (Special QES Issue)。正面反駁 Arnott:估值利差(value spread)對因子未來報酬的長期
  解釋力被誇大或根本不適用,**進出因子暴露的擇時(popping in and out based on valuations)
  很少是好主意——原則不論資產包裝形式(股票、ETF)都一樣**,主張分散持有多個因子(不擇時)
  才是穩妥取得因子報酬的方式。兩人 2016 年 6 月在 Morningstar 投資年會上正面對談,爭論
  沒有收斂到共識。
  出處:[SSRN](https://papers.ssrn.com/abstract=2763956)、
  [ETF Trends 報導](https://www.etftrends.com/2016/09/when-titans-clash-arnott-and-asness-on-factor-timing/)

### 3.2 Bender et al. (2018)——技術/多維訊號擇時因子的證據

- **Bender, Sun, Thomas & Zdorovtsov (2018)**,*The Promises and Pitfalls of Factor
  Timing*,Journal of Portfolio Management 44(4): 79–92(State Street Global Advisors,
  非 MSCI——本票原票面猜測作者所屬機構為 MSCI,查證後更正為 SSGA)。系統檢視情緒、估值、
  趨勢(technical/trend,含動量類技術訊號)、總體經濟、金融條件五類擇時訊號對因子報酬的
  歷史關聯,發現**不同類訊號在不同時間窗口各有相關性、沒有一套訊號在所有時期都管用**,
  隱含結論:因子擇時「有跡可循但不穩定」,不是可靠的、可長期依賴的策略。
  出處:[JPM 官方](https://jpm.pm-research.com/content/44/4/79)、
  [Wharton Jacobs Levy Center 全文 PDF](https://jacobslevycenter.wharton.upenn.edu/wp-content/uploads/2017/08/The-Promises-and-Pitfalls-of-Factor-Timing-2.pdf)

**量級判斷**:機構級文獻(Asness、Bender et al.)整體偏向「因子擇時難、訊號不穩定」,即使
Bender et al. 找到部分時期某些訊號類別有相關性,也沒有一套放諸四海皆準的規則。加上 Karst
只有四隻因子 ETF、樣本數天生小(對照 KARST-066 標普 500 用 625 隻實體才測出「158 條裡沒
有一條達標」的結論),**預期四隻因子 ETF 上技術訊號的預測力是三個宇宙裡最弱、可信度最低
的一格**——就算測出某條因子在四隻上「看似有訊號」,樣本量太小,更可能是雜訊而非真訊號,
解讀結果時要特別警惕假陽性。

---

## 四、結語:三個宇宙 × 預期訊號量級 × 量法 × 可信度

| 宇宙 | 預期訊號量級 | 量法 | 可信度 | 對本次實測的預期(一句) |
|---|---|---|---|---|
| 小型股(標普 600 / 羅素 2000 一類) | 三者中**最高**——異常文獻顯示技術訊號在小型股/微型股集中,方向與 KARST-066「宇宙越集中訊號越強」吻合,但流動性限制會打折 | 沿用 KARST-066 的橫斷面 IC(跨股票逐日排名),樣本數足夠 | 機構級文獻支持方向,但 Karst 自家免費成分歷史數據源不完整(比標普 500 更缺),退市覆蓋是量級上的最大不確定 | 預期會測到比標普 500(0 條達標)明顯更多達標因子,但不會到起步十二隻(84 組達標)那麼高,且要在報告上明確標示未含退市股的缺口 |
| SPDR 十一隻行業 ETF | 中等,且集中在較長窗口(21 日或以上) | **時間序列預測力**(每隻自己的因子值對自己未來回報),不能用橫斷面 IC——十一隻樣本太薄 | 行業動量文獻(Moskowitz & Grinblatt)機構級可信,但均線/相對強弱那批(Faber)屬業界研究非同行評審頂刊,而且樣本只有十一條時間序列,統計檢定力先天受限 | 預期短窗口(1、5 日)訊號偏弱,21 日或以上若含動量/趨勢類因子有機會出現較明顯訊號,但結論的統計把握度低於大樣本橫斷面測試 |
| 四隻因子 ETF(QUAL/VLUE/MTUM/USMV) | 三者中**最低** | 因子擇時類量法(把技術訊號當作「幾時該持有哪個因子」的判斷依據),量法上更接近第二個宇宙的時間序列做法,但樣本量比十一隻行業 ETF 更小 | 機構級證據(Asness 對 Arnott 的公開爭論、Bender et al. 系統性檢視)整體偏向「擇時難、不穩定」,可信度中等偏低;加上只有四隻,測出來的任何「訊號」都要高度警惕統計雜訊 | 預期測不出穩定可用的訊號,即使個別因子看似達標也大機率是小樣本雜訊,不宜作為擇時依據 |

---

## 未完全核實事項清單

- Wikipedia S&P 600 變動表的完整可追溯年份、以及其記錄是否有遺漏,本票未逐年核對,只確認
  頁面本身有變動記錄可用。
- teddykoker/survivorship-free-spy 倉庫的授權條款文字,KARST-062 與本票均未能取得明確
  license 檔內容,沿用「未核實授權細節」標示。
- talsan/ishares 這支爬蟲工具本身的開源授權條款未查證,只確認其功能(抓取 iShares 官網
  逐日持倉快照存檔)。
- 小型股退市代號在 yfinance 的具體缺口比例(相對標普 500 差多少)沒有查到量化數字,只能
  以「小型股退市率更高、缺口方向上更嚴重」定性推論,標示為未核實量級。
- A 股「日內動量、周內反轉」這批工作論文的正式發表狀態,沿用
  `research/2026-08-29-factor-horizon-evidence.md` 既有的未核實標示,本票沒有重新查證,
  與本票主題(小型股/行業 ETF/因子 ETF)無直接關係,列此僅為完整交代背景文獻鏈。
- Bender et al. (2018) 作者所屬機構原票面推測為 MSCI,本票查證後更正為 State Street
  Global Advisors(SSGA)——這點在下面回票結果時一併提醒主 agent,票面敘述若沿用需更正。
