# Insider 群買(cluster-buy)做「主題發現」早期訊號 — 探測(2026-07-08)

**⚠️ 發現訊號探測(discovery-signal probe),非交易訊號回測。** WS4(早期偵測)任務:
insider 群買喺同板塊/價值鏈跨公司短窗共振,可唔可以做「有嘢喺度發生」嘅質性研究提示。
腳本:`backtest/experiments/exp_insider_sector_cluster.py`。全程離線,複用已下載嘅 SEC bulk
Form 345 archive(`backtest/.insider_data`,78 季 2006q1–2025q2),冇重拉。

## 1. 數據盤點

- `thesis/insider_cache.json`(EDGAR、目前快照):52 隻 ticker,180d rolling window,asof
  2026-07-05(`thesis/insider_edgar.py` 產生)。呢個 cache 係「now」快照,唔夠做歷史 cluster
  頻率統計。
- SEC bulk Form 345 archive(`backtest/.insider_data`):**78 季齊全(2006q1–2025q2),已離線
  cache**(前次 `exp_insider_extended.py` 已驗證:18,751 個(舊定義)cluster 事件 / 6,766
  tickers / 9,997 有價)。本探測複用呢個 archive,套用更嚴嘅定義(≥3 insider、>$250k,對比
  舊版 ≥2/$500k),再疊 `thesis/themes.yaml` 嘅板塊/價值鏈分組(8 個 theme,≥2 tickers)。
  2025q3+ 未有(SEC bulk 遲 1–2 季)。
- **關鍵盤點結果:memory-supercycle theme(MU/SNDK/WDC/DRAM/SKHY)喺 2016q1–2025q2 幾乎冇
  insider 買入活動**——全部 5 隻 ticker 合計只有 **4 個 P-buy 日**(MU×2、WDC×1、DRAM×1),
  遠低於做 cluster 統計嘅門檻。**呢個 theme 唔係「訊號未 fire」,而係「冇料可 fire」**——
  大型半導體公司(MU/WDC)insider open-market 買入本身罕見,SKHY(SK 海力士 ADR)2026-07-10
  先掛牌、未有歷史。ai-power-grid theme(GEV/BE/VRT/ETN/PWR/MPWR/VICR/NVTS/WOLF/ON)數據
  充足(54 個 P-buy 日,集中喺 WOLF 14 次、ETN 11 次),但唔夠密集到觸發「≥2 公司同窗」。

## 2. Cluster 定義網格(pre-registered)— 每年 fire 幾多次

定義:per-company cluster = ≥N 個唔同 insider(N∈{2,3})、僅 open-market P-buy(10b5-1 剔除)、
總額 >$250k、within window W(W∈{21,42} 交易日);theme-cluster fire = 同一 `themes.yaml`
board 內 ≥2 間唔同公司,個別 company-cluster 日期喺 W 內。2016q1–2025q2(38 季),8 個 theme。

| N(insiders) | W(日) | company-cluster 事件數 | theme-fire 總數 | fires/年(mean) | 0-fire 年份 | >6-fire 年份 |
|---|---|---|---|---|---|---|
| 3 | 21 | 11,863 | 1 | 0.10 | 9/10 | 0/10 |
| 3 | 42 | 11,424 | 3 | 0.30 | 7/10 | 0/10 |
| 2 | 21 | 15,129 | 4 | 0.40 | 7/10 | 0/10 |
| 2 | 42 | 14,299 | 7 | 0.70 | 4/10 | 0/10 |

**任何一格都遠低於「0-6 次/年」帶嘅可用下限**——技術上落喺帶內(<6),但實際上太罕
(4/10 年一次都冇 fire),**唔夠做日常監測訊號**。放寬到 N=2/W=42(最鬆一格)都只係
0.7 次/年,而且集中喺 3 個 theme(oil-gas-energy 4 次、advanced-packaging 2 次、
space-satellite 1 次)——**memory-supercycle 同 ai-power-grid 兩個 theme 全程 ZERO fire**
(全部 4 個定義組合、全 10 年)。

7 個 fire(N=2/W=42,最鬆定義)全列:

