---
name: ios-simulator
description: "iOS Simulator: сборка, тестирование и автоматизация iOS-приложений через simctl. Используй когда нужно собрать Xcode проект, запустить на симуляторе, протестировать UI, управлять разрешениями или проверить push-уведомления."
allowed-tools: Bash,Read,Write,Edit
---

# iOS Simulator — Автоматизация iOS разработки

Полная автоматизация работы с iOS Simulator через `xcrun simctl` и Python-скрипты.

> Источник: https://github.com/conorluddy/ios-simulator-skill

## Когда использовать

- Сборка и тестирование Xcode проектов
- Навигация и взаимодействие с UI на симуляторе
- Accessibility аудит (WCAG)
- Управление разрешениями приложений
- Push-уведомления на симуляторе
- Visual diff / скриншот-тестирование

## Когда НЕ использовать

- Android разработка → не поддерживается
- Web-тестирование → используй `e2e-runner` или Playwright
- Просто собрать .ipa → используй Xcode напрямую

## Требования

- macOS с установленным Xcode
- `xcrun simctl` доступен в PATH
- Python 3.8+

## 21 скрипт по категориям

### Build & Development
| Скрипт | Назначение |
|--------|-----------|
| `build_and_test.py` | Компиляция Xcode проектов, запуск тестов, парсинг результатов |
| `log_monitor.py` | Стриминг логов в реальном времени с фильтрацией по severity |

### Navigation & Interaction
| Скрипт | Назначение |
|--------|-----------|
| `screen_mapper.py` | Маппинг UI элементов и интерактивных компонентов |
| `navigator.py` | Поиск и взаимодействие с элементами (семантический матчинг) |
| `gesture.py` | Свайпы, скроллы, пинчи, long-press |
| `keyboard.py` | Ввод текста и аппаратные кнопки |
| `app_launcher.py` | Жизненный цикл приложения (launch, terminate, install, deep linking) |

### Testing & Analysis
| Скрипт | Назначение |
|--------|-----------|
| `accessibility_audit.py` | WCAG compliance evaluation |
| `visual_diff.py` | Сравнение скриншотов для визуальных изменений |
| `test_recorder.py` | Документирование выполнения тестов |
| `app_state_capture.py` | Снимки состояния для отладки |
| `sim_health_check.sh` | Проверка окружения |

### Advanced Testing & Permissions
| Скрипт | Назначение |
|--------|-----------|
| `clipboard.py` | Управление буфером обмена |
| `status_bar.py` | Переопределение status bar |
| `push_notification.py` | Симуляция push-уведомлений |
| `privacy_manager.py` | 13+ разрешений приложения |

### Device Lifecycle
| Скрипт | Назначение |
|--------|-----------|
| `simctl_boot.py` | Загрузка симулятора |
| `simctl_shutdown.py` | Выключение симулятора |
| `simctl_create.py` | Создание нового симулятора |
| `simctl_delete.py` | Удаление симулятора |
| `simctl_erase.py` | Сброс к заводским |

## Базовые команды simctl

```bash
# Список доступных симуляторов
xcrun simctl list devices

# Загрузить симулятор
xcrun simctl boot <UDID>

# Установить приложение
xcrun simctl install booted /path/to/app.app

# Запустить приложение
xcrun simctl launch booted com.example.app

# Скриншот
xcrun simctl io booted screenshot /path/to/screenshot.png

# Push notification
xcrun simctl push booted com.example.app notification.json

# Управление разрешениями
xcrun simctl privacy booted grant photos com.example.app

# Открыть URL (deep linking)
xcrun simctl openurl booted "myapp://screen/123"
```

## Workflow

1. **Проверка окружения**: `sim_health_check.sh`
2. **Создание/загрузка симулятора**: `simctl_create.py` → `simctl_boot.py`
3. **Сборка**: `build_and_test.py`
4. **Установка и запуск**: `app_launcher.py`
5. **Тестирование**: `navigator.py` + `gesture.py` + `keyboard.py`
6. **Анализ**: `accessibility_audit.py` + `visual_diff.py`
7. **Отчёт**: скриншоты, логи, результаты тестов
