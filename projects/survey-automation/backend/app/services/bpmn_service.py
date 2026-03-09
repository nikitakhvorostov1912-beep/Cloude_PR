"""Сервис генерации BPMN и SVG."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

import aiofiles

from app.bpmn.json_to_bpmn import BpmnConverter
from app.bpmn.layout import BpmnLayout
from app.bpmn.process_to_bpmn import ProcessToBpmnConverter
from app.config import ProjectDir, get_project_dir
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
        bpmn_jsons = await self._load_bpmn_jsons(project_dir, process_ids)

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

        # Если загружены данные в raw-формате {processes: [...]}, конвертируем через
        # ProcessToBpmnConverter чтобы получить {elements, flows, participants} с
        # актуальными event_type, multi_instance, timer_wait и прочими метаданными
        _proc_converter = ProcessToBpmnConverter()

        # Проверяем: если загружен один файл processes.json (pid="processes"),
        # раскрываем список процессов в отдельные bpmn_json
        expanded: dict[str, dict[str, Any]] = {}
        for pid, data in bpmn_jsons.items():
            if "processes" in data and "elements" not in data:
                # Raw-формат — конвертируем каждый процесс отдельно
                for proc in data.get("processes", []):
                    proc_id = proc.get("id", pid)
                    expanded[proc_id] = _proc_converter.convert(proc)
                    logger.debug("ProcessToBpmnConverter: %s → %d элементов", proc_id, len(expanded[proc_id].get("elements", [])))
            elif "elements" not in data:
                # Возможно отдельный процесс в raw-формате
                converted = _proc_converter.convert(data)
                if converted.get("elements"):
                    expanded[pid] = converted
                else:
                    expanded[pid] = data
            else:
                # Уже в BPMN JSON формате — конвертируем заново из source если он есть
                # чтобы подхватить изменения в ProcessToBpmnConverter
                expanded[pid] = data

        bpmn_jsons = expanded or bpmn_jsons
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

        # 5. Сохраняем BPMN JSON (с полями multi_instance, event_type, timer_wait и layout)
        #    Используется при экспорте Visio чтобы сохранить все метаданные
        import json as _json
        bpmn_json_path = project_dir.processes / f"{process_id}_bpmn.json"
        try:
            bpmn_json_path.write_text(
                _json.dumps(bpmn_json, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Не удалось сохранить BPMN JSON: %s — %s", process_id, exc)

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

        Создаёт профессиональное SVG-представление BPMN-диаграммы
        в стиле Bitrix24: белые задачи с цветными акцент-полосами,
        широкие заголовки дорожек, иконки ролей, BPMN-события.
        """
        element_positions = layout.get("elements", {})
        flow_waypoints = layout.get("flows", {})
        lane_positions = layout.get("lanes", {})

        # Определяем размеры SVG
        max_x: float = 900
        max_y: float = 600
        for pos in element_positions.values():
            right = pos.get("x", 0) + pos.get("width", 0) + 80
            bottom = pos.get("y", 0) + pos.get("height", 0) + 80
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
            f'viewBox="0 0 {width} {height}" '
            f'font-family="Segoe UI, Arial, sans-serif">',
            '<defs>',
            '  <marker id="arrowhead" markerWidth="9" markerHeight="7" '
            'refX="9" refY="3.5" orient="auto">',
            '    <polygon points="0 0, 9 3.5, 0 7" fill="#5A6475" />',
            '  </marker>',
            '  <marker id="arrowhead-msg" markerWidth="9" markerHeight="7" '
            'refX="9" refY="3.5" orient="auto">',
            '    <polygon points="0 0, 9 3.5, 0 7" fill="#7B8EA8" />',
            '  </marker>',
            '  <filter id="shadow" x="-5%" y="-5%" width="120%" height="120%">',
            '    <feDropShadow dx="0" dy="2" stdDeviation="3" '
            'flood-color="#000" flood-opacity="0.10" />',
            '  </filter>',
            '  <filter id="shadow-lane" x="-2%" y="-2%" width="104%" height="104%">',
            '    <feDropShadow dx="0" dy="1" stdDeviation="2" '
            'flood-color="#000" flood-opacity="0.08" />',
            '  </filter>',
            '</defs>',
            f'<rect width="{width}" height="{height}" fill="#F0F2F5" />',
        ]

        # Палитра дорожек: (bg_light, accent, accent_dark, bg_header)
        # bg_light — фон дорожки, accent — акцент-полоса задач и заголовок
        _LANE_PALETTE = [
            ("#EEF2FA", "#4472C4", "#2B5091", "#D6E0F5"),  # Синий
            ("#EEF5EE", "#4CAF50", "#2E7D32", "#C8E6C9"),  # Зелёный
            ("#FFF8E7", "#F9A825", "#F57F17", "#FFECB3"),  # Жёлтый
            ("#FEF0EE", "#E53935", "#B71C1C", "#FFCDD2"),  # Красный
            ("#F3EEF9", "#7B1FA2", "#4A148C", "#E1BEE7"),  # Фиолетовый
            ("#E8F8F8", "#00796B", "#004D40", "#B2DFDB"),  # Бирюзовый
            ("#FFF3E0", "#E65100", "#BF360C", "#FFE0B2"),  # Оранжевый
        ]

        # Карта имён дорожек из participants
        lane_name_map: dict[str, str] = {}
        for p in bpmn_json.get("participants", []):
            lid = p.get("lane_id") or p.get("id", "")
            if p.get("name") and lid:
                lane_name_map[lid] = p["name"]

        # Строим карту: lane_id → индекс цвета и акцентный цвет
        lane_color_map: dict[str, tuple[str, str, str, str]] = {}
        for lane_idx, (lane_id, _lp) in enumerate(lane_positions.items()):
            lane_color_map[lane_id] = _LANE_PALETTE[lane_idx % len(_LANE_PALETTE)]

        # Строим карту: elem_id → lane_id (из participants)
        elem_lane_map: dict[str, str] = {}
        for p in bpmn_json.get("participants", []):
            lid = p.get("lane_id") or p.get("id", "")
            for eid in p.get("element_ids", []):
                elem_lane_map[eid] = lid

        elements = bpmn_json.get("elements", [])
        elem_map: dict[str, dict[str, Any]] = {
            e["id"]: e for e in elements if "id" in e
        }

        # ---------- ДОРОЖКИ ----------
        HEADER_W = 55  # ширина вертикального заголовка дорожки

        for lane_id, lp in lane_positions.items():
            lx, ly = lp["x"], lp["y"]
            lw, lh = lp["width"], lp["height"]
            palette = lane_color_map.get(lane_id, _LANE_PALETTE[0])
            bg_light, accent, accent_dark, bg_header = palette
            lane_name = lane_name_map.get(lane_id, lp.get("name", lane_id))

            # Фон дорожки (светлый)
            svg_parts.append(
                f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" '
                f'fill="{bg_light}" stroke="{accent}" stroke-width="1.5" '
                f'rx="6" filter="url(#shadow-lane)" />'
            )
            # Заголовок дорожки (вертикальная полоса, цвет accent_dark)
            svg_parts.append(
                f'<rect x="{lx}" y="{ly}" width="{HEADER_W}" height="{lh}" '
                f'fill="{accent_dark}" rx="6" />'
            )
            # Белая разделительная линия справа от заголовка
            svg_parts.append(
                f'<line x1="{lx + HEADER_W}" y1="{ly}" '
                f'x2="{lx + HEADER_W}" y2="{ly + lh}" '
                f'stroke="{accent}" stroke-width="1" />'
            )
            # Имя дорожки (вертикальный текст, белый, крупнее)
            svg_parts.append(
                f'<text x="{lx + HEADER_W / 2}" y="{ly + lh / 2}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'font-size="13" font-weight="bold" letter-spacing="1" '
                f'fill="#FFFFFF" '
                f'transform="rotate(-90 {lx + HEADER_W / 2} {ly + lh / 2})">'
                f'{_escape_xml(lane_name)}</text>'
            )

        # ---------- ПОТОКИ ----------
        flows_list = bpmn_json.get("flows", [])
        flow_name_map: dict[str, str] = {}
        flow_type_map: dict[str, str] = {}
        for fl in flows_list:
            fid = fl.get("id", "")
            fname = fl.get("name", "")
            ftype = fl.get("type", "sequenceFlow")
            if fname:
                flow_name_map[fid] = fname
            flow_type_map[fid] = ftype

        for flow_id, wps in flow_waypoints.items():
            if len(wps) < 2:
                continue
            points = " ".join(f"{wp['x']},{wp['y']}" for wp in wps)
            is_msg = flow_type_map.get(flow_id, "") == "messageFlow"
            stroke_color = "#7B8EA8" if is_msg else "#5A6475"
            dash = 'stroke-dasharray="6,4"' if is_msg else ""
            marker = "arrowhead-msg" if is_msg else "arrowhead"
            svg_parts.append(
                f'<polyline points="{points}" fill="none" '
                f'stroke="{stroke_color}" stroke-width="1.5" {dash} '
                f'marker-end="url(#{marker})" />'
            )
            # Подпись потока ("Да"/"Нет") с белым фоном
            flow_label = flow_name_map.get(flow_id, "")
            if flow_label:
                mid_x = (wps[0]["x"] + wps[1]["x"]) / 2
                mid_y = (wps[0]["y"] + wps[1]["y"]) / 2
                lbl_w = max(len(flow_label) * 7 + 10, 30)
                svg_parts.append(
                    f'<rect x="{mid_x - lbl_w / 2}" y="{mid_y - 11}" '
                    f'width="{lbl_w}" height="14" fill="white" '
                    f'rx="3" stroke="{stroke_color}" stroke-width="0.5" />'
                )
                svg_parts.append(
                    f'<text x="{mid_x}" y="{mid_y}" '
                    f'text-anchor="middle" dominant-baseline="middle" '
                    f'font-size="10" font-weight="600" fill="{stroke_color}">'
                    f'{_escape_xml(flow_label)}</text>'
                )

        # ---------- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ: иконка роли ----------
        def _person_icon(px: float, py: float, color: str) -> str:
            """SVG-иконка человека (голова + тело) в виде пути."""
            # Голова: круг r=4, тело: эллипс
            return (
                f'<circle cx="{px + 7}" cy="{py + 5}" r="4" '
                f'fill="{color}" opacity="0.55" />'
                f'<ellipse cx="{px + 7}" cy="{py + 14}" rx="6" ry="4" '
                f'fill="{color}" opacity="0.55" />'
            )

        # ---------- ЭЛЕМЕНТЫ ----------
        EVENT_LABEL_FONT = 11

        for elem_id, pos in element_positions.items():
            elem = elem_map.get(elem_id, {})
            elem_type = elem.get("type", "task")
            name = elem.get("name", "")
            x, y = pos["x"], pos["y"]
            w, h = pos["width"], pos["height"]

            # Получаем акцентный цвет для дорожки этого элемента
            lane_id_elem = elem_lane_map.get(elem_id, "")
            ep = lane_color_map.get(lane_id_elem, _LANE_PALETTE[0])
            _, elem_accent, elem_accent_dark, _ = ep

            if elem_type == "startEvent":
                cx, cy = x + w / 2, y + h / 2
                r = w / 2
                svg_parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r}" '
                    f'fill="#F1FAF1" stroke="#43A047" stroke-width="2.5" '
                    f'filter="url(#shadow)" />'
                )
                svg_parts.append(
                    f'<polygon points="{cx - 5},{cy - 6} {cx + 7},{cy} {cx - 5},{cy + 6}" '
                    f'fill="#43A047" />'
                )
                if name:
                    svg_parts.append(
                        f'<text x="{cx}" y="{cy + r + 14}" '
                        f'text-anchor="middle" font-size="{EVENT_LABEL_FONT}" '
                        f'fill="#2E7D32" font-weight="500">'
                        f'{_escape_xml(name)}</text>'
                    )

            elif elem_type == "messageStartEvent":
                cx, cy = x + w / 2, y + h / 2
                r = w / 2
                svg_parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r}" '
                    f'fill="#F1FAF1" stroke="#43A047" stroke-width="2.5" '
                    f'filter="url(#shadow)" />'
                )
                # Конверт SVG (упрощённый): прямоугольник + крышка
                ew, eh = r * 1.1, r * 0.8
                ex, ey = cx - ew / 2, cy - eh / 2
                svg_parts.append(
                    f'<rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" '
                    f'fill="#A5D6A7" stroke="#2E7D32" stroke-width="1" rx="1" />'
                )
                svg_parts.append(
                    f'<polyline points="{ex},{ey} {cx},{cy + 2} {ex + ew},{ey}" '
                    f'fill="none" stroke="#2E7D32" stroke-width="1" />'
                )
                if name:
                    svg_parts.append(
                        f'<text x="{cx}" y="{cy + r + 14}" '
                        f'text-anchor="middle" font-size="{EVENT_LABEL_FONT}" '
                        f'fill="#2E7D32" font-weight="500">'
                        f'{_escape_xml(name)}</text>'
                    )

            elif elem_type == "endEvent":
                cx, cy = x + w / 2, y + h / 2
                r = w / 2
                svg_parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r}" '
                    f'fill="#FFF0EE" stroke="#E53935" stroke-width="3.5" '
                    f'filter="url(#shadow)" />'
                )
                # Квадрат внутри (BPMN конец)
                sq = r * 0.55
                svg_parts.append(
                    f'<rect x="{cx - sq}" y="{cy - sq}" '
                    f'width="{sq * 2}" height="{sq * 2}" fill="#E53935" />'
                )
                if name:
                    svg_parts.append(
                        f'<text x="{cx}" y="{cy + r + 14}" '
                        f'text-anchor="middle" font-size="{EVENT_LABEL_FONT}" '
                        f'fill="#B71C1C" font-weight="500">'
                        f'{_escape_xml(name)}</text>'
                    )

            elif elem_type == "messageEndEvent":
                cx, cy = x + w / 2, y + h / 2
                r = w / 2
                svg_parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r}" '
                    f'fill="#FFF0EE" stroke="#E53935" stroke-width="3.5" '
                    f'filter="url(#shadow)" />'
                )
                # Закрашенный конверт
                ew, eh = r * 1.1, r * 0.8
                ex, ey = cx - ew / 2, cy - eh / 2
                svg_parts.append(
                    f'<rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" '
                    f'fill="#EF9A9A" stroke="#B71C1C" stroke-width="1" rx="1" />'
                )
                svg_parts.append(
                    f'<polyline points="{ex},{ey} {cx},{cy + 2} {ex + ew},{ey}" '
                    f'fill="none" stroke="#B71C1C" stroke-width="1" />'
                )
                if name:
                    svg_parts.append(
                        f'<text x="{cx}" y="{cy + r + 14}" '
                        f'text-anchor="middle" font-size="{EVENT_LABEL_FONT}" '
                        f'fill="#B71C1C" font-weight="500">'
                        f'{_escape_xml(name)}</text>'
                    )

            elif elem_type in ("cancelEndEvent", "cancelEvent"):
                cx, cy = x + w / 2, y + h / 2
                r = w / 2
                # Внешний круг (жирный красный)
                svg_parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r}" '
                    f'fill="#FFF0EE" stroke="#E53935" stroke-width="4" '
                    f'filter="url(#shadow)" />'
                )
                # Внутренний круг (тонкий)
                svg_parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r - 5}" '
                    f'fill="none" stroke="#E53935" stroke-width="1.5" />'
                )
                # Крест × из линий (BPMN cancel)
                cs = r * 0.45
                svg_parts.append(
                    f'<line x1="{cx - cs}" y1="{cy - cs}" x2="{cx + cs}" y2="{cy + cs}" '
                    f'stroke="#E53935" stroke-width="2.5" stroke-linecap="round" />'
                )
                svg_parts.append(
                    f'<line x1="{cx + cs}" y1="{cy - cs}" x2="{cx - cs}" y2="{cy + cs}" '
                    f'stroke="#E53935" stroke-width="2.5" stroke-linecap="round" />'
                )
                if name:
                    svg_parts.append(
                        f'<text x="{cx}" y="{cy + r + 14}" '
                        f'text-anchor="middle" font-size="{EVENT_LABEL_FONT}" '
                        f'fill="#B71C1C" font-weight="500">'
                        f'{_escape_xml(name)}</text>'
                    )

            elif elem_type in ("timerIntermediateCatchEvent", "timerEvent"):
                cx, cy = x + w / 2, y + h / 2
                r = w / 2
                # Двойной жёлтый круг
                svg_parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r}" '
                    f'fill="#FFFDE7" stroke="#F9A825" stroke-width="2" '
                    f'filter="url(#shadow)" />'
                )
                svg_parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r - 4}" '
                    f'fill="none" stroke="#F9A825" stroke-width="1.5" />'
                )
                # Циферблат: штрихи на 12/3/6/9
                cr = r - 7
                for angle_deg in (0, 90, 180, 270):
                    import math
                    angle_rad = math.radians(angle_deg - 90)
                    tick_x1 = cx + (cr - 3) * math.cos(angle_rad)
                    tick_y1 = cy + (cr - 3) * math.sin(angle_rad)
                    tick_x2 = cx + cr * math.cos(angle_rad)
                    tick_y2 = cy + cr * math.sin(angle_rad)
                    svg_parts.append(
                        f'<line x1="{tick_x1:.1f}" y1="{tick_y1:.1f}" '
                        f'x2="{tick_x2:.1f}" y2="{tick_y2:.1f}" '
                        f'stroke="#F57F17" stroke-width="1.5" />'
                    )
                # Стрелки часов: минутная (к 12) и часовая (к 3)
                svg_parts.append(
                    f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - cr + 2}" '
                    f'stroke="#F57F17" stroke-width="1.5" stroke-linecap="round" />'
                )
                svg_parts.append(
                    f'<line x1="{cx}" y1="{cy}" x2="{cx + cr * 0.7:.1f}" y2="{cy}" '
                    f'stroke="#F57F17" stroke-width="1.5" stroke-linecap="round" />'
                )
                timer_label = elem.get("timer_wait", name)
                if timer_label:
                    svg_parts.append(
                        f'<text x="{cx}" y="{cy + r + 14}" '
                        f'text-anchor="middle" font-size="{EVENT_LABEL_FONT}" '
                        f'fill="#F57F17" font-weight="500">'
                        f'{_escape_xml(timer_label)}</text>'
                    )

            elif elem_type in (
                "exclusiveGateway", "parallelGateway",
                "inclusiveGateway", "eventBasedGateway",
            ):
                cx, cy = x + w / 2, y + h / 2
                half = w / 2
                pts = (
                    f"{cx},{cy - half} {cx + half},{cy} "
                    f"{cx},{cy + half} {cx - half},{cy}"
                )
                is_exclusive = elem_type == "exclusiveGateway"
                gw_fill = "#FFF8E7" if is_exclusive else "#FFF8E7"
                gw_stroke = "#F9A825" if is_exclusive else "#43A047"
                svg_parts.append(
                    f'<polygon points="{pts}" '
                    f'fill="{gw_fill}" stroke="{gw_stroke}" stroke-width="2" '
                    f'filter="url(#shadow)" />'
                )
                if is_exclusive:
                    # X из линий (BPMN exclusive)
                    d = half * 0.4
                    svg_parts.append(
                        f'<line x1="{cx - d}" y1="{cy - d}" '
                        f'x2="{cx + d}" y2="{cy + d}" '
                        f'stroke="{gw_stroke}" stroke-width="2.5" stroke-linecap="round" />'
                    )
                    svg_parts.append(
                        f'<line x1="{cx + d}" y1="{cy - d}" '
                        f'x2="{cx - d}" y2="{cy + d}" '
                        f'stroke="{gw_stroke}" stroke-width="2.5" stroke-linecap="round" />'
                    )
                elif elem_type == "parallelGateway":
                    d = half * 0.4
                    svg_parts.append(
                        f'<line x1="{cx}" y1="{cy - d}" x2="{cx}" y2="{cy + d}" '
                        f'stroke="{gw_stroke}" stroke-width="2.5" stroke-linecap="round" />'
                    )
                    svg_parts.append(
                        f'<line x1="{cx - d}" y1="{cy}" x2="{cx + d}" y2="{cy}" '
                        f'stroke="{gw_stroke}" stroke-width="2.5" stroke-linecap="round" />'
                    )
                else:
                    svg_parts.append(
                        f'<circle cx="{cx}" cy="{cy}" r="{half * 0.35}" '
                        f'fill="none" stroke="{gw_stroke}" stroke-width="2" />'
                    )
                # Подпись шлюза (над ромбом)
                if name:
                    gw_lines = _wrap_text(name, max_chars=20)
                    for gi, gl in enumerate(gw_lines):
                        svg_parts.append(
                            f'<text x="{cx}" '
                            f'y="{cy - half - 8 - (len(gw_lines) - 1 - gi) * 13}" '
                            f'text-anchor="middle" font-size="10" '
                            f'fill="#5A6475" font-style="italic">'
                            f'{_escape_xml(gl)}</text>'
                        )

            else:
                # ---- Задача (task, userTask, serviceTask и т.д.) ----
                is_subprocess = elem.get("is_subprocess", False)
                multi_instance = elem.get("multi_instance", False)
                step_num = elem.get("step_number", "")

                # Цвета: подпроцессы чуть другого оттенка
                bg_fill = "#FFFFFF"
                border_color = "#CBD4E1"
                accent_bar = elem_accent if not is_subprocess else elem_accent_dark
                text_main = "#1A202C"

                # Тень + основной прямоугольник (белый)
                svg_parts.append(
                    f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                    f'rx="8" ry="8" fill="{bg_fill}" stroke="{border_color}" '
                    f'stroke-width="1.5" filter="url(#shadow)" />'
                )
                # Цветная акцент-полоса слева (4px)
                bar_h = h - 16  # оставляем скругление
                svg_parts.append(
                    f'<rect x="{x}" y="{y + 8}" width="5" height="{bar_h}" '
                    f'fill="{accent_bar}" rx="3" />'
                )
                # Скругление угла поверх полосы (маскировка)
                svg_parts.append(
                    f'<rect x="{x}" y="{y}" width="5" height="8" '
                    f'fill="{accent_bar}" />'
                )
                svg_parts.append(
                    f'<rect x="{x}" y="{y + h - 8}" width="5" height="8" '
                    f'fill="{accent_bar}" />'
                )

                # Иконка роли/задачи (правый верхний угол)
                icon_x = x + w - 22
                icon_y = y + 6
                svg_parts.append(_person_icon(icon_x, icon_y, elem_accent))

                # Маркеры снизу: [+] подпроцесс и ||| multi-instance
                has_markers = is_subprocess or multi_instance
                if is_subprocess and multi_instance:
                    sp_size = 13
                    sp_x = x + w / 2 - sp_size - 5
                    sp_y = y + h - sp_size - 4
                    svg_parts.append(
                        f'<rect x="{sp_x}" y="{sp_y}" width="{sp_size}" '
                        f'height="{sp_size}" fill="white" stroke="{accent_bar}" '
                        f'stroke-width="1.5" />'
                    )
                    svg_parts.append(
                        f'<text x="{sp_x + sp_size / 2}" y="{sp_y + sp_size - 2}" '
                        f'text-anchor="middle" font-size="11" '
                        f'font-weight="bold" fill="{accent_bar}">+</text>'
                    )
                    mi_y = y + h - 8
                    mi_cx = x + w / 2 + 10
                    for line_i in range(3):
                        lx_ = mi_cx - 4 + line_i * 5
                        svg_parts.append(
                            f'<line x1="{lx_}" y1="{mi_y - 4}" '
                            f'x2="{lx_}" y2="{mi_y + 4}" '
                            f'stroke="{accent_bar}" stroke-width="1.8" '
                            f'stroke-linecap="round" />'
                        )
                elif is_subprocess:
                    sp_size = 13
                    sp_x = x + w / 2 - sp_size / 2
                    sp_y = y + h - sp_size - 4
                    svg_parts.append(
                        f'<rect x="{sp_x}" y="{sp_y}" width="{sp_size}" '
                        f'height="{sp_size}" fill="white" stroke="{accent_bar}" '
                        f'stroke-width="1.5" />'
                    )
                    svg_parts.append(
                        f'<text x="{sp_x + sp_size / 2}" y="{sp_y + sp_size - 2}" '
                        f'text-anchor="middle" font-size="11" '
                        f'font-weight="bold" fill="{accent_bar}">+</text>'
                    )
                elif multi_instance:
                    mi_y = y + h - 8
                    mi_cx = x + w / 2
                    for line_i in range(3):
                        lx_ = mi_cx - 7 + line_i * 5
                        svg_parts.append(
                            f'<line x1="{lx_}" y1="{mi_y - 4}" '
                            f'x2="{lx_}" y2="{mi_y + 4}" '
                            f'stroke="{accent_bar}" stroke-width="1.8" '
                            f'stroke-linecap="round" />'
                        )

                # Текст задачи
                if name:
                    # Область текста: от left+8 до right-28 (иконка), до нижних маркеров
                    text_x = x + 12  # отступ от акцент-полосы
                    text_w_avail = w - 40  # минус полоса и иконка
                    text_area_h = h - (22 if has_markers else 8)

                    # Номер шага (если есть) — мелко цветом акцента
                    text_y_start = y + 16
                    if step_num:
                        svg_parts.append(
                            f'<text x="{text_x}" y="{text_y_start}" '
                            f'font-size="9" fill="{accent_bar}" '
                            f'font-weight="600">'
                            f'{_escape_xml(str(step_num))}</text>'
                        )
                        text_y_start += 12

                    # Перенос текста
                    max_chars_task = max(12, int(text_w_avail / 7.5))
                    lines = _wrap_text(name, max_chars=max_chars_task)
                    line_height = 15
                    # Центрируем по вертикали в доступной области
                    total_text_h = len(lines) * line_height
                    avail_h = text_area_h - (text_y_start - y)
                    ty = text_y_start + max(0, (avail_h - total_text_h) / 2)
                    for i, line in enumerate(lines):
                        svg_parts.append(
                            f'<text x="{text_x}" y="{ty + i * line_height}" '
                            f'font-size="12" fill="{text_main}" '
                            f'font-weight="500">'
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
    async def _load_bpmn_jsons(
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
                    async with aiofiles.open(jf, "r", encoding="utf-8") as f:
                        content = await f.read()
                    data = json.loads(content)
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
                        async with aiofiles.open(jf, "r", encoding="utf-8") as f:
                            content = await f.read()
                        data = json.loads(content)
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
