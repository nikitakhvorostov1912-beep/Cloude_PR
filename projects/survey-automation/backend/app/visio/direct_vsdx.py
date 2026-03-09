"""Прямая генерация .vsdx файлов из BPMN JSON — стиль Bitrix24.

Создаёт профессиональные Visio-диаграммы в стиле Bitrix24:
- Дорожки с широкими тёмными заголовками и светлым цветным фоном
- Задачи: белый фон + тонкая цветная полоса слева + иконка роли
- События: геометрические BPMN-фигуры (без emoji)
- Шлюзы: жёлтый ромб + метка вопроса выше + да/нет на ветках
- Соединители: серые стрелки с таблетками подписей

Все тексты на русском языке.
"""

from __future__ import annotations

import logging
import math
import unicodedata
import uuid
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from app.exceptions import ExportError
from app.visio.template_creator import create_bpmn_vsdx

logger = logging.getLogger(__name__)

# Константы конвертации
PIXELS_PER_INCH = 96.0

# ──────────────────────────────────────────────────────────────────────
# Цветовая палитра дорожек (стиль Bitrix24)
# Каждая запись: (bg_fill, accent_color, dark_header, border_color)
# ──────────────────────────────────────────────────────────────────────
LANE_PALETTE_V2: list[tuple[str, str, str, str]] = [
    ("#EEF2FA", "#4472C4", "#2B5091", "#C5D3E8"),  # Синий
    ("#EEF5EE", "#4CAF50", "#2E7D32", "#C3DFC3"),  # Зелёный
    ("#FFF8E7", "#F9A825", "#F57F17", "#F0DAAA"),  # Жёлтый
    ("#FEF0EE", "#E53935", "#B71C1C", "#F0C4C2"),  # Красный
    ("#F3EEF9", "#7B1FA2", "#4A148C", "#D4BEDF"),  # Фиолетовый
    ("#E8F8F8", "#00796B", "#004D40", "#B0D5D2"),  # Бирюзовый
    ("#FFF3E0", "#E65100", "#BF360C", "#F0C89A"),  # Оранжевый
]

# ──────────────────────────────────────────────────────────────────────
# Константы стиля
# ──────────────────────────────────────────────────────────────────────
_LANE_HEADER_W: float = 0.70       # ширина заголовка дорожки (дюймы)
_ACCENT_BAR_W: float = 0.069       # ширина акцент-полосы задачи (5pt)
_TASK_FILL = "#FFFFFF"             # белый фон задачи
_TASK_BORDER = "#CBD4E1"           # светло-серая граница задачи
_TASK_TEXT = "#1A202C"             # почти чёрный текст задачи
_TASK_ROUND = 0.0833               # скругление (6pt)
_CONNECTOR_LINE = "#5A6475"        # цвет соединителей
_GATEWAY_FILL = "#FFF8E7"          # заливка шлюза
_GATEWAY_LINE = "#F9A825"          # граница шлюза
_GATEWAY_LW = 0.0208               # 1.5pt для шлюза
_LABEL_TEXT_COLOR = "#5A6475"      # цвет подписей
_EVENT_START_FILL = "#F1FAF1"
_EVENT_START_LINE = "#43A047"
_EVENT_END_FILL = "#FFF0EE"
_EVENT_END_LINE = "#E53935"
_EVENT_TIMER_FILL = "#FFFDE7"
_EVENT_TIMER_LINE = "#F9A825"
_EVENT_CANCEL_FILL = "#FFF0EE"
_EVENT_CANCEL_LINE = "#E53935"


# ──────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _clean_text(text: str) -> str:
    """Убирает артефакты усечения ('…', '...') из текста."""
    if not text:
        return text
    t = text.strip()
    while t.endswith("…") or t.endswith("..."):
        t = t.rstrip(".…").strip()
    return t


def _px(val: float) -> float:
    """Конвертирует пиксели BPMN DI в дюймы Visio."""
    return val / PIXELS_PER_INCH


def _visual_text_width(text: str, char_coeff: float = 0.085) -> float:
    """Оценивает визуальную ширину текста в дюймах."""
    visual_units = 0.0
    for ch in text:
        cat = unicodedata.category(ch)
        cp = ord(ch)
        if cat in ("So", "Sk") or cp > 0x1F000:
            visual_units += 2.0
        elif ch == " ":
            visual_units += 0.5
        else:
            visual_units += 1.0
    return visual_units * char_coeff


def _vis_color(hex_color: str) -> str:
    """Возвращает цвет для .vsdx XML."""
    if not hex_color.startswith("#"):
        return f"#{hex_color}"
    return hex_color


def _shape_base(
    sid: int,
    cx: float, cy: float,
    w: float, h: float,
    name: str = "",
) -> str:
    """Общая XML-основа фигуры: позиционирование с GUARD()."""
    nu = f'NameU="{xml_escape(name)}"' if name else f'NameU="Shape.{sid}"'
    return (
        f'    <Shape ID="{sid}" {nu} Type="Shape"'
        f' LineStyle="0" FillStyle="0" TextStyle="0">\n'
        f'      <Cell N="PinX" V="{cx:.4f}"/>\n'
        f'      <Cell N="PinY" V="{cy:.4f}"/>\n'
        f'      <Cell N="Width" V="{w:.4f}" F="GUARD({w:.4f})"/>\n'
        f'      <Cell N="Height" V="{h:.4f}" F="GUARD({h:.4f})"/>\n'
        f'      <Cell N="LocPinX" V="{w / 2:.4f}" F="GUARD(Width*0.5)"/>\n'
        f'      <Cell N="LocPinY" V="{h / 2:.4f}" F="GUARD(Height*0.5)"/>\n'
        f'      <Cell N="Angle" V="0"/>\n'
        f'      <Cell N="FlipX" V="0"/>\n'
        f'      <Cell N="FlipY" V="0"/>\n'
        f'      <Cell N="ResizeMode" V="0"/>\n'
        f'      <Cell N="ShapeFixedCode" V="6"/>\n'
    )


# ──────────────────────────────────────────────────────────────────────
# Геометрия примитивов
# ──────────────────────────────────────────────────────────────────────

GEOM_RECT = (
    '      <Section N="Geometry" IX="0">\n'
    '        <Cell N="NoFill" V="0"/>\n'
    '        <Cell N="NoLine" V="0"/>\n'
    '        <Cell N="NoShow" V="0"/>\n'
    '        <Cell N="NoSnap" V="0"/>\n'
    '        <Cell N="NoQuickDrag" V="0"/>\n'
    '        <Row T="RelMoveTo" IX="1"><Cell N="X" V="0"/><Cell N="Y" V="0"/></Row>\n'
    '        <Row T="RelLineTo" IX="2"><Cell N="X" V="1"/><Cell N="Y" V="0"/></Row>\n'
    '        <Row T="RelLineTo" IX="3"><Cell N="X" V="1"/><Cell N="Y" V="1"/></Row>\n'
    '        <Row T="RelLineTo" IX="4"><Cell N="X" V="0"/><Cell N="Y" V="1"/></Row>\n'
    '        <Row T="RelLineTo" IX="5"><Cell N="X" V="0"/><Cell N="Y" V="0"/></Row>\n'
    '      </Section>\n'
)

