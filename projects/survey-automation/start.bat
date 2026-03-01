@echo off
chcp 65001 >nul
echo ╔══════════════════════════════════════════════╗
echo ║   Survey Automation — Запуск приложения      ║
echo ╚══════════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден. Установите Python 3.11+
    pause
    exit /b 1
)

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Node.js не найден. Установите Node.js 18+
    pause
    exit /b 1
)

:: Create data directory
if not exist "backend\data\projects" mkdir "backend\data\projects"

echo [1/2] Запуск Backend (FastAPI)...
cd backend
start "Survey-Backend" cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
cd ..

echo [2/2] Запуск Frontend (Next.js)...
cd frontend
start "Survey-Frontend" cmd /c "npm run dev"
cd ..

echo.
echo ✅ Серверы запускаются...
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:3000
echo    API docs: http://localhost:8000/docs
echo.
echo Ожидание запуска...
timeout /t 5 /nobreak >nul

:: Open browser
start http://localhost:3000

echo.
echo Нажмите любую клавишу для остановки серверов...
pause >nul

:: Kill servers
taskkill /FI "WINDOWTITLE eq Survey-Backend" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Survey-Frontend" /F >nul 2>&1
echo Серверы остановлены.
