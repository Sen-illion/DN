@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" play_game.py
echo.
echo Script finished. Press any key to exit...
pause >nul
