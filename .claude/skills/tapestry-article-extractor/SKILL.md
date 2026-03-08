---
name: tapestry-article-extractor
description: Extract clean article content from URLs (blog posts, articles, tutorials) and save as readable text. Use when user wants to download, extract, or save an article/blog post from a URL without ads, navigation, or clutter. Also interlinks related documents into knowledge networks.
allowed-tools: Bash,Write,Read,WebFetch
---

# Tapestry Article Extractor

Извлекает чистый текст статей из URL (блоги, новости, туториалы), убирая рекламу, навигацию, мусор. Связывает документы в сети знаний.

> Источник: https://github.com/michalparkola/tapestry-skills

## Когда использовать

- Пользователь дал URL статьи и хочет текст
- "Скачай эту статью", "Извлеки контент из [URL]"
- "Сохрани этот блог-пост как текст"
- Нужен чистый текст без отвлечений
- Связывание нескольких документов в базу знаний

## Инструменты извлечения (приоритет)

### 1. WebFetch (встроенный, рекомендуется)
```
Использовать WebFetch tool с промптом "Extract the full article text"
```

### 2. reader (Mozilla Readability)
```bash
# Установка: npm install -g @mozilla/readability-cli
reader "URL" > article.txt
```

### 3. trafilatura (Python, хорош для блогов)
```bash
# Установка: pip install trafilatura
trafilatura --URL "URL" --output-format txt --no-comments > article.txt
```

### 4. Fallback (curl + парсинг)
```bash
curl -s "URL" | python3 -c "
from html.parser import HTMLParser
import sys
class Ext(HTMLParser):
    def __init__(self):
        super().__init__()
        self.content, self.skip = [], {'script','style','nav','header','footer','aside'}
        self.ok = False
    def handle_starttag(self, tag, a):
        if tag not in self.skip and tag in {'p','article','main','h1','h2','h3'}:
            self.ok = True
    def handle_data(self, d):
        if self.ok and d.strip(): self.content.append(d.strip())
    def result(self): return '\n\n'.join(self.content)
p = Ext(); p.feed(sys.stdin.read()); print(p.result())
"
```

## Рабочий процесс

1. Определить лучший инструмент (WebFetch → reader → trafilatura → fallback)
2. Извлечь контент
3. Извлечь заголовок для имени файла
4. Очистить имя файла от спецсимволов
5. Сохранить в файл
6. Показать превью (первые 10-15 строк)

## Формат вывода

```
Извлечено: [Заголовок статьи]
Сохранено: [имя_файла.txt]

Превью:
[первые 10 строк]
```

## Что удаляется

- Навигация, меню
- Реклама
- Формы подписки
- Сайдбары, related articles
- Комментарии
- Кнопки соцсетей
- Cookie-баннеры

## Связывание документов (Tapestry)

При извлечении нескольких статей:
1. Сохранить каждую в отдельный файл
2. Создать `index.md` со ссылками между документами
3. Выявить общие темы и создать теги
4. Построить граф связей

```markdown
# Индекс знаний

## Статьи
- [Статья 1](article1.txt) — теги: #ai #automation
- [Статья 2](article2.txt) — теги: #ai #1c

## Связи
- Статья 1 ↔ Статья 2: общая тема AI-автоматизация
```

## Обработка ошибок

- **Paywall/авторизация** — сообщить что нужна подписка
- **Пустой контент** — попробовать альтернативный инструмент
- **Спецсимволы в заголовке** — заменить на `-`
- **Слишком длинное имя** — обрезать до 80 символов
