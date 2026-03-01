---
name: word-generation
description: "Генерация профессиональных Word документов через python-docx."
command: /gen-word
---

# Word Generation — Генерация Word документов

Создавай профессиональные Word (.docx) документы для проекта обследования.

## Библиотека: python-docx

### Шаблон документа

```python
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE

doc = Document()

# Настройка страницы (A4, поля 2см)
section = doc.sections[0]
section.page_width = Cm(21)
section.page_height = Cm(29.7)
section.top_margin = Cm(2)
section.bottom_margin = Cm(2)
section.left_margin = Cm(2)
section.right_margin = Cm(2)

# Стили
style = doc.styles['Heading 1']
style.font.size = Pt(16)
style.font.bold = True
style.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

# Таблица с форматированием
table = doc.add_table(rows=1, cols=3)
table.style = 'Table Grid'
table.alignment = WD_TABLE_ALIGNMENT.CENTER

# Нумерация страниц в футере
footer = section.footer
footer.paragraphs[0].text = "Стр. "
# (добавить поле PAGE через XML)
```

### Типы документов

1. **Описание бизнес-процессов** — карточки + текстовые описания
2. **Лист требований** — таблица с FR/NFR/IR, MoSCoW
3. **Отчёт о GAP-анализе** — таблицы, цветовая маркировка
4. **Техническое задание** — структура по ГОСТ 34.602-89

### Правила

- Шрифт: Times New Roman для документов, Calibri для таблиц
- Размер: 12pt основной текст, 14pt заголовки
- Интервал: 1.5 для текста, 1.0 для таблиц
- Язык: русский
- Нумерация: автоматическая
- Формат даты: "1 марта 2026 г."
