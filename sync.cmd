@echo off
setlocal
cd /d "%~dp0"
python tools\sync_repo.py
set "rc=%errorlevel%"
if not "%rc%"=="0" pause
exit /b %rc%
