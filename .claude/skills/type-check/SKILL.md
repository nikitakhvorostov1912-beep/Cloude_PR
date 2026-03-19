---
name: type-check
description: "Проверка типизации: mypy strict (Python) + tsc strict (TypeScript)"
---

# /type-check — Проверка типизации

## Когда использовать
После изменений в Python или TypeScript коде. Строгая типизация предотвращает runtime ошибки.

## Инструкции

### Python (Backend)
1. Найди все `.py` файлы в `projects/survey-automation/backend/`
2. Проверь каждую функцию и метод:
   - Все параметры имеют type hints?
   - Return type указан?
   - Нет `Any` без явной необходимости?
   - Pydantic модели: все поля типизированы?
3. Проверь паттерны:
   - `Optional[X]` вместо `X | None` — ок, но должно быть консистентно
   - `dict` без `Dict[str, X]` — плохо
   - `list` без `List[X]` или `list[X]` — плохо
   - `tuple` без типов элементов — плохо
4. Запусти `python -m mypy --strict` если mypy установлен, иначе выполни ручной анализ

### TypeScript (Frontend)
1. Найди все `.ts` и `.tsx` файлы в `projects/survey-automation/frontend/src/`
2. Проверь:
   - Нет `any` типов (grep `": any"`, `as any`, `<any>`)
   - Все props компонентов типизированы через interface/type
   - API response типы определены и используются
   - Нет `@ts-ignore` или `@ts-expect-error` без комментария почему
3. Запусти `npx tsc --noEmit --strict` если возможно

## Формат отчёта

```
## 📐 Проверка типизации

### Python ({X} файлов проверено)
- Функций без type hints: {N}
- Использований `Any`: {N}
- Нетипизированных dict/list: {N}

### TypeScript ({X} файлов проверено)
- Использований `any`: {N}
- `@ts-ignore`: {N}
- Компонентов без типизации props: {N}

### Детали
{файл:строка — описание проблемы}

### Вердикт: PASS / FAIL
```
