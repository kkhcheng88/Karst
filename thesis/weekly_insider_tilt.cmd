@echo off
REM Karst insider small-cap 12-month tilt -- live weekly snapshot (ROADMAP A3 / P0-c,
REM docs/ROADMAP_AGENTIC.md line 30). Display-only, NOT wired to sizing.py.
REM Fetches recent SEC Form345 quarters (skips any not yet published, 404-safe), re-runs the
REM validated cluster-buy event detector, filters to <$2B market cap + trailing 12mo.
REM Output: backtest/results/<date>_insider_tilt_live.md (snapshot, overwritten each run).
REM
REM Registered as a Windows scheduled task (Sunday 08:45 local):
REM   schtasks /Create /TN "Karst-insider-tilt-weekly" /TR "C:\projects\Investment\Karst\thesis\weekly_insider_tilt.cmd" ^
REM           /SC WEEKLY /D SUN /ST 08:45 /F
REM   (query: schtasks /Query /TN "Karst-insider-tilt-weekly" /FO LIST ; delete: schtasks /Delete /TN "Karst-insider-tilt-weekly" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
python thesis\insider_tilt_live.py >> thesis\.raw\insider_tilt_cron.log 2>&1
exit /b 0
