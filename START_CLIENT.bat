@echo off
setlocal
cd /d "%~dp0"
title SecureTeam Messenger - Client
if not exist ".venv\Scripts\python.exe" (
    echo Local environment missing. Run SETUP.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -c "import PyQt5.QtWidgets" >nul 2>&1
if errorlevel 1 (
    echo Dependencies missing. Run SETUP.bat to repair the local environment.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" run_client.py %*
if errorlevel 1 (
    echo Client exited with an error. Check the message above.
    pause
    exit /b 1
)
