@echo off
REM Karst paper-league daily mark (thesis/paper_league.py) -- marks every registered parallel
REM paper strategy (aa-strict / spy-bh / sizing-v1 / sizing-v2) to the same NAV=100 starting
REM line and appends a one-line-per-strategy scoreboard, so the AA-strict-vs-core-v2-vs-sizing
REM "paper race" (user's explicit call, 2026-07-13: no migration until the data picks a winner)
REM has a single daily readout instead of three disconnected logs.
REM
REM NOT yet registered as a Windows scheduled task (unlike the sibling daily_*.cmd files in this
REM repo) -- run manually for now (`python thesis\paper_league.py --update`) until the league has
REM enough days of history to be worth reading, and thesis/.raw/aa_strict_paper_log.jsonl is
REM confirmed running on its own daily schedule (backtest/daily_aa_paper.cmd, 05:42 HKT) so
REM aa-strict/spy-bh don't lag. SUGGESTED registration once ready, right after that job:
REM   schtasks /Create /TN "Karst-paper-league-daily" /TR "C:\projects\Investment\Karst\thesis\daily_league.cmd" /SC DAILY /ST 05:43 /F
REM   (query: schtasks /Query /TN "Karst-paper-league-daily" /FO LIST ; delete: schtasks /Delete /TN "Karst-paper-league-daily" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
python thesis\paper_league.py --update >> playbook_log.txt 2>&1
exit /b 0
