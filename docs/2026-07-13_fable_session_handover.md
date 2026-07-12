# Fable 5 Session 交接書(2026-07-12/13)——俾 Opus 接手執行

> **呢個 session 做咗乜**:投資邏輯總審查(任務書 `docs/2026-07-12_fable_investment_strategy_brief.md`)
> → 用戶連環追問演化出 Karst-AA 新結構 + 估值模組 + 機會階梯,**全部決策有實測支撐**。
> 本檔 = 決策清單 + 證據指針 + 執行 backlog + 唔准重推名單。Opus 接手請照
> `~/.claude/playbooks/10-dispatch.md` 紀律行事(派工三件套/驗證不自驗/sonnet 預設 worker)。

---

## 1. 已拍板決策(全部有檔有數,唔使重新辯論)

| # | 決策 | 證據檔 |
|---|---|---|
| D1 | **遷移去 Karst-AA-strict 結構,三步走**:①即刻換殼(ballast trio + delta 總帳 + 0.50Δ LEAP 引擎 band 115,T sleeve 25% 暫用 QQQ 市場代理)②裁判 PASS(~10月)先換入真主題 ③跑順一季升 band 130。回頭條件:主題層持續 FAIL → 退返 core v2 | `docs/2026-07-12_all_active_design_response.md` §8/§8a(BT-2:`results/2026-07-12_bt2_aa_vs_core.md`,step-0 重現過閘,307k assert)|
| D2 | **AA-strict 贏 AA-pragmatic**(推翻孤立 ballast 測試嘅直覺):現金停泊蝕章,strict damp α +5.0pp t3.4 係唯一過 Bonferroni×48 嘅格 | 同上 §7 |
| D3 | **放寬約束(准 cash/准 SPY)重審後維持 AA-strict**:cash 停泊已測蝕 1.2pp;SPY↔防守輪動(W3)已測輸長揸;SPY 長揸=core v2 本人,純結構打和,決勝在 ratio/主題容量/swing 彈藥三點 | §8a/§8b + `results/2026-07-12_ballast_parking_ab.md` |
| D4 | **Ballast = XLP/XLU/XLV 留任** + 季度職責體檢機制(唔准 return-chasing 換籃);DIA 假設證偽(downside capture 92-98%、QQQ 相關全場最高);Mag7 做 ballast 熊市地台 109% 冇得減磅;稅漏 trio 0.86pp vs USMV 0.63pp(真但非決定性) | `results/2026-07-13_bt7_ballast_definition.md` + 設計檔 §8c 前置 |
| D5 | **Sizing 改 % NAV 制**(系統係自己嘅 portfolio manager,唔鏡射用戶個人組合;crypto 剔出範圍)+ **sizing v2 方向**:conf×magnitude 兩軸 + top-K 集中 + 最低注門檻(現行 linear-conf 三重 cap 有反排序 bug:conf 第 1 注碼排第 7) | `docs/2026-07-12_fable_investment_logic_review.md` §0/§3 P0-1 + `results/2026-07-12_sizing_two_axis_decision_analysis.md` |
| D6 | **估值模組 = expectations-gap**(P_base「supercycle 白送幾多」+ g_implied「現價要求幾快增長」),v0 已實跑 28 隻:15 主題 8 個「大部分係希望」、FSLR 唯一 0.83x 白送、USAC 個平一半係債務槓桿假象、GEV 隱含 155.8%/年 | `docs/2026-07-12_valuation_expectations_gap_spec.md` + `results/2026-07-12_expectations_gap_v0.md` |
| D7 | **裁判加第二把尺 milestone-Brier**(63d IC 有效闊度=主題數、horizon 錯配 1-3y thesis) | 總審查檔 §2.2/§3 P0-2 |
| D8 | **新 sleeve 候選 A/B/C/D + 機會階梯**(撞期優先序按市況分檔;每月機會預算上限);C 經用戶修正拆 C-core(SPY/QQQ LEAP 主力 70-80%)+ C-list(P_base>1 極端錯價配角) | `docs/2026-07-12_new_sleeve_candidates.md` + `docs/2026-07-12_opportunity_ladder.md` |
| D9 | **Dashboard v4 交付架構**:DASHBOARD.md auto-commit 上 private GitHub(手機 GitHub app render)+ Telegram bot 門鐘(05:55/20:30 推送);唔起雲 web app、唔用 GitHub Pages(私隱) | `docs/2026-07-13_dashboard_v4_portable.md` |
| D10 | 外部選股服務(Seeking Alpha 類)= discovery radar 候選餵料,過自己 admission 閘;唔直接配資(edge 唔外包) | 對話決策,記於 STATUS |

## 2. 執行 backlog(照優先序;全部 shadow/paper 先行,唯一例外見 P0-3)

