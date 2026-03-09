@echo off
chcp 65001 >nul
echo ========================================
echo   Survey Automation - Запуск
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend"
set "VENV_PYTHON=python"
set "NODE_DIR=C:\CLOUDE_PR\nodejs"
set "PATH=%NODE_DIR%;%PATH%"

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

echo Остановка старых серверов на портах 8000 и 3000...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo [1/2] Starting Backend...
start /min "Survey-Backend" cmd /c "cd /d %BACKEND_DIR% && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo [2/2] Starting Frontend...
start /min "Survey-Frontend" cmd /c "cd /d %FRONTEND_DIR% && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Ожидание запуска серверов (8 сек)...
timeout /t 8 /nobreak >nul

start http://localhost:3000

echo.
echo Нажмите любую клавишу чтобы остановить серверы...
pause >nul

taskkill /FI "WINDOWTITLE eq Survey-Backend" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Survey-Frontend" /F >nul 2>&1
echo Серверы остановлены.
