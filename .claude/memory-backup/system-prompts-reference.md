# Справочник системных промптов AI-инструментов

> Источник: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools (130k+ stars)

## Покрытые инструменты (31)

| Категория | Инструменты |
|-----------|------------|
| Coding assistants | Cursor, Windsurf, VSCode Agent, Augment Code, Trae, Z.ai Code |
| AI builders | v0 (Vercel), Lovable, Replit, Same.dev, Leap.new |
| LLM-платформы | Claude (Anthropic), Google (Gemini), Perplexity |
| Autonomous agents | Devin AI, Manus, Kiro, Junie |
| Specialized | Xcode, Warp.dev, NotionAI, CodeBuddy, Qoder, Dia |

## Ключевые паттерны системных промптов

### 1. Структура промпта (общий шаблон)

```
1. Identity & Role — кто ты, кем создан
2. Knowledge cutoff — дата отсечки знаний
3. Capabilities — что можешь (image input, web search, etc.)
4. Tools definition — описание каждого инструмента
5. Behavioral rules — как себя вести
6. Code generation rules — стандарты кода
7. Safety & security — ограничения безопасности
8. Communication style — тон, формат ответов
9. Memory system — как запоминать контекст
10. Planning system — как планировать задачи
```

### 2. Паттерн "Tool Documentation" (Cursor, Claude Code)

Каждый инструмент описывается по схеме:
- **Когда использовать** (When to Use)
- **Когда НЕ использовать** (When NOT to Use)
- **Примеры** (хороший/плохой вызов)
- **Параметры** (TypeScript-подобная типизация)

### 3. Паттерн "Making Code Changes" (Windsurf, Lovable)

```
- NEVER output code to the user — use code edit tools
- Code must be immediately runnable
- Add ALL necessary imports
- Break large edits (>300 lines) into smaller ones
- After changes: brief summary + proactive run
```

### 4. Паттерн "Safety Boundaries" (все инструменты)

```
- Unsafe commands → НЕ запускать автоматически
- Never hardcode secrets/API keys
- Never make destructive changes without confirmation
- Refuse malicious requests gracefully
```

### 5. Паттерн "Memory/Context" (Windsurf, Cursor, Claude Code)

```
- Persistent memory database для будущих сессий
- Proactive save — сохранять важное сразу, не ждать
- Auto-retrieval — релевантные воспоминания подгружаются автоматически
- Context window awareness — сохранять до потери контекста
```

### 6. Паттерн "Concise Communication" (Claude Code 2.0, Lovable)

```
- Minimize output tokens
- No preamble/postamble
- Don't explain code unless asked
- Brief confirmation after task completion
- 1-3 sentences when possible
```

### 7. Паттерн "Planning" (Windsurf, v0)

```
- Maintain a plan of action
- Update plan when: new instructions, completed items, scope changes
- Update BEFORE committing to significant work
- Update AFTER completing a lot of work
```

## Сравнение подходов

| Аспект | Cursor | Windsurf | Claude Code | v0 | Lovable |
|--------|--------|----------|-------------|----|---------|
| Поиск | codebase_search (семантический) + grep | find_by_name + grep | Glob + Grep | — | search |
| Редактирование | edit_file | replace_file_content | Edit | Write | search-replace |
| Память | update_memory (persistent) | create_memory (proactive) | TodoWrite + memory files | — | useful-context |
| Планирование | — | update_plan (mandatory) | TodoWrite | AskUserQuestions | discussion mode |
| Стиль | concise | pair programming | minimal output | markdown | <2 lines |
| Безопасность | unsafe check | never auto-run unsafe | destructive action check | — | clarify first |

## Полезные техники для наших скиллов/агентов

1. **"When to Use / When NOT to Use"** → добавить в описания агентов
2. **Good/Bad examples в tool docs** → улучшить описания инструментов
3. **Proactive memory** → наша система memory уже реализована
4. **Plan-before-act** → EnterPlanMode уже есть
5. **Batch operations** → параллельные вызовы агентов (уже делаем)
6. **Safety boundaries** → pre-commit-guard агент