| 日期 | theme | 公司 |
|---|---|---|
| 2016-08-03 | oil-gas-energy | COP, LNG |
| 2017-08-17 | oil-gas-energy | EQT, LNG |
| 2018-11-15 | oil-gas-energy | EQT, LNG |
| 2018-12-10 | advanced-packaging | INTC, STX |
| 2020-03-05 | oil-gas-energy | CVX, LNG |
| 2022-02-24 | advanced-packaging | AMKR, INTC |
| 2024-04-29 | space-satellite | GSAT, LOAR |

## 3. 案例回溯(indicative,非回測)— 之後 6-12 個月發生咗乜

Forward excess return vs SPY,呢 7 個 fire 嘅相關 tickers(21d/63d/126d/252d):

| Fire | Ticker | 21d | 63d | 126d | 252d | 事後解讀 |
|---|---|---|---|---|---|---|
| 2016-08 oil/gas | COP | +0.2% | +10.4% | +15.4% | −2.8% | 油價 2016 底部反彈,中期跟得上 |
| | LNG | +4.1% | −5.8% | +15.6% | −4.6% | 同上,雜訊大 |
| 2017-08 EQT/LNG | EQT | +2.6% | −8.0% | −26.3% | −36.1% | **反訊號**——天然氣熊市持續 |
| | LNG | +4.4% | +14.5% | +28.2% | +32.8% | 贏家,同組 EQT 輸家——同 theme 內分歧大 |
| 2018-11 EQT/LNG | EQT | +16.3% | +10.5% | +19.8% | **−58.1%** | 短期贏、252d 崩(2019 氣價崩盤) |
| | LNG | +2.7% | +6.6% | +5.6% | −14.7% | 短期小贏、長期輸 |
| 2018-12 INTC/STX | INTC | +4.8% | +8.6% | −11.1% | +1.1% | 雜訊,無方向 |
| | STX | +3.9% | +13.2% | +0.4% | **+26.0%** | 贏家 |
| 2020-03 CVX/LNG | CVX | −4.8% | −3.9% | −32.7% | −14.7% | COVID 崩盤底,插入時機差(仲跌緊) |
| | LNG | −12.0% | +2.4% | −0.2% | +31.2% | 252d 反彈返贏 |
| 2022-02 AMKR/INTC | AMKR | −2.8% | −10.8% | −3.7% | +17.7% | 短輸長贏 |
| | INTC | +5.2% | −2.5% | **−23.3%** | **−39.6%** | **反訊號**——2022-23 INTC 結構性衰退 |
| 2024-04 GSAT/LOAR | GSAT | −18.5% | −14.0% | −29.3% | −8.6% | **反訊號**,全期落後 |
| | LOAR | +10.5% | +14.3% | **+60.4%** | **+80.8%** | 大贏家——但 LOAR 2024-04 啱啱 IPO,insider 買入可能係創辦人/PE 贊助人 post-IPO 慣常持股行為,非獨立買入訊號 |

**讀法:mixed,冇一致方向**——同一個 fire 內兩隻股經常一贏一輸(2017/2018 EQT vs LNG、
2022 AMKR vs INTC、2024 GSAT vs LOAR),即「theme co-buy」本身冇提供邊個會贏嘅資訊,
同單一大盤股 insider 短線訊號(`2026-07-05_insider_rigor.md` 已證:大型股 21d 有真訊號但
regime-specific、126d+ 反轉)嘅弱點一致。LOAR 個案仲有 IPO 誤判風險。

### 「早唔早過敘事」關鍵測試:記憶體/電力鏈 2024-25

