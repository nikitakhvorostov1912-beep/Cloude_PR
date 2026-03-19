# Перенос Obsidian vault через GitHub

Привет Клод на другом ПК! Вот что нужно сделать.

---

## Задача

Перенести Obsidian vault с этого ПК на другой через GitHub, чтобы потом они синхронизировались автоматически.

---

## ШАГ 1 — Установить плагин Obsidian Git

1. Открыть Obsidian
2. `Settings` → `Community plugins` → нажать **Turn on community plugins**
3. Нажать **Browse** → найти **"Obsidian Git"** → **Install** → **Enable**

---

## ШАГ 2 — Узнать путь к vault

В Obsidian: `Settings` → `About` → поле **Vault path** — скопируй этот путь.

---

## ШАГ 3 — Создать репозиторий на GitHub

1. Перейди на [github.com](https://github.com) → **New repository**
2. Имя: `obsidian-vault` (или любое)
3. Тип: **Private**
4. **НЕ** ставить галочку "Initialize with README"
5. Нажать **Create repository**
6. Скопировать URL репозитория (вида `https://github.com/твой-аккаунт/obsidian-vault.git`)

---

## ШАГ 4 — Залить vault на GitHub

Открой терминал (PowerShell или cmd), перейди в папку vault:

```bash
cd "ПУТЬ_К_VAULT"  # вставь путь из шага 2
```

Затем выполни по очереди:

```bash
git init
git add .
git commit -m "initial vault upload"
git branch -M main
git remote add origin https://github.com/ТВОЙ_АККАУНТ/obsidian-vault.git
git push -u origin main
```

> Если git попросит логин — войди через браузер или используй токен GitHub.
> Создать токен: GitHub → Settings → Developer settings → Personal access tokens → Generate new token (repo scope).

---

## ШАГ 5 — Настроить Obsidian Git (автосинхронизация)

В Obsidian: `Settings` → `Obsidian Git`:

| Настройка | Значение |
|-----------|---------|
| Auto pull interval (minutes) | 5 |
| Auto push interval (minutes) | 5 |
| Pull on startup | включить |

---

## На ДРУГОМ ПК (этот шаг выполнить там)

```bash
git clone https://github.com/ТВОЙ_АККАУНТ/obsidian-vault.git
```

Затем в Obsidian: **Open folder as vault** → выбрать склонированную папку.
Установить плагин Obsidian Git (шаг 1) и настроить (шаг 5).

---

## Готово

После этого оба ПК будут синхронизироваться через GitHub автоматически каждые 5 минут.
