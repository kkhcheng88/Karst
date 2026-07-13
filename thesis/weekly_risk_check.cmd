@echo off
REM Karst Phase-3 WEEKLY risk-check (WS3 backlog #3-4, docs/2026-07-08_phase3_ws3_lifecycle.md Sec4):
REM 1) concentration.py -- meta_factor concentration report (confidence-weighted proxy; spec cap =
REM    no single meta_factor > 50% of satellite capital; real $ enforcement pending WS5 sizing.py).
REM 2) beta_check.py -- per-theme basket vs sector-proxy-ETF rolling corr/excess-return check;
REM    flags a theme as BETA-ONLY if corr>0.90 AND excess~0 have BOTH persisted ~6 months.
REM Both scripts are cheap/fast reads (no heavy scrape) -- weekly cadence chosen (2026-07-12, user
REM call) over the spec's monthly default because Phase-3 admits new themes fast enough (6 new in
REM the 2026-07-11 discovery-radar batch alone) that a month-old concentration read can go stale
REM mid-cycle; weekly costs nothing extra to run.
REM Log: weekly_risk_log.txt (root, gitignored) -- read at the next session's STATUS.md check.
REM
REM Registered as a Windows scheduled task (Sunday 08:15 local -- between insider-weekly 08:00 and
REM the (unregistered) corpus-weekly 08:30 slot):
REM   schtasks /Create /TN "Karst-risk-check-weekly" /TR "C:\projects\Investment\Karst\thesis\weekly_risk_check.cmd" ^
REM           /SC WEEKLY /D SUN /ST 08:15 /F
REM   (query: schtasks /Query /TN "Karst-risk-check-weekly" /FO LIST ; delete: schtasks /Delete /TN "Karst-risk-check-weekly" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
echo ==== %date% %time% ==== >> weekly_risk_log.txt
python thesis\concentration.py >> weekly_risk_log.txt 2>&1
python thesis\beta_check.py >> weekly_risk_log.txt 2>&1
REM 3) crowding_composite.py (2026-07-13, Fable P2-17) -- feature-5 crowding percentile per theme
REM    (analyst attendance + bull-ratio; GS flow not available). Weekly is the right cadence:
REM    attendance moves quarterly, bull-ratio with the gooptions feed. Writes
REM    thesis\.raw\crowding_composite.json for the daily dashboard render to read.
python thesis\crowding_composite.py >> weekly_risk_log.txt 2>&1
exit /b 0
