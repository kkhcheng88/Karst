@echo off
REM Karst Phase-3 gooptions.cc Trend-Core research sync (run by Windows Task Scheduler daily).
REM 1) Downloads any NEW research reports (manifest-driven, resumable -- skips already-saved ones,
REM    polite 1.2s rate limit) into thesis/.raw/gooptions/research/ (gitignored local corpus).
REM 2) Rebuilds the thin wiki source-node stubs in thesis/wiki/sources/ (idempotent overwrite BY
REM    DESIGN -- stubs stay thin; enrichment lives in cluster/ticker pages, never in stubs).
REM 3) Commits the wiki stubs. No new articles -> nothing to commit -> exits quietly.
REM
REM Registered as a Windows scheduled task (daily 09:10 local, after Karst-forward-IC-daily 09:00):
REM   schtasks /Create /TN "Karst-gooptions-daily" /TR "C:\projects\Investment\Karst\thesis\daily_gooptions.cmd" /SC DAILY /ST 09:10 /F
REM   (query:  schtasks /Query /TN "Karst-gooptions-daily" /FO LIST
REM    delete: schtasks /Delete /TN "Karst-gooptions-daily" /F)
REM Caveat: the machine must be ON at run time (same as Karst-forward-IC-daily). Log:
REM   thesis/.raw/gooptions/cron.log
cd /d "%~dp0.."
set PYTHONUTF8=1
echo ==== %date% %time% ==== >> thesis\.raw\gooptions\cron.log
python thesis\download_gooptions.py research >> thesis\.raw\gooptions\cron.log 2>&1
python thesis\build_source_nodes.py >> thesis\.raw\gooptions\cron.log 2>&1
git add thesis/wiki/sources
git commit -m "chore: daily gooptions research sync" >nul 2>&1
exit /b 0
