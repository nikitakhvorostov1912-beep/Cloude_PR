---
name: bpmn-diagram
description: "Построение диаграмм бизнес-процессов: SVG, BPMN XML, Visio из данных процессов."
---

# BPMN Diagram Builder — Построение диаграмм бизнес-процессов

Ты — эксперт по моделированию бизнес-процессов в нотации BPMN 2.0. Задача: сгенерировать профессиональные диаграммы из данных проекта и убедиться что результат соответствует эталону.

## Архитектура генерации

Проект использует 3-слойную архитектуру:

```
processes.json → ProcessToBpmnConverter → *_bpmn.json → BpmnLayout → SVG/BPMN XML/Visio
```

### Ключевые файлы

| Файл | Назначение |
|------|------------|
| `backend/app/bpmn/process_to_bpmn.py` | Конвертер процесса → BPMN JSON (элементы, потоки, lanes) |
| `backend/app/bpmn/layout.py` | Расчёт позиций элементов (X,Y координаты) |
| `backend/app/bpmn/json_to_bpmn.py` | Генерация BPMN 2.0 XML |
| `backend/app/services/bpmn_service.py` | SVG-рендерер (`_render_svg()`) |
| `backend/app/visio/direct_vsdx.py` | Генерация Visio (.vsdx) |
| `backend/convert_to_bpmn.py` | Утилита: конвертирует processes.json → *_bpmn.json |

### Форматы вывода

- **SVG** — для inline-просмотра в браузере, лёгкий, масштабируемый
- **BPMN XML** — стандартный формат, можно открыть в Camunda, draw.io, Bizagi
- **Visio (.vsdx)** — для корпоративных презентаций, редактирования

## Эталон качества

Профессиональная диаграмма BPMN должна содержать:

### Обязательные элементы (MUST HAVE)
1. **Swim-lanes** — цветные горизонтальные дорожки с вертикальными подписями участников
2. **Нумерованные задачи** — "N. Название (Исполнитель)" с маркером [+] для подпроцессов
3. **Gateways** — ромбы с подписями условий ("Товар в наличии?") и "Да"/"Нет" на ветках
4. **Start/End events** — зелёный/красный круги с подписями
5. **Cross-lane потоки** — стрелки между задачами в разных lanes
6. **Подписи потоков** — "Да"/"Нет" на развилках

### Расширенные элементы (SHOULD HAVE)
7. **Message events** — конверт-иконка внутри круга (входящие/исходящие сообщения)
8. **Timer events** — часы-иконка (ожидание)
9. **Подпроцессы** — пунктирные контейнеры с заголовком
10. **Data objects** — документы с загнутым углом
11. **Message flows** — пунктирные линии между пулами с подписями
12. **Аннотации** — пояснения к подпроцессам

### Палитра цветов lanes (7 цветов)
```python
LANE_COLORS = [
    ("#E8EDF5", "#4472C4"),  # Синий
    ("#E2EFDA", "#548235"),  # Зелёный
    ("#FFF2CC", "#BF8F00"),  # Жёлтый
    ("#F2DCDB", "#943734"),  # Красный
    ("#EDE7F6", "#7B1FA2"),  # Фиолетовый
    ("#E0F7FA", "#00796B"),  # Бирюзовый
    ("#FFF3E0", "#E65100"),  # Оранжевый
]
```

## Процедура генерации

### Шаг 1: Подготовка данных

Если данных ещё нет — создай тестовый проект и загрузи транскрипт:
```bash
curl -X POST http://localhost:8000/api/projects/ -H "Content-Type: application/json" -d '{"name": "Тест", "description": "Тестовый проект"}'
```

### Шаг 2: Конвертация процессов → BPMN JSON

```bash
cd projects/survey-automation/backend
C:/Windows/py.exe convert_to_bpmn.py {PROJECT_ID}
```

Это создаёт файлы `{pid}_bpmn.json` в `data/projects/{id}/processes/`.

### Шаг 3: Генерация SVG/BPMN/Visio через API

```bash
curl -X POST http://localhost:8000/api/projects/{PROJECT_ID}/pipeline/generate-bpmn
```

Результат: файлы `.svg`, `.bpmn`, `.vsdx` в `data/projects/{id}/bpmn/`.

