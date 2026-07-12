# 機構持股率(低端)做早期訊號 —— feasibility + backtest(2026-07-11)

> 觸發:Peter Lynch 蒸餾(`docs/2026-07-11_magnifier_book_one_up_on_wall_street.md` §3.3)
> 指出 Phase-3 priced-in 閘而家淨用 analyst coverage/OW rating 做「遲/擠」端,但 Lynch 提出
> 呢條軸應該有兩端——機構持股低 = 未被發現 = 早期正訊號。本檔查證數據可行性 + backtest。

## 0. 一句結論(先讀)

**機構持股率本身(historical time series)喺 Karst 現有數據源下測唔到**——yfinance 淨係
snapshot、SEC 13F bulk data 技術上得但 CUSIP↔ticker 冇免費權威對照表,係多日工程,唔喺
呢個任務範圍內做。**改用可行嘅代理變數**——成交額/市值 turnover(數據源:defeatbeta 逐日
成交量 × 收市價,除以 cached 市值序列,有乾淨嘅完整歷史)——backtest 咗「低關注度」假設,
結果見 §3。學術地基:Arbel & Strebel (1982/1983) "neglected firm effect" 已證少 analyst
追蹤嘅股票平均回報較高,而且**喺控制 size 之後依然顯著**(唔淨係 small-firm effect 嘅
代理)——本 backtest 直接用 tier-matched benchmark 做呢個 size control。

---

## 1. Feasibility check(先查證,唔假設有 historical time series)

### 1.1 yfinance `heldPercentInstitutions` —— 確認淨係 snapshot,冇歷史查詢

- 直接攞 `yf.Ticker('AAPL').info` 出嚟嘅 `heldPercentInstitutions` = 0.65732(單一數值,
  冇日期參數)。
- 追查 yfinance 1.3.0 原始碼(`yfinance/scrapers/holders.py`):`Holders._fetch()` 淨係
  call 一個 endpoint —— `https://query.../v10/finance/quoteSummary/{symbol}`,
  `params_dict` 入面**冇任何日期/期間參數**;呢個 endpoint 本質係 Yahoo Finance quote 頁
  嘅即時/最新資料源,唔係歷史資料庫。`institutional_holders`/`major_holders`/
  `mutualfund_holders` 三個方法全部經同一個 `_fetch_and_parse()`,`Date Reported` 呢個
  欄位淨係話俾你知**最新一份 13F 嘅申報日**(例:AAPL 測到 `2026-03-31`),唔係「呢個
  百分比喺歷史邊個時點係幾多」——即係話你今日 call 呢個 API,揸到嘅一定係「現時最新」,
  冇辦法問「2019 年呢隻股嘅機構持股率係幾多」。
- **結論:yfinance 呢條路唔可行**,同任務原先嘅懷疑一致,已用原始碼追查證實(唔係憑
  空估計)。

### 1.2 defeatbeta_api —— 完全冇呢個欄位

`Ticker(tk)` 嘅方法清單(`dir()` 逐個列出)入面**冇任何 institutional/analyst 相關方法**
(`.info`、`.company_meta`、`.officers` 都唔含呢類數據)。defeatbeta 呢條路唔存在,連
snapshot 都冇。

### 1.3 SEC EDGAR Form 13F bulk data —— 技術上得,但 CUSIP↔ticker 對照係真.工程瓶頸

實測(唔係憑空推論):
- `sec.gov/data-research/sec-markets-data/form-13f-data-sets` 提供 **2013年7月至今**
  逐季(2024年3月後改逐月滾動 3 個月窗)ZIP,每份含 `INFOTABLE.tsv`(逐持倉明細)。
- 實際下載一份季度檔(`01sep2025-30nov2025_form13f.zip`)驗證:壓縮 **85.6MB**,
  `INFOTABLE.tsv` 解壓 **338MB、327 萬行**。由 2013 Q2 到而家約 50+ 份呢類檔,全部
  解壓埋一齊估計 **10-15GB+**。
