@echo off
setlocal
cd /d "%~dp0"
title SecureTeam Messenger - Server
if not exist ".venv\Scripts\python.exe" (
    echo Local environment missing. Run SETUP.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -c "import argon2" >nul 2>&1
if errorlevel 1 (
    echo Dependencies missing. Run SETUP.bat to repair the local environment.
    pause
    exit /b 1
)
echo SecureTeam Messenger server. First run: START_SERVER.bat --init-admin
echo Default listener: 127.0.0.1:5555. See README for TLS.
".venv\Scripts\python.exe" run_server.py %*
if errorlevel 1 (
    echo Server exited with an error. Check the message above.
    pause
    exit /b 1
)