### Шаг 4: Проверка

1. **SVG через API**:
   ```
   http://localhost:8000/api/projects/{PROJECT_ID}/export/svg/{PROCESS_ID}
   ```

2. **Через Preview (frontend)**:
   ```javascript
   // Навигация
   window.location.href = '/projects/{PROJECT_ID}/processes'
   // Клик на процесс → кнопка "Диаграмма"
   ```

3. **Через файловую систему**:
   ```bash
   ls data/projects/{PROJECT_ID}/bpmn/
   ```

## Чек-лист качества диаграммы

### R1: Структура
- [ ] Все участники имеют отдельные swim-lanes
- [ ] Задачи расположены в правильных lanes (по исполнителю)
- [ ] Нумерация шагов сохранена
- [ ] Start и End events на местах

### R2: Потоки
- [ ] Все задачи связаны потоками (нет "висящих" элементов)
- [ ] Gateway-ветки имеют подписи "Да"/"Нет"
- [ ] Cross-lane потоки корректны (стрелки не обрезаются)
- [ ] Нет пересекающихся линий (или минимум пересечений)

### R3: Визуальное качество
- [ ] Lanes имеют разные цвета
- [ ] Текст задач читаемый (не обрезан)
- [ ] Гейтвеи имеют подписи условий
- [ ] Тени на элементах
- [ ] Фон диаграммы светлый (#fafbfc)

### R4: Совместимость
- [ ] SVG корректно отображается в браузере
- [ ] BPMN XML валидный (можно открыть в draw.io)
- [ ] Visio файл (.vsdx) — валидный ZIP с OPC

## Исправление проблем

### Задачи не распределяются по lanes
**Причина**: Поле `lane` в элементах BPMN JSON не совпадает с `lane_id` из participants.
**Файл**: `backend/app/bpmn/process_to_bpmn.py`
**Решение**: Проверить `_build_lanes()` и `_detect_lane_from_text()`. Lane ID генерируется из `_safe_id(f"lane_{performer}")`.

### Все задачи в одной строке
**Причина**: Layout ставит все элементы в одну горизонтальную линию.
**Файл**: `backend/app/bpmn/layout.py`
**Решение**: Проверить что `elem.get("lane")` возвращает корректный lane ID, и `lane_y_offsets` содержит все дорожки.

### SVG слишком большой
**Причина**: Горизонтальный layout расширяет SVG по числу колонок.
**Файл**: `backend/app/bpmn/layout.py` (константы `HORIZONTAL_SPACING`, `TASK_WIDTH`)
**Решение**: Уменьшить spacing или добавить wrapping (перенос на новую строку после N элементов).

### Подписи обрезаются
**Файл**: `backend/app/services/bpmn_service.py` (`_wrap_text()`, `_render_svg()`)
**Решение**: Увеличить `max_chars` в `_wrap_text()` или `TASK_WIDTH` в layout.

## Быстрый тест

```bash
# 1. Старт серверов
# preview_start survey-backend  (port 8000)
# preview_start survey-frontend (port 3000)

# 2. Проверить API
curl -s http://localhost:8000/api/health

# 3. Найти проект с данными
curl -sL http://localhost:8000/api/projects/ | head -c 500

# 4. Сгенерировать BPMN (если не сгенерирован)
curl -X POST http://localhost:8000/api/projects/{ID}/pipeline/generate-bpmn

# 5. Посмотреть SVG
curl -s http://localhost:8000/api/projects/{ID}/export/svg/proc_001 -o test.svg
# Открыть через preview

# 6. Скачать все файлы
curl http://localhost:8000/api/projects/{ID}/export/zip -o all_files.zip
```

## Формат отчёта

```
BPMN Diagram Check: {дата}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Проект: {name} ({id})
Процессов: {count}

Процесс: {name}
  Элементов: {n}  Потоков: {m}  Lanes: {k}
  R1 Структура:    ✅/❌
  R2 Потоки:       ✅/❌
  R3 Визуальное:   ✅/❌
  R4 Совместимость: ✅/❌

ПРОБЛЕМЫ:
1. [R?] Описание → Рекомендация

ВЕРДИКТ: PASS / FAIL
```

Если FAIL — исправь найденные проблемы, перегенерируй, проверь снова.
