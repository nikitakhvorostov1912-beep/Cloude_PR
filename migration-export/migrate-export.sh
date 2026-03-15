#!/bin/bash
# ============================================================
# ЭКСПОРТ НАСТРОЕК CLAUDE CODE — текущий ПК → архив
# Запускать на ТЕКУЩЕМ ПК (Windows 11)
# ============================================================

CLAUDE_HOME="$HOME/.claude"
EXPORT_DIR="D:/Cloude_PR/migration-export/claude-global"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Экспорт глобальных настроек Claude Code ==="
echo "Источник: $CLAUDE_HOME"
echo "Назначение: $EXPORT_DIR"
echo ""

# Создаём структуру
mkdir -p "$EXPORT_DIR"

# 1. Агенты (40 шт — критично)
echo "[1/8] Копирование агентов..."
cp -r "$CLAUDE_HOME/agents" "$EXPORT_DIR/agents" 2>/dev/null
echo "  → $(ls "$EXPORT_DIR/agents" 2>/dev/null | wc -l) агентов"

# 2. Скиллы (16 шт — критично)
echo "[2/8] Копирование скиллов..."
cp -r "$CLAUDE_HOME/skills" "$EXPORT_DIR/skills" 2>/dev/null
echo "  → $(find "$EXPORT_DIR/skills" -name 'SKILL.md' 2>/dev/null | wc -l) скиллов"

# 3. Команды (15 шт — критично)
echo "[3/8] Копирование команд..."
cp -r "$CLAUDE_HOME/commands" "$EXPORT_DIR/commands" 2>/dev/null
echo "  → $(find "$EXPORT_DIR/commands" -name '*.md' 2>/dev/null | wc -l) команд"

# 4. Хуки (GSD hooks — важно)
echo "[4/8] Копирование хуков..."
cp -r "$CLAUDE_HOME/hooks" "$EXPORT_DIR/hooks" 2>/dev/null
cp -r "$CLAUDE_HOME/hooks-handlers" "$EXPORT_DIR/hooks-handlers" 2>/dev/null
echo "  → $(ls "$EXPORT_DIR/hooks" 2>/dev/null | wc -l) хуков"

# 5. GSD (Get Shit Done workflow)
echo "[5/8] Копирование GSD..."
cp -r "$CLAUDE_HOME/get-shit-done" "$EXPORT_DIR/get-shit-done" 2>/dev/null
echo "  → GSD скопирован"

# 6. Плагины
echo "[6/8] Копирование плагинов..."
cp -r "$CLAUDE_HOME/plugins" "$EXPORT_DIR/plugins" 2>/dev/null
echo "  → Плагины скопированы"

# 7. Конфигурационные файлы
echo "[7/8] Копирование конфигурации..."
cp "$CLAUDE_HOME/settings.json" "$EXPORT_DIR/settings.json" 2>/dev/null
cp "$CLAUDE_HOME/gsd-file-manifest.json" "$EXPORT_DIR/gsd-file-manifest.json" 2>/dev/null
cp "$CLAUDE_HOME/package.json" "$EXPORT_DIR/package.json" 2>/dev/null
echo "  → Конфигурация скопирована"

# 8. Скрипты
echo "[8/8] Копирование скриптов..."
cp -r "$CLAUDE_HOME/scripts" "$EXPORT_DIR/scripts" 2>/dev/null
echo "  → Скрипты скопированы"

echo ""
echo "=== НЕ КОПИРУЕМ (не нужно на новом ПК) ==="
echo "  ✗ .credentials.json (перелогин на новом ПК)"
echo "  ✗ projects/ (~350 МБ логов сессий)"
echo "  ✗ cache/, debug/, telemetry/, backups/"
echo "  ✗ session-env/, shell-snapshots/, todos/"
echo ""

# Итого
TOTAL_SIZE=$(du -sh "$EXPORT_DIR" 2>/dev/null | cut -f1)
echo "=== ИТОГО ==="
echo "Размер экспорта: $TOTAL_SIZE"
echo "Путь: $EXPORT_DIR"
echo ""
echo "Следующий шаг: скопировать $EXPORT_DIR на новый ПК"
echo "и запустить migrate-import.sh"
