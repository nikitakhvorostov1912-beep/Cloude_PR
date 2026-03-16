# Руководство по миграции Claude Code + Obsidian

> Перенос полной инфраструктуры с Windows 11 на Windows 10
> Дата: 2026-03-15

## Что переносится

| Компонент | Размер | Метод |
|-----------|--------|-------|
| Проект Cloude_PR (.claude/ внутри) | ~23 МБ | `git clone` |
| Глобальные настройки Claude | ~8.7 МБ | Папка `claude-global/` |
| Obsidian vault | ~1.7 МБ | `git clone` (приватный репо) |

### Состав глобальных настроек

- 40 агентов (1С, ECC, GSD, кастомные)
- 16 глобальных скиллов
- 46 команд (GSD, ECC, кастомные)
- 3 GSD-хука (statusline, context-monitor, check-update)
- GSD workflow (Get Shit Done)
- Плагины (маркетплейс)
- settings.json (глобальные хуки)

---

## Шаг 0: Подготовка на ТЕКУЩЕМ ПК

Уже выполнено:
- [x] Obsidian vault запушен на GitHub (приватный)
- [x] Глобальные настройки экспортированы в `migration-export/claude-global/`
- [x] Скрипты миграции созданы

---

## Шаг 1: Перенос файлов на НОВЫЙ ПК

### Вариант A: Через Git (рекомендуется)

Проект Cloude_PR уже содержит `migration-export/` — просто клонируй:

```bash
# На новом ПК
cd D:\
git clone https://github.com/nikitakhvorostov1912-beep/Cloude_PR.git
```

### Вариант B: Через USB / облако

Скопировать папку `D:\Cloude_PR\migration-export\` на новый ПК.

---

## Шаг 2: Авторизация Claude Code

```bash
claude login
```

Следуй инструкциям в браузере для авторизации.

---

## Шаг 3: Импорт глобальных настроек

```bash
cd D:\Cloude_PR\migration-export
bash migrate-import.sh
```

Скрипт:
- Копирует агенты, скиллы, команды, хуки в `~/.claude/`
- НЕ трогает credentials (используются от авторизации из шага 2)
- Создаёт бэкап существующего settings.json

---

## Шаг 4: Клон Obsidian vault

```bash
# Выбери путь для vault на этом ПК
# Рекомендуется: C:\Users\<user>\Documents\Obsidian Vault
git clone https://github.com/nikitakhvorostov1912-beep/obsidian-vault.git "C:\Users\<user>\Documents\Obsidian Vault"
```

Затем открой Obsidian → Open folder as vault → указать путь.

---

## Шаг 5: Обновить пути в конфигурации

### 5.1 Путь к Obsidian vault в .mcp.json

Откройте `D:\Cloude_PR\.mcp.json` и обновите путь vault:

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "command": "npx",
      "args": ["-y", "@bitbonsai/mcpvault@latest", "C:/Users/<НОВЫЙ_ПОЛЬЗОВАТЕЛЬ>/Documents/Obsidian Vault"]
    }
  }
}
```

### 5.2 Пути в settings.json (глобальные хуки)

Откройте `~/.claude/settings.json` — пути к JS-файлам хуков автоматически используют `$HOME`, менять не нужно.

---

## Шаг 6: Проверка

```bash
cd D:\Cloude_PR
claude
```

### Чек-лист проверки:

- [ ] `claude` запускается без ошибок
- [ ] Агенты видны (попробуй: "используй planner агент")
- [ ] Скиллы видны (попробуй: `/help`)
- [ ] Команды работают (попробуй: `/gsd:help`)
- [ ] MCP obsidian-vault работает (попробуй прочитать заметку)
- [ ] MCP context7 работает
- [ ] MCP playwright работает
- [ ] CLAUDE.md загружается (правила проекта)
- [ ] Память (MEMORY.md) доступна

### 1С проверка:

- [ ] 1С:Предприятие запускается
- [ ] Лицензия активна (Помощь → О программе)
- [ ] Конфигурация загружена
- [ ] Если нужен MCP bsl-context:
  - Java 17+ установлена
  - Путь к платформе: `C:\Program Files\1cv8\8.3.XX.YYYY`

---

## Шаг 7: Синхронизация Obsidian vault (постоянная)

### На ОБОИХ ПК — после работы:

```bash
# Сохранить изменения
cd "<путь к vault>"
git add -A
git commit -m "Обновление vault $(date +%Y-%m-%d)"
git push
```

### На ДРУГОМ ПК — перед работой:

```bash
cd "<путь к vault>"
git pull
```

### Рекомендация: Obsidian Git плагин

Установи плагин **Obsidian Git** в Obsidian:
- Settings → Community plugins → Browse → "Obsidian Git"
- Автоматический pull при запуске
- Автоматический commit+push каждые N минут
- Разрешение конфликтов через интерфейс Obsidian

---

## Архитектура синхронизации

```
┌─────────────────┐         ┌─────────────────┐
│   ПК 1 (Win 11) │         │   ПК 2 (Win 10) │
│                 │         │                 │
│ Obsidian Vault  │──push──→│                 │
│ (OneDrive +Git) │         │ Obsidian Vault  │
│                 │←──pull──│ (Git)           │
│                 │         │                 │
│ Claude Code     │         │ Claude Code     │
│ ├─ .claude/     │         │ ├─ .claude/     │
│ │  (проект)     │ git     │ │  (проект)     │
│ └─ ~/.claude/   │ clone   │ └─ ~/.claude/   │
│    (глобальные) │ ──────→ │    (из архива)  │
│                 │         │                 │
│       GitHub    │         │       GitHub    │
│  ┌──────────────┴─────────┴──────────────┐  │
│  │ obsidian-vault (private)              │  │
│  │ Cloude_PR (project repo)              │  │
│  └───────────────────────────────────────┘  │
└─────────────────┘         └─────────────────┘
```

---

## Важные замечания

1. **Credentials НЕ переносятся** — на каждом ПК свой `claude login`
2. **settings.local.json** — в Git, переносится с проектом автоматически
3. **Пути в .mcp.json** — нужно обновить под нового пользователя
4. **OneDrive** — на новом ПК vault через Git, не OneDrive
5. **Конфликты Git** — Obsidian Git плагин помогает разрешать
