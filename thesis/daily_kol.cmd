@echo off
REM Karst-kol-daily: pull 順哥 (Discord) + zsxq KOL posts. ASCII comments only (cp950 trap).
REM Both pullers exit 0 on missing creds/CLI - this chain must never crash.
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d C:\projects\Investment\Karst
python thesis\kol_pull.py >> thesis\.raw\kol_pull.log 2>&1
python thesis\zsxq_pull.py >> thesis\.raw\kol_pull.log 2>&1
