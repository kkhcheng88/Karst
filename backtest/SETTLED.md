# SETTLED —— 信念登記冊

> **呢個唔係實驗清單。`results/` 145 個檔記錄「我哋做過乜」;本檔記錄「我哋而家相信乜嘢係真」。**

## 使用協議(開新實驗之前必讀)

1. **開任何新實驗之前必查本檔。** 查到條問題已經喺度 = 你係喺重複。
2. 除非你喺實驗檔第一段明文寫低「**我改邊個配置、點解、同正本邊度唔同**」,否則**唔好跑**。
3. **新結論落地 = 更新本檔對應嗰行**(改答案/改正本/改狀態),**唔係加新行**。
4. **一行 = 一條問題。唔准寫散文。** 要解釋去正本檔。
5. **「尺」欄係防呆**:落判詞前問「呢把尺量緊嘅係咪我要答嗰樣嘢?」⚠️ = 尺錯層,結論要打折。
6. **sleeve/訊號層禁用 alpha**(用戶明令),用資本效率+絕對 PnL;alpha 只喺全組合層(core v2 vs SPY net-TR)出現。
7. **訊號嘅好壞由方向決定** —— 落判詞前問「我講緊買方定賣方?」(見 #13/#14 RSI2 兩邊符號相反)。
8. **矛盾唔准兩行並存扮冇事** —— 見 §8。

狀態:`settled` 已定論 · `suspended` 有橫額/被質疑 · `open` 未答 · `superseded` 被新檔取代
尺:`資本效率` `alpha(全組合)` `alpha(sleeve)⚠️` `IC` `命中率` `事件研究` `Sharpe` `PnL÷曝險` `描述性` `無`(設計/審查檔)

---

## §1 Tier-1 核心組合(全組合層 —— 呢層用 alpha **係啱尺**)

| # | 問題 | 答案(≤25字) | 尺 | 正本 | 狀態 |
|---|---|---|---|---|---|
| 1 | 底倉揀邊隻?大冧後換唔換? | SPY;QQQ/50-50 淨係加 beta;大冧後換 = 冇α兼 MaxDD 更差 | alpha(全組合) | `2026-07-07_base_mix.md` +`07-08_crash_switch` | settled |
| 2 | Core v2 最終配置? | SPY 底倉+SPY/QQQ LEAP、預算 15-20%、Δ0.50 | alpha(全組合) | `2026-07-06_core_assembly_real.md` | settled |
| 3 | 現金乾涸點救? | 月度 floor 補水;RSI 擇時補水 α 打和但乾涸更差 | alpha(全組合) | `2026-07-06_core_topup.md` +`07-07_topup_timing_ab` | settled |
| 4 | 防守板塊做偽現金? | 唔得:熊市每次輸現金 1.51%;B1 籃子唔使換 | alpha(全組合) | `2026-07-12_ballast_parking_ab.md` +`07-13_bt7` | settled |
| 5 | core-v2 三個改良(AA/regime band/washout)? | AA 唔輸但回報低;另兩個噪音級≈0,未過 Bonferroni | alpha(全組合) | `2026-07-12_bt2_aa_vs_core.md` +`07-13_bt3_bt4` | settled |
| 6 | crypto 算唔算分散資產? | 唔得:相關升緊、尾部同跌;thesis 六角度全 FAIL | Sharpe | `2026-07-08_crypto_decorr.md` +`07-11_crypto_thesis` | settled |

## §2 期權工具(sleeve 層 —— **禁用 alpha**)

| # | 問題 | 答案(≤25字) | 尺 | 正本 | 狀態 |
|---|---|---|---|---|---|
| 7 | LEAP 揀邊個 delta/框架? | PORTFOLIO+純 200SMA 閘、Δ0.70-0.80(0.30Δ headline 已撤) | **alpha(sleeve)⚠️** | `2026-07-06_leap_real_sweep.md` +`06-30_leap_timing` | settled |
| 8 | LEAP 部署經濟學(租金/冷啟動)? | 0.50Δ 達 115% 曝險只需 9.55% NAV;一次過 vs 分期打和 | 資本效率 | `2026-07-12_leap_rent_delta_ledger.md` +`07-17_cold_start` | settled |
| 9 | 裸賣 CSP 有冇料? | 冇:係 beta 唔係 α,牛市輸純持有 | **alpha(sleeve)⚠️** | `2026-06-30_csp.md` | settled |
| 10 | 幾時賣、賣咩期權? | 低 IV 先賣、賣 spread 唔好裸 CSP | PnL÷曝險 | `2026-06-30_regime_and_iv.md` | settled |
| 11 | 期權定價 m 值啱唔啱? | 唔啱:m=0.85 太低,應 1.00-1.15;深 ITM 更貴 | 描述性 | `2026-07-09_options_chain_spotcheck.md` | settled ⚡§8-B |
| 12 | 非核心倉用期權表達得唔得? | 一半:4/12 乾淨;washout 同本金贏 8/9、同曝險冇優勢 | 描述性 | `2026-07-12_satellite_option_expression_probe.md` +`07-13_bt_b` | settled |

## §3 擇時訊號(訊號層 —— **禁用 alpha**)

| # | 問題 | 答案(≤25字) | 尺 | 正本 | 狀態 |
|---|---|---|---|---|---|
| 13 | RSI2 撈底(**買方**)有冇用? | 驗唔出:CapEff 229 vs 隨機同曝險 219,p=0.69;方向正但細 | 資本效率 | `2026-07-17_rsi2_be_replication.md` | settled ⚡§8-A |
| 14 | RSI2(**賣方**)>90 賣 call? | **有料**:PF 1.53→2.26 —— 同買方符號相反,唔可一條線管兩邊 | PnL÷曝險 | `2026-06-30_shortcall_timing.md` | settled |
| 15 | RSI2 以外仲有均值回歸增量? | 冇增量;而且要 regime 閘先得 | 資本效率 | `2026-07-05_meanrev_family.md` | settled |
| 16 | 大市層廣度/資金流有用嗎? | 廣度洗盤 21d 喺 VIX 之上 +2pp(單邊);DIX 細、GEX≈0 | 事件研究 | `2026-07-05_breadth_reversion.md` +`gex_test`/`phase2_flow` | settled |
| 17 | F&G 同 VIX 點分工? | 入場用 VIX、賣貪婪用 F&G;極端恐懼入場全籃贏(n=7) | PnL÷曝險 | `2026-07-05_fg_vs_vix.md` +`fg_timed_capital_efficiency` | settled |
| 18 | F&G 揀唔揀到投機股? | 判不到:兩個 proxy 方向相反,同日撤回 | 事件研究 | `2026-07-05_fg_crosssectional.md` | **suspended** |
| 19 | 風險 regime 軸用咩? | 趨勢×VIX;credit 軸判 negative,已剔除 | 事件研究 | `2026-07-05_market_regime_2d.md` | settled |
| 20 | 因子家族邊個真? | 動能+RS+20 日高突破得;低波唔得;VCP/SEPA IC≈0 | 資本效率 | `2026-07-05_factor_families_momentum_lowvol_rs.md` +`breakout`/`vcp`/`minervini` | settled |
| 21 | 估值做選股/擇時? | 兩邊都唔得:QQQ 節流 vs 加速 CAGR 差 0.00% | Sharpe | `2026-07-16_mag7_valuation_throttle.md` +`07-01_valuation` | settled |
| 22 | 閃縮/恐慌撈底接唔接得真錢? | 閃縮唔得(63d excess≈0);恐慌要等 VIX 回落先買 | 事件研究 | `2026-07-13_a_flashdip_backtest.md` +`07-08_crisis_rescue` | settled |
| 23 | 擠迫+2x 就 trim 三分一? | 唔得:冇增量,63d 方向反轉,贏率得 35-42% | 事件研究 | `2026-07-13_trim_rule_validation.md` | settled |

## §4 板塊

| # | 問題 | 答案(≤25字) | 尺 | 正本 | 狀態 |
|---|---|---|---|---|---|
| 24 | 板塊輪動捕唔捕捉到? | 唔得:全部變體輸 SPY/EW;殘差 XLK 主導唔獨立;上限係噪音幻象 | Sharpe | `2026-07-06_portfolio_rotation.md` +`gics_residual`/`residual_seesaw`/`xle_xlk` | settled |
| 25 | 板塊做部署載體好過 SPY? | 唔得:四個假設全不過關,H2 顯著負;性格分唔到趨勢/震盪 | 資本效率 | `2026-07-06_sector_capeff.md` +`07-01_sector_character_2b` | settled |
| 26 | 板塊約束語言密度預測跑贏? | **未有定論**:相關近零,方向不一,未跑 placebo/LM 對照 | 描述性 | `2026-07-10_sector_constraint_language.md` | **open** |
| 27 | 主題用 ETF 定個股表達? | 記憶體/油氣有純 ETF,其餘只能個股;掃過冇 ETF 盲點 | 描述性 | `2026-07-10_theme_proxy_etf_purity.md` +`etf_turnover_scan`/`qqq_two_factor` | settled |

## §5 thesis 系統

| # | 問題 | 答案(≤25字) | 尺 | 正本 | 狀態 |
|---|---|---|---|---|---|
| 28 | 約束語言早過敘事幾耐? | 早:MU 早 17 個月/8 個月 → 定為主管道 | 描述性 | `2026-07-08_constraint_language_probe.md` | settled |
| 29 | 邊啲主題供給緊?邊啲 priced-in? | 記憶體/DC電力/鈾/銅鋁 S-A 級;半導體已擠,銅鋁鈾未擠最佳 | 無 | `2026-07-15_constraint_scan_production.md` +`constraint_register`/`demand_side_scan`/`priced_in_gate` | settled |
| 30 | 幾多 EV 要靠 supercycle 兌現? | 8/15 主題大部分係希望;11 隻槓桿爆錶;FSLR 白送 | 無 | `2026-07-15_expectations_gap_v1.md` | settled |
| 31 | 承重 claim 頂唔頂得住 red-team? | 15/15 已跑:2 STRONG,其餘 WEAK/部分中彈,冇一個 FOLD | 無 | `2026-07-15~16_redteam_*.md`(15 檔)+`china_dependency_audit` | settled |
| 32 | confidence 公式點定? | 已批准落地:single-source cap 0.30,lint 7→0 | 無 | `2026-07-16_final_confidence_diff.md` | settled |
| 33 | 擁擠複合做唔做到? | 得:15/15 有讀數;gs_flow 零數據源;分析師出席只做排名輸入 | 無 | `2026-07-13_crowding_composite.md` +`asml_contamination`/`d1_fix`/`analyst_attendance` | settled |
| 34 | 機構持股/turnover 做早期訊號? | 唔得:真構念(13F 序列)測唔到,proxy 冇 edge,擱置 | IC | `2026-07-11_institutional_ownership_crowding_axis.md` | settled |
| 35 | 語氣/復甦詞彙搶先價格底? | 唔得:訊號落後價格 284/349 日;類別 2 研究線擱置 | 事件研究 | `2026-07-11_category2_sentiment_reversal_v3.md` | settled |
| 36 | sizing 公式點砌? | 收斂速度唔入得公式;magnitude 軸必須設 conf 門檻;估值判別 6/6 | 資本效率 | `2026-07-12_sizing_two_axis_decision_analysis.md` +`sizing_formula_validation`/`bt5` | settled |
| 37 | capex/solvency 做唔做閘? | capex 只做排程 WATCH 唔做 kill;solvency 只否決 pe 平候選 | 事件研究 | `2026-07-15_solvency_gate_probe.md` +`capex_da_supply_response`/`mp_capex_da_*` | settled |
| 38 | discovery radar 揀到幾多? | 46 隻候選 → 人手覆核後約 8 隻可開新 thesis | 無 | `2026-07-10_discovery_radar.md` +`review_groupA-D` | settled |
| 39 | 逐 node 分邊檔(2-3x/3-5x)? | 15/15 覆蓋但**仲係草稿**,待大腦逐 node 覆核 | 無 | `2026-07-13_pernode_batch1-3_draft.md` | **open** |
| 40 | 記憶體超級週期見頂未? | 未見頂:趁弱加、唔追 gap;DRAM 合約價唔早過股價 | 描述性 | `2026-07-09_memory_supply_demand.md` +`07-13_dram_series_spotcheck` | settled |
| 41 | 邊個 setup 會被放大 5-10 倍? | **未答**:只建咗樣本庫,明示非最終模型 | 描述性 | `2026-07-09_magnifier_case_library.md` | **open** |

## §6 外部來源

| # | 問題 | 答案(≤25字) | 尺 | 正本 | 狀態 |
|---|---|---|---|---|---|
| 42 | Insider 買入有冇 edge? | 細價股 12 個月組合 +12%;21 日/群買廣度/市場買賣比全部冇 | 事件研究 | `2026-07-05_insider_literature.md` +`insider_breadth_and_market_ratio` | settled |
| 43 | Insider 做主題發現/接線? | 唔得:群買 <1 次/年,兩大主題零觸發;tilt 淨 display-only | 描述性 | `2026-07-08_insider_cluster_probe.md` +`07-12_insider_tilt_live` | settled |
| 44 | 跟順哥(KOL)有冇邊際? | 打和:中位超額 -0.00%,CapEff 輸 SPY 3.7pp;看空冇資訊 | 資本效率 | `2026-07-17_kol_shunge_roundtrip.md` +`bear_confound`/`exit_trailing` | settled ⚡§8-C |
| 45 | KOL 板塊講法啱唔啱? | 一半:1 部分成立、2 不成立、3 部分成立 | 事件研究 | `2026-07-16_sector_flow_claims.md` | settled |
| 46 | 邊個來源憑咩入管道? | 篩按來源類型;判斷源要 dated call;FOMO yield 2/10 | 無 | `2026-07-17_source_registry.md` +`fomosoc_ingest`/`altdata_census` | settled |
| 47 | 財報全文/全市場 transcript? | filing 劣過 transcript 唔好收;全市場塞得落但 **run 暫停中** | 描述性 | `2026-07-09_filing_vs_transcript_signal.md` +`fullmarket_transcript_scope` | **suspended** |
| 48 | 回購/盈利預期極端軸? | 回購僅大價股得且細唔做硬閘;盈利預期 P2 淨 display-only | IC | `2026-07-11_buyback_capital_allocation_signal.md` +`07-14_earnings_expectation_probe` | settled |

## §7 量度方法(呢節就係「尺」欄嘅根)

| # | 問題 | 答案(≤25字) | 尺 | 正本 | 狀態 |
|---|---|---|---|---|---|
| 49 | 訊號/sleeve 層應該用咩尺? | **資本效率+絕對 PnL**;除曝險後有料,Jensen alpha 錯層 | 資本效率 | `2026-07-03_topdays_exposure.md` | settled |
| 50 | 要幾多排序技術先贏? | IC≥0.05 先贏;實測所有量化因子≈0(價量 ML 得 0.017) | IC | `2026-07-01_skill_curve.md` +`alpha360_ml` | settled |
| 51 | 評分卡預測到乜? | 只預測風險,唔預測回報;CSP 嗰格例外 | 事件研究 | `2026-06-30_scorecard_validation.md` | settled |
| 52 | Oracle alpha 喺邊層捕到? | 年度 regime 捕到,週度唔得;高頻尾巴係可認事件唔係噪音 | 描述性 | `2026-07-01_oracle_forensics.md` +`gap_forensics`/`portfolio_oracle` | settled |
| 53 | 系統骨架/治理有冇債? | spine 四 phase 跑通;docs 5 檔 CONTRADICTS、入口鏈零覆蓋 | 無 | `2026-07-01_spine_phase0/1/2a/4.md` +`07-16_*_audit.md`(4 檔) | settled |

---

## §8 未和解嘅矛盾(**唔准當冇事**)

### A. RSI2 撈底 —— 兩個相反結論,兩把唔同嘅尺,冇人和解過 【live】

| 檔 | 講咩 | 尺 | 標籤(今日) |
|---|---|---|---|
| `2026-07-05_rsi2_capital_efficiency.md` | 「capital efficient across the board」大盤部署回報 32% vs B&H 17.1% | 資本效率 **vs B&H** | **仍然 `active — mechanism HIGH confidence`** |
| `2026-07-16_leader_dip_reversion.md` | RSI2 撈底冇料 | 事件研究 | 🛑 suspended(配置錯) |
| `2026-07-17_dip_capital_efficiency.md` | +550% 係 10 日封頂人工品 | 資本效率 | 🛑 suspended(配置錯) |
| `2026-07-17_rsi2_be_replication.md` | CapEff 229 vs **隨機同曝險** 219,p=0.69 → 分唔開 | 資本效率 **vs 隨機同曝險** | settled(**本檔判為正本**) |

**點解正本 = replication 而唔係 07-05**:
- replication **已經跑完**(77 隻、5 臂、1000 次 MC/隻/臂),唔係「重跑中」——兩份 🛑 橫額寫住「重跑中」係 **stale**,冇人返去更新。
- 兩者唔係同一把尺:07-05 用 **B&H** 做判官,replication 明文話 B&H 係錯判官,要用**隨機同曝險同交易次數**對照。換咗啱嘅判官,edge 驗唔出。
- replication 明文撤回 07-16/07-17 兩份嘅數字,但 **由頭到尾冇提過 07-05**(grep `07-05`/`rsi2_capital_efficiency` = **0 次**)。佢被 charter 去閂呢個矛盾,結果冇閂。
- 同 memory `metric-and-direction-discipline`(用戶 2026-07-17 明文裁「RSI2 買方死」)一致。

**未做嘅動作**(本檔唔改任何現有檔):① 撤 07-05 個 `active` 標籤,改指向 replication;② 更新兩份 🛑 橫額「重跑中」→「已跑完,判詞見 replication」。
**方向陷阱**:以上全部只講 **買方**。**賣方**(RSI2>90 賣 call)已驗證有料(#14)——唔好用一句「RSI2 冇用」蓋兩邊。

### B. 期權成本假設 —— m=0.85 【live,冇人提過】
`2026-07-09_options_chain_spotcheck.md` 判 **m=0.85 太低,應 1.00-1.15**;但 `2026-07-06_leap_real_sweep.md` 個 sleeve α **就係用 m=0.85 做基準**跑出嚟 → **LEAP 成本假設偏平,α 可能高估**。冇任何一份檔和解過。旁證:`2026-06-30_leap_timing.md` 自己掛住 🟡「倍數不可入帳,待真成本重跑」。→ #7 個 α 除咗尺錯層(⚠️),個成本基準都未修。

### C. 順哥 KOL —— 【已和解,記錄在案】
`kol_shunge_scorecard.md` 兩條核心結論(看多負 alpha)已自我撤回 = mirror 假象;正本 = `kol_shunge_roundtrip.md`。冇 live 矛盾。

## §9 尺錯層(⚠️)清單 —— sleeve/訊號層用咗 alpha

| 行 | 檔 | 錯咗乜 | 要點 |
|---|---|---|---|
| #7 | `2026-07-06_leap_real_sweep.md` | sleeve 層報 alpha | 判詞方向可能企得住,但**數字要用 CapEff+絕對 PnL 重量**;兼受 §8-B 成本基準污染 |
| #9 | `2026-06-30_csp.md` | sleeve 層報「冇 alpha」 | 「係 beta 唔係 α」呢個講法**本身就係攞錯尺**;未用 CapEff 重測過 |
| (已修) | `2026-06-30_rsi2_200sma.md` | 訊號層講「RSI-2 有真 alpha」 | 已被 `2026-07-17_rsi2_be_replication.md`(資本效率)取代;**舊檔個 alpha 講法唔好再引用** |

**注**:§1 全部 alpha(全組合)行**唔係**錯層 —— core v2 vs SPY net-TR 係全組合對照,用 alpha 啱。

## §10 未分類 / 待對數

- **未分類:無。** 145 個 `results/*.md` 全部有歸屬(表內 53 行 + §11 已取代清單)。
- **5 條 open,冇夾硬填**:#26(板塊約束語言)、#39(逐 node 草稿)、#41(magnifier)、#18(F&G 選股,suspended)、#47(全市場 transcript run 暫停)。
- **待 audit 對數**:`2026-07-17_false_negative_audit.md` 撰寫本檔時**尚未存在**(17 個 alpha×負面結論嘅覆審)。以上 ⚠️ 分類係我自己判嘅 —— audit 出咗之後**必須對數**,尤其 #7/#9 兩行同 §9。

## §11 已取代/已撤回 —— 唔好再引用結論

`2026-07-05_insider_rigor.md`(→#42)· `2026-07-09_constraint_language_report_scan.md`(→#29)· `2026-07-12_constraint_scan_production.md`(→#29)· `2026-07-11_category2_sentiment_reversal.md` + `_v2` + `_recovery_language`(→#35)· `2026-07-13_expectations_gap_v1.md` + `07-12_v0`(→#30)· `2026-07-16_leader_dip_reversion.md` + `2026-07-17_dip_capital_efficiency.md`(→#13)· `2026-07-17_kol_shunge_scorecard.md`(→#44)· `2026-07-05_phase2_flow.md` breadth 段(→#16)· `2026-06-30_rsi2_200sma.md`(→#13/#15)

---
*建立:2026-07-17 · 唯讀掃描 `backtest/results/*.md` 145 檔,冇改任何現有檔*
