@echo off
REM Karst crypto governance monitor (Phase-3 architecture Sec5 defect #1 fix). Read-only
REM alert -- checks the user's own pre-committed ETH/SOL recovery ladder (docs/2026-07-08_
REM transition_plan.md Sec7), never places/cancels any order. See thesis/crypto_governance.py
REM module docstring for exact scope, including what was deliberately left out (downside/time
REM exit -- user declined this, 2026-07-08, do not re-add without reading that history first).
REM
REM Registered as a Windows scheduled task (05:43 HKT daily, right after Karst-aa-paper-daily):
REM   schtasks /Create /TN "Karst-crypto-governance-daily" /TR "C:\projects\Investment\Karst\backtest\daily_crypto_governance.cmd" /SC DAILY /ST 05:43 /F
REM   (query: schtasks /Query /TN "Karst-crypto-governance-daily" /FO LIST ; delete: schtasks /Delete /TN "Karst-crypto-governance-daily" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
python thesis\crypto_governance.py >> playbook_log.txt 2>&1
exit /b 0
