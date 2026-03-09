---
name: health-check
description: "Быстрая проверка: сервер, фронт, API, данные — за 2 минуты."
---

# Health Check — Быстрая диагностика

Быстрая проверка работоспособности проекта Survey Automation. Выполни за 2 минуты.

## Окружение

- **Python**: `C:\Windows\py.exe` (НЕ `python` — его нет в PATH)
- **Node.js**: `C:\CLOUDE_PR\nodejs\node.exe`
- **Frontend build**: `C:\CLOUDE_PR\nodejs\node.exe ./node_modules/next/dist/bin/next build`
- **Backend dir**: `C:\CLOUDE_PR\projects\survey-automation\backend`
- **Frontend dir**: `C:\CLOUDE_PR\projects\survey-automation\frontend`

## Шаги

### 1. Backend
```bash
cd C:/CLOUDE_PR/projects/survey-automation/backend
C:/Windows/py.exe -c "from app.config import get_config; print('Config OK:', get_config().app.title)"
C:/Windows/py.exe -c "from main import create_app; print('App OK')"
```

### 2. Frontend Build
```bash
cd C:/CLOUDE_PR/projects/survey-automation/frontend
C:/CLOUDE_PR/nodejs/node.exe ./node_modules/next/dist/bin/next build 2>&1 | tail -15
```

### 3. API (если сервер запущен)
Сначала проверь, запущен ли бэкенд:
```bash
curl -s http://localhost:8000/api/health
```
Если нет — запусти через `preview_start` с именем `survey-backend`.

Затем:
```bash
curl -s http://localhost:8000/api/health
curl -sL http://localhost:8000/api/projects/ | head -c 200
```
**ВАЖНО**: endpoint `/api/projects` делает 307 редирект на `/api/projects/` — всегда используй trailing slash или флаг `-L` с curl.

### 4. Файловая структура
Проверь наличие ключевых файлов через Glob:
- `projects/survey-automation/backend/main.py`
- `projects/survey-automation/backend/app/config.py`
- `projects/survey-automation/backend/app/services/pipeline_service.py`
- `projects/survey-automation/backend/app/api/routes/`
- `projects/survey-automation/frontend/src/app/layout.tsx`
- `projects/survey-automation/frontend/src/lib/api.ts`
- `projects/survey-automation/start.bat`

### 5. Тесты
```bash
cd C:/CLOUDE_PR/projects/survey-automation/backend && C:/Windows/py.exe -m pytest tests/ -v --tb=short 2>&1 | tail -25
```

## Формат отчёта

```
Health Check: {дата}
━━━━━━━━━━━━━━━━━━━
Backend Config:  ✅/❌
Backend App:     ✅/❌
Frontend Build:  ✅/❌
API Health:      ✅/❌ (или ⏭ если сервер не запущен)
API Projects:    ✅/❌ (количество проектов)
File Structure:  ✅/❌
Tests:           ✅/❌ ({n} passed, {m} failed)
━━━━━━━━━━━━━━━━━━━
Статус: HEALTHY / DEGRADED / BROKEN
```

Если статус не HEALTHY — перечисли проблемы и предложи исправления.
