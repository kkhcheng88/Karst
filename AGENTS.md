# AGENTS.md — for any coding agent (Claude Code / Roo Code / Codex)

Karst = the WHEN/HOW execution + params of an investment system. Agent-agnostic entry points so
a fresh session (any agent) knows how to operate and MAINTAIN it. Communicate with the user in
Traditional Chinese (technical identifiers/tickers/code in English).

## Read first (project state + design)
- `ARCHITECTURE.md` — **the cross-phase system map (single source of truth)**: the top-down funnel,
  the signal-family → Phase placement + the "in-price vs not-in-price" firewall, built/stub/deferred
  status, and the honest signal-family assessment. Read this to understand the whole system.
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

## Core discipline (do not violate)
- **NHITL:** the system is no-human-in-the-loop. Output a CONFIDENCE (evidence-derived + calibrated),
  never human "belief". The track record is the AGENT's own log, not a human diary.
- Every claim cited; tier the source (transcript/filing = primary; analyst report/KOL = opinion to
  verify + a crowding signal); falsifiable kill_condition; priced-in / cycle gate.
- Evidence-first, adversarial (do not flatter); every number has a source; verify, don't assume.

## Do NOT install claude-obsidian
The `thesis` skill + `thesis/README` + `DESIGN` + scripts are the native, agent-portable, git-
versioned equivalent. Obsidian (the app) may be used ONLY to VIEW the `thesis/` markdown graph.
