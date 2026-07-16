# docs/ 41 檔唯讀盤點審計【2026-07-16】

> **性質**:唯讀審計,冇修改/刪除任何檔案。清理動作由 gatekeeper 決定同執行。
> **動機**:過去兩日(2026-07-15/16)系統有重大演進(confidence 公式凍結、全部 15 個 active
> theme 完成 red-team、sizing v2 三通道接線),`docs/` 41 個舊設計文件可能已被取代或同現行
> 規則矛盾,會誤導將來嘅 agent(包括即將加入嘅 Codex adversarial reviewer)。

---

## 1. 方法

### 1a. 現行事實基準(用嚟判斷過時/矛盾,全部逐一核實過)
1. `thesis/DESIGN.md` §4a:confidence 公式已凍結(2026-07-15)——
   `confidence_raw = (Σ 4-KPI subscores)/8 × penalty(crowding_band, cycle_stage)`,
   單源封頂 0.30,4-KPI 每格 0/1/2 有書面 rubric 錨點,`thesis/lint.py` 機械檢查
   themes.yaml 記錄嘅 confidence 必須等於公式輸出。
2. `thesis/DESIGN.md` §4b:INGEST 升級做 red-team 協議(2026-07-15)。全部 15 個 active
   theme 已完成 Level-2 red-team(`backtest/results/2026-07-1[56]_redteam_*.md`,15 份)。
3. `thesis/DESIGN.md` §4c:red-team 判決標準化做三通道分流(subscore/cap資格/magnitude加成),
   `thesis/sizing.py` v2 已接線 channel 3(`magnitude_unconfirmed`,2026-07-16)。
4. P1-P5(`docs/2026-07-15_quantification_review.md`)全部已實作:composite_score.py(P1)、
   confidence_formula.py + lint 機械檢查(P2)、magnitude_features.py(P3,F2/F3/F5 機械化)、
   kill_metrics.py(P4)、entry/exit block(P5)。
5. `thesis/valuation.py`(expectations-gap,P_base+g_implied)已 production 化 v1,BT-5 判別力
   6/6 全中,已接入 **週度**排程(`Karst-valuation-weekly`,SUN 09:15,經 schtasks 直接查證)。
6. 15 個 theme 全部已收編;per-node schema 已推廣到 photonics-optical/advanced-packaging/
   memory-supercycle/space-satellite(5/15,連 ai-power-grid worked example);oil-gas-energy
   仍未拆分(`thesis/themes.yaml` line 904 直接查證,拆分提案仍待用戶拍板)。
