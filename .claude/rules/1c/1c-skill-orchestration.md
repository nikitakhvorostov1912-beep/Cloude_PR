# Архитектура взаимодействия 1С-скиллов

> Автоматические цепочки вызовов скиллов. Каждый скилл ОБЯЗАН следовать указанным цепочкам.
> Источник: github.com/Nikolay-Shirokov/cc-1c-skills (67 скиллов)

## Уровни системы

```
┌─────────────────────────────────────────────────────────┐
│  ОРКЕСТРАЦИЯ          1c-feature-dev (9 фаз)            │
│                       brainstorm, erp-configuration-     │
│                       advisor, gap-analysis              │
├─────────────────────────────────────────────────────────┤
│  АГЕНТЫ               1c-code-architect → решает ЧТО    │
│                       1c-code-writer → пишет КОД         │
│                       1c-code-reviewer → проверяет       │
│                       1c-code-explorer → исследует       │
│                       1c-code-simplifier → упрощает      │
├─────────────────────────────────────────────────────────┤
│  СКИЛЛЫ (67)          XML-генерация, валидация, сборка   │
│                       Работают с файлами напрямую        │
├─────────────────────────────────────────────────────────┤
│  ИНФРАСТРУКТУРА       db-list (.v8-project.json)         │
│                       MCP bsl-context (синтаксис)        │
│                       docs/1c-specs/ (35 спецификаций)   │
└─────────────────────────────────────────────────────────┘
```

## Принцип автоматического вызова

Каждый скилл при завершении ОБЯЗАН предложить следующий скилл из цепочки:
- `init` → наполнение → `validate` → `build`/`load`
- После любой модификации → соответствующий `validate`
- После `build` → предложить `db-run` для проверки

## Цепочка 1: Внешняя обработка (EPF)

```
/epf-init ──→ /epf-add-form ──→ /form-compile ──→ /form-validate
    │              │
    ├──→ /epf-bsp-init ──→ /epf-bsp-add-command
    ├──→ /template-add
    ├──→ /help-add
    │
    └──→ /epf-validate ──→ /epf-build ──→ /db-run
```

**Автоматические правила:**
- После `/epf-init` → предложить `/epf-add-form` и `/epf-bsp-init`
- После `/epf-bsp-init` → предложить `/epf-bsp-add-command`
- Перед `/epf-build` → обязательно `/epf-validate`
- После `/epf-build` → предложить `/db-run` для проверки

## Цепочка 2: Внешний отчёт (ERF)

```
/erf-init --with-skd ──→ /form-add ──→ /skd-compile ──→ /skd-validate
    │                                       │
    ├──→ /template-add                      └──→ /skd-edit ──→ /skd-validate
    ├──→ /help-add
    │
    └──→ /erf-validate ──→ /erf-build ──→ /db-run
```

**Автоматические правила:**
- `/erf-init --with-skd` создаёт каркас СКД → далее `/skd-compile`
- После `/skd-edit` → обязательно `/skd-validate`
- ERF использует скрипты EPF (shared)

## Цепочка 3: Управляемая форма

```
/form-patterns ──→ /form-add ──→ /form-compile ──→ /form-validate
                                      │                   │
                                      └──→ /form-edit ─────┘
                                                │
                                           /form-info (анализ)
```

**Автоматические правила:**
- Перед `/form-compile` → загрузить `/form-patterns` для справки
- `/form-compile` проверяет наличие метаданных формы, если нет → `/form-add`
- После `/form-compile` или `/form-edit` → обязательно `/form-validate`
- `/form-info` — безопасно вызывать в любой момент (read-only)

## Цепочка 4: Конфигурация (CF)

```
/cf-init ──→ /meta-compile ──→ /meta-edit ──→ /meta-validate
    │              │                              │
    │              └──→ /subsystem-compile ──→ /subsystem-edit
    │              └──→ /role-compile ──→ /role-validate
    │              └──→ /interface-edit ──→ /interface-validate
    │
    └──→ /cf-validate ──→ /cf-info
              │
              └──→ /db-load-xml ──→ /db-update ──→ /db-run
```

**Автоматические правила:**
- После создания объекта `/meta-compile` → предложить `/subsystem-compile` (добавить в подсистему)
- После создания объекта → предложить `/role-compile` (настроить права)
- Перед загрузкой в базу → обязательно `/cf-validate`

## Цепочка 5: Расширение (CFE)

```
/cfe-init ──→ /cfe-borrow ──→ /cfe-patch-method
                  │                   │
                  └──→ /form-edit ────┘
                            │
                  /cfe-diff (аудит) ──→ /cfe-validate
                                            │
                                  /db-load-cf ──→ /db-update
```

**Автоматические правила:**
- `/cfe-borrow` требует существующее расширение (`/cfe-init`)
- `/cfe-patch-method` требует заимствованный объект (`/cfe-borrow`)
- Перед загрузкой → `/cfe-validate`

## Цепочка 6: База данных (DB)

