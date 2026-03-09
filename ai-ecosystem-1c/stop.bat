@echo off
chcp 65001 >nul
echo Останавливаю AI Ecosystem 1C...

:: Kill uvicorn
taskkill /F /FI "WINDOWTITLE eq AI-Ecosystem Backend*" >nul 2>&1
taskkill /F /IM uvicorn.exe >nul 2>&1

:: Kill node (Next.js)
taskkill /F /FI "WINDOWTITLE eq AI-Ecosystem Frontend*" >nul 2>&1

echo Готово.
