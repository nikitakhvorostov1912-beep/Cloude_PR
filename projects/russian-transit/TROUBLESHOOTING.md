# Troubleshooting — Русский Транзит

## load-extension.ps1 → FAILED / зависает

| Симптом | Причина | Решение |
|---|---|---|
| `Не удается удалить элемент load-result.log` | Залочен зависшим PowerShell | Скрипт сам убьёт orphan PS (с 28.04). Если не помогло: `Get-Process powershell \| Stop-Process -Force` (кроме твоего) |
| `Loading...` зависло на 5+ минут | 1С запущена ИЛИ огромный коммит | 1) `Get-Process 1cv8c` → если есть — закрыть; 2) `-TimeoutSec 300` для большой загрузки |
| `Source not found` | Неправильный путь | Проверь что есть `src/cfe/Русский_Транзит/Configuration.xml` |
| `Исключение XDTO при чтении файла Form.xml` | Невалидный XML | `/form-validate` → `/form-compile` пересобрать. Часто причина — `<TextColor>` сложной структурой (нужно простое `style:FormTextColor`), невалидные `<ChoiceButtonRepresentation>` |
| TIMEOUT после `$TimeoutSec` | DESIGNER реально не успел | Увеличить таймаут `-TimeoutSec 600`. ИЛИ закоммитить мелкими частями. ИЛИ удалить `ConfigDumpInfo.xml` если не удалился |

## MCP_Toolkit на 6010 не запускается

| Симптом | Причина | Решение |
|---|---|---|
| «Не удалось запустить сервер на порту 6003» | Windows резервирует 6003-6004 через `iphlpsvc` | В EPF MCP_Toolkit поменяй порт на **6010** |
| `curl localhost:6010/mcp` возвращает 406 | Это нормально (нужен Accept: text/event-stream) | Используй `python scripts/mcp1c.py` (helper в проекте) |

## Форма в 1С не обновилась после load

| Симптом | Причина | Решение |
|---|---|---|
| Открыл обработку — форма старая | 1С кеширует UI в открытой сессии | **Полный** перезапуск 1С (не просто закрытие формы) |
| Через MCP `get_metadata` нет нового реквизита | Не было `/UpdateDBCfg` | Перезапусти `load-extension.ps1` (без `-NoDB`) |

## BSL Lint жалуется на «неправильный символ —»

Длинное тире `—` (U+2014) недопустимо в BSL. Заменить на дефис `-` (U+002D).

```bash
python -c "import re; ...; text.replace('—', '-')"
```

## form-compile генерирует `version=\"\$(\$script:formatVersion)\"`

Старый баг скилла (до 28.04). Решение:
```powershell
powershell -File C:\CLOUDE_PR\scripts\sync-1c-ecosystem.ps1 -Mode Pull -Force
```
После sync — баг исправлен (upstream подставляет version правильно).

## Кириллица в аргументах bash → 1cv8.exe ломается

bash на Windows искажает кириллицу при передаче в native exe. **Никогда не вызывать `1cv8.exe` напрямую из bash**. Всегда:
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/<your>.ps1
```

## DESIGNER пишет ошибки в лог только при `/Out`

`load-extension.ps1` уже использует `/Out`. Лог в `scripts/load-result.log` — содержит ошибки из DESIGNER. Если FAILED — читай этот файл.

## После большого commit DESIGNER грузит 5+ минут

Это норма для snapshot 100k+ строк. Что делать:
- В будущем — мелкие коммиты после каждого валидного состояния
- Сейчас — `-TimeoutSec 600` (10 минут)
- Альтернатива: `-NoDB` (только конфигурация, без апдейта БД), потом отдельно UpdateDBCfg

## 1С процессы накапливаются (`tasklist | grep 1cv8`)

Зомби DESIGNER от прошлых запусков. Убить все:
```powershell
Get-Process 1cv8* | Stop-Process -Force
```

## Залоченные файлы базы (не открывается)

Если 1Cv8.1CD.lck или 1Cv8.1CL.lck остался после crash 1С:
```powershell
Stop-Process -Name 1cv8c, 1cv8s -Force -EA 0
Remove-Item C:\Users\Khvorostov\Documents\InfoBase5\*.lck -Force
```

## MCP не подцепился в Claude после правки .mcp.json

Перезапустить Claude Code — `.mcp.json` читается на старте сессии.
