# 結果 — BT-3/BT-4:AA-strict 結構內嘅單一機制增量(regime band / washout boost)

**日期:** 2026-07-13  **腳本:** `backtest/experiments/exp_bt3_bt4_increments.py`  **狀態:** active

## 動機同範圍

BT-2(`2026-07-12_bt2_aa_vs_core.md`)已證明 AA-strict 全主動「結構」喺風險調整後唔輸 core-v2 / SPY B&H,但佢個 delta-ledger 將兩個機制捆埋一齊計:(1) regime→band 表(按閘門狀態 1.15/0.925/0.0);(2) 設計文件第 3 節第 4 點嘅 breadth-washout 一次性 +5% NAV-delta LEAP boost。**機器覆核:grep `exp_bt2_aa_structure.py` 揾 "washout" 只有一個 hit — 檔案結尾嘅「Next」指針。washout boost 喺 BT-2 從未實作過。**本腳本逐個機制隔離其自身增量,AA-strict 機器其他一切鎖定不變。範圍:**只測 strict 變體、band=1.15 headline**(BT-2 自己推薦嘅格 — 其結論 #2);FULL 窗 + 壓力年份速查(冇 H1/H2 拆分 — 比 BT-2 本身嘅結構測試窄,見 Caveats)。`exp_bt2_aa_structure.py` 冇改過;下面嘅基線臂直接調用佢嘅 `simulate_aa`,未經修改。

## 方法(mirror / increment / horizon)

**Mirror(鏡像)**:同 BT-2 一模一樣嘅 AA-strict %-NAV 程序(防守 ballast + QQQ-beta thesis 替身 + 閘控 SPY/QQQ 0.50Δ LEAP overlay,由月度 delta ledger 定大細),對標 SPY B&H net-TR — 沿用 BT-2 嘅範圍限制(T sleeve = 零 alpha 嘅 QQQ-beta 替身;下面每個數都係「結構」結果)。
**Increment(增量)**:BT-3 只改 delta ledger 用嘅 `band` 值(regime 表 vs 鎖死 1.15)— 相對 `simulate_aa` 只有一行之差。BT-4 只改 ledger bar 上 breadth-washout 信號會唔會令 `leap_dn` 加 +5% — 只加新行,冇拆嘢。兩者都用 `simulate_aa_ext`(有文檔記錄嘅 BT2.simulate_aa 複製本);其忠實度由下面嘅等價自檢「證明」而非假設。
**Horizon(期限)**:同 BT-2 不變 — 月度 delta-ledger 節奏(每月首個交易日 + 強制 day-1),LEAP 63td roll,月中只有閘門自身嘅 T+1 出/入/roll 會觸發。

**Washout 信號(只用於 BT-4)**:原封不動重用 `exp_breadth_reversion.py` / `exp_breadth_reversion_verify.py` 嘅 `build_breadth()`/`episodes()` — 即 BT-B (`exp_bt_b_washout_expr.py`)用過嘅同一批函數。Mask = %above50 <= 自身歷史底 decile(p10=26.4%,a50 歷史 1994-11-30..2026-07-10);episode 以 gap=20td 去重(FINE 粒度,冇危機敘事式去重 — 機械觸發,唔係人手數件);入場 = episode 開始後 T+1(無前視);活躍窗 = 21 個交易日,之後歸位(階梯函數,唔係漸退)— **共 47 個 FINE episode,40 個入場點落喺 AA 窗內**(2001-01-23->2026-07-10)。

## 等價自檢(證明 `simulate_aa_ext` 係忠實複製)

`simulate_aa_ext(band_mode="regime", washout_active=None)` vs `BT2.simulate_aa`,完全相同輸入(base IV、strict、band=1.15):**PASS**(6397 個 bar 嘅最大 NAV 絕對差 = 0,容差 1e-6)。下面所有 ablation 數字都係對照「已驗證忠實」嘅 BT-2 引擎複製本量度。

## BT-3 — regime→band 增量(AA-strict,base/damp 並列)

| 臂 | IV | CAGR | Sharpe | MaxDD | β | Worst 12m | α vs SPY (t) |
|---|---|---|---|---|---|---|---|
| AA-strict 完整版(regime band,BT-2 原機)| base m0.85 | +15.4% | 0.89 | -44.2% | 0.85 | -36.1% | +7.5pp (t+5.0) |
| AA-strict 完整版(regime band,BT-2 原機)| damp 0.4 | +13.0% | 0.74 | -45.2% | 0.91 | -37.2% | +5.0pp (t+3.4) |
| AA-strict band 鎖死 @1.15(拆走 regime)| base m0.85 | +15.8% | 0.90 | -45.0% | 0.86 | -37.0% | +7.9pp (t+5.0) |
| AA-strict band 鎖死 @1.15(拆走 regime)| damp 0.4 | +13.2% | 0.73 | -46.3% | 0.94 | -38.4% | +5.0pp (t+3.2) |

**BT-3 增量(完整版 − 鎖死版,算術差)**:

| IV | ΔCAGR | ΔSharpe | ΔMaxDD | Δα (pp) | Δ 平均 alpha-capital share (pp) |
|---|---|---|---|---|---|
| base | -0.4pp | -0.01 | +0.8pp | -0.3pp | -0.7pp |
| damp | -0.2pp | +0.01 | +1.1pp | -0.0pp | n/a |

**配對價差顯著性**(long 完整版 / short 鎖死版嘅日報酬差,對 SPY 做 Jensen-alpha 以扣走 band 重新引入嘅任何 beta):base IV spread-α **-0.31pp (t-1.63, p=0.102, Bonf-FAIL)**;damp IV spread-α -0.04pp (t-0.18, p=0.86, Bonf-FAIL)— spread 對 SPY 嘅 beta:base -0.01、damp -0.02(Bonferroni×50,α<=0.00100,保守沿用 BT-2 registry 嘅門檻,唔另計 N)。

## BT-4 — washout boost 增量(AA-strict,base/damp 並列)

| 臂 | IV | CAGR | Sharpe | MaxDD | β | Worst 12m | α vs SPY (t) |
|---|---|---|---|---|---|---|---|
| AA-strict 完整版(無 boost,BT-2 原機)| base m0.85 | +15.4% | 0.89 | -44.2% | 0.85 | -36.1% | +7.5pp (t+5.0) |
| AA-strict 完整版(無 boost,BT-2 原機)| damp 0.4 | +13.0% | 0.74 | -45.2% | 0.91 | -37.2% | +5.0pp (t+3.4) |
| AA-strict + washout boost(+5% NAV delta,21td)| base m0.85 | +15.5% | 0.89 | -44.2% | 0.85 | -36.2% | +7.6pp (t+5.0) |
| AA-strict + washout boost(+5% NAV delta,21td)| damp 0.4 | +13.0% | 0.74 | -45.3% | 0.92 | -37.3% | +5.0pp (t+3.3) |

**BT-4 增量(加 boost 版 − 完整版,算術差)**:

| IV | ΔCAGR | ΔSharpe | ΔMaxDD | Δα (pp) | Δ 平均 alpha-capital share (pp) | boost 觸發(ledger bars)|
|---|---|---|---|---|---|---|
| base | +0.1pp | +0.00 | -0.1pp | +0.1pp | +0.1pp | 37 |
| damp | +0.0pp | -0.00 | -0.1pp | +0.0pp | n/a | n/a |

**配對價差顯著性**(long 加 boost 版 / short 完整版):base IV spread-α **+0.06pp (t+1.99, p=0.0471, Bonf-FAIL)**;damp IV spread-α +0.01pp (t+0.21, p=0.832, Bonf-FAIL)— spread 對 SPY 嘅 beta:base 0.00、damp 0.00(同 BT-3 一樣嘅 Bonferroni×50 門檻)。

## 資本效率讀數(base IV,FULL 窗)

| 臂 | Dn 中位 | Dn p90 | 平均 alpha-capital share | bailout | underfund | park (strict) | warm-up-zero | boost 觸發 |
|---|---|---|---|---|---|---|---|---|
| 完整版(regime band,無 boost)| 61% | 77% | 31.2% | 15 | 1 | 103 | 0 | 0 |
| BT-3 band 鎖死 | 71% | 84% | 32.0% | 15 | 6 | 103 | 0 | 0 |
| BT-4 加 washout boost | 62% | 79% | 31.3% | 15 | 2 | 103 | 0 | 37 |

## 壓力年份速查(CAGR,base IV)

| 臂 | FULL | 2008 | 2020 | 2022 |
|---|---|---|---|---|
| 完整版(regime band,無 boost)| +15.4% | -27.9% | +39.7% | -11.3% |
| BT-3 band 鎖死 | +15.8% | -28.9% | +41.0% | -11.6% |
| BT-4 加 washout boost | +15.5% | -27.9% | +39.9% | -11.3% |

## 數據來源

| 序列 | 來源 | 行數 | 起 | 迄 |
|---|---|---|---|---|
| ^IRX | yfinance | 16614 | 1960-01-04 | 2026-07-10 |
| SPY | yfinance | 8418 | 1993-01-29 | 2026-07-10 |
| SPY(adj) | yfinance(adj) | 8418 | 1993-01-29 | 2026-07-10 |
| ^VIX | yfinance | 9198 | 1990-01-02 | 2026-07-13 |
| QQQ | yfinance | 6876 | 1999-03-10 | 2026-07-10 |
| QQQ(adj) | yfinance(adj) | 6876 | 1999-03-10 | 2026-07-10 |
| ^VXN | yfinance | 6403 | 2001-01-23 | 2026-07-10 |
| XLP | yfinance | 6928 | 1998-12-22 | 2026-07-10 |
| XLP(adj) | yfinance(adj) | 6928 | 1998-12-22 | 2026-07-10 |
| XLU | yfinance | 6928 | 1998-12-22 | 2026-07-10 |
| XLU(adj) | yfinance(adj) | 6928 | 1998-12-22 | 2026-07-10 |
| XLV | yfinance | 6928 | 1998-12-22 | 2026-07-10 |
| XLV(adj) | yfinance(adj) | 6928 | 1998-12-22 | 2026-07-10 |

AA 共同窗:**2001-01-23 -> 2026-07-10(6397 日)** — 同 BT-2 一樣嘅構造;beta_B[0]=0.37、beta_T[0]=2.08,窗內 NaN-beta bar 數:0。

## Caveats

- **(範圍)只測 strict、band=1.15 headline**:BT-2 嘅完整 pragmatic×3-band 網格冇重跑;呢度係對贏家格嘅窄範圍針對性 ablation。方向「預期」對 pragmatic 都成立,但未驗證。
- **(a) washout boost 嘅月度節奏錯配**:AA ledger 只喺月初 bar resize(BT-2 自身 caveat (a),原樣繼承)。washout 信號每日計,但只喺 ledger bar 檢查 — 如果一個 episode 嘅整個 21 交易日活躍窗完全落喺兩個月初之間,佢就永遠唔會觸發。AA 窗內有 40 個 washout 入場點;boost 實際喺 37 個 ledger bar 觸發(base IV)— 兩個數之間嘅差就係呢個節奏錯配效應,如實披露,冇抹平。
- **(b) 兩個新臂冇計 DSR**:BT-2 將佢 6 個新 trial + 42 個舊 trial 餵入 `deflated_sharpe_ratio` 對照 48 格 Sharpe universe。為呢個窄增量測試重算嗰個 universe 超出範圍;呢度用 Bonferroni×50(0.05/50≈0.00104)做多重檢驗閘,同時應用於每臂自身 alpha-vs-SPY 以及(保守起見,沿用同一門檻而非另行推導)配對價差測試。
- **(c) washout boost 同現有 15% premium cap 相互作用**:+5% NAV-delta 加項同 `leap_dn` 其餘部分一樣受 `LEAP_CAP=0.15` premium 上限約束 — 如果 regime band 已經令 ledger 貼近上限,boost 會被部分或全部吸收、冇任何作用。呢點喺上面 Dn p90 / 平均 alpha-capital share 讀數度睇得到,冇隱藏。
- **(d) washout boost 觸發粒度**:用 FINE episode(gap=20td,冇危機級去重)做觸發 — 機械、非揀櫻桃嘅定義,同 BT-B 自身嘅 FINE 粒度一致,而唔係 BT-B headline 用嘅危機敘事 8-12 件事件數(嗰個對賬係俾人讀嘅顯示慣例,唔係「乜嘢先算有效一次性觸發」嘅實質要求)。
- **(e) LEAP/BSM 模型風險原樣繼承自 BT-2/core-v2**:^VIX/^VXN 30d→1y IV-proxy 不變,base(m0.85)/damp(0.4) 並列展示,冇揀櫻桃。
- **(f) 單一歷史路徑**、單一數據供應商(yfinance-first);冇 bootstrap。

## Cross-foot 驗證

- 5 次 `simulate_aa_ext` 會計運行(5 = 1 等價自檢 + 2 BT-3 + 2 BT-4),127,940 個 bar 級 assert 全部通過(同 BT-2 一樣:NAV=T+B+L+Parked+Cash / NAV>0 / Cash>=0 / Parked>=0 / 滾動恆等式,相對容差 1e-6)。2 次基線運行直接用 BT2.simulate_aa,帶 BT-2 自身嘅 assert(唔重複計入本檔 ASSERT_COUNT)。

## 結論

1. **BT-3(regime band)嘅 α 增量:不顯著(噪音級,≈零)**:完整版−鎖死版 base-IV CAGR -0.4pp、α 差 -0.3pp、MaxDD 差 +0.8pp;配對價差 base-IV α -0.31pp(t-1.63, p=0.102,未過 Bonferroni×50)。風險側讀數(唔入 α 檢驗,但係 regime band 存在嘅本意):MaxDD 差 +0.8pp、underfund 1 vs 6 次、Dn 中位 61% vs 71% — regime band 嘅實際作用係風險旋鈕(降槓桿/降尾部壓力),唔係 α 來源。
2. **BT-4(washout boost)嘅 α 增量:不顯著(噪音級,≈零)**:加 boost 版−完整版 base-IV CAGR +0.1pp、α 差 +0.1pp、MaxDD 差 -0.1pp;配對價差 base-IV α +0.06pp(t+1.99, p=0.0471,未過 Bonferroni×50);boost 喺窗內 307 個 ledger bar 之中觸發咗 37 個(窗內有 40 個 washout 入場點 — 差額係月度節奏漏接率,caveat (a))。
3. **遷移解讀**:上面判「正(顯著)」嘅組件先值得原樣帶入 live 設計;判「不顯著/負」即係嗰件複雜度喺呢條歷史路徑上冇賺到自己嘅位,冇進一步證據前唔應假設佢加值(佢仍可能因為呢個 sim 睇唔到嘅理由值得保留 — 例如 Jensen alpha 捕捉唔到嘅尾部風險框架 — 但嗰個係另一個論證,唔係回測增量)。
