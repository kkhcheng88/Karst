@echo off
REM Karst insider cache weekly rebuild -- SEC EDGAR Form 4 (discovered via defeatbeta's cached index).
REM Slow (per-ticker Form 4 XML parse) + slow-moving data -> WEEKLY, not daily. Rebuilds
REM thesis/insider_cache.json in place (gitignored); the daily scan reads it (yfinance = fallback).
REM
REM Registered as a Windows scheduled task (Sunday 08:00 local):
REM   schtasks /Create /TN "Karst-insider-weekly" /TR "C:\projects\Investment\Karst\thesis\weekly_insider.cmd" ^
REM           /SC WEEKLY /D SUN /ST 08:00 /F
REM   (query: schtasks /Query /TN "Karst-insider-weekly" /FO LIST ; delete: schtasks /Delete /TN ... /F)
cd /d "%~dp0.."
python thesis\insider_edgar.py build
exit /b 0
