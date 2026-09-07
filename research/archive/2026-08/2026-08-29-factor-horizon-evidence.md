# 量價因子對持有期的預測力——文獻與公開基準出處

- 票號:KARST-069
- 日期:2026-08-29
- 用途:回應用戶 2026-08-29 提出「這套因子對日、周、月哪個交易窗口有用?有沒有相關研究?」把主 agent 當時口頭答覆的出處落檔,供之後開預測力面板票時引用。

---

## 摘要(先講結論)

量價類因子(Alpha158 這一類)對持有期的預測力不是均勻分布的——它在極短窗口(1 個交易日上下)最強,中段(1 個月上下)反而最弱,到中期(3–12 個月)換一批因子(動量)才重新變強。公開資料顯示,同一套因子在 A 股測到的訊號強度,比在美股大型股測到的強一截(差幾倍到十倍量級)。以下四節逐一列出處。

---

## 一、qlib Alpha158 原設計的標籤、持有期與公開基準 IC 量級

**標籤與持有期**:Alpha158 官方預設標籤是 `Ref($close,-2)/Ref($close,-1)-1`,即隔一日收市到再隔一日收市的回報——換算下來是**下一個交易日的報酬**,對應「日度」持有期。這一點 research/2026-08-29-alpha158-feasibility.md 第一節已記,本票不重複查證。

**公開基準 IC 量級(A 股)**:qlib 官方基準表(`examples/benchmarks/README.md`)在 **CSI300**(滬深 300,A 股大盤股指數)上,用 Alpha158 做輸入、預測次日報酬,常見模型的樣本外 IC(資訊係數,衡量因子分數與其後回報的相關度)落在 **0.04–0.05** 這個量級,Rank IC(用名次算的版本)相近或略高:DoubleEnsemble IC 0.0521、XGBoost IC 0.0498、CatBoost IC 0.0481、TRA IC 0.0440,對應 Rank IC 約 0.045–0.054。換成 Alpha360(不經人手設計、直接餵原始價量序列)最高見到 HIST 模型 IC 0.0522、Rank IC 0.0667。測試期為 2017 年 1 月至 2020 年 8 月,20 次不同隨機種子取平均。
出處:[qlib benchmarks README](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md)

**這是次日(T+1)這一個時間點的訊號,不是「周度」或「月度」的直接量測**——qlib 官方基準只驗了這一個持有期,沒有官方的周度/月度版本可引。這是本節查證的邊界,下面第三節會用非官方來源補一個對照。

---

## 二、學術文獻:短期反轉、動量、成交量、波幅四類因子的持有期證據

### 2.1 短期反轉(持有期:1 週至 1 個月,個股層級)

- **Jegadeesh (1990)**,*Evidence of Predictable Behavior of Security Returns*,Journal of Finance 45(3): 881–898。用 1934–1987 年月度回報,發現買上月輸家、賣上月贏家的等權組合,平均月回報約 2%——**一個月的滯後上出現顯著負向序列相關(反轉)**。
  出處:[Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1990.tb05110.x)