GEOM_DIAMOND = (
    '      <Section N="Geometry" IX="0">\n'
    '        <Cell N="NoFill" V="0"/>\n'
    '        <Cell N="NoLine" V="0"/>\n'
    '        <Cell N="NoShow" V="0"/>\n'
    '        <Cell N="NoSnap" V="0"/>\n'
    '        <Cell N="NoQuickDrag" V="0"/>\n'
    '        <Row T="RelMoveTo" IX="1"><Cell N="X" V="0.5"/><Cell N="Y" V="0"/></Row>\n'
    '        <Row T="RelLineTo" IX="2"><Cell N="X" V="1"/><Cell N="Y" V="0.5"/></Row>\n'
    '        <Row T="RelLineTo" IX="3"><Cell N="X" V="0.5"/><Cell N="Y" V="1"/></Row>\n'
    '        <Row T="RelLineTo" IX="4"><Cell N="X" V="0"/><Cell N="Y" V="0.5"/></Row>\n'
    '        <Row T="RelLineTo" IX="5"><Cell N="X" V="0.5"/><Cell N="Y" V="0"/></Row>\n'
    '      </Section>\n'
)

# Геометрия треугольника-play (▶) для startEvent
GEOM_PLAY = (
    '      <Section N="Geometry" IX="0">\n'
    '        <Cell N="NoFill" V="0"/>\n'
    '        <Cell N="NoLine" V="1"/>\n'
    '        <Cell N="NoShow" V="0"/>\n'
    '        <Cell N="NoSnap" V="0"/>\n'
    '        <Cell N="NoQuickDrag" V="0"/>\n'
    '        <Row T="RelMoveTo" IX="1"><Cell N="X" V="0.18"/><Cell N="Y" V="0.80"/></Row>\n'
    '        <Row T="RelLineTo" IX="2"><Cell N="X" V="0.82"/><Cell N="Y" V="0.50"/></Row>\n'
    '        <Row T="RelLineTo" IX="3"><Cell N="X" V="0.18"/><Cell N="Y" V="0.20"/></Row>\n'
    '        <Row T="RelLineTo" IX="4"><Cell N="X" V="0.18"/><Cell N="Y" V="0.80"/></Row>\n'
    '      </Section>\n'
)

# Геометрия квадрата-terminate для endEvent (центрированный внутри circle)
GEOM_SQUARE_INNER = (
    '      <Section N="Geometry" IX="0">\n'
    '        <Cell N="NoFill" V="0"/>\n'
    '        <Cell N="NoLine" V="1"/>\n'
    '        '
    '<Row T="RelMoveTo" IX="1"><Cell N="X" V="0.20"/><Cell N="Y" V="0.20"/></Row>\n'
    '        <Row T="RelLineTo" IX="2"><Cell N="X" V="0.80"/><Cell N="Y" V="0.20"/></Row>\n'
    '        <Row T="RelLineTo" IX="3"><Cell N="X" V="0.80"/><Cell N="Y" V="0.80"/></Row>\n'
    '        <Row T="RelLineTo" IX="4"><Cell N="X" V="0.20"/><Cell N="Y" V="0.80"/></Row>\n'
    '        <Row T="RelLineTo" IX="5"><Cell N="X" V="0.20"/><Cell N="Y" V="0.20"/></Row>\n'
    '      </Section>\n'
)


def _geom_ellipse(w: float, h: float | None = None) -> str:
    """Геометрия эллипса/круга для Visio.

    w = ширина (diameter для круга)
    h = высота (если None — круг, h=w)
    """
    if h is None:
        h = w
    rx = w / 2
    ry = h / 2
    return (
        '      <Section N="Geometry" IX="0">\n'
        '        <Cell N="NoFill" V="0"/>\n'
        '        <Cell N="NoLine" V="0"/>\n'
        '        <Cell N="NoShow" V="0"/>\n'
        '        <Cell N="NoSnap" V="0"/>\n'
        '        <Cell N="NoQuickDrag" V="0"/>\n'
        f'        <Row T="Ellipse" IX="1">'
        f'<Cell N="X" V="{rx:.4f}"/>'
        f'<Cell N="Y" V="{ry:.4f}"/>'
        f'<Cell N="A" V="{w:.4f}"/>'
        f'<Cell N="B" V="{ry:.4f}"/>'
        f'<Cell N="C" V="{rx:.4f}"/>'
        f'<Cell N="D" V="{h:.4f}"/>'
        f'</Row>\n'
        '      </Section>\n'
    )


