# Roadmap — улучшения экосистемы

> Дорожная карта улучшений с приоритетами. P0 = срочно, P3 = на потом.

## 🟢 P0 — Сейчас (ничего делать НЕ нужно)

Экосистема стабильна. Все основные инструменты на актуальных версиях:
- mcp-bsl-context v0.3.2 ✅
- METR v0.5.2 ✅ (config fixed)
- BSL LS v0.29.0 ✅ (через claude-code-bsl-lsp plugin авто)
- YAxUnit 25.12 ✅
- 1c-transit (MCP Toolkit v1.7.0) ✅
- claude-code-bsl-lsp plugin ✅

**Phase 1 обновления применены:**
- +4 новых правил comol
- +12 obra-скиллов
- +3 обновлённых cc-1c-skills (skd-edit, skd-info, form-validate)
- Чистка мусора (hooks/gsd-*, plugins/connect-apps-plugin)
- METR config fix

## 🔴 P1 — На неделе (если будет время)

### 1. Установить feenlace/mcp-1c v1.6.5 — RO MCP для боевой базы

**Зачем:** Безопасный read-only доступ к `ut_rt_copy` через 9 tools. Параллельно с 1c-transit (не конфликтует).

**Сложность:** Низкая (10 минут).

**Команды:** см. `04-COMMANDS.md` секция "P1".

**Польза:**
- Безопаснее execute_code (write-операции заблокированы платформой)
- get_event_log — нативный доступ к ЖР
- get_form_structure — XCF парсер с любой глубиной вложенности
- Авто-обновление бинарника без переустановки расширения

**Риск:** Низкий — read-only, расширение проверенное (⭐98).

### 2. Закоммитить изменения Phase 1

```powershell
cd C:/CLOUDE_PR
git status  # проверить что добавлено
git add .claude/rules/1c/1c-forms.md .claude/rules/1c/1c-forms-add.md .claude/rules/1c/1c-forms-events-add.md .claude/rules/1c/1c-form-reserved-names.md
git add .claude/skills/obra-*
git add .claude/skills/skd-edit .claude/skills/skd-info .claude/skills/form-validate
git add .claude/BACKLOG.md .mcp.json
git add .claude/research/ecosystem-deep-revision-2026-05-17/
git commit -m "chore(ecosystem): deep revision Phase 1"
```

См. `02-APPLIED.md` секцию "Git коммит — рекомендация" для полного сообщения коммита.

**Зачем:** 559 modified files в git status — пора зафиксировать чистое состояние.

## 🟡 P2 — На месяце

### 3. Доустановить EDT 2026.1 → апгрейд EDT-MCP до v1.31.1

**Зачем:** +22 tools в EDT-MCP (find_references, validate_query, get_form_screenshot и др.).

**Сложность:** Высокая (~1-2 часа + риск миграции workspace).

**Pre-req:** Закрыть проблему `memory/edt_2026_1_incomplete_install_2026_05_14.md` (1.6 MB огрызок установки).

**Команды:** см. `04-COMMANDS.md` секция "P2 — EDT-MCP".

**Польза:**
- find_references из EDT в коде
- validate_query прямо в IDE
- Снимок layout формы
- 9 семантических групп инструментов

**Риски:**
- Миграция workspace InfoBase5 — может быть несовместимость
- EDT 2025.2.5 нельзя удалять до подтверждения работы 2026.1
- 1cedt.exe -data CLI не работает для 2026.1 — только Cloud Start UI

**Стратегия миграции:**
1. Установить EDT 2026.1 параллельно с 2025.2.5
2. Создать новый workspace для 2026.1
3. Import InfoBase5 как новый проект
4. Если работает — мигрировать постепенно
5. Старый EDT 2025.2.5 — fallback

### 4. Изучить Arman-Kudaibergenov OpenSpec — встроить в 1c-feature-dev

**Зачем:** OpenSpec workflow (proposal/apply/archive) может улучшить нашу Phase 0 (Spec) в `1c-feature-dev`.

**Сложность:** Средняя (~2-3 часа на чтение + дизайн).

