# Commands — пошаговая установка новых инструментов

> Copy-paste ready команды установки. Каждый блок — независимый.

## 🔴 P1 — feenlace/mcp-1c v1.6.5 (read-only MCP)

### Что даёт
9 read-only tools для AI-доступа к живой базе `ut_rt_copy`:
- Безопасно (только SELECT)
- Один Go-бинарник, ноль зависимостей
- Параллельно с 1c-transit (не конфликтует)

### Pre-requisites
- ✅ Бинарь скачан: `C:/CLOUDE_PR/tools/mcp-1c-windows-amd64.v1.6.5.exe`
- ⚠️ Сервер 1С `is-srv1c-02:5541` должен быть доступен
- ⚠️ Учётка `Администратор / 123` должна иметь права на установку расширения в `ut_rt_copy`

### Шаг 1. Установить CFE-расширение в боевую базу

```powershell
# В PowerShell, не bash
cd C:/CLOUDE_PR/tools

# Серверный вариант (для ut_rt_copy)
.\mcp-1c-windows-amd64.v1.6.5.exe --install "Srvr=is-srv1c-02:5541;Ref=ut_rt_copy" --server --db-user Администратор --db-password 123

# Для локальной InfoBase5 (файловой)
# .\mcp-1c-windows-amd64.v1.6.5.exe --install "C:/Users/Khvorostov/Documents/InfoBase5"
```

**Что произойдёт:**
1. Установится CFE-расширение в базу (single-time, добавляет HTTP-сервис)
2. Расширение появится в списке расширений базы (можно посмотреть в Конфигураторе)
3. После v1.6.5 при обновлении бинарника — расширение НЕ требуется переустанавливать

### Шаг 2. Добавить в `.mcp.json`

Открыть `C:/CLOUDE_PR/.mcp.json` и добавить в `mcpServers`:

```json
"mcp-1c-readonly": {
  "type": "stdio",
  "command": "C:/CLOUDE_PR/tools/mcp-1c-windows-amd64.v1.6.5.exe",
  "args": [],
  "description": "feenlace/mcp-1c v1.6.5 — READ-ONLY MCP для боевой ut_rt_copy. 9 tools: get_metadata_tree, get_object_structure, get_form_structure (XCF любой глубины), search_code (BM25+BSL), bsl_syntax_help (180 функций), execute_query (SELECT only), validate_query, get_event_log. Безопаснее 1c-transit для боевой базы."
}
```

### Шаг 3. Проверка

```powershell
# Тест бинарника
C:/CLOUDE_PR/tools/mcp-1c-windows-amd64.v1.6.5.exe --version

# Должно вывести: v1.6.5 (или похожее)
```

После рестарта Claude Code сессии в available MCP tools должно появиться `mcp__mcp-1c-readonly__*`.

### Шаг 4. (Опционально) Удалить устаревший v1.6.4

```powershell
rm C:/CLOUDE_PR/tools/mcp-1c-windows-amd64.v1.6.4.exe
```

### Реверс
```powershell
# Удалить расширение из базы (через Конфигуратор → Конфигурация → Расширения)
# Удалить из .mcp.json секцию mcp-1c-readonly
rm C:/CLOUDE_PR/tools/mcp-1c-windows-amd64.v1.6.5.exe
```

## 🟡 P2 — EDT-MCP v1.31.1 (требует EDT 2026.1)

### Pre-requisites — РАЗБЛОКИРОВКА

⚠️ ВАЖНО: см. `memory/edt_2026_1_incomplete_install_2026_05_14.md` — текущая установка EDT 2026.1 = 1.6 MB огрызок, не работает.

### Шаг 1. Доустановить EDT 2026.1

Использовать **1C Cloud Start UI** (не CLI):

1. Открыть 1C Cloud Start UI
2. Установки → 1C:Enterprise Development Tools 2026.1
3. Кликнуть ▶ для установки
4. Дождаться полной установки (~500 MB)

**Не использовать `1cedt.exe -data`** — по MEMORY это не работает для 2026.1.

### Шаг 2. Мигрировать workspace

```
Открыть EDT 2026.1 → File → Switch Workspace → C:/Users/Khvorostov/eclipse-workspace-2026
Import existing project → InfoBase5 из C:/Users/Khvorostov/Documents/InfoBase5
Дождаться индексации
```

⚠️ Возможна несовместимость со старым workspace (бэкап старого обязательно).

### Шаг 3. Обновить EDT-MCP плагин

