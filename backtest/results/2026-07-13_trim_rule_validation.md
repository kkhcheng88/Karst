# 獲利回收 trim 規則 —— 前瞻追蹤(Part A)+ 歷史回溯初驗(Part B)

**日期**: 2026-07-13
**規則**(Fable 交接書 P2-15,backlog item 15):擁擠複合 top decile(composite_pctile ≥90)+ 倉位 ≥2×
成本(entry)→ trim 1/3
**腳本**:
- Part A(前瞻,已上線):`thesis/trim_rule_tracker.py`(`--status` 印今日判定,觸發先寫 log,唔郁台帳)
- Part B(歷史,本次初驗):`backtest/experiments/exp_trim_rule_backtest.py`(可重跑,PYTHONUTF8=1)
**背景**:兩個前置(擁擠複合 `thesis/crowding_composite.py`、紙上台帳 `thesis/paper_ledger.json`)
2026-07-13 先啱啱到位,規則本身有冇用要 paper 記錄一段時間先知(track-record-before-adopt 原則)。
上一個 agent 因 session 限額中斷,留低兩個已 compile 但未實跑嘅 script;本次任務 = 審查 → 實跑 →
出結果。

---

## [結論]

1. **兩個 script 審查後冇發現 bug,唔使修改,原樣實跑成功**——所有引用嘅 sibling 函數
   (`beta_check.build_basket`、`crowding_composite.attendance_series`/`MIN_QUARTERS`、
   `data.load`)簽名同 schema 全部核對相符,`paper_ledger.json` 嘅純複利假設(冇 entry_pct 欄位、
   `current_pct(t) = entry_pct × cum_basket_ratio`)喺 `paper_ledger.py` `cmd_update()` 原始碼
   逐行核實成立。`.gitignore` 現有 `thesis/.raw/**/*.jsonl` 規則已覆蓋 `trim_rule_log.jsonl`,
   唔使加新規則。
2. **Part A 今日判定:0 個 theme 觸發**——3 個 theme(glp1-biologics-packaging 95.3、
   rare-earth-materials 97.8、specialty-siding-pricing-power 97.2)composite_pctile 已達 top
   decile,但台帳 2026-07-13 先啱初始化,全部 `position_multiple` ≈ 1.00x,遠低於 2x 門檻。呢個
   係機制設計內嘅誠實結果,唔係腳本壞咗。台帳、log 檔案本次執行後零改動(見〔證據〕確認)。
3. **Part B 歷史回溯結論:冇增量(且方向上有蝕章跡象)**——用 attendance-percentile 單輸入代理
   套落 1148 個歷史「2x 成本」事件(15 個 theme、68 隻 ticker):
   - 大樣本(pooled,有 overlapping-window 自相關)喺 63 交易日 horizon 出現「顯著」差距,但方向
     **同 trim 假設相反**——TRIGGER 組跑贏 NOTRIGGER 組(+40~48% vs +10~12%,Welch-t≈2.7~2.8),
     由 2021 年後嘅事件主導。
   - 去自相關嘅 DECLUSTERED 版本(樣本細但唔受 rolling-window overlap 污染,2016+ TRIGGER n=10)
     喺三個 horizon 全部唔顯著(t=0.68 / 0.05 / -1.13),訊號基本消失。
   - 前後半正負號唔一致:2016-2020(n=7)方向同 trim 假設一致但樣本太細(126d t=-4.08 睇落
     「顯著」但 n=7 唔可信);2021+(n=30)喺 63d 反而大幅跑贏。
   - 資本效率角度:喺 TRIGGER 事件套用 trim 1/3,對照純揸到尾,**贏率淨 35-42%**(pooled 2016+),
     即係話用呢個代理觸發 trim,歷史上多數時間會蝕章冇 trim 嘅選擇好。
4. **不建議單憑呢個 attendance-only 代理去自動化 trim 決策**——現有證據未能證明規則有正向增量,
   反而喺唯一有統計力嘅短 horizon 讀數方向相反。Part A 嘅前瞻 paper 追蹤機制本身設計冇問題(唔
   自動執行,人審核),可以繼續行;但佢驗證緊嘅係 3-輸入完整複合(attendance+gs_flow+bull_ratio),
   同呢度回測嘅單一 attendance 代理唔完全同一訊號——建議台帳累積夠 paper 樣本後,連同前瞻 log
   一齊重新評估,唔好淨憑呢份歷史回溯就永久否決條規則。