**Шаги:**
1. Клонировать `Arman-Kudaibergenov/1c-ai-development-kit` в `_refresh/arman-kit/`
2. Прочитать `openspec-*` скиллы
3. Сравнить с нашим `1c-feature-dev` Phase 0
4. Взять лучшие практики, встроить в наш skill
5. Документировать изменения в `memory/`

**НЕ делать:** не сливать целиком — слишком разные парадигмы со cc-1c-skills.

### 5. Обновить memory MEMORY.md

После применения изменений:
- Удалить устаревшую запись `mcp-1c v1.6.4 (требует переустановки расширения)` ✅ (уже сделано в Phase 1)
- Добавить ссылки на новые инструменты
- Обновить `feedback_1c_transit_mcp_embedded_6010.md` — упомянуть feenlace/mcp-1c как альтернативу для RO-доступа

## 🔵 P3 — На потом

### 6. Дождаться BSL LS v0.30.0 stable

**Текущее:** v0.29.0 stable (через `claude-code-bsl-lsp` плагин).
**Целевое:** v0.30.0 stable когда выйдет.

**Действие:** Ничего делать не нужно — плагин обновится автоматически каждые 8 минут после выхода stable.

**Что будет лучше:**
- Multi-workspace LSP support
- Семантическая подсветка лямбд в string literals
- Исправлены crashes на препроцессорных директивах

### 7. Рассмотреть консолидацию дубликатов агентов

**Сейчас:** 78 агентов, из них есть дубли ролей:
- code-reviewer: 3 версии (`code-reviewer.md`, `gsd-code-reviewer.md`, `ecc/code-reviewer.md`)
- planner: 2 версии (`gsd-planner.md`, `ecc/planner.md`)
- debugger: 2 версии (`bug-hunter.md`, `gsd-debugger.md`)
- doc-writer: 3 версии (`gsd-doc-writer.md`, `ecc/doc-updater.md`, `documentation-engineer.md`)
- security: 3 версии (`gsd-security-auditor.md`, `ecc/security-reviewer.md`, `security-researcher.md`)

**Действие:**
1. Решить какой канон для каждой роли (например: для 1С — наш `code-reviewer`, для общих задач — `gsd-code-reviewer`)
2. Дубли — в `agents-archive/`
3. Документировать решение в `INDEX.md`

**Польза:** меньше confusion при вызове, меньше шум в Skill tool listing.

### 8. Проверить реальное использование GSD-стека

**Сейчас:** 31 `gsd-*` агент + 21 команда `/gsd:*` (~52 объекта).

**Вопрос:** реально ли вызываются в Транзит-workflow?

**Действие:**
1. Проверить транскрипты последних 30 дней (см. `mcp__ccd_session_mgmt__search_session_transcripts`)
2. Если использование < 5 вызовов — архивировать
3. Если активно используется — оставить

**Польза если архивировать:** -52 объекта из системного промпта → быстрее загрузка контекста, меньше confusion.

### 9. Решение про content/agents/ comol vs наши 1c-*

**Сейчас:**
- В правилах `rules/1c/1c-subagent-pipeline.md` ссылки на 13 субагентов от comol (`1c-explorer`, `1c-developer`, `1c-architect` и др.) — но они НЕ скопированы локально
- Наши `1c-code-*` (6 агентов) — параллельная имплементация

**Действие:**
1. Решить какой набор канон:
   - **Вариант A:** скопировать `content/agents/` от comol, удалить наши → unified pipeline
   - **Вариант B:** оставить наши `1c-code-*`, обновить правила (убрать ссылки на comol-агентов)
2. Согласовать pipeline (`1c-subagent-pipeline.md`) с фактической имплементацией

**Польза:** консистентность — правила = реализация.

### 10. Рассмотреть anthropic-skills:* namespace vs локальные anthropics-*

**Сейчас:** В CC уже доступны 17 официальных скиллов через namespace `anthropic-skills:*` (через плагин):
- `anthropic-skills:docx`, `:xlsx`, `:pdf`, `:pptx`
- `:brand-guidelines`, `:theme-factory`, `:web-artifacts-builder`
- `:canvas-design`, `:mcp-builder`, `:skill-creator`, `:internal-comms`
- `:solution-presenter`, `:doc-coauthoring`, `:setup-cowork`, `:consolidate-memory`