**結果:呢個定義完全冇喺 memory-supercycle 或 ai-power-grid 兩個 theme fire 過(全部
4 個定義組合、2016–2025q2 全期都係 zero)。** 唔存在「早過 gooptions 敘事」嘅事件可以驗證
——因為個 signal 根本冇 fire。追查原因:
- memory-supercycle:**冇料**(5 隻股合計 10 年得 4 個 P-buy 日,見 §1)。
- ai-power-grid:**有料但唔夠密**——54 個 P-buy 日入面,不用「cluster」(≥2 insider per
  company)嘅門檻,單純睇「任何一個 insider 買入」跨公司共振,exploratory 一眼見到
  **2022-11-04(VRT,1 insider)同 2022-11-21(WOLF,1 insider)相距 17 日**——落喺 42d
  window 但因為淨係單一 insider(唔夠 N≥2)所以未被計入正式 fire 清單。呢個時點(2022 尾)
  比 AI 電力敘事主流化(2024 起)早接近 18 個月,但證據太薄(1 insider、金額細)唔構成
  可信訊號,只係一個「值得標記但唔可信」嘅雜訊點。
- **對照組(同一 repo 早前嘅 WS4 探測)**:`exp_constraint_language.py`(財報電話會「供給
  受限語言」掃描,2026-07-08_constraint_language_probe.md)喺**同一個 memory 鏈(MU)**用
  完全唔同嘅數據源(transcript 語言),真係搵到早過敘事嘅訊號(FY2024Q1 早 ≈17 個月、
  FY2025Q4 早 ≈8 個月)。**呢個對照直接話畀我哋知:insider cluster 唔係呢條鏈嘅早期偵測
  管道(數據太薄),transcript 語言先係。**

## 4. 落地規格建議

**唔建議做日常 job。** 理由排序:
1. 網格全部 4 個定義都 <1 fire/年,而且 2 個核心 AI 主題(memory/power)zero-fire——呢個
   probe 嘅「板塊/價值鏈」分組粒度(`themes.yaml` 2-13 隻股/theme)太細,insider open-market
   買入本身罕見(大型股尤甚),交叉相乘之後幾乎唔會撞。
2. 有 fire 嗰 7 次案例回溯 mixed(同組兩隻股經常一贏一輸),冇一致方向可用嚟做「即刻去邊度
   做研究」嘅可信提示——訊噪比太低。
3. 唯一一個有意義嘅早期共振(VRT/WOLF 2022-11)喺放寬到「單一 insider 都計」先浮現,但單
   insider 訊號本身喺 `2026-07-05_insider_rigor.md` 已經證實唔可信(細價股 lottery、大型股
   regime-specific)。

**如果將來要重試,呢啲改動先值得做(而家唔做):**
- 唔用 `themes.yaml`(too narrow, too few names/theme),改用真.GICS sub-industry(標普
  full universe)做分組——樣本大好多,先有機會撞出有意義嘅頻率。
- 唔用「≥2/3 insider」呢個嚴格 per-company cluster 門檻,改用「任何 open-market P-buy,
  總額門檻」(呢次 exploratory 已顯示放寬先有 hit,但要另外做嚴謹嘅事後統計驗證,唔淨係
  眼睇)。
- 如果真係要做,接去邊:**唔係 daily job**,应该係低頻(季度)batch 掃描,寫入
  `docs/_PENDING_ANALYSIS.md`(或類似隊列)做「值得質性覆核」嘅 flag,而非自動化訊號
  ——同 thesis layer 嘅 NHITL 設計一致(insider cluster 呢度只可以做「去邊度睇」嘅提示,
  唔可以做「confidence」輸入)。

## 結論

**Insider 群買跨公司(同板塊/價值鏈)共振,喺呢個 pre-registered 定義網格下,唔係一個
可用嘅主題發現早期訊號**:(1) 觸發頻率太低(全部定義 <1 次/年,兩個核心 AI 主題 zero-fire);
(2) 觸發時案例回溯方向不一致;(3) memory/power 鏈嘅「早過敘事」測試冇得做(冇 fire),而
同一 repo 已證實嘅 transcript 語言訊號(`2026-07-08_constraint_language_probe.md`)喺同一
memory 鏈度確實搵到早期訊號——即早期偵測嘅有效管道係 transcript,唔係 insider cluster。
維持 disciplined negative,唔建 daily job。

## Reproduce

`python backtest/experiments/exp_insider_sector_cluster.py`(離線,複用
`backtest/.insider_data` 已 cache 嘅 78 季 SEC bulk zip;產生
`backtest/experiments/_sector_cluster_fires.json` 做逐格 fire 清單)。
