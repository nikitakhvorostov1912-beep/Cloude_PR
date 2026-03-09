"""Прямая генерация .vsdx файлов из BPMN JSON.

Создаёт профессиональные Visio-диаграммы с BPMN-нотацией:
- Дорожки (swimlanes) с заголовками слева и рамкой
- Задачи с маркерами типа (пользователь/сервис) и системными метками
- События (старт/конец) с подписями
- Шлюзы с маркерами
- Соединители с подписями условий
- Аннотации для pain points

Все тексты на русском языке.
"""

from __future__ import annotations

import json
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

# Цвета BPMN-элементов в стиле Visio (Hex RGB)
COLORS = {
    # Задачи — синие по типу
    "user_task_fill": "#4472C4",     # Пользовательская задача
    "user_task_line": "#2F5496",
    "service_task_fill": "#5B9BD5",  # Сервисная задача
    "service_task_line": "#2E75B6",
    "task_fill": "#B4D7A0",          # Обычная задача (мягкий зелёный)
    "task_line": "#70AD47",
    "task_text": "#FFFFFF",
    # События
    "start_fill": "#70AD47",
    "start_line": "#548235",
    "end_fill": "#FF0000",
    "end_line": "#C00000",
    # Шлюзы
    "gateway_fill": "#FFD54F",       # Мягкий жёлтый
    "gateway_line": "#BF9000",
    # Дорожки
    "lane_fill": "#E8EDF5",          # Ещё светлее
    "lane_line": "#8FAADC",
    "lane_header_fill": "#4472C4",
    "lane_header_text": "#FFFFFF",
    # Соединители
    "connector_line": "#5A5A5A",     # Чуть мягче
    # Системные метки
    "system_fill": "#E2EFDA",
    "system_line": "#A9D18E",
    "system_text": "#375623",
    # Документ
    "doc_fill": "#FFF2CC",
    "doc_line": "#BF8F00",
    "doc_text": "#806000",
    # Аннотации
    "annotation_fill": "#FFF9E6",
    "annotation_line": "#C0C000",
    "annotation_text": "#404040",
}

# Маркеры типов задач — символы Unicode для обозначения типа
TASK_MARKERS = {
    "userTask": "\u2261",           # ≡ (три линии — человек)
    "serviceTask": "\u2022",        # • (точка — сервис)
    "scriptTask": "\u2022",         # • (точка — скрипт)
    "manualTask": "\u2261",         # ≡ (три линии — ручной)
    "task": "",
}


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _px(val: float) -> float:
    """Конвертирует пиксели BPMN DI в дюймы Visio."""
    return val / PIXELS_PER_INCH


def _visual_text_width(text: str, char_coeff: float = 0.085) -> float:
    """Визуальная ширина текста с учётом emoji (2x) и пробелов (0.5x).

    Emoji (Unicode Symbol Other/Sk, code > U+1F000) занимают ~2x ширины
    кириллического символа в Visio. Пробелы — примерно 0.5x.

    Args:
        text: Строка текста.
        char_coeff: Ширина в дюймах на 1 визуальную единицу.

    Returns:
        Оценка ширины текста в дюймах.
    """
    visual_units = 0.0
    for ch in text:
        cat = unicodedata.category(ch)
        cp = ord(ch)
        # Emoji: Symbol Other/Sk или code > U+1F000
        if cat in ("So", "Sk") or cp > 0x1F000:
            visual_units += 2.0
        elif ch == " ":
            visual_units += 0.5
        else:
            visual_units += 1.0
    return visual_units * char_coeff


def _vis_color(hex_color: str) -> str:
    """Возвращает цвет для .vsdx XML (формат #RRGGBB без изменений)."""
    if not hex_color.startswith("#"):
        return f"#{hex_color}"
    return hex_color


def _shape_base(
    sid: int,
    cx: float, cy: float,
    w: float, h: float,
    name: str = "",
) -> str:
    """Общая XML-основа фигуры: позиционирование.

    GUARD() предотвращает перезапись размеров Visio-движком
    (наследование из мастер-шейпов, стилей, авто-ресайз).
    """
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
        # Защита от авто-ресайза коннекторами Visio
        f'      <Cell N="ShapeFixedCode" V="6"/>\n'
    )


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


