"""Рендеринг BPMN XML в SVG для отображения в веб-интерфейсе.

Модуль парсит BPMN 2.0 XML с секцией Diagram Interchange (DI)
и генерирует SVG-изображение со всеми элементами процесса:
события, задачи, шлюзы, пулы, дорожки и потоки управления.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from lxml import etree

from app.bpmn.json_to_bpmn import BpmnConverter
from app.bpmn.layout import BpmnLayout
from app.exceptions import ExportError

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Пространства имён BPMN 2.0
# ----------------------------------------------------------------------

BPMN_NS: str = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS: str = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS: str = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS: str = "http://www.omg.org/spec/DD/20100524/DI"

_NS: dict[str, str] = {
    "bpmn": BPMN_NS,
    "bpmndi": BPMNDI_NS,
    "dc": DC_NS,
    "di": DI_NS,
}

# ----------------------------------------------------------------------
# SVG namespace
# ----------------------------------------------------------------------

SVG_NS: str = "http://www.w3.org/2000/svg"
XLINK_NS: str = "http://www.w3.org/1999/xlink"

# ----------------------------------------------------------------------
# Размеры элементов по умолчанию (fallback, если DI не содержит Bounds)
# ----------------------------------------------------------------------

_DEFAULT_TASK_W: float = 180.0
_DEFAULT_TASK_H: float = 90.0
_DEFAULT_EVENT_R: float = 18.0
_DEFAULT_GATEWAY_S: float = 50.0

# Отступ вокруг диаграммы для viewBox
_PADDING: float = 30.0

# Размер стрелки
_ARROW_SIZE: float = 10.0

# Максимальная длина текста в одной строке (символы).
# Для кириллицы ~7px/символ при font-size 12px → 22 × 7 = 154px < 180px (ширина задачи).
_MAX_LABEL_LINE_LEN: int = 22

# Высота строки текста
_LINE_HEIGHT: float = 15.0

# ----------------------------------------------------------------------
# Типы элементов BPMN
# ----------------------------------------------------------------------

_EVENT_TYPES: frozenset[str] = frozenset({
    "startEvent",
    "endEvent",
    "intermediateCatchEvent",
    "intermediateThrowEvent",
})

_TASK_TYPES: frozenset[str] = frozenset({
    "task",
    "userTask",
    "serviceTask",
    "scriptTask",
    "manualTask",
    "subProcess",
})

_GATEWAY_TYPES: frozenset[str] = frozenset({
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "eventBasedGateway",
})

# ----------------------------------------------------------------------
# CSS-стили для SVG (поддержка тёмной темы через классы)
# ----------------------------------------------------------------------

_SVG_STYLES: str = """\
  .bpmn-task {
    fill: var(--bpmn-task-fill, #ffffff);
    stroke: var(--bpmn-task-stroke, #333333);
    stroke-width: 2;
  }
  .bpmn-task-label {
    fill: var(--bpmn-label-color, #222222);
    font-family: 'Segoe UI', 'Noto Sans', Arial, sans-serif;
    font-size: 12px;
    text-anchor: middle;
    dominant-baseline: central;
  }
  .bpmn-gateway {
    fill: var(--bpmn-gateway-fill, #ffd700);
    stroke: var(--bpmn-gateway-stroke, #b8860b);
    stroke-width: 2;
  }
  .bpmn-gateway-marker {
    fill: none;
    stroke: var(--bpmn-gateway-stroke, #b8860b);
    stroke-width: 2.5;
  }
  .bpmn-gateway-marker-filled {
    fill: var(--bpmn-gateway-stroke, #b8860b);
    stroke: var(--bpmn-gateway-stroke, #b8860b);
    stroke-width: 2.5;
  }
  .bpmn-gateway-label {
    fill: var(--bpmn-label-color, #222222);
    font-family: 'Segoe UI', 'Noto Sans', Arial, sans-serif;
    font-size: 11px;
    text-anchor: middle;
    dominant-baseline: hanging;
  }
  .bpmn-start-event {
    fill: var(--bpmn-start-fill, #d4edda);
    stroke: var(--bpmn-start-stroke, #28a745);
    stroke-width: 2;
  }
  .bpmn-end-event {
    fill: var(--bpmn-end-fill, #f8d7da);
    stroke: var(--bpmn-end-stroke, #dc3545);
    stroke-width: 3.5;
  }
  .bpmn-intermediate-event {
    fill: var(--bpmn-intermediate-fill, #fff3cd);
    stroke: var(--bpmn-intermediate-stroke, #fd7e14);
    stroke-width: 2;
  }
  .bpmn-intermediate-event-inner {
    fill: none;
    stroke: var(--bpmn-intermediate-stroke, #fd7e14);
    stroke-width: 1.5;
  }
  .bpmn-event-label {
    fill: var(--bpmn-label-color, #222222);
    font-family: 'Segoe UI', 'Noto Sans', Arial, sans-serif;
    font-size: 11px;
    text-anchor: middle;
    dominant-baseline: hanging;
  }
  .bpmn-flow {
    fill: none;
    stroke: var(--bpmn-flow-stroke, #555555);
    stroke-width: 1.5;
  }
  .bpmn-flow-arrow {
    fill: var(--bpmn-flow-stroke, #555555);
    stroke: none;
  }
  .bpmn-flow-label {
    fill: var(--bpmn-label-color, #222222);
    font-family: 'Segoe UI', 'Noto Sans', Arial, sans-serif;
    font-size: 10px;
    text-anchor: middle;
    dominant-baseline: central;
  }
  .bpmn-pool {
    fill: var(--bpmn-pool-fill, #f0f4f8);
    stroke: var(--bpmn-pool-stroke, #333333);
    stroke-width: 2;
  }
  .bpmn-pool-label {
    fill: var(--bpmn-label-color, #222222);
    font-family: 'Segoe UI', 'Noto Sans', Arial, sans-serif;
    font-size: 13px;
    font-weight: bold;
    text-anchor: middle;
    dominant-baseline: central;
  }
  .bpmn-lane {
    fill: var(--bpmn-lane-fill, none);
    stroke: var(--bpmn-lane-stroke, #999999);
    stroke-width: 1;
    stroke-dasharray: 5 3;
  }
  .bpmn-lane-label {
    fill: var(--bpmn-label-color, #222222);
    font-family: 'Segoe UI', 'Noto Sans', Arial, sans-serif;
    font-size: 12px;
    font-weight: 600;
    text-anchor: middle;
    dominant-baseline: central;
  }
  .bpmn-annotation {
    fill: var(--bpmn-annotation-fill, #fffbe6);
    stroke: var(--bpmn-annotation-stroke, #bbb);
    stroke-width: 1;
  }
  .bpmn-annotation-label {
    fill: var(--bpmn-label-color, #222222);
    font-family: 'Segoe UI', 'Noto Sans', Arial, sans-serif;
    font-size: 10px;
    text-anchor: start;
    dominant-baseline: hanging;
  }
  .bpmn-data-object {
    fill: var(--bpmn-data-fill, #ffffff);
    stroke: var(--bpmn-data-stroke, #888888);
    stroke-width: 1.5;
  }
"""


# ======================================================================
# Вспомогательные функции
# ======================================================================


def _xpath(element: etree._Element, expr: str) -> list[etree._Element]:
    """Выполняет XPath-запрос с пространствами имён BPMN."""
    return element.xpath(expr, namespaces=_NS)


def _local_name(element: etree._Element) -> str:
    """Возвращает локальное имя тега без пространства имён."""
    tag: str = element.tag
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _wrap_text(text: str, max_len: int = _MAX_LABEL_LINE_LEN) -> list[str]:
    """Разбивает текст на строки длиной не более *max_len* символов.

    Перенос происходит по пробелам. Если слово длиннее лимита,
    оно разрезается принудительно.
    """
    if not text:
        return []

    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        # Если одно слово длиннее лимита — разрезаем
        while len(word) > max_len:
            chunk = word[:max_len]
            word = word[max_len:]
            if current_line:
                lines.append(current_line)
                current_line = ""
            lines.append(chunk)

        if not current_line:
            current_line = word
        elif len(current_line) + 1 + len(word) <= max_len:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def _svg_element(
    parent: etree._Element,
    tag: str,
    **attribs: str | float | int,
) -> etree._Element:
    """Создаёт дочерний SVG-элемент с указанными атрибутами."""
    str_attribs: dict[str, str] = {}
    for k, v in attribs.items():
        key = k.replace("_", "-") if k != "class_name" else "class"
        if key == "class-name":
            key = "class"
        str_attribs[key] = str(v)

    return etree.SubElement(parent, f"{{{SVG_NS}}}{tag}", attrib=str_attribs)


def _compute_arrow_points(
    x1: float, y1: float, x2: float, y2: float, size: float = _ARROW_SIZE,
) -> str:
    """Вычисляет координаты треугольника стрелки на конце линии.

    Стрелка располагается в точке (x2, y2), направлена от (x1, y1).
    """
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length < 0.001:
        return f"{x2},{y2} {x2},{y2} {x2},{y2}"

    ux = dx / length
    uy = dy / length

    # Базовые точки стрелки
    bx = x2 - ux * size
    by = y2 - uy * size

    # Перпендикуляр
    px = -uy * size * 0.4
    py = ux * size * 0.4

    p1 = f"{x2},{y2}"
    p2 = f"{bx + px},{by + py}"
    p3 = f"{bx - px},{by - py}"

    return f"{p1} {p2} {p3}"


# ======================================================================
# Основной класс
# ======================================================================


class BPMNRenderer:
    """Рендерит BPMN 2.0 XML в SVG-строку для отображения в браузере.

    Поддерживает полный набор элементов BPMN 2.0:
    - Пулы (Participant) и дорожки (Lane)
    - События: start, end, intermediate (catch/throw)
    - Задачи: task, userTask, serviceTask, scriptTask, manualTask, subProcess
    - Шлюзы: exclusive, parallel, inclusive, eventBased
    - Потоки управления (SequenceFlow) с waypoints из DI
    - Аннотации и объекты данных

    Стили вынесены в CSS-классы внутри ``<style>`` блока SVG,
    что позволяет переключать тему (светлую/тёмную) через CSS-переменные.

    Example::

        renderer = BPMNRenderer()
        svg_string = renderer.render_svg(bpmn_xml_string)
    """

    def __init__(self) -> None:
        self._converter: BpmnConverter = BpmnConverter()
        self._layout_engine: BpmnLayout = BpmnLayout()

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def render_svg(self, bpmn_xml: str) -> str:
        """Парсит BPMN 2.0 XML и рендерит его в SVG-строку.

        Args:
            bpmn_xml: Валидный BPMN 2.0 XML с секцией BPMNDiagram / DI.

        Returns:
            Строка с SVG-изображением BPMN-диаграммы.

        Raises:
            ExportError: Если парсинг или рендеринг завершился неудачно.
        """
        try:
            tree = etree.fromstring(bpmn_xml.encode("utf-8"))
        except etree.XMLSyntaxError as exc:
            logger.error("Ошибка парсинга BPMN XML: %s", exc)
            raise ExportError(
                "Не удалось разобрать BPMN XML",
                detail=str(exc),
            ) from exc

        try:
            return self._render(tree)
        except ExportError:
            raise
        except Exception as exc:
            logger.exception("Ошибка рендеринга BPMN в SVG: %s", exc)
            raise ExportError(
                "Ошибка при рендеринге BPMN в SVG",
                detail=str(exc),
            ) from exc

    def render_from_json(self, bpmn_json: dict[str, Any]) -> str:
        """Конвертирует BPMN JSON → XML → SVG за один вызов.

        Сначала вычисляется layout, затем JSON конвертируется в XML,
        после чего XML рендерится в SVG.

        Args:
            bpmn_json: Словарь с описанием BPMN-процесса (формат
                ``BpmnConverter.convert``).

        Returns:
            SVG-строка.

        Raises:
            ExportError: Если конвертация или рендеринг не удались.
        """
        try:
            # Вычислить layout, если его нет
            if "layout" not in bpmn_json or not bpmn_json["layout"]:
                layout = self._layout_engine.calculate_layout(bpmn_json)
                bpmn_json = {**bpmn_json, "layout": layout}

            bpmn_xml: str = self._converter.convert(bpmn_json)
            return self.render_svg(bpmn_xml)
        except ExportError:
            raise
        except Exception as exc:
            logger.exception(
                "Ошибка конвертации JSON → SVG: %s", exc,
            )
            raise ExportError(
                "Ошибка при конвертации BPMN JSON в SVG",
                detail=str(exc),
            ) from exc

    # ------------------------------------------------------------------
    # Внутренняя логика рендеринга
    # ------------------------------------------------------------------

    def _render(self, definitions: etree._Element) -> str:
        """Рендерит дерево ``<definitions>`` в SVG-строку."""
        BPMNRenderer._clip_counter = 0
        # Индекс bpmnElement -> локальное имя тега процесса
        bpmn_element_types: dict[str, str] = self._index_bpmn_elements(
            definitions,
        )
        # Индекс bpmnElement -> name
        bpmn_element_names: dict[str, str] = self._index_bpmn_names(
            definitions,
        )

        # Находим BPMNPlane
        planes = _xpath(definitions, ".//bpmndi:BPMNPlane")
        if not planes:
            logger.warning("BPMN XML не содержит BPMNPlane, SVG будет пустым")
            return self._empty_svg()

        plane = planes[0]

        # Собираем shapes и edges
        shapes: list[etree._Element] = _xpath(plane, "bpmndi:BPMNShape")
        edges: list[etree._Element] = _xpath(plane, "bpmndi:BPMNEdge")

        # Собираем все bounds для вычисления viewBox
        all_bounds: list[tuple[float, float, float, float]] = []

        # Предварительно парсим shapes
        parsed_shapes: list[dict[str, Any]] = []
        for shape in shapes:
            parsed = self._parse_shape(shape, bpmn_element_types, bpmn_element_names)
            if parsed:
                parsed_shapes.append(parsed)
                x = parsed["x"]
                y = parsed["y"]
                w = parsed["width"]
                h = parsed["height"]
                all_bounds.append((x, y, x + w, y + h))

        # Предварительно парсим edges
        parsed_edges: list[dict[str, Any]] = []
        for edge in edges:
            parsed = self._parse_edge(edge, bpmn_element_names)
            if parsed:
                parsed_edges.append(parsed)
                for wp in parsed["waypoints"]:
                    all_bounds.append((wp[0], wp[1], wp[0], wp[1]))

        if not all_bounds:
            return self._empty_svg()

        # viewBox
        min_x = min(b[0] for b in all_bounds) - _PADDING
        min_y = min(b[1] for b in all_bounds) - _PADDING
        max_x = max(b[2] for b in all_bounds) + _PADDING
        max_y = max(b[3] for b in all_bounds) + _PADDING
        vb_width = max_x - min_x
        vb_height = max_y - min_y

        # Создаём SVG root
        svg_root = self._create_svg_root(min_x, min_y, vb_width, vb_height)

        # Добавляем маркер стрелки в <defs>
        self._add_defs(svg_root)

        # Рисуем: сначала пулы/дорожки (фон), потом задачи/события, потом потоки
        pools: list[dict[str, Any]] = []
        lanes: list[dict[str, Any]] = []
        flow_nodes: list[dict[str, Any]] = []

        for ps in parsed_shapes:
            elem_type = ps.get("bpmn_type", "")
            if elem_type == "participant":
                pools.append(ps)
            elif elem_type == "lane":
                lanes.append(ps)
            else:
                flow_nodes.append(ps)

        # 1. Пулы (фон)
        for pool in pools:
            self._draw_pool(svg_root, pool)

        # 2. Дорожки
        for lane in lanes:
            self._draw_lane(svg_root, lane)

        # 3. Потоки (стрелки) — рисуем под элементами, чтобы стрелки не
        #    перекрывали фигуры. Метки потоков рисуем поверх.
        flow_labels_group = _svg_element(svg_root, "g", class_name="bpmn-flows")
        for pe in parsed_edges:
            self._draw_flow(flow_labels_group, pe)

        # 4. Элементы процесса (задачи, события, шлюзы)
        for node in flow_nodes:
            self._draw_shape(svg_root, node)

        # Сериализация
        svg_bytes: bytes = etree.tostring(
            svg_root,
            xml_declaration=True,
            encoding="UTF-8",
            pretty_print=True,
        )
        return svg_bytes.decode("utf-8")

    # ------------------------------------------------------------------
    # Индексирование элементов BPMN-модели
    # ------------------------------------------------------------------

    @staticmethod
    def _index_bpmn_elements(
        definitions: etree._Element,
    ) -> dict[str, str]:
        """Строит индекс ``{id -> localTagName}`` для всех элементов процесса,
        участников и дорожек.
        """
        index: dict[str, str] = {}

        # Участники (collaboration/participant)
        for part in _xpath(definitions, ".//bpmn:participant"):
            pid = part.get("id", "")
            if pid:
                index[pid] = "participant"

        # Процесс и вложенные элементы
        for process in _xpath(definitions, ".//bpmn:process"):
            _index_children_recursive(process, index)

        return index

    @staticmethod
    def _index_bpmn_names(
        definitions: etree._Element,
    ) -> dict[str, str]:
        """Строит индекс ``{id -> name}`` для всех именованных элементов."""
        index: dict[str, str] = {}

        for elem in definitions.iter():
            eid = elem.get("id", "")
            name = elem.get("name", "")
            if eid:
                index[eid] = name

        return index

    # ------------------------------------------------------------------
    # Парсинг DI-элементов
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_shape(
        shape: etree._Element,
        type_index: dict[str, str],
        name_index: dict[str, str],
    ) -> dict[str, Any] | None:
        """Парсит ``<BPMNShape>`` и возвращает словарь с координатами."""
        bpmn_element = shape.get("bpmnElement", "")
        if not bpmn_element:
            return None

        bounds_list = _xpath(shape, "dc:Bounds")
        if not bounds_list:
            return None

        bounds = bounds_list[0]
        try:
            x = float(bounds.get("x", "0"))
            y = float(bounds.get("y", "0"))
            w = float(bounds.get("width", "100"))
            h = float(bounds.get("height", "80"))
        except (ValueError, TypeError):
            logger.warning(
                "Невалидные координаты для BPMNShape bpmnElement=%s",
                bpmn_element,
            )
            return None

        bpmn_type = type_index.get(bpmn_element, "task")
        name = name_index.get(bpmn_element, "")

        # Проверяем isHorizontal для дорожек
        is_horizontal = shape.get("isHorizontal", "false").lower() == "true"

        # Метка (BPMNLabel)
        label_bounds: dict[str, float] | None = None
        label_nodes = _xpath(shape, "bpmndi:BPMNLabel/dc:Bounds")
        if label_nodes:
            lb = label_nodes[0]
            try:
                label_bounds = {
                    "x": float(lb.get("x", "0")),
                    "y": float(lb.get("y", "0")),
                    "width": float(lb.get("width", "100")),
                    "height": float(lb.get("height", "20")),
                }
            except (ValueError, TypeError) as exc:
                logger.debug("Не удалось распарсить label bounds для %s: %s", bpmn_element, exc)

        return {
            "bpmn_element": bpmn_element,
            "bpmn_type": bpmn_type,
            "name": name,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "is_horizontal": is_horizontal,
            "label_bounds": label_bounds,
        }

    @staticmethod
    def _parse_edge(
        edge: etree._Element,
        name_index: dict[str, str],
    ) -> dict[str, Any] | None:
        """Парсит ``<BPMNEdge>`` и возвращает словарь с waypoints."""
        bpmn_element = edge.get("bpmnElement", "")
        if not bpmn_element:
            return None

        waypoints: list[tuple[float, float]] = []
        for wp in _xpath(edge, "di:waypoint"):
            try:
                wx = float(wp.get("x", "0"))
                wy = float(wp.get("y", "0"))
                waypoints.append((wx, wy))
            except (ValueError, TypeError) as exc:
                logger.debug("Не удалось распарсить waypoint: %s", exc)
                continue

        if len(waypoints) < 2:
            return None

        name = name_index.get(bpmn_element, "")

        return {
            "bpmn_element": bpmn_element,
            "name": name,
            "waypoints": waypoints,
        }

    # ------------------------------------------------------------------
    # Создание SVG-корня
    # ------------------------------------------------------------------

    @staticmethod
    def _create_svg_root(
        min_x: float,
        min_y: float,
        width: float,
        height: float,
    ) -> etree._Element:
        """Создаёт корневой элемент ``<svg>`` с viewBox и стилями."""
        nsmap: dict[str | None, str] = {
            None: SVG_NS,
            "xlink": XLINK_NS,
        }

        root = etree.Element(
            f"{{{SVG_NS}}}svg",
            nsmap=nsmap,
            attrib={
                "viewBox": f"{min_x:.1f} {min_y:.1f} {width:.1f} {height:.1f}",
                "width": f"{width:.0f}",
                "height": f"{height:.0f}",
                "preserveAspectRatio": "xMidYMid meet",
            },
        )

        # Внедряем CSS-стили
        style = etree.SubElement(root, f"{{{SVG_NS}}}style")
        style.text = _SVG_STYLES

        return root

    @staticmethod
    def _add_defs(svg_root: etree._Element) -> None:
        """Добавляет ``<defs>`` с маркером стрелки."""
        defs = _svg_element(svg_root, "defs")

        marker = _svg_element(
            defs,
            "marker",
            id="arrowhead",
            markerWidth="10",
            markerHeight="7",
            refX="10",
            refY="3.5",
            orient="auto",
            markerUnits="strokeWidth",
        )
        _svg_element(
            marker,
            "polygon",
            points="0 0, 10 3.5, 0 7",
            class_name="bpmn-flow-arrow",
        )

    # ------------------------------------------------------------------
    # Отрисовка пулов
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_pool(parent: etree._Element, pool: dict[str, Any]) -> None:
        """Рисует пул (горизонтальная полоса с названием)."""
        x = pool["x"]
        y = pool["y"]
        w = pool["width"]
        h = pool["height"]
        name = pool.get("name", "")

        g = _svg_element(parent, "g", class_name="bpmn-pool-group")

        _svg_element(
            g, "rect",
            x=f"{x:.1f}",
            y=f"{y:.1f}",
            width=f"{w:.1f}",
            height=f"{h:.1f}",
            rx="0",
            ry="0",
            class_name="bpmn-pool",
        )

        if name:
            # Вертикальная метка в левой части пула
            label_x = x + 15
            label_y = y + h / 2

            text_elem = _svg_element(
                g, "text",
                x=f"{label_x:.1f}",
                y=f"{label_y:.1f}",
                class_name="bpmn-pool-label",
                transform=f"rotate(-90, {label_x:.1f}, {label_y:.1f})",
            )
            text_elem.text = name

    # ------------------------------------------------------------------
    # Отрисовка дорожек
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_lane(parent: etree._Element, lane: dict[str, Any]) -> None:
        """Рисует дорожку (swimlane) с пунктирной границей."""
        x = lane["x"]
        y = lane["y"]
        w = lane["width"]
        h = lane["height"]
        name = lane.get("name", "")

        g = _svg_element(parent, "g", class_name="bpmn-lane-group")

        _svg_element(
            g, "rect",
            x=f"{x:.1f}",
            y=f"{y:.1f}",
            width=f"{w:.1f}",
            height=f"{h:.1f}",
            class_name="bpmn-lane",
        )

        if name:
            # Вертикальная метка в левой части дорожки
            label_x = x + 15
            label_y = y + h / 2

            text_elem = _svg_element(
                g, "text",
                x=f"{label_x:.1f}",
                y=f"{label_y:.1f}",
                class_name="bpmn-lane-label",
                transform=f"rotate(-90, {label_x:.1f}, {label_y:.1f})",
            )
            text_elem.text = name

    # ------------------------------------------------------------------
    # Отрисовка элементов процесса
    # ------------------------------------------------------------------

    def _draw_shape(self, parent: etree._Element, shape: dict[str, Any]) -> None:
        """Рисует элемент процесса в зависимости от его типа."""
        bpmn_type: str = shape.get("bpmn_type", "task")

        if bpmn_type in _EVENT_TYPES:
            self._draw_event(parent, shape)
        elif bpmn_type in _GATEWAY_TYPES:
            self._draw_gateway(parent, shape)
        elif bpmn_type == "textAnnotation":
            self._draw_annotation(parent, shape)
        elif bpmn_type in ("dataObject", "dataStore"):
            self._draw_data_object(parent, shape)
        else:
            # Task и подобные
            self._draw_task(parent, shape)

    # --- Задачи (Task) ---

    _clip_counter: int = 0

    @classmethod
    def _draw_task(cls, parent: etree._Element, shape: dict[str, Any]) -> None:
        """Рисует задачу — прямоугольник со скруглёнными углами и текстом."""
        x = shape["x"]
        y = shape["y"]
        w = shape["width"]
        h = shape["height"]
        name = shape.get("name", "")

        g = _svg_element(parent, "g", class_name="bpmn-task-group")

        _svg_element(
            g, "rect",
            x=f"{x:.1f}",
            y=f"{y:.1f}",
            width=f"{w:.1f}",
            height=f"{h:.1f}",
            rx="8",
            ry="8",
            class_name="bpmn-task",
        )

        if name:
            # Clip text to task bounds
            cls._clip_counter += 1
            clip_id = f"clip-task-{cls._clip_counter}"
            defs = g.getparent()
            # Find or create defs
            svg_root = defs
            while svg_root.getparent() is not None:
                svg_root = svg_root.getparent()
            defs_el = svg_root.find(f"{{{SVG_NS}}}defs")
            if defs_el is not None:
                clip_path = _svg_element(defs_el, "clipPath", id=clip_id)
                _svg_element(
                    clip_path, "rect",
                    x=f"{x + 2:.1f}",
                    y=f"{y + 2:.1f}",
                    width=f"{w - 4:.1f}",
                    height=f"{h - 4:.1f}",
                    rx="6",
                    ry="6",
                )

            # Расчёт максимальной ширины строки в символах
            # ≈6px на кириллический символ при 11px font-size
            max_chars = max(8, int(w / 6.5))
            lines = _wrap_text(name, max_len=max_chars)

            # Ограничиваем количество строк: используем всю высоту задачи.
            # clipPath обрезает текст визуально — "…" не добавляем,
            # чтобы избежать артефактов в SVG-превью.
            max_lines = max(4, int(h / _LINE_HEIGHT))
            if len(lines) > max_lines:
                lines = lines[:max_lines]

            cx = x + w / 2
            cy = y + h / 2
            total_height = len(lines) * _LINE_HEIGHT
            start_y = cy - total_height / 2 + _LINE_HEIGHT / 2

            text_group = _svg_element(g, "g")
            if defs_el is not None:
                text_group.set("clip-path", f"url(#{clip_id})")

            for i, line in enumerate(lines):
                text_elem = _svg_element(
                    text_group, "text",
                    x=f"{cx:.1f}",
                    y=f"{start_y + i * _LINE_HEIGHT:.1f}",
                    class_name="bpmn-task-label",
                )
                text_elem.text = line

    # --- События (Event) ---

    @staticmethod
    def _draw_event(parent: etree._Element, shape: dict[str, Any]) -> None:
        """Рисует событие — круг с соответствующим стилем."""
        x = shape["x"]
        y = shape["y"]
        w = shape["width"]
        h = shape["height"]
        name = shape.get("name", "")
        bpmn_type = shape.get("bpmn_type", "startEvent")

        cx = x + w / 2
        cy = y + h / 2
        r = min(w, h) / 2

        g = _svg_element(parent, "g", class_name=f"bpmn-event-group bpmn-{bpmn_type}")

        # Определяем CSS-класс
        if bpmn_type == "startEvent":
            css_class = "bpmn-start-event"
        elif bpmn_type == "endEvent":
            css_class = "bpmn-end-event"
        else:
            css_class = "bpmn-intermediate-event"

        _svg_element(
            g, "circle",
            cx=f"{cx:.1f}",
            cy=f"{cy:.1f}",
            r=f"{r:.1f}",
            class_name=css_class,
        )

        # Для промежуточных событий — внутренний круг
        if bpmn_type in ("intermediateCatchEvent", "intermediateThrowEvent"):
            inner_r = r * 0.78
            _svg_element(
                g, "circle",
                cx=f"{cx:.1f}",
                cy=f"{cy:.1f}",
                r=f"{inner_r:.1f}",
                class_name="bpmn-intermediate-event-inner",
            )

        # Метка под событием
        if name:
            label_y = y + h + 5
            label_bounds = shape.get("label_bounds")
            if label_bounds:
                label_x = label_bounds["x"] + label_bounds["width"] / 2
                label_y = label_bounds["y"]
            else:
                label_x = cx

            lines = _wrap_text(name, max_len=16)
            for i, line in enumerate(lines):
                text_elem = _svg_element(
                    g, "text",
                    x=f"{label_x:.1f}",
                    y=f"{label_y + i * _LINE_HEIGHT:.1f}",
                    class_name="bpmn-event-label",
                )
                text_elem.text = line

    # --- Шлюзы (Gateway) ---

    @staticmethod
    def _draw_gateway(parent: etree._Element, shape: dict[str, Any]) -> None:
        """Рисует шлюз — ромб с маркером типа."""
        x = shape["x"]
        y = shape["y"]
        w = shape["width"]
        h = shape["height"]
        name = shape.get("name", "")
        bpmn_type = shape.get("bpmn_type", "exclusiveGateway")

        cx = x + w / 2
        cy = y + h / 2
        half_w = w / 2
        half_h = h / 2

        g = _svg_element(parent, "g", class_name=f"bpmn-gateway-group bpmn-{bpmn_type}")

        # Ромб
        points = (
            f"{cx:.1f},{y:.1f} "
            f"{x + w:.1f},{cy:.1f} "
            f"{cx:.1f},{y + h:.1f} "
            f"{x:.1f},{cy:.1f}"
        )
        _svg_element(
            g, "polygon",
            points=points,
            class_name="bpmn-gateway",
        )

        # Маркер внутри ромба
        marker_size = min(half_w, half_h) * 0.45

        if bpmn_type == "exclusiveGateway":
            # X-крест
            _svg_element(
                g, "line",
                x1=f"{cx - marker_size:.1f}",
                y1=f"{cy - marker_size:.1f}",
                x2=f"{cx + marker_size:.1f}",
                y2=f"{cy + marker_size:.1f}",
                class_name="bpmn-gateway-marker",
            )
            _svg_element(
                g, "line",
                x1=f"{cx + marker_size:.1f}",
                y1=f"{cy - marker_size:.1f}",
                x2=f"{cx - marker_size:.1f}",
                y2=f"{cy + marker_size:.1f}",
                class_name="bpmn-gateway-marker",
            )
        elif bpmn_type == "parallelGateway":
            # + крест
            _svg_element(
                g, "line",
                x1=f"{cx:.1f}",
                y1=f"{cy - marker_size:.1f}",
                x2=f"{cx:.1f}",
                y2=f"{cy + marker_size:.1f}",
                class_name="bpmn-gateway-marker",
            )
            _svg_element(
                g, "line",
                x1=f"{cx - marker_size:.1f}",
                y1=f"{cy:.1f}",
                x2=f"{cx + marker_size:.1f}",
                y2=f"{cy:.1f}",
                class_name="bpmn-gateway-marker",
            )
        elif bpmn_type == "inclusiveGateway":
            # Круг (не заполненный)
            _svg_element(
                g, "circle",
                cx=f"{cx:.1f}",
                cy=f"{cy:.1f}",
                r=f"{marker_size:.1f}",
                class_name="bpmn-gateway-marker",
            )
        elif bpmn_type == "eventBasedGateway":
            # Пятиугольник (пентагон) внутри
            pentagon_r = marker_size * 0.85
            pentagon_points_list: list[str] = []
            for i in range(5):
                angle = -math.pi / 2 + i * 2 * math.pi / 5
                px = cx + pentagon_r * math.cos(angle)
                py = cy + pentagon_r * math.sin(angle)
                pentagon_points_list.append(f"{px:.1f},{py:.1f}")
            _svg_element(
                g, "polygon",
                points=" ".join(pentagon_points_list),
                class_name="bpmn-gateway-marker",
            )

        # Метка шлюза — ВЫШЕ ромба (симметрично с VSDX)
        if name:
            label_bounds = shape.get("label_bounds")
            if label_bounds:
                # Если в BPMN есть явные bounds для label — используем их
                label_x = label_bounds["x"] + label_bounds["width"] / 2
                label_y = label_bounds["y"]
                lines = _wrap_text(name, max_len=20)
                for i, line in enumerate(lines):
                    text_elem = _svg_element(
                        g, "text",
                        x=f"{label_x:.1f}",
                        y=f"{label_y + i * _LINE_HEIGHT:.1f}",
                        class_name="bpmn-gateway-label",
                    )
                    text_elem.text = line
            else:
                # Размещаем ВЫШЕ шлюза: 20px для текста на каждую строку
                # max_len=20 символов → умещается в ширину ~120px
                lines = _wrap_text(name, max_len=20)
                # Сколько строк: рисуем снизу вверх от y - 4
                total_h = len(lines) * _LINE_HEIGHT
                start_y = y - 4 - total_h + _LINE_HEIGHT
                for i, line in enumerate(lines):
                    text_elem = _svg_element(
                        g, "text",
                        x=f"{cx:.1f}",
                        y=f"{start_y + i * _LINE_HEIGHT:.1f}",
                        class_name="bpmn-gateway-label",
                    )
                    text_elem.text = line

    # --- Аннотации ---

    @staticmethod
    def _draw_annotation(
        parent: etree._Element, shape: dict[str, Any],
    ) -> None:
        """Рисует текстовую аннотацию."""
        x = shape["x"]
        y = shape["y"]
        w = shape["width"]
        h = shape["height"]
        name = shape.get("name", "")

        g = _svg_element(parent, "g", class_name="bpmn-annotation-group")

        _svg_element(
            g, "rect",
            x=f"{x:.1f}",
            y=f"{y:.1f}",
            width=f"{w:.1f}",
            height=f"{h:.1f}",
            class_name="bpmn-annotation",
        )

        # Левая скобка
        bracket_points = (
            f"{x + 10:.1f},{y:.1f} "
            f"{x:.1f},{y:.1f} "
            f"{x:.1f},{y + h:.1f} "
            f"{x + 10:.1f},{y + h:.1f}"
        )
        _svg_element(
            g, "polyline",
            points=bracket_points,
            fill="none",
            stroke="var(--bpmn-annotation-stroke, #bbb)",
        )

        if name:
            text_elem = _svg_element(
                g, "text",
                x=f"{x + 14:.1f}",
                y=f"{y + 6:.1f}",
                class_name="bpmn-annotation-label",
            )
            text_elem.text = name

    # --- Объекты данных ---

    @staticmethod
    def _draw_data_object(
        parent: etree._Element, shape: dict[str, Any],
    ) -> None:
        """Рисует объект данных (свёрнутый уголок)."""
        x = shape["x"]
        y = shape["y"]
        w = shape["width"]
        h = shape["height"]
        name = shape.get("name", "")

        g = _svg_element(parent, "g", class_name="bpmn-data-group")

        fold = min(w, h) * 0.25
        path_d = (
            f"M {x:.1f},{y:.1f} "
            f"L {x + w - fold:.1f},{y:.1f} "
            f"L {x + w:.1f},{y + fold:.1f} "
            f"L {x + w:.1f},{y + h:.1f} "
            f"L {x:.1f},{y + h:.1f} Z"
        )
        _svg_element(
            g, "path",
            d=path_d,
            class_name="bpmn-data-object",
        )

        # Линия загиба
        fold_path = (
            f"M {x + w - fold:.1f},{y:.1f} "
            f"L {x + w - fold:.1f},{y + fold:.1f} "
            f"L {x + w:.1f},{y + fold:.1f}"
        )
        _svg_element(
            g, "path",
            d=fold_path,
            fill="none",
            stroke="var(--bpmn-data-stroke, #888888)",
        )

        if name:
            text_elem = _svg_element(
                g, "text",
                x=f"{x + w / 2:.1f}",
                y=f"{y + h + 14:.1f}",
                class_name="bpmn-event-label",
            )
            text_elem.text = name

    # ------------------------------------------------------------------
    # Отрисовка потоков (Sequence Flow)
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_flow(parent: etree._Element, edge: dict[str, Any]) -> None:
        """Рисует поток управления — ломаную линию со стрелкой."""
        waypoints: list[tuple[float, float]] = edge["waypoints"]
        name = edge.get("name", "")

        if len(waypoints) < 2:
            return

        g = _svg_element(parent, "g", class_name="bpmn-flow-group")

        # Полилиния
        points_str = " ".join(f"{wp[0]:.1f},{wp[1]:.1f}" for wp in waypoints)
        _svg_element(
            g, "polyline",
            points=points_str,
            class_name="bpmn-flow",
            marker_end="url(#arrowhead)",
        )

        # Метка потока (на середине)
        if name:
            mid_idx = len(waypoints) // 2
            if mid_idx > 0:
                mx = (waypoints[mid_idx - 1][0] + waypoints[mid_idx][0]) / 2
                my = (waypoints[mid_idx - 1][1] + waypoints[mid_idx][1]) / 2
            else:
                mx = waypoints[0][0]
                my = waypoints[0][1]

            # Фоновый прямоугольник для читаемости
            label_w = len(name) * 6 + 8
            label_h = 16
            _svg_element(
                g, "rect",
                x=f"{mx - label_w / 2:.1f}",
                y=f"{my - label_h / 2:.1f}",
                width=f"{label_w:.1f}",
                height=f"{label_h:.1f}",
                fill="var(--bpmn-task-fill, #ffffff)",
                stroke="none",
                rx="3",
                ry="3",
                opacity="0.85",
            )

            text_elem = _svg_element(
                g, "text",
                x=f"{mx:.1f}",
                y=f"{my:.1f}",
                class_name="bpmn-flow-label",
            )
            text_elem.text = name

    # ------------------------------------------------------------------
    # Пустой SVG
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_svg() -> str:
        """Возвращает минимальный пустой SVG."""
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 200 100" width="200" height="100">'
            '<text x="100" y="50" text-anchor="middle" '
            'dominant-baseline="central" '
            'font-family="sans-serif" font-size="12" '
            'fill="#999">Нет данных для отображения</text>'
            "</svg>"
        )


# ======================================================================
# Вспомогательная рекурсивная индексация
# ======================================================================


def _index_children_recursive(
    parent: etree._Element,
    index: dict[str, str],
) -> None:
    """Рекурсивно индексирует дочерние элементы процесса/подпроцесса."""
    for child in parent:
        local = _local_name(child)
        eid = child.get("id", "")
        if eid:
            index[eid] = local

        # Рекурсия для laneSet, lane, subProcess
        if local in ("laneSet", "lane", "subProcess"):
            _index_children_recursive(child, index)
