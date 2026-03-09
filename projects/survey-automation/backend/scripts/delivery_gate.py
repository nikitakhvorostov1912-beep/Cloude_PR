#!/usr/bin/env python3
"""
Delivery Gate — обязательная проверка перед сдачей проекта.

Запускает полный набор проверок R1 + R2 для всех VSDX-файлов проекта.
Блокирует сдачу, пока хотя бы одна проверка не прошла.

Запуск:
    cd backend
    python scripts/delivery_gate.py data/projects/<project_id>/

    # или для конкретного VSDX:
    python scripts/delivery_gate.py data/projects/<project_id>/visio/proc_001.vsdx

Exit codes:
    0 — ВСЕ проверки PASS (файлы готовы к сдаче)
    1 — Есть нарушения (сдача заблокирована)
"""
from __future__ import annotations

import sys
import io
import pathlib

# Принудительно UTF-8 для Windows-терминала
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def main() -> int:
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/delivery_gate.py data/projects/<project_id>/")
        print("  python scripts/delivery_gate.py path/to/file.vsdx")
        return 1

    target = pathlib.Path(sys.argv[1])

    # Определяем список VSDX файлов
    if target.is_dir():
        # Ищем в подпапке visio/ или напрямую
        visio_dir = target / "visio"
        if visio_dir.is_dir():
            vsdx_files = sorted(visio_dir.glob("*.vsdx"))
        else:
            vsdx_files = sorted(target.glob("**/*.vsdx"))

        if not vsdx_files:
            print(f"\n[FAIL] Нет VSDX файлов в {target}")
            print("       Запустите генерацию Visio через API или UI")
            return 1
    elif target.is_file() and target.suffix.lower() == ".vsdx":
        vsdx_files = [target]
    else:
        print(f"[ERROR] Не найдено: {target}")
        return 1

    print("=" * 60)
    print("  DELIVERY GATE — проверка перед сдачей проекта")
    print("=" * 60)
    print(f"  Файлов для проверки: {len(vsdx_files)}")
    for f in vsdx_files:
        print(f"    • {f.name}")

    # Импортируем check_file из check_visio.py (в той же папке)
    scripts_dir = pathlib.Path(__file__).parent
    sys.path.insert(0, str(scripts_dir))

    try:
        from check_visio import check_file  # type: ignore
    except ImportError as exc:
        print(f"\n[ERROR] Не удалось импортировать check_visio: {exc}")
        print("        Убедитесь, что scripts/check_visio.py существует")
        return 1

    # Запускаем проверки
    all_passed = True
    failed_files: list[str] = []

    for vsdx_path in vsdx_files:
        ok = check_file(vsdx_path)
        if not ok:
            all_passed = False
            failed_files.append(vsdx_path.name)

    # Итоговый вердикт
    print("\n" + "=" * 60)
    if all_passed:
        print("  ✅ DELIVERY GATE: PASS")
        print(f"  Все {len(vsdx_files)} файлов прошли все проверки R1+R2")
        print("  Файлы готовы к сдаче заказчику")
        print("=" * 60)
        return 0
    else:
        print("  ❌ DELIVERY GATE: BLOCKED")
        print(f"  Нарушения найдены в {len(failed_files)} из {len(vsdx_files)} файлов:")
        for name in failed_files:
            print(f"    ✗ {name}")
        print()
        print("  Исправьте ошибки и запустите снова:")
        print("    python scripts/delivery_gate.py data/projects/<project_id>/")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