- 關鍵欄位:`ACCESSION_NUMBER, NAMEOFISSUER, TITLEOFCLASS, CUSIP, VALUE, SSHPRNAMT,
  SSHPRNAMTTYPE, PUTCALL, INVESTMENTDISCRETION, VOTING_AUTH_*`——**冇 ticker 欄位,
  淨係 `CUSIP` + 自由文字 `NAMEOFISSUER`**。要將呢份數據轉做「某隻 ticker 逐季機構持股
  率」,一定要:
  1. 幫目標 universe 每隻 ticker 解析出佢嘅 CUSIP(**冇免費、權威嘅 ticker↔CUSIP 對照表**
     ——CUSIP 本身係 CUSIP Global Services(S&P 底下)嘅授權數據,OpenFIGI 明確**唔含
     CUSIP**;要做就要逐季用 `NAMEOFISSUER` 模糊比對,人手核對,公司改名/股份分類會令
     呢步更煩)。
  2. 逐季下載 + 解壓 + 過濾 INFOTABLE(全市場數萬個 filer、327 萬行/季 × 50+ 季)。
  3. 攞返每隻 ticker 逐季嘅流通股數(shares outstanding)做分母,先可以算「機構持股 佔
     流通股 %」。
  4. 仲要處理 `PUTCALL`(options 部位)、`INVESTMENTDISCRETION` 等欄位嘅正確過濾邏輯,
     否則個 % 會計錯。
- **老實評估工作量**:單係第 1 步(CUSIP 解析,~200-300 隻 ticker)已經係人手/半自動
  逐隻核對嘅活,加埋第 2-4 步嘅工程(下載/解壓/過濾/正規化 10GB+ 數據、對齊歷史股數),
  屬於**多日獨立工程項目**,唔係呢個任務範圍內可以順手做嘅嘢。
- **結論:技術上可行,但依家唔做**——同 repo 已有嘅 SEC bulk data 經驗對照(`.insider_data/
  2006q1_form345.zip` 等 Form 3/4/5 insider 交易 bulk data,由 2006 到而家逐季下載咗做
  另一個項目)可以印證:呢類 SEC bulk EDGAR 工程本身係 repo 做得到嘅事,但 Form 13F 呢個
  specific 重建(CUSIP 解析嗰步)仲未做過,值得日後獨立立項,唔應該喺呢個 probe 度夾硬塞。

### 1.4 替代 proxy 逐個查證

- **Analyst coverage 數目**(`numberOfAnalystOpinions`)——**一樣係 snapshot 問題**:
  yfinance `.info` 度嘅呢個欄位冇日期參數(同 §1.1 同一個 `quoteSummary` endpoint)；
  `t.recommendations` 雖然有 `period` 欄(0m/-1m/-2m/-3m),但**淨係得返近 4 個月嘅滾動
  窗**,唔夠做 2016+ 多年份 backtest。defeatbeta 完全冇 analyst 欄位。**結論:用戶提出
  嘅呢個替代方案,一樣被同一個 snapshot-only 限制打死,唔可行。**
- **上市年期**(listing age)——技術上可行(第一筆價格數據日期已經有),但概念上同 Lynch/
  Arbel-Strebel 講嘅「未被關注」構念距離較遠(佢哋講緊嘅係 size/coverage neglect,唔係
  IPO recency;而且大部分 Lynch 案例都係老公司、唔係新股),加上呢個變數對單一股票係
  單調遞增、時間序列上冇「今日關注度高低」呢種可以反覆進出嘅狀態——決定唔用做主測試,
  留返做備注。