**Параллельно локально:** 18 `anthropics-*` папок в `.claude/skills/`. Из них **9 не совпадают** с официальным anthropics/skills — community форк.

**Действие:**
1. Архивировать 9 локальных дублей которые есть в namespace:
   - `anthropics-pdf` (есть `anthropic-skills:pdf`)
   - `anthropics-canvas-design` (есть `anthropic-skills:canvas-design`)
   - `anthropics-mcp-builder` (есть `anthropic-skills:mcp-builder`)
   - `anthropics-frontend-design` (см. namespace?)
   - `anthropics-skill-development` (есть `anthropic-skills:skill-creator`)
   - `anthropics-feature-spec` (см. namespace?)
   - `anthropics-webapp-testing` (см. namespace?)
   - `anthropics-memory-management` (есть `anthropic-skills:consolidate-memory`)
2. Сохранить 9 уникальных community-форк:
   - `anthropics-agent-identifier`
   - `anthropics-claude-automation-recommender`
   - `anthropics-claude-md-improver`
   - `anthropics-command-development`
   - `anthropics-hook-development`
   - `anthropics-interactive-dashboard-builder`
   - `anthropics-knowledge-management`
   - `anthropics-knowledge-synthesis`
   - `anthropics-roadmap-management`
   - `anthropics-task-management`
3. Возможно переименовать в `community-*` чтобы не путать с official

**Польза:** избежать дублирования, понять что является официальным.

## Метрики прогресса

| Метрика | До ревизии | После Phase 1 | Цель P1+P2 | Идеал |
|---------|-----------|---------------|------------|-------|
| Активных MCP серверов | 7 рабочих (1 невалиден) | 7 рабочих | 8 (+feenlace) | 8 |
| Правил 1С | 27 | 31 | 31 | 31 |
| 1С-skills актуальных | 60/66 | 66/66 | 66/66 | 66/66 |
| Obra-skills | 2/14 | 14/14 | 14/14 | 14/14 |
| Дубликатов агентов | 5 ролей × 2-3 версии | те же | -3 ролей разрешены | 0 |
| Mусор в hooks/ | 12 файлов | 0 | 0 | 0 |
| Пустые plugins | 1 | 0 | 0 | 0 |
| Невалидные configs | METR yml | 0 | 0 | 0 |

## Зависимости между задачами

```
[1] feenlace/mcp-1c install ──→ Готово к использованию
                                  │
                                  └─→ [4] Изучить Arman OpenSpec

[2] Закоммитить Phase 1 ──→ Чистый git state
                              │
                              └─→ Все остальные изменения

[3] EDT 2026.1 install ──→ Workspace migration (риск)
                            │
                            └─→ [3a] EDT-MCP v1.31.1 plugin update
                                  │
                                  └─→ Доступны +22 tools

[5] Update MEMORY.md ──→ Знание систематизировано

[6] BSL LS v0.30.0 ──→ Авто (плагин обновится)

[7-10] Чистка дубликатов ──→ Независимо, в любом порядке
```

## Time budget

| Задача | Часы | Польза |
|--------|------|--------|
| P1.1 feenlace/mcp-1c | 0.5 ч | RO доступ к боевой базе |
| P1.2 git commit | 0.1 ч | Чистый репо |
| P2.3 EDT 2026.1 + EDT-MCP v1.31.1 | 2-3 ч | +22 tools |
| P2.4 Arman OpenSpec | 2-3 ч | Улучшение `1c-feature-dev` |
| P2.5 MEMORY update | 0.5 ч | Чистка устаревших записей |
| P3.7 Дубликаты агентов | 1-2 ч | Уборка |
| P3.8 GSD-стек ревью | 1 ч | Возможно -52 объекта |
| P3.9 content/agents/ vs 1c-* | 1-2 ч | Консистентность |
| P3.10 anthropics-* vs namespace | 1 ч | Уборка |

**Total P1:** ~30 минут
**Total P1+P2:** ~6-7 часов на месяц
**Total всё:** ~10-12 часов на квартал
