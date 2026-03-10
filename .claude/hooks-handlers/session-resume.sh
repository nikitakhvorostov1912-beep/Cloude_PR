#!/usr/bin/env bash

# Session Resume — краткий контекст при возобновлении сессии

BRANCH=$(git -C "D:/Cloude_PR" branch --show-current 2>/dev/null || echo "unknown")
DIFF_STAT=$(git -C "D:/Cloude_PR" diff --stat HEAD 2>/dev/null | tail -5)
STASH_COUNT=$(git -C "D:/Cloude_PR" stash list 2>/dev/null | wc -l)

cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionResume",
    "additionalContext": "## Session Resumed\n\n- Ветка: ${BRANCH}\n- Stash: ${STASH_COUNT} записей\n- Изменения с последнего коммита:\n${DIFF_STAT:-нет изменений}\n\nПродолжай работу с того места, где остановился."
  }
}
EOF

exit 0
