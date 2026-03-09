"""Шаблоны фигур Visio для BPMN элементов.

Содержит константы размеров, цвета, шрифты и маппинг типов
BPMN-элементов на мастер-фигуры Visio.

Обновлено для соответствия стилю Bitrix24:
- белые задачи с цветной акцент-полосой слева
- тёмные широкие заголовки дорожек
- геометрические BPMN-события без emoji
"""

from __future__ import annotations

# ----------------------------------------------------------------------
# Размеры фигур (в дюймах для Visio)
# ----------------------------------------------------------------------

#: Размеры задач (task, userTask, serviceTask и т.д.) — 200×100 px / 96
TASK_WIDTH: float = 2.083
TASK_HEIGHT: float = 1.042

#: Размеры шлюзов (ромб) — 50×50 px / 96
GATEWAY_SIZE: float = 0.521

#: Размеры событий (круг) — ~40px / 96
EVENT_SIZE: float = 0.40

#: Ширина заголовка дорожки (широкий тёмный блок с названием)
LANE_HEADER_WIDTH: float = 0.70

#: Высота заголовка пула
POOL_HEADER_HEIGHT: float = 0.3

#: Минимальная высота дорожки
LANE_MIN_HEIGHT: float = 2.0

#: Минимальная ширина дорожки
LANE_MIN_WIDTH: float = 8.0

#: Размеры подпроцесса
SUBPROCESS_WIDTH: float = 2.5
SUBPROCESS_HEIGHT: float = 1.5

#: Размеры объектов данных
DATA_OBJECT_WIDTH: float = 0.5
DATA_OBJECT_HEIGHT: float = 0.6

#: Размеры текстовых аннотаций
ANNOTATION_WIDTH: float = 1.5
ANNOTATION_HEIGHT: float = 0.5

# ----------------------------------------------------------------------
# Отступы и интервалы (в дюймах)
# ----------------------------------------------------------------------

#: Горизонтальный интервал между элементами — 270px / 96
HORIZONTAL_SPACING: float = 2.813

#: Вертикальный интервал между элементами при ветвлении — 250px / 96
VERTICAL_SPACING: float = 2.604

#: Отступ от левого края страницы
LEFT_MARGIN: float = 1.0

#: Отступ от верхнего края страницы
TOP_MARGIN: float = 0.75

#: Внутренний отступ внутри дорожки
LANE_PADDING: float = 0.5

# ----------------------------------------------------------------------
# Цвета (RGB hex) — стиль Bitrix24
# ----------------------------------------------------------------------

#: Ширина акцент-полосы задачи (5pt = 0.069")
ACCENT_BAR_WIDTH: float = 0.069

#: Заливка задачи — белая
TASK_FILL: str = "#FFFFFF"

#: Граница задачи — светло-серая
TASK_BORDER: str = "#CBD4E1"

#: Цвет текста задачи — почти чёрный
TASK_TEXT: str = "#1A202C"

#: Скругление углов задачи (6pt)
TASK_ROUNDING: float = 0.0833

#: Заливка шлюза — светло-жёлтая
GATEWAY_FILL: str = "#FFF8E7"

#: Граница шлюза
GATEWAY_LINE: str = "#F9A825"

#: Цвет соединителей
CONNECTOR_LINE: str = "#5A6475"

COLORS: dict[str, str] = {
    # Задачи
    "task_fill": TASK_FILL,
    "task_stroke": TASK_BORDER,
    "task_text": TASK_TEXT,
    # Шлюзы
    "gateway_fill": GATEWAY_FILL,
    "gateway_stroke": GATEWAY_LINE,
    # Стартовые события
    "start_fill": "#F1FAF1",
    "start_stroke": "#43A047",
    # Конечные события
    "end_fill": "#FFF0EE",
    "end_stroke": "#E53935",
    # Промежуточные события (таймер)
    "intermediate_fill": "#FFFDE7",
    "intermediate_stroke": "#F9A825",
    # Дорожки (заглушка, реальные берутся из LANE_PALETTE_V2)
    "lane_fill": "#EEF2FA",
    "lane_stroke": "#C5D3E8",
    "lane_header_fill": "#2B5091",
    "lane_header_text": "#FFFFFF",
    # Соединители
    "connector_stroke": CONNECTOR_LINE,
    # Подпроцессы
    "subprocess_fill": "#F3E5F5",
    "subprocess_stroke": "#7B1FA2",
    # Объекты данных
    "data_fill": "#E0F7FA",
    "data_stroke": "#00838F",
    # Аннотации
    "annotation_fill": "#FFFDE7",
    "annotation_stroke": "#F9A825",
}

