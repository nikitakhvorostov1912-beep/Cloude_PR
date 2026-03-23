# Core Rules

## Перед любой задачей — Research First

**Прежде чем писать код:**
1. Поищи существующие решения: npm/PyPI/GitHub — есть ли библиотека которая решает 80%+ задачи?
2. Если есть — изучи принцип работы, предложи пользователю: "Есть готовое решение X, вот как оно работает. Взять за основу или делать своё?"
3. Пользователь решает. Молча изобретать велосипед — запрещено.

**Творческий подход** = уникальный дизайн/архитектура/UX, НЕ отказ от готовых библиотек.

---

## Доработка существующего кода

Перед написанием ЛЮБОЙ строки кода:

### Фаза 1 — Разведка (обязательно, нельзя пропустить)
1. Прочитай все файлы которые затронет задача
2. Grep по имени изменяемой функции/класса — найди все места использования
3. Проверь наличие тестов
4. Сообщи: "Затронутые файлы: X. Зависимости: Y. Тесты: есть/нет"

### Фаза 2 — План (озвучить до кода)
- Что именно меняю и где
- Что может сломаться
- Как проверю что работает

### Фаза 3 — Реализация
- Минимум изменений для решения задачи
- Не рефакторить то что не просили
- После каждого изменённого файла — проверить синтаксис/билд

### Фаза 4 — Верификация (обязательно, нельзя пропустить)
- Запустить сервер/приложение если не запущен
- Открыть в браузере / вызвать endpoint / запустить сценарий — убедиться глазами
- Запустить тесты если есть
- Проверить edge cases: null, пустые данные, граничные значения
- **Только после реальной проверки** — сообщить что готово

### Запрещено
- Писать код не завершив Фазу 1
- Сообщать "готово" без реальной проверки в Фазе 4
- Говорить "должно работать" вместо "проверил — работает"
- Молча пропускать шаги если "кажется очевидным"

---

## Coding Style

- **Immutability (CRITICAL):** NEVER mutate — always return new copies
- Files: 200–400 lines typical, 800 max. High cohesion, low coupling, organized by feature/domain
- Functions < 50 lines, nesting ≤ 4 levels, no hardcoded values
- Always handle errors explicitly at every level — never swallow silently
- Validate all input at system boundaries; never trust external data

---

## Git

Commit format: `<type>: <description>` — types: feat, fix, refactor, docs, test, chore, perf, ci
PRs: use `git diff [base]...HEAD`, comprehensive summary, test plan included

---

## Security (check before every commit)

- [ ] No hardcoded secrets — use env vars
- [ ] All inputs validated, SQL parameterized, HTML sanitized
- [ ] CSRF protection, auth/authz verified, rate limiting on endpoints
- [ ] Error messages don't leak sensitive data
- If secrets exposed: STOP → security-reviewer agent → rotate secrets

---

## Testing

- Minimum 80% coverage. All three levels required: unit, integration, E2E
- TDD: write test (RED) → implement (GREEN) → refactor (IMPROVE)
- Python: pytest. TypeScript: Playwright for E2E
- Use **tdd-guide** agent proactively for new features
