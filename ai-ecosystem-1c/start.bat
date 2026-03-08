@echo off
chcp 65001 >nul
echo ═══════════════════════════════════════════════════
echo   AI Ecosystem 1C — Phase 1 (Суфлёр)
echo ═══════════════════════════════════════════════════

:: Backend
echo.
echo [1/2] Запуск Backend (FastAPI)...
cd /d "%~dp0"
start "AI-Ecosystem Backend" cmd /k "python -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000 --reload"

:: Frontend
echo [2/2] Запуск Frontend (Next.js)...
start "AI-Ecosystem Frontend" cmd /k "cd dashboard && npm run dev"

echo.
echo ═══════════════════════════════════════════════════
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo   Health:   http://localhost:8000/health
echo ═══════════════════════════════════════════════════
echo.
echo Для остановки закройте окна терминалов или запустите stop.bat
