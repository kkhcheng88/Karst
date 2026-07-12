# Result — BT-7: ballast (defensive sleeve) definition comparison — B1 XLP/XLU/XLV vs 5 pre-registered alternatives (incl. 1 negative control)

**Date:** 2026-07-13  **Script:** `backtest/experiments/exp_bt7_ballast_def.py`  **Status:** active

## Question

Karst-AA 設計（`docs/2026-07-12_all_active_design_response.md` §2.3/§8c）目前將 ballast（防守／壓艙 sleeve）定義死做 XLP/XLU/XLV 等權。用戶追問：「防守」應該點定義？要唔要機制／擇時？§8c 已經預先註冊呢個 BT-7 測試：候選 basket 按「職責達成度」對比（唔係鬥靚回報擇優）。任務中途用戶再加兩個候選：B5 DIA（正式提名，非對照）、B6 Mag7 月度 rebalance 合成組合（明文標示反面對照組，示範「offense 資產擺 ballast 位」嘅代價）。

## Method

- **候選（預先註冊，六個，唔准再加減）**：
  - B1 = XLP/XLU/XLV 等權（現行）
  - B2 = B1 + USMV 等權（加 min-vol 因子）
  - B3 = B1 + VIG 等權（加股息增長因子——原稿 B3 係五隻 XLP/XLU/XLV/VIG/XLRE，因 XLRE 2015-10 先上市窗太短、GLD「唔係股票，違反非零 beta equity mandate」被拒，喺 prompt 已更正做四隻版）
  - B4 = USMV 單獨（純 min-vol、低息、稅務效率極端案例）
  - B5 = DIA 單獨（**正式提名候選**——假設：低息過 trio 稅漏細、科技含量低過 SPY 對 QQQ 相關應該低啲、2022 型加息市可能係強項——全部用數證實或推翻，唔假設）
  - B6 = Mag7 等權月度 rebalance 合成組合（AAPL/MSFT/GOOGL/AMZN/NVDA/META/TSLA；自砌因 MAGS ETF 2023 年先上市，數據太短；**明文負面對照組**，預期喺 downside capture、QQQ 相關兩項判官大敗——收錄目的係量化示範「offense 資產擺 ballast 位會點」，唔係真落選候選）
- **Mirror/Increment/Horizon**：B1-B5 靜態長倉等權、逐日重平衡 buy-and-hold（唔係 200SMA 閘控嘅停泊研究，BT-7 問「邊個籃子先係防守」，唔係「幾時泊入去」）；B6 因為係集中 7 隻大型股嘅合成組合，逐日重平唔現實，改用**月度 rebalance**（首個交易日重設等權，月內權重隨價格自然漂移）——呢個係 B1-B5 同 B6 之間，喺重平頻率呢個維度上，刻意唔一致嘅一點，因為兩者本身資產性質唔同（ETF 籃子 vs 集中股票組合），見 Caveats。
- **HK 稅**：全部候選用 repo 標準 `r_net = r_adj - 0.30*dy`（1bp 門檻殺 adjustment 捨入雜訊），同 `exp_ballast_parking.py` 完全一致嘅公式。

## 共同窗口聲明（Common-window discipline — 硬性約束）

USMV 2011-10-20、VIG 2006-05-02、XLP/XLU/XLV 1998-12-22、DIA 1998-01-20、META 2012-05-18（Mag7 七隻入面上市最遲，係 B6 窗口嘅硬約束）上市——全部由 `data.load()` 實測，唔係假設。連續型聚合指標（downside capture／QQQ 相關／HK淨 CAGR／稅漏／Sharpe／MaxDD／beta）**一律喺「League」共同窗口計，B1 每次都喺嗰個窗重新計一份做錨**：
- **League A（USMV 窗）** = XLP∩XLU∩XLV∩USMV = 2011-10-21 → 2026-07-10（3699 個交易日），含 {B1(錨), B2, B4, B5}。
- **League B（VIG 窗）** = XLP∩XLU∩XLV∩VIG = 2006-05-03 → 2026-07-10（5078 個交易日），含 {B1(錨), B3, B5}。
- **League C（Mag7 窗）** = XLP∩XLU∩XLV∩Mag7(7隻) = 2012-05-21 → 2026-07-10（3554 個交易日），含 {B1(錨), B5, B6}——B5 (DIA) 歷史最長，喺三個 league 都唔係約束者，先可以合法咁同時出現喺三個 league 度同 B1 錨逐一對比。
- B2/B4 同 B3/B6 **從無直接對比**（唔同窗口）——排名淨係喺各自 league 入面同 B1 錨做；B5 因為歷史夠長，係唯一喺三個 league 都有齊數嘅非錨候選。
- 三個壓力窗（judge 2）例外：用固定絕對日期，對每個候選一致，唔需要窗口配對——只需要數據存在性檢查（未上市 = n/a，唔會捏造數字）。

