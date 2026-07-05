# backtest/experiments — 實驗檔索引與慣例

> 37 個一次性研究實驗(2026-06-30 ~ 07-03)。核心庫(data/engine/metrics/signals/
> regime/scorecard/options_engine/bsm)住上層 `backtest/`,spine 住 `backtest/spine/`。
> 盤點:2026-07-03 workspace 重組。

## 慣例(新實驗照此寫)

1. **docstring 契約**:第一段寫清楚 Question(測什麼)、Method(mirror/increment/
   horizon 三選擇——見 memory `validation-mirror-and-increment`)、成本假設。
2. **sys.path**(本目錄專用):
   `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`
3. **結論必須落檔**到 `backtest/results/YYYY-MM-DD_<topic>.md`(格式照現有檔:
   Question/Method/Results 表/Conclusions/Caveats/Implication)。**inline 跑完不存檔
   = 未完成**(2026-07-03 capstone 不可重現的教訓)。
4. 跑法:`python backtest/experiments/exp_foo.py`(輸出長就 grep 過濾)。
5. **交叉 import 群**(搬動/改名要整群一起):
   - Cluster A(fear/greed 線):`exp_topdays_exposure` ← exposure_sweep / mr_roundtrip /
     mr_split_rules / alpha_decomp / capital_efficiency
   - Cluster B(輪動線):`exp_portfolio_oracle` ← gap_forensics / oracle_forensics /
     portfolio_rotation / skill_curve / weekly_trigger
6. **測試覆蓋(2026-07-05 起強制,見 memory `backtest-testing-standard`)**:逐標的訊號測試
   **必須覆蓋 4 股種——大盤指數(SPY/QQQ/SPMO)、細價股(IWM/IJR)、板塊ETF(11 SPDR)、
   Mag7——唔可以漏細價股**(insider 教訓:edge 成日喺細價股)。細價股用 **size-matched
   benchmark(vs IWM/IJR,唔係 SPY)**;量度用**資本效率**(部署回報/條件Sharpe);窗 **2016+
   + 前/後半**;報 per-cell n + survivorship/成本/tail(mean vs median)。下負面結論前**對文獻**。

## 狀態定義

**active** 結論仍有效 · **negative** 紀律性否定(保留為證據,別重測)·
**superseded** 被後續取代(留檔可溯)· **孤兒** 結論未存檔(重跑前先補 results 文件)

## 索引(實驗 ↔ 結果文件 ↔ 狀態)

