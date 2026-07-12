@echo off
REM Karst magnifier per-node staleness check (docs/2026-07-08_phase3_ws3_lifecycle.md Sec1a-node,
REM magnifier model plan step E prep). Checks every theme's nodes: block for new transcripts
REM (corpus.db) or new gooptions articles touching a node's tickers since its last_scored date.
REM MUST run after Karst-corpus-weekly (08:30 SUN, ~1-2h) so the transcript check sees fresh
REM data -- scheduled right after Karst-constraint-scan-weekly.
REM Output: thesis/.raw/magnifier_review_queue.md (append-only, tracked in git, human triage).
REM
REM Registered as a Windows scheduled task (Sunday 10:45 local):
REM   schtasks /Create /TN "Karst-magnifier-staleness-weekly" /TR "C:\projects\Investment\Karst\thesis\weekly_magnifier_staleness.cmd" ^
REM           /SC WEEKLY /D SUN /ST 10:45 /F
REM   (query: schtasks /Query /TN "Karst-magnifier-staleness-weekly" /FO LIST ; delete: schtasks /Delete /TN "Karst-magnifier-staleness-weekly" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
python thesis\magnifier_staleness.py >> thesis\.raw\magnifier_staleness_cron.log 2>&1
exit /b 0
