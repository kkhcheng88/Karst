# 資本配置行為訊號複現——buyback_yield / net_issuance 橫截面 IC(2026-07-11)

**Date:** 2026-07-11  **Script:** `backtest/experiments/exp_buyback_capital_allocation.py`
**Cache:** `backtest/.insider_data/buyback_cap_alloc.pkl`(defeatbeta cash-flow/市值/價格,pickle)
**對照文獻:** `docs/2026-07-09_magnifier_literature.md` §2.1(Cooper-Gulen-Schill 2008 asset-growth、
Lyandres-Sun-Zhang 2008 new-issues puzzle、Fama-French 2015 CMA)

> **緣起:** 用戶讀完 Mauboussin *Expectations Investing* 同 Chancellor *Capital Returns*,兩本書都
> 論證管理層資本配置行為本身係訊號——現金併購=有信心、股票併購/增發=覺得自己股票貴、回購=覺得
> 自己股票平。本探測**唔係想「發現」新嘢**,而係喺 Karst 自己數據度**複現**呢個已有紮實學術地基
> 嘅因子,決定值唔值得加入 Phase-3 admission-lint / kill_condition 詞彙表
> (`docs/2026-07-08_phase3_ws3_lifecycle.md` §2)。

## 0. 方法

**mirror / increment / horizon**(memory `validation-mirror-and-increment`):
- **mirror** = 橫截面 rank IC + quintile long-short(呢個係 cross-sectional 因子,mirror 係「同一
  report-period 嘅全體候選股排名」,唔係單一標的擇時)。
- **increment** = 訊號本身 vs SPY-excess forward return;呢次係初探,冇「疊加喺現有訊號之上」嘅
  A/B 設計。
- **horizon** = 63/126/252 交易日(~3m/6m/12m),對應慢速基本面資本週期訊號嘅合理反應窗。

**Point-in-time 紀律**(repo 全域規則,見 `exp_family_validate.py`):signal 用 period-end ≤
(known_date − LAG)嘅現金流數據;forward return 一律用 known_date **之後**嘅價格。**LAG = 75
日曆日**(假設:涵蓋大型加速申報者 10-K 60 日死線 + buffer;10-Q 死線 40 日,75 日對兩者都保守)——
呢個係本探測自訂假設,唔係量度出嚟嘅數字。

**分母** = known_date 當日嘅 point-in-time 市值(defeatbeta `market_capitalization()`,逐日序列,
`asof()` 取值——**唔需要用 shares×price 重建**,defeatbeta 呢個 endpoint 直接俾長歷史逐日市值)。

**價格來源** = defeatbeta `price().close`,個股同 SPY 同一 vendor、同一時間戳慣例(同
`exp_valuation_broad.py`/`exp_family_validate.py` 一致)。

**成本假設:冇模擬交易成本**——呢個係橫截面 IC/quintile-spread 篩(睇排序有冇邊際訊息),唔係
live PnL;equal-weight、costless、forward window 有重疊(自相關 caveat,下文提)。

**宇宙:** `exp_valuation_broad.build_universe()` 原樣複用——11 個 SPDR 板塊 ETF 各取 top-10 US
持倉。**Caveat(如實披露,唔試圖修正):** 呢個宇宙係 mega/large-cap tilted,唔覆蓋細價股,同
repo 一般訊號測試標準(memory `backtest-testing-standard`,要求 4 股種含 IWM/IJR 細價股)唔一致。
用戶喺呢個任務明確要求複用 exp_valuation_broad 嘅宇宙構建法,所以特登唔強行塞細價股入嚟,淨係
如實披露呢個市值傾斜。

## 1. Probe 發現(defeatbeta 呢個 endpoint 冇喺 repo 用過,先驗證先寫正式管道)

用 AAPL/MSFT/XOM 三隻已知大盤股逐一驗證:

- `Ticker(tk).quarterly_cash_flow()` 返回**寬表**(row=科目名喺 `Breakdown` 欄,column=期末日
  期),數值係原始美元 `Decimal`,缺值用字串 `"*"` 標記(**唔係 NaN**,要自己轉)。
- **歷史深度只有 ~16 季**(AAPL 實測 `2022-06-30` 到 `2026-03-31`)——呢個係本探測最大嘅結構限制,
  見 §4。
- **`Repurchase of Capital Stock` 係負數**(現金流出),符合預期,要 `abs()` 轉正做「回購金額」。
- **`Net Common Stock Issuance` 正負號同用戶假設一致**:負=淨回購、正=淨增發。
- **Reconciliation(用戶要求明確檢查嘅一點):** `Net Common Stock Issuance` 係咪已經淨咗發行同
  回購?**答案:視乎公司有冇獨立嘅「Common Stock Issuance」科目。**
  - MSFT 有獨立科目:NCI(−4.09B)= Common Stock Issuance(+0.54B,員工認股計劃現金流入)+
    Common Stock Payments(−4.63B)。**真.淨額**,兩個分量方向相反。
  - AAPL/XOM/NVDA(probe 三隻 + 逐一驗證第四隻)**冇**獨立發行科目:NCI **完全等於**
    Common Stock Payments **完全等於** Repurchase of Capital Stock(逐季分毫不差)。
  - **全宇宙掃描證實呢個唔係少數例外**:101 隻有現金流數據嘅名入面,**62 隻(61%)冇獨立發行
    科目**,其中 **58 隻 NCI 逐季完全等於 −Repurchase**(機械上係同一條序列反號),**只有 39 隻
    (39%)有獨立發行科目、真正做緊淨額計算**。**呢個係一個重要嘅數據品質發現**:對六成宇宙嚟講,
    buyback_yield 同 net_issuance **唔係兩個獨立訊號**,只係同一個數字反號——下文 §2 兩訊號
    幾乎鏡像嘅結果,一部分係呢個機械關係嘅產物,唔淨止係「兩者剛好都捕捉到同一個現象」。
