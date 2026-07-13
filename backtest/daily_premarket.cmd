@echo off
REM Premarket overlay run (~1h before US open, ~20:30 HK weekdays). Fetches LIVE premarket
REM prices and overlays them on the post-close closed-form triggers (dip/accumulate,
REM sell-covered-call, 200SMA gate) computed by the ~5am HK post-close run. Read-only, no orders.
REM Appends to premarket_log.txt (repo root, gitignored) for the observation log.
REM
REM This is the PREMARKET twin of daily_playbook.cmd (which is the ~5am post-close run using
REM CLOSE prices). Register (~20:30 HK = ~08:30 ET, ~1h pre-open):
REM   schtasks /Create /TN "Karst-premarket-daily" /TR "C:\projects\Investment\Karst\backtest\daily_premarket.cmd" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 20:30 /F
REM   (query: schtasks /Query /TN "Karst-premarket-daily" /FO LIST ; delete: schtasks /Delete /TN "Karst-premarket-daily" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
python backtest\premarket_check.py >> premarket_log.txt 2>&1
REM Dashboard evening refresh (2026-07-13): re-renders DASHBOARD.md with the premarket overlay
REM just written above, commits+pushes to the GitHub mirror, pushes Telegram. Chained here
REM (not a separate schtask) so it's guaranteed to run AFTER premarket_check.py's fresh write.
REM Sentinel + ladder refreshed too (cheap; ledger is a morning-only mark, skipped here).
python thesis\data_sentinel.py >> thesis\.raw\dashboard_render.log 2>&1
python thesis\opportunity_ladder.py >> thesis\.raw\dashboard_render.log 2>&1
python thesis\dashboard_render.py --mode evening >> thesis\.raw\dashboard_render.log 2>&1
exit /b 0
