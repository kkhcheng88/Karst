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
| exp_leap_delta_sweep.py | LEAP delta 掃描(0.3/0.5/0.7/0.8)× 3 閘 × 2 frame(SLEEVE/PORTFOLIO) | 2026-07-06_leap_delta_sweep.md | superseded → leap_real_sweep(RV-proxy 冇 crash-vega,「0.80Δ 全格贏」喺真數據唔成立) |
| exp_leap_real_sweep.py | LEAP 真數據重驗:SPY×^VIX + QQQ×^VXN,4Δ×4閘×2frame×IV/成本/現金敏感度,cross-foot assert | 2026-07-06_leap_real_sweep.md | active ✅(0.30Δ GATED 贏α但當上限;0.70-0.80Δ hostable;純GATED>DIP/HYST;SLEEVE=ruin鏡) |
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
| exp_portfolio_rotation.py | 可執行週頻輪動 vs B&H | 2026-07-06_portfolio_rotation.md | active(補跑:非 duplicate,確認 rotation_challenge 判定 + 新增 bonds>cash 防守腳) |
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
| exp_family_validate.py | 四因子家族 forward IC+long-only 鏡子 | 2026-07-04_insider_family_revalidate.md | active ✅ |
| exp_insider_validate.py | insider Form4 訊號驗證(21d edge) | 2026-07-04_insider_family_revalidate.md | active ✅ |
| exp_memory_cycle.py | 記憶體股極端乖離事件 base rate | —(結論在 KARS_MEMORY,餵 thesis) | active(準孤兒) |
| exp_minervini_validate.py | Minervini SEPA/VCP 蒸餾規格回測 | 2026-07-06_minervini_validate.md | active 🟡(補跑:PARTIAL 弱,DSR 因構造性 bug 恆為 nan,唔升級 minervini_breakout 嘅負面判定) |
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
| exp_dix_ic.py | DIX(暗池)forward IC(週度/smoothed/2-4週) | 2026-07-05_phase2_flow.md | active ✅(真.modest,IC 0.11-0.14 兩半) |
| exp_breadth_flow.py · _deep · _rsi2 · _timeframe · _real | Phase-2 breadth(多量度/多 timeframe/RSI-2 modifier/真漲跌線) | 同上 | active(negative:breadth LEVEL 弱/逆向/VIX 冗餘) |
| exp_breadth_reversion.py · _verify | breadth 洗盤 reversion(decile 條件報酬/washout×VIX/thrust/背離/板塊參與度 + 日期核實/excess 單邊驗) | 2026-07-05_breadth_reversion.md | active ✅(修正:洗盤反彈真、短線 over VIX、單邊 U 形) |
| exp_sector_capeff.py | 板塊 ETF 資本效率表達 4 假設(H1 bull dip 輪動/H2 恐慌窗部署/H3 防守 tilt/H4 buffer現金vs債),全部 SPY control-leg increment | 2026-07-06_sector_capeff.md | active(negative/mixed:H1/H3 無 increment;H2②顯著負(t-2.52,n=14);H4 regime-conditional 唔顯著但方向啱——2008/2020 bonds>cash、2022 反轉) |
| exp_core_assembly_real.py | 組合總裝真數據 18 格:SPY底倉+200SMA-GATED LEAP sleeve(複用 exp_leap_real_sweep 引擎)+現金,premium預算b×delta×LEAP標的mix(SPY-only/50-50 SPY+QQQ),年度再平衡+roll掃盈利返底倉 | 2026-07-06_core_assembly_real.md | active ✅(headline b20/Δ0.50/SPY+QQQ:α+7.8pp t+4.1,Bonferroni x18 p=0.00075,DSR=1.000;damp=0.4 令0.50Δ α明顯縮;cash0%/annual-rebal-off 令sleeve永久停擺,confirm年度再平衡係load-bearing;cash-starved 40-60%已計入base case) |
| exp_core_topup.py | Loop-4(收官輪):修 exp_core_assembly_real 現金枯竭,補錢規則 4 選(年度/季度/月度/on-roll)× b{10,15%}× Δ{0.50,0.70,0.80},mix 定 SPY+QQQ;每格報 base+damp0.4 兩行(補齊唔對稱披露) | 2026-07-06_core_topup.md | active ✅(winner C-monthly/b15/Δ0.50:cash-starved 53/48%→10/7%;base α+12.4pp t+5.4,damp0.4 α+6.5pp t+3.1(vs rule-A對照 damp t+1.8 唔顯著);Bonferroni×42 base p=2.4e-6/damp p=0.095(邊緣),DSR=1.000;D-onroll負面:starved反差、MaxDD穿user帶,冇修好枯竭;rounding drag可忽略) |
| exp_power_etf_basket.py | ai-power-grid 衛星 ETF 籃(URA/URNM/NLR/XLU/UTES/GRID/FCG)持倉重疊+相關矩陣+子腿覆蓋研究 | 2026-07-08_power_etf_basket.md | active(**研究筆記,非訊號回測**;「URES」用戶確認=UTES(IPP 濃度 ~37% vs XLU ~13%);推薦 URA+GRID+UTES(主題表達)/ 換 XLU 做防守變體;三腿 top-10 重疊全 0) |
| exp_base_mix.py | Core v2 底倉 A/B:SPY vs QQQ vs SPMO vs 50/50 SPY+QQQ(sleeve/現金/top-up 全定死,benchmark 定死 SPY B&H),窗A 2015-10-12+(SPMO 起,4格)+ 窗B 2001+(3格,無SPMO),每格 base+damp0.4,β/α分開報 | 2026-07-07_base_mix.md | active ✅(長史窗B判定:QQQ=BETA BET(β1.14/1.25 vs SPY1.07/1.18,α-t反跌5.4→4.5/3.1→2.7);50/50=similar/inconclusive(同SPY打平);SPMO 得窗A單一9.7年regime出現ALPHA GAIN(damp列),唔夠證據換底倉;維持SPY;SPY列數值同core_topup.md winner cell完全對得上,獨立覆現通過) |
| exp_topup_timing_ab.py | 用戶挑戰 core_topup 勝出格(C-monthly/b15/Δ0.50/mix)嘅補錢時機:Rule E(SPY RSI-2<10 觸發補錢取代月曆)vs Rule F(月度補錢+每 leg 開倉加 GATED+DIP dip 條件),複用 exp_core_topup 引擎,C 格數值引用唔重跑(另跑 regression check 對數) | 2026-07-07_topup_timing_ab.md | active ✅(E:α打平(base+12.2pp t+5.3/damp+6.5pp t+3.0 vs C +12.4pp/+6.5pp)但 cash-starved% 更差 15/14% vs C 10/7%,RSI 事件叢集非均勻分佈；「2017 型全年零觸發」假設否證,26年每年都有≥1日 RSI<10(2017 最少 9 日);F:全窗全 IV 都輸 C,同 exp_leap_real_sweep 引擎級「純GATED>DIP」結論一致,dip-gate 傷 alpha 非救;兩格均唔換勝出格) |
| exp_crash_switch.py | DYNAMIC 換底倉 A/B:QQQ/SPMO 大冧後由 SPY 換入、回升換返(V1 左側 drawdown 20/30/40% + V2 右側 200SMA 復甦,100% base-holding-only,5bps/邊,T收市->T+1收市執行) | 2026-07-08_crash_switch.md | active(negative:三變體皆唔顯著贏 Control;V1 系列 FULL 窗 MaxDD 反而轉差 -75~-81%(2000-02 接飛刀16年主導);V2 純 whipsaw(120次換馬);SPMO V3 前提偏離——2022 dd 只達-23.7%未過30%門檻,V1 全期得一單 episode) |
| exp_crisis_rescue.py | A-型危機救援 event study:VIX>{35,40,45} close episode(60td dedup)四腿比較(L1 naive worst-2殘板塊/L2 SPY control/L3 系統性XLF-XLE epicenter/L4 右側等VIX<30先入),全 horizon 21/63/126/252d,逐 episode 表為主體 | 2026-07-08_crisis_rescue.md | active(mixed:n=12@VIX40;①系統性filter無助——L3唔贏L1;②右側L4方向一致贏左側L3全horizon全門檻但n=5-8outlier敏感;③63-126d甜區;2025-04無epicenter=非系統性危機) |
| exp_crypto_decorr.py | BTC/ETH 對 SPY/QQQ decorrelation 真考試:全期+分段相關(daily/monthly)、尾部相關(SPY 最差5%日)、5 個危機窗同窗跌幅、獨立資產 CAGR/vol/MaxDD、5/10/20% monthly-rebal 組合 A/B(ETH起+2022+ 兩窗,pre/post-2022 拆解判 bull-run artifact)、IEF/cash 對照組、2022 rebalance 買跌診斷 | 2026-07-08_crypto_decorr.md | active(negative:相關性 2022 起上升唔係下降,尾部相關+0.35/+0.37 高於全期、危機窗全數跑輸 SPY;10%組合 Sharpe 提升幾乎全靠 2017-2021 牛市——post-2022 leg 淨係5-10% BTC 打平 SPY-only 非贏;IEF/cash 對照組先見真・低相關資產樣式——MaxDD 實跌) |
| exp_constraint_language.py | WS4 早期偵測:財報電話會 transcript「供給受限語言」掃描(defeatbeta earning_call_transcripts,15 隻跨板塊,詞表 v0 雙向 pre-registered,per-ticker per-quarter 淨分數/1000字,FY2018 起 487 季度列) | 2026-07-08_constraint_language_probe.md | **可行性原型**(非回測 alpha 結論;數據 15/15 隻全覆蓋回溯 2005-2008;記憶體鏈 MU 訊號兩波提前於 gooptions 敘事——FY2024Q1(2023-12-20)早 ≈17 個月、FY2025Q4(2025-09-23)早 ≈8 個月;電力鏈 VST/ETN 2023 已轉正,提前幅度更大但置信度較低(可能只反映語料庫覆蓋遲);建議季度批次 job,詞表擴充需跨 ≥3 公司+≥2 季覆現先升級) |
| exp_insider_sector_cluster.py | WS4 早期偵測:insider 群買跨公司(同 theme/價值鏈,`thesis/themes.yaml`)共振做主題發現訊號,pre-registered 網格{N insider∈{2,3}}×{window∈{21,42}}×{≥2 公司}×{open-market P-buy>$250k},複用已 cache 嘅 SEC bulk Form 345(2006q1-2025q2,78 季,離線) | 2026-07-08_insider_cluster_probe.md | **發現訊號探測,非交易訊號回測**(negative:全部 4 個定義組合 fires/年 <1、memory-supercycle 同 ai-power-grid 兩個核心 AI theme zero-fire——memory 係「冇料」(10年僅4個P-buy日)、power 係「唔夠密」;7 個 fire 案例回溯 mixed 冇一致方向;「早過敘事」測試做唔到(冇 fire),對照 exp_constraint_language.py 喺同一 memory 鏈用 transcript 語言確實搵到早期訊號——早期偵測有效管道係 transcript 唔係 insider cluster;唔建 daily job) |
| — (無對應腳本,純研究) | **公開可得/機器可讀早期訊號數據源普查**(fan-out census:能源/電力/物流、半導體+宏觀製造業、信用+利率+預測市場、社交注意力、unknown-unknown 共 5 大類、~80 候選源逐一核實免費API/更新頻率/歷史深度) | 2026-07-08_altdata_census.md | **數據源普查,非回測**(top 5 pre-registered probe:①crack spread oil-gas-energy、②EIA-930電網 ai-power-grid、③ISM NO−Inventories 宏觀閘增量、④Cass Freight+AAR鐵路 工業/物流、⑤台灣月度營收 memory-supercycle;驚喜:分行業HY OAS免費源不存在/社交注意力類2023後大量收費死亡/Kalshi免KYC免費讀取/SEMI Book-to-Bill已停發布十年) |

## 孤兒處理原則

**3 個孤兒 + 2 個準孤兒**(2026-07-06 補跑 portfolio_rotation + minervini_validate 後由 5 減至 3;
family/insider_validate 已指向 2026-07-04 結果檔)。剩餘孤兒:exp_pmcc.py(歷史,PMCC 已除名)、
exp_sector_timeframe.py、exp_rescue_forensics.py。準孤兒:exp_memory_cycle.py、
exp_rsi2_capeff_detailed.py。**不刪**(負面結果是證據、repo 哲學)。要引用其結論前,
先重跑一次補 results 文件。
