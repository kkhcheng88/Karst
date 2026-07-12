# 文本訊號 + Smart-Money(13F)方法論文獻(2026-07-09)

> 補件,唔重覆 `docs/2026-07-09_magnifier_literature.md`(21 篇 magnifier 文獻)。呢份專門
> answer 兩條問題:(1) `exp_constraint_language.py`(供給受限語言掃描,已證 MU 早 17 個月)
> 呢套方法有冇學術地基、仲需唔需要「多讀書」先可以繼續做;(2) 監測 Bessembinder 或者類似
> smart-money 13F 持倉做 discovery 訊號,事實同學術證據點講。
>
> **方法**:WebSearch/WebFetch 逐篇核對作者/年/期刊/卷期/DOI(唔靠訓練記憶砌 citation)。
> **信心標記**:🟢 已用 primary source(期刊頁/SSRN/NBER/機構典藏)核實 ·
> 🟡 citation 核實但關鍵數字只有 secondary summary 佐證 · 🔴 搵到但唔係嚴格 peer-reviewed
> (工作論文/會議論文/業界白皮書),如實標注唔砌大。

## 0. 一句結論

**文本訊號組**:搵到 7 篇,核心 2 篇直接對應 `exp_constraint_language.py` 嘅方法論——
**Cohen-Malloy-Nguyen "Lazy Prices"(2020 JF)**證明「10-K/10-Q 逐年**文字改動**(唔係
水平)先係市場低估、underreaction 嘅來源」,同我哋探針已經獨立諗到嘅「score 環比跳升」
警報邏輯完全對得上;**Theile-Hofer-Singhal-Hoberg(2026,Production and Operations
Management)**用 earnings call NLP 量度「供應鏈風險/紓緩」語言直接預測財報日股價反應,係
最貼近我哋 transcript 掃描嘅同類研究。**唔需要額外「多讀書」先可以繼續**——現有 regex
詞表方法本身就係 Loughran-McDonald(2011 JF)官方詞典入面「constraining」呢一類(184 個
pre-registered 詞)嘅同類做法,已有學術地基;如果將來想追加準確度,Frankel-Jennings-Lee
(2022 Management Science)已量化 ML 方法喺 conference call 場景比詞典法提升幅度更大,係
**已知嘅升級路徑**,唔係現在嘅必要條件。

**Smart-money/13F 組**:**Bessembinder 釐清屬實**——佢係 ASU 學者(金融教授、JFQA 副主編、
Compass Lexecon 訴訟顧問專家證人),**冇對沖基金、冇 13F 持倉可監測**,監測佢個人持倉呢個
主意本身唔成立。底層 idea(追蹤高信念集中倉)有學術地基但**帶明顯折讓**:Cohen-Polk-Silli/
Anton-Cohen-Polk「Best Ideas」(高信念倉跑贏 2.8-4.5%/年)**由始至終未正式喺同行評審期刊
發表**(仍係 HBS working paper,雖然引用量高);13F **45 日** 延遲 + 季度頻率嘅實際成本,
由 Puckett-Yan(2011 JF)量化——機構嘅季內(interim)交易技巧貢獻 20-26bp/年,即 13F 快照
睇唔到嘅嗰部分本身就有價值,證明「等 45 日先跟」會漏走一截;但 Frank-Poterba-Shackelford-
Shoven(2004 JLE)同 Verbeek-Wang(2013 JBF)兩篇獨立顯示,扣除費用後 copycat 策略依然可以
追近原基金表現(尤其 2004 年轉季度披露後更好)。**判定:值得做 probe 級(唔係 commitment)**
——同 insider-cluster(已證陰性:訊噪比低、跨公司共振太罕)唔同,13F/copycat 呢條有較紮實
嘅學術基礎,但一定要用「真正高信念集中持倉」嘅篩選(Best Ideas 定義),唔可以做全持倉照抄,
而且要對「邊個經理值得抄」做前置篩選(過往有實證 track record 揀中 multi-bagger 嘅少數人),
呢個前置篩選本身冇現成學術公式,係 probe 要解決嘅第一個問題。

