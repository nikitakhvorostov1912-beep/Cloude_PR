---
name: full-check
description: "Полная проверка проекта: запускает ВСЕ 9 проверок последовательно"
---

# /full-check — Полная проверка проекта

## Когда использовать
Перед релизом, перед мержем в main, при передаче проекта.

## Инструкции

Запусти ВСЕ проверки последовательно. Каждую проверку выполни полностью, не пропуская.

### Порядок проверок:

1. **`/health-check`** — Быстрая диагностика: сервера, сборка, API
2. **`/lint-check`** — Стиль кода: Ruff (Python), ESLint (TypeScript)
3. **`/type-check`** — Типизация: mypy strict + tsc strict
4. **`/security-audit`** — Безопасность: OWASP, секреты, auth
5. **`/deps-audit`** — Зависимости: CVE, устаревшие пакеты
6. **`/test-coverage`** — Тесты: покрытие, качество, запуск
7. **`/perf-check`** — Производительность: N+1, blocking I/O, bundle
8. **`/api-contract`** — API контракты: backend ↔ frontend синхрон
9. **`/dead-code`** — Мёртвый код: неиспользуемые экспорты, orphans
10. **`/a11y-check`** — Доступность: WCAG, ARIA, клавиатура
11. **`/code-review`** — Code review: архитектура, паттерны, качество
12. **`/quality-gate`** — Quality gate: финальная приёмка

### После всех проверок

Составь сводный отчёт:

```
## 📋 ПОЛНАЯ ПРОВЕРКА ПРОЕКТА

**Дата**: {дата}
**Проект**: Survey Automation

| # | Проверка | Результат | Критических | Предупреждений |
|---|----------|-----------|-------------|----------------|
| 1 | Health Check | PASS/FAIL | N | N |
| 2 | Lint Check | PASS/FAIL | N | N |
| 3 | Type Check | PASS/FAIL | N | N |
| 4 | Security Audit | PASS/FAIL | N | N |
| 5 | Deps Audit | PASS/FAIL | N | N |
| 6 | Test Coverage | PASS/FAIL | N | N |
| 7 | Perf Check | PASS/FAIL | N | N |
| 8 | API Contract | PASS/FAIL | N | N |
| 9 | Dead Code | PASS/FAIL | N | N |
| 10 | A11y Check | PASS/FAIL | N | N |
| 11 | Code Review | PASS/FAIL | N | N |
| 12 | Quality Gate | PASS/FAIL | N | N |

### Итого
- PASS: {N}/12
- Критических проблем: {N}
- Предупреждений: {N}

## 🏆 ОБЩИЙ ВЕРДИКТ: PASS / FAIL

### ТОП-5 приоритетных исправлений
1. ...
2. ...
```