## Data provenance (`backtest/data.py` `load()`)

| Series | Source | Rows | From | To |
|---|---|---|---|---|
| AAPL | yfinance | 11485 | 1980-12-12 | 2026-07-10 |
| AAPL(adj) | yfinance(adj) | 11485 | 1980-12-12 | 2026-07-10 |
| AMZN | yfinance | 7333 | 1997-05-15 | 2026-07-10 |
| AMZN(adj) | yfinance(adj) | 7333 | 1997-05-15 | 2026-07-10 |
| DIA | yfinance | 7162 | 1998-01-20 | 2026-07-10 |
| DIA(adj) | yfinance(adj) | 7162 | 1998-01-20 | 2026-07-10 |
| GOOGL | yfinance | 5507 | 2004-08-19 | 2026-07-10 |
| GOOGL(adj) | yfinance(adj) | 5507 | 2004-08-19 | 2026-07-10 |
| META | yfinance | 3555 | 2012-05-18 | 2026-07-10 |
| META(adj) | yfinance(adj) | 3555 | 2012-05-18 | 2026-07-10 |
| MSFT | yfinance | 10159 | 1986-03-13 | 2026-07-10 |
| MSFT(adj) | yfinance(adj) | 10159 | 1986-03-13 | 2026-07-10 |
| NVDA | yfinance | 6908 | 1999-01-22 | 2026-07-10 |
| NVDA(adj) | yfinance(adj) | 6908 | 1999-01-22 | 2026-07-10 |
| QQQ | yfinance | 6876 | 1999-03-10 | 2026-07-10 |
| QQQ(adj) | yfinance(adj) | 6876 | 1999-03-10 | 2026-07-10 |
| SPY | yfinance | 8418 | 1993-01-29 | 2026-07-10 |
| SPY(adj) | yfinance(adj) | 8418 | 1993-01-29 | 2026-07-10 |
| TSLA | yfinance | 4032 | 2010-06-29 | 2026-07-10 |
| TSLA(adj) | yfinance(adj) | 4032 | 2010-06-29 | 2026-07-10 |
| USMV | yfinance | 3700 | 2011-10-20 | 2026-07-10 |
| USMV(adj) | yfinance(adj) | 3700 | 2011-10-20 | 2026-07-10 |
| VIG | yfinance | 5079 | 2006-05-02 | 2026-07-10 |
| VIG(adj) | yfinance(adj) | 5079 | 2006-05-02 | 2026-07-10 |
| XLP | yfinance | 6928 | 1998-12-22 | 2026-07-10 |
| XLP(adj) | yfinance(adj) | 6928 | 1998-12-22 | 2026-07-10 |
| XLU | yfinance | 6928 | 1998-12-22 | 2026-07-10 |
| XLU(adj) | yfinance(adj) | 6928 | 1998-12-22 | 2026-07-10 |
| XLV | yfinance | 6928 | 1998-12-22 | 2026-07-10 |
| XLV(adj) | yfinance(adj) | 6928 | 1998-12-22 | 2026-07-10 |

## Table A — 各候選自身原生全窗（背景脈絡，唔用嚟排名）