- **成交額/市值 turnover**(最終採用)——defeatbeta 有完整逐日成交量 + 收市價(全歷史),
  配合 `.insider_data/mktcap_defeatbeta.pkl`(已 cache 嘅市值序列,2627 隻 ticker、
  >=500 個交易日歷史),可以乾淨咁計 `trailing 63d 平均$成交額 / 市值`。呢個唔係「機構
  持股率」本身,但捕捉緊同一個底層構念嘅一部分——「呢隻股有幾多人喺主動交易/關注緊」——
  Lynch 嘅消防員/L'eggs 故仔講嘅都係「街上冇人講、冇人留意」,同低成交關注度係鄰近但
  唔完全相同嘅訊號。**呢個係本檔 backtest 用嘅 proxy,老實標注同真正機構持股率嘅distance。**

---

## 2. Backtest 方法(`backtest/experiments/exp_institutional_attention_proxy.py`)

- **Universe**:用返 repo 已有嘅 insider 項目 cache(`.insider_data/px_defeatbeta.pkl` /
  `mktcap_defeatbeta.pkl`),2627 隻 ticker(>=500 個交易日歷史)。**唔係 hand-picked**——
  按市值 tier(micro <$300M / small $300M-2B / mid $2B-10B / large >$10B,同
  `exp_families_mktcap_tiers.py` 一致嘅門檻)分層,每層系統性(字母序等距抽樣,唔係揀
  表現最好嗰啲)攞 75 隻,合共約 300 隻,**細價股冇被剔走**(符合 backtest-testing-standard
  memory)。
- **Turnover proxy**:`63d 平均$成交額 / 市值`(市值用 forward-fill 對齊落逐日)。
- **「關注度」狀態**:每隻股自己歷史(rolling 756 個交易日、最少 252)嘅 turnover 百分位
  排名(同 `exp_valuation_broad.py` 嘅 PE 百分位方法同一套慣例)——Q0=近期 turnover
  喺自己歷史嘅最低五分位(Lynch 講嘅「低關注」),Q4=最高五分位(擠)。
- **Forward excess return**(size-matched benchmark,對應 Arbel-Strebel「要喺控制 size
  後仍然顯著」嘅要求):每隻股每日嘅 forward return(63/126/252 個交易日),**減去同一
  日、同一個市值 tier 入面全部樣本股嘅等權重平均 forward return**——即係話「呢隻低關注股
  跑贏/跑輸嘅唔係因為佢細,而係喺同級數股票入面佢跑成點」。
- **統計檢定**:主測試 = 逐隻股票分別算「Q0 期間平均 excess return − Q4 期間平均 excess
  return」,再喺**跨股票**(N=股票數,唔係逐日觀測數)做 one-sample t-test——避免將
  重疊嘅逐日 forward-window 觀測當成互相獨立(pseudo-replication)。附帶 pooled 版本
  (逐觀測)做描述性參考,但明確標注呢個唔係主檢定。

---

## 3. 結果

**Universe/panel**:300 隻股票(micro 61/small 80/mid 75/large 69 隻,fetch 全部成功,
0 fail)、2016-01-04 至 2026-07-10、682,891 行 panel 觀測。

### 3.1 Part A(pooled、逐觀測)——原始數字有極端離群值污染,已用 winsorize 驗證修正

原始(未 winsorize)pooled quintile 平均 excess return:

| horizon | Q0(低關注) | Q1 | Q2 | Q3 | Q4(擠) | pooled spread Q0-Q4 |
|---|---|---|---|---|---|---|
| 63d  | +0.32% | -3.44% | -4.33% | -4.42% | **+9.01%** | -8.69pp |
| 126d | -2.35% | -6.69% | -7.07% | -5.53% | **+17.33%** | -19.68pp |
| 252d | -8.37% | -13.66% | -4.84% | -10.88% | **+33.87%** | -42.23pp |

**呢組數字表面睇好嚇人**(高關注 Q4 大幅跑贏、方向完全反 Lynch 假設),但每組
mean 同 median 差極遠——例如 252d Q4:mean=+33.87% 但 **median=-10.25%**,即係
話個 mean 完全由少數極端暴走股(可能係細價股單日/單季爆升,或者數據雜訊)拉高,
**唔可以直接讀做「高關注股平均跑贏」**。