5. **代理限制要記住**(下面〔未解/風險〕詳列):attendance-only(非完整複合)、themes.yaml 現存
   籃子套落歷史有適用性+生存者偏差、rolling entry 唔係真實歷史交易、冇交易成本、declustered 樣本
   細(n=8-10)。

---

## [證據]

### Part A —— 今日判定(2026-07-13,`python thesis/trim_rule_tracker.py --status` 原文輸出)

觸發條件:composite_pctile ≥ 90 AND position_multiple ≥ 2.0x

| theme | composite | mult | triggered |
|---|---:|---:|---|
| specialty-siding-pricing-power | 97.2 | 1.00x | - |
| rare-earth-materials | 97.8 | 1.00x | - |
| glp1-biologics-packaging | 95.3 | 1.00x | - |
| gas-compression-equipment | 88.9 | 1.00x | - |
| aerospace-specialty-alloys | 78.6 | 1.00x | - |
| us-solar-manufacturing | 76.0 | 1.00x | - |
| oil-gas-energy | 67.8 | 1.00x | - |
| space-satellite | 59.9 | 1.00x | - |
| photonics-optical | 57.1 | 1.00x | - |
| advanced-packaging | 48.1 | 1.00x | - |
| tpu-custom-silicon | 46.5 | 1.00x | - |
| semicap-equipment | 40.7 | 1.00x | - |
| ai-power-grid | 34.3 | 1.00x | - |
| memory-supercycle | 24.8 | 1.00x | - |
| euv-lithography-monopoly | 2.8 | 1.00x | - |

今日判定:**無觸發**(0/15)。全部 `position_multiple ≈ 1.00x`(台帳今日先初始化)。
確認冇副作用:`git diff --stat thesis/paper_ledger.json` 空白(台帳未改);
`thesis/.raw/trim_rule_log.jsonl` 唔存在(冇觸發,冇寫 log,符合設計)。

### Part B —— 覆蓋範圍(15 active theme,68 隻 unique ticker)

| theme | tickers | loaded | pit覆蓋 | 歷史起 | 歷史迄 | rolling entries | 2x事件 |
|---|---:|---:|---:|---|---|---:|---:|
| advanced-packaging | 13 | 13 | 13 | 1973-02-22 | 2026-07-10 | 107 | 107 |
| aerospace-specialty-alloys | 2 | 2 | 2 | 1973-02-22 | 2026-07-10 | 107 | 106 |
| ai-power-grid | 14 | 14 | 14 | 1962-01-03 | 2026-07-10 | 129 | 128 |
| euv-lithography-monopoly | 1 | 1 | 1 | 1995-03-16 | 2026-07-10 | 63 | 62 |
| gas-compression-equipment | 1 | 1 | 1 | 2013-01-16 | 2026-07-10 | 27 | 20 |
| glp1-biologics-packaging | 1 | 1 | 1 | 1980-03-18 | 2026-07-10 | 93 | 81 |
| memory-supercycle | 4 | 3 | 2 | 1978-11-01 | 2026-07-10 | 96 | 96 |
| oil-gas-energy | 7 | 7 | 7 | 1962-01-03 | 2026-07-10 | 129 | 126 |
| photonics-optical | 9 | 8 | 7 | 1982-01-04 | 2026-07-10 | 90 | 89 |
| rare-earth-materials | 2 | 2 | 1 | 2020-06-23 | 2026-07-10 | 13 | 11 |
| semicap-equipment | 1 | 1 | 1 | 1997-08-18 | 2026-07-10 | 58 | 58 |
| space-satellite | 10 | 10 | 9 | 1980-03-18 | 2026-07-10 | 93 | 92 |
| specialty-siding-pricing-power | 1 | 1 | 1 | 1980-03-18 | 2026-07-10 | 93 | 86 |
| tpu-custom-silicon | 3 | 3 | 3 | 1997-10-10 | 2026-07-10 | 58 | 56 |
| us-solar-manufacturing | 1 | 1 | 1 | 2006-11-20 | 2026-07-10 | 40 | 30 |

