# Result — Expectations Investing 注碼公式(margin of safety × 收斂速度)validation

**Date:** 2026-07-11
**Script:** `backtest/experiments/exp_sizing_formula_validation.py`(可重現;原始 case 表存
`backtest/results/_sizing_formula_validation_cases.csv`)
**對應:** `docs/2026-07-11_magnifier_book_expectations_investing.md` §2.3(Table 7.7)、
Phase-3 WS5(`thesis/sizing.py`、`docs/2026-07-08_phase3_ws5_expression.md`)
**本檔非最終模型改動** —— 純 validation,WS5 `sizing.py` 未改一行 code。

---

## 0. 一句結論

Mauboussin & Rappaport 嗰條「折讓越大 + 收斂越快 = 注碼越大」嘅**方向**,喺 Karst 自己嘅
9 個歷史 supercycle 案例庫入面**有微弱、方向一致但統計上唔夠力嘅支持**——折讓(margin of
safety)呢一半喺 ticker 層面(n=20-21)顯著,但**收斂速度呢一半單獨睇完全唔顯著**(甚至符號
反晒),要控制咗折讓大小嘅混淆(deeper discount 機械上要更耐先追返 200 日均線)先至見到收斂
速度有預期方向嘅邊際貢獻。更重要:一旦誠實咁將 20 隻 ticker 摺返做**~11 個獨立宏觀週期**
(同一週期入面嘅股票唔係獨立樣本),兩條腿嘅相關性都跌到唔顯著(p=0.08-0.69)。**證據不足以
斷定呢條公式喺量化意義上成立**——方向大致啱、細樣本入面冇反證,但唔夠力做「已驗證」嘅結論。
獨立文獻(非 Mauboussin 本人)方面:Kelly criterion 冇獨立支持「收斂速度」呢一項輸入;
Capozza & Israelsen (2010) 證實 mispricing 收斂速度係一個真實、可測量嘅現象(每年抹走
15-30% 錯價),但只係 ex-post 平均速率,唔係話個別倉位嘅 ex-ante 收斂預測可靠;Shleifer &
Vishny (1997) *Limits of Arbitrage* 明確警告「假設收斂快而重注」呢個做法本身有風險——同用戶
喺任務入面已經預警嘅方向一致。

---

## 1. 方法

### 1.1 Case 選取

由 `backtest/results/2026-07-09_magnifier_case_library.md` 揀 28 個有明確「起漲期」(trough)
日期同價位嘅 ticker/週期組合(涵蓋週期 2/3/6/7/7a,即中國商品、油/頁岩、鈾、EV/鋰、GLP-1、
AI-compute/記憶體、稀土、SMCI 會計醜聞後低點)。**4 個因 ticker 已下市/被收購,yfinance 冇歷史
數據,剔除**:X(2025 年被日本製鐵收購)、MEE(Massey Energy,2011 年被 Alpha Natural
Resources 收購)、PXD(2024 年被 ExxonMobil 收購)、LTHM(2024 併入 Arcadium Lithium,2025
再被 Rio Tinto 收購)——四個都同案例庫本身記錄嘅「體面退場」結局一致,唔係數據錯誤,係
survivorship 限制嘅直接後果(同案例庫 caveat 一致)。**3 個因 trough 前歷史 <180 個交易日
(近期 IPO/uplisting,例如 NXE 2014、URG 2008 起漲時上市未夠 1 年)冇辦法計 margin-of-safety
proxy**,喺相關性檢定入面剔除,但 raw table 保留其 converge/forward-return 數字做參考。
**最終 margin-of-safety 檢定樣本:21 個 ticker-trough 觀察值,涵蓋 ~11 個獨立宏觀週期。**

### 1.2 兩條 proxy(均為簡化代理,非完整 DCF)

- **Margin of safety proxy** = (trough 前 5 年trailing 高位 − trough 價) / trough 前 5 年
  trailing 高位。**呢個唔係書入面嘅 DCF-implied expected value 折讓**,係用戶任務要求嘅簡化
  代理——「距前一個 peak 嘅跌幅」。對「多年陰跌到低位」型 case(例如 FCX 2003:「2001-02
  銅價多年低位」)呢個 proxy 會低估真實 undervaluation(因為 trailing peak 本身已經跌咗好耐),
  對「急跌型」case(太陽能組、SLI、UEC/UUUU)會捕捉到更清晰嘅折讓。