7. Karst-AA(全風險組合)遷移狀態:`thesis/aa_strict_paper_tracker.py` docstring 明文
   「PAPER (no real capital)…before any real-money migration decision」;`STATUS.md`
   確認「AA 遷移(#25 blocked)」。即**真金遷移連決策都未拍板**,core v2 仍是現行 live 資金策略
   (`Karst-playbook-daily` 05:40 每日仍在跑)。
8. `thesis/sizing.py` 現行(2026-07-16)實測:argparse 只有 `--budget`(美元制),**冇** `--nav-pct`;
   v2 shadow 亦係 $ 制 + `$V2_MIN_POSITION` 地板。

### 1b. 掃描方法
- `git log --date=short` 取得全部 41 檔嘅最後改動日期。
- 全部 41 檔:用 Read 工具逐份讀畢全文(大檔分段 read,唔淨睇頭 40 行——矛盾通常喺內文具體
  數字/建議,唔喺標題)。主 agent 直接讀畢 14 檔(Phase-3 WS1-5/transition_plan、INDEX、
  quantification_review、oilgas_split_proposal、三份 fable 文件);另外 27 檔(magnifier 文獻
  cluster 8 檔、早期歷史+misc cluster 14 檔、sleeve/valuation/clist cluster 5 檔)分派俾三個
  並行 Explore subagent,帶同一份「現行事實」基準逐檔核對,回傳結構化判斷 + 行號證據。
- **Orphan 查核**(主 agent 親自做,唔假手 subagent):用 Grep 工具全 repo 搜尋每個檔名字串
  (排除 `.claude/worktrees/`噪音同 `thesis/corpus.db` 11GB 二進位檔),分 4 batch(各 10-11個
  pattern)confirm 邊啲檔完全冇被任何 code/其他 doc 引用。
- 每個 CONTRADICTS/SUPERSEDED 判斷都交叉查證咗實際程式碼/排程/資料(themes.yaml、
  sizing.py、valuation.py、aa_strict_paper_tracker.py、opportunity_ladder.py、schtasks、
  STATUS.md),唔淨係比對文件之間嘅文字。

---

## 2. 41 檔分類總表

標籤:🔴CONTRADICTS(最危險)· 🟠SUPERSEDED · 🟡STALE(過時但有史料價值)·
🟢CURRENT(仍準確)· ⚪ORPHAN(冇人引用,獨立於準確度判斷)

| 檔名 | 最後改動 | 分類 | 理由(證據) | 建議動作 |
|---|---|---|---|---|
| `2026-07-15_quantification_review.md` | 07-15 | 🟢CURRENT | P1-P5 提案全部已實作(commit記錄逐一對應) | 加一句「已全部落地,見 DESIGN.md §4a-4c」 |
| `2026-07-13_oilgas_split_proposal.md` | 07-13 | 🟢CURRENT | themes.yaml 查證仍係單一 oil-gas-energy theme(line 904),提案仍未執行,文件自身反覆強調「PROPOSAL ONLY」 | 唔使動;建議 STATUS.md 待辦清單提一筆防遺忘 |
| `2026-07-08_phase3_architecture.md` | 07-13 | 🟢CURRENT | line 74 已 inline update「2026-07-13判定:非缺陷,已撤回」,自我維護得宜 | 唔使動 |
| `2026-07-08_phase3_ws1_calibration.md` | 07-09 | 🟡STALE | 標「設計定稿,待執行」,但 STATUS.md 確認 Batch 1 全套已跑 live(migrate_track_record.py 已跑、judge()出PRELIMINARY、lint 0 error) | 加 header「已執行完成,見 thesis/forward_ic.py」 |
| `2026-07-08_phase3_ws2_crisis.md` | 07-09 | 🟢CURRENT(部分接線) | grep 確認 playbook_readout.py 已有 ARM/ENTER(12處);設計本身冇矛盾 | 加接線狀態註腳 |
| `2026-07-08_phase3_ws3_lifecycle.md` | 07-12 | 🟡STALE | §1a「ai-capex 54.9%>50% EXCESS WARNING」讀數後被 fable_session_handover 澄清為「誤讀:belief-weight≠實際部署39.2%」,兩檔並讀會誤導 | 加 cross-ref 指向澄清出處 |
| `2026-07-08_phase3_ws4_early_detection.md` | 07-09 | 🟢CURRENT(部分接線) | constraint-language scanner 已生產化(有排程);儀錶盤部分未完全接線但冇矛盾 | 唔使動 |
| `2026-07-08_phase3_ws5_expression.md` | 07-13 | 🟡STALE | §9 具體數字($6,443/31%/space 5.35)係 07-13 snapshot,已被 07-15/16 confidence公式凍結+channel 3 接線蓋過 | 加 §10 指向 DESIGN.md §4c 做最新狀態 |
| `2026-07-08_transition_plan.md` | 07-12 | 🟡STALE | 🔒PERSONAL,快照日 07-08,持倉必已變動 | 低優先,已標記個人檔,可留或整份歸檔 |
| `2026-07-12_fable_investment_logic_review.md` | 07-13 | 🟡STALE | P0-P3建議大部分已落地(sizing v2/milestone-Brier/valuation v1/crypto治理已判定非缺陷) | 加 header「建議已大部分執行,見 DESIGN.md+sizing.py v2+valuation.py v1」 |
| `2026-07-12_fable_investment_strategy_brief.md` | 07-12 | 🟡STALE | 任務書,任務已完成(輸出=logic_review.md);§2「magnifier打分刻意維持人手」呢句部分過時(F2/F3/F5已機械化) | 加 header 指向完成產出+現況 |
| `2026-07-13_fable_session_handover.md` | 07-13 | 🟡STALE | D1-D10決策+backlog大部分已完成,但§5「待用戶拍板」5項(AA遷移/oilgas拆分/valuation閘語意/china-supply重標籤)仍開放 | 加 header 分清邊啲已做/邊啲仍待拍板 |
| `docs/INDEX.md` | 07-12 | 🟡STALE | 自稱「更新:2026-07-09」,完全冇索引 2026-07-13/07-15 共 15 個檔(clist_v1/dashboard_v4/quantification_review/oilgas_split/confidence formula等) | **需要重寫更新**,唔係加 header 咁簡單 |
| `2026-07-09_magnifier_model_plan.md` | 07-12 | 🟡STALE | §E「feature 5冇proxy、維持人手」嘅結論摘要已被 magnitude_features.py 部分推翻;per-node schema 進度(得ai-power-grid一個)已過時(現5/15) | 加指向 quantification_review.md §1c 嘅 header |
| `2026-07-09_magnifier_literature.md` | 07-12 | 🟢CURRENT | 純學術文獻回顧,冇對現行系統狀態作斷言 | 唔使動 |
| `2026-07-09_text_and_smartmoney_methodology.md` | 07-12 | 🟢CURRENT | 純文獻回顧,同「不採用分析師目標價」現行結論一致 | 唔使動 |
| `2026-07-11_magnifier_book_capital_returns.md` | 07-12 | 🟢CURRENT | 資本週期框架蒸餾,冇系統現況斷言 | 唔使動 |
| `2026-07-11_magnifier_book_expectations_investing.md` | 07-12 | 🟡STALE | §1.5/§3「書冇提供自動化答案、仍要人手做」已被 thesis/valuation.py(production v1)填補 | 加 header 指向 valuation.py 現況 |
| `2026-07-11_magnifier_book_one_up_on_wall_street.md` | 07-12 | 🟢CURRENT | 純業界框架蒸餾,自我約束「只列方向,唔設計公式」 | 唔使動 |
| `2026-07-12_magnifier_scorecard_rubric.md` | 07-12 | 🔴**CONTRADICTS** | §10/§11 用「正式拍板」「已經落實,唔再係open item」宣稱 feature 5 冇量化proxy、打分機制永久人手判斷——已被 magnitude_features.py(P3,機械化F2/F3/F5)直接推翻 | **優先加警示 header**(見§3) |
| `2026-07-09_ima_extraction_prompts.md` | 07-12 | 🟢CURRENT | IMA 操作手冊,同現行「不採用分析師目標價」一致,誠實標注人手限制 | 唔使動 |
| `2026-07-03_dashboard_decision_experience.md` | 07-05 | 🟠SUPERSEDED | 被 `2026-07-12_dashboard_design_v3.md` 明文取代(v3 line 3-4 自述) | 建議移入 `docs/_archive/` |
| `2026-07-03_strategy_methodology_review.md` | 07-09 | 🟡STALE | 已含07-06就地修訂,但P0-3「校準迴路斷/回填程式全庫不存在」、P0-4「IC≥0.05係文字非程式」兩條最重警號已被後續實作大幅修正,冇更新標記 | 加 header 指向 STATUS.md+DESIGN.md現況 |
| `2026-07-04_progress_and_next.md` | 07-05 | 🟡STALE | insider/family重驗方向已被gap_conflict_register_v2定案取代 | 加 header 指向定案出處 |
| `2026-07-05_gamma_walls.md` | 07-05 | 🟢CURRENT | 純工具/理論reference,KARST_WIKI仍引用做權威來源 | 唔使動 |
| `2026-07-05_risk_control_layer_report.md` | 07-09 | 🟢CURRENT | 風控/擇時層結算報告,結論未被推翻 | 唔使動 |
| `2026-07-06_core_strategy_v2.md` | 07-12 | 🟢CURRENT(需cross-ref) | STATUS.md確認每日仍live跑,但完全冇提Karst-AA平行候選(已完成紙上驗證、等用戶拍板) | 加header提醒讀者並讀all_active_design_response.md |
| `2026-07-06_gap_conflict_register_v2.md` | 07-09 | 🟡STALE | 一次性稽核交付物,P0-d(校準迴路)已大幅推進但排期狀態未更新;P0-c(insider未接sizing)依然屬實 | 加header分清邊條仍屬實 |
| `2026-07-06_wiki_verification_v2.md` | 07-09 | 🟡STALE | 07-06 wiki一次性稽核,07-12後Phase-3新機制未經同等規模重驗 | 加header註明涵蓋範圍 |
| `2026-07-07_core_playbook.md` | 07-09 | 🟢CURRENT | core v2配套SOP,同每日排程完全對應 | 唔使動 |
| `2026-07-12_dashboard_design_v3.md` | 07-13 | 🟡STALE | 五條設計原則+四行骨架仍生效(v4自己承接),但具體欄位已被v4擴充/取代 | 加header註明骨架仍用、細節看v4 |
| `2026-07-13_dashboard_v4_portable.md` | 07-13 | 🟢CURRENT | STATUS.md直接引用做現行production機制 | 唔使動 |
| `docs/KARST_WIKI.md` | 07-09 | 🔴**CONTRADICTS** | 自認「更新:2026-07-06 v2」;line 168「9個Type-B thesis已建但未證」同現行「15個theme全部red-team完成」直接矛盾;line 165-166/173「打分數做sizing乘數」「未證(全系統嘅賭注)」完全冇反映confidence公式已凍結+sizing v2三通道 | **優先加警示header**(見§3) |
| `docs/ROADMAP_AGENTIC.md` | 07-09 | 🔴**CONTRADICTS** | 全部4個Phase標題寫「狀態:未開始」,但A1(校準資料流)/A3(insider接線)/B2(paper ledger)/B5(dashboard)已完成或大幅推進 | **優先加警示header**(見§3) |
| `docs/finance-method-distillation-spec.md` | 07-02 | 🟢CURRENT | 獨立通用skill規格,同Karst策略演進無關 | 唔使動 |
| `2026-07-12_new_sleeve_candidates.md` | 07-13 | 🟡STALE | 候選A「值得完整回測」已完成且**FAIL**,文件未反映;**被`thesis/opportunity_ladder.py`逐行引用做規格來源** | 加header列四候選現況;**不可刪除/大搬動**(code行號依賴) |
| `2026-07-12_opportunity_ladder.md` | 07-13 | 🟡STALE | A候選列仍寫「完整backtest必須,冇藉口跳過」,實際已完成且FAIL,表內B/A新舊不一致;**被`thesis/opportunity_ladder.py`逐行引用做規格來源** | 加header註明A列過時;**不可刪除/大搬動**(code行號依賴) |
| `2026-07-12_valuation_expectations_gap_spec.md` | 07-13 | 🔴**CONTRADICTS** | line 46「排程:季度」vs 實際`Karst-valuation-weekly`週更(schtasks查證);line 51-52「sizing閘鎖watch 0.5% NAV/P_base<0.4」vs 實際`sizing.py`係P_base<0.20 halving、$制非%NAV制 | **優先加修訂header**(見§3) |
| `2026-07-13_clist_v1.md` | 07-13 | 🟡STALE | 本身已有謹慎簽名紀律語言,但20隻股票觸發價快照已比valuation_report.json最新時間戳(07-15)舊,可能已飄移 | 加footer「啟用前須重跑valuation.py確認」 |
| `2026-07-12_all_active_design_response.md` | 07-13 | 🔴**CONTRADICTS** | §8「即刻」祈使語氣寫「賣SPY底倉、砌AA-strict殼」,但`aa_strict_paper_tracker.py`docstring明文「PAPER no real capital…before any real-money migration decision」+STATUS.md「AA遷移#25 blocked」;§2.1「sizing全部%制,$41k作廢」vs`sizing.py`實測仍係`--budget`美元制,冇`--nav-pct` | **優先加修訂header**(見§3) |
| `2026-07-13_source_expansion_survey.md` | 07-13 | ⚪ORPHAN | 全repo grep零引用(排除worktree噪音),連commit message都冇提及;內容本身(SEC EDGAR/TrendForce/Utility Dive/DIGITIMES/SIA top-5建議)準確,且TrendForce已見於themes.yaml/多份red-team引用做非正式證據來源 | 需人判:歸檔定係正式接入(見§5) |

**分類統計**:🔴CONTRADICTS 5 · 🟠SUPERSEDED 1 · 🟡STALE 18 · 🟢CURRENT 16(含2份部分接線)·
⚪ORPHAN 1(內容本身CURRENT,只係冇引用)。合計 41。

---

## 3. CONTRADICTS 詳述(最危險,逐個矛盾點)

### 3.1 `docs/KARST_WIKI.md` —— 全庫風險最高單一文件之一

呢份係「layman 全貌 wiki」,官方定位係新人/新 agent 理解成個系統嘅入口,但自認最後大修訂
「2026-07-06 v2」,同現行(2026-07-16)嘅 Phase-3 狀態有直接矛盾:

- **Line 168**:「**驗證咗**:9 個 Type-B thesis 已建;**但未證**(forward IC 要累積幾個月)」
  —— 現行事實:**15 個** active theme(唔係 9 個)全部已完成 Level-2 red-team(2026-07-16),
  confidence 公式已凍結(2026-07-15)。數目錯咗,「未證」嘅語氣完全冇反映呢兩日嘅重大進展。
- **Line 165-166**:「**做乜**:讀價格圖裡冇嘅嘢……形成投資論點,**再打分數做 sizing 乘數**」
  —— 呢個描述停留喺「半公式/簡單分數乘數」年代,完全冇反映 `thesis/DESIGN.md` §4a-4c 嘅
  精確公式(4-KPI/8×penalty、單源封頂0.30、red-team三通道分流、sizing v2 magnitude加成)。
- **Line 173**:「**狀態**:✅ 已建 / ⏳ **未證**(全系統嘅賭注)」—— 「未證」定性同 confidence
  公式已凍結+red-team全套完成+sizing v2三通道已接線(2026-07-16)嘅進度不符。

**風險**:新 agent(尤其 Codex adversarial reviewer)如果將呢份 wiki 當做權威現況,會誤以為
Phase-3 仍處於早期未驗證階段,浪費時間重新質疑已經解決咗嘅問題,或者用舊嘅「9個thesis/簡單
乘數」心智模型去理解一個而家已經有精確公式嘅系統。**Phase 0/1/4(風控/擇時層)嘅段落本身
依然準確**(同`2026-07-05_risk_control_layer_report.md`一致),矛盾集中喺 Phase-3/confidence
相關段落,唔係全文報廢。

### 3.2 `docs/ROADMAP_AGENTIC.md` —— 全部 Phase 標題「狀態:未開始」已失實

四個 Phase 標題(line 22/37/50/68)全部寫「狀態:未開始」,但實際:
- **A1**(統一track_record schema+回填job,line 28):STATUS.md 確認 `forward_ic.py judge()`
  已出PRELIMINARY、`migrate_track_record.py`已run過、`lint.py admission gate`0 error——**大幅完成**。
- **A3**(insider改接細價股12月tilt,line 30):`Karst-insider-tilt-weekly`已註冊排程 live 產出——
  **部分完成**(仍未接sizing.py)。
- **B2**(paper ledger v0,line 44):`thesis/paper_ledger.py`已建成並在跑。
- **B5**(dashboard決策條/翻轉警示,line 47):dashboard v3/v4已實現並每日運行。

**風險**:文件內 A2 一項有就地劃線標「OBSOLETE」嘅先例(證明呢個文件本身有被局部修訂嘅習慣),
但四個 Phase 嘅頂層「狀態」欄從未同步更新——新 agent 掃一眼標題會以為系統仲喺規劃階段初期,
完全睇唔出實際已經進入 Phase-3 全面上線後嘅營運階段。

### 3.3 `docs/2026-07-12_all_active_design_response.md` —— 最危險:可能觸發未拍板嘅真金動作

- **§8(line 243-247)**:用「**即刻** → 裁判首讀數(~10月)」祈使語氣寫「**賣 SPY 底倉**,砌
  AA-strict 殼(ballast trio + delta總帳 + 0.50Δ LEAP引擎)」。
- **實際狀態**(`thesis/aa_strict_paper_tracker.py` docstring 第1-4行):「daily PAPER
  (**no real capital**) NAV tracker…run in PARALLEL with core v2's existing live signals
  for a period **before any real-money migration decision**」;`STATUS.md`:「AA遷移
  (**#25 blocked**)」——真金遷移**連決策本身都未拍板**。
- **§2.1**:「Sizing全部%制:`sizing.py`嘅$41k/$20k/$15k參數作廢,改`--nav-pct`模式」——
  實測 `thesis/sizing.py` argparse(line 33、364-365)只有 `--budget`(美元制,預設$41,000),
  **完全冇`--nav-pct`呢個選項**,v2 shadow 亦係$制。

**風險**:如果將來 agent(或人)未 cross-check `STATUS.md`/paper tracker 就照本檔字面執行
「即刻賣SPY底倉」,會誤觸發一個用戶都未拍板嘅真金組合結構性遷移——呢個係全部 41 檔入面
**唯一有可能直接導致誤操作真錢**嘅矛盾,優先級最高。

### 3.4 `docs/2026-07-12_valuation_expectations_gap_spec.md`

- **Line 46**:「排程:**季度**(財報季後跑一次)」—— 實際 `Karst-valuation-weekly` schtasks
  查證係 **Weekly, SUN 09:15**(同STATUS.md「SUN 09:15週更已註冊」一致)。
- **Line 51-52**:「Sizing閘(% NAV制):…該theme注碼上限鎖watch級(0.5% NAV)…(P_base<0.4)」
  —— 實際 `thesis/sizing.py` line 89-91 邏輯係 **P_base<0.20 觸發減半**($制,非%NAV制,
  亦冇「g_implied>thesis聲稱增長」呢個AND條件)。

**風險**:中高——執行語意描述同實際程式碼行為唔一致,如果將來 session 想核對「sizing閘做緊乜」
會被呢份文件誤導,以為機制已經係%NAV制且門檻係0.4。

### 3.5 `docs/2026-07-12_magnifier_scorecard_rubric.md`

- **Line 178-181/183/196-198**:「Feature 5 **正式維持質性判斷**……**明確唔用turnover做替代**」
  「**設計決定(2026-07-12,用戶確認)**……**唔會寫成`thesis/magnifier_score.py`呢類自動輸出
  分數嘅結構化工具**」「呢個決定已經**落實**,唔再係open item」。
- **實際**:`thesis/magnitude_features.py`(P3,commit "feat: magnitude-tier computed features
  F2/F3/F5 + consistency flags")已將 F2(估值headroom)/F3(距底部)/F5(情緒擁擠)三個特徵
  機械化,只有 F1(新事實強度)/F4(樽頸位置)保留人手判斷。

**風險**:呢個係「用最強肯定語氣關閉一個之後其實重開並完成嘅工作項」——如果 agent 信呢份
文件,會誤以為 magnifier scoring 完全冇機械化工具,可能會重複「查證」已經做完嘅事,或者
忽略 `thesis/magnitude_features.py` 呢個現成工具。§1-9(rubric定義、MU/FSLR/STP校準案例)
本身依然有實證價值,矛盾集中喺 §10-11。

---

## 4. 建議動作清單

### 4a. 建議移入 `docs/_archive/`(跟現有 2026-07-12 慣例,唔係刪除)
- `2026-07-03_dashboard_decision_experience.md`(已被 v3→v4 明文取代,SUPERSEDED)

### 4b. 優先加警示 header(危險程度由高至低)
1. `docs/2026-07-12_all_active_design_response.md` —— 標明 AA 遷移未拍板、sizing 仍係$制
2. `docs/KARST_WIKI.md` —— 標明 Phase-3/confidence 段落嚴重落後,一律以 DESIGN.md §4a-4c 為準
3. `docs/ROADMAP_AGENTIC.md` —— 標明各 Phase 實際完成度,唔要信「狀態:未開始」字面
4. `docs/2026-07-12_valuation_expectations_gap_spec.md` —— 標明排程/sizing閘已被實作取代
5. `docs/2026-07-12_magnifier_scorecard_rubric.md` —— 標明 §10-11 已被 magnitude_features.py 部分推翻
6. `docs/INDEX.md` —— 需要實質重寫(缺 15 個檔嘅索引),唔係加一句 header 夠

### 4c. 其餘 STALE 檔(18份):建議統一加一行「歷史記錄,現行見 X」header,唔使大改內文
(名單見上表 🟡STALE 欄;當中 `2026-07-12_new_sleeve_candidates.md`同
`2026-07-12_opportunity_ladder.md` **格外小心**——兩者被 `thesis/opportunity_ladder.py`
逐行行號引用做規格來源,加 header 只可以喺文首/文尾加,唔可以插入內文令行號漂移。)

### 4d. Orphan
- `docs/2026-07-13_source_expansion_survey.md`:內容準確、有具體可執行嘅 top-5 資料源建議
  (SEC EDGAR全文API/TrendForce/Utility Dive RSS/DIGITIMES RSS/SIA),但零引用。TrendForce
  已見於 themes.yaml 同多份 red-team 報告(非正式、人手 WebFetch 引用),其餘 4 個建議源
  未見任何正式接線痕跡。**需人判**:(a)歸入 backlog 正式實作 SEC EDGAR API/RSS 自動抓取,
  或 (b)確認唔做就移入 `_archive/` 但保留內容(避免下次又重新調研一次同樣嘅候選)。

---

## 5. 未解/需人判

1. **`docs/2026-07-13_source_expansion_survey.md` 嘅去留**——內容有價值但從未被正式接線,
   建議動作已列(§4d),最終「做定唔做」需要人判。
2. **`docs/2026-07-08_transition_plan.md`(🔒PERSONAL)**——快照日 07-08,用戶實際持倉狀態
   截至 07-16 好可能已變動(例如AXTI trim、crypto決定執行)。呢份文件涉及真實持倉數字,
   本審計冇查證用戶戶口現況,係咪應該更新/整份歸檔需要人判。
3. **`docs/2026-07-12_all_active_design_response.md` 同 `2026-07-13_fable_session_handover.md`
   提到嘅「AA 遷移」——呢個結構性決定(core v2 → Karst-AA)本身仍然懸而未決**(用戶未拍板
   「即刻換殼」呢一步),本審計只負責指出文件同現況嘅矛盾,唔負責替用戶做呢個決定。
4. **`docs/2026-07-08_phase3_ws3_lifecycle.md` 嘅 ai-capex 54.9% 讀數框架**——本身冇明確
   「講錯」,只係同後續澄清(belief-weight≠部署額)放埋一齊會有誤導風險,呢類「框架陳舊但
   非直接矛盾」嘅案例定唔定義做 CONTRADICTS,見仁見智,已在表中標 STALE 並要求加 cross-ref,
   如果 gatekeeper 認為應該升級做 CONTRADICTS 亦合理。
5. **INDEX.md 嘅重寫工作量**——本審計判斷佢需要「實質重寫」而唔止加 header,但重寫嘅具體
   內容(邊 15 個新檔應該點分類擺入邊個章節)超出本次唯讀審計範圍,建議另開一個任務處理。

---

## 附:orphan 查核方法備忘(供覆核)

用 Grep 工具(ripgrep)分 4 batch,每 batch 用 OR-pattern 一次過搜尋 10-11 個檔名字串,
排除 `.claude/worktrees/**`(repo 內一個完整副本,會造成雙倍噪音)同 `thesis/corpus.db`
(11GB 二進位 SQLite FTS 檔,ripgrep 自動跳過二進位但體積太大會拖慢首次掃描)。首次無排除
worktree 時,單一 grep -r 命令曾因為 11GB corpus.db 同雙倍檔案樹在 2 分鐘內 timeout,
改用 Grep 工具(非 shell grep)+ 精準 glob 排除後,4 個 batch 各於數秒內完成。逐一確認
40/41 檔至少喺一處(code docstring/其他doc/STATUS.md/.agents/KARS_MEMORY.md)被引用,
唯一零引用者為 `2026-07-13_source_expansion_survey.md`。
