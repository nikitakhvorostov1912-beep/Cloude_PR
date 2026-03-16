#!/bin/bash
# ============================================================
# ИМПОРТ НАСТРОЕК CLAUDE CODE — новый ПК (Windows 10)
#
# ПЕРЕД ЗАПУСКОМ:
# 1. Claude Code уже установлен и авторизован
# 2. Node.js установлен (для npx)
# 3. Git установлен
# 4. Папка claude-global скопирована на этот ПК
# ============================================================

CLAUDE_HOME="$HOME/.claude"
IMPORT_DIR="$(dirname "$0")/claude-global"

echo "============================================================"
echo "  ИМПОРТ НАСТРОЕК CLAUDE CODE НА НОВЫЙ ПК"
echo "============================================================"
echo ""
echo "Источник:    $IMPORT_DIR"
echo "Назначение:  $CLAUDE_HOME"
echo ""

# Проверка что import dir существует
if [ ! -d "$IMPORT_DIR" ]; then
    echo "❌ ОШИБКА: Не найдена папка $IMPORT_DIR"
    echo "   Скопируйте claude-global/ рядом с этим скриптом"
    exit 1
fi

# Проверка что Claude Code установлен
if ! command -v claude &> /dev/null; then
    echo "❌ ОШИБКА: Claude Code не найден"
    echo "   Установите: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

echo "✅ Claude Code найден: $(claude --version 2>/dev/null || echo 'версия неизвестна')"
echo ""

# Создаём ~/.claude если нет
mkdir -p "$CLAUDE_HOME"

# ===== ИМПОРТ =====

# 1. Агенты
echo "[1/8] Импорт агентов..."
if [ -d "$IMPORT_DIR/agents" ]; then
    mkdir -p "$CLAUDE_HOME/agents"
    cp -r "$IMPORT_DIR/agents/"* "$CLAUDE_HOME/agents/" 2>/dev/null
    echo "  ✅ $(ls "$CLAUDE_HOME/agents" 2>/dev/null | wc -l) агентов"
else
    echo "  ⚠️  Нет агентов для импорта"
fi

# 2. Скиллы
echo "[2/8] Импорт скиллов..."
if [ -d "$IMPORT_DIR/skills" ]; then
    mkdir -p "$CLAUDE_HOME/skills"
    cp -r "$IMPORT_DIR/skills/"* "$CLAUDE_HOME/skills/" 2>/dev/null
    echo "  ✅ $(find "$CLAUDE_HOME/skills" -name 'SKILL.md' 2>/dev/null | wc -l) скиллов"
else
    echo "  ⚠️  Нет скиллов для импорта"
fi

# 3. Команды
echo "[3/8] Импорт команд..."
if [ -d "$IMPORT_DIR/commands" ]; then
    mkdir -p "$CLAUDE_HOME/commands"
    cp -r "$IMPORT_DIR/commands/"* "$CLAUDE_HOME/commands/" 2>/dev/null
    echo "  ✅ $(find "$CLAUDE_HOME/commands" -name '*.md' 2>/dev/null | wc -l) команд"
else
    echo "  ⚠️  Нет команд для импорта"
fi

# 4. Хуки
echo "[4/8] Импорт хуков..."
if [ -d "$IMPORT_DIR/hooks" ]; then
    mkdir -p "$CLAUDE_HOME/hooks"
    cp -r "$IMPORT_DIR/hooks/"* "$CLAUDE_HOME/hooks/" 2>/dev/null
    echo "  ✅ Хуки импортированы"
fi
if [ -d "$IMPORT_DIR/hooks-handlers" ]; then
    mkdir -p "$CLAUDE_HOME/hooks-handlers"
    cp -r "$IMPORT_DIR/hooks-handlers/"* "$CLAUDE_HOME/hooks-handlers/" 2>/dev/null
    echo "  ✅ Хук-обработчики импортированы"
fi

# 5. GSD
echo "[5/8] Импорт GSD..."
if [ -d "$IMPORT_DIR/get-shit-done" ]; then
    cp -r "$IMPORT_DIR/get-shit-done" "$CLAUDE_HOME/get-shit-done" 2>/dev/null
    echo "  ✅ GSD импортирован"
else
    echo "  ⚠️  Нет GSD для импорта"
fi

# 6. Плагины
echo "[6/8] Импорт плагинов..."
if [ -d "$IMPORT_DIR/plugins" ]; then
    mkdir -p "$CLAUDE_HOME/plugins"
    cp -r "$IMPORT_DIR/plugins/"* "$CLAUDE_HOME/plugins/" 2>/dev/null
    echo "  ✅ Плагины импортированы"
fi

# 7. Конфигурация
echo "[7/8] Импорт конфигурации..."
if [ -f "$IMPORT_DIR/settings.json" ]; then
    # Бэкап существующего
    if [ -f "$CLAUDE_HOME/settings.json" ]; then
        cp "$CLAUDE_HOME/settings.json" "$CLAUDE_HOME/settings.json.backup"
        echo "  📋 Бэкап текущего settings.json создан"
    fi
    cp "$IMPORT_DIR/settings.json" "$CLAUDE_HOME/settings.json"
    echo "  ✅ settings.json импортирован"
fi
[ -f "$IMPORT_DIR/gsd-file-manifest.json" ] && cp "$IMPORT_DIR/gsd-file-manifest.json" "$CLAUDE_HOME/"
[ -f "$IMPORT_DIR/package.json" ] && cp "$IMPORT_DIR/package.json" "$CLAUDE_HOME/"

# 8. Скрипты
echo "[8/8] Импорт скриптов..."
if [ -d "$IMPORT_DIR/scripts" ]; then
    mkdir -p "$CLAUDE_HOME/scripts"
    cp -r "$IMPORT_DIR/scripts/"* "$CLAUDE_HOME/scripts/" 2>/dev/null
    echo "  ✅ Скрипты импортированы"
fi

echo ""
echo "============================================================"
echo "  ИМПОРТ ЗАВЕРШЁН"
echo "============================================================"
echo ""
echo "=== СЛЕДУЮЩИЕ ШАГИ (вручную) ==="
echo ""
echo "1. АВТОРИЗАЦИЯ Claude Code:"
echo "   claude login"
echo ""
echo "2. КЛОН ПРОЕКТА:"
echo "   cd D:\\"
echo "   git clone https://github.com/nikitakhvorostov1912-beep/Cloude_PR.git"
echo "   cd Cloude_PR"
echo ""
echo "3. КЛОН OBSIDIAN VAULT:"
echo "   Выберите путь для vault (например: C:\\Users\\<user>\\Documents\\Obsidian Vault)"
echo "   git clone https://github.com/nikitakhvorostov1912-beep/obsidian-vault.git \"<путь>\""
echo ""
echo "4. ОБНОВИТЬ ПУТЬ VAULT В .mcp.json:"
echo "   Откройте D:\\Cloude_PR\\.mcp.json"
echo "   Замените путь obsidian-vault на путь на ЭТОМ компьютере"
echo ""
echo "5. ПРОВЕРКА:"
echo "   cd D:\\Cloude_PR"
echo "   claude"
echo "   → Проверить что агенты, скиллы, команды доступны"
echo "   → Проверить что MCP obsidian-vault работает"
echo ""
echo "6. 1С ПРОВЕРКА:"
echo "   → Убедиться что 1С Предприятие запускается"
echo "   → Проверить лицензию: Помощь → О программе"
echo "   → Подключить MCP bsl-context (если нужно):"
echo "     Путь к платформе: C:\\Program Files\\1cv8\\8.3.XX.YYYY"
echo ""