- **收斂速度 proxy** = trough 後,股價**連續脫離 200 日均線**(收市價高於 200sma,並喺其後
  40 個交易日入面 ≥90% 嘅日子維持喺 200sma 之上,避免單日 whipsaw 誤判)所需嘅交易日數。
  3 年內未出現呢個訊號 = 標記「未收斂」,相關性檢定用 756 交易日(≈3年)做 censoring 值。
  **重要:呢個 proxy 係 ex-post/realized(我哋知道實際發生咗幾耐先反彈),唔係 WS5 喺 trough
  當下可以觀察到嘅嘢**——書入面嘅「收斂速度」本身係一個**市場預期**輸入(你估市場幾快 revise
  期望),唔係一個可以喺事後先計嘅已實現數字。呢個 proxy 只能回答「歷史上,實際收斂快慢
  同其後回報有冇關係」,答唔到「WS5 可唔可以喺 trough 果一刻可靠咁預測收斂速度」——呢個係
  委派任務第 4 點提醒嘅 look-ahead 限制,本檔明確標注,唔當呢個 proxy 係一個可操作嘅事前訊號。
- **Forward return** = trough 後 1 年/2 年(日曆日,對齊最近嘅交易日)嘅 adjusted-close total
  return。

---

## 2. 結果表(21 個 margin-of-safety 可用觀察值,按折讓幅度排序)

| ticker | trough | margin_of_safety% | converge(交易日) | fwd_1y% | fwd_2y% |
|---|---|---:|---:|---:|---:|
| NVO | 2021-03-01 | 3.9 | 19 | 45.1 | 103.0 |
| LLY | 2020-10-01 | 14.3 | 45 | 61.8 | 129.9 |
| FCX | 2003-03-03 | 19.9 | 0* | 153.9 | 158.0 |
| ALB | 2020-03-02 | 39.5 | 56 | 85.4 | 132.4 |
| MU(2022) | 2022-12-01 | 42.7 | 73 | 37.9 | 79.8 |
| NUE | 2003-04-01 | 43.8 | 28 | 63.4 | 209.7 |
| CCJ(2002) | 2002-09-03 | 44.9 | 77 | 80.7 | 264.9 |
| LITE | 2023-10-02 | 58.1 | 52 | 34.6 | 275.2 |
| CCJ(2020) | 2020-03-23 | 61.4 | 11 | 171.7 | 371.7 |
| CLF | 2003-05-01 | 62.6 | 58 | 157.1 | 537.3 |
| WDC | 2022-12-01 | 63.3 | 115 | 35.0 | 104.9 |
| DNN | 2020-03-02 | 63.9 | 96 | 251.4 | 360.0 |
| COHR | 2023-10-02 | 67.5 | 43 | 174.7 | 254.6 |
| UROY | 2023-05-01 | 67.6 | 77 | 22.5 | **-3.2** |
| MU(2016) | 2016-03-01 | 69.7 | 92 | 121.8 | 330.2 |
| MP | 2024-03-01 | 73.4 | 142 | 45.6 | 312.0 |
| SLI | 2020-03-18 | 82.3 | 38 | 777.4 | 1878.0 |
| SMCI | 2024-11-14 | 84.8 | 122 | 102.2 | n/a(未夠 2y) |
| UEC | 2008-11-03 | 93.7 | 117 | 500.0 | 867.4 |
| UUUU | 2008-11-03 | 95.7 | 120 | 45.0 | 185.0 |
| LEU | 2018-12-03 | 97.9 | 36 | 112.5 | 508.2 |

\* FCX converge=0 係 proxy 限制:FCX 屬於「多年陰跌到低位」型(非急跌型),trough 當日 200sma
本身已經跌到貼近價位,「連續脫離 200sma」幾乎即時觸發,唔代表真正意義上嘅「即時 V 型反轉」。

