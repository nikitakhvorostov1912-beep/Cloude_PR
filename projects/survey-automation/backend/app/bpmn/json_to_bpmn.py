"""Конвертация BPMN JSON-структуры в BPMN 2.0 XML.

Модуль принимает JSON-описание бизнес-процесса и генерирует
валидный BPMN 2.0 XML с использованием lxml.etree, включая
Diagram Interchange (DI) для визуализации.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from lxml import etree

from app.exceptions import ExportError, ProcessingError

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Пространства имён BPMN 2.0
# ----------------------------------------------------------------------

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"

NSMAP: dict[str | None, str] = {
    None: BPMN_NS,
    "bpmndi": BPMNDI_NS,
    "dc": DC_NS,
    "di": DI_NS,
}

# Теги BPMN (без префикса - принадлежат пространству по умолчанию)
_BPMN = "{%s}" % BPMN_NS
_BPMNDI = "{%s}" % BPMNDI_NS
_DC = "{%s}" % DC_NS
_DI = "{%s}" % DI_NS

# ----------------------------------------------------------------------
# Допустимые типы элементов
# ----------------------------------------------------------------------

#: Типы событий
EVENT_TYPES: frozenset[str] = frozenset({
    "startEvent",
    "endEvent",
    "intermediateCatchEvent",
    "intermediateThrowEvent",
})

#: Типы задач
TASK_TYPES: frozenset[str] = frozenset({
    "task",
    "userTask",
    "serviceTask",
    "scriptTask",
    "manualTask",
})

#: Типы шлюзов
GATEWAY_TYPES: frozenset[str] = frozenset({
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "eventBasedGateway",
})

#: Типы контейнеров
CONTAINER_TYPES: frozenset[str] = frozenset({
    "subProcess",
})

#: Типы данных
DATA_TYPES: frozenset[str] = frozenset({
    "dataObject",
    "dataStore",
})

#: Типы аннотаций
ANNOTATION_TYPES: frozenset[str] = frozenset({
    "textAnnotation",
})

#: Все допустимые типы элементов процесса
ALL_ELEMENT_TYPES: frozenset[str] = (
    EVENT_TYPES | TASK_TYPES | GATEWAY_TYPES | CONTAINER_TYPES
    | DATA_TYPES | ANNOTATION_TYPES
)

# Типы определений событий (event definitions)
EVENT_DEFINITION_TYPES: dict[str, str] = {
    "timer": "timerEventDefinition",
    "message": "messageEventDefinition",
    "signal": "signalEventDefinition",
}


class BpmnConverter:
    """Конвертирует JSON-описание BPMN-процесса в BPMN 2.0 XML.

    Поддерживает полный набор элементов BPMN 2.0:
    - Процессы (Process) с пулами (Participant) и дорожками (Lane)
    - События: start, end, intermediate (catch/throw) с timer/message/signal
    - Задачи: task, userTask, serviceTask, scriptTask, manualTask
    - Шлюзы: exclusive, parallel, inclusive, eventBased
    - Подпроцессы (SubProcess)
    - Потоки управления (SequenceFlow) с условиями
    - Потоки сообщений (MessageFlow)
    - Объекты данных (DataObject, DataStore)
    - Аннотации (TextAnnotation) и ассоциации (Association)
    - Diagram Interchange (DI) для визуализации

    Example:
        >>> converter = BpmnConverter()
        >>> xml_str = converter.convert(bpmn_json)
    """

    def convert(self, bpmn_json: dict[str, Any]) -> str:
        """Конвертирует BPMN JSON в BPMN 2.0 XML-строку.

        Args:
            bpmn_json: Словарь с описанием BPMN-процесса.
                Обязательные ключи: ``process_id``, ``elements``, ``flows``.
                Опциональные: ``process_name``, ``participants``, ``message_flows``,
                ``annotations``, ``associations``, ``data_objects``, ``data_stores``.

        Returns:
            Строка с валидным BPMN 2.0 XML.

        Raises:
            ProcessingError: Если структура JSON некорректна.
            ExportError: Если не удалось сформировать XML.
        """
        self._validate_input(bpmn_json)

        try:
            root = self._build_definitions(bpmn_json)
            xml_bytes: bytes = etree.tostring(
                root,
                xml_declaration=True,
                encoding="UTF-8",
                pretty_print=True,
            )
            return xml_bytes.decode("utf-8")
        except (ProcessingError, ExportError):
            raise
        except Exception as exc:
            logger.exception("Не удалось сформировать BPMN XML: %s", exc)
            raise ExportError(
                "Ошибка при формировании BPMN XML",
                detail=str(exc),
            ) from exc

    # ------------------------------------------------------------------
    # Валидация
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_input(bpmn_json: dict[str, Any]) -> None:
        """Проверяет минимальную корректность входного JSON."""
        if not isinstance(bpmn_json, dict):
            raise ProcessingError(
                "Входные данные должны быть словарём (dict)",
                detail=f"Получен тип: {type(bpmn_json).__name__}",
            )

        if "process_id" not in bpmn_json:
            raise ProcessingError(
                "Отсутствует обязательное поле 'process_id'",
            )

        elements = bpmn_json.get("elements")
        if elements is not None and not isinstance(elements, list):
            raise ProcessingError(
                "Поле 'elements' должно быть списком",
                detail=f"Получен тип: {type(elements).__name__}",
            )

        flows = bpmn_json.get("flows")
        if flows is not None and not isinstance(flows, list):
            raise ProcessingError(
                "Поле 'flows' должно быть списком",
                detail=f"Получен тип: {type(flows).__name__}",
            )

        # Проверяем типы элементов
        for elem in (elements or []):
            elem_type = elem.get("type", "")
            if elem_type and elem_type not in ALL_ELEMENT_TYPES:
                logger.warning(
                    "Неизвестный тип элемента '%s' (id=%s), будет пропущен",
                    elem_type,
                    elem.get("id", "?"),
                )

    # ------------------------------------------------------------------
    # Построение XML-дерева
    # ------------------------------------------------------------------

    def _build_definitions(self, bpmn_json: dict[str, Any]) -> etree._Element:
        """Строит корневой элемент ``<definitions>``."""
        process_id = bpmn_json["process_id"]
        definitions_id = f"Definitions_{_short_uuid()}"

        root = etree.Element(
            f"{_BPMN}definitions",
            nsmap=NSMAP,
            attrib={
                "id": definitions_id,
                "targetNamespace": "http://bpmn.io/schema/bpmn",
                "exporter": "SurveyAutomation",
                "exporterVersion": "1.0",
            },
        )

        participants = bpmn_json.get("participants") or []
        has_collaboration = len(participants) > 0

        # --- Collaboration (пулы) ---
        collaboration_id: str | None = None
        if has_collaboration:
            collaboration_id = f"Collaboration_{_short_uuid()}"
            collab_elem = etree.SubElement(
                root,
                f"{_BPMN}collaboration",
                attrib={"id": collaboration_id},
            )
            for part in participants:
                part_attrib: dict[str, str] = {
                    "id": part["id"],
                    "processRef": process_id,
                }
                if part.get("name"):
                    part_attrib["name"] = part["name"]
                etree.SubElement(
                    collab_elem,
                    f"{_BPMN}participant",
                    attrib=part_attrib,
                )

            # Message flows (между пулами)
            for mf in bpmn_json.get("message_flows") or []:
                mf_attrib: dict[str, str] = {
                    "id": mf.get("id", f"MsgFlow_{_short_uuid()}"),
                    "sourceRef": mf["source"],
                    "targetRef": mf["target"],
                }
                if mf.get("name"):
                    mf_attrib["name"] = mf["name"]
                etree.SubElement(
                    collab_elem,
                    f"{_BPMN}messageFlow",
                    attrib=mf_attrib,
                )

        # --- Process ---
        process_attrib: dict[str, str] = {
            "id": process_id,
            "isExecutable": "true",
        }
        if bpmn_json.get("process_name"):
            process_attrib["name"] = bpmn_json["process_name"]

        process_elem = etree.SubElement(
            root,
            f"{_BPMN}process",
            attrib=process_attrib,
        )

        # --- LaneSet ---
        lanes = self._collect_lanes(bpmn_json)
        elements = bpmn_json.get("elements") or []
        if lanes:
            self._add_lane_set(process_elem, lanes, elements)

        # --- Элементы процесса ---
        for elem in elements:
            self._add_element(process_elem, elem)

        # --- DataObject / DataStore ---
        for dobj in bpmn_json.get("data_objects") or []:
            self._add_data_element(process_elem, dobj, "dataObject")
        for dstore in bpmn_json.get("data_stores") or []:
            self._add_data_element(root, dstore, "dataStore")

        # --- SequenceFlow ---
        for flow in bpmn_json.get("flows") or []:
            self._add_sequence_flow(process_elem, flow)

        # --- TextAnnotation / Association ---
        for ann in bpmn_json.get("annotations") or []:
            self._add_annotation(process_elem, ann)
        for assoc in bpmn_json.get("associations") or []:
            self._add_association(process_elem, assoc)

        # --- BPMN DI ---
        layout = bpmn_json.get("layout") or {}
        self._add_diagram(
            root,
            bpmn_json,
            layout,
            collaboration_id=collaboration_id,
        )

        return root

    # ------------------------------------------------------------------
    # Дорожки (Lanes)
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_lanes(bpmn_json: dict[str, Any]) -> list[dict[str, Any]]:
        """Собирает информацию о дорожках из участников."""
        lanes: list[dict[str, Any]] = []
        seen_lane_ids: set[str] = set()
        for part in bpmn_json.get("participants") or []:
            lane_id = part.get("lane_id")
            if lane_id and lane_id not in seen_lane_ids:
                seen_lane_ids.add(lane_id)
                lanes.append({
                    "id": lane_id,
                    "name": part.get("name", ""),
                })
        return lanes

    @staticmethod
    def _add_lane_set(
        process_elem: etree._Element,
        lanes: list[dict[str, Any]],
        elements: list[dict[str, Any]],
    ) -> None:
        """Добавляет ``<laneSet>`` с дорожками в процесс."""
        lane_set = etree.SubElement(
            process_elem,
            f"{_BPMN}laneSet",
            attrib={"id": f"LaneSet_{_short_uuid()}"},
        )

        # Сгруппировать элементы по lane
        lane_elements: dict[str, list[str]] = {}
        for elem in elements:
            lane_id = elem.get("lane")
            if lane_id:
                lane_elements.setdefault(lane_id, []).append(elem["id"])

        for lane in lanes:
            lane_elem = etree.SubElement(
                lane_set,
                f"{_BPMN}lane",
                attrib={"id": lane["id"], "name": lane.get("name", "")},
            )
            for ref_id in lane_elements.get(lane["id"], []):
                flow_node_ref = etree.SubElement(
                    lane_elem,
                    f"{_BPMN}flowNodeRef",
                )
                flow_node_ref.text = ref_id

    # ------------------------------------------------------------------
    # Элементы процесса
    # ------------------------------------------------------------------

    def _add_element(
        self,
        parent: etree._Element,
        elem: dict[str, Any],
    ) -> None:
        """Добавляет элемент BPMN (событие, задачу, шлюз, подпроцесс)."""
        elem_type = elem.get("type", "")
        elem_id = elem.get("id", f"Element_{_short_uuid()}")
        elem_name = elem.get("name", "")

        if elem_type not in ALL_ELEMENT_TYPES:
            logger.warning("Пропущен элемент с неизвестным типом: %s", elem_type)
            return

        attrib: dict[str, str] = {"id": elem_id}
        if elem_name:
            attrib["name"] = elem_name

        # Дополнительные атрибуты для шлюзов
        if elem_type == "exclusiveGateway":
            default_flow = elem.get("default")
            if default_flow:
                attrib["gatewayDirection"] = "Diverging"
                attrib["default"] = default_flow

        xml_elem = etree.SubElement(parent, f"{_BPMN}{elem_type}", attrib=attrib)

        # Event definitions (timer, message, signal)
        if elem_type in EVENT_TYPES:
            self._add_event_definitions(xml_elem, elem)

        # SubProcess: рекурсивно добавляем вложенные элементы
        if elem_type == "subProcess":
            for sub_elem in elem.get("elements") or []:
                self._add_element(xml_elem, sub_elem)
            for sub_flow in elem.get("flows") or []:
                self._add_sequence_flow(xml_elem, sub_flow)

        # Входящие/исходящие потоки (опционально, для документирования)
        for incoming_id in elem.get("incoming") or []:
            inc = etree.SubElement(xml_elem, f"{_BPMN}incoming")
            inc.text = incoming_id
        for outgoing_id in elem.get("outgoing") or []:
            out = etree.SubElement(xml_elem, f"{_BPMN}outgoing")
            out.text = outgoing_id

    @staticmethod
    def _add_event_definitions(
        event_elem: etree._Element,
        elem: dict[str, Any],
    ) -> None:
        """Добавляет определения событий (timer, message, signal)."""
        event_def_type = elem.get("event_definition_type")
        if not event_def_type:
            return

        tag_name = EVENT_DEFINITION_TYPES.get(event_def_type)
        if not tag_name:
            logger.warning(
                "Неизвестный тип определения события: %s (id=%s)",
                event_def_type,
                elem.get("id", "?"),
            )
            return

        def_attrib: dict[str, str] = {
            "id": f"EventDef_{_short_uuid()}",
        }
        def_elem = etree.SubElement(
            event_elem,
            f"{_BPMN}{tag_name}",
            attrib=def_attrib,
        )

        # Timer: выражение длительности или даты
        if event_def_type == "timer":
            timer_value = elem.get("timer_value")
            timer_type = elem.get("timer_type", "timeDuration")
            if timer_value:
                timer_child = etree.SubElement(
                    def_elem,
                    f"{_BPMN}{timer_type}",
                )
                # xsi:type="tFormalExpression"
                timer_child.text = timer_value

    # ------------------------------------------------------------------
    # Потоки управления
    # ------------------------------------------------------------------

    @staticmethod
    def _add_sequence_flow(
        parent: etree._Element,
        flow: dict[str, Any],
    ) -> None:
        """Добавляет ``<sequenceFlow>`` в процесс."""
        flow_id = flow.get("id", f"Flow_{_short_uuid()}")
        source_ref = flow.get("source", "")
        target_ref = flow.get("target", "")

        if not source_ref or not target_ref:
            logger.warning(
                "Поток '%s' пропущен: отсутствует source или target",
                flow_id,
            )
            return

        attrib: dict[str, str] = {
            "id": flow_id,
            "sourceRef": source_ref,
            "targetRef": target_ref,
        }

        name = flow.get("name")
        if name:
            attrib["name"] = name

        flow_elem = etree.SubElement(
            parent,
            f"{_BPMN}sequenceFlow",
            attrib=attrib,
        )

        # Условие перехода
        condition = flow.get("condition")
        if condition:
            cond_elem = etree.SubElement(
                flow_elem,
                f"{_BPMN}conditionExpression",
                attrib={
                    "{http://www.w3.org/2001/XMLSchema-instance}type": "tFormalExpression",
                },
            )
            cond_elem.text = condition

    # ------------------------------------------------------------------
    # Объекты данных
    # ------------------------------------------------------------------

    @staticmethod
    def _add_data_element(
        parent: etree._Element,
        data: dict[str, Any],
        data_type: str,
    ) -> None:
        """Добавляет ``<dataObject>`` или ``<dataStore>``."""
        attrib: dict[str, str] = {
            "id": data.get("id", f"Data_{_short_uuid()}"),
        }
        if data.get("name"):
            attrib["name"] = data["name"]

        etree.SubElement(parent, f"{_BPMN}{data_type}", attrib=attrib)

    # ------------------------------------------------------------------
    # Аннотации и ассоциации
    # ------------------------------------------------------------------

    @staticmethod
    def _add_annotation(
        parent: etree._Element,
        annotation: dict[str, Any],
    ) -> None:
        """Добавляет ``<textAnnotation>`` в процесс."""
        ann_id = annotation.get("id", f"Annotation_{_short_uuid()}")
        ann_elem = etree.SubElement(
            parent,
            f"{_BPMN}textAnnotation",
            attrib={"id": ann_id},
        )
        text = annotation.get("text", "")
        text_elem = etree.SubElement(ann_elem, f"{_BPMN}text")
        text_elem.text = text

    @staticmethod
    def _add_association(
        parent: etree._Element,
        association: dict[str, Any],
    ) -> None:
        """Добавляет ``<association>`` в процесс."""
        attrib: dict[str, str] = {
            "id": association.get("id", f"Assoc_{_short_uuid()}"),
            "sourceRef": association.get("source", ""),
            "targetRef": association.get("target", ""),
        }
        direction = association.get("direction", "None")
        attrib["associationDirection"] = direction

        etree.SubElement(parent, f"{_BPMN}association", attrib=attrib)

    # ------------------------------------------------------------------
    # BPMN Diagram Interchange (DI)
    # ------------------------------------------------------------------

    def _add_diagram(
        self,
        root: etree._Element,
        bpmn_json: dict[str, Any],
        layout: dict[str, Any],
        *,
        collaboration_id: str | None = None,
    ) -> None:
        """Добавляет секцию ``<BPMNDiagram>`` с визуальным представлением."""
        diagram_id = f"BPMNDiagram_{_short_uuid()}"
        diagram = etree.SubElement(
            root,
            f"{_BPMNDI}BPMNDiagram",
            attrib={"id": diagram_id},
        )

        plane_element = collaboration_id or bpmn_json["process_id"]
        plane = etree.SubElement(
            diagram,
            f"{_BPMNDI}BPMNPlane",
            attrib={
                "id": f"BPMNPlane_{_short_uuid()}",
                "bpmnElement": plane_element,
            },
        )

        element_positions = layout.get("elements") or {}
        flow_positions = layout.get("flows") or {}
        lane_positions = layout.get("lanes") or {}
        participant_positions = layout.get("participants") or {}

        # Участники (пулы)
        for part in bpmn_json.get("participants") or []:
            pos = participant_positions.get(part["id"], {})
            self._add_shape_di(plane, part["id"], pos)

        # Дорожки
        for lane_id, lane_pos in lane_positions.items():
            self._add_shape_di(plane, lane_id, lane_pos, is_horizontal=True)

        # Элементы
        for elem in bpmn_json.get("elements") or []:
            pos = element_positions.get(elem["id"], {})
            self._add_shape_di(plane, elem["id"], pos)

            # Вложенные элементы подпроцесса
            if elem.get("type") == "subProcess":
                for sub_elem in elem.get("elements") or []:
                    sub_pos = element_positions.get(sub_elem["id"], {})
                    self._add_shape_di(plane, sub_elem["id"], sub_pos)

        # Аннотации
        for ann in bpmn_json.get("annotations") or []:
            pos = element_positions.get(ann["id"], {})
            self._add_shape_di(plane, ann["id"], pos)

        # Потоки управления
        for flow in bpmn_json.get("flows") or []:
            waypoints = flow_positions.get(flow.get("id", ""), [])
            self._add_edge_di(plane, flow.get("id", ""), waypoints)

        # Потоки сообщений
        for mf in bpmn_json.get("message_flows") or []:
            mf_id = mf.get("id", "")
            waypoints = flow_positions.get(mf_id, [])
            self._add_edge_di(plane, mf_id, waypoints)

        # Ассоциации
        for assoc in bpmn_json.get("associations") or []:
            assoc_id = assoc.get("id", "")
            waypoints = flow_positions.get(assoc_id, [])
            self._add_edge_di(plane, assoc_id, waypoints)

    @staticmethod
    def _add_shape_di(
        plane: etree._Element,
        bpmn_element_id: str,
        position: dict[str, float],
        *,
        is_horizontal: bool = False,
    ) -> None:
        """Добавляет ``<BPMNShape>`` для элемента."""
        shape_attrib: dict[str, str] = {
            "id": f"{bpmn_element_id}_di",
            "bpmnElement": bpmn_element_id,
        }
        if is_horizontal:
            shape_attrib["isHorizontal"] = "true"

        shape = etree.SubElement(
            plane,
            f"{_BPMNDI}BPMNShape",
            attrib=shape_attrib,
        )

        x = position.get("x", 0)
        y = position.get("y", 0)
        width = position.get("width", 100)
        height = position.get("height", 80)

        etree.SubElement(
            shape,
            f"{_DC}Bounds",
            attrib={
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
            },
        )

        # Метка
        if position.get("label"):
            label = etree.SubElement(shape, f"{_BPMNDI}BPMNLabel")
            label_bounds = position["label"]
            etree.SubElement(
                label,
                f"{_DC}Bounds",
                attrib={
                    "x": str(label_bounds.get("x", x)),
                    "y": str(label_bounds.get("y", y + height)),
                    "width": str(label_bounds.get("width", width)),
                    "height": str(label_bounds.get("height", 20)),
                },
            )

    @staticmethod
    def _add_edge_di(
        plane: etree._Element,
        bpmn_element_id: str,
        waypoints: list[dict[str, float]],
    ) -> None:
        """Добавляет ``<BPMNEdge>`` для потока."""
        edge = etree.SubElement(
            plane,
            f"{_BPMNDI}BPMNEdge",
            attrib={
                "id": f"{bpmn_element_id}_di",
                "bpmnElement": bpmn_element_id,
            },
        )

        # Если нет waypoints, создаём заглушку
        if not waypoints:
            waypoints = [{"x": 0, "y": 0}, {"x": 100, "y": 0}]

        for wp in waypoints:
            etree.SubElement(
                edge,
                f"{_DI}waypoint",
                attrib={
                    "x": str(wp.get("x", 0)),
                    "y": str(wp.get("y", 0)),
                },
            )


# ------------------------------------------------------------------
# Вспомогательные функции
# ------------------------------------------------------------------


def _short_uuid() -> str:
    """Генерирует короткий уникальный идентификатор (8 символов)."""
    return uuid.uuid4().hex[:8]
