@echo off
REM Karst Phase-3 WEEKLY expectations-gap valuation refresh (Fable 交接 P1-6,
REM docs/2026-07-12_valuation_expectations_gap_spec.md Sec3a):
REM thesis/valuation.py --run --compare-v0 -- recomputes Mauboussin-style expectations-gap
REM (P_base@10/14/18x / g_implied / classification) for every active theme's top-2 expressive
REM tickers + the 4 WATCH names, writes thesis/.raw/valuation_report.json (machine-readable) +
REM backtest/results/<date>_expectations_gap_v1.md (human-readable, same theme-rollup table
REM format v0 used so dashboard_render.py/paper_ledger.py's row-level regex parser keeps working
REM unmodified) + a v0-vs-v1 per-ticker classification diff (also embedded in the .md).
REM
REM KNOWN GAP (see thesis/valuation.py module docstring): dashboard_render.py and paper_ledger.py
REM both auto-discover the latest report via a glob hardcoded to "*_expectations_gap_v0.md" --
REM this v1 file is NOT yet auto-picked-up by them (out of scope here; those two files are not
REM to be touched by this task). Until that glob is widened, they keep reading v0's frozen
REM 2026-07-12 snapshot.
REM
REM Cadence: the spec recommends QUARTERLY (valuation isn't an intraday signal -- re-run after
REM earnings season) but WEEKLY is chosen here to match the sibling thesis/weekly_risk_check.cmd
REM cost profile (cheap read-mostly compute, no harm running more often than the spec's quarterly
REM floor) -- 2026-07-13.
REM Log: weekly_valuation_log.txt (root, gitignored) -- read at the next session's STATUS.md check.
REM
REM NOT registered as a Windows scheduled task (per this task's explicit instruction). To register
REM (suggested slot: Sunday 09:15, after insider-weekly 08:00 / risk-check-weekly 08:15):
REM   schtasks /Create /TN "Karst-valuation-weekly" /TR "C:\projects\Investment\Karst\thesis\weekly_valuation.cmd" ^
REM           /SC WEEKLY /D SUN /ST 09:15 /F
REM   (query: schtasks /Query /TN "Karst-valuation-weekly" /FO LIST ; delete: schtasks /Delete /TN "Karst-valuation-weekly" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
echo ==== %date% %time% ==== >> weekly_valuation_log.txt
python thesis\valuation.py --run --compare-v0 >> weekly_valuation_log.txt 2>&1
exit /b 0
