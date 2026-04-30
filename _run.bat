@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%~dp0_cdp_final.py" (
  echo ERROR: _cdp_final.py was not found in %~dp0
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0_cdp_final.py"