---

## 組 1|財報/文本訊號方法論

### 1.1 Cohen, Malloy, Nguyen, "Lazy Prices"

*Journal of Finance*, Vol. 75, Issue 3 (2020), pp. 1371–1415.
DOI: [10.1111/jofi.12885](https://doi.org/10.1111/jofi.12885) ·
NBER WP 25084: [nber.org/papers/w25084](https://www.nber.org/papers/w25084) ·
SSRN: [abstract_id=1658471](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1658471)

- **方法**:用美股上市公司**完整史**嘅逐季/逐年定期披露(10-K/10-Q),量度**逐年連續兩份
  filing 之間嘅文字改動**(語言/段落結構嘅變化,唔係文本水平本身)。樣本 1995–2014。
- **核心發現**:造淡「有大幅改動」嘅公司、造好「冇改動」嘅公司,組合其後賺取**最多
  188bp/月(年化 >22%)** alpha;filing 當日**冇明顯公告效應**(即市場冇即時反應改動),
  改動仲可以預測未來盈餘、獲利能力、未來新聞事件、甚至破產——結論標題「Lazy Prices」講嘅
  正正係投資者對呢類改動**反應不足(underreaction)**。
- 信心:🟢(期刊頁 + NBER + SSRN 三源核實一致;188bp/月數字已見於摘要原文)
- **同我哋 constraint-language probe 嘅關係**:呢篇係我哋探針入面「突變警報 = score 環比
  跳升超過 X 個標準差」呢條落地建議(見 `2026-07-08_constraint_language_probe.md` §5)嘅
  **直接學術支撐**——Lazy Prices 證明市場對「filing 文字**變化**」反應不足,唔係對「文字
  水平」反應不足,即我哋而家用嘅絕對分數(score_per_1000w)本身唔係最優訊號,**應該加一條
  Δscore(QoQ/YoY 變化量)做主訊號**,先係最貼近呢篇文獻已證實 underreaction 嘅嗰個維度。
- **可唔可以套喺 defeatbeta transcript**:方法論本身係為 10-K/10-Q(regulatory filing)
  設計,對象係 transcript 要留意兩點差異——(a) transcript 冇 filing 嗰種「法律責任驅動嘅
  boilerplate 穩定性」,逐季用詞天然波動較大,雜訊底噪更高,Δscore 訊號可能需要更長平滑窗;
  (b) transcript 冇「10-K 唔改 = 冇新聞」嘅慣性假設基礎(電話會每季內容本身就預期會變),
  所以「改動」呢個概念要重新定義成「特定語意類別(受限/鬆動)嘅**頻率**變化」,唔係逐字
  similarity——呢個正正係我哋現有詞表 regex 方法(數特定 phrase 命中率)已經隱含做緊嘅事,
  唔需要另起新方法,只需要加返 Δ 呢條時間維度。

### 1.2 Loughran & McDonald, "When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks"

*Journal of Finance*, Vol. 66, Issue 1 (2011), pp. 35–65.
DOI: [10.1111/j.1540-6261.2010.01625.x](https://doi.org/10.1111/j.1540-6261.2010.01625.x)
Master Dictionary(持續更新):[sraf.nd.edu/loughranmcdonald-master-dictionary](https://sraf.nd.edu/loughranmcdonald-master-dictionary/)

- **方法**:指出通用心理學詞典(Harvard Psychosociological Dictionary)套落財務文本會
  誤判——例如 Harvard 負面詞表入面近四分之三嘅詞喺財務語境唔算負面(如 "tax"、
  "cost"、"liability" 呢類中性會計字眼)。作者由 EDGAR 全部 10-K 文本重新建構
  **6 個財務語境專用詞表**:negative、positive、uncertainty、litigious、strong modal、
  weak modal,後續版本再加**constraining**(184 個詞,2014 版)。
- **同我哋探針最直接嘅連結**:LM 詞典本身就有一個官方、pre-registered、同行評審通過嘅
  **「constraining」詞類**——呢個名同我哋 `exp_constraint_language.py` 嘅
  `CONSTRAINED_PHRASES` 概念幾乎同名。**建議行動**:攞 LM 官方 constraining word list 對照
  我哋自訂嘅 15 條 regex(lead times extending / on allocation / sold out 等),睇邊啲已經
  重疊、邊啲係我哋額外加嘅產業特定詞(呢啲更精準但更窄)——呢個交叉對照可以直接回應探針
  「未解/風險 #1」(詞表未經跨行業雜訊率評估):用 LM 官方詞表做**外部基準**,量度我哋自訂
  詞表嘅 recall/precision 差距,唔使自己憑空砌 false-positive 測試集。
- 信心:🟢(期刊頁核實;constraining 類別 184 詞嘅版本細節經 SRAF 官方頁 + 多個獨立
  package 文檔交叉核實)
- **限制**:作者原文明講詞典係為 10-K 設計,「呢套結果套落其他類型財務文本(包括 transcript)
  站唔站得住,係一條open question」——即官方都承認 domain transfer 未必 1:1,呼應 1.1 嘅
  domain-transfer 提醒。

### 1.3 Loughran & McDonald, "Textual Analysis in Accounting and Finance: A Survey"

*Journal of Accounting Research*, Vol. 54, Issue 4 (2016), pp. 1187–1230.
DOI: [10.1111/1475-679X.12123](https://doi.org/10.1111/1475-679X.12123)

- **內容**:兩位原作者自己寫嘅方法論總覽——涵蓋 bag-of-words、cosine similarity、Zipf's
  law、word list 建構陷阱、Naïve Bayes 等,並明確列出當時文獻嘅已知漏洞(小樣本詞表
  overfitting、domain mismatch、負面詞單靠字面 match 唔理解否定詞/條件句)。
- 信心:🟢(期刊頁 + SSRN 摘要核實)
- **回應「使唔使多讀書」**:呢篇本身就係「一篇睇晒全部方法論選項」嘅索引論文——如果日後
  要決定 v1 詞表升級方向(見探針 §5「詞表紀律化擴充」),呢篇係第一個要翻嘅目錄,唔使逐篇
  重新搜。**但唔係現在必讀**——探針而家做緊嘅「pre-registered regex + 跨公司/跨季覆現
  門檻」本身已經係呢篇總覽入面明確認可嘅穩健做法(避免 overfitting 嘅標準建議正正係
  「詞要喺多個獨立樣本重複出現先算數」),同探針 §5 已經寫低嘅紀律(≥3 家公司、≥2 季)
  完全對得上。

### 1.4 Price, Doran, Peterson, Bliss, "Earnings Conference Calls and Stock Returns: The Incremental Informativeness of Textual Tone"

*Journal of Banking & Finance*, Vol. 36, Issue 4 (2012), pp. 992–1011.
SSRN: [abstract_id=1625863](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1625863)

- **核心發現**:電話會**語氣(tone)**對「財報公佈當日異常回報」有顯著解釋力,而且喺財報
  後 **60 個交易日**嘅 post-earnings-announcement drift 上,tone 嘅解釋力**蓋過**盈餘驚喜
  (earnings surprise)本身;Q&A 環節(管理層即時應答,唔係讀稿部分)嘅語氣預測力尤其強。
- 信心:🟢(SSRN/ScienceDirect/RePEc 三源核實一致)
- **可 encode 成乜**:直接支持我哋「按季度批次重跑」嘅頻率設計(探針 §5 已建議);仲提示
  一個未做嘅細分——**Q&A 段 vs 管理層讀稿段分開評分**,因為 Q&A 嘅即興回答(insider 較難
  提前包裝措辭)可能比 prepared remarks 更誠實反映真實供給狀況,defeatbeta 嘅 transcript
  DataFrame 已經有 speaker/paragraph 級別資料,呢個切分技術上可行、值得下一版加入。

### 1.5 Larcker & Zakolyukina, "Detecting Deceptive Discussions in Conference Calls"

*Journal of Accounting Research*, Vol. 50, Issue 2 (2012), pp. 495–540.
DOI: [10.1111/j.1475-679X.2012.00450.x](https://doi.org/10.1111/j.1475-679X.2012.00450.x)

- **核心發現**:用日後財報重編(restatement)嚴重程度做「呃(deceptive)/唔呃」標籤,訓練
  基於語言特徵(唔止用詞,仲有代名詞使用、情緒詞、認知複雜度)嘅分類模型,單靠 CEO/CFO
  逐字稿嘅分類準確度**比隨機高 6–16 個百分點**,同用財務會計變數嘅模型表現相若。
- 信心:🟢(JAR 官方頁 + Stanford GSB + SSRN 三源核實)
- **同我哋方法嘅關係**:呢篇唔係直接量度「供給受限」,而係展示**語言特徵可以撈出管理層
  未必自覺講出嚟嘅底層狀態**(呢度係造假傾向,我哋要撈嘅係產能狀態)——方法論上嘅啟示係
  用詞頻以外嘅語言學特徵(代名詞比例、確定性用語比例)可能有額外資訊量,係我哋 regex
  詞表法嘅一個潛在升級方向,但唔係現階段必要(現有探針已證有效,呢個係鋪墊將來 v2 嘅選項)。

### 1.6 Frankel, Jennings, Lee, "Disclosure Sentiment: Machine Learning vs. Dictionary Methods"

*Management Science*, Vol. 68, Issue 7 (2022), pp. 5514–5532.
DOI: [10.1287/mnsc.2021.4156](https://doi.org/10.1287/mnsc.2021.4156)

- **核心發現**:直接比較 ML(random forest 表現最好)vs Loughran-McDonald 詞典法喺兩個
  披露場景(10-K filing 日、conference call 日)嘅解釋力。**喺 conference call 場景,
  ML 相對 LM 詞典嘅提升幅度,大過 LM 詞典相對更舊嘅 Harvard 通用詞典嘅提升幅度**——即係
  「詞典法→ML」呢一步升級,喺 transcript 呢類文本上帶嚟嘅邊際改善,比「通用詞典→財務
  專用詞典」嗰一步仲大。
- 信心:🟢(Management Science 官方 DOI + SSRN + RePEc 三源核實)
- **直接回答「使唔使多讀書」**:**唔係現在必要,但係已知嘅、有量化證據嘅升級路徑**。
  現有 regex 詞表法(本質係一個手做嘅小型 LM-style 詞典)喺 10-K 場景已經證實有效
  (Lazy Prices、LM 原文),但呢篇話畀我哋知,如果將來想喺 **transcript** 呢個特定場景
  進一步提升準確度,ML(而非再擴詞表)先係已證實嘅方向——**探針嘅「詞表紀律化擴充」
  (§5)可以停喺「跨公司/跨季驗證嘅 regex 詞表」呢個階段做落地版本,升級去 ML 應該係
  另一個獨立項目,唔應該用嚟阻住而家已經證實有效嘅 v0 落地**。

### 1.7 Theile, Hofer, Singhal, Hoberg, "Supply Chain Risk and Resolution: An Empirical Study of Stock Market Reactions"

*Production and Operations Management*(POMS 官方期刊,UTD/FT-50 A+級),2026,ahead-of-print。
DOI: [10.1177/10591478261420550](https://doi.org/10.1177/10591478261420550)

- **方法**:用 NLP 由**季度電話會逐字稿**(唔係 10-K)建構「供應鏈風險」同「供應鏈風險
  紓緩(resolution)」兩條分數,樣本 **129,981 個公司-季度觀測、2008–2019**。
- **核心發現**:供應鏈風險語言最高五分位嘅公司,財報日股價回報比最低五分位低
  **1.07 個百分點**;回歸分析顯示供應鏈風險分數每升 1 個標準差,回報跌 **0.56 個百分點**;
  「風險已紓緩」嘅語言可以抵銷部分負面效應。
- 信心:🟢(POMS 官方 DOI 核實;數字經 2 個獨立搜尋結果一致;作者 Vinod Singhal 係
  Georgia Tech 供應鏈中斷研究知名學者)
- **同我哋 constraint-language probe 嘅關係——係全部 7 篇入面最貼近嘅一篇**:數據源
  (電話會逐字稿)、量度對象(供應鏈受限/緊張語言)、產出用途(預測股價回報)三者都同
  `exp_constraint_language.py` 一致,分別在於:(a) 呢篇用 129,981 個觀測嘅全市場樣本,
  我哋而家淨係 15 隻精選 ticker;(b) 呢篇量度嘅係**負面**供應鏈風險(斷鏈、延誤),我哋
  量度嘅係**正面**供給受限(定價權/sold-out,對股東反而係好事)——方向相反但方法論相通,
  證明「電話會語言 → 供應鏈狀態 → 股價反應」呢條因果鏈本身喺同行評審文獻入面**已經成立**,
  唔係我哋自己發明嘅假設。**呢篇係目前搵到最強嘅一篇 methodology 佐證**,建議喺
  `exp_constraint_language.py` 檔頭 comment 引用呢篇做方法論出處。

### 組 1 總表

| 論文 | 期刊/年 | 核心貢獻 | 對 constraint-language 探針嘅意涵 |
|---|---|---|---|
| Cohen-Malloy-Nguyen (2020) | JF | 10-K 文字**改動**預測回報,市場反應不足 | 加 Δscore(變化量)做主訊號,唔淨用水平 |
| Loughran-McDonald (2011) | JF | 財務專用情緒詞典,含 constraining 類 | 官方 constraining 詞表做外部 recall/precision 基準 |
| Loughran-McDonald (2016) | JAR | 方法論總覽/總目錄 | 詞表 overfitting 防範原則,同探針 §5 紀律一致 |
| Price-Doran-Peterson-Bliss (2012) | JBF | 電話會語氣預測 60 日 drift,Q&A 段最強 | 建議切分 Q&A vs prepared remarks 分開評分 |
| Larcker-Zakolyukina (2012) | JAR | 語言特徵(唔止用詞)撈出隱藏狀態 | 詞頻以外特徵嘅潛在 v2 升級方向 |
| Frankel-Jennings-Lee (2022) | Management Science | ML > 詞典法,喺電話會場景差距更大 | 已知升級路徑,非現在必要條件 |
| **Theile-Hofer-Singhal-Hoberg (2026)** | POM | **電話會 NLP 直接量度供應鏈受限語言預測回報** | **方法論最直接佐證,建議引用** |

---

## 組 2|Smart-money / 13F 追蹤

### 2.1 事實釐清:Hendrik Bessembinder 冇基金、冇 13F 持倉

- Hendrik Bessembinder 係 **Arizona State University (W.P. Carey School of Business)**
  金融教授(Francis J. and Mary B. Labriola Chair),曾任教 Emory、Utah、Rochester;
  現任 *Journal of Financial and Quantitative Analysis* Managing Editor、*Journal of
  Financial Markets* Associate Editor。
- 佢嘅「consulting」係 **Compass Lexecon**(訴訟經濟顧問公司)嘅資深顧問/專家證人角色
  ——即打官司提供經濟分析證供,**唔係資產管理、唔係對沖基金經理**。搜尋唔到任何 SEC
  Form 13F filer 記錄同呢個名字掛鈎(13F 只需機構投資經理、管理 $100M+ 美股股權持倉先要
  申報,學者個人研究戶口唔屬呢類)。
- 信心:🟢(ASU 官方 profile、Compass Lexecon 官網、newsroom 專家頁三源一致核實)
- **結論**:「monitor Bessembinder 嘅 holdings」呢個字面意思**不成立**——冇呢樣嘢可以
  monitor。佢喺 magnifier 文獻入面嘅角色純粹係學者(見
  `docs/2026-07-09_magnifier_literature.md` §1「回報極度偏態」——證明少數股撐起大部分
  財富創造嗰篇論文作者),同「邊隻股佢自己揸」完全冇關係。用戶原意應該係問底層 idea
  (追蹤高信念集中倉嘅投資者),下面 2.2–2.5 answer 呢條底層 idea。

### 2.2 Cohen, Polk, Silli / Anton, Cohen, Polk, "Best Ideas"

原始版:Cohen, Polk, Silli,SSRN 2010(abstract_id=1364827)。
現行擴充版:Antón, Cohen, Polk,Harvard Business School Working Paper No. 21-004
(2021-04-21 最後更新),LSE 版本:[personal.lse.ac.uk/polk/research/bestideas.pdf](https://personal.lse.ac.uk/polk/research/bestideas.pdf)

- **方法**:用共同基金/對沖基金申報持倉,對每個基金經理定義「Best Idea」= 相對佢自己
  基準嘅**主動押注最重**嗰隻股(唔係持倉市值最大,而係相對 benchmark 嘅 active weight
  最高),逐個經理追蹤呢隻股嘅表現,同佢自己基金其餘持倉、同大盤比較。
- **核心發現**:經理嘅「Best Idea」跑贏大盤同跑贏自己基金其餘持倉,**約 2.8–4.5%/年**
  (視乎用邊個 benchmark);細基金嘅 best idea 跑贏大基金嘅 best idea 達 **15%/年**;
  絕大部份「非 best idea」持倉**冇**顯著超額回報。
- 信心:🟢 核心發現(多個獨立來源一致引用同一組數字)· ⚠️ **發表狀態**:**搜尋唔到呢篇
  正式喺任何同行評審期刊發表嘅記錄**——由 2010 年 SSRN 掛出到 2021 年 HBS working
  paper 版本,一直維持 working paper 狀態,雖然學界/業界引用量極高(Value Line 等實務
  機構常引用),但**唔可以當「已發表、經同行評審把關」嘅結論**,只可以當「方法論扎實、
  高度可信但未經正式期刊審核」嘅證據。
- **可 encode 成乜**:核心 idea 係「唔好抄基金全部持倉,淨係抄相對 benchmark 主動押注
  最重嗰幾隻」——套落我哋語境,如果要做 13F probe,篩選邏輯應該係「邊個經理嘅邊隻持倉
  係佢嘅 active bet(相對佢自己 historical 持倉集中度嘅異常高權重),唔係佢個 13F
  表格入面市值最大嗰隻(可能只係大盤指數型持倉)」。

### 2.3 Frank, Poterba, Shackelford, Shoven, "Copycat Funds: Information Disclosure Regulation and the Returns to Active Management in the Mutual Fund Industry"

*Journal of Law and Economics*, Vol. 47, Issue 2 (2004), pp. 515–541.
DOI: [10.1086/422982](https://doi.org/10.1086/422982) · NBER WP 8653(2001-12 首發,
[nber.org/papers/w8653](https://www.nber.org/papers/w8653))

- **方法**:模擬「copycat 基金」——喺主動基金披露持倉**之後**先照抄,量度扣除費用後嘅
  淨回報,對比原基金表現。樣本聚焦 1990 年代一批高費用主動基金(**半年披露**年代,即
  比而家嘅季度 13F 更遲、更粗)。
- **核心發現**:扣費前主動基金顯著跑贏 copycat;**扣費後,copycat 基金嘅回報同原基金
  「統計上冇分別,甚至可能更高」**——即抄仔嘅劣勢主要嚟自主動基金本身收費貴,唔係延遲
  披露本身抹殺晒 edge。
- 信心:🟢(JLE 官方 DOI + NBER 摘要核實一致)
- **意涵**:呢篇用嘅係更差條件(半年延遲、非最優篩選標的),都搵到 copycat 唔輸——喺
  而家季度 13F(45 日延遲)嘅環境下,理論上 copycat 嘅相對劣勢應該更細。

### 2.4 Verbeek & Wang, "Better than the Original? The Relative Success of Copycat Funds"

*Journal of Banking & Finance*, Vol. 37, Issue 9 (2013), pp. 3454–3471.
DOI 經 ScienceDirect:[S0378426613002070](https://www.sciencedirect.com/science/article/abs/pii/S0378426613002070)

- **核心發現**:重做 copycat 策略研究,發現 **copycat 相對成功嘅程度喺 2004 年 SEC 將
  披露頻率由半年改為季度後顯著提升**——直接證據支持「披露愈頻密,copycat 可以捕捉嘅
  edge 愈多」。
- 信心:🟢(ScienceDirect + RePEc + SSRN 三源核實)
- **意涵**:同 2.3 合讀,兩篇獨立團隊喺唔同年代嘅樣本都話 copycat 可行,而且季度披露
  (而家嘅 13F 標準)比半年披露(2.3 嘅樣本年代)對 copycat 更有利——支持「45 日延遲
  雖然唔完美,但唔係致命傷」嘅判斷。

### 2.5 Puckett & Yan, "The Interim Trading Skills of Institutional Investors"

*Journal of Finance*, Vol. 66, Issue 2 (2011), pp. 601–633.
DOI: [10.1111/j.1540-6261.2010.01643.x](https://doi.org/10.1111/j.1540-6261.2010.01643.x)

- **方法**:用一個包含季度**內**逐日交易嘅獨有機構交易資料庫(唔止季末快照),量度機構
  喺**季度中間**(quarter 內、13F 睇唔到嗰段)嘅買賣交易技巧。
- **核心發現**:機構嘅季內(interim)交易存在顯著、持續嘅選股技巧,扣除交易成本後,對
  基金整體年化超額表現貢獻 **20–26 個基點**。
- 信心:🟢(JF 官方 DOI + JSTOR + SSRN 三源核實)
- **意涵——呢篇係 13F/45 日延遲呢條路嘅「量化代價」**:證明 13F 季末快照本身**睇唔到**
  嘅嗰部分交易(季度內買咗又賣、換馬)本身有真實 alpha(20-26bp/年),即係話**單靠 13F
  季末快照,天生就漏走一截機構真正嘅技巧**——呢個係支持我哋 2.2-2.4 判斷嘅反面提醒:
  抄 13F 快照,注定抄唔晒,只可以抄到「持有到季末仲未平倉」嗰部分,而且仲要等 45 日先
  出爐。呢個唔係否定 copycat 可行(2.3/2.4 已證明扣費後仲有 edge),而係量化咗「呢個
  管道結構性有多殘缺」。

### 組 2 總表

| 論文 | 期刊/年 | 核心發現 | 對 13F probe 判斷嘅意涵 |
|---|---|---|---|
| Cohen-Polk-Silli/Anton-Cohen-Polk「Best Ideas」 | HBS working paper(未正式發表) | 高信念倉(active weight 最高)跑贏 2.8-4.5%/年 | 篩選邏輯核心:抄 active bet,唔係抄市值最大持倉 |
| Frank-Poterba-Shackelford-Shoven (2004) | JLE | 半年延遲下扣費後 copycat 回報同原基金無異 | 延遲本身唔致命,費用先係主因 |
| Verbeek-Wang (2013) | JBF | 2004 轉季度披露後 copycat 相對成功度提升 | 季度(較短延遲)比半年披露對 copycat 更有利 |
| Puckett-Yan (2011) | JF | 機構季內(13F 睇唔到)交易技巧貢獻 20-26bp/年 | 量化 13F 快照結構性漏走嘅部分,設定 probe 嘅上限預期 |

**同 insider-cluster(`2026-07-08_insider_cluster_probe.md`,已證陰性)嘅分別**:insider
cluster 探測失敗嘅根本原因係**冇料**(memory/power 兩個核心 AI 主題全期 zero-fire,樣本
太薄)同**訊噪比低**(同一 fire 內兩隻股常一贏一輸)。13F/Best-Ideas 路線唔一樣——(a)
數據密度遠高(全市場機構持倉,唔係得個別 insider 嘅零星 open-market 買賣);(b)「Best
Ideas」方法論本身有明確嘅前置篩選邏輯(active weight,唔係單純「有冇買」);(c) 有兩篇
獨立文獻(2.3/2.4)證實延遲/頻率問題唔致命。**但呢條路線仍然只值得做 probe**,理由:
Best Ideas 論文本身**未經同行評審發表**(信心打折扣);而且 Best Ideas 嘅篩選單位係
「一個基金經理嘅一隻股」,套落我哋語境要解決嘅第一個問題係「邊個經理值得抄」(過往
track record 揀中 multi-bagger 嘅少數集中投資者),呢個前置篩選冇現成學術公式,係
probe 要自己解決嘅部分,唔係文獻直接畀嘅答案。

---

## 回報結論(重述)

- **文本訊號組**兩篇最直接可用:**Cohen-Malloy-Nguyen (2020 JF)**——加 Δscore(變化量)
  做主訊號嘅學術支撐;**Theile-Hofer-Singhal-Hoberg (2026 POM)**——電話會 NLP 量度供應鏈
  受限語言預測回報嘅方法論最直接佐證,建議引用喺 `exp_constraint_language.py` 檔頭。
- **13F idea 值得做 probe**(唔係 commitment):底層邏輯(Best Ideas 篩選)有學術支撐,
  45 日延遲代價已被量化(Puckett-Yan 20-26bp/年)但唔致命(Frank-Poterba/Verbeek-Wang
  兩篇證實扣費後仲有 edge);但要解決「邊個經理值得抄」呢個前置問題,冇現成公式。
- **Bessembinder 釐清**:佢係純學者(ASU 教授 + 訴訟顧問),冇基金冇 13F,監測佢個人
  持倉呢個字面主意不成立;佢喺本 repo 文獻入面嘅角色係「回報極度偏態」實證(另一份
  magnifier 文獻檔),同 smart-money 追蹤完全唔相關。
- **需唔需要多讀書**:**唔需要**——現有 regex/詞表方法已經係 Loughran-McDonald(2011）
  「constraining」呢類正式學術詞典嘅同類做法,方向已證(Lazy Prices、Theile et al.),
  可以直接落地;Frankel-Jennings-Lee(2022)嘅 ML 升級路徑係已知選項,留返做 v2,唔阻住
  而家嘅 v0/v1 落地決定。

---

## 產物

- 本文件:`docs/2026-07-09_text_and_smartmoney_methodology.md`
- 對照/背景檔(唔重覆):`docs/2026-07-09_magnifier_literature.md`(21 篇 magnifier 文獻)
- 相關既有探針:`backtest/results/2026-07-08_constraint_language_probe.md`(文本訊號原型,
  已證 MU 早 17 個月)、`backtest/results/2026-07-08_insider_cluster_probe.md`(insider
  群買,已證陰性,做本文 13F 判斷嘅對照組)

## 未解/風險

1. Best Ideas(2.2)未經同行評審正式發表,雖然引用量高、方法論扎實,但正式落地前應該
   當「高可信 working paper」而非「已審核期刊結論」處理,同 repo 一貫紀律(引用強度要
   如實標注)一致。
2. 「邊個經理值得抄」呢個前置篩選,7 篇文獻入面冇一篇直接畀答案(Best Ideas 講嘅係
   「識別佢自己嘅 best idea」,前提係已經揀定邊個經理),如果要做 13F probe,呢個係
   第一個要自己設計嘅步驟(例如:回溯測試邊類機構嘅「集中新增倉」historically 領先
   multi-bagger)。
3. Loughran-McDonald「constraining」官方詞表嘅具體 184 個詞內容未直接下載核對(只核實
   數量同存在,冇逐詞比對我哋自訂 regex)——如果要做組 1 建議嘅「外部基準交叉對照」,
   下一步要去 SRAF 官網下載完整詞表 CSV。
4. Theile-Hofer-Singhal-Hoberg(2026)標示為 ahead-of-print/2026,屬最新接受但可能仲
   未正式排入印刷卷期,DOI 已可解析、期刊本身信譽良好(POM 係 FT-50 A+），信心維持 🟢,
   但如果日後 DOI 有變動需要留意。
