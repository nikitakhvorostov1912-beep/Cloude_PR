# Audit — состояние ДО ревизии (2026-05-17)

> Параллельный аудит экосистемы через 4 независимых subagent'а. Каждый отвечал за свой блок.

## Метод

В единый Agent-блок отправлено 4 параллельных запроса (Fan-Out паттерн):
- **Agent A:** 1С-skills (cc-1c-skills от Nikolay-Shirokov) + rules/1c/ (от comol/ai_rules_1c)
- **Agent B:** Внешние скиллы (anthropics-*, obra-*, davila7-*, ecc/, и др.)
- **Agent C:** Агенты (1c-*, gsd-*, team-*, ecc/, bpm-*, и др.)
- **Agent D:** MCP-серверы, JAR-инструменты, hooks, plugins

Все 4 агента вернули результаты в одном tool-call message (parallel execution).

## Audit A — 1С-skills и rules

### cc-1c-skills (Nikolay-Shirokov)

**Upstream:** https://github.com/Nikolay-Shirokov/cc-1c-skills

- Last upstream commit: 2026-05-15 (`7fa279c` — `feat(skd-edit): clear-conditionalAppearance + multiline patch-query`)
- Активная разработка — 10+ коммитов за один день 2026-05-15
- Last local sync (filesystem mtime): 2026-05-13 17:15:47

**Сравнение:**
- Upstream: 66 скиллов
- Local: 68 скиллов (66 upstream + 2 кастомных: `epf-add-form`, `web-asset-generator`)
- NEW в upstream (отсутствуют локально): ОТСУТСТВУЮТ

**Устаревшие (требуют обновления):**

| Skill | Что нового | Detected |
|-------|------------|----------|
| `skd-edit` | 8 фич от 2026-05-15: set-field-role, @once, @hidden/@always, modify-structure, availableValue, add-total identity, clear-conditionalAppearance, multiline patch-query | Локально найдено только 2 из 8 паттернов |
| `skd-info` | kv-параметры роли в детализации поля (commit `610720`) | Отсутствует |
| `form-validate` | silent-skip числовых и UUID-DataPath, резолв `Items.<Table>.CurrentData.*` (commits `8b0f55`, `54cbc6`) | Отсутствует |
| `form-compile` | ColumnGroup DSL (2026-05-04) | Уже локально применено — OK |

**Актуальные:** ~60 из 66 скиллов без upstream-изменений после 2026-05-13.

### ai_rules_1c (comol)

**Upstream:** https://github.com/comol/ai_rules_1c

- Last upstream commit: 2026-05-17 (`9bb5ec4` — «некоторые улучшения»)
- Активные коммиты 14-17 мая 2026
- Upstream rules total: 28 файлов в `content/rules/`

**NEW rules в upstream (отсутствуют локально):**

| Файл | Назначение |
|------|-----------|
| `forms.md` | router-файл для form-задач (навигация по companion rules) |
| `form-reserved-names.md` | запрет имён переменных совпадающих со свойствами элементов формы (ПараметрыВыбора, СписокВыбора и т.д.) |
| `forms-events-add.md` | wiring обработчиков событий формы (Form.Module.bsl ↔ Form.xml) |
| `forms-add.md` | отдельная инструкция по созданию форм |
| `coding-standards.md` | (вероятно слит с `core-standards.md` локально) |

**Соответствия upstream → local** (ребрендинг):
- `dev-standards-core.md` → `1c-core-standards.md`
- `dev-standards-architecture.md` → `1c-architecture-standards.md`
- `dev-standards-forms.md` → `1c-form-module-standards.md`
- `platform-solutions.md` → `1c-platform-cookbook.md`
- `locks-and-transactions.md` → `1c-locks-transactions.md`
- `form-module.md` → `1c-form-module-standards.md` (overlap)

## Audit B — внешние скиллы (~120 папок)

### По префиксам

| Префикс | Локально | Upstream | NEW в upstream | Статус |
|---------|----------|----------|-----------------|--------|
| `anthropics-*` | 18 | 17 (anthropics/skills) | 11 (algorithmic-art, claude-api, brand-guidelines, docx, internal-comms, pptx, slack-gif-creator, theme-factory, web-artifacts-builder, xlsx, doc-coauthoring) | 9 локальных НЕ из официального — community форк |
| `ecc/` | 65 | 230 (v1.9.0) | +165 | КРИТИЧНО УСТАРЕЛО |
| `davila7-*` | 5 | (агрегатор) | N/A | Снимок, не растёт |
| `obra-*` | 2 | 14 | 12 (systematic-debugging, test-driven-development, verification-before-completion, writing-plans, executing-plans, dispatching-parallel-agents, using-git-worktrees, finishing-a-development-branch, requesting-code-review, receiving-code-review, subagent-driven-development, writing-skills) | Значимая нехватка |
| `wshobson-*` | 1 (только prompt-engineering-patterns) | 153 (заявлено) | Много | Минимальный импорт |
| `1c-*` | 14 | — | — | Кастомные, наши |

