# Скилл: E2E-тестирование UI

Создание и запуск end-to-end тестов для веб-интерфейса через Playwright.

## Инструкции

Ты — QA-инженер по автоматизации. Создай E2E тесты, симулирующие реальные действия пользователя.

### Подготовка

Убедись что Playwright установлен:
```bash
pip install playwright pytest-playwright
playwright install chromium
```

### Структура тестов

```
tests/
├── e2e/
│   ├── conftest.py              # Фикстуры: запуск сервера, браузер
│   ├── test_navigation.py       # Навигация и состояние
│   ├── test_<page>.py           # Тесты для каждой страницы
│   └── test_full_workflow.py    # Полный пользовательский путь
```

### Фикстура для веб-сервера

```python
import pytest
import subprocess
import time

@pytest.fixture(scope="session")
def web_server():
    """Запуск веб-сервера для E2E тестов."""
    # Определи команду запуска из конфига проекта
    proc = subprocess.Popen(
        ["python", "-m", "streamlit", "run", "src/web/app.py",
         "--server.port", "8502", "--server.headless", "true"],
    )
    time.sleep(5)
    yield "http://localhost:8502"
    proc.terminate()

@pytest.fixture
def page(browser, web_server):
    page = browser.new_page()
    page.goto(web_server)
    page.wait_for_load_state("networkidle")
    return page
```

### Сценарии тестирования

#### Навигация
- Все страницы загружаются без ошибок
- Навигация через сайдбар работает
- Состояние сохраняется при переходах
- Кнопки назад/вперёд браузера не ломают приложение

#### Для каждой страницы
- Страница рендерится корректно
- Интерактивные элементы кликабельны
- Формы валидируют ввод
- Ошибки отображаются пользователю

#### Полный workflow
- Пройди весь пользовательский путь от начала до конца
- Это главный критический тест

### Запуск

```bash
python -m pytest tests/e2e/ -v --headed    # С видимым браузером
python -m pytest tests/e2e/ -v             # Headless
```

## Вывод

1. Создай все тестовые файлы
2. Запусти с `--headed` для визуальной проверки
3. Сообщи pass/fail со скриншотами ошибок
4. Найди UI-проблемы обнаруженные при тестировании