**Winsorize(全 panel 逐 horizon 在 1%/99% 分位裁剪)之後重算**,pooled spread
**近乎消失**:

| horizon | winsorized pooled spread Q0-Q4 |
|---|---|
| 63d  | +0.02pp |
| 126d | +0.48pp |
| 252d | -1.15pp |

即係話 Part A 原始版本嘅「大幅負 spread、隨 horizon 拉長」純粹係離群值駕馭
(outlier-driven)嘅假象,唔係真實嘅、廣泛存在嘅 momentum/attention 效應。**呢個
本身係一個有用嘅方法論教訓**:turnover-based 排序喺細價股容易撞到單日/單季暴走
(reverse split、生技binary event、meme式炒作)污染 pooled mean,分析呢類 proxy
一定要做 winsorize/median 驗證,唔可以睇 pooled mean 就收工。

### 3.2 Part B(主測試)——逐股票 Q0-Q4 spread,跨股票 t-test(size/tier-matched)

**Winsorized 版本(穩健,呈報做主結果)**:

| horizon | N | mean(Q0-Q4 excess) | t | p | %股正 |
|---|---|---|---|---|---|
| 63d  | 285 | -0.13pp | -0.16 | 0.870 | 49% |
| 126d | 284 | +0.71pp | +0.48 | 0.633 | 52% |
| 252d | 284 | -2.63pp | -1.01 | 0.314 | 45% |

**全部三個 horizon 都唔顯著**(p 全部 >> 0.05),點估計正負都有、幅度細、%股正
貼近 50%(即係隨機)。**冇證據支持「低 turnover(低關注)跑贏同 tier 高 turnover
股」,亦都冇證據支持反過嚟嘅方向。**

分 tier 拆解(winsorized):

| tier | 63d t(p) | 126d t(p) | 252d t(p) |
|---|---|---|---|
| micro <$300M | -0.13 (0.90) | +0.75 (0.45) | -0.05 (0.96) |
| small $300M-2B | -0.61 (0.55) | -0.66 (0.51) | -1.67 (0.10) |
| mid $2B-10B | +1.29 (0.20) | +1.45 (0.15) | +1.40 (0.17) |
| large >$10B | -1.85 (0.07) | -1.69 (0.10) | **-2.18 (0.033)** |

**重要:呢張表本身就係一個「唔好過度解讀單一顯著結果」嘅示範**。未 winsorize 版本
入面,mid-cap 252d 曾經出現 p=0.044(當時解讀做「支持 Lynch 方向」);winsorize
之後,mid-cap 252d 變返唔顯著(p=0.166),反而係 **large-cap 252d 變成 p=0.033**
(方向仲要係反 Lynch——低關注跑輸)。兩個唔同嘅前處理方式,「邊個 tier/horizon
顯著」會轉軚——加上 4 tier × 3 horizon = 12 個子檢定、冇做 multiple-comparison
校正,單一 p<0.05 嘅出現率本身就同隨機噪聲一致(12 次獨立檢定,5% 顯著水平下預期
~0.6 次「顯著」)。**結論:呢啲子群組結果應該當雜訊睇,唔應該攞嚟做「發現咗個
角落 edge」嘅敘事。**

### 3.3 Part C——時期穩定性(pre-2021 vs 2021+,原始未 winsorize 版)

pooled spread Q0-Q4(126d horizon):pre-2021 = -39.04pp,2021+ = -4.60pp——
同 §3.1 一致,原始 pooled 數字本身已經對離群值極度敏感,呢個時期差異更可能反映
2016-2020 vs 2021+ 樣本入面離群暴走股嘅分佈唔同,而唔係一個穩定嘅 regime 轉變,
**唔獨立支持任何方向嘅結論**。

---

## 4. 結論同建議

### (a) 機構持股率呢個訊號而家喺 Karst 數據源下測唔測得到?

