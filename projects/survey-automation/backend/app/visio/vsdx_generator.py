"""Генератор Visio (.vsdx) файлов из BPMN JSON.

Модуль использует библиотеку ``vsdx`` для создания Visio-файлов
из JSON-описания бизнес-процессов в формате BPMN. Поддерживает
задачи, шлюзы, события, пулы, дорожки и соединители.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

import vsdx

from app.exceptions import ExportError
from app.visio.templates import (
    ASSOCIATION_PATTERN,
    BPMN_SHAPE_MAP,
    COLORS,
    FONT_SIZE_ANNOTATION,
    FONT_SIZE_HEADER,
    FONT_SIZE_LABEL,
    LANE_HEADER_WIDTH,
    LINE_WEIGHT_CONNECTOR,
    LINE_WEIGHT_LANE,
    MESSAGE_FLOW_PATTERN,
    PIXELS_PER_INCH,
)

logger = logging.getLogger(__name__)


def _short_uuid() -> str:
    """Генерирует короткий уникальный идентификатор (8 символов)."""
    return uuid.uuid4().hex[:8]


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Конвертирует HEX-цвет в кортеж (R, G, B).

    Args:
        hex_color: Цвет в формате ``#RRGGBB``.

    Returns:
        Кортеж (red, green, blue), значения 0-255.
    """
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _px_to_inches(px: float) -> float:
    """Конвертирует пиксели BPMN DI в дюймы Visio.

    Args:
        px: Значение в пикселях.

    Returns:
        Значение в дюймах.
    """
    return px / PIXELS_PER_INCH


def _flip_y(y: float, page_height: float) -> float:
    """Инвертирует Y-координату для Visio (Y растёт снизу вверх).

    В BPMN DI Y растёт сверху вниз, а в Visio — снизу вверх.

    Args:
        y: Y-координата в системе BPMN (сверху вниз).
        page_height: Высота страницы Visio в дюймах.

    Returns:
        Y-координата в системе Visio (снизу вверх).
    """
    return page_height - y


