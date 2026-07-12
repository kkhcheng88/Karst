@echo off
REM Karst Phase-3 WEEKLY transcript + corpus refresh (full-market discovery corpus).
REM 1) Reset the full-universe cursor to idx 0, then prefetch_transcripts.py --universe full
REM    walks ALL ~9.9k tickers every week (unknown-unknowns discovery -- a name with ZERO
REM    prior transcript coverage can newly report and must be caught, not just the watchlist).
REM    Per-ticker fetch is itself incremental (a date file already on disk is skipped without
REM    re-downloading), so re-walking the full universe weekly only pays for tickers with a
REM    genuinely NEW transcript since last week; the ~0.4s/ticker politeness delay still means
REM    a floor of ~66min wall-clock (realistically 1-2h) for the full walk -- fine for a WEEKLY
REM    Sunday-morning job, machine must be ON. Without the cursor reset, --universe full is a
REM    no-op once the initial marathon reaches idx==len(universe) (see prefetch_transcripts.py
REM    main(): "Full universe already fully walked ... Nothing to do.").
REM    Lands under thesis/.raw/transcripts/<TICKER>/<date>.json (gitignored local corpus).
REM 2) corpus.py build --incremental -- indexes ONLY the new docs into thesis/corpus.db.
REM    Two FTS5 tables by language (2026-07-10): docs_fts_en (transcripts, porter unicode61,
REM    word+stem) + docs_fts (gooptions, trigram, Chinese substring). Indexed doc_id skip ->
REM    scales to full market. See thesis/corpus.py module docstring.
REM Weekly cadence (NOT quarterly): earnings prints land spread across ~6 weeks + off-cycle
REM names report year-round, and constraint-language is a TREND to catch as it builds -> weekly
REM re-index + scan catches emerging signals fastest.
REM Nothing here is version-controlled (transcripts/ and *.db are gitignored) -> no git commit.
REM Log: thesis/.raw/transcripts/cron.log (inside the gitignored transcripts/ dir).
REM
REM NOT auto-registered -- register yourself when ready:
REM   schtasks /Create /TN "Karst-corpus-weekly" /TR "C:\projects\Investment\Karst\thesis\weekly_corpus.cmd" /SC WEEKLY /D SUN /ST 08:30 /F
REM   (query:  schtasks /Query /TN "Karst-corpus-weekly" /FO LIST
REM    delete: schtasks /Delete /TN "Karst-corpus-weekly" /F)
REM Caveat: machine must be ON at run time (same as the other Karst scheduled jobs). ASCII-only.
cd /d "%~dp0.."
set PYTHONUTF8=1
echo ==== %date% %time% ==== >> thesis\.raw\transcripts\cron.log
if exist thesis\.raw\transcripts\_full_universe_cursor.json del /f /q thesis\.raw\transcripts\_full_universe_cursor.json >> thesis\.raw\transcripts\cron.log 2>&1
python thesis\prefetch_transcripts.py --universe full >> thesis\.raw\transcripts\cron.log 2>&1
python thesis\corpus.py build --incremental >> thesis\.raw\transcripts\cron.log 2>&1
exit /b 0