# ----------------------------------------------------------------------
# Палитра дорожек (стиль Bitrix24)
# Каждая запись: (bg_fill, accent_color, dark_header, border_color)
# ----------------------------------------------------------------------

LANE_PALETTE_V2: list[tuple[str, str, str, str]] = [
    ("#EEF2FA", "#4472C4", "#2B5091", "#C5D3E8"),  # Синий
    ("#EEF5EE", "#4CAF50", "#2E7D32", "#C3DFC3"),  # Зелёный
    ("#FFF8E7", "#F9A825", "#F57F17", "#F0DAAA"),  # Жёлтый
    ("#FEF0EE", "#E53935", "#B71C1C", "#F0C4C2"),  # Красный
    ("#F3EEF9", "#7B1FA2", "#4A148C", "#D4BEDF"),  # Фиолетовый
    ("#E8F8F8", "#00796B", "#004D40", "#B0D5D2"),  # Бирюзовый
    ("#FFF3E0", "#E65100", "#BF360C", "#F0C89A"),  # Оранжевый
]

# ----------------------------------------------------------------------
# Настройки шрифтов
# ----------------------------------------------------------------------

#: Имя шрифта
FONT_NAME: str = "Calibri"

#: Размер шрифта для меток элементов (pt)
FONT_SIZE_LABEL: int = 11

#: Размер шрифта для заголовков дорожек/пулов (pt)
FONT_SIZE_HEADER: int = 12

#: Размер шрифта для аннотаций (pt)
FONT_SIZE_ANNOTATION: int = 8

# ----------------------------------------------------------------------
# Толщина линий (pt)
# ----------------------------------------------------------------------

#: Обводка фигур
LINE_WEIGHT_SHAPE: float = 0.75

#: Обводка событий
LINE_WEIGHT_EVENT: float = 1.5

#: Конечные события (жирная обводка — 3pt)
LINE_WEIGHT_END_EVENT: float = 3.0

#: Соединительные линии
LINE_WEIGHT_CONNECTOR: float = 0.75

#: Обводка пулов/дорожек
LINE_WEIGHT_LANE: float = 0.5

# ----------------------------------------------------------------------
# Маппинг типов BPMN-элементов на мастер-фигуры Visio
# ----------------------------------------------------------------------