class DirectVsdxGenerator:
    """Генератор .vsdx файлов в стиле Bitrix24.

    Создаёт Visio-файлы с полной BPMN-стилизацией:
    - Дорожки с широкими тёмными заголовками
    - Белые задачи с акцент-полосой и иконкой роли
    - Геометрические BPMN-события
    - Шлюзы с вопросами и да/нет ветками
    """

    def __init__(self) -> None:
        self._shape_id = 0
        self._page_width = 33.11
        self._page_height = 46.81
        self._step_systems: dict[str, str] = {}
        self._step_inputs: dict[str, list[str]] = {}
        self._step_outputs: dict[str, list[str]] = {}
        # Маппинг lane_id → (bg_fill, accent_color, dark_header, border_color)
        self._lane_palette: dict[str, tuple[str, str, str, str]] = {}

    def generate(
        self,
        bpmn_json: dict[str, Any],
        output_path: Path,
        process_data: dict[str, Any] | None = None,
    ) -> Path:
        """Генерирует Visio-файл из BPMN JSON."""
        try:
            # Вычисляем layout, если его нет
            if "layout" not in bpmn_json or not bpmn_json.get("layout"):
                from app.bpmn.layout import BpmnLayout
                layout_engine = BpmnLayout()
                layout = layout_engine.calculate_layout(bpmn_json)
                bpmn_json = {**bpmn_json, "layout": layout}

            self._load_step_metadata(process_data)

            layout = bpmn_json.get("layout") or {}
            elements = bpmn_json.get("elements") or []
            flows = bpmn_json.get("flows") or []

            element_positions = layout.get("elements") or {}
            flow_waypoints = layout.get("flows") or {}
            lane_positions = layout.get("lanes") or {}

            # Маппинг lane_id → имя участника
            lane_names: dict[str, str] = {}
            for part in bpmn_json.get("participants") or []:
                lid = part.get("lane_id") or part.get("id", "")
                pname = part.get("name", "")
                if lid and pname:
                    lane_names[lid] = pname

            # Назначаем палитру дорожкам по порядку
            for lane_idx, lane_id in enumerate(lane_positions.keys()):
                self._lane_palette[lane_id] = LANE_PALETTE_V2[lane_idx % len(LANE_PALETTE_V2)]

            self._compute_page_size(element_positions, lane_positions)

            shapes: list[str] = []

            # 1. Дорожки (фон + заголовок)
            for lane_idx, (lane_id, lane_pos) in enumerate(lane_positions.items()):
                name = lane_names.get(lane_id, lane_pos.get("name", lane_id))
                shapes.extend(self._lane_shapes(name, lane_pos, lane_idx))

            # 2. Элементы (задачи, события, шлюзы)
            for elem in elements:
                eid = elem.get("id", "")
                pos = element_positions.get(eid)
                if pos:
                    shapes.extend(self._element_shapes(elem, pos, lane_positions))

            # 3. Соединители — один Shape с множеством Geometry секций
            connector_geoms: list[tuple[list[dict], str]] = []
            for flow in flows:
                fid = flow.get("id", "")
                wps = flow_waypoints.get(fid, [])
                if len(wps) >= 2:
                    text = flow.get("name", "")
                    connector_geoms.append((wps, text))
            if connector_geoms:
                shapes.append(self._make_all_connectors(connector_geoms))

            shapes_xml = "\n".join(s for s in shapes if s)
            title = bpmn_json.get("process_name", "Диаграмма BPMN")
            create_bpmn_vsdx(
                shapes_xml, output_path,
                title=title,
                page_width=self._page_width,
                page_height=self._page_height,
            )

            logger.info(
                "Visio создан: %s (%d элементов, %d потоков)",
                output_path.name, len(elements), len(flows),
            )
            return output_path

        except ExportError:
            raise
        except Exception as exc:
            logger.exception("Ошибка генерации Visio: %s", exc)
            raise ExportError(
                "Ошибка создания Visio-файла", detail=str(exc),
            ) from exc

    # ──────────────────────────────────────────────────────────────────
    # Метаданные шагов
    # ──────────────────────────────────────────────────────────────────

    def _load_step_metadata(self, process_data: dict[str, Any] | None) -> None:
        """Загружает системы и документы из данных процесса."""
        self._step_systems.clear()
        self._step_inputs.clear()
        self._step_outputs.clear()
        if not process_data:
            return
        for step in process_data.get("steps") or []:
            name = step.get("name", "")
            order = step.get("order", "")
            performer = step.get("performer", step.get("executor", ""))
            system = step.get("system", "")
            inputs = step.get("inputs") or []
            outputs = step.get("outputs") or []

            names_to_index = [name]
            if order and name:
                names_to_index.append(f"{order}. {name}")
                if performer:
                    names_to_index.append(f"{order}. {name} ({performer})")

            for key in names_to_index:
                if not key:
                    continue
                if system:
                    self._step_systems[key] = system
                if inputs:
                    self._step_inputs[key] = inputs
                if outputs:
                    self._step_outputs[key] = outputs

    # ──────────────────────────────────────────────────────────────────
    # Размер страницы
    # ──────────────────────────────────────────────────────────────────

    def _compute_page_size(
        self, element_positions: dict, lane_positions: dict,
    ) -> None:
        max_x = 0.0
        max_y = 0.0
        for pos in list(element_positions.values()) + list(lane_positions.values()):
            right = _px(pos.get("x", 0) + pos.get("width", 0))
            bottom = _px(pos.get("y", 0) + pos.get("height", 0))
            max_x = max(max_x, right)
            max_y = max(max_y, bottom)
        self._page_width = max(11.0, max_x + 2.0)
        self._page_height = max(8.5, max_y + 2.0)

    def _next_id(self) -> int:
        self._shape_id += 1
        return self._shape_id

    def _flip_y(self, y_in: float) -> float:
        """Инвертирует Y для Visio (снизу вверх)."""
        return self._page_height - y_in

    def _lane_accent(self, lane_id: str) -> str:
        """Возвращает accent_color дорожки по lane_id."""
        entry = self._lane_palette.get(lane_id)
        if entry:
            return entry[1]
        return LANE_PALETTE_V2[0][1]

    # ══════════════════════════════════════════════════════════════════
    # Дорожка (swimlane)
    # ══════════════════════════════════════════════════════════════════

    def _lane_shapes(self, name: str, pos: dict, lane_idx: int = 0) -> list[str]:
        """Создаёт дорожку: цветной фон + широкий тёмный заголовок."""
        parts: list[str] = []
        x = _px(pos.get("x", 0))
        y = _px(pos.get("y", 0))
        w = _px(pos.get("width", 600))
        h = _px(pos.get("height", 200))

        bg_fill, accent, dark_header, border = LANE_PALETTE_V2[lane_idx % len(LANE_PALETTE_V2)]

        # Фон дорожки
        sid = self._next_id()
        cx = x + w / 2
        cy = self._flip_y(y + h / 2)
        bg_v = _vis_color(bg_fill)
        border_v = _vis_color(border)
        parts.append(
            _shape_base(sid, cx, cy, w, h)
            + f'      <Cell N="FillForegnd" V="{bg_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{bg_v}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{border_v}"/>\n'
            + '      <Cell N="LineWeight" V="0.008"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + "    </Shape>"
        )

        # Заголовок дорожки — тёмный блок слева с белым вертикальным текстом
        header_w = _LANE_HEADER_W
        parts.append(self._make_lane_header(
            x, y, header_w, h, name,
            header_fill=dark_header,
            header_line=dark_header,
        ))

        return parts

    def _make_lane_header(
        self,
        x: float, y: float, w: float, h: float,
        name: str,
        header_fill: str | None = None,
        header_line: str | None = None,
    ) -> str:
        """Заголовок дорожки — широкий тёмный блок с белым текстом."""
        sid = self._next_id()
        cx = x + w / 2
        cy = self._flip_y(y + h / 2)
        fill_v = _vis_color(header_fill or "#2B5091")
        line_v = _vis_color(header_line or "#2B5091")
        txt_angle = math.pi / 2  # 90° CCW — снизу вверх

        return (
            _shape_base(sid, cx, cy, w, h, name=name)
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{line_v}"/>\n'
            + '      <Cell N="LineWeight" V="0.008"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="Char.Color" V="#FFFFFF"/>\n'
            + '      <Cell N="Char.Size" V="0.1111"/>\n'  # 12pt / 1.08 ≈ 0.1111"
            + '      <Cell N="Char.Style" V="1"/>\n'  # Bold
            + '      <Cell N="Para.HorzAlign" V="1"/>\n'  # Center
            + '      <Cell N="VerticalAlign" V="1"/>\n'  # Middle
            + f'      <Cell N="TxtWidth" V="{h:.4f}"/>\n'
            + f'      <Cell N="TxtHeight" V="{w:.4f}"/>\n'
            + f'      <Cell N="TxtPinX" V="{w / 2:.4f}" F="Width*0.5"/>\n'
            + f'      <Cell N="TxtPinY" V="{h / 2:.4f}" F="Height*0.5"/>\n'
            + f'      <Cell N="TxtLocPinX" V="{h / 2:.4f}" F="TxtWidth*0.5"/>\n'
            + f'      <Cell N="TxtLocPinY" V="{w / 2:.4f}" F="TxtHeight*0.5"/>\n'
            + f'      <Cell N="TxtAngle" V="{txt_angle:.6f}"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + f"      <Text>{xml_escape(name)}</Text>\n"
            + "    </Shape>"
        )

    # ══════════════════════════════════════════════════════════════════
    # Элементы BPMN
    # ══════════════════════════════════════════════════════════════════

    def _find_lane_bottom(self, y_inch: float, h_inch: float, lane_positions: dict) -> float:
        """Находит нижнюю границу дорожки для элемента."""
        center_y = y_inch + h_inch / 2
        best: float | None = None
        best_dist = float("inf")
        for lane_pos in lane_positions.values():
            ly = _px(lane_pos.get("y", 0))
            lh = _px(lane_pos.get("height", 0))
            lane_center = ly + lh / 2
            dist = abs(center_y - lane_center)
            if dist < best_dist:
                best_dist = dist
                best = ly + lh
        return best if best is not None else 1e9

    def _element_shapes(
        self,
        elem: dict,
        pos: dict,
        lane_positions: dict | None = None,
    ) -> list[str]:
        """Создаёт фигуры для BPMN-элемента."""
        parts: list[str] = []
        etype = elem.get("type", "task")
        name = _clean_text(elem.get("name", ""))
        x = _px(pos.get("x", 0))
        y = _px(pos.get("y", 0))
        w = _px(pos.get("width", 180))
        h = _px(pos.get("height", 90))
        lane_id = elem.get("lane", "")

        # Accent color for this element (from its lane)
        accent = self._lane_accent(lane_id)

        # Event helpers
        r_inch = _px(pos.get("width", 36)) / 2
        cx_px = pos.get("x", 0) + pos.get("width", 36) / 2
        cy_px = pos.get("y", 0) + pos.get("height", 36) / 2

        if etype == "startEvent":
            # Зелёный круг с треугольником-play внутри
            parts.extend(self._make_start_event(cx_px, cy_px, r_inch))
            if name:
                parts.append(self._make_event_label(x, y, w, h, name, _EVENT_START_LINE))

        elif etype == "messageStartEvent":
            # Зелёный круг с конвертом
            parts.extend(self._make_message_start_event(cx_px, cy_px, r_inch))
            if name:
                parts.append(self._make_event_label(x, y, w, h, name, _EVENT_START_LINE))

        elif etype == "endEvent":
            # Красный жирный круг с квадратом-terminate
            parts.extend(self._make_end_event(cx_px, cy_px, r_inch))
            if name:
                parts.append(self._make_event_label(x, y, w, h, name, _EVENT_END_LINE))

        elif etype == "messageEndEvent":
            # Красный жирный круг с закрашенным конвертом
            parts.extend(self._make_message_end_event(cx_px, cy_px, r_inch))
            if name:
                parts.append(self._make_event_label(x, y, w, h, name, _EVENT_END_LINE))

        elif etype in ("cancelEndEvent", "cancelEvent"):
            # Двойной красный круг с X
            parts.extend(self._make_cancel_event(cx_px, cy_px, r_inch))
            if name:
                parts.append(self._make_event_label(x, y, w, h, name, _EVENT_CANCEL_LINE))

        elif etype in ("timerIntermediateCatchEvent", "timerEvent"):
            # Двойной жёлтый круг с часами
            parts.extend(self._make_timer_event(cx_px, cy_px, r_inch))
            timer_label = elem.get("timer_wait", "") or name
            if timer_label:
                parts.append(self._make_event_label(x, y, w, h, timer_label, _EVENT_TIMER_LINE))

        elif "Gateway" in etype or "gateway" in etype:
            # Жёлтый ромб + метка вопроса выше
            parts.append(self._make_diamond(x, y, w, h))
            condition_label = _clean_text(elem.get("condition_label", "")) or name
            if condition_label:
                label_w, label_h = self._label_dims(condition_label, max_w=2.2, min_w=w)
                parts.append(self._make_gateway_label(
                    x + w / 2 - label_w / 2,
                    y - label_h - 0.10,
                    label_w, label_h,
                    condition_label,
                ))

        else:
            # Задача: белый прямоугольник + акцент-полоса слева + иконка роли
            parts.extend(self._make_task(x, y, w, h, name, accent))
            # Маркеры подпроцесса/multi-instance
            is_subprocess = elem.get("is_subprocess", False)
            multi_instance = elem.get("multi_instance", False)
            if is_subprocess and multi_instance:
                sp_size = 0.16
                mi_size = 0.18
                parts.append(self._make_subprocess_marker(
                    x + w / 2 - sp_size - 0.04, y + h - sp_size - 0.02, sp_size,
                ))
                parts.append(self._make_multi_instance_marker(
                    x + w / 2 + 0.04, y + h - mi_size - 0.02, mi_size,
                ))
            elif is_subprocess:
                sp_size = 0.16
                parts.append(self._make_subprocess_marker(
                    x + w / 2 - sp_size / 2, y + h - sp_size - 0.02, sp_size,
                ))
            elif multi_instance:
                mi_size = 0.18
                parts.append(self._make_multi_instance_marker(
                    x + w / 2 - mi_size / 2, y + h - mi_size - 0.02, mi_size,
                ))

        return parts

    # ══════════════════════════════════════════════════════════════════
    # BPMN-события — геометрические фигуры
    # ══════════════════════════════════════════════════════════════════

    def _make_start_event(
        self, cx_px: float, cy_px: float, r_inch: float,
    ) -> list[str]:
        """startEvent: зелёный тонкий круг + треугольник-play."""
        parts = []
        d = r_inch * 2
        cx = _px(cx_px)
        cy = self._flip_y(_px(cy_px))

        # Внешний круг
        sid = self._next_id()
        parts.append(
            _shape_base(sid, cx, cy, d, d, name="StartEvent")
            + f'      <Cell N="FillForegnd" V="{_EVENT_START_FILL}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{_EVENT_START_FILL}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_START_LINE}"/>\n'
            + '      <Cell N="LineWeight" V="0.0208"/>\n'  # 1.5pt
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + _geom_ellipse(d)
            + "    </Shape>"
        )

        # Треугольник-play внутри (чуть меньше круга)
        play_size = d * 0.55
        sid2 = self._next_id()
        parts.append(
            _shape_base(sid2, cx, cy, play_size, play_size, name="PlayTriangle")
            + f'      <Cell N="FillForegnd" V="{_EVENT_START_LINE}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{_EVENT_START_LINE}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + '      <Cell N="LinePattern" V="0"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_PLAY
            + "    </Shape>"
        )
        return parts

    def _make_message_start_event(
        self, cx_px: float, cy_px: float, r_inch: float,
    ) -> list[str]:
        """messageStartEvent: зелёный круг + конверт."""
        parts = []
        d = r_inch * 2
        cx = _px(cx_px)
        cy = self._flip_y(_px(cy_px))

        # Круг
        sid = self._next_id()
        parts.append(
            _shape_base(sid, cx, cy, d, d, name="MsgStartEvent")
            + f'      <Cell N="FillForegnd" V="{_EVENT_START_FILL}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{_EVENT_START_FILL}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_START_LINE}"/>\n'
            + '      <Cell N="LineWeight" V="0.0208"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + _geom_ellipse(d)
            + "    </Shape>"
        )

        # Конверт — прямоугольник
        ew = d * 0.58
        eh = d * 0.40
        sid2 = self._next_id()
        parts.append(
            _shape_base(sid2, cx, cy, ew, eh, name="EnvelopeRect")
            + '      <Cell N="FillForegnd" V="#A5D6A7"/>\n'
            + '      <Cell N="FillBkgnd" V="#A5D6A7"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_START_LINE}"/>\n'
            + '      <Cell N="LineWeight" V="0.008"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + "    </Shape>"
        )

        # Крышка конверта (V-образная линия)
        sid3 = self._next_id()
        parts.append(
            _shape_base(sid3, cx, cy, ew, eh, name="EnvelopeFlap")
            + '      <Cell N="FillPattern" V="0"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_START_LINE}"/>\n'
            + '      <Cell N="LineWeight" V="0.008"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + '      <Section N="Geometry" IX="0">\n'
            + '        <Cell N="NoFill" V="1"/>\n'
            + '        <Cell N="NoLine" V="0"/>\n'
            + '        <Row T="RelMoveTo" IX="1"><Cell N="X" V="0.0"/><Cell N="Y" V="1.0"/></Row>\n'
            + '        <Row T="RelLineTo" IX="2"><Cell N="X" V="0.5"/><Cell N="Y" V="0.35"/></Row>\n'
            + '        <Row T="RelLineTo" IX="3"><Cell N="X" V="1.0"/><Cell N="Y" V="1.0"/></Row>\n'
            + '      </Section>\n'
            + "    </Shape>"
        )
        return parts

    def _make_end_event(
        self, cx_px: float, cy_px: float, r_inch: float,
    ) -> list[str]:
        """endEvent: красный жирный круг + квадрат-terminate."""
        parts = []
        d = r_inch * 2
        cx = _px(cx_px)
        cy = self._flip_y(_px(cy_px))

        sid = self._next_id()
        parts.append(
            _shape_base(sid, cx, cy, d, d, name="EndEvent")
            + f'      <Cell N="FillForegnd" V="{_EVENT_END_FILL}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{_EVENT_END_FILL}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_END_LINE}"/>\n'
            + '      <Cell N="LineWeight" V="0.0417"/>\n'  # 3pt
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + _geom_ellipse(d)
            + "    </Shape>"
        )

        # Квадрат-terminate внутри
        sq_size = d * 0.42
        sid2 = self._next_id()
        parts.append(
            _shape_base(sid2, cx, cy, sq_size, sq_size, name="TerminateSquare")
            + f'      <Cell N="FillForegnd" V="{_EVENT_END_LINE}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{_EVENT_END_LINE}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + '      <Cell N="LinePattern" V="0"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + "    </Shape>"
        )
        return parts

    def _make_message_end_event(
        self, cx_px: float, cy_px: float, r_inch: float,
    ) -> list[str]:
        """messageEndEvent: красный жирный круг + закрашенный конверт."""
        parts = []
        d = r_inch * 2
        cx = _px(cx_px)
        cy = self._flip_y(_px(cy_px))

        # Жирный красный круг
        sid = self._next_id()
        parts.append(
            _shape_base(sid, cx, cy, d, d, name="MsgEndEvent")
            + f'      <Cell N="FillForegnd" V="{_EVENT_END_FILL}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{_EVENT_END_FILL}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_END_LINE}"/>\n'
            + '      <Cell N="LineWeight" V="0.0417"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + _geom_ellipse(d)
            + "    </Shape>"
        )

        # Закрашенный конверт
        ew = d * 0.58
        eh = d * 0.40
        sid2 = self._next_id()
        parts.append(
            _shape_base(sid2, cx, cy, ew, eh, name="EnvelopeRectEnd")
            + f'      <Cell N="FillForegnd" V="{_EVENT_END_LINE}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{_EVENT_END_LINE}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_END_FILL}"/>\n'
            + '      <Cell N="LineWeight" V="0.008"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + "    </Shape>"
        )

        # Крышка конверта
        sid3 = self._next_id()
        parts.append(
            _shape_base(sid3, cx, cy, ew, eh, name="EnvelopeFlapEnd")
            + '      <Cell N="FillPattern" V="0"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_END_FILL}"/>\n'
            + '      <Cell N="LineWeight" V="0.010"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + '      <Section N="Geometry" IX="0">\n'
            + '        <Cell N="NoFill" V="1"/>\n'
            + '        <Cell N="NoLine" V="0"/>\n'
            + '        <Row T="RelMoveTo" IX="1"><Cell N="X" V="0.0"/><Cell N="Y" V="1.0"/></Row>\n'
            + '        <Row T="RelLineTo" IX="2"><Cell N="X" V="0.5"/><Cell N="Y" V="0.35"/></Row>\n'
            + '        <Row T="RelLineTo" IX="3"><Cell N="X" V="1.0"/><Cell N="Y" V="1.0"/></Row>\n'
            + '      </Section>\n'
            + "    </Shape>"
        )
        return parts

    def _make_cancel_event(
        self, cx_px: float, cy_px: float, r_inch: float,
    ) -> list[str]:
        """cancelEndEvent: двойной красный круг + X-крест."""
        parts = []
        d = r_inch * 2
        cx = _px(cx_px)
        cy = self._flip_y(_px(cy_px))

        # Внешний круг (жирный)
        sid = self._next_id()
        parts.append(
            _shape_base(sid, cx, cy, d, d, name="CancelOuter")
            + f'      <Cell N="FillForegnd" V="{_EVENT_CANCEL_FILL}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{_EVENT_CANCEL_FILL}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_CANCEL_LINE}"/>\n'
            + '      <Cell N="LineWeight" V="0.0417"/>\n'  # 3pt
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + _geom_ellipse(d)
            + "    </Shape>"
        )

        # Внутренний круг (тонкий)
        d_inner = d * 0.80
        sid2 = self._next_id()
        parts.append(
            _shape_base(sid2, cx, cy, d_inner, d_inner, name="CancelInner")
            + f'      <Cell N="FillForegnd" V="{_EVENT_CANCEL_FILL}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{_EVENT_CANCEL_FILL}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_CANCEL_LINE}"/>\n'
            + '      <Cell N="LineWeight" V="0.010"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + _geom_ellipse(d_inner)
            + "    </Shape>"
        )

        # X-крест: 2 диагональные линии
        # Параметры: 40% радиуса внутреннего круга от центра
        cross_half = r_inch * 0.35
        # Линия 1: ↘ (top-left to bottom-right) — в Visio coords
        x1_v = cx - cross_half
        y1_v = cy + cross_half  # Visio: + = up
        x2_v = cx + cross_half
        y2_v = cy - cross_half
        parts.append(self._make_line_vis(
            x1_v, y1_v, x2_v, y2_v,
            _EVENT_CANCEL_LINE, 0.0208,
        ))
        # Линия 2: ↙ (top-right to bottom-left)
        parts.append(self._make_line_vis(
            cx + cross_half, cy + cross_half,
            cx - cross_half, cy - cross_half,
            _EVENT_CANCEL_LINE, 0.0208,
        ))
        return parts

    def _make_timer_event(
        self, cx_px: float, cy_px: float, r_inch: float,
    ) -> list[str]:
        """timerIntermediateCatchEvent: двойной жёлтый круг + часы."""
        parts = []
        d = r_inch * 2
        cx = _px(cx_px)
        cy = self._flip_y(_px(cy_px))

        # Внешний круг
        sid = self._next_id()
        parts.append(
            _shape_base(sid, cx, cy, d, d, name="TimerOuter")
            + f'      <Cell N="FillForegnd" V="{_EVENT_TIMER_FILL}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{_EVENT_TIMER_FILL}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_TIMER_LINE}"/>\n'
            + '      <Cell N="LineWeight" V="0.0139"/>\n'  # 1pt
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + _geom_ellipse(d)
            + "    </Shape>"
        )

        # Внутренний круг
        d_inner = d * 0.80
        sid2 = self._next_id()
        parts.append(
            _shape_base(sid2, cx, cy, d_inner, d_inner, name="TimerInner")
            + f'      <Cell N="FillForegnd" V="{_EVENT_TIMER_FILL}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{_EVENT_TIMER_FILL}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{_EVENT_TIMER_LINE}"/>\n'
            + '      <Cell N="LineWeight" V="0.010"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + _geom_ellipse(d_inner)
            + "    </Shape>"
        )

        # Tick-марки на 12, 3, 6, 9 часов (в Visio coords)
        tick_inner_r = r_inch * 0.58
        tick_outer_r = r_inch * 0.72
        for angle_deg in (90, 0, 270, 180):  # 12=90°, 3=0°, 6=270°, 9=180°
            rad = math.radians(angle_deg)
            x1_v = cx + math.cos(rad) * tick_inner_r
            y1_v = cy + math.sin(rad) * tick_inner_r
            x2_v = cx + math.cos(rad) * tick_outer_r
            y2_v = cy + math.sin(rad) * tick_outer_r
            parts.append(self._make_line_vis(x1_v, y1_v, x2_v, y2_v, _EVENT_TIMER_LINE, 0.012))

        # Часовая стрелка → 3 часа (вправо, ~50% радиуса)
        hand_h_len = r_inch * 0.42
        parts.append(self._make_line_vis(
            cx, cy,
            cx + hand_h_len, cy,
            _EVENT_TIMER_LINE, 0.015,
        ))

        # Минутная стрелка → 12 часов (вверх, ~62% радиуса)
        hand_m_len = r_inch * 0.55
        parts.append(self._make_line_vis(
            cx, cy,
            cx, cy + hand_m_len,
            _EVENT_TIMER_LINE, 0.010,
        ))
        return parts

    def _make_event_label(
        self,
        x: float, y: float, w: float, h: float,
        text: str,
        text_color: str,
    ) -> str:
        """Подпись под событием (прозрачный фон)."""
        label_w, label_h = self._label_dims(text, max_w=1.5, min_w=0.50)
        min_lx = _px(80) + _LANE_HEADER_W + 0.05
        label_x = max(min_lx, x + w / 2 - label_w / 2)
        label_y = y + h + 0.10

        sid = self._next_id()
        cx = label_x + label_w / 2
        cy = self._flip_y(label_y + label_h / 2)
        text_v = _vis_color(text_color)

        return (
            _shape_base(sid, cx, cy, label_w, label_h, name="EventLabel")
            + '      <Cell N="FillPattern" V="0"/>\n'
            + '      <Cell N="LinePattern" V="0"/>\n'
            + f'      <Cell N="Char.Color" V="{text_v}"/>\n'
            + '      <Cell N="Char.Size" V="0.0833"/>\n'  # ~7pt / 1.08
            + '      <Cell N="Para.HorzAlign" V="1"/>\n'
            + '      <Cell N="VerticalAlign" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + f"      <Text>{xml_escape(text)}</Text>\n"
            + "    </Shape>"
        )

    # ══════════════════════════════════════════════════════════════════
    # Задача (Bitrix24 style)
    # ══════════════════════════════════════════════════════════════════

    def _make_task(
        self,
        x: float, y: float, w: float, h: float,
        name: str,
        accent_color: str,
    ) -> list[str]:
        """Задача: белый фон + акцент-полоса слева + иконка роли + текст."""
        parts = []

        # 1. Основной прямоугольник (белый, скруглённый)
        sid = self._next_id()
        cx = x + w / 2
        cy = self._flip_y(y + h / 2)
        fill_v = _vis_color(_TASK_FILL)
        border_v = _vis_color(_TASK_BORDER)
        text_v = _vis_color(_TASK_TEXT)
        accent_v = _vis_color(accent_color)

        parts.append(
            _shape_base(sid, cx, cy, w, h)
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{border_v}"/>\n'
            + '      <Cell N="LineWeight" V="0.0104"/>\n'  # 0.75pt
            + '      <Cell N="LinePattern" V="1"/>\n'
            + f'      <Cell N="Rounding" V="{_TASK_ROUND:.4f}"/>\n'
            + f'      <Cell N="Char.Color" V="{text_v}"/>\n'
            + '      <Cell N="Char.Size" V="0.1014"/>\n'  # ~11pt
            + '      <Cell N="Char.Face" V="Calibri"/>\n'
            + '      <Cell N="Para.HorzAlign" V="0"/>\n'  # Left
            + '      <Cell N="VerticalAlign" V="1"/>\n'    # Middle
            + f'      <Cell N="LeftMargin" V="{_ACCENT_BAR_W + 0.07:.4f}"/>\n'
            + '      <Cell N="RightMargin" V="0.22"/>\n'
            + '      <Cell N="TopMargin" V="0.06"/>\n'
            + '      <Cell N="BottomMargin" V="0.04"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + f"      <Text>{xml_escape(name)}</Text>\n"
            + "    </Shape>"
        )

        # 2. Акцент-полоса (цветная вертикальная полоска слева)
        bar_h = h - 2 * _TASK_ROUND
        bar_y = y + _TASK_ROUND
        bar_x = x
        sid2 = self._next_id()
        bcx = bar_x + _ACCENT_BAR_W / 2
        bcy = self._flip_y(bar_y + bar_h / 2)
        parts.append(
            _shape_base(sid2, bcx, bcy, _ACCENT_BAR_W, bar_h, name="AccentBar")
            + f'      <Cell N="FillForegnd" V="{accent_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{accent_v}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + '      <Cell N="LinePattern" V="0"/>\n'
            + '      <Cell N="Rounding" V="0.042"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + "    </Shape>"
        )

        # 3. Иконка роли: голова + тело (в правом верхнем углу)
        parts.extend(self._make_person_icon(x, y, w, accent_color))

        return parts

    def _make_person_icon(
        self,
        task_x: float, task_y: float,
        task_w: float,
        accent_color: str,
    ) -> list[str]:
        """Иконка-персонаж: круг (голова) + эллипс (тело) — top-right задачи."""
        parts = []
        fill_v = _vis_color(accent_color)
        icon_inset = 0.09   # отступ от края задачи

        # Голова (маленький круг)
        head_d = 0.11
        head_cx = task_x + task_w - icon_inset - head_d / 2
        head_cy = task_y + icon_inset + head_d / 2
        sid = self._next_id()
        parts.append(
            _shape_base(sid, head_cx, self._flip_y(head_cy), head_d, head_d, name="PersonHead")
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + '      <Cell N="LinePattern" V="0"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + _geom_ellipse(head_d)
            + "    </Shape>"
        )

        # Тело (маленький широкий эллипс)
        body_w = 0.17
        body_h = 0.09
        body_cx = task_x + task_w - icon_inset - head_d / 2
        body_cy = head_cy + head_d / 2 + body_h / 2 + 0.01
        sid2 = self._next_id()
        parts.append(
            _shape_base(sid2, body_cx, self._flip_y(body_cy), body_w, body_h, name="PersonBody")
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + '      <Cell N="LinePattern" V="0"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + _geom_ellipse(body_w, body_h)
            + "    </Shape>"
        )
        return parts

    # ══════════════════════════════════════════════════════════════════
    # Шлюз (gateway)
    # ══════════════════════════════════════════════════════════════════

    def _make_diamond(
        self,
        x: float, y: float, w: float, h: float,
    ) -> str:
        """Жёлтый ромб шлюза с × маркером."""
        sid = self._next_id()
        cx = x + w / 2
        cy = self._flip_y(y + h / 2)
        fill_v = _vis_color(_GATEWAY_FILL)
        line_v = _vis_color(_GATEWAY_LINE)

        return (
            _shape_base(sid, cx, cy, w, h)
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{line_v}"/>\n'
            + f'      <Cell N="LineWeight" V="{_GATEWAY_LW:.4f}"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="Char.Size" V="0.1667"/>\n'  # крупный × внутри
            + '      <Cell N="Char.Style" V="1"/>\n'      # Bold
            + f'      <Cell N="Char.Color" V="{line_v}"/>\n'
            + '      <Cell N="Para.HorzAlign" V="1"/>\n'
            + '      <Cell N="VerticalAlign" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_DIAMOND
            + "      <Text>\u00D7</Text>\n"  # ×
            + "    </Shape>"
        )

    def _make_gateway_label(
        self,
        x: float, y: float, w: float, h: float,
        text: str,
    ) -> str:
        """Подпись шлюза — прозрачный блок выше ромба."""
        sid = self._next_id()
        cx = x + w / 2
        cy = self._flip_y(y + h / 2)
        text_v = _vis_color(_LABEL_TEXT_COLOR)

        return (
            _shape_base(sid, cx, cy, w, h, name="GatewayLabel")
            + '      <Cell N="FillPattern" V="0"/>\n'
            + '      <Cell N="LinePattern" V="0"/>\n'
            + f'      <Cell N="Char.Color" V="{text_v}"/>\n'
            + '      <Cell N="Char.Size" V="0.0833"/>\n'
            + '      <Cell N="Char.Style" V="2"/>\n'  # Italic
            + '      <Cell N="Para.HorzAlign" V="1"/>\n'
            + '      <Cell N="VerticalAlign" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + f"      <Text>{xml_escape(text)}</Text>\n"
            + "    </Shape>"
        )

    # ══════════════════════════════════════════════════════════════════
    # Маркеры подпроцессов
    # ══════════════════════════════════════════════════════════════════

    def _make_subprocess_marker(self, x: float, y: float, size: float) -> str:
        """Маркер подпроцесса [+]."""
        sid = self._next_id()
        cx = x + size / 2
        cy = self._flip_y(y + size / 2)
        return (
            _shape_base(sid, cx, cy, size, size, name="SubprocessMarker")
            + '      <Cell N="FillForegnd" V="#FFFFFF"/>\n'
            + '      <Cell N="FillBkgnd" V="#FFFFFF"/>\n'
            + '      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{_TASK_BORDER}"/>\n'
            + '      <Cell N="LineWeight" V="0.008"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + f'      <Cell N="Char.Color" V="{_TASK_TEXT}"/>\n'
            + '      <Cell N="Char.Size" V="0.10"/>\n'
            + '      <Cell N="Char.Style" V="1"/>\n'
            + '      <Cell N="Para.HorzAlign" V="1"/>\n'
            + '      <Cell N="VerticalAlign" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + "      <Text>+</Text>\n"
            + "    </Shape>"
        )

    def _make_multi_instance_marker(self, x: float, y: float, size: float) -> str:
        """Маркер multi-instance ||| — три вертикальные линии."""
        parts = []
        bar_w = size / 6
        bar_gap = bar_w * 1.5
        total = 3 * bar_w + 2 * bar_gap
        start_x = x + (size - total) / 2

        for i in range(3):
            bx = start_x + i * (bar_w + bar_gap)
            sid = self._next_id()
            cx = bx + bar_w / 2
            cy = self._flip_y(y + size / 2)
            parts.append(
                _shape_base(sid, cx, cy, bar_w, size, name="MIBar")
                + f'      <Cell N="FillForegnd" V="{_TASK_TEXT}"/>\n'
                + f'      <Cell N="FillBkgnd" V="{_TASK_TEXT}"/>\n'
                + '      <Cell N="FillPattern" V="1"/>\n'
                + '      <Cell N="LinePattern" V="0"/>\n'
                + '      <Cell N="ObjType" V="1"/>\n'
                + GEOM_RECT
                + "    </Shape>"
            )
        return "\n".join(parts)

    # ══════════════════════════════════════════════════════════════════
    # Линии (для геометрических фигур событий)
    # ══════════════════════════════════════════════════════════════════

    def _make_line_vis(
        self,
        x1_vis: float, y1_vis: float,
        x2_vis: float, y2_vis: float,
        line_color: str = "#404040",
        line_weight: float = 0.010,
    ) -> str:
        """Линия в Visio-координатах (уже перевёрнутые Y)."""
        sid = self._next_id()
        margin = 0.001
        min_x = min(x1_vis, x2_vis) - margin
        max_x = max(x1_vis, x2_vis) + margin
        min_y = min(y1_vis, y2_vis) - margin
        max_y = max(y1_vis, y2_vis) + margin

        w = max(max_x - min_x, 0.002)
        h = max(max_y - min_y, 0.002)
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2

        # Local coordinates within the shape's bounding box
        lx1 = x1_vis - min_x
        ly1 = y1_vis - min_y
        lx2 = x2_vis - min_x
        ly2 = y2_vis - min_y

        line_v = _vis_color(line_color)
        return (
            _shape_base(sid, cx, cy, w, h, name="Line")
            + '      <Cell N="FillPattern" V="0"/>\n'
            + f'      <Cell N="LineColor" V="{line_v}"/>\n'
            + f'      <Cell N="LineWeight" V="{line_weight:.4f}"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + '      <Section N="Geometry" IX="0">\n'
            + '        <Cell N="NoFill" V="1"/>\n'
            + '        <Cell N="NoLine" V="0"/>\n'
            + f'        <Row T="MoveTo" IX="1">'
            + f'<Cell N="X" V="{lx1:.4f}"/><Cell N="Y" V="{ly1:.4f}"/></Row>\n'
            + f'        <Row T="LineTo" IX="2">'
            + f'<Cell N="X" V="{lx2:.4f}"/><Cell N="Y" V="{ly2:.4f}"/></Row>\n'
            + '      </Section>\n'
            + "    </Shape>"
        )

    # ══════════════════════════════════════════════════════════════════
    # Утилиты размеров
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _label_dims(
        text: str,
        char_coeff: float = 0.085,
        font_size: float = 0.08,
        max_w: float = 2.2,
        min_w: float = 1.0,
    ) -> tuple[float, float]:
        """Вычисляет (width, height) для текстовой метки."""
        raw_w = _visual_text_width(text, char_coeff=char_coeff)
        label_w = max(min(raw_w + 0.12, max_w), min_w)
        visual_len = _visual_text_width(text, char_coeff=1.0)
        chars_per_line = max(1, int(label_w / char_coeff))
        lines = max(1, math.ceil(visual_len / chars_per_line))
        label_h = max(0.28, font_size * 1.8 * lines + 0.06)
        return label_w, label_h

    # ══════════════════════════════════════════════════════════════════
    # Соединители
    # ══════════════════════════════════════════════════════════════════

    def _make_all_connectors(
        self,
        connector_geoms: list[tuple[list[dict], str]],
    ) -> str:
        """Все соединители в ОДНОМ Shape — предотвращает auto-routing Visio."""
        all_vis_paths: list[list[tuple[float, float]]] = []
        all_texts: list[str] = []

        for wps, text in connector_geoms:
            vis_pts = [
                (_px(wp.get("x", 0)), self._flip_y(_px(wp.get("y", 0))))
                for wp in wps
            ]
            if len(vis_pts) >= 2:
                all_vis_paths.append(vis_pts)
                all_texts.append(text)

        if not all_vis_paths:
            return ""

        flat_x = [p[0] for pts in all_vis_paths for p in pts]
        flat_y = [p[1] for pts in all_vis_paths for p in pts]
        margin = 0.02
        bb_min_x = min(flat_x) - margin
        bb_max_x = max(flat_x) + margin
        bb_min_y = min(flat_y) - margin
        bb_max_y = max(flat_y) + margin

        w = bb_max_x - bb_min_x
        h = bb_max_y - bb_min_y
        cx = (bb_min_x + bb_max_x) / 2
        cy = (bb_min_y + bb_max_y) / 2

        sid = self._next_id()
        line_v = _vis_color(_CONNECTOR_LINE)

        geom_parts: list[str] = []
        for idx, vis_pts in enumerate(all_vis_paths):
            rows: list[str] = []
            for i, (px, py) in enumerate(vis_pts):
                rel_x = (px - bb_min_x) / w if w > 0.001 else 0.0
                rel_y = (py - bb_min_y) / h if h > 0.001 else 0.0
                row_type = "RelMoveTo" if i == 0 else "RelLineTo"
                rows.append(
                    f'        <Row T="{row_type}" IX="{i + 1}">'
                    f'<Cell N="X" V="{rel_x:.6f}"/>'
                    f'<Cell N="Y" V="{rel_y:.6f}"/></Row>'
                )
            rows_xml = "\n".join(rows)
            geom_parts.append(
                f'      <Section N="Geometry" IX="{idx}">\n'
                f'        <Cell N="NoFill" V="1"/>\n'
                f'        <Cell N="NoLine" V="0"/>\n'
                f'        <Cell N="NoShow" V="0"/>\n'
                f'        <Cell N="NoSnap" V="0"/>\n'
                f'        <Cell N="NoQuickDrag" V="0"/>\n'
                + rows_xml + "\n"
                + "      </Section>\n"
            )

        all_geom = "".join(geom_parts)

        connector_shape = (
            _shape_base(sid, cx, cy, w, h, name="Connectors")
            + f'      <Cell N="LineColor" V="{line_v}"/>\n'
            + '      <Cell N="LineWeight" V="0.0100"/>\n'
            + '      <Cell N="LinePattern" V="1"/>\n'
            + '      <Cell N="EndArrow" V="13"/>\n'
            + '      <Cell N="EndArrowSize" V="2"/>\n'
            + '      <Cell N="FillPattern" V="0"/>\n'
            + '      <Cell N="ObjType" V="1"/>\n'
            + all_geom
            + "    </Shape>"
        )

        # Таблетки-подписи (Да / Нет) на ветках шлюзов
        labels: list[str] = []
        for vis_pts, text in zip(all_vis_paths, all_texts):
            if not text:
                continue
            mid = len(vis_pts) // 2
            mx, my = vis_pts[mid]
            label_w = max(_visual_text_width(text, char_coeff=0.08), 0.28)
            label_h = 0.18
            lsid = self._next_id()

            p_prev = vis_pts[max(0, mid - 1)]
            p_curr = vis_pts[mid]
            dx = abs(p_curr[0] - p_prev[0])
            dy = abs(p_curr[1] - p_prev[1])
            if dy > dx:
                label_cx = mx + label_w / 2 + 0.10
                label_cy = my
            else:
                label_cx = mx
                label_cy = my + 0.14

            fill_v = _vis_color("#FFFFFF")
            border_v = _vis_color(_TASK_BORDER)
            text_v = _vis_color(_LABEL_TEXT_COLOR)
            labels.append(
                _shape_base(lsid, label_cx, label_cy, label_w, label_h)
                + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
                + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
                + '      <Cell N="FillPattern" V="1"/>\n'
                + f'      <Cell N="LineColor" V="{border_v}"/>\n'
                + '      <Cell N="LineWeight" V="0.007"/>\n'
                + '      <Cell N="LinePattern" V="1"/>\n'
                + '      <Cell N="Rounding" V="0.09"/>\n'   # pill shape
                + f'      <Cell N="Char.Color" V="{text_v}"/>\n'
                + '      <Cell N="Char.Size" V="0.0694"/>\n'  # ~7.5pt
                + '      <Cell N="Char.Style" V="1"/>\n'       # Bold
                + '      <Cell N="Para.HorzAlign" V="1"/>\n'
                + '      <Cell N="VerticalAlign" V="1"/>\n'
                + '      <Cell N="ObjType" V="1"/>\n'
                + GEOM_RECT
                + f"      <Text>{xml_escape(text)}</Text>\n"
                + "    </Shape>"
            )

        parts = [connector_shape] + labels
        return "\n".join(parts)


# ──────────────────────────────────────────────────────────────────────
# Точка входа
# ──────────────────────────────────────────────────────────────────────

def generate_visio_direct(
    bpmn_json: dict[str, Any],
    output_path: Path,
    process_data: dict[str, Any] | None = None,
) -> Path:
    """Генерирует Visio-файл из BPMN JSON.

    Args:
        bpmn_json: BPMN JSON-структура.
        output_path: Путь вывода .vsdx.
        process_data: Дополнительные данные процесса (шаги с системами).
    """
    gen = DirectVsdxGenerator()
    return gen.generate(bpmn_json, output_path, process_data)