| 候選 | 原生窗 | CAGR(HK淨) | 稅漏 pp/yr | Sharpe | MaxDD | β vs SPY |
|---|---|---|---|---|---|---|
| B1 XLP/XLU/XLV | 1998-12-23→2026-07-10 | +7.4% | +0.78 | 0.55 | -39.5% | 0.62 |
| B2 XLP/XLU/XLV/USMV | 2011-10-21→2026-07-10 | +10.8% | +0.80 | 0.83 | -30.4% | 0.65 |
| B3 XLP/XLU/XLV/VIG | 2006-05-03→2026-07-10 | +9.3% | +0.81 | 0.67 | -41.1% | 0.68 |
| B4 USMV(單獨) | 2011-10-21→2026-07-10 | +11.0% | +0.63 | 0.84 | -33.1% | 0.71 |
| B5 DIA(單獨) | 1998-01-21→2026-07-10 | +8.5% | +0.68 | 0.53 | -52.4% | 0.91 |
| B6 Mag7等權合成(月度reb, 負面對照) | 2012-05-21→2026-07-10 | +36.3% | +0.21 | 1.29 | -48.9% | 1.32 |

## 判官表 1/3 — League A（USMV 窗，B1 vs B2 vs B4 vs B5）

共同窗：2011-10-21 → 2026-07-10（3699 交易日）。B1 喺呢度係喺 League A 窗重新計嘅錨，唔係全歷史數字。

| 候選 | DC 全窗 | DC 3y-rolling(中位/n) | 三壓力窗平均超額(vs SPY) | QQQ corr 126d(中位) | HK淨CAGR | 稅漏pp/yr | Sharpe(參考) | MaxDD(參考) | β vs SPY |
|---|---|---|---|---|---|---|---|---|---|
| B1 XLP/XLU/XLV | 55.1% | 57.6%(n=142) | +10.5% | 0.63 | +10.7% | +0.86 | 0.80 | -29.5% | 0.63 |
| B2 XLP/XLU/XLV/USMV | 58.2% | 61.0%(n=142) | +9.3% | 0.68 | +10.8% | +0.80 | 0.83 | -30.4% | 0.65 |
| B4 USMV(單獨) | 67.4% | 67.5%(n=142) | +4.6% | 0.77 | +11.0% | +0.63 | 0.84 | -33.1% | 0.71 |
| B5 DIA(單獨) | 97.3% | 98.9%(n=142) | +3.7% | 0.82 | +12.4% | +0.70 | 0.80 | -36.8% | 0.92 |

排名（1=最佳；judge 1-4 排名，Sharpe/MaxDD 唔計分，純參考）：

| 候選 | DC 排名 | 壓力窗排名 | QQQ相關排名 | HK淨CAGR排名 | **總分** |
|---|---|---|---|---|---|
| B1 XLP/XLU/XLV | 1 | 1 | 1 | 4 | **7** |
| B2 XLP/XLU/XLV/USMV | 2 | 2 | 2 | 3 | **9** |
| B4 USMV(單獨) | 3 | 3 | 3 | 2 | **11** |
| B5 DIA(單獨) | 4 | 4 | 4 | 1 | **13** |

## 判官表 2/3 — League B（VIG 窗，B1 vs B3 vs B5）

共同窗：2006-05-03 → 2026-07-10（5078 交易日）。B1 喺呢度係喺 League B 窗重新計嘅錨（同 League A 嘅 B1 數值唔同——唔同窗口，兩個都係合法嘅獨立錨，唔可以互相比較）。

| 候選 | DC 全窗 | DC 3y-rolling(中位/n) | 三壓力窗平均超額(vs SPY) | QQQ corr 126d(中位) | HK淨CAGR | 稅漏pp/yr | Sharpe(參考) | MaxDD(參考) | β vs SPY |
|---|---|---|---|---|---|---|---|---|---|
| B1 XLP/XLU/XLV | 54.4% | 53.9%(n=207) | +10.5% | 0.69 | +9.2% | +0.86 | 0.67 | -39.5% | 0.62 |
| B3 XLP/XLU/XLV/VIG | 61.2% | 62.1%(n=207) | +9.0% | 0.75 | +9.3% | +0.81 | 0.67 | -41.1% | 0.68 |
| B5 DIA(單獨) | 92.4% | 95.5%(n=207) | +3.7% | 0.85 | +9.6% | +0.73 | 0.59 | -52.4% | 0.92 |

排名（1=最佳；judge 1-4 排名，Sharpe/MaxDD 唔計分，純參考）：