BPMN_SHAPE_MAP: dict[str, dict[str, object]] = {
    # --- Задачи ---
    "task": {
        "shape": "rectangle",
        "width": TASK_WIDTH,
        "height": TASK_HEIGHT,
        "fill_color": "task_fill",
        "stroke_color": "task_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": TASK_ROUNDING,
    },
    "userTask": {
        "shape": "rectangle",
        "width": TASK_WIDTH,
        "height": TASK_HEIGHT,
        "fill_color": "task_fill",
        "stroke_color": "task_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": TASK_ROUNDING,
    },
    "serviceTask": {
        "shape": "rectangle",
        "width": TASK_WIDTH,
        "height": TASK_HEIGHT,
        "fill_color": "task_fill",
        "stroke_color": "task_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": TASK_ROUNDING,
    },
    "scriptTask": {
        "shape": "rectangle",
        "width": TASK_WIDTH,
        "height": TASK_HEIGHT,
        "fill_color": "task_fill",
        "stroke_color": "task_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": TASK_ROUNDING,
    },
    "manualTask": {
        "shape": "rectangle",
        "width": TASK_WIDTH,
        "height": TASK_HEIGHT,
        "fill_color": "task_fill",
        "stroke_color": "task_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": TASK_ROUNDING,
    },
    # --- Шлюзы ---
    "exclusiveGateway": {
        "shape": "diamond",
        "width": GATEWAY_SIZE,
        "height": GATEWAY_SIZE,
        "fill_color": "gateway_fill",
        "stroke_color": "gateway_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "marker": "X",
    },
    "parallelGateway": {
        "shape": "diamond",
        "width": GATEWAY_SIZE,
        "height": GATEWAY_SIZE,
        "fill_color": "gateway_fill",
        "stroke_color": "gateway_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "marker": "+",
    },
    "inclusiveGateway": {
        "shape": "diamond",
        "width": GATEWAY_SIZE,
        "height": GATEWAY_SIZE,
        "fill_color": "gateway_fill",
        "stroke_color": "gateway_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "marker": "O",
    },
    "eventBasedGateway": {
        "shape": "diamond",
        "width": GATEWAY_SIZE,
        "height": GATEWAY_SIZE,
        "fill_color": "gateway_fill",
        "stroke_color": "gateway_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "marker": "E",
    },
    # --- События ---
    "startEvent": {
        "shape": "circle",
        "width": EVENT_SIZE,
        "height": EVENT_SIZE,
        "fill_color": "start_fill",
        "stroke_color": "start_stroke",
        "line_weight": LINE_WEIGHT_EVENT,
    },
    "endEvent": {
        "shape": "circle",
        "width": EVENT_SIZE,
        "height": EVENT_SIZE,
        "fill_color": "end_fill",
        "stroke_color": "end_stroke",
        "line_weight": LINE_WEIGHT_END_EVENT,
    },
    "intermediateCatchEvent": {
        "shape": "circle",
        "width": EVENT_SIZE,
        "height": EVENT_SIZE,
        "fill_color": "intermediate_fill",
        "stroke_color": "intermediate_stroke",
        "line_weight": LINE_WEIGHT_EVENT,
    },
    "intermediateThrowEvent": {
        "shape": "circle",
        "width": EVENT_SIZE,
        "height": EVENT_SIZE,
        "fill_color": "intermediate_fill",
        "stroke_color": "intermediate_stroke",
        "line_weight": LINE_WEIGHT_EVENT,
    },
    # --- Подпроцессы ---
    "subProcess": {
        "shape": "rectangle",
        "width": SUBPROCESS_WIDTH,
        "height": SUBPROCESS_HEIGHT,
        "fill_color": "subprocess_fill",
        "stroke_color": "subprocess_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": 0.1,
    },
    # --- Объекты данных ---
    "dataObject": {
        "shape": "rectangle",
        "width": DATA_OBJECT_WIDTH,
        "height": DATA_OBJECT_HEIGHT,
        "fill_color": "data_fill",
        "stroke_color": "data_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": 0.0,
    },
    "dataStore": {
        "shape": "rectangle",
        "width": DATA_OBJECT_WIDTH,
        "height": DATA_OBJECT_HEIGHT,
        "fill_color": "data_fill",
        "stroke_color": "data_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": 0.0,
    },
    # --- Аннотации ---
    "textAnnotation": {
        "shape": "rectangle",
        "width": ANNOTATION_WIDTH,
        "height": ANNOTATION_HEIGHT,
        "fill_color": "annotation_fill",
        "stroke_color": "annotation_stroke",
        "line_weight": LINE_WEIGHT_LANE,
        "rounding": 0.0,
    },
}

# ----------------------------------------------------------------------
# Коэффициент конвертации пикселей BPMN DI в дюймы Visio
# ----------------------------------------------------------------------

#: 1 дюйм Visio = 96 пикселей BPMN DI (стандартный DPI)
PIXELS_PER_INCH: float = 96.0

# ----------------------------------------------------------------------
# Стили соединителей
# ----------------------------------------------------------------------

#: Тип стрелки на конце соединителя (наконечник)
ARROW_TYPE_SEQUENCE: str = "open"
ARROW_TYPE_MESSAGE: str = "open"

#: Паттерн линии для message flow (пунктирная)
MESSAGE_FLOW_PATTERN: str = "dash"

#: Паттерн линии для association (точечная)
ASSOCIATION_PATTERN: str = "dot"
