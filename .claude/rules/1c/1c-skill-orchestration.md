---
paths:
  - "**/*.bsl"
  - "**/*.os"
  - "**/1c-*/**"
  - "**/projects/1c*/**"
---
# Архитектура взаимодействия 1С-скиллов

> Автоматические цепочки вызовов скиллов. Каждый скилл ОБЯЗАН следовать цепочкам.

## Уровни системы

```
ОРКЕСТРАЦИЯ   1c-feature-dev (9 фаз), brainstorm, gap-analysis
АГЕНТЫ        1c-code-architect → 1c-code-writer → 1c-code-reviewer → 1c-code-explorer
СКИЛЛЫ (67)   XML-генерация, валидация, сборка (работают с файлами напрямую)
ИНФРАСТРУКТУРА db-list (.v8-project.json), MCP bsl-context, docs/1c-specs/ (35 спец.)
```

## Принцип: после завершения скилла — предложи следующий

`init` → наполнение → `validate` → `build`/`load`
После любой модификации → соответствующий `validate`
После `build` → предложить `db-run`

## Цепочки вызовов

**EPF:** `/epf-init` → `/epf-add-form` → `/form-compile` → `/form-validate` → `/epf-validate` → `/epf-build` → `/db-run`

**ERF:** `/erf-init --with-skd` → `/skd-compile` → `/skd-validate` → `/erf-validate` → `/erf-build` → `/db-run`

**Форма:** `/form-patterns` → `/form-add` → `/form-compile` → `/form-validate`

**CF:** `/cf-init` → `/meta-compile` → `/meta-edit` → `/meta-validate` → `/cf-validate` → `/db-load-xml` → `/db-update` → `/db-run`

**CFE:** `/cfe-init` → `/cfe-borrow` → `/cfe-patch-method` → `/cfe-diff` → `/cfe-validate` → `/db-load-cf` → `/db-update`

**DB:** `/db-list` → `/db-create` → `/db-load-*` → `/db-update` → `/db-run` → `/db-dump-*`

**MXL:** `/img-grid` → `/mxl-compile` → `/mxl-validate`

**Web:** `/web-publish` → `/web-info` → `/web-test` → `/web-unpublish`

## db-list — алгоритм разрешения базы (для 15 скиллов)

1. Явные параметры → используй
2. Имя базы → поиск по id/alias/name в `.v8-project.json`
3. Текущая ветка Git → сопоставление с `branches[]`
4. Fallback → поле `default`
5. Не найдено → предложить `/db-list add`

## DSL-спецификации (загружай перед compile)

| Скилл | Спецификация |
|-------|-------------|
| `form-compile` | `docs/1c-specs/form-dsl-spec.md` |
| `skd-compile` | `docs/1c-specs/skd-dsl-spec.md` |
| `mxl-compile` | `docs/1c-specs/mxl-dsl-spec.md` |
| `meta-compile` | `docs/1c-specs/meta-dsl-spec.md` |
| `role-compile` | `docs/1c-specs/role-dsl-spec.md` |

## Агент vs Скилл

| Задача | Агент | Скиллы |
|--------|-------|--------|
| Понять код | `1c-code-explorer` | `meta-info`, `form-info`, `skd-info` |
| Спроектировать | `1c-code-architect` | `meta-compile`, `form-patterns`, `role-compile` |
| Написать BSL | `1c-code-writer` | — |
| XML-артефакты | — | `form-compile`, `skd-compile`, `mxl-compile` |
| Собрать/проверить | — | `*-validate`, `*-build`, `db-run` |
| Ревью | `1c-code-reviewer` | `*-validate` |

## Безопасные скиллы (read-only, вызывай без ограничений)

`meta-info`, `form-info`, `skd-info`, `mxl-info`, `cf-info`, `role-info`, `subsystem-info`, `cfe-diff`, `web-info`, `db-list`, `form-patterns`, `img-grid`

## Правила для Claude

1. Перед compile → загрузи DSL-спецификацию из `docs/1c-specs/`
2. После любого compile/edit → вызови validate
3. Перед build → вызови validate
4. После build → предложи db-run
5. Агенты пишут BSL-код, скиллы генерируют XML — не смешивай