```
/db-list (реестр) ──→ /db-create ──→ /db-load-cf или /db-load-xml или /db-load-git
                           │                               │
                           └──→ /db-update ←───────────────┘
                                    │
                              /db-run (запуск)
                                    │
                           /db-dump-xml или /db-dump-cf (выгрузка)
```

**Автоматические правила:**
- ВСЕ db-скиллы используют единый алгоритм разрешения базы из `/db-list`:
  1. Явные параметры → используй
  2. Имя базы → поиск по id/alias/name в `.v8-project.json`
  3. Текущая ветка Git → сопоставление с `branches[]`
  4. Fallback → поле `default`
  5. Не найдено → предложить `/db-list add`
- После `/db-load-*` → обязательно предложить `/db-update`

## Цепочка 7: MXL-макеты

```
/img-grid (анализ изображения)
    │
    └──→ /mxl-compile ──→ /mxl-validate ──→ /mxl-info
              ↕
         /mxl-decompile (обратное)
```

**Автоматические правила:**
- При создании MXL по скриншоту → сначала `/img-grid`
- После `/mxl-compile` → обязательно `/mxl-validate`
- `/mxl-decompile` → редактирование JSON → `/mxl-compile`

## Цепочка 8: Веб-тестирование

```
/db-list ──→ /web-publish ──→ /web-info ──→ /web-test
                                                │
                                    /web-unpublish ──→ /web-stop
```

**Автоматические правила:**
- `/web-test` требует опубликованную базу → проверить `/web-info`
- Если не опубликована → предложить `/web-publish`

## Централизованные зависимости

### db-list — хаб для 11 скиллов

Все эти скиллы используют алгоритм разрешения базы из `db-list`:
`db-create`, `db-dump-cf`, `db-dump-xml`, `db-load-cf`, `db-load-git`, `db-load-xml`, `db-run`, `db-update`, `epf-build`, `epf-dump`, `erf-build`, `erf-dump`, `cfe-init`, `cfe-borrow`, `web-publish`

### docs/1c-specs/ — справочники для DSL-скиллов

| DSL-скилл | Спецификация |
|-----------|-------------|
| `form-compile` | `docs/1c-specs/form-dsl-spec.md` |
| `skd-compile` | `docs/1c-specs/skd-dsl-spec.md` |
| `mxl-compile` | `docs/1c-specs/mxl-dsl-spec.md` |
| `meta-compile` | `docs/1c-specs/meta-dsl-spec.md` |
| `role-compile` | `docs/1c-specs/role-dsl-spec.md` |

### Shared scripts (ERF повторно использует EPF)

| ERF-скилл | Использует скрипт из |
|-----------|---------------------|
| `erf-build` | `epf-build/scripts/` |
| `erf-dump` | `epf-dump/scripts/` |
| `erf-validate` | `epf-validate/scripts/` |

## Интеграция с агентами

### Когда агент → когда скилл

| Задача | Агент | Скиллы |
|--------|-------|--------|
| Понять существующий код | `1c-code-explorer` | `meta-info`, `form-info`, `skd-info` |
| Спроектировать архитектуру | `1c-code-architect` | `meta-compile`, `form-patterns`, `role-compile` |
| Написать код модулей | `1c-code-writer` | — (пишет BSL-код) |
| Создать XML-артефакты | — | `form-compile`, `skd-compile`, `mxl-compile`, `meta-compile` |
| Собрать и проверить | — | `*-validate`, `*-build`, `db-run`, `web-test` |
| Ревью результата | `1c-code-reviewer` | `*-validate` (автоматическая валидация) |

### Полный цикл через 1c-feature-dev

```
Phase 0-3: Анализ
  └─ агент 1c-code-explorer + info-скиллы (meta-info, form-info, cf-info)

Phase 4-5: Проектирование
  └─ агент 1c-code-architect + form-patterns, docs/1c-specs/

Phase 6: Реализация
  └─ агент 1c-code-writer (BSL-код)
  └─ скиллы: meta-compile → form-compile → skd-compile → *-validate
  └─ скиллы: epf-build или db-load-xml → db-update → db-run

Phase 7: Ревью
  └─ агент 1c-code-reviewer
  └─ скиллы: *-validate (автоматическая валидация XML)
  └─ скилл: web-test (автоматическое тестирование через браузер)

Phase 8: Итоги
  └─ результат: .epf/.erf файл или обновлённая конфигурация
```

## Безопасные скиллы (read-only, можно вызывать всегда)

`meta-info`, `form-info`, `skd-info`, `mxl-info`, `cf-info`, `role-info`, `subsystem-info`, `cfe-diff`, `web-info`, `db-list` (show), `form-patterns`, `img-grid`

## Правила для Claude

1. **Перед compile → загрузи DSL-спецификацию** из `docs/1c-specs/`
2. **После любого compile/edit → вызови validate**
3. **Перед build → вызови validate**
4. **После build → предложи db-run**
5. **db-list — обязательная зависимость** для всех операций с базой
6. **info-скиллы безопасны** — вызывай для анализа без ограничений
7. **Агенты пишут BSL-код**, скиллы генерируют XML-артефакты — не смешивай
