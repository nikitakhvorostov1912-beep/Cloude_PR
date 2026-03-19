---
name: lint-check
description: "Проверка стиля кода, линтинг, форматирование для Python и TypeScript."
command: /lint-check
---

# Lint Check — Проверка стиля кода

Проверь и исправь стиль кода в проекте Survey Automation.

## Backend (Python)

### Проверки
```bash
cd projects/survey-automation/backend
# Синтаксис
python -m py_compile main.py
python -m py_compile app/config.py
# ... для каждого .py файла

# Импорты — проверь что все используются
# Типы — проверь type hints
```

### Правила
- Type hints обязательны для всех функций и методов
- Docstrings для публичных классов и методов (но только если логика неочевидна)
- Нет неиспользуемых импортов
- Нет `# type: ignore` без обоснования
- Строки не длиннее 120 символов
- Пустая строка в конце файла

## Frontend (TypeScript)

### Проверки
```bash
cd projects/survey-automation/frontend
npm run lint
npm run build  # TypeScript проверка
```

### Правила
- Нет `any` типов (используй конкретные типы или `unknown`)
- Нет `@ts-ignore` без обоснования
- Нет неиспользуемых переменных (prefix `_` для намеренно неиспользуемых)
- "use client" директива где нужно
- Все компоненты типизированы

## Формат отчёта

```
## Lint Report

### Backend
Файлов проверено: N
Ошибок: M
- файл:строка — описание

### Frontend
ESLint: N ошибок, M предупреждений
TypeScript: N ошибок
- файл:строка — описание

### Исправлено автоматически: K
```

После отчёта — ИСПРАВЬ все найденные проблемы.