def _geom_ellipse(d: float) -> str:
    r = d / 2
    return (
        '      <Section N="Geometry" IX="0">\n'
        '        <Cell N="NoFill" V="0"/>\n'
        '        <Cell N="NoLine" V="0"/>\n'
        '        <Cell N="NoShow" V="0"/>\n'
        '        <Cell N="NoSnap" V="0"/>\n'
        '        <Cell N="NoQuickDrag" V="0"/>\n'
        f'        <Row T="Ellipse" IX="1">'
        f'<Cell N="X" V="{r:.4f}"/>'
        f'<Cell N="Y" V="{r:.4f}"/>'
        f'<Cell N="A" V="{d:.4f}"/>'
        f'<Cell N="B" V="{r:.4f}"/>'
        f'<Cell N="C" V="{r:.4f}"/>'
        f'<Cell N="D" V="{d:.4f}"/>'
        f'</Row>\n'
        '      </Section>\n'
    )


# Ширина заголовка дорожки (дюймы) — используется и в _lane_shapes, и для clamp labels
_LANE_HEADER_W = 0.50


class DirectVsdxGenerator:
    """Генератор профессиональных .vsdx файлов с BPMN-нотацией.

    Создаёт Visio-файлы с полной BPMN-стилизацией:
    дорожки с заголовками, маркеры типов задач, системные метки,
    аннотации и документы.
    """

    def __init__(self) -> None:
        self._shape_id = 0
        self._page_width = 33.11
        self._page_height = 46.81
        self._step_systems: dict[str, str] = {}   # имя шага → система
        self._step_inputs: dict[str, list[str]] = {}   # имя шага → входы
        self._step_outputs: dict[str, list[str]] = {}  # имя шага → выходы

    def generate(
        self,
        bpmn_json: dict[str, Any],
        output_path: Path,
        process_data: dict[str, Any] | None = None,
    ) -> Path:
        """Генерирует Visio-файл из BPMN JSON.

        Args:
            bpmn_json: BPMN JSON с элементами, потоками.
            output_path: Путь для сохранения .vsdx.
            process_data: Доп. данные процесса (шаги, системы, pain_points).

        Returns:
            Путь к файлу.
        """
        try:
            # Вычисляем layout, если его нет
            if "layout" not in bpmn_json or not bpmn_json.get("layout"):
                from app.bpmn.layout import BpmnLayout
                layout_engine = BpmnLayout()
                layout = layout_engine.calculate_layout(bpmn_json)
                bpmn_json = {**bpmn_json, "layout": layout}

            # Загружаем доп. данные о шагах (системы, вх/вых)
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

            self._compute_page_size(element_positions, lane_positions)

            shapes: list[str] = []

            # 1. Дорожки (фон + заголовок)
            for lane_id, lane_pos in lane_positions.items():
                name = lane_names.get(lane_id, lane_pos.get("name", lane_id))
                shapes.extend(self._lane_shapes(name, lane_pos))

            # 2. Элементы (задачи, события, шлюзы)
            for elem in elements:
                eid = elem.get("id", "")
                pos = element_positions.get(eid)
                if pos:
                    shapes.extend(self._element_shapes(elem, pos))

            # 3. Соединители — один Shape с множеством Geometry секций.
            # Visio при наличии множества отдельных connector-шейпов
            # запускает auto-routing, который переопределяет Width
            # соседних фигур (даже c GUARD). Объединение в одну
            # фигуру полностью обходит эту проблему.
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

    # ------------------------------------------------------------------
    # Метаданные шагов
    # ------------------------------------------------------------------

    def _load_step_metadata(self, process_data: dict[str, Any] | None) -> None:
        """Загружает системы и документы из данных процесса."""
        self._step_systems.clear()
        self._step_inputs.clear()
        self._step_outputs.clear()
        if not process_data:
            return
        for step in process_data.get("steps") or []:
            name = step.get("name", "")
            system = step.get("system", "")
            if name and system:
                self._step_systems[name] = system
            inputs = step.get("inputs") or []
            outputs = step.get("outputs") or []
            if inputs:
                self._step_inputs[name] = inputs
            if outputs:
                self._step_outputs[name] = outputs

    # ------------------------------------------------------------------
    # Размер страницы
    # ------------------------------------------------------------------

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
        self._page_width = max(11.0, max_x + 0.75)
        self._page_height = max(8.5, max_y + 0.75)

    def _next_id(self) -> int:
        self._shape_id += 1
        return self._shape_id

    def _flip_y(self, y_in: float) -> float:
        """Инвертирует Y для Visio (снизу вверх)."""
        return self._page_height - y_in

    # ==================================================================
    # Дорожка (swimlane)
    # ==================================================================

    def _lane_shapes(self, name: str, pos: dict) -> list[str]:
        """Создаёт дорожку: фон + заголовок слева."""
        parts: list[str] = []
        x = _px(pos.get("x", 0))
        y = _px(pos.get("y", 0))
        w = _px(pos.get("width", 600))
        h = _px(pos.get("height", 200))

        # Фон дорожки (с рамкой)
        parts.append(self._make_rect(
            x, y, w, h,
            fill=COLORS["lane_fill"],
            line=COLORS["lane_line"],
            line_weight=0.010,
        ))

        # Заголовок слева — повёрнутый текстовый блок
        header_w = _LANE_HEADER_W
        parts.append(self._make_lane_header(
            x, y, header_w, h, name,
        ))

        return parts

    def _make_lane_header(
        self,
        x: float, y: float, w: float, h: float,
        name: str,
    ) -> str:
        """Заголовок дорожки — вертикальный текст на цветном фоне.

        Создаёт узкий прямоугольник с тёмным фоном и белым текстом,
        повёрнутым на 90° (чтение снизу вверх).
        Текстовый блок растягивается на всю высоту дорожки,
        чтобы длинные названия помещались в одну строку.
        """
        sid = self._next_id()
        cx = x + w / 2
        cy = self._flip_y(y + h / 2)
        fill_v = _vis_color(COLORS["lane_header_fill"])
        line_v = _vis_color(COLORS["lane_line"])
        text_v = _vis_color(COLORS["lane_header_text"])
        txt_angle = math.pi / 2  # 90° CCW — снизу вверх

        return (
            _shape_base(sid, cx, cy, w, h, name=name)
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{line_v}"/>\n'
            + f'      <Cell N="LineWeight" V="0.012"/>\n'
            + f'      <Cell N="LinePattern" V="1"/>\n'
            + f'      <Cell N="Char.Color" V="{text_v}"/>\n'
            + f'      <Cell N="Char.Size" V="0.09"/>\n'
            + f'      <Cell N="Char.Style" V="1"/>\n'  # Bold
            + f'      <Cell N="Para.HorzAlign" V="1"/>\n'  # Center
            + f'      <Cell N="VerticalAlign" V="1"/>\n'   # Middle
            # Текстовый блок: ширина = высота дорожки, высота = ширина заголовка
            + f'      <Cell N="TxtWidth" V="{h:.4f}"/>\n'
            + f'      <Cell N="TxtHeight" V="{w:.4f}"/>\n'
            + f'      <Cell N="TxtPinX" V="{w / 2:.4f}" F="Width*0.5"/>\n'
            + f'      <Cell N="TxtPinY" V="{h / 2:.4f}" F="Height*0.5"/>\n'
            + f'      <Cell N="TxtLocPinX" V="{h / 2:.4f}" F="TxtWidth*0.5"/>\n'
            + f'      <Cell N="TxtLocPinY" V="{w / 2:.4f}" F="TxtHeight*0.5"/>\n'
            + f'      <Cell N="TxtAngle" V="{txt_angle:.6f}"/>\n'
            + f'      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + f"      <Text>{xml_escape(name)}</Text>\n"
            + "    </Shape>"
        )

    # ==================================================================
    # Элементы BPMN
    # ==================================================================

    def _element_shapes(self, elem: dict, pos: dict) -> list[str]:
        """Создаёт фигуры для BPMN-элемента + дополнительные метки."""
        parts: list[str] = []
        etype = elem.get("type", "task")
        name = elem.get("name", "")
        x = _px(pos.get("x", 0))
        y = _px(pos.get("y", 0))
        w = _px(pos.get("width", 120))
        h = _px(pos.get("height", 80))

        if etype == "startEvent":
            r = _px(pos.get("width", 36)) / 2
            cx_px = pos.get("x", 0) + pos.get("width", 36) / 2
            cy_px = pos.get("y", 0) + pos.get("height", 36) / 2
            # Круг с иконкой ▶ внутри (текст встроен в фигуру)
            parts.append(self._make_circle(
                cx_px, cy_px, r,
                fill=COLORS["start_fill"],
                line=COLORS["start_line"],
                line_weight=0.03,
                text="\u25B6", font_size=0.12,
                text_color="#FFFFFF",
            ))
            # Подпись под событием — ограниченная ширина + word wrap
            if name:
                label_w, label_h = self._label_dims(name, 0.07, 0.065, max_w=1.4)
                min_lx = _px(30) + _LANE_HEADER_W + 0.03
                label_x = max(min_lx, x + w / 2 - label_w / 2)
                parts.append(self._make_label(
                    label_x,
                    y + _px(pos.get("height", 36)) + 0.10,
                    label_w, label_h,
                    text=name, font_size=0.065,
                    text_color="#375623",
                ))

        elif etype == "endEvent":
            r = _px(pos.get("width", 36)) / 2
            cx_px = pos.get("x", 0) + pos.get("width", 36) / 2
            cy_px = pos.get("y", 0) + pos.get("height", 36) / 2
            # Круг с иконкой ■ внутри (текст встроен в фигуру)
            parts.append(self._make_circle(
                cx_px, cy_px, r,
                fill=COLORS["end_fill"],
                line=COLORS["end_line"],
                line_weight=0.05,
                text="\u25A0", font_size=0.14,
                text_color="#FFFFFF",
            ))
            if name:
                label_w, label_h = self._label_dims(name, 0.07, 0.065, max_w=1.4)
                min_lx = _px(30) + _LANE_HEADER_W + 0.03
                label_x = max(min_lx, x + w / 2 - label_w / 2)
                parts.append(self._make_label(
                    label_x,
                    y + _px(pos.get("height", 36)) + 0.10,
                    label_w, label_h,
                    text=name, font_size=0.065,
                    text_color="#C00000",
                ))

        elif "Gateway" in etype or "gateway" in etype:
            markers = {
                "exclusiveGateway": "\u00D7",   # × знак умножения
                "parallelGateway": "+",
                "inclusiveGateway": "\u25CB",   # ○ круг
                "eventBasedGateway": "\u2605",  # ★ звезда
            }
            marker = markers.get(etype, "\u00D7")
            parts.append(self._make_diamond(
                x, y, w, h,
                fill=COLORS["gateway_fill"],
                line=COLORS["gateway_line"],
                marker=marker,
            ))
            # Подпись шлюза — ограниченная ширина + word wrap
            if name:
                label_w, label_h = self._label_dims(name, 0.07, 0.06)
                label_w = max(label_w, w + 0.2)  # мин: шлюз + 0.2"
                parts.append(self._make_label(
                    x + w / 2 - label_w / 2,
                    y + h + 0.04,
                    label_w, label_h,
                    text=name, font_size=0.06,
                    text_color="#806000",
                    italic=True,
                ))

        else:
            # Задача (userTask, serviceTask, task, и т.д.)
            task_colors = {
                "userTask": (COLORS["user_task_fill"], COLORS["user_task_line"]),
                "serviceTask": (COLORS["service_task_fill"], COLORS["service_task_line"]),
            }
            fill, line_c = task_colors.get(
                etype, (COLORS["task_fill"], COLORS["task_line"]),
            )

            # Иконка типа встраивается в текст (надёжнее отдельного shape)
            marker = TASK_MARKERS.get(etype, "")
            display_name = f"{marker} {name}" if marker else name

            parts.append(self._make_rect(
                x, y, w, h,
                fill=fill, line=line_c,
                text=display_name,
                text_color=COLORS["task_text"],
                rounding=0.06,
                line_weight=0.012,
                font_size=0.075,
                left_margin=0.04,
                right_margin=0.04,
                top_margin=0.03,
                bottom_margin=0.03,
            ))

            # === Бейджи под задачей (вертикальный стек) ===
            badge_y = y + h + 0.12  # начало стека под задачей
            max_badge_w = w  # бейджи не шире задачи

            # Системная метка
            system = self._step_systems.get(name, "")
            if system:
                sys_text = system  # просто название системы (цвет отличает)
                sys_w = min(self._badge_w(sys_text), max_badge_w)
                sys_h = self._badge_h(sys_text, sys_w)
                parts.append(self._make_system_badge(
                    x + w / 2 - sys_w / 2, badge_y,
                    sys_text, sys_w, sys_h,
                ))
                badge_y += sys_h + 0.10  # зазор между бейджами

            # Входные документы
            inputs_list = self._step_inputs.get(name, [])
            if inputs_list:
                doc_text = inputs_list[0]  # просто название (цвет отличает)
                doc_w = min(self._badge_w(doc_text), max_badge_w)
                doc_h = self._badge_h(doc_text, doc_w)
                parts.append(self._make_doc_badge(
                    x + w / 2 - doc_w / 2,
                    badge_y,
                    doc_text, doc_w, doc_h,
                    is_input=True,
                ))
                badge_y += doc_h + 0.10

            # Выходные документы
            outputs = self._step_outputs.get(name, [])
            if outputs:
                doc_text = outputs[0]  # просто название (цвет отличает)
                doc_w = min(self._badge_w(doc_text), max_badge_w)
                doc_h = self._badge_h(doc_text, doc_w)
                parts.append(self._make_doc_badge(
                    x + w / 2 - doc_w / 2,
                    badge_y,
                    doc_text, doc_w, doc_h,
                ))

        return parts

    # ==================================================================
    # Примитивы фигур
    # ==================================================================

    def _make_rect(
        self,
        x: float, y: float, w: float, h: float,
        fill: str, line: str, text: str = "",
        text_color: str = "#000000",
        rounding: float = 0.0,
        line_weight: float = 0.01,
        font_size: float = 0.1111,
        text_angle: float = 0,
        left_margin: float = 0.0,
        right_margin: float = 0.0,
        top_margin: float = 0.0,
        bottom_margin: float = 0.0,
    ) -> str:
        sid = self._next_id()
        cx = x + w / 2
        cy = self._flip_y(y + h / 2)
        fill_v = _vis_color(fill)
        line_v = _vis_color(line)
        text_v = _vis_color(text_color)
        text_esc = xml_escape(text) if text else ""
        text_block = f"      <Text>{text_esc}</Text>\n" if text_esc else ""

        # Поворот текста
        angle_cell = ""
        if text_angle:
            rad = math.radians(text_angle)
            angle_cell = f'      <Cell N="TxtAngle" V="{rad:.6f}"/>\n'

        # Отступы текста от границ фигуры
        margin_cells = ""
        if left_margin > 0:
            margin_cells += f'      <Cell N="LeftMargin" V="{left_margin:.4f}"/>\n'
        if right_margin > 0:
            margin_cells += f'      <Cell N="RightMargin" V="{right_margin:.4f}"/>\n'
        if top_margin > 0:
            margin_cells += f'      <Cell N="TopMargin" V="{top_margin:.4f}"/>\n'
        if bottom_margin > 0:
            margin_cells += f'      <Cell N="BottomMargin" V="{bottom_margin:.4f}"/>\n'

        return (
            _shape_base(sid, cx, cy, w, h)
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{line_v}"/>\n'
            + f'      <Cell N="LineWeight" V="{line_weight:.4f}"/>\n'
            + f'      <Cell N="LinePattern" V="1"/>\n'
            + f'      <Cell N="Rounding" V="{rounding:.4f}"/>\n'
            + f'      <Cell N="Char.Color" V="{text_v}"/>\n'
            + f'      <Cell N="Char.Size" V="{font_size:.4f}"/>\n'
            + f'      <Cell N="Para.HorzAlign" V="1"/>\n'
            + f'      <Cell N="VerticalAlign" V="1"/>\n'
            + margin_cells
            + f'      <Cell N="ObjType" V="1"/>\n'
            + angle_cell
            + GEOM_RECT
            + text_block
            + "    </Shape>"
        )

    def _make_circle(
        self,
        cx_px: float, cy_px: float, radius: float,
        fill: str, line: str,
        line_weight: float = 0.02,
        text: str = "",
        text_color: str = "#FFFFFF",
        font_size: float = 0.12,
    ) -> str:
        sid = self._next_id()
        d = radius * 2
        cx = _px(cx_px)
        cy = self._flip_y(_px(cy_px))
        fill_v = _vis_color(fill)
        line_v = _vis_color(line)
        text_v = _vis_color(text_color)

        text_block = ""
        text_cells = ""
        if text:
            text_block = f"      <Text>{xml_escape(text)}</Text>\n"
            text_cells = (
                f'      <Cell N="Char.Color" V="{text_v}"/>\n'
                f'      <Cell N="Char.Size" V="{font_size:.4f}"/>\n'
                f'      <Cell N="Para.HorzAlign" V="1"/>\n'
                f'      <Cell N="VerticalAlign" V="1"/>\n'
            )

        return (
            _shape_base(sid, cx, cy, d, d)
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{line_v}"/>\n'
            + f'      <Cell N="LineWeight" V="{line_weight:.4f}"/>\n'
            + f'      <Cell N="LinePattern" V="1"/>\n'
            + f'      <Cell N="ObjType" V="1"/>\n'
            + text_cells
            + _geom_ellipse(d)
            + text_block
            + "    </Shape>"
        )

    def _make_diamond(
        self,
        x: float, y: float, w: float, h: float,
        fill: str, line: str, marker: str = "\u00D7",
    ) -> str:
        sid = self._next_id()
        cx = x + w / 2
        cy = self._flip_y(y + h / 2)
        fill_v = _vis_color(fill)
        line_v = _vis_color(line)

        return (
            _shape_base(sid, cx, cy, w, h)
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{line_v}"/>\n'
            + f'      <Cell N="LineWeight" V="0.0139"/>\n'
            + f'      <Cell N="LinePattern" V="1"/>\n'
            + f'      <Cell N="Char.Size" V="0.14"/>\n'
            + f'      <Cell N="Char.Style" V="1"/>\n'
            + f'      <Cell N="Para.HorzAlign" V="1"/>\n'
            + f'      <Cell N="VerticalAlign" V="1"/>\n'
            + f'      <Cell N="ObjType" V="1"/>\n'
            + GEOM_DIAMOND
            + f"      <Text>{xml_escape(marker)}</Text>\n"
            + "    </Shape>"
        )

    def _make_task_icon(
        self,
        x: float, y: float, size: float, marker: str,
    ) -> str:
        """Иконка типа задачи — маленький overlay в верхнем-левом углу.

        Прозрачный фон, без рамки — только символ Unicode.
        Размещается поверх прямоугольника задачи.
        """
        sid = self._next_id()
        cx = x + size / 2
        cy = self._flip_y(y + size / 2)
        return (
            _shape_base(sid, cx, cy, size, size, name="TaskIcon")
            + f'      <Cell N="FillPattern" V="0"/>\n'
            + f'      <Cell N="LinePattern" V="0"/>\n'
            + f'      <Cell N="Char.Color" V="#FFFFFF"/>\n'
            + f'      <Cell N="Char.Size" V="0.11"/>\n'
            + f'      <Cell N="Para.HorzAlign" V="1"/>\n'
            + f'      <Cell N="VerticalAlign" V="1"/>\n'
            + f'      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + f"      <Text>{xml_escape(marker)}</Text>\n"
            + "    </Shape>"
        )

    def _make_label(
        self,
        x: float, y: float, w: float, h: float,
        text: str, font_size: float = 0.08,
        text_color: str = "#000000",
        italic: bool = False,
    ) -> str:
        """Текстовая метка — реализована как прямоугольник с фоном дорожки.

        Visio игнорирует Width для текстового блока в фигурах без
        видимой заливки (FillPattern=0). Поэтому используем полноценный
        прямоугольник с заливкой цвета дорожки для корректного переноса.
        """
        sid = self._next_id()
        cx = x + w / 2
        cy = self._flip_y(y + h / 2)
        text_v = _vis_color(text_color)
        fill_v = _vis_color(COLORS["lane_fill"])

        char_style = ""
        if italic:
            char_style = '      <Cell N="Char.Style" V="2"/>\n'

        return (
            _shape_base(sid, cx, cy, w, h)
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{fill_v}"/>\n'
            + f'      <Cell N="LineWeight" V="0.001"/>\n'
            + f'      <Cell N="LinePattern" V="1"/>\n'
            + f'      <Cell N="Rounding" V="0.0000"/>\n'
            + f'      <Cell N="Char.Color" V="{text_v}"/>\n'
            + f'      <Cell N="Char.Size" V="{font_size:.4f}"/>\n'
            + char_style
            + f'      <Cell N="Para.HorzAlign" V="1"/>\n'
            + f'      <Cell N="VerticalAlign" V="1"/>\n'
            + f'      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + f"      <Text>{xml_escape(text)}</Text>\n"
            + "    </Shape>"
        )

    # ------------------------------------------------------------------
    # Утилиты размеров (бейджи, labels)
    # ------------------------------------------------------------------

    @staticmethod
    def _label_dims(
        text: str,
        char_coeff: float = 0.07,
        font_size: float = 0.065,
        max_w: float = 1.8,
        min_w: float = 0.8,
    ) -> tuple[float, float]:
        """Вычисляет (width, height) для текстовой метки с word wrap.

        Ширина ограничена max_w, при превышении текст переносится
        и высота увеличивается.
        """
        raw_w = _visual_text_width(text, char_coeff=char_coeff)
        label_w = max(min(raw_w + 0.1, max_w), min_w)
        # Сколько строк нужно
        visual_len = _visual_text_width(text, char_coeff=1.0)
        chars_per_line = max(1, int(label_w / char_coeff))
        lines = max(1, math.ceil(visual_len / chars_per_line))
        label_h = max(0.30, font_size * 1.8 * lines + 0.06)
        return label_w, label_h

    @staticmethod
    def _badge_w(text: str) -> float:
        """Ширина бейджа: visual_text_width + padding 0.14"."""
        text_w = _visual_text_width(text, char_coeff=0.075)
        return max(text_w + 0.14, 0.8)

    @staticmethod
    def _badge_h(
        text: str, badge_w: float, font_size: float = 0.06,
    ) -> float:
        """Динамическая высота бейджа: 0.22" для 1 строки, больше для 2+.

        Учитывает word-wrap в Visio: текст переносится по словам,
        а не по символам, что увеличивает кол-во строк.
        """
        # Фактическая ширина текстовой области в Visio (за вычетом LeftMargin + RightMargin)
        usable = badge_w - 0.08
        # word-wrap penalty ~20%: Visio переносит по словам, теряя место
        effective_per_line = max(1, int(usable / 0.075 * 0.80))
        visual_len = _visual_text_width(text, char_coeff=1.0)
        lines = max(1, math.ceil(visual_len / effective_per_line))
        return max(0.22, font_size * 2.0 * lines + 0.10)

    # ------------------------------------------------------------------
    # Бейджи
    # ------------------------------------------------------------------

    def _make_system_badge(
        self,
        x: float, y: float, system: str,
        w: float, h: float,
    ) -> str:
        """Цветная метка системы (⚙ 1С:ERP, и т.д.) под задачей."""
        sid = self._next_id()
        cx = x + w / 2
        cy = self._flip_y(y + h / 2)
        fill_v = _vis_color(COLORS["system_fill"])
        line_v = _vis_color(COLORS["system_line"])
        text_v = _vis_color(COLORS["system_text"])

        return (
            _shape_base(sid, cx, cy, w, h)
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{line_v}"/>\n'
            + f'      <Cell N="LineWeight" V="0.006"/>\n'
            + f'      <Cell N="LinePattern" V="1"/>\n'
            + f'      <Cell N="Rounding" V="0.05"/>\n'
            + f'      <Cell N="Char.Color" V="{text_v}"/>\n'
            + f'      <Cell N="Char.Size" V="0.06"/>\n'
            + f'      <Cell N="Char.Style" V="1"/>\n'
            + f'      <Cell N="Para.HorzAlign" V="1"/>\n'
            + f'      <Cell N="VerticalAlign" V="1"/>\n'
            + f'      <Cell N="LeftMargin" V="0.04"/>\n'
            + f'      <Cell N="RightMargin" V="0.04"/>\n'
            + f'      <Cell N="TopMargin" V="0.02"/>\n'
            + f'      <Cell N="BottomMargin" V="0.02"/>\n'
            + f'      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + f"      <Text>{xml_escape(system)}</Text>\n"
            + "    </Shape>"
        )

    def _make_doc_badge(
        self,
        x: float, y: float, text: str,
        w: float, h: float,
        is_input: bool = False,
    ) -> str:
        """Документ — плоский скруглённый прямоугольник (flat modern).

        is_input=True — входной документ (серо-голубой, 📥).
        is_input=False — выходной документ (жёлтый, 📤).
        """
        sid = self._next_id()
        cx = x + w / 2
        cy = self._flip_y(y + h / 2)
        if is_input:
            fill_v = _vis_color("#DAEEF3")
            line_v = _vis_color("#5B9BD5")
            text_v = _vis_color("#1F4E79")
        else:
            fill_v = _vis_color(COLORS["doc_fill"])
            line_v = _vis_color(COLORS["doc_line"])
            text_v = _vis_color(COLORS["doc_text"])

        return (
            _shape_base(sid, cx, cy, w, h)
            + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
            + f'      <Cell N="FillPattern" V="1"/>\n'
            + f'      <Cell N="LineColor" V="{line_v}"/>\n'
            + f'      <Cell N="LineWeight" V="0.006"/>\n'
            + f'      <Cell N="LinePattern" V="1"/>\n'
            + f'      <Cell N="Rounding" V="0.05"/>\n'
            + f'      <Cell N="Char.Color" V="{text_v}"/>\n'
            + f'      <Cell N="Char.Size" V="0.06"/>\n'
            + f'      <Cell N="Char.Style" V="2"/>\n'  # Italic
            + f'      <Cell N="Para.HorzAlign" V="1"/>\n'
            + f'      <Cell N="VerticalAlign" V="1"/>\n'
            + f'      <Cell N="LeftMargin" V="0.04"/>\n'
            + f'      <Cell N="RightMargin" V="0.04"/>\n'
            + f'      <Cell N="TopMargin" V="0.02"/>\n'
            + f'      <Cell N="BottomMargin" V="0.02"/>\n'
            + f'      <Cell N="ObjType" V="1"/>\n'
            + GEOM_RECT
            + f"      <Text>{xml_escape(text)}</Text>\n"
            + "    </Shape>"
        )

    # ==================================================================
    # Соединитель
    # ==================================================================

    def _make_all_connectors(
        self,
        connector_geoms: list[tuple[list[dict], str]],
    ) -> str:
        """Все соединители в ОДНОМ Shape с множеством Geometry секций.

        Visio при наличии множества отдельных connector-шейпов запускает
        auto-routing, который переопределяет Width соседних фигур
        (даже с GUARD). Объединение всех коннекторов в одну фигуру
        полностью обходит эту проблему.

        Каждый коннектор — отдельная ``<Section N="Geometry" IX="N">``.
        ``EndArrow`` рисуется на конце каждой Geometry секции.

        Текстовые подписи на коннекторах — отдельные label-фигуры
        (ObjType=1, обычные прямоугольники — не влияют на routing).
        """
        # Конвертируем все waypoints в Visio-координаты (inches, Y flipped)
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

        # Bounding box всех коннекторов (с маленьким запасом)
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
        line_v = _vis_color(COLORS["connector_line"])

        # Geometry секции — одна на каждый коннектор
        geom_parts: list[str] = []
        for idx, vis_pts in enumerate(all_vis_paths):
            rows: list[str] = []
            for i, (px, py) in enumerate(vis_pts):
                # Относительные координаты (0..1) внутри bounding box
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

        # Основной shape — одна фигура со всеми коннекторами
        connector_shape = (
            _shape_base(sid, cx, cy, w, h, name="Connectors")
            + f'      <Cell N="LineColor" V="{line_v}"/>\n'
            + f'      <Cell N="LineWeight" V="0.0100"/>\n'
            + f'      <Cell N="LinePattern" V="1"/>\n'
            + f'      <Cell N="EndArrow" V="13"/>\n'
            + f'      <Cell N="EndArrowSize" V="2"/>\n'
            + f'      <Cell N="FillPattern" V="0"/>\n'
            + f'      <Cell N="ObjType" V="1"/>\n'
            + all_geom
            + "    </Shape>"
        )

        # Текстовые подписи — отдельные label-фигуры для коннекторов
        # с текстом (обычные Shape ObjType=1, не влияют на routing)
        labels: list[str] = []
        for vis_pts, text in zip(all_vis_paths, all_texts):
            if not text:
                continue
            # Позиция метки — середина пути коннектора
            mid = len(vis_pts) // 2
            mx, my = vis_pts[mid]
            label_w = max(_visual_text_width(text, char_coeff=0.055), 0.3)
            label_h = 0.16
            lsid = self._next_id()

            # Определяем направление сегмента для правильного offset
            p_prev = vis_pts[max(0, mid - 1)]
            p_curr = vis_pts[mid]
            dx = abs(p_curr[0] - p_prev[0])
            dy = abs(p_curr[1] - p_prev[1])
            if dy > dx:
                # Вертикальный сегмент — смещаем вправо от линии
                label_cx = mx + label_w / 2 + 0.05
                label_cy = my
            else:
                # Горизонтальный — смещаем вверх от линии
                label_cx = mx
                label_cy = my + 0.10
            text_v = _vis_color("#404040")
            fill_v = _vis_color(COLORS["lane_fill"])
            labels.append(
                _shape_base(lsid, label_cx, label_cy, label_w, label_h)
                + f'      <Cell N="FillForegnd" V="{fill_v}"/>\n'
                + f'      <Cell N="FillBkgnd" V="{fill_v}"/>\n'
                + f'      <Cell N="FillPattern" V="1"/>\n'
                + f'      <Cell N="LineColor" V="{fill_v}"/>\n'
                + f'      <Cell N="LineWeight" V="0.001"/>\n'
                + f'      <Cell N="LinePattern" V="1"/>\n'
                + f'      <Cell N="Char.Color" V="{text_v}"/>\n'
                + f'      <Cell N="Char.Size" V="0.055"/>\n'
                + f'      <Cell N="Char.Style" V="2"/>\n'
                + f'      <Cell N="Para.HorzAlign" V="1"/>\n'
                + f'      <Cell N="VerticalAlign" V="1"/>\n'
                + f'      <Cell N="ObjType" V="1"/>\n'
                + GEOM_RECT
                + f"      <Text>{xml_escape(text)}</Text>\n"
                + "    </Shape>"
            )

        # Возвращаем основную фигуру + все метки
        parts = [connector_shape] + labels
        return "\n".join(parts)


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