| 候選 | DC 排名 | 壓力窗排名 | QQQ相關排名 | HK淨CAGR排名 | **總分** |
|---|---|---|---|---|---|
| B1 XLP/XLU/XLV | 1 | 1 | 1 | 3 | **6** |
| B3 XLP/XLU/XLV/VIG | 2 | 2 | 2 | 2 | **8** |
| B5 DIA(單獨) | 3 | 3 | 3 | 1 | **10** |

## 判官表 3/3 — League C（Mag7 窗，B1 vs B5 vs B6【負面對照】）

共同窗：2012-05-21 → 2026-07-10（3554 交易日，由 META 2012-05-18 上市決定）。B6 係明文負面對照組，呢張表嘅目的係用真實數字驗證/推翻「offense 資產做 ballast 會大敗」呢個預期，唔係揀佢做真候選。

| 候選 | DC 全窗 | DC 3y-rolling(中位/n) | 三壓力窗平均超額(vs SPY) | QQQ corr 126d(中位) | HK淨CAGR | 稅漏pp/yr | Sharpe(參考) | MaxDD(參考) | β vs SPY |
|---|---|---|---|---|---|---|---|---|---|
| B1 XLP/XLU/XLV | 57.7% | 58.5%(n=135) | +10.5% | 0.61 | +10.6% | +0.86 | 0.79 | -29.5% | 0.63 |
| B5 DIA(單獨) | 98.3% | 98.6%(n=135) | +3.7% | 0.82 | +12.3% | +0.69 | 0.80 | -36.8% | 0.92 |
| B6 Mag7等權合成(月度reb, 負面對照) | 95.0% | 75.4%(n=135) | -11.5% | 0.93 | +36.3% | +0.21 | 1.29 | -48.9% | 1.32 |

排名（1=最佳；judge 1-4 排名，Sharpe/MaxDD 唔計分，純參考）：

| 候選 | DC 排名 | 壓力窗排名 | QQQ相關排名 | HK淨CAGR排名 | **總分** |
|---|---|---|---|---|---|
| B1 XLP/XLU/XLV | 1 | 1 | 1 | 3 | **6** |
| B5 DIA(單獨) | 3 | 2 | 2 | 2 | **9** |
| B6 Mag7等權合成(月度reb, 負面對照) | 2 | 3 | 3 | 1 | **9** |

## 三壓力窗明細表（固定絕對日期，全部候選 + SPY 錨；n/a = 未上市，唔係計算失敗）

| 候選 | 2011-08 歐債（2011-08-01→2011-10-03） | 2020 COVID（2020-02-19→2020-03-23） | 2022 加息年（2022-01-01→2022-12-31） |
|---|---|---|---|
| B1 XLP/XLU/XLV | -4.9% (SPY -14.7%, 超額 +9.8%) | -29.5% (SPY -33.5%, 超額 +4.0%) | -0.8% (SPY -18.6%, 超額 +17.8%) |
| B2 XLP/XLU/XLV/USMV | n/a(未上市) | -30.4% (SPY -33.5%, 超額 +3.1%) | -3.1% (SPY -18.6%, 超額 +15.5%) |
| B3 XLP/XLU/XLV/VIG | -6.7% (SPY -14.7%, 超額 +8.0%) | -30.0% (SPY -33.5%, 超額 +3.5%) | -3.2% (SPY -18.6%, 超額 +15.4%) |
| B4 USMV(單獨) | n/a(未上市) | -33.1% (SPY -33.5%, 超額 +0.5%) | -9.9% (SPY -18.6%, 超額 +8.7%) |
| B5 DIA(單獨) | -11.8% (SPY -14.7%, 超額 +2.8%) | -36.2% (SPY -33.5%, 超額 -2.7%) | -7.6% (SPY -18.6%, 超額 +11.0%) |
| B6 Mag7等權合成(月度reb, 負面對照) | n/a(未上市) | -29.9% (SPY -33.5%, 超額 +3.6%) | -45.1% (SPY -18.6%, 超額 -26.5%) |

