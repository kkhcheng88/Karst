# STATUS — Karst 現況(新 session 從這裡開始)

> **單一入口檔**。每個 session 結束時更新「現在在哪/下一步」兩節(取代散落交接)。
> 最後更新:2026-07-06。歷史細節不放這裡——放指針。

## 30 秒版:這是什麼

Karst = 每日 top-down 投資決策支援系統(NHITL 目標,**決策支援,人執行下單**)。
two-tier 輸出:SPY/QQQ/SPMO 用期權工具(LEAP/SHORT_CALL/CSP),其他個股只做多。
實證定位(20+ 回測):**價量訊號 = 風控,不是 alpha;alpha 唯一可能的門 = Phase 3
質性 thesis**。全系統的可證偽靶心:**thesis 排序 forward IC ≥ 0.05**。

## 現在在哪(2026-07-06)

**2026-07-06(Vanessa session)—— Phase-2 收官 + Trend-Core value-chain 更新 + Fable 交棒:**
- **Phase-2 大市層 flow 收官**(`results/2026-07-05_phase2_flow.md` + `_breadth_reversion.md`):DIX(慢 tilt,配 GEX)
  + **breadth 洗盤 reversion**(底 decile / ≤27% above50 → 21d +2.58% ≈3× baseline、短線 over VIX +2pp、**單邊**——
  洗盤會彈 / 見頂唔會即插、做空頂實證冇值、減 drift 後仍然;對實際股災底 GFC/COVID/2011/2022/2025 核實)。**修正**舊
  「breadth 冇用」(嗰個只對 LEVEL 線性成立)。淨結論:大市層 flow ≈ VIX 冗餘,只 DIX + 洗盤兩個小 tilt 加值 → 收官。
  餘下(板塊/子板塊 breadth + 背離 + 群體行為;大市層背離已證冇用)= Phase-3 rider,需 value-chain 成份定義。
