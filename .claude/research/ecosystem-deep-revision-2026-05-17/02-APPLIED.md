# Phase 1 — Применённые обновления (2026-05-17)

> Безопасные обновления применены в этой сессии. Все деструктивные операции имеют бэкап.

## Сводка

| # | Что | Где | Тип | Реверсивно |
|---|-----|-----|-----|-----------|
| 1 | METR Spring config fix | `.mcp.json` | Edit | ✅ Edit назад |
| 2 | +4 правил comol/ai_rules_1c | `.claude/rules/1c/` | Copy from upstream | ✅ Удалить файлы |
| 3 | +12 obra-скиллов | `.claude/skills/obra-*` | Copy from upstream | ✅ Удалить папки |
| 4 | Обновление 3 cc-1c-skills | `.claude/skills/skd-*, form-validate` | Overwrite | ✅ Бэкапы в `_refresh/local-backups/` |
| 5 | Архив `connect-apps-plugin` | `_refresh/archived/` | Move | ✅ Move назад |
| 6 | Архив `hooks/gsd-*` | `_refresh/archived/hooks-gsd/` | Move | ✅ Move назад |
| 7 | BACKLOG.md обновлён | `.claude/BACKLOG.md` | Edit | ✅ Через git |
| 8 | Скачан бинарь feenlace/mcp-1c | `tools/mcp-1c-windows-amd64.v1.6.5.exe` | Download | ✅ Удалить файл |

## 1. METR Spring config fix

### Проблема
В `.mcp.json` METR ссылался на `application-metr.yml`. По `memory/metr_deep_dive_2026_05_16.md` этот конфиг невалиден (нет `CONFIGURATION` секции). Рабочий конфиг — `application-metr-v2.yml`.

### Что сделано
Изменена строка в `.mcp.json` (секция `metr.args`):
```diff
- "--spring.config.location=file:C:/CLOUDE_PR/tools/application-metr.yml"
+ "--spring.config.location=file:C:/CLOUDE_PR/tools/application-metr-v2.yml"
```

### Проверка
- METR должен запуститься со старта сессии и предоставить 8 tools (run_all_tests, run_module_tests, build_project, dump_config, launch_app, check_syntax_designer_config, check_syntax_designer_modules, check_syntax_edt)
- В подгруженных deferred tools видны: `mcp__metr__build_project`, `mcp__metr__check_syntax_designer_config`, `mcp__metr__check_syntax_designer_modules`, `mcp__metr__check_syntax_edt`, `mcp__metr__dump_config`, `mcp__metr__launch_app`, `mcp__metr__run_all_tests`, `mcp__metr__run_module_tests` ✅

## 2. +4 правил comol/ai_rules_1c

### Источник
github.com/comol/ai_rules_1c (active 2026-05-17 commit `9bb5ec4`)

### Скачано в _refresh/comol-ai-rules/

### Применено
Скопировано в `C:/CLOUDE_PR/.claude/rules/1c/` с переименованием по локальной конвенции (префикс `1c-`):

| Upstream | Local |
|----------|-------|
| `forms.md` | `1c-forms.md` |
| `form-reserved-names.md` | `1c-form-reserved-names.md` |
| `forms-events-add.md` | `1c-forms-events-add.md` |
| `forms-add.md` | `1c-forms-add.md` |

### Содержание новых правил

**1c-forms.md** — router для form-задач, навигация по companion rules для разных типов работы с формами.

**1c-form-reserved-names.md** — критичное правило (защита от runtime-error):
> Запрет имён локальных переменных, совпадающих со свойствами элементов формы: `ПараметрыВыбора`, `СвязиПараметровВыбора`, `СписокВыбора`, `ПараметрыОтбора`, `ОтборСтрок`. В контексте `&НаСервере` платформа может интерпретировать `ПараметрыВыбора = ...` как попытку установить свойство элемента формы — приведёт к ошибке `Несоответствие типов`.

**1c-forms-events-add.md** — wiring обработчиков событий формы (Form.Module.bsl ↔ Form.xml). Шпаргалка по `<Event>` XML-тегам и Russian-handler-name.

**1c-forms-add.md** — инструкция по созданию форм, обязательная валидация через XSD после правки XML.

### Проверка
```bash
ls C:/CLOUDE_PR/.claude/rules/1c/ | grep form
# 1c-form-module-standards.md (был)
# 1c-form-reserved-names.md   (новый)
# 1c-forms-add.md             (новый)
# 1c-forms-events-add.md      (новый)
# 1c-forms.md                 (новый)
```

## 3. +12 obra-скиллов

### Источник
github.com/obra/superpowers — meta-prompting framework

### Скачано в _refresh/obra-superpowers/skills/

### Применено
Скопировано в `C:/CLOUDE_PR/.claude/skills/` с префиксом `obra-` (соответствует существующей конвенции `obra-brainstorming`, `obra-using-superpowers`):

