# Knowledge Base Router

Перед ответом на вопрос проверь: попадает ли тема в одну из категорий ниже.
Если да — прочитай соответствующий файл из памяти и используй его данные в ответе.

## Маршруты базы знаний

| Тема / Ключевые слова | Файл для чтения |
|------------------------|-----------------|
| 1С события, проведение, подписки, ПередЗаписью, ПриЗаписи, обработчики объектов | `memory/1c-event-sequences.md` |
| 1С обмен, CommerceML, каталог, синхронизация, интернет-магазин, товары из 1С | `memory/1c-exchange-protocols.md` |
| Промпты, роли, "Act as", ролевые паттерны, prompt engineering | `memory/prompt-patterns.md` |
| Системные промпты, Cursor, Windsurf, v0, Lovable, как устроен AI-инструмент | `memory/system-prompts-reference.md` |
| Инструменты аналитика 1С, tools_ui_1c, GitHub для 1С, обследование, ТЗ шаблоны | `memory/1c-analyst-tools-github.md` |

## Smart Router — автоподбор скиллов и агентов по теме

При получении запроса автоматически подключай релевантные скиллы:

| Тема запроса | Скиллы для вызова | Агенты |
|--------------|-------------------|--------|
| FastAPI, backend, endpoint, Pydantic, роутер | `/fastapi-patterns` | — |
| Next.js, React, фронтенд, компонент, shadcn, Tailwind | `/nextjs-patterns` | — |
| API контракт, типы, OpenAPI, fetch, фронт↔бэк | `/api-contract` | — |
| Новая фича, доработка, реализация | `/brainstorm` → `/feature-dev` | `planner` |
| Баг, ошибка, не работает, падает | `/debug`, `/smart-fix` | `bug-hunter` |
| Ревью, проверка кода, качество | `/code-review` | `code-reviewer` |
| Тесты, покрытие, TDD | `/e2e-test` | `tdd-guide`, `e2e-runner` |
| Безопасность, секреты, уязвимость | — | `security-reviewer` |
| Билд не собирается, ошибка компиляции | — | `build-error-resolver` |
| 1С код, модуль, процедура, функция | — | `1c-code-writer` |
| 1С обработка EPF, внешняя обработка | `/epf-init` → цепочка | `1c-code-architect` |
| 1С форма, управляемая форма | `/form-patterns`, `/form-compile` | — |
| 1С расширение CFE | `/cfe-init` → цепочка | — |
| 1С обследование, интервью, AS-IS | `/1c-survey-methodology`, `/process-extraction` | — |
| 1С GAP-анализ, TO-BE | `/gap-analysis`, `/to-be-optimization` | — |
| Исследование, сравнение, анализ | `/research` | `deep-researcher` |
| Документация, README | — | `doc-updater` |
| Рефакторинг, мёртвый код, дубли | — | `refactor-cleaner` |

## Правила

- Файлы памяти лежат в `~/.claude/projects/D--Cloude-PR/memory/`
- Читай файл только когда тема действительно релевантна
- Не загружай все файлы сразу — только нужный
- Если тема не попадает ни в одну категорию — не читай ничего
- Smart Router: подключай скиллы/агенты молча, без лишних объяснений
- При неоднозначности — подключай наиболее вероятный набор