**2008 GFC（2008-01-01→2008-12-31，本 study 規格只報 B1，B5/B6 加入後此規則不變）**：B1 -22.5% vs SPY -37.2%（超額 +14.7%）。B2/B4 因 USMV 2011-10 先上市、B6 因 META 2012-05 先上市，遠喺 2008 之後，天然無數據，唔存在「漏報」；B3 嘅成員 VIG、B5 嘅 DIA 技術上 2008 已上市（有真實數據），但本 study 依原定規格淨報 B1，唔擴大範圍——呢個係預先註冊決定，唔係事後選擇性隱藏。

## 稅漏表 — HK 30% 股息預扣稅年化滲漏（pp/yr = CAGR_gross − CAGR_net）

| 候選 | 窗 | CAGR(稅前 r_adj) | CAGR(HK淨 r_net) | 稅漏 pp/yr |
|---|---|---|---|---|
| B1 XLP/XLU/XLV | League A | +11.5% | +10.7% | +0.86 |
| B2 XLP/XLU/XLV/USMV | League A | +11.6% | +10.8% | +0.80 |
| B4 USMV(單獨) | League A | +11.6% | +11.0% | +0.63 |
| B5 DIA(單獨) | League A | +13.1% | +12.4% | +0.70 |
| B1 XLP/XLU/XLV | League B | +10.0% | +9.2% | +0.86 |
| B3 XLP/XLU/XLV/VIG | League B | +10.1% | +9.3% | +0.81 |
| B5 DIA(單獨) | League B | +10.3% | +9.6% | +0.73 |
| B1 XLP/XLU/XLV | League C | +11.4% | +10.6% | +0.86 |
| B5 DIA(單獨) | League C | +13.0% | +12.3% | +0.69 |
| B6 Mag7等權合成(月度reb, 負面對照) | League C | +36.5% | +36.3% | +0.21 |

高息 XLU 系（B1/B2/B3 皆含）vs 低息 USMV（B4）vs DIA（B5，藍籌股息中等）vs Mag7（B6，多數低息/無息）嘅稅差係本測試焦點之一——見上表逐候選、逐 league 獨立呈現，唔淨係報一個 pooled 數字。

## beta-租金咬合表（內部咬合讀數，STATIC APPROXIMATION）+ 熊市 delta 地台

租金咬合公式：`Δneeded_from_LEAP = 0.45 × (β_B1(league) − β_X(league))`；`Δrent pp/NAV/yr = 11.64% × Δneeded_from_LEAP`（SPY 0.50Δ 每 $1 delta-notional 年租，取自 `backtest/results/2026-07-12_leap_rent_delta_ledger.md` §5，115% band 下嘅例子作錨；此邊際 rent-per-beta-point 計算同目標 delta 水平（100/115/130%）無關，係 level-independent 嘅一階近似——band 只係語境，唔影響呢條數）。
熊市 delta 地台公式：`floor = 0.60 × β_X(league) + 0.30`（LEAP 全閘出時嘅組合最低曝險——ballast 權重假設由 45% 提升到 60%，模擬防守股占比喺去槓桿情境下自然上升；thesis sleeve 25%×β1.20 一項固定不變）。ballast 45%／thesis 25%×β1.20／熊市地台 60% 三組假設原封不動照搬自 leap_rent ledger 同用戶最新指示，屬示意假設，唔係重新擬合嘅數字。

| 候選 | League | β_B1(league,錨) | β_X(league) | Δβ(B1−X) | Δneeded_from_LEAP | Δrent pp/NAV/yr(若由 B1 換成呢個候選) | **熊市 delta 地台** |
|---|---|---|---|---|---|---|---|
| B1 XLP/XLU/XLV | A | 0.63 | 0.63 | +0.00 | +0.0% | +0.00 | 68.0% |
| B2 XLP/XLU/XLV/USMV | A | 0.63 | 0.65 | -0.02 | -0.9% | -0.10 | 69.2% |
| B4 USMV(單獨) | A | 0.63 | 0.71 | -0.08 | -3.6% | -0.42 | 72.8% |
| B5 DIA(單獨) | A | 0.63 | 0.92 | -0.29 | -12.9% | -1.51 | 85.3% |
| B1 XLP/XLU/XLV | B | 0.62 | 0.62 | +0.00 | +0.0% | +0.00 | 67.3% |
| B3 XLP/XLU/XLV/VIG | B | 0.62 | 0.68 | -0.05 | -2.5% | -0.29 | 70.6% |
| B5 DIA(單獨) | B | 0.62 | 0.92 | -0.29 | -13.2% | -1.54 | 84.9% |
| B1 XLP/XLU/XLV | C | 0.63 | 0.63 | +0.00 | +0.0% | +0.00 | 68.1% |
| B5 DIA(單獨) | C | 0.63 | 0.92 | -0.29 | -12.9% | -1.51 | 85.3% |
| B6 Mag7等權合成(月度reb, 負面對照) | C | 0.63 | 1.32 | -0.68 | -30.7% | -3.58 | 109.1% |

