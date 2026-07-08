# Gap / 衝突登記冊 v2 —— 獨立重掃(取代同日 sandbox 版)

> **性質**:任務 2 交付物(Fable brief §4)。獨立 adversarial 重掃(掃描員禁讀 2026-07-06 舊產出),
> 主腦裁定 + **即場修復可修項**。**本檔取代** `docs/2026-07-06_gap_conflict_register.md`(sandbox 版)。
> 掃描範圍:STATUS / ARCHITECTURE / ROADMAP_AGENTIC / 2026-07-03 methodology review /
> 2026-07-05 risk report / KARS_MEMORY / KARST_WIKI / experiments README,對照全部 2026-06-30~07-05
> 結果檔 + spine/thesis 程式碼。合併任務 1(wiki 驗證 v2)嘅遺留項。

## 1. P0(影響交易決策/工程方向)—— 4 項,3 項已修 1 項排期

| # | 問題 | 判定 | 狀態 |
|---|---|---|---|
| P0-a | **insider 修法文字寫錯方向**:ROADMAP A3 + methodology review P0-1 + ARCHITECTURE §6 仍寫「改接 21d 戰術 tilt」,但 21d 版已被 `insider_rigor` R8 證實 regime-fragile(大型股全樣本 t1.1);定案 = **細價 <$2B 12 個月 portfolio tilt vs IWM**(`insider_literature` FINAL)。照舊文字執行會做錯方向。 | 21d 版唔採 | ✅ **已修**(ROADMAP A3 行、review 修法段+優先表、ARCHITECTURE §6)|
| P0-b | **STATUS.md 尾段「仍有效」列住已作廢嘅 A2 credit 軸**(credit 07-05 已剔除)+ 舊 A3 講法 | 殘留 footer | ✅ **已修**(STATUS.md 尾段)|
| P0-c | **insider `conf_eff` 計咗從未接入 score**(`expression.py:66` 只用 `thesis.unit`;`spine/__init__.py:13` code 自認)——insider 而家 display-only | 屬實、現行未修 | ⏳ **排期**:= ROADMAP A3 工程(方向已修正做 12月版);任務 3 core 策略完成後做,接線前必須 A/B 增量回測過 DSR |
| P0-d | **校準迴路斷裂**:兩個 schema 唔一致嘅 logger 寫同一 `track_record.jsonl`;outcome 回填 code 全 repo 唔存在(`log_predictions.py:64` 永遠 None);`forward_ic.report()` 無 PASS/FAIL 程式判定(IC≥0.05 只喺 docstring) | 屬實、現行未修;全系統最大單一 P0(唔修 = confidence 校準只係設計文字,每日流失不可補資料)| ⏳ **排期**:= ROADMAP A1;同上,工程項 |

## 2. P1(影響研究優先序)—— 已修

| # | 問題 | 狀態 |
|---|---|---|
| P1-a | ARCHITECTURE §6 仍列「GEX → Phase 0」做待建缺口,但 §3 同檔已寫「測完唔建」(07-05 `gex_test` partial≈−0.08)| ✅ 已修(§6 該行標已測唔建)|
| P1-b | `params/layer1_options.md` 參數同 `options_engine.py` 對唔上:CSP DTE 30↔21、LEAP roll 90↔63(KARS_MEMORY 記低咗但源頭檔冇改)| ✅ 已修(params 檔加勘誤 banner,以 code 為準)|

## 3. P2(文檔衛生)

