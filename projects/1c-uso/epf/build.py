# -*- coding: utf-8 -*-
"""
Сборка внешней обработки МетаданныеУСО.epf
─────────────────────────────────────────
Способ 1 (автоматический): указать путь к базе 1С → скрипт скомпилирует .epf
Способ 2 (ручной): открыть Designer → File → Load from files → указать папку src/
"""

import subprocess
import os
import sys
import glob

# ── Настройки ────────────────────────────────────────────────────────────────

SRC_DIR    = os.path.join(os.path.dirname(__file__), "src")
OUTPUT_EPF = os.path.join(os.path.dirname(__file__), "МетаданныеУСО.epf")

# Путь к 1cv8c.exe — обычно в C:\Program Files\1cv8\<версия>\bin\
# Скрипт ищет автоматически, но можно указать вручную:
PATH_1CV8C = None  # например: r"C:\Program Files\1cv8\8.3.22.1750\bin\1cv8c.exe"

# Путь к файловой базе 1С (нужна для компиляции)
# Укажи путь к любой файловой базе, к которой есть доступ:
PATH_INFOBASE = None  # например: r"C:\bases\my_base"

# ── Поиск 1cv8c.exe ──────────────────────────────────────────────────────────

def find_1cv8c():
    if PATH_1CV8C and os.path.exists(PATH_1CV8C):
        return PATH_1CV8C
    # Автопоиск в Program Files
    for pattern in [
        r"C:\Program Files\1cv8\*\bin\1cv8c.exe",
        r"C:\Program Files (x86)\1cv8\*\bin\1cv8c.exe",
    ]:
        matches = glob.glob(pattern)
        if matches:
            # Берём последнюю (самую свежую по имени)
            return sorted(matches)[-1]
    return None

# ── Компиляция ───────────────────────────────────────────────────────────────

def build():
    exe = find_1cv8c()
    if not exe:
        print("ОШИБКА: 1cv8c.exe не найден.")
        print("Укажи PATH_1CV8C в этом скрипте или используй ручной способ.")
        manual_instructions()
        return

    if not PATH_INFOBASE:
        print("ОШИБКА: PATH_INFOBASE не указан.")
        print("Укажи путь к любой файловой базе 1С в переменной PATH_INFOBASE.")
        manual_instructions()
        return

    print(f"1cv8c.exe: {exe}")
    print(f"Источник:  {SRC_DIR}")
    print(f"Результат: {OUTPUT_EPF}")
    print()

    cmd = [
        exe, "DESIGNER",
        "/F", PATH_INFOBASE,
        "/LoadExternalDataProcessorFromFiles", SRC_DIR, OUTPUT_EPF,
        "/DisableStartupDialogs",
    ]

    print("Компилирую...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode == 0 and os.path.exists(OUTPUT_EPF):
        size = os.path.getsize(OUTPUT_EPF)
        print(f"OK: {OUTPUT_EPF}  ({size // 1024} КБ)")
        print("Открой файл в 1С: Файл → Открыть → МетаданныеУСО.epf")
    else:
        print(f"ОШИБКА (код {result.returncode}):")
        print(result.stdout[-2000:] if result.stdout else "нет вывода")
        print(result.stderr[-1000:] if result.stderr else "")
        manual_instructions()

# ── Ручные инструкции ────────────────────────────────────────────────────────

def manual_instructions():
    print()
    print("─" * 60)
    print("РУЧНОЙ СПОСОБ (через Конфигуратор):")
    print("─" * 60)
    print("1. Открыть 1С в режиме Конфигуратора (не 1С:Предприятие)")
    print("   Пуск → 1С:Предприятие → выбрать базу → Конфигуратор")
    print()
    print("2. В Конфигураторе:")
    print("   Файл → Загрузить внешнюю обработку из файлов...")
    print(f"   Указать папку: {SRC_DIR}")
    print(f"   Сохранить как: {OUTPUT_EPF}")
    print()
    print("3. Открыть обработку в 1С:Предприятии:")
    print("   Файл → Открыть → МетаданныеУСО.epf")
    print("   Нажать кнопку 'Выполнить'")
    print()
    print("─" * 60)
    print("АЛЬТЕРНАТИВА: вставить код вручную")
    print("─" * 60)
    print("1. Конфигуратор → Файл → Новый → Внешняя обработка")
    print("2. Добавить реквизит: Результат (Строка, неограниченная длина)")
    print("3. Добавить форму → скопировать Module.bsl в модуль формы")
    print("4. Скопировать ObjectModule.bsl в модуль объекта")
    print("5. Добавить на форму: поле 'РезультатПоле' (привязать к Результат)")
    print("6. Добавить кнопки: 'Выполнить', 'Сохранить в файл'")
    print("7. Файл → Сохранить как → МетаданныеУСО.epf")
    print()
    print(f"Исходники в: {SRC_DIR}")

# ── Точка входа ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # py build.py C:\bases\my_base
        PATH_INFOBASE = sys.argv[1]

    build()