**P0(即開工)**
1. **Dashboard v4 實作**(1-2 session):`thesis/dashboard_render.py` 聚合現有輸出 → DASHBOARD.md+PNG → auto-commit;Telegram bot(用戶自攞 token 落 `~/.config/karst/telegram`);驗收清單喺 v4 檔 §3。用戶最新確認嘅方向。
2. **B 測試已完成**(`results/2026-07-13_bt_b_washout_expression.md`,n=9 crisis-severe episode):
   同曝險口徑期權只贏 2-4/9(洗盤期 IV 貴 + theta/vol-crush)→「期權表達本質更優」**唔成立**;
   同本金口徑贏 8/9 純係槓桿(max DD 深好多)。**定案已入機會階梯:B 預設表達 = SPY 現貨細注
   2-3% NAV,期權僅作刻意加槓桿時嘅工具選項。** 剩餘工作:B 雷達燈接 dashboard v4(P0-1 一併)。
   Episode 重建 caveat:crisis-window 分組係透明重建(9 個落 8-12 範圍)但未逐個對號原作者名單,
   接手如要嚴格化可覆核。
3. **Crypto 治理**(總審查 P0-3,Phase-3 以外但 EV 最大):architecture §5 缺陷 #1,修法已寫,一個鐘。**呢項係唯一建議即刻郁真錢層面嘅嘢。**
4. **Sizing v2 落地為 shadow**:sizing.py 加 `--nav-pct` % 制 + conf×magnitude formula flag;同現行 linear 平行記帳兩季;修 WS5 §8 mf-cap 口徑 + 集中度 cut 反排序問題。

**P1(裁判首讀數 ~10 月前)**
5. milestone-Brier:每 theme wiki 加 2-4 條具名限期預測 + 30 行 scorer(D7)。
6. `thesis/valuation.py` production 化(v0→v1:E_norm revenue 項改 TTM/3 年中位,減週期頂 bias)+ **BT-5 判別力測試**(案例庫六案 ex-ante 全中先接 sizing 閘——判官預先寫死)。
7. A(優質股閃縮)完整 backtest 立項:事件庫 + transcript「過性 vs 結構」過濾器 + insider/回購確認 + solvency gate(house 4 股種標準)。
8. C-list 第一版:用 expectations-gap 現成輸出揀 20 隻複利機器 + 觸發價,簽名落檔。
9. D:DRAM 合約價序列 spot-check(MU 2016/2023 兩個校準點現成)。
10. AA 遷移執行細節(委託次序/LEAP 換月銜接/ballast 分段建倉)——等用戶落實遷移決定先做。

**P2**
11. BT-3(regime band 增量)/BT-4(washout boost 增量)——BT-2 機器現成。
12. Per-node schema 推廣:photonics → advanced-packaging → memory → space;oil-gas-energy 直接拆兩個 thesis 唔好 node 化。
13. china-supply hub page(四條線匯聚:rare-earth+us-solar 碲+MP capex 警號+AXTI);energy-macro 考慮拆標籤唔寫 hub。
14. 需求端反向驗證掃描(買家 transcript 呻缺貨,corpus FTS5 現成)。
15. 獲利回收 trim 規則(擁擠複合 top decile + 倉位 ≥2× 成本 → trim 1/3)paper 驗證。
16. MP capex/D&A 警號人手覆核(兩軸齊響 2.192x/2.540x,`results/2026-07-12_capex_da_supply_response_probe.md` 新發現,**未有人跟**);AMKR YoY 2.81x 記一筆。
17. Feature-5 擁擠複合(analyst 出席數 percentile + GS flow Z + bull-ratio;先修 NVDA 2025 parser)。

## 3. 唔准重推名單(本 session 新增,連同原有 20+ 回測結論)

- 現金停泊 / SPY↔防守輪動 / DIA 做 ballast / Mag7 做 ballast——四樣全部有數判死(D3/D4)。
- turnover 做擁擠 proxy(舊)/ 板塊層 constraint-language(舊)——維持判死。
- 「ai-capex 54.9% 爆錶」係誤讀:belief-weight ≠ 實際部署(39.2%,冇超 50% cap);決策語言用 kill-scenario VaR。
- BT-2 嘅 T sleeve 係零 alpha QQQ 代理——**唔准引用 BT-2 做「主題有 alpha」證據**;主題真 edge 判官係 forward IC/Brier。

## 4. 風險與誠實界線(接手者必知)

- **LEAP model 風險係全系統最大假設**(30d→1y IV proxy;真鏈 spot-check 顯示 0.70-0.80Δ 揹 skew premium)——所有 α 引用一律 base/damped 並列,operative 用 damped。
- 裁判 matured=0,首判決 ~10 月;之前所有 confidence 讀成「未校準排名分」。
- 判官/表達類新機制一律 pre-register 判官先跑數,唔准事後搬龍門。
- 夜班 headless 寫唔到工作目錄外(permission boundary,見 memory)。
- 用戶溝通:香港白話中文、大白話少術語(用戶 2026-07-13 明確要求 plain business words)。

## 5. 用戶未答/待用戶拍板

- AA 遷移正式開波日(結構層;設計已 §8 三步,等一聲令下)
- Telegram bot token(用戶五分鐘人手步驟)
- 套餐確認:「全動員」(AA+B/A/D+階梯)已係現行默認方向,用戶如改主意退「簡單機器」(core v2+B+C-core)亦係合法選項(設計檔 §8b)
