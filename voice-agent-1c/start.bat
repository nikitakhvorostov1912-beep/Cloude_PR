@echo off
chcp 65001 >nul 2>&1
title Voice Agent 1C

echo.
echo  ========================================
echo    Voice Agent 1C — Запуск серверов
echo  ========================================
echo.

cd /d "%~dp0"

:: --- Проверки зависимостей ---
if not exist "venv\Scripts\python.exe" (
    echo  [!] venv не найден. Создаю...
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt
)

if not exist "dashboard\node_modules" (
    echo  [!] node_modules не найден. Устанавливаю...
    cd dashboard && call npm install && cd ..
)

if not exist "demo.db" (
    echo  [i] Создаю демо-данные...
    set "PYTHONPATH=."
    venv\Scripts\python scripts\seed_demo.py
)

:: --- Убить старые процессы ---
echo  Очищаю порты...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":3001 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8090 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

:: --- Запуск серверов ---
echo  [1/3] Backend (порт 8000)...
start "VA-Backend" /min cmd /c "cd /d "%~dp0" && set PYTHONPATH=. && venv\Scripts\python -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000"

echo  [2/3] Dashboard (порт 3001)...
start "VA-Dashboard" /min cmd /c "cd /d "%~dp0dashboard" && npx next dev -p 3001"

echo  [3/3] Презентация (порт 8090)...
start "VA-Presentation" /min cmd /c "cd /d "%~dp0presentation" && python -m http.server 8090"

:: --- Ждём готовности через PowerShell ---
echo.
echo  Жду готовности серверов...
powershell -NoProfile -Command ^
  "$ok=0; for($i=0;$i -lt 40;$i++){" ^
  "  try{$r=[System.Net.WebRequest]::Create('http://localhost:8000/api/health');" ^
  "  $r.Timeout=2000; $r.GetResponse().Close(); $ok=1; break}catch{}" ^
  "  Start-Sleep 1; Write-Host '.' -NoNewline}" ^
  "; if($ok){Write-Host ' Backend OK'}else{Write-Host ' Backend timeout'}"

powershell -NoProfile -Command ^
  "$ok=0; for($i=0;$i -lt 60;$i++){" ^
  "  try{$r=[System.Net.WebRequest]::Create('http://localhost:3001');" ^
  "  $r.Timeout=2000; $r.GetResponse().Close(); $ok=1; break}catch{}" ^
  "  Start-Sleep 1; Write-Host '.' -NoNewline}" ^
  "; if($ok){Write-Host ' Dashboard OK'}else{Write-Host ' Dashboard timeout'}"

:: --- Открыть браузер ---
echo.
echo  =========================================
echo    Backend API:    http://localhost:8000
echo    Dashboard:      http://localhost:3001
echo    Презентация:    http://localhost:8090
echo  =========================================
echo.

rundll32 url.dll,FileProtocolHandler http://localhost:3001
timeout /t 1 /nobreak >nul
rundll32 url.dll,FileProtocolHandler http://localhost:8090

echo  Готово! Браузер открыт.
echo  Для остановки: stop.bat
echo.
pause
