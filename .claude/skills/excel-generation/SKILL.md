---
name: excel-generation
description: "Генерация Excel с фильтрами, формулами, условным форматированием через openpyxl."
---

# Excel Generation — Генерация Excel документов

Создавай профессиональные Excel (.xlsx) документы с фильтрами и форматированием.

## Библиотека: openpyxl

### Шаблон

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule

wb = Workbook()
ws = wb.active
ws.title = "Требования"

# Стили заголовков
header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="2B5797", end_color="2B5797", fill_type="solid")

# Заморозить шапку
ws.freeze_panes = "A2"

# AutoFilter
ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"

# Ширина столбцов
for col in range(1, ws.max_column + 1):
    max_len = max(len(str(cell.value or "")) for cell in ws[get_column_letter(col)])
    ws.column_dimensions[get_column_letter(col)].width = min(max_len + 2, 50)

# Условное форматирование (MoSCoW)
red_fill = PatternFill(start_color="FF6B6B", end_color="FF6B6B", fill_type="solid")
orange_fill = PatternFill(start_color="FFB347", end_color="FFB347", fill_type="solid")
yellow_fill = PatternFill(start_color="FFE066", end_color="FFE066", fill_type="solid")
gray_fill = PatternFill(start_color="C0C0C0", end_color="C0C0C0", fill_type="solid")

ws.conditional_formatting.add("D2:D100",
    CellIsRule(operator="equal", formula=['"Must"'], fill=red_fill))
ws.conditional_formatting.add("D2:D100",
    CellIsRule(operator="equal", formula=['"Should"'], fill=orange_fill))

# Сводная таблица на отдельном листе
ws_summary = wb.create_sheet("Сводка")

wb.save("output.xlsx")
```

### Типы документов

1. **Лист требований** — столбцы: №, ID, Описание, Тип, Приоритет, Модуль, Категория, Статус
2. **GAP-анализ** — столбцы: №, Модуль, Процесс, Покрытие%, GAP, Трудозатраты, Рекомендация
3. **Сводка процессов** — столбцы: №, Процесс, Отдел, Участники, Шагов, Проблем

### Правила

- Всегда AutoFilter на заголовках
- Всегда freeze первой строки
- Условное форматирование для статусов и приоритетов
- Сводный лист с подсчётами
- Русские названия листов и заголовков
- Ширина столбцов по содержимому
