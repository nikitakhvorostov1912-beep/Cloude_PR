# Запуск Agent Team

Создай Agent Team для выполнения задачи пользователя. Pipeline формируется динамически на основе задачи.

## Инструкции

1. Проанализируй задачу пользователя: $ARGUMENTS
2. Определи тип pipeline:

### Автоматический выбор pipeline

| Задача | Pipeline | Агенты |
|--------|---------|--------|
| Исследование, мониторинг, обзор | research | scraper → analyst → reporter |
| Исправить баг, мелкая правка | quick-fix | coder → reviewer |
| Новая фича, реализация | feature | architect → coder → reviewer → tester |
| Фича с исследованием | full-cycle | scraper → analyst → architect → coder → reviewer → tester |
| Спланировать, спроектировать | plan-only | architect |
| Ревью кода | review-only | reviewer |
| Полный цикл с отчётом | complete | scraper → analyst → architect → coder → reviewer → tester → reporter |

3. Очисти runtime: `rm -rf agent-runtime/shared/*.json agent-runtime/shared/*.md agent-runtime/messages/*.md agent-runtime/state/*.md`
4. Создай plan в `agent-runtime/state/plan.md`:
   - Задача
   - Выбранный pipeline
   - Конкретное задание для каждого агента
   - Проект и путь (если dev pipeline)
5. Создай команду через TeamCreate
6. Запусти агентов через Agent tool (с `team_name`, `name`, `mode: bypassPermissions`)
7. Первому агенту дай полное задание в prompt. Остальным — инструкцию ждать SendMessage
8. Координируй: мониторь сообщения, передавай между агентами
9. После завершения: shutdown всех агентов → TeamDelete → брифинг

## Важно для dev-pipeline

- В prompt каждого агента указывай **путь к проекту** и **стек**
- Architect и Coder получают путь к CLAUDE.md проекта
- Coder работает ТОЛЬКО по плану architect (не импровизирует)
- Reviewer проверяет соответствие плану + качество
- Tester пишет тесты в стиле проекта
- Revision loop: reviewer → coder (макс 2 итерации)

## Аргумент

$ARGUMENTS — описание задачи. Если пустой — спроси у пользователя.
