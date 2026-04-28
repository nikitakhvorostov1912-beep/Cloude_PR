# Workflow — Русский Транзит (быстрая разработка)

> Цель: одна правка → проверка в 1С за <2 минуты, без ручных шагов и зависаний.

## Цикл изменения формы

```
1. Правка JSON DSL    →   build/form-<name>.json
2. /form-compile      →   src/cfe/.../Forms/.../Ext/Form.xml
3. /form-validate     →   проверка XML
4. closeWindow 1C     →   Файл → Завершить (или Stop-Process 1cv8c)
5. load-extension.ps1 →   ~30 sec, через DESIGNER
6. start-1c.ps1       →   1С запускается
7. Запустить EPF MCP_Toolkit на 6010 (вручную в 1С)
```

## Цикл изменения BSL-кода (без структуры формы)

```
1. Правка .bsl файла
2. /bsl-lint <module-dir>   →   <30s, должно быть 0 Error
3. (опционально) /1c-test-runner →  YAxUnit unit-тесты
4. closeWindow 1C
5. load-extension.ps1
6. start-1c.ps1
```

## Скрипты (все robust)

| Скрипт | Что делает | Опции |
|---|---|---|
| `scripts/start-1c.ps1` | Запуск 1С на InfoBase5 | `-Force` (перезапуск если открыта) |
| `scripts/load-extension.ps1` | Загрузка расширения через DESIGNER | `-Force` (kill 1С), `-TimeoutSec N` (default 180), `-DumpOnly`, `-NoDB` |
| `scripts/run-all-tests.ps1` | Все тесты (BDD + verification) | — |
| `scripts/run-bdd.ps1` | BDD по тегу | `-Tag smoke|critical|regression` |

Все скрипты:
- pre-flight check 1С процесса
- silent log cleanup (не падают на залоченном файле)
- timestamps в выводе
- timeout с auto-kill зависшего DESIGNER

## Pre-flight checks (автоматически в load-extension.ps1)

1. Source `src/cfe/Русский_Транзит/` существует
2. **1С закрыта** (1cv8c.exe, 1cv8s.exe) — иначе early exit с подсказкой
3. **load-result.log можно удалить** — иначе kill orphan PowerShell
4. **ConfigDumpInfo.xml удалён** — для force full reload
5. DESIGNER timeout — auto-kill после `$TimeoutSec` (default 180s)

## MCP-серверы (.mcp.json)

| Имя | Порт/Тип | Назначение |
|---|---|---|
| `bsl-context` | stdio | Справочник API платформы 1С |
| `1c-mcp-kppzht` | http://localhost:6010/mcp | InfoBase5 / Русский Транзит — запросы, BSL-код, метаданные |
| `1c-mcp-infobase5` | http://localhost:6004/mcp | Альтернативный порт (запасной) |
| `metr-test-runner` | stdio | YAxUnit запуск из Claude |

**Важно:** Windows резервирует 6003-6004 через `iphlpsvc` — `1c-mcp-kppzht` живёт на **6010**.
Запускается вручную: открыть 1С → запустить EPF `MCP_Toolkit` (Встроенный сервер, порт 6010, формат TOON, нажать «Запустить сервер»).

## Что делать если зависло / не работает

См. [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Маленькие коммиты — критично

DESIGNER грузит коммит линейно. Snapshot из 947k строк = 5+ минут. Поэтому:

- **После каждого валидного состояния** — `git add` + `git commit`
- НЕ накапливать неделями работу
- При большой пачке правок — `-TimeoutSec 300` или больше для load-extension

## Тесты в проекте

- `tests/verification/run-all-tests.bsl` — 5 тестов через MCP (метаданные, регистры, формы)
- `tests/yaxunit/` — unit тесты модулей (`Тесты_исРасчет`, `Тесты_ОперацияПоПоручительству`, и др.)
- `features/` — BDD сценарии (smoke, critical, regression теги)

Запуск:
- Verification: `mcp__1c-mcp-kppzht__execute_code` с содержимым run-all-tests.bsl
- YAxUnit: METR MCP `run_all_tests` или `mcp__metr-test-runner__run_module_tests`
- BDD: `scripts/run-bdd.ps1 -Tag smoke`

## Sync экосистемы (при подозрении на расхождения)

```powershell
# Diff (read-only, default)
powershell -File C:\CLOUDE_PR\scripts\sync-1c-ecosystem.ps1 -Mode Diff

# Раскатать toolkit → global (если в toolkit обновления)
powershell -File C:\CLOUDE_PR\scripts\sync-1c-ecosystem.ps1 -Mode Pull -Force

# Зафиксировать локальные правки в toolkit
powershell -File C:\CLOUDE_PR\scripts\sync-1c-ecosystem.ps1 -Mode Push -Force
```
