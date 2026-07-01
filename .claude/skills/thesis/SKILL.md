---
name: thesis
description: >-
  Operate and maintain the Karst Phase-3 thesis layer (thesis/) — the qualitative offense that
  produces a calibrated CONFIDENCE (not human "belief") per ticker and feeds the spine's
  thesis_quality seam. Use to add/update a theme, INGEST an analyst report / KOL post / web
  research into a cited thesis, recompute confidence + cycle_stage, run maintenance (lint), or
  log predictions. NHITL: confidence is evidence-derived + calibrated; the track record is the
  AGENT's own log, not a human diary. Read thesis/DESIGN.md first for the full design.
---

# thesis — Phase 3 qualitative offense (NHITL)

The edge (empirically established, `backtest/results/2026-07-01_*.md`) is qualitative: reading
regime + catalyst + supply/demand — information NOT in price charts. This layer turns that into a
**confidence** score that multiplies tier-2 eligibility into sizing. **Always read `thesis/DESIGN.md`
first** (the full blueprint) — this skill is the operating procedure.

## Where things live
- `thesis/DESIGN.md` — the design (read first). `thesis/README.md` — structure.
- `thesis/themes.yaml` — machine-readable registry (`spine/providers.thesis_quality` reads it): a
  theme -> {confidence, cycle_stage, verdict, kill_condition, tickers, wiki}.
- `thesis/wiki/<slug>.md` — the synthesis page: 4-KPI evidence (cited) + confidence derivation +
  cycle_stage + kill + `[[wiki-links]]`.
- `thesis/.raw/` — raw fed reports/posts (immutable, for citation/audit). Distil FROM here INTO wiki.
- `thesis/track_record.jsonl` — the AGENT's self-monitoring log (`thesis/log_predictions.py` writes it).
- Raw corpora at scale (news/transcripts) live in DBs/APIs (defeatbeta, later FNSPID+FTS), NOT the vault.

**Wiki page format (MUST):** frontmatter = valid-YAML SCALARS only (slug, type, cycle_stage,
confidence, verdict, updated, tickers). **NEVER put `[[wiki-links]]` in YAML frontmatter** — `[[` is
a flow-seq start and breaks the parser. Put `[[links]]` INLINE in the body (Obsidian graphs those);
cite sources inline per claim. `python thesis/lint.py` flags invalid frontmatter.

## Non-negotiable discipline (why this isn't FOMO)
1. **Confidence, NOT belief.** `confidence = f(4-KPI scores, #independent sources, distance-to-kill,
   payoff-asymmetry, regime-fit)` — every input traceable to cited evidence. Never a gut number.
   Mark it `INITIAL/uncalibrated` until `track_record` calibrates it (DESIGN §6).
2. **Cite everything.** Every claim carries source + quote (+ doc/date). No source -> not in the wiki.
3. **Tier the source.** Tier-1 primary (transcripts/filings/prices/financials) = evidence. Tier-2
   analyst report / KOL = OPINION to VERIFY, not truth. Tier-3 news = event/timing signal.
4. **A report/KOL being bullish is itself a CROWDING (Tier-3) signal.** If everyone is bullish on X,
   that is late-stage / priced-in -> the cycle gate should LOWER confidence (like the DRAM-ETF-launch
   crowding signal on memory). Note "how consensus is this" during ingest.
5. **Falsifiable kill_condition required.** State what would make the thesis wrong. Price only after
   the thesis is confirmed (USER.md rule).
6. **Priced-in gate.** Reject already-run consensus: valuation percentile at a historical top +
   supply responding (capex boom) + crowding -> late / priced-in -> temper or skip.
7. **Track record is the AGENT's log, not a human diary** (NHITL): the system logs its own
   predictions + back-fills outcomes to self-calibrate (DESIGN §6). A human only reads a derived
   summary at the narrow "adopt a NEW thesis type" gate.

## The thesis thinking loop (NHITL — adapted from claude-obsidian /think, with FEEL removed)
`/think`'s human-emotion step ("FEEL") is antithetical to a system built to REMOVE human emotion.
Use this NHITL loop instead when forming/updating a thesis:
1. **OBSERVE** — gather CITED evidence (transcripts / financials / the fed report / web), full-read,
   never from memory.
