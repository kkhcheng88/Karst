@echo off
REM Core v2 daily playbook readout (run by Windows Task Scheduler on weekday mornings HK time,
REM after the prior US close). Appends the gate decision + M1/M3 status + current LEAP quotes
REM to playbook_log.txt (repo root, for the user's observation log). Read-only: no orders.
REM
REM Registered:
REM   schtasks /Create /TN "Karst-playbook-daily" /TR "C:\projects\Investment\Karst\backtest\daily_playbook.cmd" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 09:15 /F
REM   (query: schtasks /Query /TN "Karst-playbook-daily" /FO LIST ; delete: schtasks /Delete /TN "Karst-playbook-daily" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
python backtest\playbook_readout.py >> playbook_log.txt 2>&1
exit /b 0
