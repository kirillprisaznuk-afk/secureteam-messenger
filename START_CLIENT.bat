@echo off
title Corporate Messenger - Client
echo ============================================
echo   CORPORATE MESSENGER CLIENT
echo ============================================
echo Connecting to server...
echo Login: admin/admin123
echo ============================================
echo.
timeout /t 2 /nobreak >nul
python run_client.py
pause