- **Trend-Core(gooptions)re-scrape = Phase-3「3b 發現」loop**(commit `50bcb2e`):抓新 9 篇 #138-146 → 更新 5 個
  value-chain wiki。**AXTI「唯一便宜錨」糾正 3 處**(#141 蝕錢 / fwd PE 72.8× / 峰值盈利假象);新節點:光纖耦合、
  冷卻內化、HBM base-die 代工、tpu interactive;tpu 護城河再定義=「開源模型 GPU-shaped」非 CUDA。9 個 confidence 全部不變。
- **LEAP 擇時 = alpha 機制釐清(用戶點明)**:指數擇時分兩種——SPY 現貨 1:1 入出贏唔到 Jensen alpha(結構拖累中和 T1);
  **但 LEAP call(槓桿 + 非 benchmark 工具)= 唯一結構解**(finding #12),擇時有價值、曝險可低、槓桿放大真 +T1;
  代價 = 尾部風險,必須閘(>200SMA × RSI-2 dip × 恐懼)。→ core 期權層真.alpha 機制。
- **★ 下一步 = Fable 5 交棒**(見「下一步」+ `docs/2026-07-06_fable_brief.md`)。

**2026-07-05(Vanessa session)—— 風控/擇時層全面回測 + ebooks 蒸餾。4 份新結果檔 `results/2026-07-05_*.md`:**
- `fg_timed_capital_efficiency` · `meanrev_family` · `factor_families_momentum_lowvol_rs` · `breakout_momentum`
- **核心定案(高信心)**:
  - **價量/擇時層 = 風控/timing,唔係 alpha**(全面再確認)。**Capital-efficiency 係真但細嘅 T1 擇時 alpha**
    (`exp_alpha_decomp` T1 +2-6%/yr),兌現要靠個股表達/多-sleeve portfolio;大 alpha 仍靠 Phase 3。
  - **Momentum**:粗糙 SMA 誇大咗;正版 TSMOM = **downside protection(H2/跌浪先顯,H1平穩牛≈B&H)**;
    **最佳 timer = 20日高突破 > TSMOM > SMA**(兩半贏、修 H1;修返用戶「月lookback太慢」)。**已測未接線。**
  - **Mean-rev(RSI-2)**:regime-gated(高波)+ cap-gated(**micro dip=落刀**)+ **RS-leader filter 救返 H1 脆弱**。
  - **RS**:選 leaders 穩健(選股)、gate RSI-2(filter);LEVEL 係 edge、TREND 只對 dip-filter 反向有用。
  - **Low-vol/Vol**:低波選股非 alpha(防守);vol = **regime gate** 唔係引擎。
  - **突破 SELECTION(Minervini)/ risk-layer**:price-only 版無 alpha;**止蝕/trail 斬贏家傷回報 → 封尾部生存唔係 alpha**(caveat:無成交量確認未測)。
- **ebooks 蒸餾**:`ebooks/Discretionary Momentum/DISTILLATION-backtestable-rules.md`(O'Neil/Darvas/Livermore/Minervini common core + SPEC A-D;**在 Karst repo 外**)。
- **大市 2D regime 定案**(`results/2026-07-05_market_regime_2d.md`):**credit(HYG/LQD)做風險軸 = 失敗**
  (regime 反覆、對 VIX 無增量);**改用「VIX × 趨勢(200SMA)」2D = 成立**——② 牛市+高VIX 兩半前望最好
  (+5%)+ 回撤最淺,∴ **買恐懼優先喺上升趨勢做**;熊市買恐懼細注(方向 regime-dependent)。VIX 主軸、
  趨勢做安全度修正器。
- **未閉 gap**:突破加成交量確認(救 Minervini selection?);VCP 型態本身未測;GEX(Phase 0 fragility)未建;
  gamma 牆 + BofA Bull&Bear + trend×VIX 大市閘 forward-log。

**2026-07-04(Vanessa session,於 Claude Code 續)—— 詳見 `docs/2026-07-04_progress_and_next.md`:**
- **定位更正**:Karst = 獨立、自足系統(非三大腦執行臂、edge 不外包);`README`/`ARCHITECTURE`/`KARS_MEMORY`/`AGENTS` 已清 framing。
- **Backtest 全盤點完成**;insider + 四大家族重跑並存檔(`results/2026-07-04_insider_family_revalidate.md`,S&P500 離線版:RSI-2 long-only **+12.5%** 重現;insider 大型股 21d t2.30 / 63d t2.91,DSR 0.79)。兩者**未到「高」**(insider 只大型股;family 有 survivorship)。
- **修咗實驗檔 2 bug**:`_DATA` 路徑(reorg 後指錯)+ None 價格快取永不重抓。**weekly cron 冇壞**(寫 `thesis/`,未搬)。
- ⚠️ `px_defeatbeta.pkl` 全 None(死快取);sandbox 上唔到網攞唔到小型股價 → 需**本機 defeatbeta 重抓**(bug 已修,一 run 即補)。

**2026-07-03:**

- **已建**:spine Phase 0/1/4(市場閘/板塊/擇時,`python backtest/scan.py`)、
  thesis 9 主題 + forward-IC 每日排程、web dashboard(`web/`,可部署)、
  insider EDGAR 家族、20+ 回測結論(`backtest/results/`)。
- **剛完成**:全系統審查(`docs/2026-07-03_*.md` 三份)→ 抓到 **P0 級接線問題,
  未修**:① insider `conf_eff` 算了但從未接回分數;② credit 軸/兩軸背離已驗證卻
  完全缺席;③ 校準迴路是斷的(outcome 回填程式不存在);④ IC≥0.05 只是文字非程式。
- **已核准開工**(用戶 2026-07-03):`docs/ROADMAP_AGENTIC.md` 全部。
- **用戶事實**:香港稅務居民(無 CGT、美股股息 30% 預扣)→ 稅後比較用 HK 參數。
- **workspace 已重組**(2026-07-03):37 個實驗檔移入 `backtest/experiments/`
  (含索引),本檔成為唯一入口。

## 下一步(2026-07-06 更新)

**★ 主線 = Fable 5 交棒**(`docs/2026-07-06_fable_brief.md`):Fable 做 **adversarial reviewer + 策略主腦**(loop
engineering、自主、每 ~5 loop 報進度、用量有限、spawn 平價 sub-agent 做手腳)。任務 1-5 優先:① 驗 wiki + 底層邏輯;
② 找 gap / 衝突 → 補跑;③ 砌 **core portfolio 策略**(SPY/QQQ/SPMO 期權 + Sector ETF 擇時/現金,**誠實用 Jensen alpha
對 SPY B&H**、scenario 執行 + backtest);④ **LOOP 只喺任務 3**(其餘一次過交付);⑤ 結果可係**策略樹(多策略)+ 明確 transition 機制**(唔一定單一策略)。之後:⑥ dashboard
設計、⑦ Phase-3 方法論審查、⑧ emerging bottleneck。**framing:core(大盤+板塊 ETF)= 大部分資金;Phase 3 = 衛星
(高風險高回報);core 真.alpha = LEAP 擇時 + 賣保費 + 資本效率,唔係 SPY 現貨入出。**

**策略主線(研究層,仍有效)**:風控/擇時層特徵已徹底釘死(見上)→ **重心轉 Phase 3 thesis + forward-IC**(唯一 alpha 門)。
**可選接線**(風控層):① 20日高突破 timer 入 `spine/timing.py`;② RSI-2 × RS-leader gating;③ vol/VIX regime 開關。
**可選補測**:突破 + 成交量確認(唯一未閉 gap);VCP 數值代理;GEX(Phase 0)。

---

### (2026-07-04 下一步,仍有效)

**即刻(Vanessa 本機,有 defeatbeta):** 2 bug 已修,run 以下即補小型股價、重現全宇宙:
```
python backtest\experiments\exp_insider_validate.py
python backtest\experiments\exp_family_validate.py
```
完成後更新 `results/2026-07-04_insider_family_revalidate.md`(全宇宙 insider 預期 21d t≈5.12)。

**升級到「高」(rigor):** ① 選股類 point-in-time 除 survivorship;② 期權類 BSM+成本+walk-forward(到中高,無真實期權鏈);③ VCP + 大盤擇時補存檔;④(可選)出總表:測咩｜結果｜可信度｜點升級。

**清理(可選):** `reference/README.md`、`invariants/`、`params/` 殘留的 Compass / 三大腦 framing。

---

### (前 ROADMAP Phase A/B 次序,仍有效)

1. **A1 校準資料流**(統一 track_record schema + `log_predictions` 進排程 +
   outcome 回填)——每天不修就流失一天不可補的資料
2. **B1 持久化價格庫**(parquet + as-of manifest)——與 A1 並行
3. A2 credit 軸+兩軸背離 → A3 insider 改接 21d tilt → B2 paper ledger(詳 ROADMAP)

## 東西在哪

| 要做什麼 | 去哪 |
|---|---|
| **懂整個系統(layman 全貌 wiki,由此入)** | **`docs/KARST_WIKI.md`** |
| **★ Fable 交棒任務書(adversarial review + 砌 core 策略)** | **`docs/2026-07-06_fable_brief.md`** |
| 懂整個系統(技術版真相) | `ARCHITECTURE.md`(跨 Phase 地圖,single source of truth) |
| 風控/擇時層結算(標準化量度+逐訊號+決策矩陣) | `docs/2026-07-05_risk_control_layer_report.md` |
| 開工 roadmap | `docs/ROADMAP_AGENTIC.md`(A1-D6,含驗收條件) |
| 懂「為什麼要修/為什麼不做」 | `docs/2026-07-03_strategy_methodology_review.md`(P0-P3 + 反建議) |
| 改 dashboard | `docs/2026-07-03_dashboard_decision_experience.md`(逐面板規格+錨點) |
| 跑每日掃描 | `python backtest/scan.py [--json]`;dashboard:`web/README.md` |
| 找/跑/寫回測實驗 | `backtest/experiments/README.md`(37 實驗索引+慣例) |
| 回測結論 | `backtest/results/*.md`(dated;經 experiments 索引反查) |
| thesis 層操作 | `thesis/DESIGN.md` + `.claude/skills/thesis/SKILL.md` |
| 歷史決策/坑 | `.agents/KARS_MEMORY.md`(§1-10) |
| 期權/timing 參數 | `params/`(帶 ✅/📄/⚠️ tag;注意 PMCC 已於 v3.1 移除) |
| 風控鐵律 | `invariants/systematic_rules.md`(INV-5/8/9 已進程式,其餘文件層) |
| agent 工作制度 | `~/.claude/playbooks/`(調度/判斷/模板/維護) |

## 新 session 閱讀順序(按任務)

- **接續開發**:本檔 → `docs/ROADMAP_AGENTIC.md` → 對應程式碼
- **做研究/回測**:本檔 → `backtest/experiments/README.md`(慣例+索引)→
  memory `validation-mirror-and-increment`(鏡子/增量/horizon 三原則)
- **懂系統**:本檔 → `ARCHITECTURE.md` → `.agents/KARS_MEMORY.md`
- 2026-07-03 當日研究細節:`HANDOFF.md`(該 session 的詳細交接,已被本檔取代為入口)

## 維護規則

- session 結束:更新本檔「現在在哪/下一步」;新結論落 `backtest/results/` 或 `docs/`;
  重大決策/坑 append 到 `.agents/KARS_MEMORY.md`。
- `.agents/sessions/` 日誌已停用(2026-07-01 起由 KARS_MEMORY §8-10 + 本檔取代)。
- 別讓兩套入口再分岔:**AGENTS.md 的 Read-first 指向本檔,本檔指向其他一切。**
