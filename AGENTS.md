# AGENTS.md — for any coding agent (Claude Code / Roo Code / Codex)

Karst = an independent, self-contained fully-automated agentic investment decision system — it finds
its OWN edge (Phase 3 built in-house) and runs the full decision pipeline; Compass/Tree/Reference are
external reference material only, not dependencies. Agent-agnostic entry points so
a fresh session (any agent) knows how to operate and MAINTAIN it. Communicate with the user in
Traditional Chinese (technical identifiers/tickers/code in English).

## Read first (project state + design)
- **`STATUS.md` — START HERE.** 單一入口:現在在哪、下一步、東西在哪、閱讀順序。
  (2026-07-03 起取代散落交接;session 結束要更新它。)
- `ARCHITECTURE.md` — **the cross-phase system map (single source of truth)**: the top-down funnel,
  the signal-family → Phase placement + the "in-price vs not-in-price" firewall, built/stub/deferred
  status, and the honest signal-family assessment. Read this to understand the whole system.
- `docs/ROADMAP_AGENTIC.md` — 已核准的實施計畫(Phase A-D);`docs/2026-07-03_*` — 全系統審查
  (原 P0 接線問題清單)。**2026-07-16 覆核狀態**(動 spine/thesis 前先睇,唔好照單全收「未修」):
  ① insider `conf_eff` **仍未接分,真.未修**(`backtest/spine/__init__.py:13`、`expression.py:66`);
  ② credit 軸/兩軸背離 **已作廢**(2026-07-05 判死剔除,`STATUS.md:199-201, 284`);
  ③ 校準迴路 **已修**(`thesis/backfill_outcomes.py` + `thesis/daily_ic.cmd` 已排程,log_predictions
  = the ONE writer);④ IC≥0.05 判定 **已程式化**(`thesis/forward_ic.py:44` `PASS_MEAN_MIN` + `judge()`
  狀態機)。只有 ① 仲係真 gap。
- `.agents/KARS_MEMORY.md` — long-term project memory (decisions, current status).
- `.agents/USER.md` — who the user is + work preferences (adversarial thinking, evidence-first, NHITL).
- `README.md` — repo定位.

## Daily engine (the spine — built)
- `python backtest/scan.py [--json]` — the top-down scan: market gate → sector temp → two-tier
  router → RSI-2 timing → thesis confidence → sizing. Code in `backtest/spine/`.
- Studies/evidence: `backtest/results/2026-07-01_*.md` (why quant = risk control, edge = qualitative).

## Phase 3 — thesis layer (qualitative offense, NHITL)
- **Design:** `thesis/DESIGN.md` (read before touching the thesis layer).
- **How to operate/maintain it:** the `thesis` skill (`.claude/skills/thesis/SKILL.md`) — add/update
  a theme, INGEST a report/KOL/web into a cited thesis, recompute confidence + cycle_stage, lint,
  log predictions. Claude Code auto-discovers it; other agents: read that SKILL.md as the procedure.
- Structure: `thesis/README.md`. Registry `thesis/themes.yaml`. Pages `thesis/wiki/*.md`. Raw fed
  sources `thesis/.raw/`. Agent log `thesis/track_record.jsonl` (+ `thesis/log_predictions.py`).
  Lint `thesis/lint.py`.
- **現行規則(2026-07-15/16 凍結,`thesis/DESIGN.md` §4a-§4c)**:confidence = **§4a 凍結公式輸出**
  (4-KPI rubric + penalty 表 + single-source cap 0.30),**唔准手工推導**,`thesis/lint.py` P2 formula
  check 機械把關(誤差 >0.01 = error)。**§4b red-team 協議**:INGEST = 審判,夜班 Level-1 永遠唔准向上
  郁 confidence,moat/growth 攞 2 分前提 = 經 Level-2 red-team 生還——**15/15 active theme 已完成
  Level-2 red-team**(`backtest/results/2026-07-1[56]_redteam_*.md`)。**§4c 三通道分流**:red-team 判決
  只准入通道 1 subscore / 通道 2 cap 資格 / 通道 3 magnitude 加成,唔准喺 confidence 數字酌情。新工具:
  `confidence_formula.py` / `composite_score.py` / `kill_metrics.py` / `magnitude_features.py`。

## Core discipline (do not violate)
- **NHITL:** the system is no-human-in-the-loop. Output a CONFIDENCE (evidence-derived + calibrated),
  never human "belief". The track record is the AGENT's own log, not a human diary.
- Every claim cited; tier the source (transcript/filing = primary; analyst report/KOL = opinion to
  verify + a crowding signal); falsifiable kill_condition; priced-in / cycle gate.
- Evidence-first, adversarial (do not flatter); every number has a source; verify, don't assume.

## Do NOT install claude-obsidian
The `thesis` skill + `thesis/README` + `DESIGN` + scripts are the native, agent-portable, git-
versioned equivalent. Obsidian (the app) may be used ONLY to VIEW the `thesis/` markdown graph.
