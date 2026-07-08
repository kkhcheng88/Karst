# Gap / 衝突登記 + 解決(Fable 任務 2)【SUPERSEDED】

> ⛔ **本檔已被取代**(2026-07-06 同日):用戶下令棄用斷網 sandbox run 嘅產出、獨立重掃。
> 新版 = `docs/2026-07-06_gap_conflict_register_v2.md`。本檔留檔可溯,唔好再引用。

> **做咗乜**:三路審計——① cross-doc 衝突掃描(6 份主 doc 對 34 份 results + STATUS 07-06 真相);
> ② code 接線真相審計(12 條 claim 逐條對 spine/thesis/params 原始碼);③ 補跑缺失回測(LEAP delta sweep)。
> 每項標明:**已修** / **已登記待接線** / **已補跑**。姊妹檔:`2026-07-06_wiki_verification.md`(任務 1)。

## 1. 衝突 —— 已修(本次直接改檔)

| # | 衝突 | 檔 | 修法 |
|---|---|---|---|
| F1 | 「Phase 0 gate:VIX/credit/RV(已有)」— credit 07-05 已剔除仍當 live | risk_control_layer_report L51 | 改 VIX×趨勢 2D + 註明剔除 |
| F2 | insider「大型股 21d/63d 顯著」無 caveat(63d 其實 t0.95 唔顯著;21d 拉長到 2006 冧到 t1.1) | risk_control_layer_report L45 | 改為細價 12月主 claim + 大型 2022+-only |
| F3 | 「credit > VIX(KC Fed RORO)」舊結論無 forward-pointer | strategy_methodology_review L46 | 加 2026-07-06 更正框(P0-2 修法作廢) |
| F4 | ROADMAP A2 仲叫人起 credit 軸 | ROADMAP_AGENTIC A2 | 標 OBSOLETE,改為接 2D quadrant 邏輯 |
| F5 | insider t=5.12 做 headline 冇拆解 caveat(micro-cap tail) | ARCHITECTURE L111 | 補拆解 + 「或停用」選項 |
| F6 | RSI-2 +12.5% 冇 DSR 0.908<0.95 caveat | ARCHITECTURE L115-118(+ wiki §2/§3.2 任務 1 已修) | 補 |
| F7 | **wiki 講「vol regime 開關已 live」= 假**(spine 完全冇 switch;timing.py 只有 RSI-2;得研究版 exp_rsi2_vix_regime) | KARST_WIKI §7.1 | 改「未接線」+ 註明證據 |
| F8 | wiki Phase 0「✅ 已 live」誇大——**2D quadrant 邏輯未入 spine**(context.py 兩個 input 分開存在,fragile 係 OR 邏輯,無 interaction) | KARST_WIKI Phase 0 狀態 + §7.1 2D row | 改 🟡 input live / 閘未接 |
| F9 | KARS_MEMORY §10「credit>VIX」為事實、§12 冇更正 | KARS_MEMORY | 新增 §13 撤銷/降級清單 |
| F10 | §7.1 2D row 恐懼側寫「VIX/F&G 高」——違反 fg_vs_vix 收官分工 | KARST_WIKI | 改淨 VIX(任務 1 A5 系列) |

## 2. Code 接線真相(audit 12 條;code 唔改——排優先次序係策略/roadmap 決定)