TOTAL 歷史 2x 成本事件(raw,overlapping):**1148**。crowding 可計:586(TRIGGER≥90pctile:47,
NOTRIGGER<90:539,insufficient_data:562 — attendance-only 代理 + `MIN_QUARTERS=8` 篩走一半事件,
誠實反映代理覆蓋率有限)。DECLUSTERED(同 theme cross_date 63 個交易日內只留最早一個):429。

### POOLED(raw,overlapping)—— 全歷史

| h | TRIG n | mean% | med% | mdd% | NOTRIG n | mean% | med% | mdd% | Welch-t |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 63 | 46 | +40.4% | +22.3% | -31.5% | 528 | +10.1% | +6.2% | -15.5% | **2.76** |
| 126 | 46 | +14.4% | +6.3% | -42.7% | 513 | +22.9% | +13.0% | -20.8% | -1.24 |
| 252 | 40 | +20.5% | +12.8% | -51.9% | 476 | +26.3% | +21.9% | -27.3% | -0.69 |

### POOLED —— 2016+ headline window,前後半

**POOLED 2016+**(TRIG=38,NOTRIG=378)

| h | TRIG n | mean% | med% | mdd% | NOTRIG n | mean% | med% | mdd% | Welch-t |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 63 | 37 | +48.0% | +29.4% | -33.0% | 367 | +11.6% | +6.8% | -17.5% | **2.74** |
| 126 | 37 | +17.6% | +8.1% | -46.4% | 352 | +28.1% | +15.4% | -23.1% | -1.24 |
| 252 | 31 | +25.0% | +17.8% | -56.8% | 315 | +30.0% | +26.3% | -29.3% | -0.48 |

**2016-01-01 至 2020-12-31(前半,TRIG n=7 極細)**

| h | TRIG mean% | NOTRIG mean% | Welch-t |
|---:|---:|---:|---:|
| 63 | -1.5% | +4.1% | -1.84 |
| 126 | +0.3% | +16.0% | -4.08 |
| 252 | +12.6% | +27.6% | -1.98 |

**2021-01-01 起(後半,TRIG n=30)**

| h | TRIG mean% | NOTRIG mean% | Welch-t |
|---:|---:|---:|---:|
| 63 | +59.6% | +16.1% | **2.76** |
| 126 | +21.6% | +35.9% | -1.31 |
| 252 | +28.6% | +31.8% | -0.24 |

前後半方向唔一致:前半 63d/126d/252d 全部 TRIGGER 跑輸(同 trim 假設一致,但 n=7 太細唔可信);
後半 63d TRIGGER 大幅跑贏(t=2.76,同 trim 假設相反),126d/252d 轉為輕微跑輸但唔顯著。

### DECLUSTERED(去自相關,robustness)—— 2016+(TRIG n=10,NOTRIG n=122)

| h | TRIG n | mean% | med% | mdd% | NOTRIG n | mean% | med% | mdd% | Welch-t |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 63 | 9 | +29.5% | +1.1% | -21.6% | 117 | +12.0% | +9.2% | -15.9% | 0.68 |
| 126 | 9 | +26.5% | +8.8% | -26.6% | 110 | +25.8% | +17.6% | -21.8% | 0.05 |
| 252 | 8 | +22.6% | +21.6% | -36.8% | 100 | +37.1% | +28.8% | -29.4% | -1.13 |

去除 rolling-window overlap 帶嚟嘅自相關後,POOLED 版本嗰個「顯著」63d 差距完全消失
(t 由 2.74 跌到 0.68);252d 雖然數值上 TRIGGER 較低(22.6% vs 37.1%),但 n=8 太細,t=-1.13
唔顯著。

### 資本效率(TRIM 1/3 realized + 0% 閒置現金 vs HOLD,TRIGGER 事件,2016+ pooled)

| h | n | HOLD mean% | TRIM mean% | diff(TRIM-HOLD) | TRIM 贏率 |
|---:|---:|---:|---:|---:|---:|
| 63 | 37 | +48.0% | +32.0% | -16.0pp | 35% |
| 126 | 37 | +17.6% | +11.7% | -5.9pp | 35% |
| 252 | 31 | +25.0% | +16.6% | -8.3pp | 42% |