**未納入相關性檢定(保留做質性參考)**:NXE(2014 起漲時 margin_of_safety N/A,但 converge=149日、
fwd_1y=7.1%、fwd_2y=85.4%——公司特定發現驅動,同板塊性折讓機制唔同)、URG(2008-11 呢個
trough margin_of_safety N/A,但呢個其實係 URG 嘅**強**週期,converge=129日、fwd_1y=72.9%、
fwd_2y=250%;案例庫提到嘅「URG 現輪較弱」講嘅係另一個 2023- 嘅 trough,本檔未獨立測試)。

**WOLF(SiC 功率半導體)—— 數據斷裂,獨立質性討論見 §4**:trough 定喺 2023-06(距 2021-11
峰值 $141.87 已跌 >70%,表面睇「折讓好大」),但 yfinance 而家嘅 WOLF ticker **只保留
2025-09-29 破產重組後嘅新股數據**——舊股東喺 Chapter 11(2025-06-30 申請)入面被
0.008352 比例換股,實質接近全損,舊股票歷史已經被數據源清空,script 自動偵測唔到「trough 前
歷史」而標記 N/A。呢個唔係 script bug,係一個**極有價值嘅負面案例**,見 §4。

---

## 3. 統計檢定(三個層次,由寬鬆到嚴謹)

### 3.1 Ticker 層面,單變量 Spearman(n=20-21)

| target | margin_of_safety | 收斂速度(neg converge_days) |
|---|---|---|
| fwd_return_1y | rho=0.26, p=0.26(不顯著) | rho=0.19, p=0.40(不顯著) |
| fwd_return_2y | **rho=0.56, p=0.0098(顯著)** | rho=-0.03, p=0.91(近乎零,符號同預期方向相反) |

單獨睇,折讓喺 2 年期顯著,1 年期唔顯著;**收斂速度單獨睇完全冇解釋力**,兩個期限都唔顯著,
2 年期仲同書嘅預期方向相反(慢收斂反而略為對應更高回報,雖然 rho 接近零、唔顯著)。

### 3.2 混淆檢查 + Partial correlation(控制咗折讓大小之後,收斂速度重新出現預期方向)

先做混淆檢查:margin_of_safety 同 converge_days 本身**顯著正相關**(rho=0.53, p=0.013,
n=21)——即折讓越大,機械上越耐先追返 200sma(距離遠、200sma 本身仲拖住舊高位未跌完),
呢個係一個真實嘅方法論混淆,單變量相關性會被呢個混淆遮蔽。

控制咗呢個混淆之後(partial correlation,rank-based):

| | fwd_return_1y | fwd_return_2y |
|---|---|---|
| margin_of_safety \| converge_days | r=0.44, **p=0.048** | r=0.63, **p=0.0029** |
| converge_days \| margin_of_safety | r=-0.41, p=0.068(邊緣) | r=-0.35, p=0.135(不顯著) |

控制咗折讓大小之後,收斂速度嘅偏相關**符號變返同書嘅預期一致**(收斂越快=converge_days
越細=同回報正相關,即 converge_days 本身應該係負相關)——但只喺 1 年期邊緣顯著(p=0.068),
2 年期仍未達顯著(p=0.135)。折讓呢一項喺兩個期限都轉強(1 年期由不顯著 p=0.26 變做邊緣顯著
p=0.048)。**呢個支持書嘅核心主張——兩項要合埋睇先有意義,單獨睇任何一項都唔夠**——但樣本
太細(n=20-21),呢個仍然係「方向一致」唔係「已證實」。

### 3.3 週期層面(誠實嘅有效樣本數:~11 個獨立宏觀週期,唔係 20 隻 ticker)

**呢個係全份分析入面最重要嘅一個誠實檢查。** 20-21 隻 ticker 入面,好多隻其實屬於同一個
宏觀週期(例如 2022-23 AI/記憶體週期入面 MU/WDC/LITE/COHR 四隻股價走勢高度相關,唔係四個
獨立樣本;2020 COVID 觸發嘅鋰/鈾/GLP-1 群組同一樣)。用戶喺任務入面已經預警「~9 個週期,
可能子集更少」——摺返做週期層面(用每個週期嘅中位數):

