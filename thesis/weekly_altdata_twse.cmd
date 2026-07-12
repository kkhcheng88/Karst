@echo off
REM Karst altdata top-5 probe item 5 / ROADMAP Batch-3 item 8: TWSE (Taiwan) monthly revenue,
REM free public OpenAPI, no key. Disclosure is monthly; this runs weekly and dedups against
REM already-recorded (code, period) pairs, so most weeks are a no-op until a new month posts.
REM
REM Registered as a Windows scheduled task (Sunday 08:50 local, right after insider-tilt):
REM   schtasks /Create /TN "Karst-altdata-twse-weekly" /TR "C:\projects\Investment\Karst\thesis\weekly_altdata_twse.cmd" ^
REM           /SC WEEKLY /D SUN /ST 08:50 /F
REM   (query: schtasks /Query /TN "Karst-altdata-twse-weekly" /FO LIST ; delete: schtasks /Delete /TN "Karst-altdata-twse-weekly" /F)
cd /d "%~dp0.."
set PYTHONUTF8=1
python thesis\altdata_twse.py >> thesis\.raw\altdata_twse_cron.log 2>&1
exit /b 0
