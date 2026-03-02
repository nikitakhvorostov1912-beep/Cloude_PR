@echo off
chcp 65001 >nul
echo ========================================
echo   Survey Automation - Zapusk
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend"
set "VENV_PYTHON=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "NODE_DIR=C:\tools\nodejs\node-v22.14.0-win-x64"
set "PATH=%NODE_DIR%;%PATH%"

if not exist "%VENV_PYTHON%" goto no_venv
goto check_node

:no_venv
echo [ERROR] Python venv not found: %VENV_PYTHON%
pause
exit /b 1

:check_node
if not exist "%NODE_DIR%\node.exe" goto no_node
goto check_modules

:no_node
echo [ERROR] Node.js not found: %NODE_DIR%
pause
exit /b 1

:check_modules
if exist "%FRONTEND_DIR%\node_modules" goto start_servers
echo Installing frontend dependencies...
pushd "%FRONTEND_DIR%"
call npm install
popd

:start_servers
if not exist "%BACKEND_DIR%\data\projects" mkdir "%BACKEND_DIR%\data\projects"

echo [1/2] Starting Backend...
start "Survey-Backend" cmd /k "cd /d %BACKEND_DIR% && %VENV_PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Starting Frontend...
start "Survey-Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Waiting 8 sec...
timeout /t 8 /nobreak >nul

start http://localhost:3000

echo.
echo Press any key to stop servers...
pause >nul

taskkill /FI "WINDOWTITLE eq Survey-Backend" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Survey-Frontend" /F >nul 2>&1
echo Servers stopped.
