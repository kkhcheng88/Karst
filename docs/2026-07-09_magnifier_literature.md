# Supercycle Magnifier 模型 —— 學術文獻地基(2026-07-09)

> 對應 `docs/2026-07-09_magnifier_model_plan.md` 步驟 B。目的:用 peer-reviewed 論文/NBER-SSRN
> working paper 支撐「點解少數股會被供需超級週期非線性放大成 10x」嘅模型假設,並分辨
> **真 magnifier 訊號** vs **彩票股追高陷阱**。
>
> **方法**:5 個獨立 subagent 平行 WebSearch/WebFetch,逐篇核實作者/年份/期刊/卷期/DOI 是否
> 對得上(唔靠訓練記憶砌citation);有數字嘅盡量攞兩個獨立來源交叉核對。
>
> **信心標記**:🟢 = 已用 primary source(期刊頁/SSRN/NBER/作者頁)核實
> · 🟡 = citation 本身核實,但關鍵數字只搵到 secondary summary 佐證,冇 primary text 核對
> · 🔴 = 搵過但冇搵到嚴格 peer-reviewed 文獻(如實講明,唔砌假論文)

## 0. 一句結論

搵到 **21 篇**已核實嘅論文/working paper,覆蓋 7 個主題入面 6 個有紮實學術地基(第 4 主題「週期股
估值倒轉」冇專門期刊論文,只有實務界 heuristic + 相鄰嘅 profitability mean-reversion 學術文獻)。
最直接可用嗰 3 篇:**Bessembinder (2018/2023)**(整個 magnifier 邏輯嘅實證地基——極少數股票撐起
全部財富)、**Novy-Marx (2011) Operating Leverage**(feature #1 直接可 encode 嘅量度公式)、
**Bali-Cakici-Whitelaw (2011) MAX effect**(feature #5「情緒/擁擠」嘅風控篩,防止把彩票股追高當
alpha)。**同 repo 已知結論冇直接衝突**,但發現 1 個文獻內部張力(§9:Hou-Robinson vs
Grullon-Larkin-Michaely 對「產業集中度」方向相反),已 resolve 成「用集中度**變化**唔用**水平**」
嘅 feature 設計建議。

---

## 1. 回報極度偏態(少數股撐起全部財富)—— 支撐組

呢組係「10x 點解重要 + 幾罕見」嘅實證地基:少數股票撐起幾乎全部長期財富創造,大多數股票連
一個月期國庫券都跑輸。

**1.1 Hendrik Bessembinder, "Do Stocks Outperform Treasury Bills?"**
*Journal of Financial Economics*, Vol. 129, Issue 3 (2018), pp. 440–457.
DOI: [10.1016/j.jfineco.2018.06.004](https://doi.org/10.1016/j.jfineco.2018.06.004) ·
SSRN: [abstract_id=2900447](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2900447)
- 核心發現:1926–2015 CRSP 全美股樣本,**最好嘅 4% 上市公司撐起全部美股淨財富創造**;
  其餘 ~96% 股票合計只等於國庫券回報。約 58% 個股一生持有回報低於一個月國庫券(🟡 此數字
  只搵到 secondary summary 佐證)。歸因於個股回報分佈嘅正偏態(月度偏態 + 複利)。
- 信心:🟢(headline 4% 數字/主結論已用 2 個獨立 institutional repository 核實一致)
- 可 encode 成邊個 feature:唔係直接 feature,而係**整個模型嘅存在理由** —— 證明呢個問題係
  base-rate/tail-identification 問題,唔係 mean-return 問題。意涵:(a) 部位集中度紀律要容許
  贏家不設上限咁複利,唔好過早獲利了結;(b) 篩選特徵應該扣連「偏態持續性」而唔係
  expected-return/Sharpe 類特徵;(c) payoff function 入面漏 10x(false negative)嘅代價要遠大過
  揸中一隻蝕本股(false positive)。

**1.2 Hendrik Bessembinder, Te-Feng Chen, Goeun Choi, K.C. John Wei, "Long-Term Shareholder
Returns: Evidence from 64,000 Global Stocks"**
*Financial Analysts Journal*, Vol. 79, No. 3 (2023), pp. 33–63.
DOI: [10.1080/0015198X.2023.2188870](https://doi.org/10.1080/0015198X.2023.2188870)
(peer-reviewed 定稿版;2019 SSRN/NBER working paper 版本 abstract_id=3415739 數字唔同,用呢篇
2023 定稿為準)
- 核心發現:64,000+ 全球普通股,1990–2020。**美股 55.2%、非美股 57.4% 一生跑輸一個月美國國庫券**;
  最強嘅 **2.4% 公司撐起全部 $75.7 兆全球淨財富創造**;單計美國以外,只係 **1.41%** 公司撐起
  $30.7 兆。
- 信心:🟢(2 個獨立大學機構典藏頁一字不差引述出版社摘要)
- 可 encode 成邊個 feature:全球樣本印證 1.1 唔係美股獨有現象,tail 比例喺美國以外更極端
  (1.41% vs 4%)——強化「magnifier 揀股要夠狠、唔好中庸分散」嘅論點。

**1.3(相鄰對照)Fang, Marshall, Nguyen, Visaltanachoti, "Do Stocks Outperform Treasury Bills
in International Markets?"**
*Finance Research Letters*, Vol. 40 (2021), Art. 101686.
- 核心發現:65,000 隻股票、57 個國家,55/57 個市場多數股票跑輸國庫券;跑輸比率同治理質素/
  金融發展程度負相關 —— 提供治理質素做調節變數,同 Bessembinder 系列係唔同作者嘅獨立佐證,
  唔好同 1.1/1.2 混為一談。
- 信心:🟢(citation 核實;此為輔助佐證,唔係核心引用)
- 可 encode 成邊個 feature:提示如果將來 magnifier 掃描擴去非美股,治理質素應該做前置閘門。

---

## 2. 資本週期 / 供給側投資理論 —— 支撐組

Marathon/Chancellor 嘅資本週期實務框架之外,peer-reviewed 學界有獨立嘅 asset-growth / investment
anomaly 文獻支撐「資本紀律 → 未來回報」呢條邏輯鏈。

**2.1 Cooper, Gulen, Schill, "Asset Growth and the Cross-Section of Stock Returns"**
*Journal of Finance*, Vol. 63, Issue 4 (2008), pp. 1609–1651.
DOI: [10.1111/j.1540-6261.2008.01370.x](https://doi.org/10.1111/j.1540-6261.2008.01370.x)
- 核心發現:1968–2003,年度資產增長率係眾多橫斷面變數入面**最強嘅負向回報預測因子**(比
  B/M、規模、動能都強),大型股一樣顯著。低資產增長十分位年化 ~26% raw return,高資產增長
  十分位 ~6%,約 20%/yr 等權差距(13%/yr 市值加權)(🟡 magnitude 只搵到 secondary
  summary/Quantpedia 複製佐證,論文原文 paywall 未直接核對)。
- 信心:🟢 citation/方向 · 🟡 magnitude
- 可 encode 成邊個 feature:對應 model plan feature #2(供給受限)嘅**反向輸入** —— 產業/個股
  trailing 資產增長率(或 capex/PP&E 增長)作為 NEGATIVE input:高增長 = 資本追週期 = fade
  訊號;低/負增長 = 資本紀律 = amplify 訊號。呼應 MU anecdote「對手過剩期砍 capex → 供給收緊」。

**2.2 Titman, Wei, Xie, "Capital Investments and Stock Returns"**
*Journal of Financial and Quantitative Analysis*, Vol. 39, Issue 4 (2004), pp. 677–700.
DOI: [10.1017/S0022109000003173](https://doi.org/10.1017/S0022109000003173) ·
NBER WP 9951: [nber.org/papers/w9951](https://www.nber.org/papers/w9951)
- 核心發現:大幅增加資本支出嘅公司,其後基準調整回報顯著為負;效應喺高裁量權公司(高現金流、
  低負債)較強,喺敵意收購紀律活躍時較弱 —— 同「市場對 empire building 反應不足」一致。
  **magnitude 唔可靠**(多個 secondary 來源數字互相矛盾,由 2.65%/yr 到 16.8%/yr 到
  -4%~-7.5%/yr 都有),所以只引方向,唔引具體數字。
- 信心:🟢 方向(NBER 摘要核實) · 🔴 magnitude(唔可靠,故意唔引用具體數字)
- 可 encode 成邊個 feature:產業級 capex 增長「加速度」(相對自身趨勢,唔淨係 YoY),按資本配置
  紀律(回購、維權股東壓力)做裁量權加權折讓。

**2.3 Fama & French, "A Five-Factor Asset Pricing Model"**
*Journal of Financial Economics*, Vol. 116, Issue 1 (2015), pp. 1–22.
DOI: [10.1016/j.jfineco.2014.10.010](https://doi.org/10.1016/j.jfineco.2014.10.010)
- 核心發現:加入獲利能力(RMW)同投資(CMA,conservative-minus-aggressive)兩個因子;
  1963–2013 美股樣本,CMA 同 HML 相關性 ~0.7,令 HML 喺解釋平均回報上變得統計上多餘 ——
  即「低投資跑贏高投資」已經係一個被定價嘅正式 factor,唔止係 anomaly(CMA 具體月均回報數字
  未能經 primary source 核實,故略去)。
- 信心:🟢 citation/核心結論 · 🔴 CMA 具體數字未核實(略去)
- 可 encode 成邊個 feature:理論驗證「投資保守性」係合法被定價因子;可以建構 sector-relative
  CMA 式 spread(同產業內低 vs 高 capex 增長公司)做 magnifier 嘅子分數。

**2.4 Lyandres, Sun, Zhang, "The New Issues Puzzle: Testing the Investment-Based Explanation"**
*Review of Financial Studies*, Vol. 21, Issue 6 (2008), pp. 2825–2855.
- 核心發現:低減高投資因子平均 +0.57%/月;加入標準因子回歸後,可解釋 SEO 跑輸 ~75%、IPO
  跑輸 ~80%、可轉債跑輸 ~50%、Daniel-Titman 綜合發行效應 ~40% —— 支持 q-theory/real-options
  對新股發行謎團嘅解釋(🟡 magnitude 經 2 個獨立搜尋一致,但原文 PDF 未直接解析核對)。
- 信心:🟢 citation · 🟡 magnitude
- 可 encode 成邊個 feature:股權融資驅動嘅 capex 擴張(IPO/SEO 後產能建設)作為額外負向
  overlay —— 即使短期敘事睇好,標記為「供給側逆風」。

---

## 3. 營運槓桿同股票回報 —— 支撐組(model plan feature #1 直接對應)

**3.1 Robert Novy-Marx, "Operating Leverage"**
*Review of Finance*, Vol. 15, Issue 1 (2011), pp. 103–134.
DOI: [10.1093/rof/rfq019](https://doi.org/10.1093/rof/rfq019)
- 核心發現:OL 量度 = (COGS+SG&A)/總資產(Compustat AT),五分位由 0.14(低)到 2.18(高)。
  1963–2008,高 OL 組合跑贏低 OL 組合 **44 bp/月(市值加權,t=2.69)、51 bp/月(等權,t=3.35)**,
  年化 Sharpe **0.40(VW)/0.50(EW)** —— 同 value 策略(HML)嘅 0.43 相若。價值溢價喺**產業內**
  強而單調,喺**跨產業**弱且非單調 —— 由產業內 OL 差異驅動。
- 信心:🟢(直接下載 PDF 全文抽取核對,非中介 summary)
- 可 encode 成邊個 feature:**直接對應 model plan feature #1**——(COGS+SG&A)/資產作為 OL 分數;
  用作週期性名股嘅收入增長/動能訊號嘅**乘數**(唔係獨立買入訊號)。

**3.2 Mandelker & Rhee, "The Impact of the Degree of Operating and Financial Leverage on
Systematic Risk of Common Stock"**
*Journal of Financial and Quantitative Analysis*, Vol. 19, Issue 1 (1984), pp. 45–57.
DOI: [10.2307/2331000](https://doi.org/10.2307/2331000)
- 核心發現:由 Hamada/Rubinstein beta 分解正式推導 DOL/DFL;51 個組合按 beta 排序回歸,
  **DOL 單獨解釋 14%** 橫斷面 beta 變異,DFL 單獨解釋 33%,兩者相關係數約 -0.30 —— 確認營運槓桿
  獨立於財務槓桿都會推高股票系統性風險(beta)。
- 信心:🟢(作者學院典藏全文核對,同 JFQA 期刊頁一致)
- 可 encode 成邊個 feature:提供 OL → beta 放大嘅古典理論基礎,支持將 OL 當作「風險/回報放大器」
  而唔止係「回報放大器」——magnifier 揀出嘅股票預期波動都會同步放大,倉位管理要對應。

**3.3 Gu, Hackbarth, Johnson, "Inflexibility and Stock Returns"**
*Review of Financial Studies*, Vol. 31, Issue 1 (2018), pp. 278–321.
DOI: [10.1093/rfs/hhx092](https://doi.org/10.1093/rfs/hhx092)
- 核心發現:關鍵細節 —— OL 只喺**規模缺乏彈性**(產能唔能夠快速伸縮)嘅公司先會推高風險/回報;
  彈性公司(容易擴張/收縮)OL 甚至可能令回報**下降**。1980–2013,高減低「準固定成本」五分位
  回報差,喺最有彈性產業只係 **19 bp/月(t=1.14,不顯著)**,喺最缺彈性產業升到 **72 bp/月
  (t=3.28)**。
- 信心:🟢(working paper 全文核對內容,期刊卷期經 RePEc/IDEAS 交叉核實)
- 可 encode 成邊個 feature:同 feature #4(樽頸位置)交互 —— OL 放大器要同「資產不可撓性」
  (fab/重資產、產能擴建需要幾年)做交乘項,先最貼合 MU anecdote(晶圓廠固定成本 + 產能擴建
  需時)。

**3.4(限制條件,提醒)Kogan, Li, Zhang, "Operating Hedge and Gross Profitability Premium"**
*Journal of Finance*, Vol. 78, Issue 6 (2023), pp. 3387–3422.
- 核心發現:可變/週期性投入成本可以形成「營運避險」,抵銷部分 OL 嘅風險放大效應,尤其對低毛利
  公司 —— 呢個係 OL 訊號嘅**限制條件**,唔係反證,但提醒 OL 分數要連同毛利結構一齊睇,唔可以
  單一量度硬套所有產業。
- 信心:🟢(citation 經 2 個獨立搜尋核實)
- 可 encode 成邊個 feature:OL 分數嘅 sanity check——投入成本高度可變嘅產業(例如商品型
  加工業)OL 訊號應該降權。

---

## 4. 週期股估值倒轉 —— 支撐組(冇專門期刊論文,誠實標注)

**冇搵到專門處理「週期股 P/E 喺 peak 最平、trough 最貴」呢個現象嘅期刊論文** —— 呢個係實務界
heuristic,最出名嘅係 James Montier(GMO)嘅評論:投資者錯誤咁「喺 peak earnings 畀 peak
multiple、喺 trough earnings 畀 trough multiple」,佢建構咗一個 Graham & Dodd P/E 篩(股價 ÷
10 年移動平均 EPS,門檻 <16x)去避開呢個陷阱。呢個唔係期刊論文,信心標🔴(只有實務界研究,
如實講明,唔砌假論文充數)。

最貼近嘅學術地基係「獲利能力均值回歸」文獻:

**4.1 Fama & French, "Forecasting Profitability and Earnings"**
*Journal of Business*, Vol. 73, No. 2 (2000), pp. 161–175.
DOI: [10.1086/209638](https://doi.org/10.1086/209638) ·
SSRN: [abstract_id=40660](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=40660)
- 核心發現:1964–1996 逐年橫斷面回歸,獲利能力喺簡單 partial-adjustment 模型下約
  **每年均值回歸 38%**,但呈非線性——低於均值時回歸較快,偏離均值越遠回歸越快。呢個均值回歸
  產生未來盈餘嘅可預測變異,即**現時(極端)盈餘係 normalized 盈餘嘅劣質嚮導**。
- 信心:🟢(JSTOR/SSRN 摘要核實)
- 可 encode 成邊個 feature:**直接對應 model plan feature #3**(距底部幾遠)——用
  normalized/mid-cycle 盈餘(唔用 trailing)去計算真實估值水平。

**4.2 Campbell & Shiller, "Stock Prices, Earnings, and Expected Dividends"**
*Journal of Finance*, Vol. 43, Issue 3 (1988), pp. 661–676.
DOI: [10.1111/j.1540-6261.1988.tb04598.x](https://doi.org/10.1111/j.1540-6261.1988.tb04598.x) ·
NBER WP 2511: [nber.org/papers/w2511](https://www.nber.org/papers/w2511)
- 核心發現:1871–1986 美股總體數據,長期(移動)平均實質盈餘係未來股息現值嘅良好預測因子;
  最優預測**2/3 到 3/4 嘅權重放喺 smoothed/normalized 盈餘**,唔係單靠現價。呢篇係 CAPE
  嘅方法論始祖,原文係指數層級,唔係產業/個股層級。
- 信心:🟢(NBER/Wiley 摘要核實)
- 可 encode 成邊個 feature:同 4.1 一齊構成「產業/個股層級 cyclically-adjusted P/E」嘅方法論
  基礎——股價 ÷ N 年 trailing 或 regression-normalized EPS,喺 trough(trailing P/E 睇落貴或
  無意義)反而評分吸引,喺 peak(trailing P/E 睇落平)反而評分貴。

---

## 5. 樽頸 / 定價權 / 產業結構同超額利潤 —— 支撐組(內部有張力,見 §9)

**5.1 Grullon, Larkin, Michaely, "Are US Industries Becoming More Concentrated?"**
*Review of Finance*, Vol. 23, Issue 4 (2019), pp. 697–743.
SSRN: [abstract_id=2612047](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2612047)
- 核心發現:超過 75% 嘅美國產業自 1990 年代後期起 HHI 集中度上升(平均 +90%,1997 年起
  總體集中度 +70%),**冇證據顯示營運效率提升**,論文明確指出集中度帶嚟嘅較高毛利
  **「反映喺較高嘅股東回報」**。
- 信心:🟢(Oxford Academic 摘要頁核實)
- 可 encode 成邊個 feature:對應 feature #2/#4——產業集中度**趨勢**(HHI 上升,即整合中嘅
  產業)作為定價權/毛利順風訊號。

**5.2 De Loecker, Eeckhout, Unger, "The Rise of Market Power and the Macroeconomic
Implications"**
*Quarterly Journal of Economics*, Vol. 135, Issue 2 (2020), pp. 561–644.
DOI: [10.1093/qje/qjz041](https://doi.org/10.1093/qje/qjz041) ·
NBER WP 23687: [nber.org/papers/w23687](https://www.nber.org/papers/w23687)
- 核心發現:美國企業平均加價率(markup)自 1980 年起由高於邊際成本 21% 升到 61%(定稿數字;
  2017 年 NBER 初稿數字為 18%→67%,發表前有修訂,以定稿為準),平均利潤率由 1% 升到 8%,
  由上尾企業驅動(中位數企業加價率無變)。
- 信心:🟢(NBER/QJE 交叉核實,包括修訂前後數字差異)
- 可 encode 成邊個 feature:呼應「定價權集中喺上尾少數贏家」——同 §1 Bessembinder 財富集中
  發現互相呼應,強化「magnifier 應該搵產業內上尾定價權贏家,唔係產業平均」嘅選股邏輯。

**5.3(方向相反,張力來源)Hou & Robinson, "Industry Concentration and Average Stock Returns"**
*Journal of Finance*, Vol. 61, Issue 4 (2006), pp. 1927–1956.
DOI: [10.1111/j.1540-6261.2006.00893.x](https://doi.org/10.1111/j.1540-6261.2006.00893.x) ·
SSRN: [abstract_id=479726](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=479726)
- 核心發現(方向已確認,唔係估計):**產業集中度較高嘅公司,平均回報反而較低**(控制規模/
  B-M/動能後依然穩健),歸因於進入門檻降低咗財務困境風險,及/或集中產業創新較少 —— 即集中度
  係較低風險嘅代理,唔係定價權 alpha 嘅代理。呢個結論**同 5.1 精神相反**,已喺 §9 討論點
  resolve。
- 信心:🟢(方向經直接核對,唔係憑印象假設)
- 可 encode 成邊個 feature:警示唔好將**靜態高集中度水平**直接當正向 feature;見 §9 建議。

---

## 6. 反面警告:Lottery stocks / MAX effect —— 警告組(model plan feature #5 直接對應)

呢組係「唔好把所有 10x-chasing 當 alpha」嘅關鍵反證,分辨**真 magnifier**(基本面驅動嘅
非線性放大)vs **彩票股**(純偏態/擁擠驅動,平均跑輸)。

**6.1 Bali, Cakici, Whitelaw, "Maxing Out: Stocks as Lotteries and the Cross-Section of Expected
Returns"**
*Journal of Financial Economics*, Vol. 99, Issue 2 (2011), pp. 427–446.
DOI: [10.1016/j.jfineco.2010.08.014](https://doi.org/10.1016/j.jfineco.2010.08.014) ·
SSRN: [abstract_id=1262416](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1262416)
- 核心發現:MAX = 過去一個月**最高 5 個交易日回報嘅平均值**(MAX(5))。原文:「最低同最高
  MAX 十分位之間嘅平均 raw 同風險調整回報差**超過 1%/月**」——呢個係月度數字,raw 同
  risk-adjusted(alpha)都成立,喺控制規模、B/M、動能、短期反轉、流動性、偏態後依然穩健。
  一個重要副結果:控制 MAX 後,原本負向嘅特異波動率-回報謎團會反轉。
- 信心:🟢(DOI 解析到 ScienceDirect 記錄,同 repec 摘要一致)
- 可 encode 成邊個 feature:**直接對應 model plan feature #5**(情緒/擁擠,低=早=好)——對
  magnifier 候選股計算 MAX(5) 作為**取消資格/降權**篩:如果近期極端回報集中喺少數單日
  (options gamma squeeze、meme 資金流),而冇對應基本面突變(capex 承諾、backlog、毛利
  guidance)佐證,視為彩票股追高,唔係真正嘅資本週期 re-rating——降權或唔追,唔好追高。

**6.2 Kumar, "Who Gambles in the Stock Market?"**
*Journal of Finance*, Vol. 64, Issue 4 (2009), pp. 1889–1933.
DOI: [10.1111/j.1540-6261.2009.01483.x](https://doi.org/10.1111/j.1540-6261.2009.01483.x)
- 核心發現:彩票型股票定義為低價(<$5)、高波動、高特異偏態嘅股票;有博彩傾向嘅散戶(用
  州彩票銷售/人口統計特徵代理——低收入、高本地失業率、經濟低迷期間持倉比例偏高)系統性
  超配呢類股票,而呢種博彩驅動需求同其後跑輸相關(呢類投資者組合實現回報約低 2-3 個百分點)。
- 信心:🟢(Wiley JF 記錄 + repec + 多個獨立 secondary summary 一致)
- 可 encode 成邊個 feature:提供額外「擁擠檢查」——如果 magnifier 候選股嘅擁擠特徵吻合
  Kumar 嘅散戶博彩畫像(低價股、options 活動異常爆升、社交情緒過熱),而冇機構/capex 週期
  佐證,更可能係 Kumar 式博彩資金流,唔係真正超級週期拐點。

**6.3 Boyer, Mitton, Vorkink, "Expected Idiosyncratic Skewness"**
*Review of Financial Studies*, Vol. 23, Issue 1 (2010), pp. 169–202.
DOI: [10.1093/rfs/hhp041](https://doi.org/10.1093/rfs/hhp041)
- 核心發現:建構一個**預測性**(而唔止事後量度)特異偏態橫斷面模型,發現預期偏態被負向定價:
  低預期偏態五分位嘅 Fama-French alpha 比高預期偏態五分位**高 1.00%/月**(風險調整後、
  月度、五分位差)。呢個亦有助解釋特異波動率折讓現象。
- 信心:🟢(BYU 學院典藏全文引述,同 Oxford Academic 記錄一致)
- 可 encode 成邊個 feature:因為呢個係**預測性**模型(唔淨係 trailing MAX),係最可直接複用嘅
  一篇——可以喺 model 入面建構類似嘅「預期偏態分數」(由基本面特徵預測,唔淨係睇實現回報),
  凡係分數落喺最高偏態五分位嘅 magnifier 候選股,除非基本面(收入/毛利軌跡)獨立佐證,否則
  篩走。

---

## 7. (可選)動能/quality 喺 theme 層面嘅實證 —— 支撐組

**7.1 Moskowitz & Grinblatt, "Do Industries Explain Momentum?"**
*Journal of Finance*, Vol. 54, Issue 4 (1999), pp. 1249–1290.
- 核心發現:產業級動能龐大且高度可獲利;個股動能利潤「幾乎全部」可歸因於產業層級動能,
  唯獨 12 個月期限,個股特定動能依然獨立存在。
- 信心:🟢(AQR 自家發布頁核實)
- 可 encode 成邊個 feature:支持 theme/產業層級動能係一個合法嘅確認訊號,可以幫手判斷
  「價值鏈邊個 node 已經被市場定價」(呼應 model plan §3b 逐 node 標 stage 嘅需要)。

**7.2 Asness, Frazzini, Pedersen, "Quality Minus Junk"**
*Review of Accounting Studies*, Vol. 24, Issue 1 (2019), pp. 34–112.
DOI: [10.1007/s11142-018-9470-2](https://doi.org/10.1007/s11142-018-9470-2)
(原為 AQR working paper)
- 核心發現:Quality 由獲利能力、增長、安全性、派息定義;做多 quality/做空 junk(QMJ)因子喺
  美股同 24 個國家都賺取顯著風險調整回報;quality 嘅定價隨時間變化,並可預測未來 QMJ 回報
  (均值回歸)。
- 信心:🟢(Springer/EconPapers + AQR working paper 摘要交叉核實)
- 可 encode 成邊個 feature:可以做 magnifier 籃子入面嘅 sanity-check overlay ——避免將
  資產負債表脆弱嘅純彩票名股計入,同時 QMJ 嘅「安全性」維度可以幫手扣連 feature #1
  營運槓桿嘅下行風險控管。

---

## 8. 兩組總表

### 支撐組(magnifier 存在嘅實證地基)

| 主題 | 論文 | 對應 model plan feature |
|---|---|---|
| 回報偏態 | Bessembinder (2018), Bessembinder et al. (2023) | 整體存在理由(倉位集中/唔早獲利) |
| 資本週期 | Cooper-Gulen-Schill (2008), Titman-Wei-Xie (2004), Fama-French (2015), Lyandres-Sun-Zhang (2008) | #2 供給受限(反向輸入) |
| 營運槓桿 | Novy-Marx (2011), Mandelker-Rhee (1984), Gu-Hackbarth-Johnson (2018) | **#1 營運槓桿(直接)**、#4 樽頸位置(交乘) |
| 週期估值倒轉 | Fama-French (2000), Campbell-Shiller (1988) | **#3 距底部幾遠(直接)** |
| 樽頸/定價權 | Grullon-Larkin-Michaely (2019), De Loecker-Eeckhout-Unger (2020) | #2/#4(用趨勢唔用水平) |
| 動能/quality(可選) | Moskowitz-Grinblatt (1999), Asness-Frazzini-Pedersen (2019) | value-chain node staging 確認訊號 |

### 警告組(彩票/追高陷阱)

| 論文 | 警告內容 | 對應 model plan feature |
|---|---|---|
| Bali-Cakici-Whitelaw (2011) MAX effect | 高偏態股平均跑輸 >1%/月 | **#5 情緒/擁擠(直接篩)** |
| Kumar (2009) 散戶博彩 | 彩票股由博彩性散戶資金流推升,其後跑輸 | #5 擁擠檢查(散戶博彩畫像) |
| Boyer-Mitton-Vorkink (2010) 預期偏態 | 預期高偏態被負向定價,1%/月 alpha 差 | #5(可複用嘅預測性偏態分數) |
| Hou-Robinson (2006) | 靜態高集中度 → 較低回報(同 5.1 方向相反) | 提醒 #2/#4 唔可以只睇水平 |

---

## 9. 同 repo / model plan 已知結論嘅對照

1. **內部文獻張力(已 resolve)**:Hou-Robinson (2006) 發現靜態高產業集中度對應**較低**平均回報
   (風險降低嘅代理),Grullon-Larkin-Michaely (2019) 發現集中度**上升**對應**較高**股東回報。
   兩者唔矛盾——分別講緊「水平」同「變化」。已喺 feature #2/#4 設計入面 resolve:用**集中度
   趨勢(HHI 上升 = 整合中產業)**做正向訊號,唔用靜態集中度水平,並用 Hou-Robinson 做提醒
   唔好單憑「呢個產業本來就集中」就當定價權訊號。

2. **Titman-Wei-Xie / Cooper-Gulen-Schill 嘅具體 magnitude 唔可靠**(多個 secondary source 數字
   打架),故意冇喺 scorecard 建議入面引用具體 bps/百分比權重——同 repo 一貫紀律一致
   (`backtest-testing-standard` memory:「下負面結論前對文獻」,同 07-05 風控報告對「真但細」
   效應嘅審慎態度相符),應該將呢兩篇當**方向性/定性閘門**(capex 加速 = 警戒旗)嚟用,唔好
   硬編碼成量化權重。

3. **Novy-Marx OL 溢價本身係「真但細」**(Sharpe 0.40-0.50,同 HML 相若,唔係 outsized alpha)——
   同 repo 07-05 風控報告嘅既有結論(「capital-efficiency 係真但細嘅 T1 擇時 alpha」)呼應
   一致,唔衝突。呼應 model plan 嘅乘數公式設計(「10x = 營運槓桿 × 需求超級週期 × 供給受限
   × 情緒 re-rating」)——OL 應該做**乘數**,唔係獨立買入訊號,呢個做法同文獻嘅實證強度相符
   (OL 單獨解釋力有限,但同其他因子交互後喺低彈性產業可以放大到 72bp/月)。

4. **Bessembinder 嘅「~55-60% 個股一世跑輸國庫券」隱含一個風險**:case 庫(model plan 步驟 A,
   平行進行中)必須夠大先可以定 base rate,否則 magnifier 模型會過度擬合單一 MU anecdote。
   呢個唔係文獻同 repo 衝突,而係對步驟 A/D(逆向工程 case study)嘅一個明確要求——單一案例
   唔足以驗證模型,一定要多案例交叉驗證(呼應 repo 一貫嘅「多案例、避 survivorship」紀律)。

5. 冇搵到同 repo 現有 insider/credit/regime 結論直接衝突嘅文獻(呢兩組屬唔同領域,literature
   review 冇觸及)。

**未解/風險**:第 4 主題(週期股估值倒轉)冇專門期刊論文,只有 Montier/GMO 實務界 heuristic +
相鄰嘅獲利能力均值回歸文獻(Fama-French 2000, Campbell-Shiller 1988)做方法論支撐——如果日後
要對呢條 feature 做嚴謹統計驗證,呢個係地基較薄弱嘅一環,應該喺 case 庫(步驟 A)入面特別
驗證呢個「trough 高 PE 買 / peak 低 PE 賣」邏輯本身(唔淨係假設佢岩)。

---

## 10. 想睇原文?How-to

- **有 DOI 嘅**:去 `https://doi.org/<DOI>`,會轉去出版社頁面;大部份期刊(JFE、JF、RFS、
  Review of Finance、QJE、JFQA)paywall,需要機構訂閱先睇到全文,冇訂閱通常都可以睇摘要。
- **有 SSRN 連結嘅**(`papers.ssrn.com/sol3/papers.cfm?abstract_id=...`):大部份作者上載嘅係
  working paper 版本,**免費全文 PDF**,同期刊定稿內容通常一致(數字偶有修訂,如
  De Loecker-Eeckhout-Unger 2017 NBER 稿 vs 2020 QJE 定稿有出入,本文已標注)。
- **有 NBER WP 編號嘅**(`nber.org/papers/w<編號>`):NBER working paper **一律免費全文 PDF**。
- **搵唔到免費版嘅**:試下作者自己嘅學院/faculty 個人頁(通常會掛自己論文嘅免費版,例如
  Novy-Marx、Bessembinder 都有自己嘅學術頁面),或者搜尋 Google Scholar 睇有冇 cached PDF
  連結。
- 全部 21 篇論文嘅 DOI/SSRN/NBER 連結已喺 §1–§7 逐篇列出,可以直接複製去瀏覽器。
