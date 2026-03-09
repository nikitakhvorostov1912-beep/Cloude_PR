"""Конвертер данных процесса в BPMN JSON-формат.

Принимает структуру процесса с шагами (steps), решениями (decisions)
и участниками (participants), и формирует BPMN JSON с элементами
(elements), потоками (flows), дорожками (lanes) и участниками.

Это промежуточный слой между извлечёнными процессами и генераторами
BPMN XML / Visio / SVG.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def _uid(prefix: str = "id") -> str:
    """Генерирует короткий уникальный ID."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _safe_id(text: str) -> str:
    """Преобразует текст в безопасный XML-идентификатор.

    Для кириллических и других не-ASCII строк добавляет короткий
    хеш оригинального текста, чтобы гарантировать уникальность
    (иначе разные кириллические строки одинаковой длины
    дают одинаковый ID из подчёркиваний).
    """
    # Проверяем, содержит ли текст не-ASCII символы
    has_non_ascii = bool(re.search(r"[^\x00-\x7f]", text))
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", text)
    if safe and safe[0].isdigit():
        safe = f"id_{safe}"
    # Добавляем хеш для строк с не-ASCII символами
    if has_non_ascii:
        short_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
        # Берём ASCII-префикс (если есть) + хеш
        prefix = re.sub(r"_+$", "", safe[:30]).rstrip("_")
        safe = f"{prefix}_{short_hash}" if prefix else f"id_{short_hash}"
    return safe[:50] or _uid()