### Источники найденные

| Префикс | Repo |
|---------|------|
| anthropics-* | github.com/anthropics/skills (но 9 — НЕ из официального) |
| obra-* | github.com/obra/superpowers |
| ecc/ | github.com/affaan-m/everything-claude-code (v2.0.0-rc.1, 170K stars) |
| davila7-* | github.com/davila7/claude-code-templates |
| wshobson-* | github.com/wshobson/agents |

### Источники не найдены (одиночные импорты)

`composiohq-content-research-writer`, `tapestry-article-extractor`, `nextlevelbuilder-ui-ux-pro-max`, `smithery-ai-cli`, `langchain-ai-web-research`, `openstatushq-find-skills`, `vercel-labs-agent-browser` — единичные случайные импорты, к 1С-стеку не относятся.

## Audit C — агенты (78 файлов)

### Кастомные 1С агенты

`1c-code-architect`, `1c-code-explorer`, `1c-code-reviewer`, `1c-code-simplifier`, `1c-code-writer`, `1c-data-analyst` — все на `model: sonnet`, локальные, на русском, без upstream.

**Параллельно** в `content/agents/` от comol/ai_rules_1c существует 13 структурированных 1С-субагентов с pipeline `1c-subagent-pipeline.md` — НО они НЕ скопированы локально. Возможный дубликат функций.

### ECC агенты

**Upstream:** github.com/affaan-m/everything-claude-code — 170K stars, v2.0.0-rc.1 (апрель 2026), всего **48 агентов** в upstream.

**Локально:** 16 файлов в `agents/ecc/`. **Устарели:**
- Отсутствуют: `docs-lookup`, `mle-reviewer`, `typescript-reviewer`, `cpp-reviewer`, `fsharp-reviewer`, `java-reviewer`, `kotlin-reviewer`, `rust-reviewer`, `cpp-build-resolver`, `java-build-resolver`, `kotlin-build-resolver`, `rust-build-resolver`, `pytorch-build-resolver`, `harmonyos-app-resolver`

### wshobson агенты

**Upstream:** github.com/wshobson/agents — 185 агентов в 80 plugins (383 коммита).

**Локально:** ~17 агентов взято: `ai-engineer`, `api-designer`, `devops-engineer`, `docker-expert`, `documentation-engineer`, `financial-analyst`, `kubernetes-specialist`, `mcp-developer`, `mlops-engineer`, `performance-engineer`, `prompt-engineer`, `qa-automation`, `rapid-prototyper`, `security-researcher`, `sprint-prioritizer`, `terraform-engineer`, `vector-database-engineer`.

**Все продублированы в `agents-archive/`** — фактически выключены, но опять рядом.

**NEW в upstream (отсутствуют локально):** `python-pro`, `django-pro`, `fastapi-pro`, `typescript-pro`, `backend-architect`, `database-architect`, `frontend-developer`, `test-automator`, `security-auditor`, `deployment-engineer`, `observability-engineer`, `blockchain-developer`, `kubernetes-architect`.

### GSD агенты

**Source:** github.com/gsd-build/get-shit-done — meta-prompting framework.

**Локально:** 31 `gsd-*` агент. Связаны со slash-commands `/gsd:*` (21 команда).

**Status:** актуально, но **связка с workflow Транзита неочевидна** — нужно ревью, реально ли используется.

### Кастомные авторские (без upstream)

- `team-*` (8 шт.) — на русском, без frontmatter (`team-coder` начинается с `# team-coder`). Дублированы в archive.
- `bpm-*` (4 шт.) — BPMN-аудит, кастомные. Дублированы в archive.
- `nexus-orchestrator`, `code-scout`, `bug-hunter`, `deep-researcher`, `code-reviewer`, `parallel-executor`, `pre-commit-guard`, `research-fetcher`, `artifact-validator` — авторская сборка на русском.

### Дубликаты ролей

| Роль | Версии |
|------|--------|
| code-reviewer | `code-reviewer.md` (root) + `gsd-code-reviewer.md` + `ecc/code-reviewer.md` |
| planner | `gsd-planner.md` + `ecc/planner.md` |
| debugger | `bug-hunter.md` + `gsd-debugger.md` |
| doc-writer | `gsd-doc-writer.md` + `ecc/doc-updater.md` + `documentation-engineer.md` |
| security | `gsd-security-auditor.md` + `ecc/security-reviewer.md` + `security-researcher.md` |

## Audit D — MCP серверы, tools, hooks, plugins

### Версии MCP — все актуальны

