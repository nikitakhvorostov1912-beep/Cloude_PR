@echo off
echo [DEV] Запуск Survey Automation Desktop в режиме разработки...
echo.
echo Убедитесь что запущены:
echo   - Backend:  cd backend ^&^& uvicorn main:app --port 8000
echo   - Frontend: cd frontend ^&^& npm run dev
echo.

cd /d "%~dp0.."
set ELECTRON_DEV=1
npx electron . --dev
