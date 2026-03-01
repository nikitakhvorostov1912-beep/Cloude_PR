"""Автоматическая компоновка BPMN-диаграмм.

Модуль реализует алгоритм расстановки элементов BPMN-диаграммы
слева направо с учётом дорожек (lanes), ветвлений через шлюзы
и точек слияния потоков.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

from app.exceptions import ProcessingError

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Константы размеров элементов (в пикселях)
# ----------------------------------------------------------------------

#: Размеры событий (start, end, intermediate)
EVENT_WIDTH: int = 36
EVENT_HEIGHT: int = 36

#: Размеры задач (task, userTask, serviceTask и т.д.)
TASK_WIDTH: int = 120
TASK_HEIGHT: int = 80

#: Размеры шлюзов (exclusive, parallel, inclusive, eventBased)
GATEWAY_WIDTH: int = 50
GATEWAY_HEIGHT: int = 50

#: Размеры подпроцессов
SUBPROCESS_WIDTH: int = 200
SUBPROCESS_HEIGHT: int = 120

#: Размеры объектов данных
DATA_OBJECT_WIDTH: int = 40
DATA_OBJECT_HEIGHT: int = 50

#: Размеры аннотаций
ANNOTATION_WIDTH: int = 120
ANNOTATION_HEIGHT: int = 40

#: Высота дорожки по умолчанию
LANE_HEIGHT: int = 200

#: Минимальная ширина дорожки
LANE_MIN_WIDTH: int = 600

#: Отступ меток дорожек (левый блок с названием)
LANE_LABEL_WIDTH: int = 40

#: Горизонтальный отступ между элементами
HORIZONTAL_SPACING: int = 80

#: Вертикальный отступ между элементами (при ветвлении)
VERTICAL_SPACING: int = 60

#: Начальный отступ от левого края
LEFT_MARGIN: int = 80

#: Начальный отступ от верхнего края
TOP_MARGIN: int = 60

#: Вертикальный отступ внутри дорожки (от верхнего и нижнего края)
LANE_PADDING: int = 40

#: Отступ между пулом и первой дорожкой
POOL_PADDING: int = 20

# ----------------------------------------------------------------------
# Таблица размеров по типу элемента
# ----------------------------------------------------------------------

_ELEMENT_SIZES: dict[str, tuple[int, int]] = {
    "startEvent": (EVENT_WIDTH, EVENT_HEIGHT),
    "endEvent": (EVENT_WIDTH, EVENT_HEIGHT),
    "intermediateCatchEvent": (EVENT_WIDTH, EVENT_HEIGHT),
    "intermediateThrowEvent": (EVENT_WIDTH, EVENT_HEIGHT),
    "task": (TASK_WIDTH, TASK_HEIGHT),
    "userTask": (TASK_WIDTH, TASK_HEIGHT),
    "serviceTask": (TASK_WIDTH, TASK_HEIGHT),
    "scriptTask": (TASK_WIDTH, TASK_HEIGHT),
    "manualTask": (TASK_WIDTH, TASK_HEIGHT),
    "exclusiveGateway": (GATEWAY_WIDTH, GATEWAY_HEIGHT),
    "parallelGateway": (GATEWAY_WIDTH, GATEWAY_HEIGHT),
    "inclusiveGateway": (GATEWAY_WIDTH, GATEWAY_HEIGHT),
    "eventBasedGateway": (GATEWAY_WIDTH, GATEWAY_HEIGHT),
    "subProcess": (SUBPROCESS_WIDTH, SUBPROCESS_HEIGHT),
    "dataObject": (DATA_OBJECT_WIDTH, DATA_OBJECT_HEIGHT),
    "dataStore": (DATA_OBJECT_WIDTH, DATA_OBJECT_HEIGHT),
    "textAnnotation": (ANNOTATION_WIDTH, ANNOTATION_HEIGHT),
}


def _get_element_size(elem_type: str) -> tuple[int, int]:
    """Возвращает (width, height) для заданного типа элемента."""
    return _ELEMENT_SIZES.get(elem_type, (TASK_WIDTH, TASK_HEIGHT))


class BpmnLayout:
    """Вычисляет позиции элементов BPMN-диаграммы.

    Алгоритм компоновки:
    1. Определяет топологический порядок элементов по потокам управления.
    2. Группирует элементы по дорожкам (lanes).
    3. Размещает элементы слева направо в порядке выполнения.
    4. Шлюзы создают вертикальные ответвления для параллельных путей.
    5. Точки слияния определяются автоматически.

    Example:
        >>> layout_engine = BpmnLayout()
        >>> layout = layout_engine.calculate_layout(bpmn_json)
        >>> # layout["elements"]["task_1"] == {"x": 200, "y": 100, "width": 120, "height": 80}
    """

    def calculate_layout(self, bpmn_json: dict[str, Any]) -> dict[str, Any]:
        """Вычисляет координаты всех элементов диаграммы.

        Args:
            bpmn_json: JSON-описание BPMN-процесса (тот же формат,
                что принимает ``BpmnConverter.convert``).

        Returns:
            Словарь с ключами:
            - ``elements``: ``{id: {x, y, width, height}}``
            - ``flows``: ``{id: [{x, y}, ...]}`` (waypoints)
            - ``lanes``: ``{lane_id: {x, y, width, height}}``
            - ``participants``: ``{part_id: {x, y, width, height}}``

        Raises:
            ProcessingError: Если структура JSON некорректна.
        """
        if not isinstance(bpmn_json, dict):
            raise ProcessingError(
                "Входные данные для компоновки должны быть словарём",
            )

        elements = bpmn_json.get("elements") or []
        flows = bpmn_json.get("flows") or []
        participants = bpmn_json.get("participants") or []

        if not elements:
            return self._empty_layout()

        # Построить граф смежности
        adjacency = self._build_adjacency(elements, flows)

        # Определить порядок обхода (топологическая сортировка)
        order = self._topological_sort(elements, adjacency)

        # Собрать информацию о дорожках
        lanes = self._collect_lanes(participants)
        lane_ids = [lane["id"] for lane in lanes] if lanes else []

        # Сгруппировать элементы по дорожкам
        elem_by_lane = self._group_by_lane(elements, lane_ids)

        # Вычислить позиции элементов
        element_positions = self._compute_positions(
            order, elements, adjacency, elem_by_lane, lane_ids,
        )

        # Вычислить размеры и позиции дорожек
        lane_positions = self._compute_lane_positions(
            lane_ids, lanes, element_positions, elements,
        )

        # Вычислить размеры и позиции участников (пулов)
        participant_positions = self._compute_participant_positions(
            participants, lane_positions, element_positions,
        )

        # Вычислить waypoints потоков
        flow_waypoints = self._compute_flow_waypoints(
            flows, element_positions, elements,
        )

        return {
            "elements": element_positions,
            "flows": flow_waypoints,
            "lanes": lane_positions,
            "participants": participant_positions,
        }

    # ------------------------------------------------------------------
    # Построение графа
    # ------------------------------------------------------------------

    @staticmethod
    def _build_adjacency(
        elements: list[dict[str, Any]],
        flows: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        """Строит граф смежности: source -> [targets]."""
        adj: dict[str, list[str]] = defaultdict(list)
        elem_ids = {e["id"] for e in elements if "id" in e}

        for flow in flows:
            src = flow.get("source", "")
            tgt = flow.get("target", "")
            if src in elem_ids and tgt in elem_ids:
                adj[src].append(tgt)

        return dict(adj)

    @staticmethod
    def _build_reverse_adjacency(
        elements: list[dict[str, Any]],
        flows: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        """Строит обратный граф: target -> [sources]."""
        rev: dict[str, list[str]] = defaultdict(list)
        elem_ids = {e["id"] for e in elements if "id" in e}

        for flow in flows:
            src = flow.get("source", "")
            tgt = flow.get("target", "")
            if src in elem_ids and tgt in elem_ids:
                rev[tgt].append(src)

        return dict(rev)

    # ------------------------------------------------------------------
    # Топологическая сортировка
    # ------------------------------------------------------------------

    @staticmethod
    def _topological_sort(
        elements: list[dict[str, Any]],
        adjacency: dict[str, list[str]],
    ) -> list[str]:
        """Возвращает список id элементов в топологическом порядке.

        Использует алгоритм Кана (BFS). Элементы без входящих рёбер
        обрабатываются первыми.
        """
        elem_ids = [e["id"] for e in elements if "id" in e]
        in_degree: dict[str, int] = {eid: 0 for eid in elem_ids}

        for src, targets in adjacency.items():
            for tgt in targets:
                if tgt in in_degree:
                    in_degree[tgt] += 1

        # Начинаем с элементов без входящих рёбер
        queue: deque[str] = deque()
        for eid in elem_ids:
            if in_degree[eid] == 0:
                queue.append(eid)

        result: list[str] = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in adjacency.get(node, []):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        # Если есть элементы, не попавшие в результат (циклы), добавляем их в конец
        remaining = [eid for eid in elem_ids if eid not in set(result)]
        if remaining:
            logger.warning(
                "Обнаружены циклические зависимости для элементов: %s",
                remaining,
            )
            result.extend(remaining)

        return result

    # ------------------------------------------------------------------
    # Группировка по дорожкам
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_lanes(
        participants: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Собирает уникальные дорожки из участников."""
        lanes: list[dict[str, Any]] = []
        seen: set[str] = set()
        for part in participants:
            lane_id = part.get("lane_id")
            if lane_id and lane_id not in seen:
                seen.add(lane_id)
                lanes.append({"id": lane_id, "name": part.get("name", "")})
        return lanes

    @staticmethod
    def _group_by_lane(
        elements: list[dict[str, Any]],
        lane_ids: list[str],
    ) -> dict[str, list[str]]:
        """Группирует id элементов по дорожкам.

        Элементы без указанной дорожки попадают в специальную группу ``_default``.
        """
        groups: dict[str, list[str]] = {lid: [] for lid in lane_ids}
        groups["_default"] = []

        for elem in elements:
            lane = elem.get("lane", "_default")
            if lane not in groups:
                lane = "_default"
            groups[lane].append(elem["id"])

        return groups

    # ------------------------------------------------------------------
    # Вычисление позиций
    # ------------------------------------------------------------------

    def _compute_positions(
        self,
        order: list[str],
        elements: list[dict[str, Any]],
        adjacency: dict[str, list[str]],
        elem_by_lane: dict[str, list[str]],
        lane_ids: list[str],
    ) -> dict[str, dict[str, float]]:
        """Вычисляет координаты каждого элемента.

        Алгоритм:
        1. Назначает каждому элементу «колонку» (column) по топологическому порядку.
        2. Элементы одной колонки в одной дорожке размещаются вертикально.
        3. X определяется колонкой, Y — дорожкой и позицией внутри неё.
        """
        elem_map: dict[str, dict[str, Any]] = {
            e["id"]: e for e in elements if "id" in e
        }

        # Назначить колонку каждому элементу
        columns: dict[str, int] = {}
        for idx, eid in enumerate(order):
            # Колонка = максимальная колонка предшественников + 1
            predecessors_cols: list[int] = []
            for src, targets in adjacency.items():
                if eid in targets and src in columns:
                    predecessors_cols.append(columns[src])

            if predecessors_cols:
                columns[eid] = max(predecessors_cols) + 1
            else:
                columns[eid] = 0

        # Определить вертикальное расположение дорожек
        lane_y_offsets: dict[str, float] = {}
        current_y: float = TOP_MARGIN
        effective_lane_ids = lane_ids if lane_ids else ["_default"]

        for lane_id in effective_lane_ids:
            lane_y_offsets[lane_id] = current_y
            current_y += LANE_HEIGHT

        # Подсчитать количество элементов в каждой (колонка, дорожка) ячейке
        cell_counts: dict[tuple[int, str], int] = defaultdict(int)
        cell_indices: dict[str, int] = {}

        for eid in order:
            lane = elem_map.get(eid, {}).get("lane", "_default")
            if lane not in lane_y_offsets:
                lane = "_default" if "_default" in lane_y_offsets else effective_lane_ids[0]
            col = columns.get(eid, 0)
            key = (col, lane)
            cell_indices[eid] = cell_counts[key]
            cell_counts[key] += 1

        # Вычислить координаты
        positions: dict[str, dict[str, float]] = {}

        for eid in order:
            elem = elem_map.get(eid)
            if not elem:
                continue

            elem_type = elem.get("type", "task")
            width, height = _get_element_size(elem_type)
            col = columns.get(eid, 0)
            lane = elem.get("lane", "_default")
            if lane not in lane_y_offsets:
                lane = "_default" if "_default" in lane_y_offsets else effective_lane_ids[0]

            lane_y = lane_y_offsets[lane]
            idx_in_cell = cell_indices.get(eid, 0)
            total_in_cell = cell_counts.get((col, lane), 1)

            # X: колонка * (макс.ширина + отступ) + начальный отступ
            x = LEFT_MARGIN + LANE_LABEL_WIDTH + col * (TASK_WIDTH + HORIZONTAL_SPACING)

            # Центрируем элемент по горизонтали в слоте, если он уже задачи
            x += (TASK_WIDTH - width) / 2

            # Y: позиция в дорожке с учётом количества элементов в ячейке
            lane_center_y = lane_y + LANE_HEIGHT / 2
            total_block_height = (
                total_in_cell * height
                + (total_in_cell - 1) * VERTICAL_SPACING
            )
            start_y = lane_center_y - total_block_height / 2
            y = start_y + idx_in_cell * (height + VERTICAL_SPACING)

            positions[eid] = {
                "x": round(x, 1),
                "y": round(y, 1),
                "width": float(width),
                "height": float(height),
            }

        return positions

    # ------------------------------------------------------------------
    # Позиции дорожек
    # ------------------------------------------------------------------

    def _compute_lane_positions(
        self,
        lane_ids: list[str],
        lanes: list[dict[str, Any]],
        element_positions: dict[str, dict[str, float]],
        elements: list[dict[str, Any]],
    ) -> dict[str, dict[str, float]]:
        """Вычисляет координаты и размеры дорожек."""
        if not lane_ids:
            return {}

        # Определить максимальную X-координату правого края элементов
        max_right: float = LANE_MIN_WIDTH
        for pos in element_positions.values():
            right = pos["x"] + pos["width"]
            if right > max_right:
                max_right = right

        total_width = max_right + HORIZONTAL_SPACING + LEFT_MARGIN

        lane_positions: dict[str, dict[str, float]] = {}
        current_y: float = TOP_MARGIN

        for lane_id in lane_ids:
            # Подсчитать количество элементов в этой дорожке
            lane_elems = [
                e for e in elements
                if e.get("lane") == lane_id and e["id"] in element_positions
            ]

            # Определить реальную высоту по содержимому
            if lane_elems:
                min_y = min(
                    element_positions[e["id"]]["y"] for e in lane_elems
                )
                max_y = max(
                    element_positions[e["id"]]["y"]
                    + element_positions[e["id"]]["height"]
                    for e in lane_elems
                )
                content_height = max_y - min_y + 2 * LANE_PADDING
                lane_height = max(LANE_HEIGHT, content_height)
            else:
                lane_height = LANE_HEIGHT

            lane_positions[lane_id] = {
                "x": float(LEFT_MARGIN),
                "y": round(current_y, 1),
                "width": round(total_width, 1),
                "height": float(lane_height),
            }
            current_y += lane_height

        return lane_positions

    # ------------------------------------------------------------------
    # Позиции участников (пулов)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_participant_positions(
        participants: list[dict[str, Any]],
        lane_positions: dict[str, dict[str, float]],
        element_positions: dict[str, dict[str, float]],
    ) -> dict[str, dict[str, float]]:
        """Вычисляет координаты пулов (охватывают все дорожки)."""
        if not participants:
            return {}

        if not lane_positions:
            # Если нет дорожек, вычисляем по элементам
            if not element_positions:
                return {}

            min_x = min(p["x"] for p in element_positions.values())
            min_y = min(p["y"] for p in element_positions.values())
            max_x = max(
                p["x"] + p["width"] for p in element_positions.values()
            )
            max_y = max(
                p["y"] + p["height"] for p in element_positions.values()
            )

            pool_pos: dict[str, dict[str, float]] = {}
            for part in participants:
                pool_pos[part["id"]] = {
                    "x": min_x - POOL_PADDING,
                    "y": min_y - POOL_PADDING,
                    "width": max_x - min_x + 2 * POOL_PADDING,
                    "height": max_y - min_y + 2 * POOL_PADDING,
                }
            return pool_pos

        # Пул охватывает все дорожки
        all_lane_pos = list(lane_positions.values())
        pool_x = min(lp["x"] for lp in all_lane_pos)
        pool_y = min(lp["y"] for lp in all_lane_pos)
        pool_width = max(lp["x"] + lp["width"] for lp in all_lane_pos) - pool_x
        pool_height = (
            max(lp["y"] + lp["height"] for lp in all_lane_pos) - pool_y
        )

        result: dict[str, dict[str, float]] = {}
        for part in participants:
            result[part["id"]] = {
                "x": pool_x,
                "y": pool_y,
                "width": pool_width,
                "height": pool_height,
            }
        return result

    # ------------------------------------------------------------------
    # Waypoints потоков
    # ------------------------------------------------------------------

    def _compute_flow_waypoints(
        self,
        flows: list[dict[str, Any]],
        element_positions: dict[str, dict[str, float]],
        elements: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, float]]]:
        """Вычисляет путевые точки (waypoints) для каждого потока.

        Для каждого потока определяются точки начала (правый край источника)
        и конца (левый край цели). При необходимости добавляются
        промежуточные точки для обхода пересечений.
        """
        elem_map: dict[str, dict[str, Any]] = {
            e["id"]: e for e in elements if "id" in e
        }

        result: dict[str, list[dict[str, float]]] = {}

        for flow in flows:
            flow_id = flow.get("id", "")
            src_id = flow.get("source", "")
            tgt_id = flow.get("target", "")

            src_pos = element_positions.get(src_id)
            tgt_pos = element_positions.get(tgt_id)

            if not src_pos or not tgt_pos:
                # Элемент не найден — прямая линия-заглушка
                result[flow_id] = [{"x": 0, "y": 0}, {"x": 100, "y": 0}]
                continue

            src_type = elem_map.get(src_id, {}).get("type", "task")
            tgt_type = elem_map.get(tgt_id, {}).get("type", "task")

            # Точка выхода — правый центр элемента
            src_cx = src_pos["x"] + src_pos["width"]
            src_cy = src_pos["y"] + src_pos["height"] / 2

            # Точка входа — левый центр элемента
            tgt_cx = tgt_pos["x"]
            tgt_cy = tgt_pos["y"] + tgt_pos["height"] / 2

            waypoints: list[dict[str, float]] = []

            # Если цель левее источника (обратный поток), добавляем промежуточные точки
            if tgt_cx < src_cx:
                mid_y = max(src_cy, tgt_cy) + VERTICAL_SPACING
                waypoints = [
                    {"x": round(src_cx, 1), "y": round(src_cy, 1)},
                    {"x": round(src_cx + HORIZONTAL_SPACING / 2, 1), "y": round(src_cy, 1)},
                    {"x": round(src_cx + HORIZONTAL_SPACING / 2, 1), "y": round(mid_y, 1)},
                    {"x": round(tgt_cx - HORIZONTAL_SPACING / 2, 1), "y": round(mid_y, 1)},
                    {"x": round(tgt_cx - HORIZONTAL_SPACING / 2, 1), "y": round(tgt_cy, 1)},
                    {"x": round(tgt_cx, 1), "y": round(tgt_cy, 1)},
                ]
            elif abs(src_cy - tgt_cy) < 1.0:
                # Прямая горизонтальная линия
                waypoints = [
                    {"x": round(src_cx, 1), "y": round(src_cy, 1)},
                    {"x": round(tgt_cx, 1), "y": round(tgt_cy, 1)},
                ]
            else:
                # Ступенчатая линия (L-образная или Z-образная)
                mid_x = (src_cx + tgt_cx) / 2
                waypoints = [
                    {"x": round(src_cx, 1), "y": round(src_cy, 1)},
                    {"x": round(mid_x, 1), "y": round(src_cy, 1)},
                    {"x": round(mid_x, 1), "y": round(tgt_cy, 1)},
                    {"x": round(tgt_cx, 1), "y": round(tgt_cy, 1)},
                ]

            result[flow_id] = waypoints

        return result

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_layout() -> dict[str, Any]:
        """Возвращает пустую структуру компоновки."""
        return {
            "elements": {},
            "flows": {},
            "lanes": {},
            "participants": {},
        }