| Сервер | Локально | Upstream | Update? |
|--------|----------|----------|---------|
| mcp-bsl-context | v0.3.2 (`tools/mcp-bsl-context-0.3.2.jar`, 42 MB) | v0.3.2 (2026-03-11) | NO |
| METR | v0.5.2 (`tools/mcp-onec-test-runner.jar`, 47 MB) | v0.5.2 (2026-03-16) | NO |
| BSL Language Server | v0.29.0 (`tools/bsl-language-server-0.29.0-exec.jar`, 115 MB) | v0.29.0 (2026-03-25, latest stable) | NO (0.30.0-ra.1 — pre-release) |
| YAxUnit | 25.12 (`InfoBase5`) | 25.12 (2025-12-31) | NO |
| 1c-transit | MCP Toolkit v1.7.0 (port 6010) | UncleSerg upstream | OK |
| edt-mcp | плагин EDT v1.26.1 (port 8770) | v1.31.1 | заблокировано EDT 2025.2 |
| mcp-1c | v1.6.4.exe (по MEMORY нерабочее, не подключён в `.mcp.json`) | v1.6.5 | устаревший бинарь |

### Tools на диске (`C:/CLOUDE_PR/tools/`)

**Актуально:**
- `bsl-language-server-0.29.0-exec.jar` (115 MB)
- `mcp-bsl-context-0.3.2.jar` (42 MB)
- `mcp-onec-test-runner.jar` (47 MB)
- `MCP_Toolkit_v1.7.0.epf` (1.8 MB)
- `jdk-17/`, `jdk-21/`
- `application-metr-v2.yml` (по MEMORY: v2 работает)

**Кандидаты на чистку:**
- `MCP_Toolkit_x86.epf` — старая версия
- `mcp-1c-windows-amd64.v1.6.4.exe` — по MEMORY нерабочее
- `_archive/`, `_archive_purge_2026-05-16/`, `_feron_imgs/` — архивные папки
- `cloudflared.exe` (66 MB), `ngrok/`, `apache24/` — не используются
- `application-metr.yml` — старая невалидная конфигурация METR

### Hooks

**Активные** (в `~/.claude/hooks-handlers-1c/`):
- `post-bsl-edit.sh` — детект A1/A2/A6/A8/A11 + Матаков#1-3 + Latin/Cyrillic
- `post-form-edit.sh` — валидация Form.xml, дубли ID
- `tdad-trigger.sh`
- `post-compact.sh`
- `post-tool-failure-bsl.sh`
- `stop-gate-bsl.sh` — БЛОКИРУЕТ Stop при критических нарушениях
- `worktree-create.sh`

**В `C:/CLOUDE_PR/.claude/hooks-handlers/`:**
- `session-boot.sh`, `session-resume.sh`

**Мусор (НЕ подключены в settings.local.json):**

`C:/CLOUDE_PR/.claude/hooks/`:
- 12 файлов `gsd-*.{js,sh}` (gsd-check-update.js, gsd-context-monitor.js, gsd-phase-boundary.sh, gsd-prompt-guard.js, gsd-read-guard.js, gsd-read-injection-scanner.js, gsd-session-state.sh, gsd-statusline.js, gsd-update-banner.js, gsd-validate-commit.sh, gsd-workflow-guard.js, gsd-check-update-worker.js)

### Plugins

- `plugins/connect-apps-plugin/` — содержит только `commands/setup.md`, нет `plugin.json` → **пустышка** (Composio MCP не подключён)

### Конфигурационные проблемы

- `.mcp.json` → METR ссылается на невалидный `application-metr.yml` (вместо рабочего `application-metr-v2.yml`) — потенциально не запускается

## Состояние git

- **559 modified files** в `git status` (локальные правки в скриптах скиллов)
- 1 stash (`epitaxy: pre-switch from feature/transit-v4-tasks`)
- Текущая ветка: `feature/transit-v4-tasks`
- Последние коммиты:
  - `a1a6176b` — fix(transit): ЗагрузкаРееструТД маппинг по имени колонок + APIСигма CMR
  - `64a2b622` — fix(ЗагрузкаРееструТД): СтрШаблон с 13 параметрами разбит на 9+4
  - `eb5e6a18` — Revert "feat(ЗагрузкаРееструТД): фильтр чужих ТД"
  - `478d27c7` — Revert "refactor: переименовать «БезНомеров» → «Пропустить»"
  - `39391d1d` — refactor: переименовать «БезНомеров» → «Пропустить»

## Выводы аудита

### Что обновить (применено в Phase 1 — см. 02-APPLIED.md)
1. METR config: `application-metr.yml` → `application-metr-v2.yml`
2. +4 новых правил comol (forms.md, form-reserved-names.md, forms-events-add.md, forms-add.md)
3. +12 obra-скиллов (systematic-debugging, test-driven-development, verification-before-completion и др.)
4. Обновить 3 устаревших cc-1c-skills (skd-edit, skd-info, form-validate)
5. Чистка мусора (connect-apps-plugin, hooks/gsd-*)

### Что требует решения пользователя (см. 05-ROADMAP.md)
1. ECC массовый refresh (65→230 skills, 16→48 agents)
2. wshobson 13 NEW агентов
3. anthropics-* локальные дубли (officials через `anthropic-skills:*` namespace)
4. Дубликаты ролей агентов
5. GSD-стек — реально используется?
6. content/agents/ comol vs наши 1c-* — какой канон?