| | n(週期) | rho | p |
|---|---:|---:|---:|
| margin_of_safety vs fwd_2y | 11 | 0.55 | 0.083(不顯著) |
| margin_of_safety vs fwd_1y | 12 | 0.15 | 0.65(不顯著) |
| converge_days vs fwd_2y | 11 | 0.14 | 0.69(不顯著) |
| converge_days vs fwd_1y | 12 | -0.21 | 0.51(不顯著) |

**摺返做週期層面之後,冇一項達到常規顯著水平。** 折讓喺 2 年期仍然係正方向、幅度唔細
(rho=0.55),但 p=0.083、n=11,喺呢個樣本大細之下呢個結果同「純粹噪音」分唔太開。

### 3.4 書嘅 Table 7.7 公式字面套用(用 realized 收斂時間)—— 唔係一個公平嘅數值測試

用 `((1/(1-margin_of_safety)) ^ (1/converge_years)) - 1` 逐案例計「年化超額回報」,結果由
69% 到 5.5×10¹³% 唔等,**數字完全爆錶、無意義**。原因:本檔嘅收斂 proxy(連續脫離 200sma)
捕捉嘅係「市場停止插水、重新確立升軌」呢個**淺、快**嘅訊號(通常幾個星期到幾個月),唔係
書入面 Table 7.7 舉例嗰種「股價完全收斂到 DCF 隱含 expected value」嘅**深、慢**過程(書嘅例子
用 1-2 年做收斂期)。將呢個淺訊號嘅收斂時間(往往 <0.5 年)代入書嘅公式,分母 1/T 會變得極大,
令公式數學上爆炸。**呢個唔係書錯,係本檔嘅收斂 proxy 定義同書嘅「收斂到 expected value」定義
唔係同一件事**——本檔只可以誠實咁講「方向一致」,唔可以講「數值吻合 Table 7.7」。呢個亦係
點解 §3 嘅檢定全部用 rank-based Spearman/partial correlation(睇方向同單調關係),而唔係用
書嘅精確公式做逐案例回歸。

---

## 4. WOLF —— 一個關鍵嘅質性反例(公式冇 solvency gate)

WOLF(Wolfspeed,SiC 功率半導體)喺 2021-11 見頂 $141.87 後,喺 「SiC/EV 電力鏈供給樽頸」
敘事下持續回落。任何時間點(2023-2024)睇,較 2021 峰值嘅折讓都已經 >70-80%——用 margin of
safety proxy 嚟睇,呢隻股會顯示「極具吸引力嘅折讓」。但實際結局:**2025-06-30 申請
Chapter 11,舊股東按 0.008352 比例換新股(即 1,000 股舊股換 8.35 股新股),實質接近全損**;
`2026-07-09_magnifier_case_library.md` 已經將呢個 case 列為 ai-power-grid.md wiki 嘅
kill_condition 兌現案例。

呢個對 WS5 有直接含義:**margin-of-safety × 收斂速度呢條公式,本身完全冇處理「呢間公司會唔會
喺收斂發生之前先破產/股權清零」呢個風險**——書嘅框架假設你揀緊嘅係一間會生存到收斂發生嗰刻
嘅公司,唔係一間本身有償付能力風險嘅公司。折讓越大**唔一定**代表機會越大,亦可能代表「市場
已經開始定價緊償付能力風險」,兩者喺純折讓 % 呢個維度上完全睇唔出分別。案例庫本身已經有呢個
教訓(§3c 死亡 marker、太陽能組 FSLR vs 純商品同業),本檔嘅 WOLF case 再次獨立確認。

---

## 5. 獨立文獻檢查(非 Mauboussin 本人,委派 subagent 完成)

**Kelly criterion**:連續時間 Kelly(f* = (μ−r)/σ²)同單注 Kelly(f* = edge/odds)都冇明確
「收斂時間」呢一項——μ 本身已經假設係年化回報率。Mauboussin 嘅「折讓 ÷ 收斂年期 → 年化超額
回報」呢條算術,同 Kelly/mean-variance sizing 相容,但只係喺「任何 sizing 框架都會跟隨你餵
落去嘅年化回報估計」呢個瑣碎意義上相容——**唔算係獨立支持「收斂速度應該入 sizing 公式」呢個
具體主張**,如果誇大呢個類比會係 false analogy。