2. **CLASSIFY** — regime (VIX/rates/inflation cell), cycle_stage (early/mid/late), event-type,
   A(crisis) vs B(supercycle).
3. **SCORE (4-KPI)** — moat/bottleneck, capital-allocation/ROIC (capex trend), valuation/priced-in
   (`ttm_pe` percentile, own-history), growth-durability/TAM. Each 0-2, each cited.
4. **FALSIFY** — write the kill_condition (Tree hypothesis).
5. **PRICE** — the priced-in / cycle gate (valuation extreme + supply response + crowding).
6. **COMPUTE CONFIDENCE** — from the above; ACCEPT irreducible uncertainty (mark uncalibrated; size
   small; the kill bounds the downside; payoff is convex). NOT a feeling.
7. **CONNECT** — write/update `thesis/wiki/<slug>.md` with `[[links]]` to concepts/companies/chains;
   run `thesis/lint.py`.
8. **LOG** — register in `themes.yaml`; run `python thesis/log_predictions.py` (the agent logs itself).

## Workflow A — INGEST a report / KOL post / web research (add or update a theme)
Adapted from claude-obsidian `/autoresearch` (3-round loop) + the legal-MCP `research_cases`
pattern (concept -> search -> harvest -> synthesise). The user feeds a report (paste / file / URL).
1. **Land the raw** in `thesis/.raw/<slug>-<source>.md` (immutable, for citation). Full-read it.
2. **Extract typed + cited claims** mapped to the 4-KPI. Tag each as Tier-1/2/3. Note the report's
   own bullishness as a crowding signal.
3. **Verify** the verifiable claims against primary sources (defeatbeta `earning_call_transcripts`,
   `quarterly_cash_flow` capex, `ttm_pe`, `roic`, `quarterly_revenue_by_breakdown`). Optionally
   web-research (WebSearch/WebFetch) for gaps — broad round, then gap-filling round.
4. **Run the thinking loop** (above) -> confidence + cycle_stage + kill.
5. **Write/update** `thesis/wiki/<slug>.md` (cited, `[[]]`) + register in `thesis/themes.yaml`
   (tickers, confidence, cycle_stage, verdict, kill, wiki path). If the theme brings NEW tickers,
   add them to `backtest/spine/universe.yaml` (a thematic group) so the scan covers them.
6. **Verify end-to-end:** `python backtest/scan.py` shows the tier-2 cards with the thesis; then
   `python thesis/log_predictions.py` records the predictions.

## Workflow B — MAINTAIN / continue (adapted from /wiki continue + /wiki-lint)
- `python thesis/lint.py` — broken `[[]]` links, orphan pages, and STALE/PENDING flags (unchecked
  `[ ]` evidence items in a thesis, or a cycle_stage that the latest data contradicts).
- Re-verify any thesis whose kill_condition may have fired, or whose cycle_stage signals changed
  (new capex data, a new thematic-ETF launch, valuation moved to a new percentile) -> update confidence.
- Surface theses whose `待補` evidence is still open and fill it (like memory's capex/ttm_pe).

## Tools
- Scan: `python backtest/scan.py [--json]` (the front door; tier-2 shows thesis confidence + cycle).
- Log: `python thesis/log_predictions.py` (agent appends predictions to track_record.jsonl).
- Lint: `python thesis/lint.py`.
- Data: defeatbeta via `backtest/data.py` + direct `Ticker(sym).<method>()` (fundamentals/transcripts/
  news/ttm_pe/capex). Web: WebSearch / WebFetch. Retrieval (later): the VR-style FTS engine.

## Honest reminders (surface to the user)
- Cold start: confidences are INITIAL/uncalibrated until the track record accumulates (months, ~20-30
  theses). Read them as disciplined relative strength × cycle temperature, not precise probabilities.
- Ideas from reports are usually CONSENSUS (not novel foresight) — the priced-in + cycle gates guard
  against chasing run themes. The edge is being early + disciplined + risk-managed, not the idea.
- Do NOT install claude-obsidian (Claude-Code-bound + external dep); this native skill + thesis/README
  + DESIGN + scripts are the agent-portable, git-versioned equivalent. Use Obsidian (the app) only to
  VIEW the `thesis/` vault graph if desired.
