@echo off
chcp 65001 >nul 2>&1
title Voice Agent 1C — Остановка

echo.
echo  Останавливаю серверы...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3001 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8090 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo  Готово. Все серверы остановлены.
echo.
pause
