---
name: pptx-generation
description: "Генерация презентаций PowerPoint через python-pptx."
---

# PPTX Generation — Генерация презентаций

Создавай профессиональные PowerPoint (.pptx) презентации для руководства и заказчиков.

## Библиотека: python-pptx

### Шаблон

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Cm, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.chart import XL_CHART_TYPE

prs = Presentation()
prs.slide_width = Cm(33.867)  # 16:9
prs.slide_height = Cm(19.05)

# Титульный слайд
slide = prs.slides.add_slide(prs.slide_layouts[0])
slide.shapes.title.text = "Результаты обследования"
slide.placeholders[1].text = "Компания / Дата"

# Слайд с контентом
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Ключевые процессы"
body = slide.placeholders[1]
tf = body.text_frame
tf.text = "Процесс 1"
p = tf.add_paragraph()
p.text = "Процесс 2"

# Таблица на слайде
rows, cols = 5, 4
table_shape = slide.shapes.add_table(rows, cols, Cm(2), Cm(5), Cm(30), Cm(12))
table = table_shape.table

# Диаграмма
chart_data = CategoryChartData()
chart_data.categories = ["Продажи", "Склад", "Бухгалтерия"]
chart_data.add_series("Покрытие %", (85, 60, 90))
chart = slide.shapes.add_chart(
    XL_CHART_TYPE.BAR_CLUSTERED, Cm(2), Cm(5), Cm(28), Cm(12), chart_data
).chart

prs.save("presentation.pptx")
```

### Структура презентации обследования

1. Титульный слайд
2. Содержание
3. О предприятии (краткая сводка)
4. Выявленные процессы (список по отделам)
5. Ключевые проблемы (pain points)
6. GAP-анализ (таблица + диаграмма покрытия)
7. Рекомендации по конфигурации 1С
8. Лист требований (сводка по приоритетам)
9. План внедрения (высокоуровневый)
10. Следующие шаги

### Правила

- Формат 16:9
- Минимум текста, максимум визуализации
- Тёмная цветовая схема (фон #1a1a2e, текст #ffffff)
- Шрифт: Calibri
- Русский язык
