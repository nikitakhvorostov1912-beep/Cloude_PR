#!/bin/bash
# Запуск Agent Teams через tmux в WSL
# Использование: wsl -d Ubuntu -- bash /mnt/d/Cloude_PR/agent-runtime/setup-wsl.sh

set -e

echo "=== Проверка зависимостей ==="
echo "tmux: $(tmux -V)"
echo "node: $(node --version)"
echo "claude: $(claude --version 2>/dev/null || echo 'нужен логин: claude auth login')"

echo ""
echo "=== Запуск Agent Teams ==="
cd /mnt/d/Cloude_PR

# Очистка runtime перед запуском
rm -rf agent-runtime/shared/*.json agent-runtime/shared/*.md
rm -rf agent-runtime/messages/*.md agent-runtime/state/*.md
echo "Runtime очищен."

# Создание tmux-сессии
if tmux has-session -t agent-team 2>/dev/null; then
    echo "Сессия agent-team уже существует. Подключаюсь..."
    tmux attach -t agent-team
else
    echo "Создаю сессию agent-team..."
    tmux new -s agent-team -c /mnt/d/Cloude_PR
fi
