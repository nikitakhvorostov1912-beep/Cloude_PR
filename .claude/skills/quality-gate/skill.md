---
name: quality-gate
description: "Полная проверка проекта по чек-листу приёмки. Вердикт PASS/FAIL."
---

# Quality Gate — Полная проверка проекта

Ты — строгий QA-инженер. Проведи полную проверку проекта Survey Automation по чек-листу приёмки.

## Окружение

- **Python**: `C:\Windows\py.exe` (НЕ `python` — его нет в PATH)
- **Node.js**: `C:\CLOUDE_PR\nodejs\node.exe`
- **Frontend build**: `C:\CLOUDE_PR\nodejs\node.exe ./node_modules/next/dist/bin/next build`
- **Backend dir**: `C:\CLOUDE_PR\projects\survey-automation\backend`
- **Frontend dir**: `C:\CLOUDE_PR\projects\survey-automation\frontend`

## Порядок проверки

### 1. Запуск (критично)
- Проверь что `start.bat` существует и корректен
- Запусти backend через `preview_start` с именем `survey-backend`
- Запусти frontend через `preview_start` с именем `survey-frontend`
- Если порт занят — убей процесс: `taskkill //PID {pid} //F` и запусти снова
- Проверь http://localhost:8000/api/health отвечает 200
- Проверь http://localhost:3000 через `preview_screenshot`

### 2. Backend API
```bash
cd C:/CLOUDE_PR/projects/survey-automation/backend && C:/Windows/py.exe -m pytest tests/ -v --tb=short
```
- Проверь что ВСЕ тесты зелёные
- Проверь Swagger UI: `curl -sL -o /dev/null -w "%{http_code}" http://localhost:8000/docs`

### 3. Frontend Build
```bash
cd C:/CLOUDE_PR/projects/survey-automation/frontend
C:/CLOUDE_PR/nodejs/node.exe ./node_modules/next/dist/bin/next build 2>&1 | tail -20
```
- Не должно быть ошибок
- Все routes должны быть в выводе

### 4. UI Функциональность (через Preview)
Используй `preview_screenshot` и `preview_snapshot` для проверки:
- [ ] Главная страница загружается (есть заголовок "Проекты")
- [ ] Проекты отображаются (или empty state)
- [ ] Навигация по сайдбару работает
- [ ] Все кнопки видны и кликабельны
- [ ] Нет заглушек, TODO, placeholder-контента
- [ ] Loading/Error/Empty состояния присутствуют

Проверь несколько страниц через `preview_eval`:
```javascript
window.location.href = '/projects/{id}'
window.location.href = '/projects/{id}/upload'
window.location.href = '/projects/{id}/processes'
window.location.href = '/projects/{id}/gaps'
window.location.href = '/projects/{id}/requirements'
window.location.href = '/projects/{id}/files'
```

### 5. Экспорт
Проверь ВСЕ экспорт-эндпоинты. **URL формат**: `/api/projects/{project_id}/export/...`

```bash
# Найди проект с данными (progress > 0)
curl -sL "http://localhost:8000/api/projects/" | head -c 500

# Проверь экспорт (подставь реальный project_id)
curl -sL -o /dev/null -w "process_doc: %{http_code} %{size_download}b\n" "http://localhost:8000/api/projects/{id}/export/process-doc"
curl -sL -o /dev/null -w "req_excel: %{http_code} %{size_download}b\n" "http://localhost:8000/api/projects/{id}/export/requirements-excel"
curl -sL -o /dev/null -w "req_word: %{http_code} %{size_download}b\n" "http://localhost:8000/api/projects/{id}/export/requirements-word"
curl -sL -o /dev/null -w "gap_report: %{http_code} %{size_download}b\n" "http://localhost:8000/api/projects/{id}/export/gap-report"
curl -sL -o /dev/null -w "all_zip: %{http_code} %{size_download}b\n" "http://localhost:8000/api/projects/{id}/export/all"
curl -sL -o /dev/null -w "visio: %{http_code} %{size_download}b\n" "http://localhost:8000/api/projects/{id}/export/visio/{process_id}"
```

**ВАЖНО**: НЕ используй переменные bash (типа `$PROJECT_ID`) — они могут не подставиться в Git Bash. Подставляй ID напрямую в URL.

### 6. UX/Дизайн
- [ ] Тёмная тема по умолчанию (проверь через `preview_screenshot`)
- [ ] Все тексты на русском (проверь через `preview_snapshot`)
- [ ] Нет визуальных багов
- [ ] Мобильная адаптация (`preview_resize` с preset mobile)

### 7. Консоль
- `preview_console_logs` с level=error — нет ошибок
- `preview_logs` с level=error — нет backend exceptions

### 8. Пайплайн (опционально, если есть LLM API ключ)
Если переменная `ANTHROPIC_API_KEY` настроена:
- Создай проект через API
- Загрузи тестовый транскрипт
- Запусти стадии

Если ключа нет — пропусти и отметь как ⏭ SKIPPED.

## Формат отчёта

```
# Quality Gate Report

Дата: {дата}
Статус: PASS / FAIL

## Результаты по категориям:
| Категория          | Статус | Детали                           |
|--------------------|--------|----------------------------------|
| Запуск             | ✅/❌   | start.bat, серверы, health       |
| Backend API        | ✅/❌   | тесты, Swagger                   |
| Frontend Build     | ✅/❌   | build, routes                    |
| UI Функциональность| ✅/❌   | страницы, кнопки, состояния      |
| Экспорт            | ✅/❌   | Visio/Word/Excel/GAP/ZIP         |
| UX/Дизайн          | ✅/❌   | тема, язык, адаптация            |
| Консоль            | ✅/❌   | browser + backend errors         |
| Пайплайн           | ✅/⏭   | E2E тест (или SKIPPED без ключа) |

## Критические проблемы:
(список или "НЕТ")

## Рекомендации:
(список или "НЕТ")

## Вердикт: PASS / FAIL
```

Если хотя бы одна обязательная категория (1-7) FAIL — общий вердикт FAIL.
Категория 8 (Пайплайн) опциональна и не влияет на вердикт.
