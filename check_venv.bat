@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -c "import requests; print('requests ok:', requests.__version__)"
