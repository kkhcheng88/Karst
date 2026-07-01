@echo off
REM Karst Phase-3 forward-IC daily accumulation (run by Windows Task Scheduler on trading days).
REM Logs today's point-in-time thesis cross-section, refreshes the report, commits the log.
REM US market holidays are safe: the as-of date dedups to 0 new predictions -> nothing to commit.
REM
REM Registered as a Windows scheduled task (weekdays 09:00 local, captures the prior US close):
REM   schtasks /Create /TN "Karst-forward-IC-daily" /TR "C:\projects\Investment\Karst\thesis\daily_ic.cmd" ^
REM           /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 09:00 /F
REM   (query: schtasks /Query /TN "Karst-forward-IC-daily" /FO LIST ; delete: schtasks /Delete /TN ... /F)
REM Caveat: the machine must be ON at run time; enable "run task ASAP after a missed start" in Task
REM Scheduler if the box is often off. Timing is flexible -- it just logs the latest available US close.
cd /d "%~dp0.."
python thesis\forward_ic.py log
python thesis\forward_ic.py report
git add thesis/track_record.jsonl
git commit -m "chore: daily forward-IC log" >nul 2>&1
exit /b 0
