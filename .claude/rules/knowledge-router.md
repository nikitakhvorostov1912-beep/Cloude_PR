# Knowledge Base Router

Перед ответом на вопрос проверь: попадает ли тема в одну из категорий ниже.
Если да — прочитай соответствующий файл из памяти и используй его данные в ответе.

## Маршруты

| Тема / Ключевые слова | Файл для чтения |
|------------------------|-----------------|
| 1С события, проведение, подписки, ПередЗаписью, ПриЗаписи, обработчики объектов | `memory/1c-event-sequences.md` |
| 1С обмен, CommerceML, каталог, синхронизация, интернет-магазин, товары из 1С | `memory/1c-exchange-protocols.md` |
| Промпты, роли, "Act as", ролевые паттерны, prompt engineering | `memory/prompt-patterns.md` |
| Системные промпты, Cursor, Windsurf, v0, Lovable, как устроен AI-инструмент | `memory/system-prompts-reference.md` |
| Инструменты аналитика 1С, tools_ui_1c, GitHub для 1С, обследование, ТЗ шаблоны | `memory/1c-analyst-tools-github.md` |
| 1С антипаттерны, критические ошибки BSL, confidence score, God Module, Copy-Paste | `rules/1c/1c-anti-patterns.md` |
| 1С архитектурные паттерны, Result-Structure, Early Return, ВТ_ prefix, CFE правила | `rules/1c/1c-architecture-standards.md` |
| 1С платформа cookbook: ЗначениеЗаполнено, ДлительныеОперации, блокировки, транзакции | `rules/1c/1c-platform-cookbook.md` |
| 1С стандарты кода: PREFIX, метрики качества, именование, документирование, типографика | `rules/1c/1c-core-standards.md` |
| Модуль управляемой формы: области, НаСервереБезКонтекста, асинхронные диалоги | `rules/1c/1c-form-module-standards.md` |
| Когда AI помогает / ломает в 1С, правило 3 итераций Матакова, ROI кейсы, юридические границы LLM+1С | `rules/1c/1c-ai-collaboration.md` |

## Правила

- Файлы лежат в `.claude/rules/1c/` (файлы правил) или `~/.claude/projects/C--CLOUDE-PR/memory/` (память)
- Читай файл только когда тема действительно релевантна
- Не загружай все файлы сразу — только нужный
- Если тема не попадает ни в одну категорию — не читай ничего