| # | 項 | 判定 | 證據 |
|---|---|---|---|
| C1 | insider `conf_eff` 接回分數 | **算咗、冇接**(display-only) | orchestrator.py:48 算;expression.py:66 score 用 raw `thesis.unit`;spine/__init__.py:13 自認 P0-1 |
| C2 | 校準迴路 outcome 回填 | **不存在** | log_predictions.py:64 全部 `outcome: None`;全 repo 無 backfill;**另發現:兩個唔一致 logger 寫同一 track_record.jsonl**(forward_ic.py:62-81 vs log_predictions.py:39-73,schema 唔同)→ 修 A1 時要先統一 |
| C3 | forward IC ≥ 0.05 | 算到、**冇 enforce**(prose target,無 PASS/FAIL) | forward_ic.py:168/176 |
| C4 | credit 軸喺 code | 正確地**冇**(同剔除結論一致) | context.py:54-115 無 HYG/LQD |
| C5 | VIX×趨勢 2D 閘 | **PARTIAL**:input 有、quadrant 邏輯無 | context.py:62-88(獨立欄位,fragile=OR);quadrant 只喺 exp_trend_vix_axis.py |
| C6 | 20日突破 timer | **無**(同 doc 自述一致) | timing.py 只有 RSI-2(L15-28) |
| C7 | RSI-2 × RS-leader × 高波 gate | **無(RSI-2 裸奔)** | timing.py:15 淨 close+固定閾值;sector.py is_laggard 只係 advisory 文字 |
| C8 | F&G 恐懼側喺 spine | 正確地**冇**(context.py:16 明文排除) | — |
| C9 | vol regime 引擎開關 | **無**(→ F7 wiki 假 claim) | spine 無 switch、無動能引擎可切 |
| C10 | scorecard v3.1(LEAP=>200SMA×dip、PMCC 除名) | ✅ WIRED | scorecard.py:52/56;params/layer1_options.md:8-12 |
| C11 | Phase-2 DIX/washout tilt | **無**(schemas 無欄位) | 只喺 exp_dix_ic.py |
| C12 | 期權參數 | WIRED,但 **doc↔code 唔對辦**:CSP DTE doc 30 / code 21;LEAP roll doc 90 DTE / code 63;engine 仲留住 PMCC 函數(scorecard 已除名) | options_engine.py:21-23/77/135/192 vs params/layer1_options.md:38/81 |

**→ 接線 backlog(依任務 3 策略需要排序,唔係全部要做)**:
P0 = C5(2D quadrant——策略樹 transition 靠佢)+ C2(校準迴路,日日流失數據);
P1 = C6+C7(兩個已證 timer 接入)+ C12(param 對齊);
P2 = C1(等 insider 重定位決定:短 tilt 或停用)+ C11(DIX/washout 細 tilt)。

## 3. 已補跑 —— LEAP delta sweep(缺失回測,任務 3 直接用)

**背景**:所有舊 LEAP 回測淨係測過 0.80Δ;0.3/0.5/0.8 對比喺 `regime_and_iv` 明文列「未做」。
用戶記憶「backtest 話 0.3 最好」查實 = **short call 條腿嘅 0.30Δ/21DTE**(`shortcall_timing`),唔係 LEAP。

**結果**(`results/2026-07-06_leap_delta_sweep.md`,DRAFT;script `exp_leap_delta_sweep.py`):
- **0.80Δ deep-ITM 全面贏**:4 delta × 3 gate × 2 frame × IV/成本敏感度,**0.80Δ 每格 Sharpe 第一**,
  兩半(1996-2010/2011-26)+ 子分割(2016-20/2021+)全部成立。
- 機制:0.30Δ 槓桿高 2.4×(13.3x vs 5.6x)但 **theta 損耗高 8×**(119%/yr vs 14%/yr)——extrinsic 比例
  越大,decay 增長快過凸性收益;sleeve 級 0.3/0.5Δ 直接爆倉(MaxDD≈−100%,連最好嘅 gate 都救唔返)。
- PORTFOLIO frame(10% NAV premium + 90% cash,GATED+DIP,0.80Δ):CAGR 6.49%、Sharpe 0.89、
  MaxDD −12.9%、**Jensen alpha +4.29%/yr(t3.8)** vs SPY B&H TR(9.69%/0.58/−55.8%)。
- **Caveat(嚴)**:SPY-only、RV-proxy IV(sandbox 攞唔到 VIX)、flat vol;**skew 方向不利本結論**
  (deep-ITM 真實會貴少少、OTM 平少少)但 8× theta 差距冚得住;**magnitude 未 bankable,ranking 係交付物**。
  本機重跑 command 喺 results 檔尾。

## 4. 覆蓋洞(登記,未解決)

| # | 洞 | 去向 |
|---|---|---|
| G1 | 突破 + 成交量確認(cache 無 volume;唯一可能救 Minervini selection) | 需本機數據,掛起 |
| G2 | RSI-2×RS-leader gate、vol-switch、突破 timer 唔喺 ROADMAP 任何 tracked 任務入面(孤兒 recommendation) | 已入 §2 backlog;ROADMAP 下次 revision 收編 |
| G3 | 兩半定義跨檔唔一致(§3.3 = 2016-20/2021+;2d 檔用 1993-2009/2010+;gex 用 <2019/2019+) | 記錄在案;新回測跟 §3.3 標準 |
| G4 | sandbox 攞唔到 QQQ/VIX/板塊 ETF 價(Yahoo/FRED/stooq 403)→ 任務 3 嘅 sector 檢驗要用 SPY+505 隻成份股 approximation,或本機補跑 | 任務 3 設計已考慮 |
