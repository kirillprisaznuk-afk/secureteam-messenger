@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -c "import sys; assert (3, 11) <= sys.version_info[:2] < (3, 14)" >nul 2>&1
    if errorlevel 1 (
        echo Install Python 3.11, 3.12 or 3.13 with the Windows py launcher.
        echo Or create .venv manually with a supported Python. See README.
        pause
        exit /b 1
    )
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Could not create .venv. Check your Python installation.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency setup failed. Check network access and your Python installation.
    pause
    exit /b 1
)
echo Setup complete. Run START_SERVER.bat --init-admin once, then START_SERVER.bat.
pause
