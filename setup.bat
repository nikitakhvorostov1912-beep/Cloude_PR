@echo off
chcp 65001 >nul
echo === Claude Code Workspace Setup ===
echo.

:: 1. Memory
set MEMORY_DIR=%USERPROFILE%\.claude\projects\D--Cloude-PR\memory
echo [1/4] Восстановление памяти Claude Code...
if not exist "%MEMORY_DIR%" mkdir "%MEMORY_DIR%"
copy /Y ".claude\memory-backup\*.md" "%MEMORY_DIR%\" >nul
echo       OK: 10 файлов памяти скопированы в %MEMORY_DIR%

:: 2. Python venvs
echo.
echo [2/4] Python окружения...
if exist "voice-agent-1c\requirements.txt" (
    if not exist "voice-agent-1c\venv" (
        echo       Создаю venv для voice-agent-1c...
        python -m venv voice-agent-1c\venv
        voice-agent-1c\venv\Scripts\pip install -r voice-agent-1c\requirements.txt -q
        echo       OK: voice-agent-1c
    ) else (
        echo       SKIP: voice-agent-1c\venv уже существует
    )
)
if exist "ai-ecosystem-1c\requirements.txt" (
    if not exist "ai-ecosystem-1c\venv" (
        echo       Создаю venv для ai-ecosystem-1c...
        python -m venv ai-ecosystem-1c\venv
        ai-ecosystem-1c\venv\Scripts\pip install -r ai-ecosystem-1c\requirements.txt -q
        echo       OK: ai-ecosystem-1c
    ) else (
        echo       SKIP: ai-ecosystem-1c\venv уже существует
    )
)

:: 3. Node modules
echo.
echo [3/4] Node.js зависимости...
if exist "voice-agent-1c\dashboard\package.json" (
    if not exist "voice-agent-1c\dashboard\node_modules" (
        echo       npm install voice-agent-1c\dashboard...
        cd voice-agent-1c\dashboard && npm install --silent 2>nul && cd ..\..
        echo       OK
    ) else (
        echo       SKIP: voice-agent-1c\dashboard\node_modules уже существует
    )
)
if exist "ai-ecosystem-1c\dashboard\package.json" (
    if not exist "ai-ecosystem-1c\dashboard\node_modules" (
        echo       npm install ai-ecosystem-1c\dashboard...
        cd ai-ecosystem-1c\dashboard && npm install --silent 2>nul && cd ..\..
        echo       OK
    ) else (
        echo       SKIP: ai-ecosystem-1c\dashboard\node_modules уже существует
    )
)

:: 4. .env files
echo.
echo [4/4] Проверка .env файлов...
if exist "voice-agent-1c\.env.example" (
    if not exist "voice-agent-1c\.env" (
        copy "voice-agent-1c\.env.example" "voice-agent-1c\.env" >nul
        echo       СОЗДАН: voice-agent-1c\.env (заполни ключи!)
    ) else (
        echo       OK: voice-agent-1c\.env
    )
)
if exist "ai-ecosystem-1c\.env.example" (
    if not exist "ai-ecosystem-1c\.env" (
        copy "ai-ecosystem-1c\.env.example" "ai-ecosystem-1c\.env" >nul
        echo       СОЗДАН: ai-ecosystem-1c\.env (заполни ключи!)
    ) else (
        echo       OK: ai-ecosystem-1c\.env
    )
)

echo.
echo === Готово! ===
echo.
echo Следующие шаги:
echo   1. Заполни .env файлы API-ключами
echo   2. Запусти: claude
echo   3. Проверь: /health-check
echo.
pause
