@echo off
REM Karst-AA-strict PAPER tracker (no real capital) -- runs daily alongside core v2's own
REM playbook_readout.py so both structures' signals land in the same log window, for the
REM parallel-run comparison period the user asked for (2026-07-13) before any real-capital
REM migration decision. See thesis/aa_strict_paper_tracker.py module docstring for the model.
REM
REM Registered as a Windows scheduled task (05:42 HKT daily, right after Karst-playbook-daily):
REM   schtasks /Create /TN "Karst-aa-paper-daily" /TR "C:\projects\Investment\Karst\backtest\daily_aa_paper.cmd" /SC DAILY /ST 05:42 /F
REM   (query: schtasks /Query /TN "Karst-aa-paper-daily" /FO LIST ; delete: schtasks /Delete /TN "Karst-aa-paper-daily" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
python thesis\aa_strict_paper_tracker.py >> playbook_log.txt 2>&1
exit /b 0
