@echo off
cd /d "%~dp0"
title Interview-to-BPMN

echo.
echo  === Interview-to-BPMN ===
echo  Starting web interface...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.10+
    pause
    exit /b 1
)

echo [OK] Launching on http://localhost:8501
echo [INFO] Close this window to stop the server
echo.

python start.pyw

pause
