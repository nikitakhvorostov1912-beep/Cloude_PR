---
name: ui-ux-review
description: "Проверка UI/UX: каждый элемент работает, навигация, отзывчивость, тёмная тема."
---

# UI/UX Review — Проверка интерфейса

Ты — UX-эксперт. Проведи детальную проверку пользовательского интерфейса Survey Automation.

## Окружение

- **Frontend**: `preview_start` с именем `survey-frontend` (порт 3000)
- **Backend**: `preview_start` с именем `survey-backend` (порт 8000) — нужен для данных
- **Если preview_screenshot не работает**: используй `preview_snapshot` (accessibility tree) — он всегда работает

## Методология

### Двухуровневая проверка:

**Уровень 1 — Анализ кода** (быстро, надёжно):
Используй Task agent (Explore) для чтения ВСЕХ page.tsx файлов:
```
projects/survey-automation/frontend/src/app/page.tsx
projects/survey-automation/frontend/src/app/projects/[id]/page.tsx
projects/survey-automation/frontend/src/app/projects/[id]/upload/page.tsx
projects/survey-automation/frontend/src/app/projects/[id]/transcripts/page.tsx
projects/survey-automation/frontend/src/app/projects/[id]/processes/page.tsx
projects/survey-automation/frontend/src/app/projects/[id]/gaps/page.tsx
projects/survey-automation/frontend/src/app/projects/[id]/requirements/page.tsx
projects/survey-automation/frontend/src/app/projects/[id]/files/page.tsx
```
Проверь в каждом файле:
- Все тексты на русском
- Все кнопки имеют onClick/href обработчики
- Есть loading, error, empty состояния
- Нет TODO, placeholder, Lorem ipsum

**Уровень 2 — Визуальная проверка** (через Preview):
1. Запусти серверы через `preview_start`
2. Сделай `preview_screenshot` главной страницы
3. Перейди на страницу проекта (используй `preview_eval` для навигации)
4. Проверь каждую подстраницу через скриншот или snapshot
5. Проверь мобильную адаптацию через `preview_resize` с preset `mobile`

### Навигация через preview_eval:
```javascript
window.location.href = '/projects/{id}'           // обзор проекта
window.location.href = '/projects/{id}/upload'     // загрузка
window.location.href = '/projects/{id}/transcripts'// транскрипции
window.location.href = '/projects/{id}/processes'  // процессы
window.location.href = '/projects/{id}/gaps'       // GAP-анализ
window.location.href = '/projects/{id}/requirements'// требования
window.location.href = '/projects/{id}/files'      // файлы
```

Чтобы найти ID проекта с данными:
```bash
curl -sL "http://localhost:8000/api/projects/" | head -c 500
```

## Чек-лист по страницам

### Главная (/)
- [ ] Список проектов отображается (или empty state если нет проектов)
- [ ] Кнопка "Создать проект" работает
- [ ] Карточки проектов кликабельны (onClick → router.push)
- [ ] Статус-бейджи: Новый, В работе, Завершён, Ошибка

### Проект (/projects/[id])
- [ ] Прогресс пайплайна отображается
- [ ] 6 этапов с кнопками "Запустить"
- [ ] Прогресс-бар общий
- [ ] Сайдбар с навигацией

### Загрузка (/projects/[id]/upload)
- [ ] 3 вкладки: Аудио файлы, Загрузить транскрипт, Указать папку
- [ ] Drag-drop зона с визуальным feedback
- [ ] Список загруженных файлов (или empty state)

### Транскрипции (/projects/[id]/transcripts)
- [ ] Список транскрипций (или empty state)
- [ ] 2 вкладки: Диалог / Полный текст
- [ ] Статистика по спикерам

### Процессы (/projects/[id]/processes)
- [ ] Accordion раскрывается/сворачивается
- [ ] Кнопки "Диаграмма" и "Редактировать"
- [ ] Редактирование: Название, Отдел, Описание + Сохранить/Отмена
- [ ] Шаги процесса (таблица), Решения (Да/Нет), Проблемные зоны

### GAP-анализ (/projects/[id]/gaps)
- [ ] Выбор конфигурации 1С (dropdown)
- [ ] Кнопка "Запустить GAP-анализ"
- [ ] Summary карточки: Всего GAP, Критичные, По типам
- [ ] Таблица с данными

### Требования (/projects/[id]/requirements)
- [ ] Фильтры: Тип (FR/NFR/IR/DR/SR) + Приоритет (Must/Should/Could/Won't)
- [ ] Кнопка "Сбросить" при активных фильтрах
- [ ] Кнопки экспорта Excel / Word
- [ ] Таблица ID | Тип | Описание | Приоритет | Статус

### Файлы (/projects/[id]/files)
- [ ] Группировка: Visio, BPMN, Документы, Таблицы
- [ ] Кнопки скачивания на каждом файле
- [ ] "Скачать всё (ZIP)"

## Общие проверки

### Тёмная тема
- [ ] Все компоненты на тёмном фоне
- [ ] Нет белых/светлых "вспышек"
- [ ] Текст читаемый (контраст)

### Тексты
- [ ] ВСЕ тексты на русском
- [ ] Нет "Lorem ipsum", "placeholder", "TODO"
- [ ] Ошибки на русском ("Ошибка загрузки", "Ошибка запроса")

### Отзывчивость
- [ ] Мобильный вид (375x812) — контент адаптирован
- [ ] Сайдбар скрывается на мобильном
- [ ] Нет горизонтального скролла

### Консоль
- [ ] `preview_console_logs` level=error — 0 ошибок

## Формат отчёта

```
UI/UX Review: {дата}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
СТРАНИЦЫ:
  /                      ✅/❌
  /projects/[id]         ✅/❌
  /projects/[id]/upload  ✅/❌
  /projects/[id]/transcripts ✅/❌
  /projects/[id]/processes   ✅/❌
  /projects/[id]/gaps        ✅/❌
  /projects/[id]/requirements ✅/❌
  /projects/[id]/files       ✅/❌

ОБЩИЕ:
  Тёмная тема      ✅/❌
  Русский язык     ✅/❌
  Мобильная версия ✅/❌
  Console errors   ✅/❌

ПРОБЛЕМЫ: {count} критичных, {count} важных, {count} мелочей
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Вердикт: PASS / FAIL
```

Для каждой проблемы укажи: Страница, Описание, Серьёзность, Рекомендация.
Затем ИСПРАВЬ все найденные проблемы самостоятельно.
