# Public research reader

Scope: D12 / P1 human-facing delivery. The user approved public investment analysis on GitHub Pages, maintained by agents, with reading as the primary interaction. The user subsequently made the repository public and explicitly accepted that visibility; confirmed via GitHub on 2026-09-18.

## Ownership and source of truth

- Karst research versions, evidence and calculation receipts remain the agent-facing research record. The static site is a public reading projection, not a research engine or another database.
- `reports/<kind>/<slug>/<publication-date>-r<N>.json` contains explicitly authored public prose. `kind` is `stocks`, `themes` or `market`. Each subject has a stable URL; dated editions remain available under `history/`.
- `provenance/` is agent-facing material excluded from the reading-site export. Because the repository is now public, this material is also publicly readable through GitHub; exclusion from Pages is a presentation boundary, not access control. Record the originating research version, source cutoff, review status and any limitations there. The initial BE independent reassessment has **no formal saved cloud research version**; do not imply otherwise. Its original calculations and cloud receipts are retained here for continuity.
- `assets/` contains selected PNGs and allowlisted public OHLC projections. Only referenced, validated assets are copied; raw vendor envelopes, private fields and evidence IDs are excluded.
- Public HTML contains no research IDs, receipts, JSON payloads, credentials, internal paths, or developer appendices. Ordinary human-readable source links remain available in a collapsed section.

## Agent publication procedure

1. Read the applicable research state and relevant changes. Reuse unchanged evidence where reasonable; challenge inherited assumptions and correct previous errors, including when no new external evidence exists. Do not treat the previous recommendation as the default answer.
2. Save the substantive research through the established Karst research/review/publication workflow. If an independent note is intentionally being shared before formal intake, label that status explicitly and retain its agent record; it must not silently supersede the formal version.
3. Write a new public summary edition. Stock keys remain fixed; schema 2 displays `judgment`, `plan`, `fundamentals`, `valuation`, `technicals`. Explain changes briefly in `change`; give the current action in `action`. Date the market price, valuation horizon and plan review date. Preserve the distinction between DCF value, conditional market multiples and technical support.
4. Use the initial reports as schema examples. Text is plain text, not raw HTML or Markdown. Each paragraph is `{text, lead?}`; optional comparison rows are `{label, value, note}`. Unknown fields fail validation. A chart uses `{file, alt, caption}` and a public HTTPS source uses `{label, url}`. Related pages must exist.
5. Add a new edition rather than editing or deleting a published one. Corrections explain what was wrong, its effect on the advice and the replacement conclusion. New chart versions get new filenames. Existing source editions remain unchanged. Five pre-v2 published HTML archives are explicitly retained under `archives/`; later archives list only versions known at their publication.
6. Build and inspect the output, then commit the new public summary, selected chart and agent provenance. The Pages workflow publishes **only** the generated directory. A successful local build is not proof of a successful deployment; check Actions and the public URL.

```bash
python -m unittest karst.tests.test_reader -v
python -m karst.reader --content cards/reader --output /tmp/karst-reader-preview
```

The output directory must be new or empty. The builder refuses to package an existing directory or copy the repo wholesale. It uses only the Python standard library and does not call a model, fetch new data or recalculate advice. There is no website server, login system, tracking script, scheduler or live quote feed. Lightweight Charts 5.2.1 is vendored locally under Apache 2.0 with attribution; no chart library CDN is required.

Optional chart generation uses `python -m karst.reader.chart --source <registered-snapshot.json> --config <chart-config.json> --output <public.png>` and requires matplotlib in the research environment. Explicitly select the correct registered daily snapshot and check the market-close timestamp before rendering. The renderer checks cutoff, close, OHLC consistency and sufficient moving-average history; it does not independently certify session completeness. Calculate averages before trimming the visible window. The initial chart configuration is retained with BE's agent provenance.

## Deployment status and recovery

In the repository's **Settings → Pages → Build and deployment → Source**, select **GitHub Actions**. Then run **Publish research reader** from the Actions tab, or rerun the pending deployment after enabling Pages.

The user enabled Pages and reran the workflow on 2026-09-18. Attempt 2 completed successfully for both build and deploy, including all eight tests. The public site is https://kkhcheng88.github.io/Karst/ . Browser acceptance confirmed the home page, the five-section BE report and loaded chart, the AI power topic, and dated report history. The user also made the repository public; GitHub reports `private=false` and `has_pages=true`. This is not a security audit or a claim that repository contents were checked for secrets.