**教學位驗證**：B6（Mag7）喺 League C 嘅熊市 delta 地台 = 109.1% —— 已驗證 >100%，即使 LEAP 全部閘出、ballast 都仲要用 offense 級 beta 頂住成個組合曝險，完全冇得喺熊市減磅，正正係「offense 資產擺 ballast 位」嘅代價量化。

## Cross-foot verification

- 269,294 bar-level NAV>0 assertions across all candidate/league NAV builds (incl. B6's monthly-rebalance simulation), ALL passed.
- 每個 basket 嘅組成標的索引交集喺 `equal_weight_basket()`/`monthly_rebalance_basket()` 內部 assert 冇 NaN——複合報酬只喺全部成員都有數嗰啲交易日先計。
- League A/B/C 索引各自驗證 `is_monotonic_increasing`。

## 結論

- **League A（B1 vs B2 vs B4 vs B5，USMV 窗）總分（1=最佳）**：B1 XLP/XLU/XLV=7、B2 XLP/XLU/XLV/USMV=9、B4 USMV(單獨)=11、B5 DIA(單獨)=13。最低分（職責達成最好）= **B1 XLP/XLU/XLV**。
- **League B（B1 vs B3 vs B5，VIG 窗）總分**：B1 XLP/XLU/XLV=6、B3 XLP/XLU/XLV/VIG=8、B5 DIA(單獨)=10。最低分 = **B1 XLP/XLU/XLV**。
- **League C（B1 vs B5 vs B6【負面對照】，Mag7 窗）總分**：B1 XLP/XLU/XLV=6、B5 DIA(單獨)=9、B6 Mag7等權合成(月度reb, 負面對照)=9。最低分 = **B1 XLP/XLU/XLV**——**B6 唔論排名高低都唔係真候選**，佢存在嘅目的係量化對照，結果解讀見下。
- 判官係預先註冊嘅職責達成度（downside capture、三壓力窗、QQQ 正交、HK 淨回報+稅漏各佔一票），**唔係揀 CAGR 最高嗰個**——HK 淨 CAGR 只係四項之一，唔係唯一票。
- **B5（DIA）角色**：正式候選，同時喺 League A 同 League B 都有齊數同 B1 直接對比——具體邊項贏邊項輸見上面判官表 1/2；係咪值得換 B1，睇 League A/B 嘅總分差距，唔靠呢度單一句話下判斷。
- **B6（Mag7）角色**：明文負面對照組——結果只用嚟量化「用 offense 資產做 ballast」嘅代價（downside capture、QQQ 相關、熊市 delta 地台三個讀數），**唔會、亦唔應該被讀成「B6 輸咗所以淘汰」——佢由頭到尾都唔係一個候選人，係一把量尺**。
- （逐項邊個贏邊個輸嘅具體數字見上面三張判官表；本段刻意唔喺 script 內自動生成「換唔換 B1」嘅最終建議文字，避免 script 自己下判斷變成隱性 return-chasing——最終建議見對話回覆 [結論] 段，基於呢啲表逐項核對後撰寫。）

## 誠實 Caveat

- **USMV 歷史短**：2011-10-20 先上市，League A 窗只有 3699 個交易日（~15年），唔含 2000 dot-com、2008 GFC、2011 歐債任何一個熊市——B2/B4 嘅 downside capture／壓力窗判斷樣本天然偏向 2012+ 嘅牛市為主 regime，結論外推去下一次危機有限度。
- **VIG 歷史中等**：2006-05-02 上市，League B 窗 5078 個交易日（~20年），含 2008 GFC 但唔含 2000 dot-com；B3 嘅 2008 數字本 study 冇獨立報（跟原定規格淨報 B1）。
- **B6 窗口最短**：由 META 2012-05-18 上市決定，League C 窗只有 3554 個交易日（~14年），完全冇 2008 GFC；但 B6 本身係負面對照組，唔係用嚟做長期資產配置決策，呢個短窗對佢嘅「教學」目的影響有限——2020 COVID + 2022 兩個壓力窗仍然覆蓋到。
- **B5（DIA）歷史最長但唔係『萬能錨』**：DIA 1998-01-20 上市，早過 XLP/XLU/XLV，喺三個 league 都唔係約束者，所以佢嘅數字喺三個 league 之間可以互相對照趨勢（但唔可以直接跨 league 數值相減——common-window 規矩依然適用，B5-in-A 同 B5-in-B 係兩個獨立讀數，唔係同一個窗口嘅同一條數）。
- **B6 月度 vs 其他候選逐日 rebalance 唔一致**：呢個唔係疏忽，係因為 7 隻集中大型股逐日重平唔現實（交易成本/滑點喺呢個規模下唔可忽略，逐日重平會嚴重高估合成組合嘅真實可執行回報），但都要意識到：呢個令 B6 同 B1-B5 嘅比較唔係 100% 純粹「淨係換咗成員」嘅乾淨 increment——重平頻率呢個變數都變咗。呢點喺 B6 係負面對照組（唔係候選）嘅前提下影響有限，但唔應該被忽略。
- **單一歷史路徑**：冇 bootstrap／冇 Monte Carlo／冇多重測試修正（Bonferroni/DSR）——本 study 係 6 個 pre-registered 候選嘅單一路徑驗證，唔係大格網 sweep。
- **預先註冊聲明**：候選集合（B1-B4）同判官標準喺任務指派時已經寫死；B5/B6 喺同一次任務指派入面（測試執行前）由用戶正式加入，判官標準同稅務處理全部不變——呢個係任務指派範圍內嘅正式擴充，唔係睇完初步結果先改嘅 post-hoc 調整。
- **等權重、逐日重平衡係建模簡化**（B1-B5 適用）：真實執行唔會逐日重平所有成員，籃子內部重平假設無額外成本；本 study 冇對權重方案做任何搜索（等權係指定，唔係擇優）。
- **beta-租金咬合表／熊市 delta 地台都係 STATIC 一階近似**：用嘅係固定 45%/60%/25%/β1.20 假設（來自 leap_rent ledger 嘅示意數字 + 用戶最新指示的地台權重，非重新擬合），冇考慮 target-delta band 唔同、冇考慮 beta 本身隨 regime 波動（Table A 嘅原生窗 beta 同 League 窗 beta 有機會唔同，讀者留意兩表唔係同一個數字）。
- **壓力窗定義係本 study 自訂**：2011-08 歐債 = 2011-08-01→2011-10-03（SPY 修正段）、2020 COVID = 2020-02-19→2020-03-23（急跌段）、2022 = 全年（「加息年」）——三個窗長度唔一（急性事件 vs 全年），讀者要意識到「平均超額」跨三個唔同長度嘅窗計，唔係嚴格同質嘅平均。
- **QQQ 相關性判官**：用 126 交易日 rolling correlation 嘅中位數（唔係全窗單一 Pearson 相關），中位數本身可能隱藏尾部（危機期相關性飆升嘅片段）——本 study 冇獨立報 rolling correlation 嘅危機期子集。

## Implication

（見對話回覆——若 B5 喺其所屬 league 總分明顯低過 B1（贏 3/4 或以上判官項），屬「體檢唔合格，換籃子有充分理由」的證據；若總分打平或 B1 仍然最低分，維持現行 XLP/XLU/XLV 等權係合理決定。B6 嘅讀數（downside capture、QQQ 相關、熊市 delta 地台）直接餵返 §8c 點 4「內部咬合」嘅可測錶盤——量化示範「ballast 揀錯資產」嘅代價量級，供設計文件引用做反面教材，唔需要另外做決策。）
