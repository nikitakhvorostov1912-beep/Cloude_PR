"""Шаблоны фигур Visio для BPMN элементов.

Содержит константы размеров, цвета, шрифты и маппинг типов
BPMN-элементов на мастер-фигуры Visio.
"""

from __future__ import annotations

# ----------------------------------------------------------------------
# Размеры фигур (в дюймах для Visio)
# ----------------------------------------------------------------------

#: Размеры задач (task, userTask, serviceTask и т.д.)
TASK_WIDTH: float = 1.5
TASK_HEIGHT: float = 0.75

#: Размеры шлюзов (ромб)
GATEWAY_SIZE: float = 0.5

#: Размеры событий (круг)
EVENT_SIZE: float = 0.4

#: Ширина заголовка дорожки (левый блок с названием)
LANE_HEADER_WIDTH: float = 0.4

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

#: Горизонтальный интервал между элементами
HORIZONTAL_SPACING: float = 1.0

#: Вертикальный интервал между элементами при ветвлении
VERTICAL_SPACING: float = 0.75

#: Отступ от левого края страницы
LEFT_MARGIN: float = 1.0

#: Отступ от верхнего края страницы
TOP_MARGIN: float = 0.75

#: Внутренний отступ внутри дорожки
LANE_PADDING: float = 0.5

# ----------------------------------------------------------------------
# Цвета (RGB hex)
# ----------------------------------------------------------------------

COLORS: dict[str, str] = {
    # Задачи
    "task_fill": "#FFFFFF",
    "task_stroke": "#333333",
    # Шлюзы
    "gateway_fill": "#FFF7CC",
    "gateway_stroke": "#D4A800",
    # Стартовые события
    "start_fill": "#E8F5E9",
    "start_stroke": "#2E7D32",
    # Конечные события
    "end_fill": "#FFEBEE",
    "end_stroke": "#C62828",
    # Промежуточные события
    "intermediate_fill": "#FFF3E0",
    "intermediate_stroke": "#EF6C00",
    # Дорожки
    "lane_fill": "#F5F5F5",
    "lane_stroke": "#BDBDBD",
    # Пулы
    "pool_fill": "#E3F2FD",
    "pool_stroke": "#1565C0",
    # Соединители
    "connector_stroke": "#666666",
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
# Настройки шрифтов
# ----------------------------------------------------------------------

#: Имя шрифта
FONT_NAME: str = "Calibri"

#: Размер шрифта для меток элементов (pt)
FONT_SIZE_LABEL: int = 10

#: Размер шрифта для заголовков дорожек/пулов (pt)
FONT_SIZE_HEADER: int = 12

#: Размер шрифта для аннотаций (pt)
FONT_SIZE_ANNOTATION: int = 8

# ----------------------------------------------------------------------
# Толщина линий (pt)
# ----------------------------------------------------------------------

#: Обводка фигур
LINE_WEIGHT_SHAPE: float = 1.0

#: Обводка событий
LINE_WEIGHT_EVENT: float = 1.5

#: Конечные события (жирная обводка)
LINE_WEIGHT_END_EVENT: float = 3.0

#: Соединительные линии
LINE_WEIGHT_CONNECTOR: float = 1.0

#: Обводка пулов/дорожек
LINE_WEIGHT_LANE: float = 0.5

# ----------------------------------------------------------------------
# Маппинг типов BPMN-элементов на мастер-фигуры Visio
# ----------------------------------------------------------------------

#: Конфигурация фигуры Visio для каждого типа BPMN-элемента.
#: Ключ — тип элемента из BPMN JSON.
#: Значение — словарь с параметрами отрисовки:
#:   - shape: тип геометрической фигуры ("rectangle", "diamond", "circle")
#:   - width, height: размеры фигуры в дюймах
#:   - fill_color: ключ из словаря COLORS для заливки
#:   - stroke_color: ключ из словаря COLORS для обводки
#:   - line_weight: толщина обводки (pt)
#:   - rounding: скругление углов в дюймах (для прямоугольников)
BPMN_SHAPE_MAP: dict[str, dict[str, object]] = {
    # --- Задачи ---
    "task": {
        "shape": "rectangle",
        "width": TASK_WIDTH,
        "height": TASK_HEIGHT,
        "fill_color": "task_fill",
        "stroke_color": "task_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": 0.1,
    },
    "userTask": {
        "shape": "rectangle",
        "width": TASK_WIDTH,
        "height": TASK_HEIGHT,
        "fill_color": "task_fill",
        "stroke_color": "task_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": 0.1,
    },
    "serviceTask": {
        "shape": "rectangle",
        "width": TASK_WIDTH,
        "height": TASK_HEIGHT,
        "fill_color": "task_fill",
        "stroke_color": "task_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": 0.1,
    },
    "scriptTask": {
        "shape": "rectangle",
        "width": TASK_WIDTH,
        "height": TASK_HEIGHT,
        "fill_color": "task_fill",
        "stroke_color": "task_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": 0.1,
    },
    "manualTask": {
        "shape": "rectangle",
        "width": TASK_WIDTH,
        "height": TASK_HEIGHT,
        "fill_color": "task_fill",
        "stroke_color": "task_stroke",
        "line_weight": LINE_WEIGHT_SHAPE,
        "rounding": 0.1,
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
ARROW_TYPE_SEQUENCE: str = "open"  # открытая стрелка для sequence flow
ARROW_TYPE_MESSAGE: str = "open"  # открытая стрелка для message flow

#: Паттерн линии для message flow (пунктирная)
MESSAGE_FLOW_PATTERN: str = "dash"

#: Паттерн линии для association (точечная)
ASSOCIATION_PATTERN: str = "dot"
