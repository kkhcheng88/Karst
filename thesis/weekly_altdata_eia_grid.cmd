@echo off
REM Karst altdata top-5 probe item 2: EIA-930 hourly grid demand (PJM), AI-power-grid theme.
REM Data-collection + display only (see thesis/altdata_eia_grid.py module docstring) -- does NOT
REM assert a verdict/threshold, just tracks trailing-7d YoY demand over time.
REM Requires ~/.config/eia/api_key (free, self-registered by user 2026-07-12).
REM
REM Registered as a Windows scheduled task (Sunday 08:55 local, after the TWSE altdata job):
REM   schtasks /Create /TN "Karst-altdata-eia-grid-weekly" /TR "C:\projects\Investment\Karst\thesis\weekly_altdata_eia_grid.cmd" ^
REM           /SC WEEKLY /D SUN /ST 08:55 /F
REM   (query: schtasks /Query /TN "Karst-altdata-eia-grid-weekly" /FO LIST ; delete: schtasks /Delete /TN "Karst-altdata-eia-grid-weekly" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
python thesis\altdata_eia_grid.py >> thesis\.raw\altdata_eia_grid_cron.log 2>&1
exit /b 0
