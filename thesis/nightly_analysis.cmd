@echo off
REM Karst nightly analysis (Task Scheduler, daily 05:55 HKT, after the 05:30-05:45 fetch batch).
REM Python guard checks for NEW material (transcripts inbox / gooptions manifest delta);
REM only then invokes headless Claude (opus judge, sonnet subagents for bulk reading) with
REM acceptEdits + python-only bash. Zero-new nights spend zero model quota.
REM Prompt: thesis\nightly_analysis_prompt.md   Log: thesis\.raw\nightly_analysis.log
REM
REM Registered:
REM   schtasks /Create /TN "Karst-nightly-analysis" /TR "C:\projects\Investment\Karst\thesis\nightly_analysis.cmd" /SC DAILY /ST 05:55 /F
REM Caveats: machine ON + user logged in (claude CLI auth); ASCII-only comments in .cmd files.
cd /d "%~dp0.."
set PYTHONUTF8=1
python thesis\nightly_analysis.py
exit /b 0
