"""Модуль генерации Visio (.vsdx) из BPMN JSON.

Предоставляет функцию ``generate_visio`` для конвертации
BPMN JSON-описания в редактируемый Visio-файл.

Использует DirectVsdxGenerator — прямую сборку XML/ZIP
на базе шаблона из библиотеки ``vsdx``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .direct_vsdx import DirectVsdxGenerator, generate_visio_direct

logger = logging.getLogger(__name__)


def generate_visio(bpmn_json: dict[str, Any], output_path: Path) -> Path:
    """Генерирует Visio-файл (.vsdx) из BPMN JSON.

    Автоматически загружает данные процесса (шаги, системы)
    из файла processes.json рядом с BPMN JSON.

    Args:
        bpmn_json: Словарь с описанием BPMN-процесса.
        output_path: Путь для сохранения .vsdx файла.

    Returns:
        Путь к созданному .vsdx файлу.
    """
    # Пытаемся найти доп. данные процесса (шаги с системами)
    process_data = _find_process_data(bpmn_json, output_path)
    return generate_visio_direct(bpmn_json, output_path, process_data)


def _find_process_data(
    bpmn_json: dict[str, Any],
    output_path: Path,
) -> dict[str, Any] | None:
    """Ищет данные процесса (steps, systems) в processes.json."""
    proc_id = bpmn_json.get("process_id", "")
    proc_name = bpmn_json.get("process_name", "")

    # output_path: data/projects/{proj_id}/visio/{proc_id}.vsdx
    # processes.json: data/projects/{proj_id}/processes/processes.json
    try:
        project_dir = output_path.parent.parent
        processes_file = project_dir / "processes" / "processes.json"
        if not processes_file.is_file():
            return None

        with open(processes_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for proc in data.get("processes", []):
            if proc.get("id") == proc_id or proc.get("name") == proc_name:
                return proc
    except Exception as exc:
        logger.debug("Не удалось загрузить процесс: %s", exc)
    return None


__all__ = ["generate_visio", "DirectVsdxGenerator"]