В EDT 2026.1:
```
Help → Install New Software → https://ditrix.io/edt-mcp-update-site/
Выбрать EDT-MCP v1.31.1 → Install
Restart EDT
```

### Шаг 4. Проверка

После рестарта в EDT:
- Открыть EDT-MCP перспективу
- Должен запуститься MCP-сервер на `localhost:8770`
- В available tools должно появиться: `mcp__edt-mcp__get_form_screenshot`, `mcp__edt-mcp__get_form_layout_snapshot`, `mcp__edt-mcp__find_references`, `mcp__edt-mcp__validate_query` (новые в 1.27+)

**Если что-то идёт не так:** откат к EDT 2025.2.5 + EDT-MCP 1.26.1 (текущая рабочая).

## 🟡 P2 — Arman-Kudaibergenov OpenSpec идеи

### Что взять

**OpenSpec workflow** — методология "спецификация → реализация → архив". Может быть встроена в наш существующий `1c-feature-dev` Phase 0.

### Шаг 1. Клонировать в _refresh/ для изучения

```powershell
cd C:/CLOUDE_PR/_refresh
git clone --depth 5 https://github.com/Arman-Kudaibergenov/1c-ai-development-kit.git arman-kit
```

### Шаг 2. Прочитать ключевые скиллы

```powershell
# Главные OpenSpec скиллы
cat _refresh/arman-kit/.claude/skills/openspec-proposal/SKILL.md
cat _refresh/arman-kit/.claude/skills/openspec-apply/SKILL.md
cat _refresh/arman-kit/.claude/skills/openspec-archive/SKILL.md

# Пример спецификации
ls _refresh/arman-kit/openspec/specs/
```

### Шаг 3. Интегрировать идеи

**НЕ копировать целиком.** Взять только концепции:
- Структура `openspec/specs/<имя>.md` с метаданными (Problem, Out of scope, Acceptance criteria, Risks)
- Workflow proposal → approved → done
- Apply phase clarification discipline

Встроить в наш `1c-feature-dev` Phase 0 (Spec) — там уже есть похожая структура.

### Шаг 4. Решение

Если OpenSpec лучше нашего `1c-feature-dev` Phase 0 — заменить только Phase 0, остальные фазы (1-8) оставить нашими.

## 🟢 P0 — Уже работает (ничего делать не нужно)

### claude-code-bsl-lsp плагин

✅ Активен (видно в session boot: "claude-code-bsl-lsp: LSP-сервер BSL Language Server v0.29.0 (130+ диагностик в реальном времени при чтении .bsl)").

Не требует действий. Авто-обновление каждые 8 минут.

### METR config

✅ Исправлен в Phase 1 — переключён на `application-metr-v2.yml`. После рестарта сессии METR работает (видно в deferred tools: `mcp__metr__build_project`, `run_all_tests` и др.).

## 🔵 Заметка — что НЕ устанавливать

См. `03-RESEARCH.md → "НЕ рекомендую"`:
- 1С:Напарник
- alkoleft/bsl-graph (alpha)
- infaton/MCP35 (риск CRUD)
- hawkxtreme/mini-ai-1c (десктоп дубль)
- YandexGPT для 1С
- Infostart MCP marketplace

## Чеклист после установки

После установки feenlace/mcp-1c v1.6.5:

- [ ] `.mcp.json` содержит секцию `mcp-1c-readonly`
- [ ] Расширение установлено в `ut_rt_copy` (видно в Конфигураторе → Расширения)
- [ ] Тест: `mcp-1c-windows-amd64.v1.6.5.exe --version` возвращает версию
- [ ] После рестарта Claude Code: `mcp__mcp-1c-readonly__*` tools доступны
- [ ] Smoke-тест: вызвать `get_metadata_tree` — должен вернуть дерево
- [ ] Удалён `tools/mcp-1c-windows-amd64.v1.6.4.exe` (старая нерабочая версия)
- [ ] Обновлена `memory/MEMORY.md` — отметить установку

После установки EDT-MCP v1.31.1 (если решишь делать):

- [ ] EDT 2026.1 установлен полностью
- [ ] Workspace InfoBase5 мигрирован
- [ ] EDT-MCP plugin v1.31.1 установлен в EDT
- [ ] localhost:8770 отвечает
- [ ] Новые tools доступны (find_references, validate_query, screenshots)
- [ ] Старый EDT 2025.2.5 рабочий как fallback