| Skill | Назначение |
|-------|-----------|
| `obra-systematic-debugging` | 4-фазное расследование багов (Reproduce→Hypothesize→Experiment→Fix). Пересекается с нашим `rules/1c/1c-systematic-debugging.md` — взаимодополняемо |
| `obra-test-driven-development` | TDD Red-Green-Refactor. Сопоставимо с нашим `1c-tdd` (для YAxUnit) |
| `obra-verification-before-completion` | Гейт перед "готово" — пересекается с нашим `verification-checklist.md` |
| `obra-writing-plans` | Шаблоны планов перед реализацией |
| `obra-executing-plans` | Execution discipline по плану |
| `obra-dispatching-parallel-agents` | Параллельный запуск subagent'ов (Fan-Out) |
| `obra-using-git-worktrees` | Worktrees для изоляции работы |
| `obra-finishing-a-development-branch` | Завершение ветки разработки |
| `obra-requesting-code-review` | Как запрашивать ревью |
| `obra-receiving-code-review` | Как получать и применять ревью |
| `obra-subagent-driven-development` | Subagent-driven workflow |
| `obra-writing-skills` | Как писать новые скиллы (meta) |

### Подтверждение
В system-reminder показалось что все 12 скиллов доступны через Skill tool после копирования (`obra-systematic-debugging`, `obra-test-driven-development`, и др.).

## 4. Обновление 3 устаревших cc-1c-skills

### Источник
github.com/Nikolay-Shirokov/cc-1c-skills (last commit 2026-05-15 `7fa279c`)

### Скачано в _refresh/cc-1c-skills/

### Что обновлено

**skd-edit** — 8 новых фич от 2026-05-15:
- `set-field-role` — установка роли поля
- `@once` assert — patch-query @once утверждает ровно одно вхождение
- `@hidden` / `@always` — флаги полей
- `modify-structure` — модификация структуры
- `availableValue` — список с replace-семантикой и в add-parameter
- `add-total identity` — identity expression для не-аггрегатных функций
- `clear-conditionalAppearance` — очистка условного оформления
- multiline patch-query — мультистрочные патчи

**skd-info** — `kv-параметры роли` в детализации поля (commit `610720`).

**form-validate** — `silent-skip` числовых и UUID-DataPath, резолв `Items.<Table>.CurrentData.*` (commits `8b0f55`, `54cbc6`). Снимает false-positive ошибки валидации форм.

### Бэкап
Локальные версии до перезаписи сохранены:
- `_refresh/local-backups/skd-edit.bak/`
- `_refresh/local-backups/skd-info.bak/`
- `_refresh/local-backups/form-validate.bak/`

### Реверс (если нужно)
```powershell
cd C:/CLOUDE_PR
rm -rf .claude/skills/skd-edit .claude/skills/skd-info .claude/skills/form-validate
cp -r _refresh/local-backups/skd-edit.bak .claude/skills/skd-edit
cp -r _refresh/local-backups/skd-info.bak .claude/skills/skd-info
cp -r _refresh/local-backups/form-validate.bak .claude/skills/form-validate
```

## 5. Архив `connect-apps-plugin`

### Проблема
`C:/CLOUDE_PR/.claude/plugins/connect-apps-plugin/` содержал только `commands/setup.md`, нет `plugin.json`. Composio MCP не подключён нигде. Файлы — мусор.

### Что сделано
```
mv C:/CLOUDE_PR/.claude/plugins/connect-apps-plugin → C:/CLOUDE_PR/_refresh/archived/connect-apps-plugin
```

### Проверка
```bash
ls C:/CLOUDE_PR/.claude/plugins/
# (пусто)
```

## 6. Архив `hooks/gsd-*`

### Проблема
12 файлов `gsd-*.{js,sh}` в `C:/CLOUDE_PR/.claude/hooks/` НЕ подключены в `settings.local.json`. Это GSD-плагин, который не используется в текущем workflow Транзита.

### Что сделано
```
mv C:/CLOUDE_PR/.claude/hooks/gsd-*.js → C:/CLOUDE_PR/_refresh/archived/hooks-gsd/
mv C:/CLOUDE_PR/.claude/hooks/gsd-*.sh → C:/CLOUDE_PR/_refresh/archived/hooks-gsd/
```

12 файлов перемещены:
- gsd-check-update.js, gsd-check-update-worker.js, gsd-context-monitor.js, gsd-phase-boundary.sh, gsd-prompt-guard.js, gsd-read-guard.js, gsd-read-injection-scanner.js, gsd-session-state.sh, gsd-statusline.js, gsd-update-banner.js, gsd-validate-commit.sh, gsd-workflow-guard.js

### Проверка
```bash
ls C:/CLOUDE_PR/.claude/hooks/
# ecc/  (только ECC поддиректория)
```

## 7. BACKLOG.md обновлён