diff 代數上等於 `-1/3 × fwd_ret`(閒置現金 0% 回報係保守假設,若閒置資金另有用途 TRIM 相對優勢
只會更強唔會更弱);真正嘅實證問題係 TRIGGER 同 NOTRIGGER 嘅 forward-return 分佈有冇分別
(上面幾個表),唔係呢個 $ 轉換本身。喺呢個歷史集,TRIM 嘅贏率只有 35-42%,即係話套用呢條規則
嘅歷史結果多數時間差過揸到尾。

---

## [產物]

- `C:\projects\Investment\Karst\thesis\trim_rule_tracker.py` —— Part A 前瞻追蹤(審查後原樣,冇改動)
- `C:\projects\Investment\Karst\backtest\experiments\exp_trim_rule_backtest.py` —— Part B 歷史回溯
  (審查後原樣,冇改動)
- `C:\projects\Investment\Karst\backtest\results\2026-07-13_trim_rule_validation.md` —— 本報告
- `C:\projects\Investment\Karst\thesis\.raw\trim_rule_log.jsonl` —— 本次未產生(今日 0 觸發,符合
  idempotent 設計)
- `C:\projects\Investment\Karst\backtest\.insider_data\trim_rule_backtest_cache.pkl` —— Part B 磁碟
  快取(point-in-time attendance + close price 快取,已 `.gitignore`,可重跑重建)
- 台帳 `thesis\paper_ledger.json` 本次執行**零改動**(已用 `git diff --stat` 核實)

---

## [未解/風險]

1. **代理限制(繼承自 crowding_composite.py 已披露限制,回測再收緊一層)**:今日 dashboard 用嘅
   composite_pctile 有 3 個輸入(attendance/gs_flow/bull_ratio),但 bull_ratio 冇歷史時序、
   gs_flow 完全冇數據源,所以呢份歷史回溯**淨用 attendance percentile 單輸入**做代理——結論
   「冇增量」係針對呢個代理嘅讀數,唔係針對今日 3-輸入完整複合。若果 composite 嘅其餘兩軸未來
   有歷史時序,值得重跑。
2. **DECLUSTERED 樣本細**:2016+ 去自相關後 TRIGGER 淨得 n=8-10 個真正獨立事件(15 個 theme
   × 5.5 年),統計力有限。「冇增量」係「未搵到可信嘅正向增量」,唔係「證明咗規則完全冇用」——
   絕對唔可以排除細樣本掩蓋咗真訊號嘅可能。
3. **適用性 + 生存者偏差**:basket = themes.yaml 現存(2026-07 定案)嘅 15 個 theme/68 隻
   ticker,套落 1962-2026 嘅歷史——呢啲 theme 分類喺歷史大部分年份根本未存在,且 2026 年仲喺
   名單入面嘅先會入呢個回測(冇資格但已經消失/被收購嘅 ticker 唔會出現)。
4. **rolling entry 唔係真實歷史交易**:台帳 2026-07-13 先開倉,冇歷史成本可用,用每 126 個交易日
   一個模擬進場點模擬「隨便邊個時間點買入,啱好升咗 2x」嘅情境——呢啲時間點唔係策略歷史上真係
   買入過嘅日子。
5. **冇交易成本**:呢個係 event-return 對比,唔係可執行 PnL;實際執行仲要計入 slippage/稅務等。
6. **euv-lithography-monopoly(ASML)資料品質已知問題**(見 `2026-07-13_crowding_composite.md`
   〔未解/風險〕#1):最近 3 季 transcript 喺 corpus.db 疑似投資者日節錄非標準法人電話會議,令呢個
   theme 最新幾個事件嘅 attendance 讀數失真(偏低)。呢個 theme 只有 1 隻 ticker、62 個事件,對
   pooled 總數(1148)影響有限,但不排除拖低該 theme 個別事件嘅 crowd_pctile。
7. **前後半正負號唔一致嘅根因未深挖**:後半(2021+)63d TRIGGER 大幅跑贏,可能同「擠迫+已經
   2x」喺呢個 AI/materials 主題週期入面本身就係動能延續訊號(唔係頂部訊號)有關,但呢個假設未經
   額外驗證(例如分拆邊幾個 theme/ticker 主導咗後半嘅 outlier),留待下次有更完整代理時一併深挖。