- `market_capitalization()` / `price()` 兩個 endpoint 都係**逐日長歷史序列**(AAPL/SPY 都返到
  1994-1996 年),唔係單一 snapshot——`asof()` 直接攞 point-in-time 市值,唔需要用
  shares×price 重建。

## 2. Pooled 結果(全宇宙、跨期、跨板塊 pooled)

宇宙 110 隻(11×10,GOOG/GOOGL 雙股權類別各計一隻)。**9 隻完全冇 `Repurchase of Capital Stock`
科目**(TSLA、BA、CRH、APD、AEP/ETR/XEL 三隻電力股、EQIX/VTR 兩隻 REIT——見 §4 結構性原因)。
最終 panel:**88 隻名、750 個 name-quarter 觀測、33 個 report-period(2023-03-31~2026-06-30)**。

`buyback_yield`:高 = 回購越多(方向預期 **正**)。`net_issuance`:高 = 淨增發越多(方向預期
**負**)。

| 訊號 | horizon | FM-IC(mean) | FM-t | hit-rate | n 日期 | pooled IC | pooled-t | n obs | Q5−Q1 | spread-t |
|---|---|---|---|---|---|---|---|---|---|---|
| buyback_yield | 63d | +0.082 | 1.78 | 88% | 8 | +0.087 | **2.25** | 661 | +3.3% | 1.85 |
| buyback_yield | 126d | +0.176 | **4.61** | 100% | 7 | +0.134 | **3.26** | 579 | +3.1% | 0.94 |
| buyback_yield | 252d | (n日期不足,5<6) | — | — | — | +0.192 | **3.99** | 417 | +4.6% | 0.47 |
| net_issuance | 63d | −0.066 | −1.43 | 25%* | 8 | −0.075 | −1.92 | 661 | −2.5% | −1.39 |
| net_issuance | 126d | −0.157 | **−5.12** | 0%* | 7 | −0.121 | **−2.93** | 579 | −1.1% | −0.34 |
| net_issuance | 252d | (n日期不足) | — | — | — | −0.162 | **−3.34** | 417 | −1.7% | −0.18 |