class ProcessToBpmnConverter:
    """Конвертирует описание бизнес-процесса в BPMN JSON.

    Вход: словарь процесса из стадии extract::

        {
            "id": "proc_001",
            "name": "Обработка заказа клиента",
            "steps": [
                {"order": 1, "name": "Приём заявки", "performer": "Менеджер", ...},
                ...
            ],
            "decisions": [
                {"condition": "Товар на складе?", "yes_branch": "...", "no_branch": "..."},
                ...
            ],
            "participants": [
                {"role": "Менеджер", "department": "Продажи"},
                ...
            ],
            "trigger": "...",
            "result": "...",
        }

    Выход: BPMN JSON для BpmnConverter / VsdxGenerator::

        {
            "process_id": "proc_001",
            "process_name": "Обработка заказа клиента",
            "elements": [...],
            "flows": [...],
            "participants": [...],
        }

    Example::

        converter = ProcessToBpmnConverter()
        bpmn_json = converter.convert(process_data)
    """

    def convert(self, process: dict[str, Any]) -> dict[str, Any]:
        """Конвертирует процесс в BPMN JSON.

        Args:
            process: Словарь с описанием процесса.

        Returns:
            BPMN JSON-структура для генерации BPMN XML и Visio.
        """
        proc_id = process.get("id", _uid("proc"))
        proc_name = process.get("name", "Бизнес-процесс")

        steps = process.get("steps") or []
        decisions = process.get("decisions") or []
        participants_raw = process.get("participants") or []

        # Собираем уникальных исполнителей → дорожки
        lanes = self._build_lanes(steps, participants_raw)
        lane_id_map = {lane["name"]: lane["id"] for lane in lanes}

        # Генерируем BPMN-элементы
        elements: list[dict[str, Any]] = []
        flows: list[dict[str, Any]] = []

        # 1. Стартовое событие
        start_id = f"{proc_id}_start"
        trigger_text = process.get("trigger", "Начало")
        elements.append({
            "id": start_id,
            "type": "startEvent",
            "name": self._truncate(trigger_text, 40),
            "lane": self._get_first_lane(lanes),
        })

        # 2. Шаги → задачи + решения → шлюзы
        prev_id = start_id
        decision_map = self._map_decisions_to_steps(decisions, steps)

        sorted_steps = sorted(steps, key=lambda s: s.get("order", 0))

        for i, step in enumerate(sorted_steps):
            step_order = step.get("order", i + 1)
            step_name = step.get("name", step.get("step", f"Шаг {step_order}"))
            performer = step.get("performer", step.get("executor", ""))
            lane_id = lane_id_map.get(performer)

            # Определяем тип задачи
            task_type = self._infer_task_type(step)
            task_id = f"{proc_id}_task_{step_order}"

            elements.append({
                "id": task_id,
                "type": task_type,
                "name": step_name,
                "lane": lane_id,
            })

            # Поток от предыдущего элемента
            flow_id = f"{proc_id}_flow_{prev_id}_to_{task_id}"
            flows.append({
                "id": flow_id,
                "source": prev_id,
                "target": task_id,
            })

            prev_id = task_id

            # Проверяем, есть ли решение после этого шага
            step_decision = decision_map.get(step_order)
            if step_decision:
                gw_result = self._add_gateway_for_decision(
                    proc_id, step_decision, step_order,
                    prev_id, lane_id, elements, flows,
                )
                prev_id = gw_result["merge_id"]

        # 3. Конечное событие
        end_id = f"{proc_id}_end"
        result_text = process.get("result", "Завершение")
        elements.append({
            "id": end_id,
            "type": "endEvent",
            "name": self._truncate(result_text, 40),
            "lane": self._get_first_lane(lanes),
        })

        flows.append({
            "id": f"{proc_id}_flow_{prev_id}_to_{end_id}",
            "source": prev_id,
            "target": end_id,
        })

        # 4. Формируем участников (пулы)
        bpmn_participants = []
        if lanes:
            bpmn_participants.append({
                "id": f"{proc_id}_pool",
                "name": proc_name,
                "processRef": proc_id,
            })
            for lane in lanes:
                lane["participant_id"] = f"{proc_id}_pool"

        result = {
            "process_id": proc_id,
            "process_name": proc_name,
            "elements": elements,
            "flows": flows,
            "participants": bpmn_participants,
            "annotations": [],
            "associations": [],
            "message_flows": [],
            "data_objects": [],
            "data_stores": [],
        }

        # Добавляем информацию о дорожках в participants для layout
        for lane in lanes:
            bpmn_participants.append({
                "id": lane["id"],
                "name": lane["name"],
                "lane_id": lane["id"],
            })

        logger.info(
            "Конвертирован процесс '%s': %d элементов, %d потоков, %d дорожек",
            proc_name, len(elements), len(flows), len(lanes),
        )

        return result

    def convert_all(self, processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Конвертирует список процессов в список BPMN JSON.

        Args:
            processes: Список словарей с описанием процессов.

        Returns:
            Список BPMN JSON-структур.
        """
        results = []
        for process in processes:
            try:
                bpmn_json = self.convert(process)
                results.append(bpmn_json)
            except Exception as exc:
                logger.warning(
                    "Ошибка конвертации процесса '%s': %s",
                    process.get("name", "?"), exc,
                )
        return results

    # ------------------------------------------------------------------
    # Дорожки (Lanes)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_lanes(
        steps: list[dict[str, Any]],
        participants: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Собирает уникальные дорожки из исполнителей шагов."""
        seen: dict[str, dict[str, Any]] = {}

        # Из участников
        for p in participants:
            name = p.get("role", "") if isinstance(p, dict) else str(p)
            if name and name not in seen:
                dept = p.get("department", "") if isinstance(p, dict) else ""
                seen[name] = {
                    "id": _safe_id(f"lane_{name}"),
                    "name": name,
                    "department": dept,
                }

        # Из исполнителей шагов (могут быть новые)
        for step in steps:
            performer = step.get("performer", step.get("executor", ""))
            if performer and performer not in seen:
                seen[performer] = {
                    "id": _safe_id(f"lane_{performer}"),
                    "name": performer,
                    "department": "",
                }

        return list(seen.values())

    @staticmethod
    def _get_first_lane(lanes: list[dict[str, Any]]) -> str | None:
        """Возвращает ID первой дорожки или None."""
        return lanes[0]["id"] if lanes else None

    # ------------------------------------------------------------------
    # Решения → Шлюзы
    # ------------------------------------------------------------------

    @staticmethod
    def _map_decisions_to_steps(
        decisions: list[dict[str, Any]],
        steps: list[dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:
        """Привязывает решения к шагам.

        Если у решения есть ``after_step``, используется он.
        Иначе решения распределяются равномерно по шагам.
        """
        result: dict[int, dict[str, Any]] = {}

        for i, decision in enumerate(decisions):
            after_step = decision.get("after_step")
            if after_step is not None:
                result[int(after_step)] = decision
            else:
                # Распределяем после каждого N-го шага
                if steps:
                    step_idx = min(i + 1, len(steps))
                    step_order = steps[step_idx - 1].get("order", step_idx)
                    if step_order not in result:
                        result[step_order] = decision

        return result

    def _add_gateway_for_decision(
        self,
        proc_id: str,
        decision: dict[str, Any],
        step_order: int,
        prev_id: str,
        lane_id: str | None,
        elements: list[dict[str, Any]],
        flows: list[dict[str, Any]],
    ) -> dict[str, str]:
        """Добавляет шлюз с ветвлением для решения.

        Создаёт: exclusiveGateway (split) → ветки Да/Нет → exclusiveGateway (merge).

        Returns:
            Словарь с ключом ``merge_id`` — ID элемента слияния.
        """
        condition = decision.get("condition", decision.get("question", "Условие?"))
        yes_branch = decision.get("yes_branch", decision.get("yes", "Да"))
        no_branch = decision.get("no_branch", decision.get("no", "Нет"))

        # Шлюз разветвления
        gw_split_id = f"{proc_id}_gw_split_{step_order}"
        elements.append({
            "id": gw_split_id,
            "type": "exclusiveGateway",
            "name": self._truncate(condition, 35),
            "lane": lane_id,
        })

        flows.append({
            "id": f"{proc_id}_flow_{prev_id}_to_{gw_split_id}",
            "source": prev_id,
            "target": gw_split_id,
        })

        # Задача ветки "Да"
        yes_task_id = f"{proc_id}_yes_{step_order}"
        elements.append({
            "id": yes_task_id,
            "type": "task",
            "name": self._truncate(yes_branch, 30),
            "lane": lane_id,
        })

        flows.append({
            "id": f"{proc_id}_flow_{gw_split_id}_to_{yes_task_id}",
            "source": gw_split_id,
            "target": yes_task_id,
            "name": "Да",
            "condition": condition,
        })

        # Задача ветки "Нет"
        no_task_id = f"{proc_id}_no_{step_order}"
        elements.append({
            "id": no_task_id,
            "type": "task",
            "name": self._truncate(no_branch, 30),
            "lane": lane_id,
        })

        flows.append({
            "id": f"{proc_id}_flow_{gw_split_id}_to_{no_task_id}",
            "source": gw_split_id,
            "target": no_task_id,
            "name": "Нет",
        })

        # Шлюз слияния
        gw_merge_id = f"{proc_id}_gw_merge_{step_order}"
        elements.append({
            "id": gw_merge_id,
            "type": "exclusiveGateway",
            "name": "",
            "lane": lane_id,
        })

        flows.append({
            "id": f"{proc_id}_flow_{yes_task_id}_to_{gw_merge_id}",
            "source": yes_task_id,
            "target": gw_merge_id,
        })
        flows.append({
            "id": f"{proc_id}_flow_{no_task_id}_to_{gw_merge_id}",
            "source": no_task_id,
            "target": gw_merge_id,
        })

        return {"merge_id": gw_merge_id}

    # ------------------------------------------------------------------
    # Тип задачи
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_task_type(step: dict[str, Any]) -> str:
        """Определяет тип BPMN-задачи по данным шага."""
        systems = step.get("systems", step.get("system", []))
        if isinstance(systems, str):
            systems = [systems]

        # Если есть системы автоматизации → serviceTask
        auto_systems = {"1С", "1C", "ERP", "API", "REST", "SOAP", "SAP"}
        if systems:
            for sys_name in systems:
                if any(kw in str(sys_name).upper() for kw in auto_systems):
                    return "serviceTask"

        # Если исполнитель — система
        performer = str(step.get("performer", step.get("executor", ""))).lower()
        if any(kw in performer for kw in ["система", "сервис", "автомат", "бот"]):
            return "serviceTask"

        # По умолчанию — userTask (пользовательская задача)
        return "userTask"

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate(text: str, max_len: int = 40) -> str:
        """Обрезает текст до max_len символов."""
        text = str(text).strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"