### Что обновлено
- Пункт 3 (METR): помечен как ✅ УСТАНОВЛЕНО (v0.5.2 актуальная)
- Пункт 5 (mcp-bsl-platform-context v0.3.2): помечен как ✅ УСТАНОВЛЕНО
- Добавлены новые пункты:
  - 4.1 — feenlace/mcp-1c v1.6.5 (🔴 HIGH PRIORITY)
  - 4.2 — Arman-Kudaibergenov/1c-ai-development-kit (🟡 Средний)
  - 4.3 — 1c-syntax/claude-code-bsl-lsp (✅ УСТАНОВЛЕНО)
  - 4.4 — Untru/1c-mcp каталог (🔵 Низкий)
  - 4.5 — EDT-MCP v1.31.1 (⏸️ Заблокировано)

## 8. Скачан бинарь feenlace/mcp-1c v1.6.5

### URL
https://github.com/feenlace/mcp-1c/releases/download/v1.6.5/mcp-1c-windows-amd64.exe

### Куда
`C:/CLOUDE_PR/tools/mcp-1c-windows-amd64.v1.6.5.exe` (14.81 MB)

### Не активирован
- Расширение НЕ установлено в базу `ut_rt_copy`
- НЕ добавлен в `.mcp.json`
- Это решение пользователя — см. **04-COMMANDS.md** для пошаговой инструкции

## Что НЕ применено (специально)

| Категория | Почему |
|-----------|--------|
| ECC массовый refresh (+165 skills, +32 agents) | Контекст уже большой (~400 skills), шум в system prompt |
| wshobson 13 NEW agents | Дальнейшее раздувание агентов |
| Удаление anthropics-* дублей | Требует подтверждения — пересекаются с `anthropic-skills:*` namespace |
| Удаление дубликатов ролей (3× code-reviewer, gsd vs ecc planner и т.д.) | Требует выбора канона |
| Удаление GSD-стека (31 agent + 21 command) | Неясно используется ли в Транзит-workflow |
| comol content/agents/ vs наши 1c-* | Решение про канон 1С-pipeline'а |
| Установка feenlace/mcp-1c в боевую базу | Пишет CFE-расширение в `ut_rt_copy` — нужно решение |

Подробнее: **05-ROADMAP.md**.

## Состояние upstream-клонов

В `C:/CLOUDE_PR/_refresh/`:
- `comol-ai-rules/` — github.com/comol/ai_rules_1c (28 файлов rules)
- `obra-superpowers/` — github.com/obra/superpowers (14 skills)
- `cc-1c-skills/` — github.com/Nikolay-Shirokov/cc-1c-skills (66 skills)
- `local-backups/` — бэкапы перезаписанных файлов
- `archived/` — архив мусора
- `UPDATE_REPORT_2026-05-17.md` — кратко применённое

Можно удалить через `rm -rf C:/CLOUDE_PR/_refresh/` после фиксации в git, либо оставить для следующего refresh.

## Git коммит — рекомендация

```powershell
cd C:/CLOUDE_PR
git add .claude/rules/1c/1c-forms.md .claude/rules/1c/1c-forms-add.md .claude/rules/1c/1c-forms-events-add.md .claude/rules/1c/1c-form-reserved-names.md
git add .claude/skills/obra-systematic-debugging .claude/skills/obra-test-driven-development .claude/skills/obra-verification-before-completion .claude/skills/obra-writing-plans .claude/skills/obra-executing-plans .claude/skills/obra-dispatching-parallel-agents .claude/skills/obra-using-git-worktrees .claude/skills/obra-finishing-a-development-branch .claude/skills/obra-requesting-code-review .claude/skills/obra-receiving-code-review .claude/skills/obra-subagent-driven-development .claude/skills/obra-writing-skills
git add .claude/skills/skd-edit .claude/skills/skd-info .claude/skills/form-validate
git add .claude/BACKLOG.md
git add .mcp.json
git add .claude/research/ecosystem-deep-revision-2026-05-17/

git commit -m "chore(ecosystem): deep revision — +4 comol rules, +12 obra skills, +3 1С skills updates, METR config fix, cleanup
- +4 rules: 1c-forms, 1c-form-reserved-names, 1c-forms-events-add, 1c-forms-add (from comol/ai_rules_1c upstream)
- +12 obra-* skills (systematic-debugging, test-driven-development, verification-before-completion, и др.)
- skd-edit, skd-info, form-validate обновлены до upstream cc-1c-skills 2026-05-15
- METR Spring config: application-metr.yml → application-metr-v2.yml (рабочий)
- Архив: hooks/gsd-* (12 файлов), plugins/connect-apps-plugin → _refresh/archived/
- BACKLOG.md: пункты 4.1-4.5 для новых инструментов
- feenlace/mcp-1c v1.6.5 бинарь скачан в tools/ — не установлен в базу"
```

(не выполнял автоматически — оставил пользователю)
