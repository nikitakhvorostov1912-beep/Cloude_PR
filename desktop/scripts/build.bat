@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

echo ╔══════════════════════════════════════════╗
echo ║   Survey Automation — Desktop Builder   ║
echo ╚══════════════════════════════════════════╝
echo.

set ROOT=%~dp0..\..
set DESKTOP=%~dp0..
set BACKEND=%ROOT%\projects\survey-automation\backend
set FRONTEND=%ROOT%\projects\survey-automation\frontend

:: ─── Шаг 1: Проверить зависимости ──────────────────────────────────────────

echo [1/6] Проверка инструментов...

where node >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Node.js не найден. Установите с https://nodejs.org
    pause & exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден. Установите Python 3.11+
    pause & exit /b 1
)

echo    Node.js: OK
echo    Python:  OK

:: ─── Шаг 2: Скачать Python embeddable ──────────────────────────────────────

echo.
echo [2/6] Проверка Python embeddable...

set PYTHON_VERSION=3.11.9
set PYTHON_ZIP=python-%PYTHON_VERSION%-embed-amd64.zip
set PYTHON_DIR=%DESKTOP%\resources\python

if exist "%PYTHON_DIR%\python.exe" (
    echo    Python embeddable: уже скачан
    goto :python_done
)

echo    Скачиваем Python %PYTHON_VERSION% embeddable...
mkdir "%PYTHON_DIR%" 2>nul

:: Скачать через PowerShell
set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_ZIP%
set PYTHON_ZIP_PATH=%TEMP%\%PYTHON_ZIP%

powershell -Command "Write-Host 'Загрузка Python embeddable...'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP_PATH%' -UseBasicParsing"

if errorlevel 1 (
    echo ОШИБКА: Не удалось скачать Python embeddable
    echo Скачайте вручную: %PYTHON_URL%
    echo И распакуйте в: %PYTHON_DIR%
    pause & exit /b 1
)

:: Распаковать
echo    Распаковка Python embeddable...
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP_PATH%' -DestinationPath '%PYTHON_DIR%' -Force"

if errorlevel 1 (
    echo ОШИБКА: Не удалось распаковать Python embeddable
    pause & exit /b 1
)

del "%PYTHON_ZIP_PATH%" 2>nul

echo    Python embeddable: готов

:python_done

:: ─── Шаг 3: Собрать Next.js frontend ───────────────────────────────────────

echo.
echo [3/6] Сборка Next.js frontend...

cd /d "%FRONTEND%"

if not exist "node_modules" (
    echo    npm install...
    call npm install --silent
)

echo    npm run build...
call npm run build
if errorlevel 1 (
    echo ОШИБКА: Сборка Next.js провалилась
    pause & exit /b 1
)

echo    Frontend: собран

:: ─── Шаг 4: Установить Electron зависимости ────────────────────────────────

echo.
echo [4/6] Установка Electron зависимостей...

cd /d "%DESKTOP%"

if not exist "node_modules" (
    call npm install
) else (
    echo    node_modules: уже установлены
)

:: ─── Шаг 5: Сгенерировать иконку если не существует ────────────────────────

echo.
echo [5/6] Проверка иконки...

if not exist "%DESKTOP%\build\icon.ico" (
    echo    Генерация иконки через Python...
    python "%DESKTOP%\scripts\generate-icon.py"
    if errorlevel 1 (
        echo    ПРЕДУПРЕЖДЕНИЕ: Иконка не создана, используется дефолтная
    )
)

:: ─── Шаг 6: Собрать Electron installer ─────────────────────────────────────

echo.
echo [6/6] Сборка Windows installer...

cd /d "%DESKTOP%"
call npx electron-builder --win

if errorlevel 1 (
    echo ОШИБКА: Сборка installer провалилась
    pause & exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════╗
echo ║   ✓ Сборка завершена успешно!               ║
echo ╚══════════════════════════════════════════════╝
echo.
echo Installer находится в:
echo   %DESKTOP%\dist\
dir "%DESKTOP%\dist\*.exe" 2>nul

echo.
pause