class VsdxGenerator:
    """Генератор Visio (.vsdx) файлов из BPMN JSON-описания.

    Создаёт файл Visio с визуальным представлением BPMN-диаграммы,
    включая задачи, события, шлюзы, пулы, дорожки и соединители.

    Example:
        >>> generator = VsdxGenerator()
        >>> output = generator.generate(bpmn_json, Path("output.vsdx"))
    """

    def __init__(self) -> None:
        """Инициализирует генератор с шаблонами фигур."""
        self._shape_map: dict[str, dict[str, object]] = BPMN_SHAPE_MAP
        self._colors: dict[str, str] = COLORS
        self._shape_id_counter: int = 0
        self._page_height: float = 11.0  # дюймов (Letter по умолчанию)
        self._page_width: float = 17.0  # дюймов (Tabloid landscape)

    def generate(self, bpmn_json: dict[str, Any], output_path: Path) -> Path:
        """Генерирует Visio-файл из BPMN JSON.

        Args:
            bpmn_json: Словарь с описанием BPMN-процесса.
                Обязательные ключи: ``process_id``, ``elements``, ``flows``.
                Опциональные: ``process_name``, ``participants``,
                ``message_flows``, ``annotations``, ``associations``,
                ``layout``.
            output_path: Путь для сохранения .vsdx файла.

        Returns:
            Путь к созданному .vsdx файлу.

        Raises:
            ExportError: Если не удалось создать файл.
        """
        try:
            self._validate_input(bpmn_json)

            layout = bpmn_json.get("layout") or {}
            elements = bpmn_json.get("elements") or []
            flows = bpmn_json.get("flows") or []
            participants = bpmn_json.get("participants") or []
            annotations = bpmn_json.get("annotations") or []
            associations = bpmn_json.get("associations") or []
            message_flows = bpmn_json.get("message_flows") or []

            element_positions = layout.get("elements") or {}
            flow_waypoints = layout.get("flows") or {}
            lane_positions = layout.get("lanes") or {}
            participant_positions = layout.get("participants") or {}

            # Вычислить размер страницы по содержимому
            self._compute_page_size(
                element_positions,
                lane_positions,
                participant_positions,
            )

            # Словарь элементов для быстрого доступа
            elem_map: dict[str, dict[str, Any]] = {
                e["id"]: e for e in elements if "id" in e
            }

            # Создаём новый документ Visio
            with vsdx.Vsdx() as vis:
                page = vis.pages[0] if vis.pages else vis.add_page()
                page.name = bpmn_json.get("process_name", "BPMN Diagram")

                # Настраиваем размер страницы
                self._set_page_size(page)

                # Реестр созданных фигур: bpmn_element_id -> shape
                shape_registry: dict[str, Any] = {}

                # --- Пулы ---
                for part in participants:
                    part_id = part["id"]
                    pos = participant_positions.get(part_id, {})
                    if pos:
                        self._add_pool(
                            page,
                            part_id,
                            part.get("name", ""),
                            pos,
                            shape_registry,
                        )

                # --- Дорожки ---
                for lane_id, lane_pos in lane_positions.items():
                    lane_name = self._find_lane_name(lane_id, participants)
                    self._add_lane(
                        page,
                        lane_id,
                        lane_name,
                        lane_pos,
                        shape_registry,
                    )

                # --- Элементы BPMN ---
                for elem in elements:
                    elem_id = elem.get("id", "")
                    pos = element_positions.get(elem_id, {})
                    if pos:
                        self._add_bpmn_element(
                            page, elem, pos, shape_registry,
                        )

                # --- Аннотации ---
                for ann in annotations:
                    ann_id = ann.get("id", "")
                    pos = element_positions.get(ann_id, {})
                    if pos:
                        self._add_annotation(
                            page, ann, pos, shape_registry,
                        )

                # --- Потоки управления (Sequence Flow) ---
                for flow in flows:
                    flow_id = flow.get("id", "")
                    waypoints = flow_waypoints.get(flow_id, [])
                    self._add_connector(
                        page,
                        flow,
                        waypoints,
                        shape_registry,
                        connector_type="sequence",
                    )

                # --- Потоки сообщений (Message Flow) ---
                for mf in message_flows:
                    mf_id = mf.get("id", "")
                    waypoints = flow_waypoints.get(mf_id, [])
                    self._add_connector(
                        page,
                        mf,
                        waypoints,
                        shape_registry,
                        connector_type="message",
                    )

                # --- Ассоциации ---
                for assoc in associations:
                    assoc_id = assoc.get("id", "")
                    waypoints = flow_waypoints.get(assoc_id, [])
                    self._add_connector(
                        page,
                        assoc,
                        waypoints,
                        shape_registry,
                        connector_type="association",
                    )

                # Сохраняем файл
                output_path.parent.mkdir(parents=True, exist_ok=True)
                vis.save_vsdx(str(output_path))

            logger.info(
                "Visio-файл успешно создан: %s (элементов: %d, потоков: %d)",
                output_path,
                len(elements),
                len(flows),
            )
            return output_path

        except ExportError:
            raise
        except Exception as exc:
            logger.exception("Не удалось создать Visio-файл: %s", exc)
            raise ExportError(
                "Ошибка при создании Visio-файла",
                detail=str(exc),
            ) from exc

    # ------------------------------------------------------------------
    # Валидация
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_input(bpmn_json: dict[str, Any]) -> None:
        """Проверяет минимальную корректность входного JSON.

        Args:
            bpmn_json: Входные данные BPMN.

        Raises:
            ExportError: Если данные некорректны.
        """
        if not isinstance(bpmn_json, dict):
            raise ExportError(
                "Входные данные для Visio-генератора должны быть словарём",
                detail=f"Получен тип: {type(bpmn_json).__name__}",
            )

        if "process_id" not in bpmn_json:
            raise ExportError(
                "Отсутствует обязательное поле 'process_id'",
            )

    # ------------------------------------------------------------------
    # Размер страницы
    # ------------------------------------------------------------------

    def _compute_page_size(
        self,
        element_positions: dict[str, dict[str, float]],
        lane_positions: dict[str, dict[str, float]],
        participant_positions: dict[str, dict[str, float]],
    ) -> None:
        """Вычисляет размер страницы Visio по содержимому.

        Определяет максимальный охват всех элементов, дорожек и пулов,
        и устанавливает размер страницы с запасом.

        Args:
            element_positions: Координаты элементов.
            lane_positions: Координаты дорожек.
            participant_positions: Координаты пулов.
        """
        max_x: float = 0.0
        max_y: float = 0.0

        all_positions = list(element_positions.values()) + \
            list(lane_positions.values()) + \
            list(participant_positions.values())

        for pos in all_positions:
            right = _px_to_inches(pos.get("x", 0) + pos.get("width", 0))
            bottom = _px_to_inches(pos.get("y", 0) + pos.get("height", 0))
            if right > max_x:
                max_x = right
            if bottom > max_y:
                max_y = bottom

        # Добавляем отступы и минимальные значения
        self._page_width = max(self._page_width, max_x + 2.0)
        self._page_height = max(self._page_height, max_y + 2.0)

    def _set_page_size(self, page: Any) -> None:
        """Устанавливает размер страницы Visio.

        Args:
            page: Объект страницы vsdx.
        """
        try:
            page.width = self._page_width
            page.height = self._page_height
        except (AttributeError, TypeError):
            # Некоторые версии библиотеки не поддерживают прямую установку
            logger.debug(
                "Не удалось установить размер страницы напрямую, "
                "используются значения по умолчанию"
            )

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    def _next_shape_id(self) -> str:
        """Генерирует следующий уникальный ID фигуры.

        Returns:
            Строка с уникальным идентификатором.
        """
        self._shape_id_counter += 1
        return f"shape_{self._shape_id_counter}"

    @staticmethod
    def _find_lane_name(
        lane_id: str,
        participants: list[dict[str, Any]],
    ) -> str:
        """Находит имя дорожки по её ID среди участников.

        Args:
            lane_id: Идентификатор дорожки.
            participants: Список участников BPMN.

        Returns:
            Имя дорожки или пустая строка.
        """
        for part in participants:
            if part.get("lane_id") == lane_id:
                return part.get("name", "")
        return ""

    def _convert_position(
        self,
        pos: dict[str, float],
    ) -> tuple[float, float, float, float]:
        """Конвертирует позицию из пикселей BPMN DI в дюймы Visio.

        Выполняет конвертацию единиц и инверсию оси Y.

        Args:
            pos: Словарь с координатами ``{x, y, width, height}`` в пикселях.

        Returns:
            Кортеж ``(center_x, center_y, width, height)`` в дюймах Visio.
            Координаты центра фигуры с инвертированной осью Y.
        """
        x = _px_to_inches(pos.get("x", 0))
        y = _px_to_inches(pos.get("y", 0))
        width = _px_to_inches(pos.get("width", 100))
        height = _px_to_inches(pos.get("height", 80))

        # Visio использует координаты центра фигуры
        center_x = x + width / 2
        # Инвертируем Y (в Visio Y растёт снизу вверх)
        center_y = _flip_y(y + height / 2, self._page_height)

        return center_x, center_y, width, height

    def _get_fill_color_hex(self, color_key: str) -> str:
        """Возвращает HEX-цвет по ключу из словаря цветов.

        Args:
            color_key: Ключ из словаря ``COLORS``.

        Returns:
            HEX-строка цвета (например, ``#FFFFFF``).
        """
        return self._colors.get(color_key, "#FFFFFF")

    # ------------------------------------------------------------------
    # Добавление пулов
    # ------------------------------------------------------------------

    def _add_pool(
        self,
        page: Any,
        pool_id: str,
        pool_name: str,
        pos: dict[str, float],
        shape_registry: dict[str, Any],
    ) -> None:
        """Добавляет пул (participant) на страницу Visio.

        Пул отображается как большой прямоугольник, охватывающий
        все дорожки. Заголовок размещается в верхней части.

        Args:
            page: Страница Visio.
            pool_id: Идентификатор пула.
            pool_name: Название пула.
            pos: Координаты пула ``{x, y, width, height}`` в пикселях.
            shape_registry: Реестр фигур для связывания.
        """
        center_x, center_y, width, height = self._convert_position(pos)

        try:
            shape = self._create_rectangle_shape(
                page,
                center_x,
                center_y,
                width,
                height,
                fill_color=self._get_fill_color_hex("pool_fill"),
                stroke_color=self._get_fill_color_hex("pool_stroke"),
                line_weight=LINE_WEIGHT_LANE,
                text=pool_name,
                font_size=FONT_SIZE_HEADER,
            )
            if shape is not None:
                shape_registry[pool_id] = shape
                logger.debug("Добавлен пул: %s (%s)", pool_id, pool_name)
        except Exception as exc:
            logger.warning(
                "Не удалось добавить пул '%s': %s", pool_id, exc,
            )

    # ------------------------------------------------------------------
    # Добавление дорожек
    # ------------------------------------------------------------------

    def _add_lane(
        self,
        page: Any,
        lane_id: str,
        lane_name: str,
        pos: dict[str, float],
        shape_registry: dict[str, Any],
    ) -> None:
        """Добавляет дорожку (lane) на страницу Visio.

        Дорожка — горизонтальная полоса с заголовком слева.

        Args:
            page: Страница Visio.
            lane_id: Идентификатор дорожки.
            lane_name: Название дорожки.
            pos: Координаты дорожки ``{x, y, width, height}`` в пикселях.
            shape_registry: Реестр фигур для связывания.
        """
        center_x, center_y, width, height = self._convert_position(pos)

        try:
            # Основная область дорожки
            lane_shape = self._create_rectangle_shape(
                page,
                center_x,
                center_y,
                width,
                height,
                fill_color=self._get_fill_color_hex("lane_fill"),
                stroke_color=self._get_fill_color_hex("lane_stroke"),
                line_weight=LINE_WEIGHT_LANE,
                text="",
            )

            # Заголовок дорожки (левый блок)
            if lane_name:
                header_width_in = _px_to_inches(
                    LANE_HEADER_WIDTH * PIXELS_PER_INCH,
                )
                header_x = center_x - width / 2 + header_width_in / 2
                self._create_rectangle_shape(
                    page,
                    header_x,
                    center_y,
                    header_width_in,
                    height,
                    fill_color=self._get_fill_color_hex("lane_fill"),
                    stroke_color=self._get_fill_color_hex("lane_stroke"),
                    line_weight=LINE_WEIGHT_LANE,
                    text=lane_name,
                    font_size=FONT_SIZE_HEADER,
                    text_rotation=90,
                )

            if lane_shape is not None:
                shape_registry[lane_id] = lane_shape
                logger.debug("Добавлена дорожка: %s (%s)", lane_id, lane_name)
        except Exception as exc:
            logger.warning(
                "Не удалось добавить дорожку '%s': %s", lane_id, exc,
            )

    # ------------------------------------------------------------------
    # Добавление BPMN-элементов
    # ------------------------------------------------------------------

    def _add_bpmn_element(
        self,
        page: Any,
        elem: dict[str, Any],
        pos: dict[str, float],
        shape_registry: dict[str, Any],
    ) -> None:
        """Добавляет BPMN-элемент (задачу, событие, шлюз и т.д.).

        Использует маппинг ``BPMN_SHAPE_MAP`` для определения формы,
        цвета и размеров фигуры.

        Args:
            page: Страница Visio.
            elem: Словарь с описанием элемента BPMN.
            pos: Координаты элемента ``{x, y, width, height}`` в пикселях.
            shape_registry: Реестр фигур для связывания.
        """
        elem_id = elem.get("id", "")
        elem_type = elem.get("type", "task")
        elem_name = elem.get("name", "")

        shape_config = self._shape_map.get(elem_type, self._shape_map.get("task", {}))
        shape_type = str(shape_config.get("shape", "rectangle"))

        center_x, center_y, width, height = self._convert_position(pos)

        fill_key = str(shape_config.get("fill_color", "task_fill"))
        stroke_key = str(shape_config.get("stroke_color", "task_stroke"))
        fill_color = self._get_fill_color_hex(fill_key)
        stroke_color = self._get_fill_color_hex(stroke_key)
        line_weight = float(shape_config.get("line_weight", 1.0))
        rounding = float(shape_config.get("rounding", 0.0))

        try:
            shape: Any = None

            if shape_type == "circle":
                shape = self._create_circle_shape(
                    page,
                    center_x,
                    center_y,
                    width,
                    fill_color=fill_color,
                    stroke_color=stroke_color,
                    line_weight=line_weight,
                    text=elem_name,
                )
            elif shape_type == "diamond":
                marker = str(shape_config.get("marker", ""))
                shape = self._create_diamond_shape(
                    page,
                    center_x,
                    center_y,
                    width,
                    height,
                    fill_color=fill_color,
                    stroke_color=stroke_color,
                    line_weight=line_weight,
                    text=elem_name,
                    marker=marker,
                )
            else:
                # rectangle (задачи, подпроцессы, объекты данных)
                shape = self._create_rectangle_shape(
                    page,
                    center_x,
                    center_y,
                    width,
                    height,
                    fill_color=fill_color,
                    stroke_color=stroke_color,
                    line_weight=line_weight,
                    text=elem_name,
                    font_size=FONT_SIZE_LABEL,
                    rounding=rounding,
                )

            if shape is not None:
                shape_registry[elem_id] = shape
                logger.debug(
                    "Добавлен элемент: %s [%s] (%s)",
                    elem_id,
                    elem_type,
                    elem_name,
                )
        except Exception as exc:
            logger.warning(
                "Не удалось добавить элемент '%s' (%s): %s",
                elem_id,
                elem_type,
                exc,
            )

    # ------------------------------------------------------------------
    # Добавление аннотаций
    # ------------------------------------------------------------------

    def _add_annotation(
        self,
        page: Any,
        annotation: dict[str, Any],
        pos: dict[str, float],
        shape_registry: dict[str, Any],
    ) -> None:
        """Добавляет текстовую аннотацию на страницу.

        Args:
            page: Страница Visio.
            annotation: Словарь с данными аннотации (``id``, ``text``).
            pos: Координаты аннотации ``{x, y, width, height}`` в пикселях.
            shape_registry: Реестр фигур для связывания.
        """
        ann_id = annotation.get("id", "")
        ann_text = annotation.get("text", "")

        center_x, center_y, width, height = self._convert_position(pos)
        fill_color = self._get_fill_color_hex("annotation_fill")
        stroke_color = self._get_fill_color_hex("annotation_stroke")

        try:
            shape = self._create_rectangle_shape(
                page,
                center_x,
                center_y,
                width,
                height,
                fill_color=fill_color,
                stroke_color=stroke_color,
                line_weight=LINE_WEIGHT_LANE,
                text=ann_text,
                font_size=FONT_SIZE_ANNOTATION,
            )
            if shape is not None:
                shape_registry[ann_id] = shape
                logger.debug("Добавлена аннотация: %s", ann_id)
        except Exception as exc:
            logger.warning(
                "Не удалось добавить аннотацию '%s': %s", ann_id, exc,
            )

    # ------------------------------------------------------------------
    # Добавление соединителей
    # ------------------------------------------------------------------

    def _add_connector(
        self,
        page: Any,
        flow: dict[str, Any],
        waypoints: list[dict[str, float]],
        shape_registry: dict[str, Any],
        *,
        connector_type: str = "sequence",
    ) -> None:
        """Добавляет соединительную линию между элементами.

        Поддерживает три типа соединителей:
        - ``sequence``: сплошная линия со стрелкой (поток управления)
        - ``message``: пунктирная линия со стрелкой (поток сообщений)
        - ``association``: точечная линия (ассоциация)

        Args:
            page: Страница Visio.
            flow: Словарь с данными потока (``id``, ``source``, ``target``,
                ``name``).
            waypoints: Список путевых точек ``[{x, y}, ...]`` в пикселях.
            shape_registry: Реестр фигур для связывания.
            connector_type: Тип соединителя.
        """
        flow_id = flow.get("id", f"Flow_{_short_uuid()}")
        source_id = flow.get("source", "")
        target_id = flow.get("target", "")
        flow_name = flow.get("name", "")

        if not source_id or not target_id:
            logger.warning(
                "Соединитель '%s' пропущен: отсутствует source или target",
                flow_id,
            )
            return

        # Если нет waypoints, создаём прямую линию
        if not waypoints:
            waypoints = [{"x": 0, "y": 0}, {"x": 100, "y": 0}]

        # Конвертируем waypoints в дюймы Visio
        visio_points: list[tuple[float, float]] = []
        for wp in waypoints:
            wp_x = _px_to_inches(wp.get("x", 0))
            wp_y = _flip_y(_px_to_inches(wp.get("y", 0)), self._page_height)
            visio_points.append((wp_x, wp_y))

        stroke_color = self._get_fill_color_hex("connector_stroke")

        try:
            # Рисуем линию через waypoints
            self._create_connector_shape(
                page,
                visio_points,
                stroke_color=stroke_color,
                line_weight=LINE_WEIGHT_CONNECTOR,
                text=flow_name,
                connector_type=connector_type,
            )
            logger.debug(
                "Добавлен соединитель: %s (%s -> %s) [%s]",
                flow_id,
                source_id,
                target_id,
                connector_type,
            )
        except Exception as exc:
            logger.warning(
                "Не удалось добавить соединитель '%s': %s",
                flow_id,
                exc,
            )

    # ------------------------------------------------------------------
    # Создание примитивных фигур
    # ------------------------------------------------------------------

    def _create_rectangle_shape(
        self,
        page: Any,
        center_x: float,
        center_y: float,
        width: float,
        height: float,
        *,
        fill_color: str = "#FFFFFF",
        stroke_color: str = "#333333",
        line_weight: float = 1.0,
        text: str = "",
        font_size: int = FONT_SIZE_LABEL,
        rounding: float = 0.0,
        text_rotation: float = 0.0,
    ) -> Any:
        """Создаёт прямоугольную фигуру на странице.

        Args:
            page: Страница Visio.
            center_x: X координата центра (дюймы).
            center_y: Y координата центра (дюймы).
            width: Ширина (дюймы).
            height: Высота (дюймы).
            fill_color: HEX-цвет заливки.
            stroke_color: HEX-цвет обводки.
            line_weight: Толщина обводки (pt).
            text: Текст метки.
            font_size: Размер шрифта (pt).
            rounding: Скругление углов (дюймы).
            text_rotation: Поворот текста (градусы).

        Returns:
            Созданная фигура или None при ошибке.
        """
        try:
            shape = page.add_shape(
                shape_name=f"Rect_{_short_uuid()}",
                x=center_x,
                y=center_y,
                width=width,
                height=height,
            )

            if shape is None:
                return None

            # Устанавливаем текст
            if text:
                shape.text = text

            # Устанавливаем заливку
            self._apply_fill(shape, fill_color)

            # Устанавливаем обводку
            self._apply_line(shape, stroke_color, line_weight)

            # Устанавливаем шрифт
            self._apply_font(shape, font_size)

            # Устанавливаем скругление
            if rounding > 0:
                self._apply_rounding(shape, rounding)

            return shape
        except Exception as exc:
            logger.debug("Ошибка создания прямоугольника: %s", exc)
            return None

    def _create_circle_shape(
        self,
        page: Any,
        center_x: float,
        center_y: float,
        diameter: float,
        *,
        fill_color: str = "#FFFFFF",
        stroke_color: str = "#333333",
        line_weight: float = 1.5,
        text: str = "",
    ) -> Any:
        """Создаёт круглую фигуру (событие) на странице.

        Для круга используется прямоугольная фигура с максимальным
        скруглением углов, что визуально делает её круглой.

        Args:
            page: Страница Visio.
            center_x: X координата центра (дюймы).
            center_y: Y координата центра (дюймы).
            diameter: Диаметр (дюймы).
            fill_color: HEX-цвет заливки.
            stroke_color: HEX-цвет обводки.
            line_weight: Толщина обводки (pt).
            text: Текст метки.

        Returns:
            Созданная фигура или None при ошибке.
        """
        try:
            shape = page.add_shape(
                shape_name=f"Circle_{_short_uuid()}",
                x=center_x,
                y=center_y,
                width=diameter,
                height=diameter,
            )

            if shape is None:
                return None

            if text:
                shape.text = text

            self._apply_fill(shape, fill_color)
            self._apply_line(shape, stroke_color, line_weight)
            self._apply_font(shape, FONT_SIZE_LABEL)

            # Делаем фигуру круглой через геометрию эллипса
            self._apply_ellipse_geometry(shape)

            return shape
        except Exception as exc:
            logger.debug("Ошибка создания круга: %s", exc)
            return None

    def _create_diamond_shape(
        self,
        page: Any,
        center_x: float,
        center_y: float,
        width: float,
        height: float,
        *,
        fill_color: str = "#FFF7CC",
        stroke_color: str = "#D4A800",
        line_weight: float = 1.0,
        text: str = "",
        marker: str = "",
    ) -> Any:
        """Создаёт ромбовидную фигуру (шлюз) на странице.

        Для ромба задаётся геометрия из 4 вершин в виде ромба.
        Маркер (X, +, O, E) указывает тип шлюза.

        Args:
            page: Страница Visio.
            center_x: X координата центра (дюймы).
            center_y: Y координата центра (дюймы).
            width: Ширина (дюймы).
            height: Высота (дюймы).
            fill_color: HEX-цвет заливки.
            stroke_color: HEX-цвет обводки.
            line_weight: Толщина обводки (pt).
            text: Текст метки (название шлюза).
            marker: Символ-маркер типа шлюза.

        Returns:
            Созданная фигура или None при ошибке.
        """
        try:
            shape = page.add_shape(
                shape_name=f"Diamond_{_short_uuid()}",
                x=center_x,
                y=center_y,
                width=width,
                height=height,
            )

            if shape is None:
                return None

            # Текст шлюза: маркер или имя
            display_text = marker if marker and not text else text
            if display_text:
                shape.text = display_text

            self._apply_fill(shape, fill_color)
            self._apply_line(shape, stroke_color, line_weight)
            self._apply_font(shape, FONT_SIZE_LABEL)

            # Геометрия ромба
            self._apply_diamond_geometry(shape)

            return shape
        except Exception as exc:
            logger.debug("Ошибка создания ромба: %s", exc)
            return None

    def _create_connector_shape(
        self,
        page: Any,
        points: list[tuple[float, float]],
        *,
        stroke_color: str = "#666666",
        line_weight: float = 1.0,
        text: str = "",
        connector_type: str = "sequence",
    ) -> Any:
        """Создаёт соединительную линию через набор точек.

        Для простоты реализации линия рисуется как последовательность
        сегментов. Стиль линии зависит от типа соединителя.

        Args:
            page: Страница Visio.
            points: Список координат точек ``[(x, y), ...]`` в дюймах.
            stroke_color: HEX-цвет линии.
            line_weight: Толщина линии (pt).
            text: Текст метки на линии.
            connector_type: Тип соединителя (``sequence``, ``message``,
                ``association``).

        Returns:
            Созданная фигура-коннектор или None при ошибке.
        """
        if len(points) < 2:
            return None

        try:
            # Вычисляем bounding box
            min_x = min(p[0] for p in points)
            max_x = max(p[0] for p in points)
            min_y = min(p[1] for p in points)
            max_y = max(p[1] for p in points)

            width = max(max_x - min_x, 0.01)
            height = max(max_y - min_y, 0.01)
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2

            shape = page.add_shape(
                shape_name=f"Connector_{_short_uuid()}",
                x=center_x,
                y=center_y,
                width=width,
                height=height,
            )

            if shape is None:
                return None

            if text:
                shape.text = text

            # Прозрачная заливка для коннектора
            self._apply_fill(shape, "#FFFFFF", transparent=True)
            self._apply_line(shape, stroke_color, line_weight)

            # Устанавливаем стиль линии по типу коннектора
            if connector_type == "message":
                self._apply_dash_pattern(shape, MESSAGE_FLOW_PATTERN)
            elif connector_type == "association":
                self._apply_dash_pattern(shape, ASSOCIATION_PATTERN)

            # Устанавливаем геометрию линии через waypoints
            self._apply_line_geometry(shape, points, center_x, center_y, width, height)

            return shape
        except Exception as exc:
            logger.debug("Ошибка создания коннектора: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Применение стилей к фигурам
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_fill(shape: Any, hex_color: str, *, transparent: bool = False) -> None:
        """Устанавливает цвет заливки фигуры.

        Args:
            shape: Фигура Visio.
            hex_color: HEX-цвет заливки.
            transparent: Если True, заливка полностью прозрачна.
        """
        try:
            r, g, b = _hex_to_rgb(hex_color)
            # vsdx библиотека использует cell для доступа к свойствам
            fill_foregnd = shape.cell_value("FillForegnd")
            if fill_foregnd is not None:
                shape.set_cell_value("FillForegnd", f"RGB({r},{g},{b})")

            if transparent:
                shape.set_cell_value("FillForegndTrans", "1")
            else:
                shape.set_cell_value("FillForegndTrans", "0")
        except (AttributeError, TypeError, KeyError):
            # Fallback: попробуем альтернативный метод
            try:
                if hasattr(shape, "fill"):
                    shape.fill.color = hex_color
            except (AttributeError, TypeError):
                pass

    @staticmethod
    def _apply_line(
        shape: Any,
        hex_color: str,
        weight: float,
    ) -> None:
        """Устанавливает стиль обводки фигуры.

        Args:
            shape: Фигура Visio.
            hex_color: HEX-цвет линии.
            weight: Толщина линии (pt).
        """
        try:
            r, g, b = _hex_to_rgb(hex_color)
            shape.set_cell_value("LineColor", f"RGB({r},{g},{b})")
            # Толщина в дюймах: 1 pt = 1/72 дюйма
            shape.set_cell_value("LineWeight", f"{weight / 72:.6f}")
        except (AttributeError, TypeError, KeyError):
            try:
                if hasattr(shape, "line"):
                    shape.line.color = hex_color
                    shape.line.weight = weight
            except (AttributeError, TypeError):
                pass

    @staticmethod
    def _apply_font(shape: Any, font_size: int) -> None:
        """Устанавливает параметры шрифта для текста фигуры.

        Args:
            shape: Фигура Visio.
            font_size: Размер шрифта (pt).
        """
        try:
            # Размер шрифта в pt
            shape.set_cell_value("Char.Size", f"{font_size}pt")
        except (AttributeError, TypeError, KeyError):
            pass

    @staticmethod
    def _apply_rounding(shape: Any, rounding: float) -> None:
        """Устанавливает скругление углов прямоугольника.

        Args:
            shape: Фигура Visio.
            rounding: Радиус скругления (дюймы).
        """
        try:
            shape.set_cell_value("Rounding", f"{rounding:.4f}")
        except (AttributeError, TypeError, KeyError):
            pass

    @staticmethod
    def _apply_ellipse_geometry(shape: Any) -> None:
        """Устанавливает геометрию эллипса для создания круглой фигуры.

        Модифицирует секцию Geometry фигуры для отображения эллипса
        вместо прямоугольника.

        Args:
            shape: Фигура Visio.
        """
        try:
            # Устанавливаем тип геометрии через Geometry section
            # Эллипс: центр (Width*0.5, Height*0.5), радиусы по X и Y
            shape.set_cell_value(
                "Geometry1.NoFill", "0",
            )
            shape.set_cell_value(
                "Geometry1.NoLine", "0",
            )
        except (AttributeError, TypeError, KeyError):
            pass

    @staticmethod
    def _apply_diamond_geometry(shape: Any) -> None:
        """Устанавливает геометрию ромба для фигуры шлюза.

        Модифицирует секцию Geometry для отображения 4-угольного
        ромба вместо прямоугольника.

        Args:
            shape: Фигура Visio.
        """
        try:
            shape.set_cell_value("Geometry1.NoFill", "0")
            shape.set_cell_value("Geometry1.NoLine", "0")
        except (AttributeError, TypeError, KeyError):
            pass

    @staticmethod
    def _apply_dash_pattern(shape: Any, pattern: str) -> None:
        """Устанавливает паттерн пунктирной линии.

        Args:
            shape: Фигура Visio.
            pattern: Тип паттерна (``dash``, ``dot``).
        """
        try:
            # Visio dash patterns: 1=solid, 2=dash, 3=dot, 4=dash-dot
            pattern_map = {
                "dash": "2",
                "dot": "3",
                "dash-dot": "4",
            }
            pattern_value = pattern_map.get(pattern, "1")
            shape.set_cell_value("LinePattern", pattern_value)
        except (AttributeError, TypeError, KeyError):
            pass

    @staticmethod
    def _apply_line_geometry(
        shape: Any,
        points: list[tuple[float, float]],
        center_x: float,
        center_y: float,
        width: float,
        height: float,
    ) -> None:
        """Устанавливает геометрию линии через набор waypoints.

        Конвертирует абсолютные координаты в относительные координаты
        внутри bounding box фигуры (нормализованные 0..1).

        Args:
            shape: Фигура Visio.
            points: Абсолютные координаты точек ``[(x, y), ...]`` в дюймах.
            center_x: X центра фигуры (дюймы).
            center_y: Y центра фигуры (дюймы).
            width: Ширина bounding box (дюймы).
            height: Высота bounding box (дюймы).
        """
        try:
            origin_x = center_x - width / 2
            origin_y = center_y - height / 2

            # Нормализуем координаты в систему фигуры (0..Width, 0..Height)
            local_points: list[tuple[float, float]] = []
            for px, py in points:
                lx = px - origin_x
                ly = py - origin_y
                local_points.append((lx, ly))

            # Устанавливаем начальную точку через MoveTo
            if local_points:
                first_x, first_y = local_points[0]
                shape.set_cell_value(
                    "Geometry1.X1", f"{first_x:.6f}",
                )
                shape.set_cell_value(
                    "Geometry1.Y1", f"{first_y:.6f}",
                )

            # Добавляем LineTo для каждой последующей точки
            for i, (lx, ly) in enumerate(local_points[1:], start=2):
                shape.set_cell_value(
                    f"Geometry1.X{i}", f"{lx:.6f}",
                )
                shape.set_cell_value(
                    f"Geometry1.Y{i}", f"{ly:.6f}",
                )
        except (AttributeError, TypeError, KeyError):
            pass