The workflow builds and uploads first, then checks Pages configuration and deploys with `pages: write` and `id-token: write`. The GitHub connector used for this delivery cannot administer Pages. `configure-pages` does not auto-enable it using `GITHUB_TOKEN`; no extra credentials are requested or stored in the repo.

Official setup: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

## Remaining integration (Claude Code / service)

- Formal research publication does not yet automatically write a reader edition or push GitHub. For now the agent explicitly performs step 3–6. Successful content commits then trigger automatic site rebuild/deployment with Pages enabled.
- Add a narrow publication adapter later: consume the selected stored research version and its authored human summary, record provenance, then append a reader edition. Do not expose the service database, credentials or raw evidence to the browser; do not ask the renderer to invent investment conclusions.
- Do not backfill the initial independent BE note with a fabricated research version ID. Use the retained calculations and evidence links when completing normal contract intake and review.
- Market pages are supported by the same renderer but omitted until there is an actual market analysis. The AI power page is a scoped extension of BE research, not a completed sector universe or a valuation for unresearched peers.
- Scheduled scans, notifications, relation propagation and cloud chart source-selection fixes remain separate work; this delivery does not claim they are implemented.

## First stored cloud research (2026-09-19)

BE edition `2026-09-19-r2` is now tied to a stored cloud primary research version and its immutable calculation/input records. The initial saved version received a citation-only correction before publication; both remain in the cloud. Provenance under the matching edition records the version, publication, source cutoff and pending Claude review job. Independent review has **not** run. The human summary explicitly says so. Earlier standalone notes and engineering samples remain in history; they are not retrospectively relabelled as reviewed cloud research.

The reading summary is still deliberately authored by the agent, then committed through the existing Pages workflow. This delivery does not add an unattended DB-to-GitHub publisher, an event router, or a scheduler.

## Incremental check notes (2026-09-19)

The optional `checks/<kind>/<slug>/*.json` records a human-authored check against an existing `report_edition` without creating another research edition. Fields: schema_version=1, public=true, kind, slug, report_edition, checked_at (timezone required), summary. The latest matching check appears above the current report; archives keep their original content, and a new research edition does not inherit a stale check. Checks and agent provenance JSON are not exported to the site. State the actual source scope and outstanding gaps; never label a price-only refresh as a complete fundamental reassessment.

BE’s first check refreshes prices successfully and keeps the cloud primary research unchanged. Its provenance records the existing coverage diagnostics and pending independent review. Core incremental routing is deployed, while scheduling and automated DB-to-Pages publication remain separate.

## Reader v2 / G1–G2 (2026-09-20)

Homepage is a searchable/filterable/sortable list, 15 entries per page. Engineering samples remain in history but do not occupy the investment listing. `overview` holds chain, substantive change, next event, action_state and coverage. No-change check runs do not bump research dates. Schema 2 supports generic tables, expandable calculation detail, directed company relations and optional chart JSON with a required static PNG fallback.

Public chart JSON carries only date/OHLC/volume/completion and selected overlays. `karst.reader.interactive.project` uses the same normalized bars and MA/resample functions as the MCP chart engine. It never fetches, guesses fundamentals, or projects today's fair value into historical candles. D/W/M, zoom/crosshair and MA/level controls were exercised in a local browser. SMC visualization controls remain a later, optional improvement; existing MCP SMC calculations are unchanged.

BE r3 is an editorial correction of the stored primary research, not a newly recalibrated valuation. Its EPS/P/E matrix exposes the existing assumptions; peer multiple calibration and full research update remain open. AI power and Neocloud pages are sourced preliminary comparisons, not full individual-company research ratings. Their input universe, relationship and comparison manifests are versioned under strategy/data and seeded explicitly by the deployment configuration.

Repository provenance is Agent-native; only the selected reading data and vendor library are exported. Source financial excerpts have also been ingested into cloud evidence with their limitations. No unattended DB-to-Pages writer has been added.

Deployment confirmed: PR #9 and CI dependency correction 7fc027e are live on Pages; Actions run 35496672341 build and deploy succeeded. Live BE chart loaded and period status was checked. The data service still reports 0.2.4; knowledge bootstrap/API deployment is pending authenticated Zeabur access. Existing cloud source subscriptions and BE watch/check were saved successfully. See the deployment acceptance receipt for exact scope.
