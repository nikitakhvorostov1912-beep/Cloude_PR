# MCP BSL Platform Context — Синтакс-помощник 1С для Claude

> Источник: github.com/alkoleft/mcp-bsl-platform-context (MIT)

## Что это

MCP-сервер, предоставляющий Claude доступ к справке платформы 1С:Предприятие. Аналог Синтакс-помощника — поиск функций, методов, свойств, типов данных.

## Инструменты MCP

| Tool | Назначение | Пример |
|------|-----------|--------|
| `search` | Нечёткий поиск по API платформы | `search("МассивСтрок")` |
| `info` | Детали элемента (сигнатура, описание) | `info("Массив")` |
| `getMember` | Метод/свойство конкретного типа | `getMember("Массив", "Добавить")` |
| `getMembers` | Все методы/свойства типа | `getMembers("Массив")` |
| `getConstructors` | Конструкторы объектов | `getConstructors("Запрос")` |

## Стек

- Kotlin + Spring Boot 3.5 + Spring AI 1.0
- Алгоритм Левенштейна для нечёткого поиска
- Режимы: STDIO (локально) / SSE (по сети)

## Требования

- Java 17+
- Платформа 1С 8.3.20+
- 512MB RAM минимум

## Установка

### 1. Скачать JAR
```bash
# Из GitHub Releases
wget https://github.com/alkoleft/mcp-bsl-platform-context/releases/latest/download/mcp-bsl-context.jar
```

### 2. Запуск
```bash
java -jar mcp-bsl-context.jar --platform-path "C:/Program Files/1cv8/8.3.XX.YYYY"
```

### 3. Конфигурация Claude Code
В `.claude/settings.json` или `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "bsl-context": {
      "command": "java",
      "args": [
        "-jar",
        "C:/path/to/mcp-bsl-context.jar",
        "--platform-path",
        "C:/Program Files/1cv8/8.3.XX.YYYY"
      ]
    }
  }
}
```

### 4. Конфигурация Cursor IDE
В `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "bsl-context": {
      "command": "java",
      "args": ["-jar", "path/to/mcp-bsl-context.jar", "--platform-path", "/path/to/1c"]
    }
  }
}
```

## Применение в агентах

Используется агентами `1c-code-writer` и `1c-code-reviewer` для:
- Проверки существования методов/свойств платформы
- Валидации сигнатур функций
- Поиска правильного синтаксиса
- Проверки имён переменных на коллизии с глобальным контекстом