*net_issuance 嘅 hit-rate 定義係「IC>0 嘅日期比例」,但 net_issuance 嘅**預期方向係負**——所以
25%/**0%** 讀成「75%/**100%** 嘅期數方向啱」(126d 全部 7 個橫截面日期都係負 IC,方向零例外)。

**讀法:**
1. **兩個訊號 pooled rank-IC 方向都同文獻假設一致**,126d 同 252d 兩個 horizon、兩個訊號 **t 值
   都 >2.9**(buyback_yield 126d t=3.26、252d t=3.99;net_issuance 126d t=−2.93、252d t=−3.34),
   63d 邊際(|t|≈1.8-2.3)。FM-IC(逐日期平均,樣本力較弱因為 n日期只有 7-8)喺 126d 兩訊號都非常
   一致(buyback_yield t=4.61 hit 100%;net_issuance t=−5.12、7/7 日期方向啱)。
2. **但 quintile-spread(可交易嘅 top-vs-bottom 20% lens)明顯弱過 rank-IC**——buyback_yield
   spread-t 由 1.85(63d)跌到 0.94(126d)、0.47(252d);net_issuance 更弱(全部 |t|<1.4)。
   Quintile 均值亦**唔單調**(例如 buyback_yield 63d 嘅 Q1..Q5 = −0.4/1.8/−0.1/3.0/2.8%,
   Q2>Q3;net_issuance 126d Q1..Q5 = 4.1/8.7/1.1/1.6/3.0%,Q2 反而最高)——即排序相關性
   (rank IC)穩健,但「攞最極端 20% 做多空」嘅簡化交易表達雜訊大、對離群值敏感。**呢個係一個
   誠實嘅落差,唔係訊號唔存在,而係「量度方法比交易實作更穩健」。**
3. 兩訊號幾乎鏡像(見 §1 reconciliation)——61% 宇宙嘅 net_issuance 機械上等於
   −buyback_yield,所以呢個「鏡像」好大部分係定義上嘅,唔係兩個獨立驗證。真正提供獨立資訊嘅只有
   39% 有獨立發行科目嘅名(主要係大盤科技股同金融股,員工認股/ESPP 現金流入被拆開報)。

**訊號分佈(定 threshold 用,見 §6):**

| 訊號 | p10 | p20 | median | p80 | p90 |
|---|---|---|---|---|---|
| buyback_yield(占市值%) | +0.17% | +0.51% | +1.83% | +3.72% | +5.65% |
| net_issuance(占市值%) | −5.10% | −3.48% | −1.77% | −0.48% | −0.13% |

## 3. 分板塊結果(用戶關鍵問題:訊號係咪集中喺 Phase-3 supercycle target 嘅週期/materials/energy?)

板塊內 name 數目太少(~8-10隻)冇辦法做逐日期 Fama-MacBeth(`MIN_NAMES=25` 遠超板塊內樣本),
改用**板塊內 pooled Spearman IC**(跨全部季度、全部板塊內名一次過算)。**n 誠實列出——Util(3隻)
同 RealEst(2隻)樣本太薄,唔應該讀出結論。**

### buyback_yield 分板塊

| 板塊 | n名 | n obs | IC63 | t | IC126 | t | IC252 | t | Q5-Q1@126d | t |
|---|---|---|---|---|---|---|---|---|---|---|
| **Fin** | 10 | 50 | +0.247 | 2.23 | +0.312 | **2.69** | +0.414 | **3.15** | **+11.0%** | **2.29** |
| **Discr** | 9 | 41 | +0.153 | 1.20 | +0.217 | 1.61 | +0.235 | 1.51 | +9.6% | 1.60 |
| Indus | 9 | 33 | −0.054 | −0.40 | +0.068 | 0.47 | +0.373 | 2.24 | — | — |
| Materl | 8 | 42 | +0.118 | 0.95 | +0.155 | 1.18 | −0.028 | −0.18 | +13.8% | 1.62 |
| Tech | 9 | 41 | +0.108 | 0.87 | +0.148 | 1.12 | +0.070 | 0.44 | −3.0% | −0.13 |
| Health | 10 | 47 | +0.059 | 0.50 | +0.010 | 0.08 | +0.003 | 0.02 | −3.7% | −0.48 |
| Staples | 10 | 45 | +0.017 | 0.14 | −0.062 | −0.48 | +0.005 | 0.03 | +3.3% | 0.56 |
| Comm | 8 | 38 | −0.037 | −0.28 | −0.027 | −0.19 | −0.062 | −0.37 | +4.8% | 0.65 |
| Energy | 10 | 53 | −0.050 | −0.44 | −0.092 | −0.77 | +0.087 | 0.62 | −4.9% | −0.77 |
| Util | 3 | 17 | — | — | — | — | — | — | — | — |
| RealEst | 2 | 10 | — | — | — | — | — | — | — | — |

### net_issuance 分板塊(方向預期為負)

| 板塊 | n名 | n obs | IC63 | t | IC126 | t | IC252 | t | Q5-Q1@126d | t |
|---|---|---|---|---|---|---|---|---|---|---|
| **Discr** | 9 | 41 | −0.155 | −1.22 | −0.221 | −1.65 | −0.244 | −1.57 | −9.6% | −1.60 |
| Fin | 10 | 50 | −0.131 | −1.16 | −0.121 | −1.00 | −0.123 | −0.86 | −2.0% | −0.36 |
| Materl | 8 | 42 | −0.116 | −0.93 | −0.152 | −1.15 | +0.031 | 0.20 | −13.8% | −1.62 |
| Tech | 9 | 41 | −0.104 | −0.83 | −0.147 | −1.11 | −0.089 | −0.56 | +1.8% | 0.08 |
| Indus | 9 | 33 | +0.049 | 0.37 | −0.066 | −0.45 | −0.301 | −1.76 | — | — |
| Health | 10 | 47 | −0.019 | −0.16 | −0.044 | −0.35 | −0.011 | −0.07 | +3.7% | 0.49 |
| Staples | 10 | 45 | −0.021 | −0.17 | +0.063 | 0.49 | −0.009 | −0.06 | −1.4% | −0.23 |
| Comm | 8 | 38 | +0.039 | 0.30 | +0.018 | 0.13 | +0.077 | 0.46 | −4.8% | −0.65 |
| Energy | 10 | 53 | +0.056 | 0.50 | +0.092 | 0.77 | −0.086 | −0.62 | +4.9% | 0.77 |
| Util / RealEst | — | — | — | — | — | — | — | — | — | — |

**核心答案(直接回應用戶問題):訊號唔集中喺週期/materials/energy——最強嘅係 Financials 同
Discretionary,Energy/Materials 反而近零或方向不定。**

- **Financials 最強、最一致**:buyback_yield 三個 horizon t 值全部隨 horizon 拉長而**單調上升**
  (2.23→2.69→3.15),Q5-Q1@126d +11.0% t=2.29——全份報告入面**唯一一個 quintile-spread t>2
  嘅板塊**。呢個機制可能同用戶假設嘅「供給側資本紀律」唔同源:銀行回購金額受監管資本適足率同
  年度 CCAR/壓力測試批核限制,回購批核本身就係監管機構對資本強度嘅背書,同 Mauboussin/Chancellor
  講嘅「實體資產供給紀律」係唔同機制。
- **Discretionary 次強、方向兩個訊號都一致**(buyback_yield 同 net_issuance 喺 63/126/252d 三個
  horizon 方向全部啱,雖然 t 值未過 2)。
- **Energy 同 Materials——用戶特別關心嘅 Phase-3 supercycle target 板塊——訊號近零或方向反覆**:
  Energy 三個 horizon 之間方向都唔一致(buyback_yield −0.050/−0.092/+0.087);Materials 喺
  252d 訊號直接反號(+0.118/+0.155/**−0.028**)。**冇證據支持呢個訊號喺 Phase-3 想擴張嘅
  週期/商品板塊特別有效**——反而喺完全唔同機制嘅 Financials 最強。
- Indus 喺 252d 出現高 IC(+0.373,t=2.24)但 63/126d 唔顯著、且 n=33 obs 太薄(quintile 直接
  insufficient),**唔應該單憑一個 horizon 嘅單點結果下結論**。

## 4. 數據品質問題(未來維護者要知)

1. **現金流歷史只有 ~16 季**(2022Q2~2026Q1)——**整個測試活喺單一總體經濟 regime**(後疫情/
   加息/AI-capex 週期)。呢個唔係「樣本細」呢種一般 caveat,係**結構性單一 regime**——一個
   弱/null 結果**唔能夠推翻**幾十年歷史嘅學術因子(Cooper-Gulen-Schill 用 1968-2003),
   一個正結果都**對呢個 regime 高度敏感**(fragile),唔應該直接當長期穩健因子用。
2. **9 隻完全冇 `Repurchase of Capital Stock` 科目**:TSLA、BA、Materials 兩隻(CRH/APD 部分)、
   **電力三隻(AEP/ETR/XEL)全部**、**REIT 兩隻(EQIX/VTR)全部**。呢個唔止係隨機數據缺口——
   **公用電力同 REIT 結構性係資本募集者、唔係資本歸還者**(佢哋靠持續發新股/舉債嚟資助重資產
   資本開支,監管費率結構亦令佢哋較少回購),所以先解釋咗 §3 表入面 Util/RealEst 板塊樣本
   特別薄(3隻/2隻)——**呢個本身係一個有資訊性嘅發現:呢個訊號喺資本密集型受監管行業結構上
   唔適用,唔淨係「defeatbeta 冇呢個板塊嘅數據」**。
3. **不同財年結算日令 Fama-MacBeth 橫截面日期數目偏少**:NVDA 等公司財年唔跟日曆季(NVDA 2026
   財年 Q1 結算喺 2026-04-30,唔喺 03-31),令逐日期分組(`groupby("q_end")`)嘅「同一日期」
   橫截面實際上只有日曆季結算日(3/31、6/30、9/30、12/31)嘅公司先夠 `MIN_NAMES=25` 門檻——
   FM-IC 只有 7-8 個可用日期(遠少過 33 個總 report-period 數),呢個直接令 FM-IC 嘅統計力偏弱、
   252d horizon 直接 insufficient(可用日期跌到 <6)。**呢個唔係 bug,係財年錯開嘅結構性後果**,
   pooled IC(唔分日期直接全部 pool)冇呢個問題,樣本力較強,所以本報告以 pooled IC 為主要判讀
   依歸、FM-IC 做交叉印證。
4. **`Net Common Stock Issuance` 對 61% 宇宙嚟講機械上等於 −Repurchase**(見 §1)——即
   buyback_yield 同 net_issuance 兩條序列喺呢啲名度**唔係獨立訊號**,兩者嘅結果高度相關係預期
   之內,唔可以當成「兩個獨立方法互相驗證」嘅證據。
5. **GOOG/GOOGL 雙股權類別**都入咗宇宙(XLK/XLC top-10 各自持有兩個股權類別),等於 Alphabet
   喺 pooled 統計入面被算兩次——輕微膨脹 n,對結論方向影響可忽略但如實披露。
6. **Overlapping forward windows**(63/126/252d 逐季度取樣,相鄰季度嘅 forward window 大幅重疊)
   帶嚟自相關,t-stat 有輕微高估嘅風險——本報告冇做 Newey-West 或 block bootstrap 修正,讀 t 值
   時打個折扣。

## 5. 判定

**訊號喺 Karst 自己數據度可複現,方向同文獻一致,但係「真但細、regime 唔穩、板塊集中喺意外
嘅地方」——同 repo 對 Novy-Marx OL 溢價嘅既有判讀(memory:「真但細嘅 T1 擇時 alpha」)係同一種
結論形狀。**

1. Pooled rank-IC 喺 126d/252d 兩訊號皆 |t|>2.9,方向 100% 符合 Mauboussin/Chancellor 假設
   (回購多=好、增發多=差)。
2. 但 quintile-spread(較貼近實際可執行嘅 top-vs-bottom 分組)明顯弱過 rank-IC、且非單調——**呢個
   訊號更似係一個連續排序訊號,唔係一個可以簡單二分做多空嘅乾淨切分**。
3. 分板塊拆解係本次最反直覺嘅發現:**唔集中喺 Phase-3 想擴張嘅週期/materials/energy**(呢兩個
   板塊訊號近零、方向唔穩定),反而**集中喺 Financials(監管資本紀律機制)同 Discretionary**。
4. 單一 ~16 季 regime,結論嘅時間跨度信心低——呢個唔係否證幾十年學術文獻,但都唔足以喺 Karst
   自己數據度單獨支持一個高信心嘅硬性規則。

## 6. 建議:Admission-lint / kill_condition 收編方式

**建議 (c):人手判斷 checklist 項目,收編入 WS3 §2 嘅「4-KPI 逐項 cited 打分」——唔升做 (a)
machine lint 硬閘,亦唔建議做 (b) kill_condition trigger-language 候選詞。**

**理由(對應上面每個發現):**

- **反對 (a) machine lint 硬閘**:硬閘需要一個對全部候選主題都穩健嘅門檻,但呢個訊號(i)只喺
  單一 ~16 季總體經濟 regime 驗證過,(ii)quintile-spread lens 弱(spread-t 全部 <1.9),
  (iii)喺 Phase-3 實際想擴張嘅週期/materials/energy 板塊近零——三個一齊睇,將呢個訊號寫死做
  admission 硬閘(好似 tickers loadable / kill_condition trigger verb 咁),會喺最相關嘅目標
  板塊誤殺或誤放行真正嘅供給紀律故事,風險大過收益。
- **反對 (b) kill_condition trigger-language 候選**:`TRIGGER_RE`(`thesis/lint.py`)嘅設計係
  單一 catalyst 式事件觸發(「Trigger」、「觸發」、「to zero」、「de-list」、「mean-revert」),
  資本配置訊號係一個**連續、逐季更新嘅排序特徵**,唔係一個離散事件——語意上唔啱套入 kill_condition
  嘅「事實成立即除牌」框架,勉強塞入去反而會製造一個永遠唔會乾淨觸發嘅偽 kill_condition。
- **支持 (c) 4-KPI checklist 項目**:呢個訊號真.存在且方向符合文獻,但強度/板塊分佈嘅細節需要
  分析師逐案判斷(尤其:Financials 嘅回購反映監管資本強度、唔係供給紀律,套用落 Phase-3 嘅
  supercycle thesis 時要小心呢個機制差異;Materials/Energy 訊號本身弱,唔應該作為呢兩個板塊
  thesis 嘅主要佐證)——呢種「方向啱但要人手判斷邊個機制」嘅情況,正正係 checklist 而唔係
  自動閘嘅設計初衷。

**具體門檻建議(落 checklist 用,數字取自 §2 pooled 分佈嘅實測分位數,唔係憑空定):**

- **正面佐證**(支持「管理層有信心/資本紀律」呢一格 KPI):trailing-4Q `buyback_yield` **≥
  3.7%**(市值)——對應 pooled p80 cutoff,即回購強度排名前 20% 嘅名。
- **負面/警示旗**(供給紀律缺口,尤其套用喺 materials/energy/週期 thesis 時要求分析師額外解釋):
  trailing-4Q `net_issuance` **≥ −0.5%**(市值,即最接近零/轉正嘅一端)——對應 pooled p80
  cutoff,即淨增發(相對最少回購)排名前 20% 嘅名。
- 兩個門檻都應該**連同板塊一齊讀**:Financials 名觸發正面門檻,證據力應該**打折**(監管資本
  機制,唔係供給紀律);Materials/Energy 名觸發任一門檻,證據力都**弱**(訊號喺呢兩個板塊本身
  近零,唔應該單憑呢一項就大幅調高 confidence)。

**未來如果要重新評估**:等 defeatbeta 現金流歷史自然累積過多一個總體經濟 regime(例如跨埋一次
明顯嘅利率週期轉向)先重跑,或者手動補歷史久遠嘅 10-K/10-Q 現金流數據延長樣本——喺單一 regime
基礎上升級呢個訊號做硬閘,風險大過現階段能證明嘅收益。

---

## 2026-07-11 追加:look-ahead 驗證 + market-cap tier breakdown

用戶追問兩點:(1) 原 backtest 宇宙(SPDR top-10)清一色大價股,細/中價股完全未測,會唔會好似
insider 訊號咁喺細價股先特別有效;(2) 訊號係咪受「公佈嗰刻即時反應」污染,即冇小心處理
publish lag。本節逐點回應,**唔改動上面原有內容**。

### A. Look-ahead 方法論驗證(獨立結論)

**方法:** 唔淨止讀 code 就假設冇事,直接用 `backtest/.insider_data/buyback_cap_alloc.pkl`
cache 做程式化逐案檢查(AAPL/MSFT),印出「feature 窗口實際用咗邊幾季」、「known_date 點計」、
「forward window 實際由邊個交易日開始」,睇三者關係係咪真係符合設計意圖。

**驗證結果(AAPL 2025-12-31 report period 為例,見附帶輸出):**

```
trailing 4Q window used as FEATURE (all <= q_end):
  2025-03-31 .. 2025-12-31   <- 全部係 q_end 或之前嘅歷史數據
q_end (report period end)      = 2025-12-31
known_date = q_end + 75d       = 2026-03-16
p0 (forward window 起點,首個 >= known_date 嘅交易日) = 2026-03-16
=> feature 窗口喺 2025-12-31 完結;forward-return 窗口喺 2026-03-16 先開始,相距 75 日,
   零重疊。
```

再對全部 quarters(唔止呢一個 case)跑咗一次「`p0 >= known_date` 係咪對全部觀測都成立」嘅
programmatic assertion(`px.index.searchsorted(known_date)` 揾嘅第一個交易日),AAPL/MSFT
**全部觀測都成立**——冇一個 case 用咗 known_date 之前嘅價格做 forward-return 起點。

**結論(三層面逐一確認,冇搵到 look-ahead bug):**
1. **Feature(trailing 4Q buyback/issuance)**:只用 `q_end` 或之前嘅歷史現金流數據,冇任何一格
   用到 `q_end` 之後先出現嘅數字。
2. **分母(market cap)**:用 `mcap.asof(known_date)`——known_date 本身已經係 `q_end + 75
   日`之後,唔係用 `q_end` 當日嘅市值(如果用 q_end 當日市值,先會有「用咗未公佈消息影響落嘅
   分母」呢種微妙污染;現在冇呢個問題)。
3. **Forward-return 起點**:`searchsorted(known_date)` 揾嘅係 known_date 當日或之後嘅第一個
   交易日,實測全部 case 都 `>= known_date`。即由 `q_end` 到 `known_date` 呢 ~75 日(涵蓋真實
   財報發佈同市場消化嗰段時間)**完全被排除喺 forward window 之外**——非但冇「公佈嗰刻即時反應
   污染」,反而係**保守到攞唔到呢段真實嘅 post-earnings drift**(如果用真實發佈日做起點,可能
   反而攞到更多訊號,而家嘅設計已經係方向上偏向低估訊號、唔係高估)。

**但延伸去細/中價股先浮現嘅新風險(用戶追問嘅「污染」喺呢個新場景先有實質意義):**
`LAG_DAYS = 75` 呢個假設本身係為**大型加速申報人**(Large Accelerated Filer)校準——SEC 申報
死線實際分三級:

| Filer 級別 | 流通市值門檻 | 10-K 死線 | 10-Q 死線 |
|---|---|---|---|
| Large Accelerated Filer | ≥ $700M | 60 日 | 40 日 |
| Accelerated Filer | $75M–$700M | 75 日 | 40 日 |
| Non-Accelerated Filer | < $75M(好多 micro/small-cap 屬呢級) | **90 日** | **45 日** |

原本嘅 SPDR top-10 宇宙全部係 large accelerated filer(流通市值遠超 $700M),75 日對佢哋嚟講
本身已經有 buffer,冇問題。但**如果將 75 日不加區分咁套用去 micro-cap,就有實質 look-ahead
風險**——因為對一個真正嘅 non-accelerated filer,`known_date`(q_end+75d)嗰陣佢個 10-K 可能
仲未到 90 日死線、仲未真正公開,「訊號用咗未公開嘅數據」。**呢個唔係原 backtest 嘅 bug(佢淨係
測大價股,75 日綽綽有餘),而係「淨係複製 75 日呢個數字去細價股先會產生」嘅新風險**——下面嘅
market-cap tier extension 因此改用 **LAG_DAYS = 100 日**(90 日死線 + 10 日 buffer),四個
tier 統一套用,對細價股安全、對大價股方向唔變(大價股實際發佈都遠早過 75 日,加闊去 100 日
淨係令 forward window 起點推遲少少,唔會反轉訊號方向)。

**驗證結論一句話:原 script(大價股宇宙、LAG_DAYS=75)冇 look-ahead bug,通過逐案 + 全量
programmatic 驗證;但佢嘅 LAG_DAYS 假設係為大價股校準,唔應該不加修改咁直接套用去細/中價股
——延伸測試已對應修正(LAG_DAYS=100)。**

### B. Market-cap tier breakdown

**Script:** `backtest/experiments/exp_buyback_mktcap_tier.py`  **CF cache:**
`backtest/.insider_data/buyback_cf_tiers.pkl`

**宇宙構建:** 唔重新起 ETF-holdings 宇宙,直接復用 repo 現成、已被 `exp_insider_mktcap.py` /
`exp_institutional_attention_proxy.py` / `exp_families_mktcap_tiers.py` 用開嘅 broad pool——
`backtest/.insider_data/px_defeatbeta.pkl`(6,769 隻 ticker 嘅逐日收市價)+
`mktcap_defeatbeta.pkl`(6,766 隻 ticker 嘅逐日市值),按**歷史中位數市值**分 4 級(同 repo 既有
tier 定義完全一致:micro <$300M / small $300M–2B / mid $2B–10B / large >$10B),每級**系統性
等距抽樣**(唔係隨機、唔係開頭 N 個)最多 150 隻做候選——micro/small/mid 三級嘅合資格池都
遠超 150(881/946/554 隻),large 池得 241 隻(>=500 日價、有市值史嘅名),照樣抽 150。**淨新
數據拉取只有 quarterly_cash_flow**(價/市值全部複用現成 pickle,冇重新叫 defeatbeta 嘅
price()/market_capitalization())。

**LAG_DAYS 改用 100 日(唔係原 script 嘅 75 日)**——見上面 §A 尾段:75 日係為 large accelerated
filer(10-K 60 日死線)校準,細價股好多屬 non-accelerated filer(10-K 90 日死線),繼續用 75
日去細價股會有真實 look-ahead 風險。四個 tier 統一用 100 日(90 日死線+10 日 buffer),令 tier
之間嘅比較唔會被「唔同 tier 用唔同 lag」呢個混淆因素污染。**代價:同原 script(75 日)嘅
large-cap 結果唔係 byte-for-byte 對照,係方法論上更保守嘅版本**——下面會見到方向一致、強度
稍為溫和咗(符合預期:lag 拉闊咗,forward window 起點推遲,攞少咗少少早段 drift)。

**Tiering 用 dynamic(逐 observation 動態判定),唔用 static(抽樣時嘅歷史中位數):** 每一個
name-quarter 觀測嘅 tier,係用嗰次觀測嘅 `known_date` 嗰刻嘅**即時市值**(同 buyback_yield/
net_issuance 分母同一個數字)重新 `pd.cut()` 分級——因為 ~2023-2026 呢 3 年入面唔少名嘅市值
跨咗級界(例如唔少「候選時中位數係 mid」嘅名,喺後期觀測時已經漲到 large;反之亦然)。實測
**72.9% 觀測嘅動態 tier 同抽樣時嘅 tier 一致**,其餘 27.1% 有跨級——用動態 tier 先係誠實嘅
「呢個訊號喺呢個市值級別 work 唔 work」讀法,唔係用「呢隻股票喺 2023 年係咩級」呢種過時標籤。

#### 樣本流失(老實報告,唔隱瞞)

| Tier(候選抽樣時嘅級別) | 抽樣 n | cash-flow 拉到 | 有 rep+nci 兩行 | 有齊 px/mc 可用 | 落最終 panel 嘅 obs |
|---|---|---|---|---|---|
| micro <$300M | 150 | 150(100%) | 77(**51.3%**) | 45(**30.0%**) | 311 |
| small $300M-2B | 150 | 150(100%) | 101(67.3%) | 78(52.0%) | 550 |
| mid $2B-10B | 150 | 150(100%) | 136(90.7%) | 112(74.7%) | 864 |
| large >$10B | 150 | 150(100%) | 139(92.7%) | 122(**81.3%**) | 1012 |
| **合計** | **600** | **600** | **453** | **357** | **2737** |

**讀法:** defeatbeta 嘅 `quarterly_cash_flow()` endpoint 本身對細價股冇「攞唔到」問題(100%
拉到數據),**但拉到嘅表入面有冇 `Repurchase of Capital Stock` / `Net Common Stock Issuance`
呢兩行,micro-cap 得 51%、large-cap 有 93%**——即接近一半 micro-cap 完全冇回購/增發呢類線目
(好多細價股單純冇做過回購,或者財報格式簡化到冇呢個科目)。加埋要有齊 4 季連續數據 + 可用
市值/價格史,micro-cap 嘅**端到端存活率只有 30%**,large-cap 有 81%——**細價股樣本先天薄
過大價股接近 3 倍**,呢個係報告呢個訊號喺細價股結論時必須帶住嘅 caveat(micro tier 最終得
49 隻名、105-205 個 obs,睇 t 值時要打好大折)。最終 panel:**2,737 個 name-quarter 觀測、
357 隻名、35 個 report-period(2023-01-31~2026-05-31)**。

#### 核心結果:按 dynamic tier 拆解(對照原 §2 大價股 pooled 結果並列)

`buyback_yield`(高=多回購,預期 **正**)pooled Spearman IC(t 值):

| Tier | 63d IC(t) | 126d IC(t) | 252d IC(t) | Q5-Q1@126d(t) |
|---|---|---|---|---|
| **micro <$300M** | −0.020 (−0.29) | −0.045 (−0.58) | −0.021 (−0.21) | −8.5% (−0.84) |
| **small $300M-2B** | −0.087 (−1.71) | **−0.153 (−2.86)** | −0.174 (−2.73) | −15.9% (−2.82) |
| **mid $2B-10B** | −0.028 (−0.66) | −0.096 (−2.07) | −0.109 (−1.95) | −6.7% (−1.54) |
| **large >$10B(本次 broad 樣本,LAG=100)** | +0.063 (2.01) | **+0.086 (2.54)** | +0.129 (3.12) | +8.3% (2.85) |
| *[對照] large SPDR top-10(原 §2,LAG=75)* | *+0.087 (2.25)* | *+0.134 (3.26)* | *+0.192 (3.99)* | *+3.1% (0.94)* |
| **ALL TIERS POOLED(本次全樣本一齊 pool)** | −0.001 (−0.03) | −0.024 (−1.04) | −0.014 (−0.49) | −1.4% (−0.58) |

`net_issuance`(高=多增發,預期 **負**)pooled Spearman IC(t 值):

| Tier | 63d IC(t) | 126d IC(t) | 252d IC(t) | Q5-Q1@126d(t) |
|---|---|---|---|---|
| **micro <$300M** | +0.018 (0.25) | +0.030 (0.39) | −0.027 (−0.27) | −2.7% (−0.40) |
| **small $300M-2B** | +0.071 (1.39) | **+0.117 (2.18)** | +0.140 (2.18) | +13.9% (2.80) |
| **mid $2B-10B** | +0.045 (1.04) | +0.102 (2.19) | +0.128 (2.29) | +7.1% (1.68) |
| **large >$10B(本次 broad 樣本,LAG=100)** | −0.061 (−1.92) | **−0.086 (−2.54)** | −0.129 (−3.11) | −8.0% (−2.72) |
| *[對照] large SPDR top-10(原 §2,LAG=75)* | *−0.075 (−1.92)* | *−0.121 (−2.93)* | *−0.162 (−3.34)* | *−1.1% (−0.34)* |
| **ALL TIERS POOLED(本次全樣本一齊 pool)** | +0.002 (0.09) | +0.013 (0.56) | +0.000 (0.01) | −0.3% (−0.14) |

（FM-IC 交叉印證:small/mid 喺 63/126d 都有夠日期數計 FM-IC,方向同 pooled IC 完全一致——
small `net_issuance` 126d FM-IC=+0.125、t=2.03、6 個橫截面日期入面 83% 方向一致,唔係 pooled
autocorrelation 製造出嚟嘅假象。large tier FM-IC 126d 都顯著(buyback_yield t=3.02、
net_issuance t=−3.33)。micro tier 全部 horizon 都 `MIN_NAMES=25` 唔夠、FM-IC insufficient
——micro 嘅結論本身已經薄弱,呢點令佢更加唔可信。）

#### 讀法(直接回應用戶核心問題)

1. **同 insider 訊號嘅型態完全相反,唔係「細價股先特別有效」,而係「細/中價股方向反晒」。**
   large-cap(broad >$10B 樣本)兩個訊號、三個 horizon、pooled IC **全部方向啱且 t>2**(除
   63d net_issuance t=−1.92 邊際),同原 §2 嘅 SPDR-top-10 mega-cap 結果**方向、量級都一致**
   ——證實原結果唔係「淨係 mega-cap 先得」嘅假象,>$10B 呢個更廣嘅 large-cap 定義一樣 work。
   但 small($300M-2B)同 mid($2B-10B)兩級,**126d/252d 兩個訊號都顯著(t 值 1.7-3.5)反晒
   方向**——買得多回購嘅 small/mid-cap,forward return 反而**跑輸**;增發得多嘅 small/mid-cap,
   forward return 反而**跑贏**。252d 呢個反轉仲**加劇**(small net_issuance 252d IC=+0.140
   t=2.18;mid net_issuance 252d Q5-Q1=+26.0% t=3.53,係全份報告見過最大嘅 quintile spread)。
   Micro-cap(<$300M)全部唔顯著(|t|<1.2)、樣本亦最薄(§ 樣本流失表)、quintile means 非單調
   ——**讀唔出任何結論,唔係「冇效」,而係數據唔夠撐任何結論**。
2. **呢個反轉唔係 statistical noise:pooled IC、FM-IC(獨立日期分組)、quintile spread 三個
   lens 喺 small/mid 兩級都指向同一個方向**,同原報告 §2 話「quintile-spread lens 弱過
   rank-IC」嗰種「有排序訊號但唔夠乾淨切分做多空」嘅情況唔同——small/mid 兩級嘅 quintile
   spread(126d small net_issuance +13.9% t=2.80;mid 252d net_issuance +26.0% t=3.53)反而
   **好乾淨、單調、t 值仲高過 large-cap 自己嘅 spread**。
3. **合理經濟機制假說(未驗證,留俾分析師 checklist 判斷):** Mauboussin/Chancellor 嘅「回購=
   管理層覺得平、增發=管理層覺得貴」呢個 signalling 框架,前提係「管理層有其他資金來源、增發
   係主動選擇」——呢個假設對 large-cap 成立。但 small/mid-cap 嘅增發好大機會係**成長期融資**
   (擴產能、做 M&A、燒錢期補充彈藥),唔係「股價貴就發股」嘅機會主義行為;反過嚟講,一間
   small/mid-cap 選擇大手回購而唔係再投資,可能反映**佢已經冇高回報嘅增長機會**(mature/
   declining 嘅訊號,唔係「平」嘅訊號)。呢個假說如果成立,就同 insider 訊號嘅「細價股資訊
   不對稱大、訊號更強」機制**完全唔同源、甚至方向相反**——insider 買賣係「知情人士對抗市場
   錯價」,回購/增發喺細價股更似係「生命週期階段」嘅副產品,唔係「對抗錯價」嘅訊號。
4. **ALL TIERS POOLED 呢一行係一個獨立警示:三個 horizon pooled IC 全部 |t|<1.1、接近零。**
   如果唔做 tier 拆解、直接喺全市場 pool 呢個訊號,會錯誤結論「訊號唔存在」——實情係
   large-cap 同 small/mid-cap **兩個真實但方向相反嘅效應互相抵銷**咗。呢個係本次擴展測試
   最重要嘅方法論教訓:**呢個訊號一定要按市值分層先可以讀,唔可以當單一因子全市場套用。**
5. **旁支發現:broad large-cap(>$10B,177 隻名)嘅 quintile-spread 明顯強過原 SPDR-top-10
   mega-cap 樣本**(buyback_yield 126d spread-t:2.85 vs 原 0.94;net_issuance 126d spread-t:
   −2.72 vs 原 −0.34)——即用更廣嘅「>$10B」定義、唔淨係最頭 10 大嘅 mega-cap,quintile 極端組
   反而更乾淨可交易。可能機制:SPDR top-10 淨係攞最大嗰批(通常係全市場最多分析師覆蓋、最有效
   price in 嘅名),邊際訊息更少;$10B-mega-cap 之間呢批「大但未至於巨大」嘅名可能仲有少少
   殘餘 mispricing 畀呢個因子捕捉。呢點屬旁支觀察,冇再深挖,留低俾未來想調 large-cap
   threshold 嘅人參考。

#### 對 §6 建議嘅修正

原 §6 建議(c)「人手判斷 checklist 項目」呢個大方向**不變**,但門檻同讀法要按呢次發現**收窄
適用範圍**:

- **正面/負面門檻(原 §6 嘅 p80 cutoff)只應該套用喺 large-cap(>$10B)名**——呢個係唯一
  一個訊號方向、統計顯著性、quintile 乾淝度三者都對齊嘅級別。
- **Small-cap($300M-2B)同 mid-cap($2B-10B)名唔應該套用原本嘅門檻方向,反而應該讀成
  反向警示**:一個 small/mid-cap 名觸發「trailing buyback_yield 高」呢一格,喺呢個市值
  級別**唔係正面佐證,反而statistically 更似係負面**(可能反映增長機會枯竭);觸發
  「net_issuance 高(淨增發)」喺呢個級別**唔應該直接扣分**,分析師要先判斷係咪成長期
  融資(如果係,增發本身唔應該減 confidence)。**呢個唔係「訊號較弱所以打折」,係「訊號可能
  反方向」,兩者喺 checklist 操作上完全唔同——打折係「證據力減半」,反方向係「證據力可能要
  反轉正負號讀」。**
- **Micro-cap(<$300M)名:呢格 KPI 直接標「數據不足,不適用」**,唔好嘗試套用任何門檻(正或
  反)——樣本(49 隻名、105-205 obs)同 quintile 非單調嘅表現都話畀你知冇足夠證據支持任何
  方向嘅結論,強行套用門檻(無論正反)都係假精確。
- 呢個修正令原 §6 嘅 checklist 項目由「一個跨全宇宙嘅門檻」變成「一個按市值分層讀嘅門檻—
  large-cap 正常讀、small/mid-cap 反著讀、micro-cap 唔讀」,複雜咗,但呢個複雜度係數據逼出
  嚟嘅誠實結論,唔係過度工程。
