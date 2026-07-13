@echo off
REM Karst Phase-3 WEEKLY constraint-language production scan (WS4 backlog #1,
REM docs/2026-07-08_phase3_ws4_early_detection.md Sec3). Scans themes.yaml's tracked tickers
REM against thesis/corpus.db for constraint-phrase density shifts, per theme per quarter.
REM MUST run after Karst-corpus-weekly (08:30 SUN, ~1-2h) has refreshed the corpus -- scheduled
REM with a 2h safety buffer.
REM Output: backtest/results/<date>_constraint_scan_production.md (heatmap snapshot) +
REM thesis/.raw/constraint_scan_queue.md (append-only alert checklist, gitignored).
REM
REM Registered as a Windows scheduled task (Sunday 10:30 local):
REM   schtasks /Create /TN "Karst-constraint-scan-weekly" /TR "C:\projects\Investment\Karst\thesis\weekly_constraint_scan.cmd" ^
REM           /SC WEEKLY /D SUN /ST 10:30 /F
REM   (query: schtasks /Query /TN "Karst-constraint-scan-weekly" /FO LIST ; delete: schtasks /Delete /TN "Karst-constraint-scan-weekly" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
python thesis\constraint_scan.py >> thesis\.raw\constraint_scan_cron.log 2>&1
exit /b 0
