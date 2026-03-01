"""Сервис генерации BPMN и SVG."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from app.bpmn.json_to_bpmn import BpmnConverter
from app.bpmn.layout import BpmnLayout
from app.config import ProjectDir, get_config, get_project_dir
from app.exceptions import ExportError, NotFoundError, ProcessingError

logger = logging.getLogger(__name__)


class BPMNService:
    """Генерация BPMN XML и SVG-диаграмм из описания бизнес-процессов.

    Координирует конвертацию JSON-процессов в BPMN 2.0 XML
    с автоматической компоновкой и SVG-рендерингом.

    Args:
        converter: Экземпляр BpmnConverter. Если не задан, создаётся.
        layout_engine: Экземпляр BpmnLayout. Если не задан, создаётся.
    """

    def __init__(
        self,
        converter: BpmnConverter | None = None,
        layout_engine: BpmnLayout | None = None,
    ) -> None:
        self._converter = converter or BpmnConverter()
        self._layout = layout_engine or BpmnLayout()

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    async def generate_bpmn(
        self,
        project_id: str,
        process_ids: list[str] | None = None,
        on_progress: Callable[[float, float, str], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Генерирует BPMN XML и SVG для процессов проекта.

        Args:
            project_id: Идентификатор проекта.
            process_ids: Список ID процессов. Если None, генерируются все.
            on_progress: Колбэк прогресса (current, total, message).

        Returns:
            Список словарей с информацией о сгенерированных файлах:
            ``[{"process_id": ..., "bpmn_path": ..., "svg_path": ...}, ...]``

        Raises:
            NotFoundError: Если проект или процессы не найдены.
            ProcessingError: При ошибке генерации.
        """
        project_dir = self._ensure_project_exists(project_id)
        bpmn_jsons = self._load_bpmn_jsons(project_dir, process_ids)

        if not bpmn_jsons:
            raise NotFoundError(
                "BPMN-описания процессов не найдены. "
                "Сначала выполните извлечение процессов.",
                detail={"project_id": project_id},
            )

        if on_progress:
            on_progress(0, 100, "Генерация BPMN-диаграмм...")

        project_dir.ensure_dirs()
        results: list[dict[str, Any]] = []
        total = len(bpmn_jsons)

        for idx, (pid, bpmn_json) in enumerate(bpmn_jsons.items()):
            if on_progress:
                pct = 10 + (idx / total) * 80
                on_progress(pct, 100, f"Генерация BPMN: {pid}...")

            try:
                result = self._generate_single(project_dir, pid, bpmn_json)
                results.append(result)
            except (ProcessingError, ExportError):
                raise
            except Exception as exc:
                raise ProcessingError(
                    f"Ошибка генерации BPMN для процесса: {pid}",
                    detail=str(exc),
                ) from exc

        if on_progress:
            on_progress(100, 100, "Генерация BPMN завершена")

        logger.info(
            "Сгенерировано %d BPMN-диаграмм (проект: %s)",
            len(results),
            project_id,
        )
        return results

    async def get_bpmn_svg(
        self,
        project_id: str,
        process_id: str,
    ) -> str:
        """Возвращает SVG-строку для процесса.

        Args:
            project_id: Идентификатор проекта.
            process_id: Идентификатор процесса.

        Returns:
            SVG-строка диаграммы.

        Raises:
            NotFoundError: Если SVG-файл не найден.
        """
        project_dir = self._ensure_project_exists(project_id)
        svg_path = project_dir.bpmn / f"{process_id}.svg"

        if not svg_path.is_file():
            raise NotFoundError(
                f"SVG-диаграмма не найдена для процесса: {process_id}",
                detail={"project_id": project_id, "process_id": process_id},
            )

        try:
            return svg_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ProcessingError(
                f"Ошибка чтения SVG-файла: {process_id}",
                detail=str(exc),
            ) from exc

    async def get_bpmn_xml(
        self,
        project_id: str,
        process_id: str,
    ) -> str:
        """Возвращает BPMN XML-строку для процесса.

        Args:
            project_id: Идентификатор проекта.
            process_id: Идентификатор процесса.

        Returns:
            BPMN 2.0 XML-строка.

        Raises:
            NotFoundError: Если BPMN-файл не найден.
        """
        project_dir = self._ensure_project_exists(project_id)
        bpmn_path = project_dir.bpmn / f"{process_id}.bpmn"

        if not bpmn_path.is_file():
            raise NotFoundError(
                f"BPMN-файл не найден для процесса: {process_id}",
                detail={"project_id": project_id, "process_id": process_id},
            )

        try:
            return bpmn_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ProcessingError(
                f"Ошибка чтения BPMN-файла: {process_id}",
                detail=str(exc),
            ) from exc

    # ------------------------------------------------------------------
    # Приватные методы
    # ------------------------------------------------------------------

    def _generate_single(
        self,
        project_dir: ProjectDir,
        process_id: str,
        bpmn_json: dict[str, Any],
    ) -> dict[str, Any]:
        """Генерирует BPMN XML и SVG для одного процесса.

        Returns:
            Словарь с путями к сгенерированным файлам.
        """
        # 1. Вычисляем компоновку
        layout = self._layout.calculate_layout(bpmn_json)
        bpmn_json["layout"] = layout

        # 2. Конвертируем в BPMN XML
        bpmn_xml = self._converter.convert(bpmn_json)

        # 3. Сохраняем BPMN XML
        bpmn_path = project_dir.bpmn / f"{process_id}.bpmn"
        try:
            bpmn_path.write_text(bpmn_xml, encoding="utf-8")
        except OSError as exc:
            raise ProcessingError(
                f"Ошибка сохранения BPMN-файла: {process_id}",
                detail=str(exc),
            ) from exc

        # 4. Генерируем и сохраняем SVG
        svg_content = self._render_svg(bpmn_json, layout)
        svg_path = project_dir.bpmn / f"{process_id}.svg"
        try:
            svg_path.write_text(svg_content, encoding="utf-8")
        except OSError as exc:
            raise ProcessingError(
                f"Ошибка сохранения SVG-файла: {process_id}",
                detail=str(exc),
            ) from exc

        logger.debug(
            "BPMN сгенерирован: %s -> %s, %s",
            process_id,
            bpmn_path.name,
            svg_path.name,
        )

        return {
            "process_id": process_id,
            "process_name": bpmn_json.get("process_name", ""),
            "bpmn_path": str(bpmn_path),
            "svg_path": str(svg_path),
        }

    @staticmethod
    def _render_svg(
        bpmn_json: dict[str, Any],
        layout: dict[str, Any],
    ) -> str:
        """Рендерит SVG-диаграмму из BPMN JSON и компоновки.

        Создаёт минимальное SVG-представление BPMN-диаграммы
        с элементами, потоками и подписями.
        """
        element_positions = layout.get("elements", {})
        flow_waypoints = layout.get("flows", {})
        lane_positions = layout.get("lanes", {})

        # Определяем размеры SVG
        max_x: float = 800
        max_y: float = 600
        for pos in element_positions.values():
            right = pos.get("x", 0) + pos.get("width", 0) + 60
            bottom = pos.get("y", 0) + pos.get("height", 0) + 60
            max_x = max(max_x, right)
            max_y = max(max_y, bottom)
        for lp in lane_positions.values():
            right = lp.get("x", 0) + lp.get("width", 0) + 60
            bottom = lp.get("y", 0) + lp.get("height", 0) + 60
            max_x = max(max_x, right)
            max_y = max(max_y, bottom)

        width = int(max_x)
        height = int(max_y)

        svg_parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            '<defs>',
            '  <marker id="arrowhead" markerWidth="10" markerHeight="7" '
            'refX="10" refY="3.5" orient="auto">',
            '    <polygon points="0 0, 10 3.5, 0 7" fill="#333" />',
            '  </marker>',
            '</defs>',
            f'<rect width="{width}" height="{height}" fill="#fff" />',
        ]

        # Дорожки (прямоугольники с заливкой)
        elements = bpmn_json.get("elements", [])
        elem_map: dict[str, dict[str, Any]] = {
            e["id"]: e for e in elements if "id" in e
        }

        for lane_id, lp in lane_positions.items():
            lx, ly = lp["x"], lp["y"]
            lw, lh = lp["width"], lp["height"]
            svg_parts.append(
                f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" '
                f'fill="#f9f9f9" stroke="#ccc" stroke-width="1" />'
            )
            svg_parts.append(
                f'<text x="{lx + 14}" y="{ly + lh / 2}" '
                f'text-anchor="middle" font-size="11" fill="#666" '
                f'transform="rotate(-90 {lx + 14} {ly + lh / 2})">'
                f'{lane_id}</text>'
            )

        # Потоки (линии со стрелками)
        for flow_id, wps in flow_waypoints.items():
            if len(wps) < 2:
                continue
            points = " ".join(f"{wp['x']},{wp['y']}" for wp in wps)
            svg_parts.append(
                f'<polyline points="{points}" fill="none" '
                f'stroke="#333" stroke-width="1.5" '
                f'marker-end="url(#arrowhead)" />'
            )

        # Элементы
        for elem_id, pos in element_positions.items():
            elem = elem_map.get(elem_id, {})
            elem_type = elem.get("type", "task")
            name = elem.get("name", "")
            x, y = pos["x"], pos["y"]
            w, h = pos["width"], pos["height"]

            if elem_type == "startEvent":
                cx, cy = x + w / 2, y + h / 2
                svg_parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{w / 2}" '
                    f'fill="#e8f5e9" stroke="#4caf50" stroke-width="2" />'
                )
                if name:
                    svg_parts.append(
                        f'<text x="{cx}" y="{cy + w / 2 + 14}" '
                        f'text-anchor="middle" font-size="10" fill="#333">'
                        f'{_escape_xml(name)}</text>'
                    )
            elif elem_type == "endEvent":
                cx, cy = x + w / 2, y + h / 2
                svg_parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{w / 2}" '
                    f'fill="#ffebee" stroke="#f44336" stroke-width="3" />'
                )
                if name:
                    svg_parts.append(
                        f'<text x="{cx}" y="{cy + w / 2 + 14}" '
                        f'text-anchor="middle" font-size="10" fill="#333">'
                        f'{_escape_xml(name)}</text>'
                    )
            elif elem_type in (
                "exclusiveGateway", "parallelGateway",
                "inclusiveGateway", "eventBasedGateway",
            ):
                cx, cy = x + w / 2, y + h / 2
                half = w / 2
                points = (
                    f"{cx},{cy - half} {cx + half},{cy} "
                    f"{cx},{cy + half} {cx - half},{cy}"
                )
                svg_parts.append(
                    f'<polygon points="{points}" '
                    f'fill="#fff3e0" stroke="#ff9800" stroke-width="2" />'
                )
                # Символ шлюза
                symbol = "X" if elem_type == "exclusiveGateway" else (
                    "+" if elem_type == "parallelGateway" else "O"
                )
                svg_parts.append(
                    f'<text x="{cx}" y="{cy + 5}" '
                    f'text-anchor="middle" font-size="14" '
                    f'font-weight="bold" fill="#e65100">{symbol}</text>'
                )
                if name:
                    svg_parts.append(
                        f'<text x="{cx}" y="{cy + half + 14}" '
                        f'text-anchor="middle" font-size="9" fill="#666">'
                        f'{_escape_xml(name)}</text>'
                    )
            else:
                # Задача (task, userTask, etc.) — скруглённый прямоугольник
                svg_parts.append(
                    f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                    f'rx="8" ry="8" fill="#e3f2fd" stroke="#1976d2" '
                    f'stroke-width="1.5" />'
                )
                if name:
                    # Разбиваем длинные названия на строки
                    lines = _wrap_text(name, max_chars=18)
                    line_height = 14
                    start_y = y + h / 2 - (len(lines) - 1) * line_height / 2
                    for i, line in enumerate(lines):
                        svg_parts.append(
                            f'<text x="{x + w / 2}" y="{start_y + i * line_height}" '
                            f'text-anchor="middle" font-size="11" fill="#333">'
                            f'{_escape_xml(line)}</text>'
                        )

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    @staticmethod
    def _ensure_project_exists(project_id: str) -> ProjectDir:
        """Проверяет существование проекта."""
        project_dir = get_project_dir(project_id)
        if not project_dir.exists():
            raise NotFoundError(
                f"Проект не найден: {project_id}",
                detail={"project_id": project_id},
            )
        return project_dir

    @staticmethod
    def _load_bpmn_jsons(
        project_dir: ProjectDir,
        process_ids: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Загружает BPMN JSON-описания процессов.

        Ищет файлы с суффиксом ``_bpmn.json`` в директории процессов,
        а при их отсутствии — обычные JSON-файлы процессов.
        """
        result: dict[str, dict[str, Any]] = {}

        if not project_dir.processes.is_dir():
            return result

        # Сначала ищем готовые BPMN JSON
        for jf in sorted(project_dir.processes.iterdir()):
            if jf.is_file() and jf.name.endswith("_bpmn.json"):
                pid = jf.stem.replace("_bpmn", "")
                if process_ids and pid not in process_ids:
                    continue
                try:
                    with open(jf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        result[pid] = data
                except Exception as exc:
                    logger.warning(
                        "Не удалось прочитать BPMN JSON %s: %s",
                        jf.name, exc,
                    )

        # Если не нашли BPMN JSON, используем обычные JSON процессов
        if not result:
            for jf in sorted(project_dir.processes.iterdir()):
                if (
                    jf.is_file()
                    and jf.suffix.lower() == ".json"
                    and not jf.name.startswith("_")
                    and not jf.name.endswith("_gap.json")
                    and not jf.name.endswith("_tobe.json")
                ):
                    pid = jf.stem
                    if process_ids and pid not in process_ids:
                        continue
                    try:
                        with open(jf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if isinstance(data, dict):
                            result[pid] = data
                    except Exception as exc:
                        logger.warning(
                            "Не удалось прочитать процесс %s: %s",
                            jf.name, exc,
                        )

        return result


# ------------------------------------------------------------------
# Вспомогательные функции
# ------------------------------------------------------------------


def _escape_xml(text: str) -> str:
    """Экранирует специальные символы XML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _wrap_text(text: str, max_chars: int = 18) -> list[str]:
    """Разбивает текст на строки по ширине."""
    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        if current_line and len(current_line) + 1 + len(word) > max_chars:
            lines.append(current_line)
            current_line = word
        else:
            current_line = f"{current_line} {word}".strip()

    if current_line:
        lines.append(current_line)

    return lines if lines else [text]