- **Lehmann (1990)**,*Fads, Martingales, and Market Efficiency*,Quarterly Journal of Economics 105: 1–28。用**周度**回報,發現本周贏家在下一周有系統性反轉,扣除薄交易與買賣價差的量測誤差、以及合理交易成本後,這個套利利潤仍然存在。**比 Jegadeesh 更短——這是周度窗口的直接證據**。
  出處:[QJE(摘要)](https://academic.oup.com/qje/article-abstract/105/1/1/1928416)、[全文 PDF](http://finance.martinsewell.com/stylized-facts/dependence/Lehmann1990.pdf)

### 2.2 動量(持有期:3–12 個月,不是量價因子這一類的短窗口)

- **Jegadeesh & Titman (1993)**,*Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency*,Journal of Finance 48(1): 65–91。按過去 1–4 季報酬排名,買贏家、賣輸家,**持有期 3–12 個月**能得到顯著正報酬(月化約 1.5%)。第一年後部分異常報酬在其後兩年內消退。
  出處:[Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1993.tb04702.x)、[全文 PDF](https://www.bauer.uh.edu/rsusmel/phd/jegadeesh-titman93.pdf)
  **這一條確認:動量因子的有效窗口跟 Alpha158 這類日線量價因子的窗口不重疊**——動量要 3 個月以上才顯現,1 天到 1 個月這段窗口動量本身不管用(甚至跟反轉打對台)。

### 2.3 成交量類因子(持有期:1 個月)

- **Gervais, Kaniel & Mingelgrin (2001)**,*The High-Volume Return Premium*,Journal of Finance 56: 877–919。單日或單周出現異常高(低)成交量的股票,**在其後一個月**傾向上升(下跌)——這是「量價因子」裡少數官方標明**月度**窗口生效的證據。機制解釋:成交量衝擊改變股票能見度,進而改變後續需求與價格。
  出處:[Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00349)、[Duke 頁面(含連結)](https://sites.duke.edu/sgervais/research/gervais-kaniel-mingelgrin-2001/)

### 2.4 波幅類因子(持有期:月度橫斷面,非短線交易訊號)

- **Ang, Hodrick, Xing & Zhang (2006)**,*The Cross-Section of Volatility and Expected Returns*,Journal of Finance 61(1): 259–299。用**月度**橫斷面迴歸,發現特異波幅(相對 Fama-French 三因子模型的殘差波幅)高的股票,其後平均報酬反常地低。這條方向跟直覺相反(高風險理應高報酬),文獻稱為「波幅異常」。
  出處:[NBER 工作論文](https://www.nber.org/papers/w10852)、[全文 PDF](https://business.columbia.edu/sites/default/files-efs/pubfiles/3361/ang_high_idiosyncratic_volatility.pdf)
  這條是**橫斷面選股訊號**,不是「持有幾日賺幾多」的交易訊號——引用時要留意跟前面三條的性質不同。

### 2.5 美股 vs A 股的技術因子預測力差異

沒有查到一篇專門「逐一比較同一套技術因子在美股與 A 股的 IC」的論文,但有兩條間接但方向一致的證據:

1. **Liu, Stambaugh & Yuan (2019)**,*Size and Value in China*,Journal of Financial Economics 134(1): 48–69。A 股市場結構(殼股、IPO 管制)令傳統 Fama-French 因子模型在中國留下 17% 年化的異常 alpha 解釋不了,要另建一套中國專屬的三因子模型。**這條說明 A 股跟美股不是同一套風險溢價結構,不能假設美股驗出來的量價因子強度可以照搬。**
   出處:[ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0304405X19300625)、[NBER](https://www.nber.org/papers/w24458)
2. 多篇近年研究(如新進投資者與日內動量、周轉率與動量的關係)一致指出:**A 股散戶佔比高、換手率極高(新進散戶單日換手率達 18%),令市場短線行為偏強、中期動量反而缺席**——A 股呈現「日內動量、周內反轉」的模式,跟美股「中期動量、短期反轉」的經典模式不同。這批研究屬機構工作論文/會議論文,尚未逐一核實是否已正式發表,標示為**未完全核實**。
   出處(未核實發表狀態):[Daily Momentum and New Investors in Emerging Stock Markets](https://wxiong.mycpanel.princeton.edu/papers/DailyMomentum.pdf)

---

## 三、美股上實際跑過 Alpha158/Alpha360 的公開結果

沒有查到同行評審論文或機構級公開報告在美股上跑 Alpha158/360 並公布 IC。查到的唯一具體數字來自一個個人技術部落格(Vadim's blog),**可信度定性為「業餘覆現、非機構級,僅供量級參考」**:

- 用 qlib 官方框架,`instruments: sp500`(標普 500),Alpha360 特徵,2008–2014 訓練、2015–2016 驗證、2017–2020 測試(跟官方 A 股基準同一個測試窗口方便對照),**PyTorch MLP 模型測出 IC ≈ 0.0045、Rank IC ≈ 0.0048**,年化報酬 −6.7%(扣交易成本後倒蝕)。作者自己形容這是「很低的預測相關度」,懷疑要更進階的模型或特徵才夠用。
  出處:[Vadim's blog - PyTorch MLP on Alpha360](https://vadim.blog/qlib-ai-quant-workflow-pytorch-mlp/)
- 同一作者用 LightGBM(不確定是否為 Alpha158 特徵集,文中沒有明確標名)測出 **IC ≈ 0.0045、Rank IC ≈ 0.0048**,同樣定性為「正但微弱」。
  出處:[Vadim's blog - LightGBM workflow](https://vadim.blog/qlib-ai-quant-workflow-lightgbm/)

**對照量級**:上面兩個美股大型股(標普 500)的 IC 落在 0.004–0.005,對比第一節 A 股(CSI300)官方基準 IC 落在 0.04–0.05——**差了一個數量級**。雖然這只是一個非機構級的業餘覆現,樣本量薄弱、不能當定論,但方向跟第二節第 5 點(A 股市場結構不同、技術因子在 A 股更強)是一致的,可以互相佐證,不算孤證。

---

## 四、結語:對 Karst 的意思

**持有期分佈不是均勻的,量價因子的「甜蜜區」在極短端**:第二節四類因子疊起來看,1 個交易日(次日)是 qlib 官方標籤驗證過的窗口(第一節),1 週是反轉最強的窗口(Lehmann 1990),1 個月是反轉開始減弱、成交量異常訊號生效的窗口(Jegadeesh 1990、Gervais et al. 2001),而動量因子要等 3–12 個月才顯現、跟 Alpha158 這類量價因子完全是兩個不同的時間尺度。

**美股大型股上,同一套量價因子的訊號比 A 股弱一截**——第三節的業餘覆現數字(IC 0.004–0.005)雖然不能當機構級定論,但方向跟「A 股市場結構不同、技術異常更強」(第二節第 5 點)一致。這對 Karst 的意思是:**不要假設 Alpha158 在美股上會有 qlib README 那種 IC 0.04–0.05 的表現,實測前要有心理準備看到弱得多的訊號,甚至要合併多因子或縮窄到有基本面篩選的子集才有機會浮出訊號**——這一點主 agent 之前口頭答覆已經講中,現在有出處撐住。

**預測力面板首輪應看的三個持有期窗口:建議 1、5、21 個交易日**,查證下來合理:
- **1 個交易日**:對應 qlib 官方標籤與基準的原設計窗口(第一節),是最直接可跟公開基準對照的一格。
- **5 個交易日(約 1 週)**:對應 Lehmann (1990) 驗證的周度反轉窗口——現有文獻裡最乾淨的一個「非日度」對照點。
- **21 個交易日(約 1 個月)**:對應 Jegadeesh (1990) 的月度反轉、Gervais et al. (2001) 的月度成交量溢價、以及 Ang et al. (2006) 的月度波幅異常——三條月度證據疊在同一個窗口,是量價因子「反轉力度開始減弱、但另一批因子(量、波幅)接手」的轉折點,值得單獨看一格。

三個窗口再往上到 3–12 個月會踏入動量的地盤,但動量不屬於 Alpha158 這類日線量價因子的核心假設,建議留給日後另一批因子(基本面/風格)覆蓋,不併入本輪面板。

---

## 未完全核實事項清單

- 第二節第 5 點「A 股日內動量、周內反轉」一批工作論文的正式發表狀態未逐一核實。
- 第三節的美股 IC 數字來自個人部落格的一次性覆現,非機構級、樣本量未知,只能當量級參考,不可引作定論。
- Alpha158 158 條因子的精確條數(是否恰好 158)未在本票重新核實,沿用 research/2026-08-29-alpha158-feasibility.md 既有結論。