| 檔名 | 測什麼 | 結果文件(backtest/results/) | 狀態 |
|---|---|---|---|
| exp_rsi2_filter.py | 200SMA 濾網對 RSI-2 幫助還是傷害 | 2026-06-30_rsi2_200sma.md | active ✅ |
| exp_rsi2_exit.py | RSI-2 出場門檻掃描(>70/80/90/95) | 同上(Addendum) | active |
| exp_rsi2_alpha.py | RSI-2 的 Jensen alpha/回撤分佈/勝率 | 同上(Addendum 2) | active |
| exp_leap_timing.py | 深 ITM LEAP 要不要 200SMA 閘 | 2026-06-30_leap_timing.md | active 🟡 |
| exp_csp.py | CSP 的 VRP + 進場時機 | 2026-06-30_csp.md | active 🟡 |
| exp_csp_ivrank.py | 裸 CSP 按 IV-rank 分桶(U 型) | 2026-06-30_regime_and_iv.md | active |
| exp_shortcall.py | 短 call 何時賣(超買/高 IV) | 2026-06-30_shortcall_timing.md | active ✅ |
| exp_scorecard_validation.py | scorecard 分數是否預測報酬/風險 | 2026-06-30_scorecard_validation.md | active ✅ |
| exp_pmcc.py | PMCC vs 純 LEAP vs 持有 | — | **孤兒**(PMCC 已於 v3.1 移除,歷史) |
| exp_sector_character.py | 板塊性格:趨勢 vs 均值回歸 | 2026-07-01_sector_character_2b.md | negative(不建 11 板塊地圖) |
| exp_sector_timeframe.py | 板塊 RSI-2 日線 vs 週線 | — | **孤兒** |
| exp_valuation.py | PE 自身歷史分位(18 檔科技) | 2026-07-01_valuation.md | superseded → valuation_broad |
| exp_valuation_broad.py | 估值訊號廣宇宙+分板塊重測 | 同上(Broad update) | active |
| exp_portfolio_oracle.py | 週頻輪動完美預知上限 | 2026-07-01_portfolio_oracle.md | active(Cluster B 基底) |
| exp_portfolio_rotation.py | 可執行週頻輪動 vs B&H | — | **孤兒/存疑**(疑被 rotation_challenge 吸收) |
| exp_rotation_challenge.py | 輪動 7%→155% 落差:因子還是幻象 | 2026-07-01_rotation_challenge.md | active(收斂輪動線) |
| exp_oracle_forensics.py | 拆解 oracle:哪板塊/何時/為何 | 2026-07-01_oracle_forensics.md | active |
| exp_gap_forensics.py | 非科技板塊最大跳空:事件或噪音 | 2026-07-01_gap_forensics.md | active |
| exp_rescue_forensics.py | 最大單週爆發=恐慌超賣救援? | — | **孤兒** |
| exp_skill_curve.py | IC vs 報酬的獎勵曲線(凸性) | 2026-07-01_skill_curve.md | negative(價量門關閉) |
| exp_weekly_trigger.py | 什麼因子預測下週板塊報酬 | 同上 | negative |
| exp_factor_sweep.py | ~30 因子 IC 掃描+Bonferroni | 同上 | negative |
| exp_alpha360_ml.py | GBDT ML 板塊窄截面 OOS IC | 2026-07-01_alpha360_ml.md | negative |
| exp_alpha360_broad.py | Alpha360 ML 廣度股票池 OOS IC | 同上 | negative |
| exp_ml_broad2sectors.py | 廣度訓練 GBDT 套板塊排序 | 同上 | negative |
| exp_family_validate.py | 四因子家族 forward IC+long-only 鏡子 | —(結論在 ARCHITECTURE/HANDOFF) | active(準孤兒) |
| exp_insider_validate.py | insider Form4 訊號驗證(21d edge) | —(結論在 ARCHITECTURE/docs 審查) | active(準孤兒) |
| exp_memory_cycle.py | 記憶體股極端乖離事件 base rate | —(結論在 KARS_MEMORY,餵 thesis) | active(準孤兒) |
| exp_minervini_validate.py | Minervini SEPA/VCP 蒸餾規格回測 | — | **孤兒**(verdict 只印 console) |
| exp_vcp_pattern.py | VCP 收縮結構 vs 純突破(A/B + IC,5-63d swing) | 2026-07-05_vcp_pattern.md | active(negative:VCP 唔加值/輕微傷) |
| exp_vcp_sharpely.py | sharpely VCP tightness 規則 A/B | 同上(佐證段) | active(negative,同 pattern 一致) |
| exp_topdays_exposure.py | fear/greed overlay 會錯過 top-10 日? | 2026-07-03_topdays_exposure.md | active(Cluster A 基底) |
| exp_exposure_sweep.py | 持有天數掃曝險 0.12-0.48 relever | 同上(Refinement 1) | superseded → mr_roundtrip |
| exp_mr_roundtrip.py | findings 原味進出場,曝險用算的 | 同上(Refinement 1) | active/negative(無 alpha) |
| exp_mr_split_rules.py | RSI2-only vs VIX+F&G-only 拆規則 | 同上(Refinement 2) | active/negative |
| exp_capital_efficiency.py | 單位曝險資本效率(部署計時器) | 同上(Refinement 3) | active ✅ |
| exp_alpha_decomp.py | alpha = T1 擇時 + T2 結構拖累 | 同上(Refinement 4) | active ✅ |
| exp_fg_timed_capeff.py | F&G 買恐懼/賣貪婪 資本效率全格(4類×4市值×entry×exit) | 2026-07-05_fg_timed_capital_efficiency.md | active ✅ |
| exp_fg_spec_strategy.py | F&G-timed 投機籃(個股 spec/safe)資本效率 | 2026-07-05_fg_crosssectional.md(RETRACTION) | negative(proxy 依賴) |
| exp_rsi2_capeff_detailed.py | RSI-2 資本效率全格(4市值×entry×exit,per-trade) | —(餵 mean-rev 家族) | active(準孤兒) |
| exp_rsi2_meanrev_family.py | mean-rev 增量 A(換K線)+B(vs SPY),4類×entry×exit | 2026-07-05_meanrev_family.md | active ✅ |
| exp_rsi2_twohalves.py | 日K RSI-2 前後半 robustness(2016-20 vs 2021+) | 同上(TWO-HALVES 段) | active ✅(關鍵 disproof) |
| exp_rsi2_news_filter.py | mean-rev 增量 C:RSI-2 避財報窗 A/B(個股) | 2026-07-05_meanrev_family.md(C 段) | active(大型股無用/細價有用=PEAD) |
| exp_momentum_family.py | 動能/趨勢 timer(ABS + RS vs SPY)4類×SMA網格×two-halves | 2026-07-05_factor_families_momentum_lowvol_rs.md | active ✅(穩健兩 regime) |
| exp_lowvol_family.py | 低波:選股異常 + 波動 timer,4類×two-halves | 同上 | active(選股非alpha/timer半artifact) |
| exp_rs_selection_filter.py | RS 5-tier 選股(多 horizon)+ RS filter on RSI-2(two-halves) | 同上 | active ✅(RS-leader gating 救 RSI-2) |
| exp_families_mktcap_tiers.py | momentum + mean-rev × 4 市值層 × two-halves(補 small/mid) | 同上(市值層段) | active ✅(動能全市值/MR micro死) |
| exp_rs_trend.py | RS LEVEL×TREND 2×2 選股 + RSI-2 filter(加速vs褪色leader) | 同上(RS 2×2 段) | active(level=edge/trend僅dip-filter反向) |
| exp_momentum_proper.py | 正版 TSMOM(trailing-月報酬>0)取代 SMA,4類+市值層+two-halves | 同上(RE-VALIDATION 段) | active ✅(修正:動能=側避跌浪非處處贏) |
| exp_breakout_timer.py | SPEC D Donchian 新N日高突破 timer,4類+市值層+two-halves | 2026-07-05_breakout_momentum.md | active ✅(20日高突破>TSMOM>SMA,修H1) |
| exp_minervini_breakout.py | SPEC A/B Minervini 範本+突破個股 + RISK/FIXED overlay | 同上 | active(selection無alpha/risk-layer傷回報) |
| exp_gex_test.py | GEX(免費 SqueezeMetrics CSV)vs VIX 增量 + DIX flow | 2026-07-05_gex_test.md | active(negative:GEX對VIX無增量,唔建) |
| exp_gamma_walls.py | live 逐 strike gamma 牆:支持/阻力區+強度+企穩線(SPY/QQQ 0DTE/1W/1M) | docs/2026-07-05_gamma_walls.md | active(live 工具,無回測,forward-log 驗證) |
| exp_credit_axis.py | credit(HYG/LQD)做風險軸 × VIX 四象限 | 2026-07-05_market_regime_2d.md | active(negative:regime反覆、對VIX無增量) |
| exp_trend_vix_axis.py | 趨勢(200SMA)× VIX 2D 四象限(替代 credit) | 同上 | active ✅(②牛市+恐懼兩半最好+最安全) |

## 孤兒處理原則

7 個孤兒 + 3 個準孤兒:**不刪**(負面結果是證據、repo 哲學)。要引用其結論前,
先重跑一次補 results 文件(尤其 exp_minervini_validate 的 verdict 從未存檔)。