**測唔到**。yfinance `heldPercentInstitutions`/`numberOfAnalystOpinions` 兩個都
證實淨係 snapshot(原始碼追查,冇日期參數);defeatbeta 完全冇呢類欄位。SEC EDGAR
Form 13F bulk data 技術上載到足夠原始資料(已實測下載一份季度檔核實格式/大小),
但 CUSIP↔ticker 冇免費權威對照表,重建歷史機構持股率係一個獨立嘅多日工程項目,
唔喺呢次任務範圍內做。**用戶提出嘅「analyst coverage 數目」呢個替代方案,一樣被
證實係 snapshot-only,冚唪唥都測唔到。**

### (b) 如果測到(用 proxy),有冇 edge?

用**成交額/市值 turnover**做「市場關注度」proxy(唯一有乾淨完整歷史嘅相關變數),
喺 300 隻股(2016-2026、涵蓋 micro/small/mid/large 四個 tier、tier-matched size
control)做 backtest:**冇發現顯著 edge,任何方向都冇**。主測試(逐股票 Q0-Q4
spread 跨股票 t-test,winsorized)三個 horizon(3/6/12 個月)p 值全部 >0.3,分
tier 拆解出現嘅單一「顯著」結果喺 raw vs winsorized 兩種前處理之間會轉軚(唔穩定),
判定為 multiple-testing 雜訊,唔係真訊號。

**老實嘅但書**:turnover 唔係機構持股率本身,充其量係鄰近但唔完全相同嘅構念——
Arbel-Strebel 嘅 neglected-firm effect 原始文獻用嘅係 **analyst 追蹤人數**(研究
關注度),唔係交易活躍度(流動性/動量)。呢個 backtest 可以話係「低交易活躍度」
呢個具體假設冇支持,但**唔可以直接推翻 Lynch/Arbel-Strebel 講嘅『低機構持股率/低
analyst 追蹤』呢個原始構念**——因為冇測到嗰個構念本身,只測到一個鄰近 proxy。

### (c) 建議

**暫時擱置,唔好整合入 Phase-3 priced-in 閘**。三個理由:
1. 真正嘅構念(機構持股率/analyst 追蹤數嘅歷史序列)喺現有免費數據源下測唔到。
2. 唯一測得到嘅 proxy(turnover)搵唔到 edge(嚴謹 size-controlled 測試全部
   不顯著)。
3. 唔應該將一個測唔到假設本身、只測到鄰近 proxy 嘅 null result,包裝做「Lynch
   呢個 idea 已經測試過、冇用」——正確講法係「呢個構念而家測唔到,而佢嘅鄰近 proxy
   冇 edge」。

**如果日後想真正驗證呢個假設**,具體路徑(排優先序):
1. **SEC 13F CUSIP 解析項目**(獨立立項,唔好夾喺其他任務度做):針對 Phase-3
   實際覆蓋嘅 candidate universe(而唔係呢次隨機抽樣嘅 300 隻),人手/半自動解析
   CUSIP,下載 2013Q2 至今全部季度 INFOTABLE,重建歷史機構持股率 %。工作量評估:
   CUSIP 解析 + 下載/解壓/過濾 10-15GB 數據 + 對齊歷史流通股數,屬於多日工程。
2. 或者考慮**付費數據源**(WhaleWisdom/Fintel/WRDS 等已經做咗呢個 CUSIP 解析同
   歷史序列,如果 Karst 已經有訂閱其中一個,可以大幅跳過 §1.3 嘅工程瓶頸)。
3. 短期唔想開新項目嘅話,**維持現狀**——priced-in 閘繼續淨用 analyst
   coverage/OW rating 敘事做遲/擠端,唔加低端「未被發現」加分,直到有可靠嘅
   historical ownership/coverage 數據源為止。

---

## 產物

- 腳本:`backtest/experiments/exp_institutional_attention_proxy.py`
- Panel cache:`backtest/.insider_data/attention_panel.pkl`(300 股 × 2016-2026,
  可重用做其他 turnover-based 探針,唔使重新 fetch)
- 本檔:`backtest/results/2026-07-11_institutional_ownership_crowding_axis.md`
