@echo off
REM Karst Phase-3 narrow-band kill-axis news watcher (thesis/news_watch.py).
REM News is CONTEXT not a signal (user-set design, 2026-07-13) -- listens ONLY to the kill_condition
REM keyword axes in thesis/news_watch_keywords.yaml (distilled from thesis/themes.yaml), NOT a
REM generic feed. Writes thesis/.raw/news_watch.json for the premarket briefing to read (separate
REM wiring task, not done by this script).
REM
REM Suggested registration (NOT executed by this file -- run by hand once approved), 20:00 HKT,
REM i.e. BEFORE the premarket briefing so same-evening kill-axis news is already captured:
REM   schtasks /Create /TN "Karst-news-watch-daily" /TR "C:\projects\Investment\Karst\thesis\daily_news_watch.cmd" /SC DAILY /ST 20:00 /F
REM   (query:  schtasks /Query /TN "Karst-news-watch-daily" /FO LIST
REM    delete: schtasks /Delete /TN "Karst-news-watch-daily" /F)
REM Caveat: the machine must be ON at run time. Log: thesis\.raw\news_watch_cron.log
cd /d "%~dp0.."
set PYTHONUTF8=1
echo ==== %date% %time% ==== >> thesis\.raw\news_watch_cron.log
python thesis\news_watch.py >> thesis\.raw\news_watch_cron.log 2>&1
exit /b 0
