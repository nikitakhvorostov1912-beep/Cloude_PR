---
name: health-check
description: "Быстрая проверка: сервер, фронт, API, данные — за 2 минуты."
command: /health-check
---

# Health Check — Быстрая диагностика

Быстрая проверка работоспособности проекта Survey Automation. Выполни за 2 минуты.

## Шаги

### 1. Backend
```bash
cd projects/survey-automation/backend
python -c "from app.config import get_config; print('Config OK:', get_config().app.title)"
python -c "from main import create_app; print('App OK')"
```

### 2. Frontend
```bash
cd projects/survey-automation/frontend
npm run build 2>&1 | tail -5
```

### 3. API (если сервер запущен)
```bash
curl -s http://localhost:8000/api/health | python -m json.tool
curl -s http://localhost:8000/api/projects | python -m json.tool
```

### 4. Файловая структура
Проверь наличие ключевых файлов:
- `projects/survey-automation/backend/main.py`
- `projects/survey-automation/backend/app/config.py`
- `projects/survey-automation/backend/app/services/pipeline_service.py`
- `projects/survey-automation/backend/app/api/routes/`
- `projects/survey-automation/frontend/src/app/layout.tsx`
- `projects/survey-automation/frontend/src/lib/api.ts`
- `projects/survey-automation/start.bat`

### 5. Тесты
```bash
cd projects/survey-automation/backend && pytest tests/ -v --tb=short 2>&1 | tail -20
```

## Формат отчёта

```
Health Check: {дата}
━━━━━━━━━━━━━━━━━━━
Backend Config:  ✅/❌
Backend App:     ✅/❌
Frontend Build:  ✅/❌
API Health:      ✅/❌ (или ⏭ если сервер не запущен)
File Structure:  ✅/❌
Tests:           ✅/❌ ({n} passed, {m} failed)
━━━━━━━━━━━━━━━━━━━
Статус: HEALTHY / DEGRADED / BROKEN
```

Если статус не HEALTHY — перечисли проблемы и предложи исправления.
