# 美股公開因子集調研:WorldQuant 101 Alphas、Open Source Asset Pricing、JKP

- 票號:KARST-074
- 日期:2026-08-29
- 用途:回應用戶 2026-08-29 提問(原話「whether anyone made the quant factor set which is good for US Stock? if not Qlib?」),核實主 agent 當時口頭提及的三套公開因子集,供後續建置票排序參考。

---

## 摘要(五句起)

1. **WorldQuant 101 Alphas 不是「純 OHLCV」因子集**——101 條裡有 26 條要行業分類做中性化、逾 12 條要用到成交量加權平均價(VWAP),兩者都是 Alpha158 不需要的額外數據;論文報的持有期短(平均 0.6–6.4 天),比 Alpha158 官方標籤設計的次日窗口更短。
2. **GitHub 上有現成 pandas 實作,但沒有一個「星數高、授權清楚、近年仍在維護」三樣齊全**——最多星的那個(862 星)沒有授權聲明、五年多沒更新;授權清楚(MIT)的兩個裡,一個近年仍有動態但星數只得 3,另一個 188 星但同樣五年多沒更新。跟 Alpha158 上次調研的結論一樣:表達式本身是公開發表的公式,可以照抄,不必依賴任何一個現成套件。
3. **算力量級比 Alpha158 更輕**:101 條 × 625 隻(標普 500)× 約 2,900 個交易日 ≈ 1.8 億格,比 Alpha158 的 158 條少約三分之一,參考 KARST-062/066 已跑出來的 Alpha158 實測基準(158 條在同一規模約 25 分鐘、幾百 MB parquet),101 Alphas 落地應在同一量級或更輕,現有 D-032(按快照 × 因子版本存 parquet)的落地方式直接沿用,不用改架構。
4. **Open Source Asset Pricing 資料本身用 MIT 授權、免費下載,是月度而非日度頻率的美股訊號**;JKP 全球因子庫資料用 CC BY-NC 4.0(非商業限定),分析程式碼是 MIT——兩者都覆蓋美股、都可以當「別人已經算好的訊號」拿來對照基準,但兩者都不是逐日更新的高頻價量因子,跟 Alpha158/101 Alphas 這類日線技術因子性質不同,適合當「基本面/長線因子」的對照庫,不適合取代日線量價因子。
5. **實測前要交代的量級**:已查到的唯一「美股實測」數字不是 101 Alphas 本身,而是同類日線量價因子(Alpha158/360)在標普 500 上的實測——Karst 自己 2026-08-29 的實測(KARST-066)顯示 158 條裡沒有一條 |IC 均值| 達 0.02;沒有查到 101 Alphas 本身在美股大盤股上的公開 IC 數字,只能用同類因子的量級做心理準備,不能假裝有直接出處。

**建議路徑一句可裁**:101 Alphas 目前優先順序低於已經在跑的 Alpha158 建置線——先把 Alpha158 的建置票(標普 500 入庫、IC 面板)做完,101 Alphas 待有餘力時另開一組建置票,照抄公式自寫 pandas(不裝任何現成套件),VWAP 用近似公式代、indneutralize 需要的行業分類另開一張數據源調研票確認有沒有免費美股行業分類可用;OSAP/JKP 兩套都先當「對照基準庫」處理,不進 Karst 的因子生產線。

---

## 一、WorldQuant 101 Alphas(Kakushadze 2016, arXiv 1601.00991)逐條分類

