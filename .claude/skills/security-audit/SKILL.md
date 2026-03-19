---
name: security-audit
description: "Аудит безопасности: OWASP Top 10, секреты, auth, input validation"
---

# /security-audit — Аудит безопасности

## Когда использовать
Перед мержем, после добавления API endpoints, auth логики, работы с пользовательскими данными.

## Инструкции

Выполни полный аудит безопасности проекта. Проверь каждый пункт и выдай отчёт.

### 1. Секреты и credentials
- Grep по всему проекту: `password`, `secret`, `token`, `api_key`, `API_KEY`, `Bearer`, `sk-`, `ssh-rsa`
- Проверь `.env`, `config.yaml`, `.gitignore` — секреты НЕ должны быть в коде
- Проверь, что `.env` в `.gitignore`

### 2. OWASP Top 10
- **Injection (A03)**: SQL/NoSQL injection, command injection. Все запросы параметризованы?
- **XSS (A07)**: Пользовательский ввод экранируется? React dangerouslySetInnerHTML?
- **Broken Auth (A07)**: Есть ли проверка прав на каждом endpoint?
- **SSRF**: URL от пользователя валидируется?
- **Path Traversal**: `../` в путях файлов обрабатывается?

### 3. Backend (FastAPI)
- CORS: проверь `allow_origins` — не должно быть `["*"]` в проде
- Все Pydantic модели имеют валидацию (min_length, max_length, regex)?
- File upload: проверка типа, размера, расширения
- Rate limiting на критичных endpoints
- HTTPException с безопасными сообщениями (без stack trace)

### 4. Frontend (Next.js/React)
- Нет `eval()`, `innerHTML`, `dangerouslySetInnerHTML`
- Все формы имеют валидацию на клиенте И сервере
- API ключи не в клиентском коде (только `NEXT_PUBLIC_` переменные — и только безопасные)
- Нет hardcoded URLs к внутренним сервисам

### 5. Зависимости
- Запусти `pip audit` или проверь requirements.txt на CVE
- Проверь `npm audit` или package.json на уязвимости

## Формат отчёта

```
## 🔒 Аудит безопасности

**Дата**: {дата}
**Scope**: {какие файлы/модули проверены}

### Критические проблемы (🔴)
{список или "Не обнаружены"}

### Предупреждения (🟡)
{список или "Не обнаружены"}

### Рекомендации (🟢)
{список улучшений}

### Вердикт: PASS / FAIL
```