**Grinold & Kahn,*Active Portfolio Management***(Fundamental Law of Active Management、
alpha decay):有用持有期做 annualize/攤銷交易成本,概念上「時間影響倉位構建」呢個大方向
相關,但焦點喺成本/turnover trade-off 同訊號衰減,唔係「收斂越快應該注碼越大」——屬相鄰唔算
直接支持。

**Capozza & Israelsen (2010),*Journal of Investment Management*, Vol.8(4)**——「How
Quickly do Equity Prices Converge to Intrinsic Value?」:用 1997-2006 年約 8,845 隻股票,
發現市場每年平均抹走 mispricing 嘅 15-30%,速率隨規模/槓桿/analyst coverage 系統性變化。
**呢個係最接近嘅獨立實證支持**——證實「收斂速度」係一個真實、可測量、可以按公司特徵預測嘅
現象,但呢個係 ex-post 嘅平均 fade rate(regression 出嚟),唔係證明個別投資者對單一倉位嘅
ex-ante 收斂預測可靠。

**Shleifer & Vishny (1997),"The Limits of Arbitrage",*Journal of Finance***:經典論證——
錯價收斂嘅時機本身極不確定,noise-trader risk + 資本/agency 約束令錯價可以先擴闊先收窄,
**假設收斂快而重注嘅套利者,正正係最容易喺收斂發生之前被迫離場嘅一批**。呢個直接對應委派
任務第 4 點嘅預警,亦同標準 fractional-Kelly 文獻(因為輸入係估計值、唔係已知值,故打折用
Kelly)方向一致。

**Subagent 結論**:冇搵到獨立文獻將「折讓 × 收斂速度 → 注碼大小」正式驗證做一條規則——呢個
係書自己嘅框架延伸,唔係一條有獨立學術根基嘅公式。但收斂速度呢個**現象本身**(Capozza &
Israelsen)係真、可測量嘅,只係個別倉位嘅**預測**(唔係事後平均值)呢一步,先係文獻警告
(Shleifer-Vishny、Kelly 估計誤差文獻)嘅弱點所在。

---

## 6. 淨判斷

1. **折讓(margin of safety)呢一半**:喺 ticker 層面(n=20-21)有統計顯著支持(2 年期單變量
   p=0.0098,partial correlation 兩個期限都顯著/邊緣顯著),但摺返做誠實嘅週期層面樣本
   (n=11)後跌到唔顯著(p=0.083)。**方向一致、幅度唔細,但樣本太細唔夠力斷定「已證實」。**
2. **收斂速度呢一半**:單獨睇完全冇解釋力(甚至符號反晒);控制咗同折讓嘅混淆之後,符號
   轉返做預期方向,但只喺 partial correlation、1 年期邊緣顯著(p=0.068),週期層面完全唔顯著
   (p=0.51-0.69)。**呢一半嘅證據明顯比折讓弱**,加上呢個 proxy 本質上係 ex-post,WS5 喺
   trough 當下冇辦法可靠咁預先知道。
3. **聯合效應**(書嘅核心主張——兩項合埋睇先有意義)喺 partial correlation 層面有一定支持
   (控制混淆之後兩項符號都啱、1 年期折讓由唔顯著變邊緣顯著),但呢個發現建基於 n=20 嘅細
   樣本、~11 個真正獨立嘅週期,**唔應該被讀成「公式已驗證」**——只可以講「喺呢個歷史樣本入面
   冇睇到反證,方向大致一致,但統計力不足以確認」。
4. **WOLF 案例獨立確認**:呢條公式對「折讓」嘅定義本身冇區分「平常被低估」同「市場開始定價
   償付能力風險」,喺應用去 WS5 之前必須加一層 solvency/going-concern gate。
5. **獨立文獻**:收斂速度現象本身有真實學術支持(Capozza & Israelsen),但「你可唔可以喺
   買入嗰刻可靠咁預測佢」正正係文獻(Shleifer-Vishny、Kelly 估計誤差)警告嘅弱點——同本檔
   quant 部分嘅發現(收斂速度 ex-post 先見到訊號、ex-ante 冇獨立證據話計到)完全吻合。