| # | 問題 | 狀態 |
|---|---|---|
| P2-a | experiments README 孤兒計數錯(寫 7+3,實際 5+4)| ✅ 已修(連同 P2-b 修正後 = 5 孤兒 + 2 準孤兒;**2026-07-06 補跑 P2-d/P2-e 後再減至 3 孤兒 + 2 準孤兒**,見下)|
| P2-b | `exp_family_validate` / `exp_insider_validate` 索引仍寫「結論在 ARCHITECTURE/HANDOFF」,實際已落檔 `2026-07-04_insider_family_revalidate.md` | ✅ 已修(索引指向結果檔,升 active)|
| P2-c | 孤兒:`exp_pmcc`(死功能,PMCC 已下架)/ `exp_sector_timeframe` / `exp_rescue_forensics`(無下游引用)| 維持孤兒標記,唔補跑(低價值)|
| P2-d | 孤兒:`exp_portfolio_rotation`(疑被 rotation_challenge 吸收,「存疑」拖咗幾日)| ✅ **已補跑落檔**(真 yfinance 數據,2026-07-06):`backtest/results/2026-07-06_portfolio_rotation.md`。判定:**非 duplicate**——測嘅係唔同 variant(weekly cross-sectional momentum + cash fallback,vs rotation_challenge 嘅 monthly dual-mom + bond fallback),數字唔同,但**verdict 一致**(冇 causal 輪動邊際贏 SPY/EW);新增發現:bonds > cash 做防守腳。README 狀態行已改 active。|
| P2-e | 孤兒:`exp_minervini_validate`(verdict 只印 console;現行 Minervini 結論來自另一實驗 `_breakout`,有檔)| ✅ **已補跑落檔**(2026-07-06):`backtest/results/2026-07-06_minervini_validate.md`。修咗一個路徑 bug(`_DATA` 少咗一層 dirname,2026-07-03 reorg 後其他姊妹檔都已對齊,呢個漏咗)先跑得郁——**冇改實驗邏輯**。判定:**PARTIAL 弱**(per-trade excess vs SPY 全格正,但 Sharpe 只得 0.12-0.16、win率31-34%);**發現 script 自己嘅 DSR 呼叫係構造性 bug**(傳 12 個相同值嘅陣列入 `deflated_sharpe_ratio`,std=0 → 恆為 nan)——已披露、冇修。**唔升級** `_breakout` 嘅負面判定,兩檔分工已喺結果檔寫清。README 狀態行已改 active 🟡。|

## 4. 覆蓋洞(自認未測,文檔已一致反映 —— 非新問題,登記留底)

| # | 洞 | 排期建議 |
|---|---|---|
| H-1 | VCP 量縮維度未測(cache 無 volume)| 低優先(VCP 本身 negative)|
| H-2 | 突破 selection 缺成交量確認 —— risk report 自認「唯一未閉 gap」,可能救返 Minervini selection | 中;要救 selection 就測呢個 |
| H-3 | 板塊內部/子板塊 breadth 未測(要 value-chain member map)| 跟 Phase 3 基建 |
| H-4 | insider opportunistic vs routine 分類(Cohen-Malloy,估計 ~4× 放大)—— 要 owner ID 歷史 | insider v3 |
| H-5 | gamma 牆無歷史回測(vendor 無歷史 OI)→ forward-log 驗證 | 維持;夠樣本後 retrospective |
| H-6 | 防守板塊 tilt portfolio 級從未測(wiki §7.1 已標未接線)| **任務 3 board 上**(用戶 steering:板塊三角度之一)|
| H-7 | (任務 1 遺留)`exp_lowvol_family` 細價/板塊 vol-timer 數只喺 console 從未落檔 | ✅ **已補跑落檔**(2026-07-06,真 yfinance 數據):Addendum 加喺 `backtest/results/2026-07-05_factor_families_momentum_lowvol_rs.md` 尾;KARST_WIKI §5.6 該行同步更新為實數。判定:**細價股 ❌ 明確唔 work**(48 格 46 輸 B&H)、**板塊 ETF 🟡 regime-dependent**(H1 幾乎全輸、H2 幾乎全贏,唔穩健)——同大盤/Mag7(穩健)反差大;原「vol=regime gate 唔係 alpha」判定不變,加咗「唔係全宇宙一致」嘅 caveat。|
| H-8 | (任務 1 遺留)+12.5pp long-only headline 無直接 DSR(0.908 係 21d long-short mirror 檢定)| 可選;引用時帶註(wiki 已註)|
| H-9 | (任務 1 遺留)§八 155%/196%(1999-2026)vs 151.5%(2002-2026)唔同窗口易誤會 | 已知,低優先 |

## 5. 正面確認(掃描中核實「文檔=code」一致嘅位)

- 2D quadrant / vol-switch / 突破 timer / RS-leader gate:**確認未接線**,wiki §7.1 v2 講法同 code 一致
- credit 軸推翻已喺 6 份主檔正確反映(sandbox agent 嗰批改動屬實)
- Minervini「選股無 alpha」現行引用來源正確(`_breakout` 有檔,唔係懸空嗰個 `_validate`)

## 6. 修改記錄

2026-07-06 已修檔案(全部有 `~/.claude/backups/*.2026-07-06.bak` 備份):STATUS.md、ARCHITECTURE.md、
docs/ROADMAP_AGENTIC.md、docs/2026-07-03_strategy_methodology_review.md、params/layer1_options.md、
backtest/experiments/README.md。詳細掃描表(20 項逐行 file:line):session scratchpad `task2_E_register.md`,
重要判定已全部併入本檔。
