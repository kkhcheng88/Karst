@echo off
REM Karst dashboard morning render (Task Scheduler, daily ~06:00 HKT, after the 05:30-05:45
REM fetch/compute batch -- playbook/AA-paper/transcripts all need to have already written
REM their outputs). Pure aggregation, no new calc (see thesis\dashboard_render.py docstring).
REM Writes .dashboard_mirror\DASHBOARD.md, commits+pushes to origin/main (the curated
REM engine-only GitHub mirror), and pushes a Telegram summary. Read-only against the research
REM repo itself: no orders, no writes outside .dashboard_mirror\ and the Telegram API call.
REM
REM Registered:
REM   schtasks /Create /TN "Karst-dashboard-daily" /TR "C:\projects\Investment\Karst\thesis\daily_dashboard.cmd" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 06:00 /F
REM   (query: schtasks /Query /TN "Karst-dashboard-daily" /FO LIST ; delete: schtasks /Delete /TN "Karst-dashboard-daily" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
REM Refresh the render's upstream signal files first (2026-07-13 finale integration):
REM sentinel (freshness verdict), opportunity ladder (tier + radar), paper ledger (mark
REM positions + kill-VaR + roll countdown). Each is cheap; failures still leave the previous
REM json on disk, and the sentinel itself is what tells the reader when something is stale.
python thesis\data_sentinel.py >> thesis\.raw\dashboard_render.log 2>&1
python thesis\opportunity_ladder.py >> thesis\.raw\dashboard_render.log 2>&1
python thesis\paper_ledger.py --update >> thesis\.raw\dashboard_render.log 2>&1
python thesis\dashboard_render.py --mode morning >> thesis\.raw\dashboard_render.log 2>&1
exit /b 0