---

## 7. 對 WS5 嘅方向建議(唔寫 code,純方向)

1. **折讓/margin-of-safety 呢一半值得考慮做一個輔助 sizing multiplier,但唔應該取代
   confidence 做主軸**——confidence 本身已經係 evidence-derived + calibrated(thesis 層
   NHITL 設計),折讓應該係一個**正交嘅第二輸入**(例如:同一個 confidence 分數,如果現價
   相對 thesis wiki 自己記錄嘅 normalized/mid-cycle 估值錨——例如 ttm_pe 分位、或者 §1.2
   提到嘅 threshold-margin spread——有明顯折讓,可以喺 raw_cap 上面加一個細嘅、有上限嘅
   multiplier;冇折讓或者估值已經貼近/超過歷史高位,唔加成)。**唔好將呢個 multiplier 做到
   同 confidence 同一數量級**——本檔嘅證據強度只夠支持一個保守嘅調整,唔夠支持一個主導性
   嘅輸入。
2. **收斂速度呢一半唔應該做 entry-time sizing 輸入**——證據太弱、而且本質上要求 ex-ante
   預測一個 WS5 冇辦法可靠計到嘅嘢。但收斂速度嘅**已實現**版本(即本檔嘅 200sma-reclaim
   proxy)可以考慮做一個 **post-entry 覆核訊號**——「開倉後,thesis 有冇開始被市場確認
   (股價連續脫離 200sma)」可以做 sizing 覆核/加碼嘅觸發條件之一(唔係初始注碼公式嘅輸入),
   呢個框架同 repo 現有嘅「crowding 壓 confidence」邏輯(thesis wiki 已用緊)方向一致——
   都係用 price-revealed 訊號做覆核,唔係做事前預測。
3. **必須加 solvency/going-concern gate**——任何折讓型 multiplier 生效前,先要通過一個
   基本嘅財務健康篩(例如:利息覆蓋率、淨負債/EBITDA、流動性跑道)。WOLF 證明純折讓 % 完全
   分唔開「平常低估」同「即將破產」。
4. **樣本量誠實聲明**:本檔嘅結論建基於 9-11 個歷史 supercycle、~20 個 ticker-trough 觀察值
   ——呢個樣本量喺統計上只夠支持一個**方向性、保守**嘅調整,唔夠支持一條精確嘅、Table-7.7
   風格嘅數值公式。如果 WS5 想採納呢個框架,建議做一個**粗粒度**嘅離散調整(例如「深度折讓
   +已開始確認」= 輕微加成一級;「淺折讓或未確認」= 唔加成),而唔係逐 basis-point 套用書嘅
   連續公式——後者嘅精確度冇被本檔嘅證據支持。

---

## Caveats

- 本檔用嘅 margin-of-safety proxy(trailing 5 年高位折讓)同書嘅 DCF-implied expected value
  折讓係兩件唔同嘅嘢——本檔只測試咗一個粗略、可觀察嘅代理,唔係書嘅原始定義。
- 收斂速度 proxy(連續脫離 200sma)係 ex-post/realized,唔係 WS5 可以喺 trough 當下用嘅事前
  訊號——呢個限制喺 §1.2、§6.5 已反覆強調,唔重複。
- 4 隻 ticker(X/MEE/PXD/LTHM)因已下市/被收購剔除,呢個係案例庫本身已經明寫嘅 survivorship
  限制嘅延伸,唔係本檔獨有嘅缺陷。
- 部分案例庫原始數字本身標註「約/unverified」(嚟自 subagent WebSearch,未經二次核實)——
  本檔只用咗案例庫入面**有明確日期同一手核實價位**嘅 case,盡量避免咗未核實數字,但案例庫
  本身嘅方法論限制(見 `2026-07-09_magnifier_case_library.md` Caveats 節)仍然適用。
- 統計檢定全部用 Spearman/partial rank correlation,冇做 multiple-comparison correction
  ——本檔匯報咗好幾個檢定(1y/2y × 3 個層次),如果做 Bonferroni 一類校正,§3.1-3.2 嘅
  「顯著」結果會更加站唔住腳。呢個係額外一層保守提醒,冇喺上面逐項重複計。
