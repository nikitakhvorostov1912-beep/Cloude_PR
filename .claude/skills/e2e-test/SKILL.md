---
name: e2e-test
description: "Генерация и запуск E2E тестов (Playwright) для проверки UI."
---

# E2E Test — End-to-End тестирование

Создай или запусти E2E тесты для Survey Automation через Playwright.

## Структура тестов

Путь: `projects/survey-automation/frontend/e2e/`

### Сценарии для покрытия

1. **project-crud.spec.ts** — CRUD проектов
   - Создание проекта с названием
   - Просмотр списка проектов
   - Переход в проект
   - Удаление проекта с подтверждением

2. **file-upload.spec.ts** — Загрузка файлов
   - Загрузка аудио через drag-drop
   - Загрузка транскрипта (.txt, .json)
   - Указание пути к папке
   - Отображение загруженных файлов

3. **pipeline-flow.spec.ts** — Пайплайн
   - Запуск стадии транскрипции
   - Прогресс-бар обновляется
   - Переход между стадиями
   - Обработка ошибок стадии

4. **process-editor.spec.ts** — Редактор процессов
   - Просмотр списка процессов
   - Раскрытие accordion
   - Редактирование текстовых полей
   - Сохранение изменений

5. **export-files.spec.ts** — Экспорт
   - Скачивание Visio
   - Скачивание Word
   - Скачивание Excel
   - Скачивание ZIP

6. **navigation.spec.ts** — Навигация
   - Сайдбар работает
   - Все ссылки корректны
   - Тёмная тема отображается

## Шаблон теста

```typescript
import { test, expect } from "@playwright/test";

test.describe("Название группы", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("http://localhost:3000");
  });

  test("описание на русском", async ({ page }) => {
    // Arrange
    // Act
    // Assert
    await expect(page.locator("...")).toBeVisible();
  });
});
```

## Запуск

```bash
cd projects/survey-automation/frontend
npx playwright test
npx playwright test --ui  # интерактивный режим
npx playwright test e2e/navigation.spec.ts  # один файл
```

## Правила
- Тесты должны быть независимыми
- Использовать тестовые данные из backend/test_data/
- Ожидания (assertions) на русском тексте в UI
- Таймауты: 30с для операций пайплайна, 5с для навигации