出處:[arXiv 摘要頁](https://arxiv.org/abs/1601.00991)、[PDF 全文](https://arxiv.org/pdf/1601.00991)(已下載但本機缺 `pdftoppm`,無法逐頁渲染核對逐條公式,以下數字來自摘要原文與可信二手整理,凡未從原文摘要直接核對的一律標明)、[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2701346)。

### 1.1 依賴項分類

- **只需 OHLCV(開高低收量)**:多數公式屬此類,論文摘要形容整體為「price-volume」風格的公式集,但未查到論文原文逐條列出的精確條數統計,以下條數來自二手整理,**標示為未完全核實**:
  - **VWAP(成交量加權平均價)**:至少 12 條用到(出處:[coriva.eu.org 分類整理](https://coriva.eu.org/en/alpha101-overview/),文中稱「超過一打的公式使用 VWAP」,原話未逐條列出編號,未完全核實)。已知具體用到 VWAP 的編號包含 Alpha#47、#50、#57、#58、#59、#61、#62、#63(出處同上,同樣未逐一對照原文核實)。
  - **indneutralize(行業中性化)**:**26 條**用到(出處:同上 coriva.eu.org 整理,數字明確標出,但同樣未逐條對照原文核實;這是本節查到最具體的一個統計數字)。已知包含 Alpha#48、#58、#59、#63。
  - **市值(cap)**:至少 1 條(Alpha#56 一類)用到市值加權,查到的二手來源未給出精確條數統計,標示為**未核實**。
- **對 Karst 的意義**:26 條要 indneutralize 代表**逾四分之一**的公式需要「行業分類」這項 Karst 現有數據管線沒有的輸入——這是比 Alpha158(只缺 VWAP 一項,且可用近似公式代)更大的數據缺口,行業分類本身也要先有一個免費、覆蓋美股大盤股的來源(例如 GICS 或 SIC 代碼),本票未查證此來源,列入下面建置票拆法第 0 項。

### 1.2 論文報的持有期、相關性、Sharpe 量級

- **平均持有期**:約 **0.6–6.4 天**(出處:[arXiv 1601.00991 摘要原文](https://arxiv.org/abs/1601.00991)——「Their average holding period approximately ranges 0.6-6.4 days.」)。比 Alpha158 官方標籤設計的「次日」窗口更短,落在 Karst 已查證的「量價因子甜蜜區在極短端」範圍內(research/2026-08-29-factor-horizon-evidence.md 結語),方向一致。
- **平均兩兩相關性**:**15.9%**(出處:同上摘要原文——「The average pair-wise correlation of these alphas is low, 15.9%.」),論文以此論證 101 條組合起來有分散風險的價值。
- **報酬與波動度、換手率的關係**:論文摘要指出「returns are strongly correlated with volatility, but have no significant dependence on turnover」(出處同上)。
- **Sharpe 比率量級**:論文正文附表報了逐條 alpha 的年化 Sharpe 比率、日換手率、持有期、每股報酬(cents-per-share)等指標(出處:[hedgefundalpha.com 摘要整理](https://hedgefundalpha.com/strategies/101-formulaic-alphas/)提及論文有此表格,但該頁本身抓取失敗,無法取得表格逐行數字),**本票未能取得逐條 Sharpe 的具體數值,標示為未核實**——這是論文正文表格內容,需要人手打開 PDF 逐頁核對才能補齊,不在本次調研工具能力範圍內。

---

## 二、GitHub 上不依賴 qlib/自建的 pandas 實作

搜尋詞:「alpha101 pandas」「worldquant 101 alphas python」「101 formulaic alphas implementation」。

| 專案 | 星數 | 授權 | 最後動態 | 備註 / 可否直接借用 |
|---|---|---|---|---|
| [yli188/WorldQuant_alpha101_code](https://github.com/yli188/WorldQuant_alpha101_code) | 862 | **無授權聲明**(GitHub API 回報 `license: null`) | 2019-03-07(**逾五年半沒更新**) | 星數最高、公式抄自原始 Quantigic 版本口碑較好,但無授權文字、逾五年無人維護,開 4 個 issue 未見官方回覆;**公式可參考核對,程式碼不建議直接照搬**(無授權 = 法律上不能確定可否重用) |
| [lvlh2/alpha101](https://github.com/lvlh2/alpha101)(可透過 PyPI `pip install alpha101` 安裝) | 3 | **MIT** | 2026-08-04(**近期仍在維護**) | 輸入介面要求 `market_value`、`industry`、`vwap` 三個額外欄位一律必填(即使某條 alpha 用不到也要餵),星數低、口碑未經驗證,但授權清楚、活躍度是三者中最新的 |
| [STHSF/alpha101](https://github.com/STHSF/alpha101) | 188 | **MIT** | 2019-06-24(逾五年無更新) | 授權清楚、星數居中,但同樣五年沒更新 |

**結論(依「業務先行、不預設自建」原則覆核)**:跟 Alpha158 上次調研(research/2026-08-29-alpha158-feasibility.md 第二節)同一個結論——**沒有一個「開箱即用、授權清楚、近年仍活躍」三樣齊全的套件**。101 條公式本身是論文公開發表的文字定義,照抄公式自己寫 pandas 仍然是最務實的路;上面三個 repo 的價值在於**核對用**(自己寫完後拿它們的輸出對照抽查,尤其是 862 星那個口碑較好但無授權,只適合拿來核對數值,不適合照搬程式碼),不是直接依賴的基礎套件。

---

## 三、算力估計

**規模**:101 條 × 625 實體(標普 500)× 約 2,900 個交易日 ≈ **1.83 億格**,比 Alpha158 的 158 條(2.37 億格,見 research/2026-08-29-alpha158-feasibility.md 第三節)少約 23%。

**已有的實測錨點**:KARST-062/066 已經在同一個標普 500 快照上實測跑完 158 條 Alpha158,入庫約 4–5 分鐘、IC 計算約 25 分鐘(experiments/2026-08-29-factor-ic/README.md)。101 Alphas 若按同一種「分批寫入、`groupby().rolling()` 向量化」的寫法做,量級應落在 Alpha158 實測時間的七至八成左右,估計**入庫幾分鐘、IC 計算約十幾到二十分鐘**——這是類比估計,不是實測,實際數字要等建置票跑一次基準才能定案。

**儲存**:沿用 D-032 的做法——因子值不進定義庫逐行存,改按「數據快照 × 因子版本」一批一個 parquet 檔,101 條的檔案體積預期比 Alpha158(實測落地約 300–700MB 量級,按第一節比例縮放)略小,同一套機制直接沿用,不用另外設計。

---

## 四、Open Source Asset Pricing 與 JKP 因子庫

### 4.1 Open Source Asset Pricing(OSAP)

出處:[openassetpricing.com](https://www.openassetpricing.com/)、[openassetpricing.com/data](https://www.openassetpricing.com/data/)、[PyPI openassetpricing](https://pypi.org/project/openassetpricing/)、[CRAN OpenSourceAP.DownloadR](https://cran.r-project.org/web/packages/OpenSourceAP.DownloadR/index.html)、[GitHub mk0417/open-asset-pricing-download](https://github.com/mk0417/open-asset-pricing-download)。

- **授權**:官方 R 下載套件用 MIT 授權;本票未查到網站本身對「數據」的授權條款有獨立聲明,以套件授權為準,判斷為**可自由使用**,但**未完全核實**——建議實際引用前到網站頁腳/使用條款頁再確認一次。
- **下載方式**:三種——直接到網站 Data 頁面下載、`pip install openassetpricing`(Python 套件)、或 R 套件 `OpenSourceAP.DownloadR`。
- **美股覆蓋**:提供逾 200 個橫斷面預測訊號(209 個 OSAP 自算的特徵 + 3 個要 WRDS 訂閱才能拿到的 CRSP 變數:Price、Size、STreversal),覆蓋範圍是**美股**(這套資料庫的定位就是複現美股資產定價文獻),具體起訖年份與股票數本票未查到明確數字,**未核實**。
- **頻率**:**月度**橫斷面特徵與月度投資組合報酬——這是與 Alpha158/101 Alphas 這類日線因子最大的差異,不是同一種頻率的訊號。
- **只需價量的訊號有幾多**:網頁本身沒有把 209 個特徵按「只需價量 vs 要財務報表」分類,本票未逐一核對 209 條清單,**未核實**;可以合理推斷其中包含動量、短期反轉(STreversal)、規模(Size)等少數只需價量的經典訊號,但多數特徵(帳面市值比、應計項目、投資成長率一類)明顯要用到財務報表數據,不是「只需 OHLCV」的集合。
- **對 Karst 的用法**:適合當**對照基準**(拿 Karst 自己算出來的月度因子表現,對照 OSAP 已發表的同名因子表現做健全性檢查),不建議直接進 Karst 的因子生產線——頻率不合、且多數特徵需要財務報表,超出「業務先行、量價優先」的現階段範圍。

### 4.2 JKP(Jensen, Kelly & Pedersen)全球因子庫

出處:[jkpfactors.com](https://jkpfactors.com/)、[GitHub bkelly-lab/jkp-data](https://github.com/bkelly-lab/jkp-data)、[GitHub bkelly-lab/ReplicationCrisis](https://github.com/bkelly-lab/ReplicationCrisis)。

- **授權**:**數據本身 CC BY-NC 4.0(僅限非商業使用)**,分析程式碼另外用 MIT 授權——這一點跟 OSAP 不同,**JKP 的數據不能商用**,Karst 若日後有任何商業化路徑要留意這條限制。
- **下載方式**:網站下拉選單直接下載已算好的多空因子組合;若要股票層級的原始特徵/報酬,要接 WRDS 訂閱的 Global Factor Data,或用 GitHub 上的 Python 程式碼自己重算。
- **美股覆蓋**:全球 93 個國家,美股包含在內,可從下拉選單或程式碼裡按國家/地區篩選取用美股子集(本票未實際跑一次篩選流程核對操作細節,**未完全核實**)。
- **只需價量的訊號有幾多**:153 個特徵分 13 個主題群,同樣沒有查到官方按「只需價量」分類的統計數字,**未核實**;結構與 OSAP 類似,可推斷同樣是財務報表特徵佔多數。
- **頻率**:同樣以**月度**為主。
- **對 Karst 的用法**:跟 OSAP 一樣定位為對照基準庫,而且因為非商業授權的限制,若 Karst 有任何未來商業化考慮,OSAP(MIT)比 JKP(CC BY-NC)更安全。

---

## 五、結語:建議路徑與建置票拆法

**建議路徑(一句可裁)**:101 Alphas 排在 Alpha158 建置線之後——先完成 Alpha158 既有建置票(標普 500 入庫、IC 面板),101 Alphas 待有餘力再開新一組建置票,照抄公式自寫 pandas(不裝任何現成 GitHub 套件,只拿它們的輸出核對數值),VWAP 缺口用近似公式代,indneutralize 需要的行業分類另開數據源調研票確認有沒有免費美股來源;OSAP 與 JKP 兩套都先當「月度對照基準庫」處理,不進日線因子生產線,JKP 因非商業授權要另外標注使用限制。

**建置票拆法(每張一程,101 Alphas 這條線)**:

0. **行業分類數據源調研票**(先於下面各票)——確認美股大盤股有沒有免費、覆蓋 12 年以上的行業/子行業分類來源(GICS 或 SIC),沒有的話 26 條 indneutralize 公式要留白或改用替代分組(例如按市值分位數代替行業分組),這一步不確認,101 Alphas 實作票無法完整開工。
1. **101 Alphas pandas 實作票**——照抄公式清單、對照上面第二節三個現成 repo 的輸出抽查核對數值,VWAP 用近似公式,不含入庫。
2. **因子入庫與版本登記票**——比照 Alpha158 建置票(KARST-064)同一套流程,101 條各自登記 `factor`/`factor_version`,按 D-021/D-032 補齊必填欄位、寫入 parquet。
3. **101 Alphas × 標普 500 IC 實測票**——比照 KARST-066 同一套跑法,補上「本票第五節」缺的那個實測數字。

**實測前要向用戶交代的預期量級一句**:**沒有查到 101 Alphas 本身在美股大盤股上的公開 IC 數字**(只查到論文本身的持有期、相關性統計,沒有查到獨立第三方在美股上覆現 101 Alphas 的 IC 報告);可比照的唯一參考是同類日線量價因子(Alpha158)在標普 500 上的 Karst 自家實測——158 條裡沒有一條 |IC 均值| 達到 0.02(KARST-066 結論)——**101 Alphas 屬同一大類(日線量價技術因子),沒有理由預期會顯著優於這個量級,實測前應設定「多數條目訊號薄弱、少數波幅/極值類條目較好」這個心理預期**,但這是類比推論,不是 101 Alphas 本身的實測或文獻數字,標示清楚以免誤導。

---

## 未完全核實事項清單

- 101 Alphas 逐條依賴分類(VWAP 12+ 條、indneutralize 26 條、cap 條數)來自二手整理網站(coriva.eu.org),未逐條對照 arXiv 原文核實;原文 PDF 已下載但本機缺 `pdftoppm` 無法渲染逐頁核對。
- 論文正文表格裡逐條 Sharpe 比率、換手率、每股報酬的具體數值未取得,只查到摘要層級的持有期(0.6–6.4 天)與相關性(15.9%)兩個數字。
- OSAP 數據本身(非下載套件)的授權條款未在官網獨立確認,以套件 MIT 授權推斷。
- OSAP 209 個特徵、JKP 153 個特徵裡「只需價量」的精確條數,兩者官網都沒有現成統計,本票未逐條分類核對。
- JKP 美股子集的實際篩選操作流程未實跑核對。
- 101 Alphas 在美股大盤股上沒有查到任何公開 IC 實測數字(不論機構級或個人覆現),第五節的「預期量級」是類比 Alpha158 的推論,非直接出處。

## 出處總表

- [arXiv 1601.00991 摘要](https://arxiv.org/abs/1601.00991) / [PDF 全文](https://arxiv.org/pdf/1601.00991)
- [SSRN 2701346](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2701346)
- [coriva.eu.org — WorldQuant Alpha101 因子分類整理](https://coriva.eu.org/en/alpha101-overview/)
- [hedgefundalpha.com — 101 Formulaic Alphas 摘要](https://hedgefundalpha.com/strategies/101-formulaic-alphas/)
- [github.com/yli188/WorldQuant_alpha101_code](https://github.com/yli188/WorldQuant_alpha101_code)
- [github.com/lvlh2/alpha101](https://github.com/lvlh2/alpha101)(PyPI:[alpha101](https://pypi.org/project/alpha101/))
- [github.com/STHSF/alpha101](https://github.com/STHSF/alpha101)
- [github.com/Menooker/KunQuant](https://github.com/Menooker/KunQuant)(C++ 編譯層,方向不合,沿用 Alpha158 調研的判斷)
- [openassetpricing.com](https://www.openassetpricing.com/)、[openassetpricing.com/data](https://www.openassetpricing.com/data/)
- [PyPI openassetpricing](https://pypi.org/project/openassetpricing/)
- [CRAN OpenSourceAP.DownloadR](https://cran.r-project.org/web/packages/OpenSourceAP.DownloadR/index.html)
- [github.com/mk0417/open-asset-pricing-download](https://github.com/mk0417/open-asset-pricing-download)
- [jkpfactors.com](https://jkpfactors.com/)
- [github.com/bkelly-lab/jkp-data](https://github.com/bkelly-lab/jkp-data)
- [github.com/bkelly-lab/ReplicationCrisis](https://github.com/bkelly-lab/ReplicationCrisis)(Jensen, Kelly & Pedersen (2023),*Is There a Replication Crisis in Finance?*,Journal of Finance)
- 本倉背景:`research/2026-08-29-alpha158-feasibility.md`、`research/2026-08-29-factor-horizon-evidence.md`、`experiments/2026-08-29-factor-ic/README.md`、`karst/factors/alpha158.py`、`.kira/decisions.md` D-021/D-032
