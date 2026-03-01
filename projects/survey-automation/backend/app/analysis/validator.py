"""Валидатор данных бизнес-процессов.

Проверяет корректность структуры, обязательных полей, типов данных
и логическую согласованность данных процессов, BPMN JSON, GAP-анализа
и листов требований.

Все сообщения об ошибках и предупреждениях на русском языке.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Модели результата валидации
# ----------------------------------------------------------------------


class ValidationResult(BaseModel):
    """Результат валидации данных.

    Attributes:
        valid: True, если данные прошли валидацию без критических ошибок.
        errors: Список критических ошибок, блокирующих дальнейшую обработку.
        warnings: Список предупреждений (некритичные замечания).
    """

    valid: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Добавляет критическую ошибку и помечает результат как невалидный."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Добавляет предупреждение (не влияет на флаг valid)."""
        self.warnings.append(message)

    def merge(self, other: ValidationResult) -> None:
        """Объединяет результаты другой валидации в текущий."""
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


# ----------------------------------------------------------------------
# Допустимые значения перечислений
# ----------------------------------------------------------------------

_VALID_SEVERITIES = {"low", "medium", "high", "critical"}
_VALID_PAIN_CATEGORIES = {
    "efficiency",
    "quality",
    "compliance",
    "integration",
    "manual_work",
}
_VALID_COVERAGE_TYPES = {"full", "partial", "custom", "absent"}
_VALID_PRIORITIES = {"Must", "Should", "Could", "Won't"}
_VALID_REQUIREMENT_TYPES = {"FR", "NFR", "IR"}
_VALID_BPMN_ELEMENT_TYPES = {
    "startEvent",
    "endEvent",
    "task",
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "intermediateCatchEvent",
    "intermediateThrowEvent",
    "subProcess",
}
_VALID_GATEWAY_DIRECTIONS = {"diverging", "converging"}


# ----------------------------------------------------------------------
# Валидатор
# ----------------------------------------------------------------------


class ProcessValidator:
    """Валидатор данных бизнес-процессов и связанных структур.

    Выполняет проверки:
    - Наличие обязательных полей.
    - Корректность типов данных.
    - Допустимость значений перечислений.
    - Логическая согласованность (ссылки, порядок шагов, связи).
    """

    # ------------------------------------------------------------------
    # Валидация бизнес-процесса
    # ------------------------------------------------------------------

    def validate_process(self, data: dict) -> ValidationResult:
        """Валидирует структуру извлечённого бизнес-процесса.

        Проверяет:
        - Обязательные поля: id, name, steps.
        - Типы полей: строки, списки, словари.
        - Корректность шагов: order, name, performer.
        - Корректность pain_points: severity, category.
        - Корректность decisions: condition, yes_branch, no_branch.
        - Логическую согласованность (последовательность order).

        Args:
            data: Словарь с данными процесса.

        Returns:
            ValidationResult с ошибками и предупреждениями.
        """
        result = ValidationResult()

        if not isinstance(data, dict):
            result.add_error("Данные процесса должны быть словарём (dict).")
            return result

        # --- Обязательные поля ---
        self._check_required_str(data, "id", "Процесс", result)
        self._check_required_str(data, "name", "Процесс", result)

        process_id = data.get("id", "<без id>")

        # --- Необязательные строковые поля ---
        for field in ("description", "department", "trigger", "result"):
            if field in data and not isinstance(data[field], str):
                result.add_error(
                    f"Процесс '{process_id}': поле '{field}' должно быть строкой, "
                    f"получено: {type(data[field]).__name__}."
                )

        # --- participants ---
        if "participants" in data:
            if not isinstance(data["participants"], list):
                result.add_error(
                    f"Процесс '{process_id}': поле 'participants' должно быть списком."
                )

        # --- steps ---
        steps = data.get("steps")
        if steps is None:
            result.add_warning(
                f"Процесс '{process_id}': отсутствует поле 'steps'. "
                "Процесс без шагов не может быть преобразован в BPMN."
            )
        elif not isinstance(steps, list):
            result.add_error(
                f"Процесс '{process_id}': поле 'steps' должно быть списком."
            )
        elif len(steps) == 0:
            result.add_warning(
                f"Процесс '{process_id}': список шагов пуст. "
                "Рекомендуется указать хотя бы один шаг."
            )
        else:
            result.merge(self._validate_steps(steps, process_id))

        # --- decisions ---
        decisions = data.get("decisions")
        if decisions is not None:
            if not isinstance(decisions, list):
                result.add_error(
                    f"Процесс '{process_id}': поле 'decisions' должно быть списком."
                )
            else:
                for i, decision in enumerate(decisions):
                    result.merge(
                        self._validate_decision(decision, process_id, i + 1)
                    )

        # --- pain_points ---
        pain_points = data.get("pain_points")
        if pain_points is not None:
            if not isinstance(pain_points, list):
                result.add_error(
                    f"Процесс '{process_id}': поле 'pain_points' должно быть списком."
                )
            else:
                for i, pp in enumerate(pain_points):
                    result.merge(
                        self._validate_pain_point(pp, process_id, i + 1)
                    )

        # --- integrations ---
        if "integrations" in data:
            if not isinstance(data["integrations"], list):
                result.add_error(
                    f"Процесс '{process_id}': поле 'integrations' должно быть списком."
                )

        # --- metrics ---
        if "metrics" in data:
            if not isinstance(data["metrics"], (dict, list)):
                result.add_warning(
                    f"Процесс '{process_id}': поле 'metrics' должно быть "
                    "словарём или списком."
                )

        logger.debug(
            "Валидация процесса '%s': valid=%s, ошибок=%d, предупреждений=%d",
            process_id,
            result.valid,
            len(result.errors),
            len(result.warnings),
        )
        return result

    # ------------------------------------------------------------------
    # Валидация BPMN JSON
    # ------------------------------------------------------------------

    def validate_bpmn_json(self, data: dict) -> ValidationResult:
        """Валидирует JSON-структуру BPMN-диаграммы.

        Проверяет:
        - Обязательные поля: process_id, process_name, elements, flows.
        - Корректность типов элементов.
        - Наличие startEvent и endEvent.
        - Парность шлюзов (diverging/converging).
        - Корректность flows (source/target ссылаются на существующие элементы).
        - Отсутствие «висящих» элементов без связей.

        Args:
            data: Словарь с BPMN JSON.

        Returns:
            ValidationResult с ошибками и предупреждениями.
        """
        result = ValidationResult()

        if not isinstance(data, dict):
            result.add_error("BPMN JSON должен быть словарём (dict).")
            return result

        # --- Обязательные поля ---
        self._check_required_str(data, "process_id", "BPMN", result)
        self._check_required_str(data, "process_name", "BPMN", result)

        process_id = data.get("process_id", "<без id>")

        # --- Elements ---
        elements = data.get("elements")
        if elements is None:
            result.add_error(
                f"BPMN '{process_id}': отсутствует обязательное поле 'elements'."
            )
            return result

        if not isinstance(elements, list):
            result.add_error(
                f"BPMN '{process_id}': поле 'elements' должно быть списком."
            )
            return result

        if len(elements) == 0:
            result.add_error(
                f"BPMN '{process_id}': список элементов пуст."
            )
            return result

        # Собираем все id элементов и проверяем типы
        element_ids: set[str] = set()
        has_start = False
        has_end = False
        diverging_gateways: list[str] = []
        converging_gateways: list[str] = []

        for i, elem in enumerate(elements):
            if not isinstance(elem, dict):
                result.add_error(
                    f"BPMN '{process_id}': элемент #{i + 1} должен быть словарём."
                )
                continue

            elem_id = elem.get("id")
            elem_type = elem.get("type")

            if not elem_id or not isinstance(elem_id, str):
                result.add_error(
                    f"BPMN '{process_id}': элемент #{i + 1} не имеет "
                    "корректного поля 'id'."
                )
                continue

            if elem_id in element_ids:
                result.add_error(
                    f"BPMN '{process_id}': дублирующийся id элемента '{elem_id}'."
                )
            element_ids.add(elem_id)

            if not elem_type or elem_type not in _VALID_BPMN_ELEMENT_TYPES:
                result.add_error(
                    f"BPMN '{process_id}': элемент '{elem_id}' имеет "
                    f"некорректный тип '{elem_type}'. "
                    f"Допустимые: {', '.join(sorted(_VALID_BPMN_ELEMENT_TYPES))}."
                )
                continue

            if elem_type == "startEvent":
                has_start = True
            elif elem_type == "endEvent":
                has_end = True
            elif elem_type in (
                "exclusiveGateway",
                "parallelGateway",
                "inclusiveGateway",
            ):
                direction = elem.get("direction")
                if direction == "diverging":
                    diverging_gateways.append(elem_id)
                elif direction == "converging":
                    converging_gateways.append(elem_id)
                elif direction:
                    result.add_warning(
                        f"BPMN '{process_id}': шлюз '{elem_id}' имеет "
                        f"нестандартное направление '{direction}'. "
                        f"Допустимые: {', '.join(_VALID_GATEWAY_DIRECTIONS)}."
                    )
                else:
                    result.add_warning(
                        f"BPMN '{process_id}': шлюз '{elem_id}' не имеет "
                        "указанного направления (diverging/converging)."
                    )

        if not has_start:
            result.add_error(
                f"BPMN '{process_id}': отсутствует начальное событие (startEvent)."
            )
        if not has_end:
            result.add_error(
                f"BPMN '{process_id}': отсутствует конечное событие (endEvent)."
            )

        # Проверка парности шлюзов
        if len(diverging_gateways) != len(converging_gateways):
            result.add_warning(
                f"BPMN '{process_id}': количество разделяющих шлюзов "
                f"({len(diverging_gateways)}) не совпадает с количеством "
                f"объединяющих ({len(converging_gateways)}). "
                "Рекомендуется парное использование шлюзов."
            )

        # --- Flows ---
        flows = data.get("flows")
        if flows is None:
            result.add_error(
                f"BPMN '{process_id}': отсутствует обязательное поле 'flows'."
            )
        elif not isinstance(flows, list):
            result.add_error(
                f"BPMN '{process_id}': поле 'flows' должно быть списком."
            )
        elif len(flows) == 0:
            result.add_error(
                f"BPMN '{process_id}': список потоков (flows) пуст."
            )
        else:
            connected_elements: set[str] = set()
            for i, flow in enumerate(flows):
                if not isinstance(flow, dict):
                    result.add_error(
                        f"BPMN '{process_id}': поток #{i + 1} должен быть словарём."
                    )
                    continue

                source = flow.get("source")
                target = flow.get("target")

                if not source or not isinstance(source, str):
                    result.add_error(
                        f"BPMN '{process_id}': поток #{i + 1} не имеет "
                        "корректного поля 'source'."
                    )
                elif source not in element_ids:
                    result.add_error(
                        f"BPMN '{process_id}': поток #{i + 1} ссылается "
                        f"на несуществующий source '{source}'."
                    )
                else:
                    connected_elements.add(source)

                if not target or not isinstance(target, str):
                    result.add_error(
                        f"BPMN '{process_id}': поток #{i + 1} не имеет "
                        "корректного поля 'target'."
                    )
                elif target not in element_ids:
                    result.add_error(
                        f"BPMN '{process_id}': поток #{i + 1} ссылается "
                        f"на несуществующий target '{target}'."
                    )
                else:
                    connected_elements.add(target)

            # Проверяем «висящие» элементы
            disconnected = element_ids - connected_elements
            if disconnected:
                result.add_warning(
                    f"BPMN '{process_id}': элементы без связей: "
                    f"{', '.join(sorted(disconnected))}. "
                    "Все элементы должны быть соединены потоками."
                )

        # --- Lanes (необязательно, но проверяем если есть) ---
        lanes = data.get("lanes")
        if lanes is not None and isinstance(lanes, list):
            lane_element_refs: set[str] = set()
            for lane in lanes:
                if isinstance(lane, dict):
                    refs = lane.get("element_refs", [])
                    if isinstance(refs, list):
                        lane_element_refs.update(refs)

            # Элементы типа task должны быть назначены lane
            for elem in elements:
                if isinstance(elem, dict) and elem.get("type") == "task":
                    eid = elem.get("id")
                    if eid and eid not in lane_element_refs:
                        result.add_warning(
                            f"BPMN '{process_id}': задача '{eid}' не назначена "
                            "ни одной дорожке (lane)."
                        )

        logger.debug(
            "Валидация BPMN '%s': valid=%s, ошибок=%d, предупреждений=%d",
            process_id,
            result.valid,
            len(result.errors),
            len(result.warnings),
        )
        return result

    # ------------------------------------------------------------------
    # Валидация GAP-анализа
    # ------------------------------------------------------------------

    def validate_gap_analysis(self, data: dict) -> ValidationResult:
        """Валидирует структуру GAP-анализа.

        Проверяет:
        - Обязательные поля: process_id, config_name, coverage_summary, step_analysis.
        - Корректность coverage_summary (числа, процент).
        - Корректность step_analysis (coverage, priority).
        - Согласованность данных coverage_summary с step_analysis.

        Args:
            data: Словарь с данными GAP-анализа.

        Returns:
            ValidationResult с ошибками и предупреждениями.
        """
        result = ValidationResult()

        if not isinstance(data, dict):
            result.add_error("GAP-анализ должен быть словарём (dict).")
            return result

        # --- Обязательные поля ---
        self._check_required_str(data, "process_id", "GAP-анализ", result)
        self._check_required_str(data, "config_name", "GAP-анализ", result)

        process_id = data.get("process_id", "<без id>")

        # --- coverage_summary ---
        summary = data.get("coverage_summary")
        if summary is None:
            result.add_error(
                f"GAP-анализ '{process_id}': отсутствует обязательное поле "
                "'coverage_summary'."
            )
        elif not isinstance(summary, dict):
            result.add_error(
                f"GAP-анализ '{process_id}': поле 'coverage_summary' "
                "должно быть словарём."
            )
        else:
            for num_field in (
                "total_steps",
                "full_coverage",
                "partial_coverage",
                "custom_required",
                "absent",
            ):
                val = summary.get(num_field)
                if val is not None and not isinstance(val, (int, float)):
                    result.add_error(
                        f"GAP-анализ '{process_id}': поле "
                        f"'coverage_summary.{num_field}' должно быть числом, "
                        f"получено: {type(val).__name__}."
                    )

            coverage_pct = summary.get("coverage_percent")
            if coverage_pct is not None:
                if not isinstance(coverage_pct, (int, float)):
                    result.add_error(
                        f"GAP-анализ '{process_id}': поле "
                        "'coverage_summary.coverage_percent' должно быть числом."
                    )
                elif not (0 <= coverage_pct <= 100):
                    result.add_warning(
                        f"GAP-анализ '{process_id}': процент покрытия "
                        f"({coverage_pct}) вне диапазона 0-100."
                    )

            # Согласованность: сумма категорий == total_steps
            total = summary.get("total_steps")
            if isinstance(total, (int, float)):
                parts_sum = sum(
                    summary.get(f, 0)
                    for f in (
                        "full_coverage",
                        "partial_coverage",
                        "custom_required",
                        "absent",
                    )
                    if isinstance(summary.get(f), (int, float))
                )
                if parts_sum != total:
                    result.add_warning(
                        f"GAP-анализ '{process_id}': сумма категорий покрытия "
                        f"({parts_sum}) не совпадает с total_steps ({total})."
                    )

        # --- step_analysis ---
        steps = data.get("step_analysis")
        if steps is None:
            result.add_error(
                f"GAP-анализ '{process_id}': отсутствует обязательное поле "
                "'step_analysis'."
            )
        elif not isinstance(steps, list):
            result.add_error(
                f"GAP-анализ '{process_id}': поле 'step_analysis' "
                "должно быть списком."
            )
        else:
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    result.add_error(
                        f"GAP-анализ '{process_id}': элемент step_analysis "
                        f"#{i + 1} должен быть словарём."
                    )
                    continue

                coverage = step.get("coverage")
                if coverage and coverage not in _VALID_COVERAGE_TYPES:
                    result.add_error(
                        f"GAP-анализ '{process_id}': шаг #{i + 1} имеет "
                        f"некорректный тип покрытия '{coverage}'. "
                        f"Допустимые: {', '.join(sorted(_VALID_COVERAGE_TYPES))}."
                    )

                priority = step.get("priority")
                if priority and priority not in _VALID_PRIORITIES:
                    result.add_warning(
                        f"GAP-анализ '{process_id}': шаг #{i + 1} имеет "
                        f"нестандартный приоритет '{priority}'. "
                        f"Рекомендуемые: {', '.join(sorted(_VALID_PRIORITIES))}."
                    )

        # --- mandatory_customizations ---
        customizations = data.get("mandatory_customizations")
        if customizations is not None and isinstance(customizations, list):
            for i, cust in enumerate(customizations):
                if isinstance(cust, dict):
                    priority = cust.get("priority")
                    if priority and priority not in _VALID_PRIORITIES:
                        result.add_warning(
                            f"GAP-анализ '{process_id}': доработка #{i + 1} "
                            f"имеет нестандартный приоритет '{priority}'."
                        )
                    effort = cust.get("effort_hours")
                    if effort is not None and (
                        not isinstance(effort, (int, float)) or effort < 0
                    ):
                        result.add_warning(
                            f"GAP-анализ '{process_id}': доработка #{i + 1} "
                            f"имеет некорректную трудоёмкость: {effort}."
                        )

        logger.debug(
            "Валидация GAP-анализа '%s': valid=%s, ошибок=%d, предупреждений=%d",
            process_id,
            result.valid,
            len(result.errors),
            len(result.warnings),
        )
        return result

    # ------------------------------------------------------------------
    # Валидация листа требований
    # ------------------------------------------------------------------

    def validate_requirements(self, data: dict) -> ValidationResult:
        """Валидирует структуру листа требований.

        Проверяет:
        - Обязательные поля: requirements (список).
        - Для каждого требования: id, name, type, priority.
        - Формат id (FR-XXX, NFR-XXX, IR-XXX).
        - Уникальность id.
        - Корректность зависимостей (ссылки на существующие id).

        Args:
            data: Словарь с листом требований.

        Returns:
            ValidationResult с ошибками и предупреждениями.
        """
        result = ValidationResult()

        if not isinstance(data, dict):
            result.add_error("Лист требований должен быть словарём (dict).")
            return result

        # --- requirements ---
        requirements = data.get("requirements")
        if requirements is None:
            result.add_error(
                "Лист требований: отсутствует обязательное поле 'requirements'."
            )
            return result

        if not isinstance(requirements, list):
            result.add_error(
                "Лист требований: поле 'requirements' должно быть списком."
            )
            return result

        if len(requirements) == 0:
            result.add_warning(
                "Лист требований: список требований пуст."
            )
            return result

        # Первый проход: собираем все id
        req_ids: set[str] = set()
        id_pattern = re.compile(r"^(FR|NFR|IR)-\d{3}$")

        for i, req in enumerate(requirements):
            if not isinstance(req, dict):
                result.add_error(
                    f"Лист требований: элемент #{i + 1} должен быть словарём."
                )
                continue

            req_id = req.get("id")
            if not req_id or not isinstance(req_id, str):
                result.add_error(
                    f"Лист требований: требование #{i + 1} не имеет "
                    "корректного поля 'id'."
                )
                continue

            if not id_pattern.match(req_id):
                result.add_warning(
                    f"Лист требований: id '{req_id}' не соответствует "
                    "формату (FR-XXX, NFR-XXX, IR-XXX)."
                )

            if req_id in req_ids:
                result.add_error(
                    f"Лист требований: дублирующийся id '{req_id}'."
                )
            req_ids.add(req_id)

            # Обязательные строковые поля
            if not req.get("name") or not isinstance(req.get("name"), str):
                result.add_error(
                    f"Требование '{req_id}': отсутствует или некорректно "
                    "поле 'name'."
                )

            # Тип требования
            req_type = req.get("type")
            if req_type and req_type not in _VALID_REQUIREMENT_TYPES:
                result.add_error(
                    f"Требование '{req_id}': некорректный тип '{req_type}'. "
                    f"Допустимые: {', '.join(sorted(_VALID_REQUIREMENT_TYPES))}."
                )

            # Приоритет
            priority = req.get("priority")
            if priority and priority not in _VALID_PRIORITIES:
                result.add_warning(
                    f"Требование '{req_id}': нестандартный приоритет "
                    f"'{priority}'. "
                    f"Рекомендуемые: {', '.join(sorted(_VALID_PRIORITIES))}."
                )

            # Трудоёмкость
            effort = req.get("effort_hours")
            if effort is not None:
                if not isinstance(effort, (int, float)) or effort < 0:
                    result.add_warning(
                        f"Требование '{req_id}': некорректная трудоёмкость "
                        f"({effort}). Ожидается неотрицательное число."
                    )

            # Критерии приёмки
            criteria = req.get("acceptance_criteria")
            if criteria is not None and not isinstance(criteria, list):
                result.add_warning(
                    f"Требование '{req_id}': поле 'acceptance_criteria' "
                    "должно быть списком."
                )
            elif criteria is not None and len(criteria) == 0:
                result.add_warning(
                    f"Требование '{req_id}': список критериев приёмки пуст. "
                    "Каждое требование должно быть тестируемым."
                )

        # Второй проход: проверяем зависимости
        for req in requirements:
            if not isinstance(req, dict):
                continue
            req_id = req.get("id", "")
            deps = req.get("dependencies")
            if deps and isinstance(deps, list):
                for dep in deps:
                    if isinstance(dep, str) and dep not in req_ids:
                        result.add_warning(
                            f"Требование '{req_id}': зависимость '{dep}' "
                            "ссылается на несуществующее требование."
                        )

        # --- summary (если есть) ---
        summary = data.get("summary")
        if summary is not None and isinstance(summary, dict):
            for req_type_key in ("FR", "NFR", "IR"):
                type_summary = summary.get(req_type_key)
                if type_summary and isinstance(type_summary, dict):
                    for prio in type_summary:
                        if prio not in _VALID_PRIORITIES:
                            result.add_warning(
                                f"Лист требований: в сводке для '{req_type_key}' "
                                f"указан нестандартный приоритет '{prio}'."
                            )

        logger.debug(
            "Валидация требований: valid=%s, ошибок=%d, предупреждений=%d, "
            "всего требований=%d",
            result.valid,
            len(result.errors),
            len(result.warnings),
            len(requirements),
        )
        return result

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _check_required_str(
        data: dict,
        field: str,
        context: str,
        result: ValidationResult,
    ) -> None:
        """Проверяет наличие и тип обязательного строкового поля."""
        value = data.get(field)
        if value is None:
            result.add_error(
                f"{context}: отсутствует обязательное поле '{field}'."
            )
        elif not isinstance(value, str):
            result.add_error(
                f"{context}: поле '{field}' должно быть строкой, "
                f"получено: {type(value).__name__}."
            )
        elif not value.strip():
            result.add_error(
                f"{context}: поле '{field}' не должно быть пустым."
            )

    def _validate_steps(
        self, steps: list, process_id: str
    ) -> ValidationResult:
        """Валидирует список шагов процесса."""
        result = ValidationResult()
        orders_seen: list[int] = []

        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                result.add_error(
                    f"Процесс '{process_id}': шаг #{i + 1} должен быть словарём."
                )
                continue

            # order
            order = step.get("order")
            if order is None:
                result.add_warning(
                    f"Процесс '{process_id}': шаг #{i + 1} не имеет "
                    "порядкового номера (order)."
                )
            elif not isinstance(order, int):
                result.add_error(
                    f"Процесс '{process_id}': шаг #{i + 1} -- 'order' "
                    f"должен быть целым числом, получено: {type(order).__name__}."
                )
            else:
                if order in orders_seen:
                    result.add_warning(
                        f"Процесс '{process_id}': дублирующийся порядковый "
                        f"номер шага: {order}."
                    )
                orders_seen.append(order)

            # name
            name = step.get("name")
            if not name or not isinstance(name, str):
                result.add_error(
                    f"Процесс '{process_id}': шаг #{i + 1} не имеет "
                    "корректного поля 'name'."
                )

            # performer
            performer = step.get("performer")
            if not performer or not isinstance(performer, str):
                result.add_warning(
                    f"Процесс '{process_id}': шаг #{i + 1} "
                    f"('{name or '?'}') не имеет указанного исполнителя."
                )

            # inputs/outputs/systems (списки)
            for list_field in ("inputs", "outputs", "systems"):
                val = step.get(list_field)
                if val is not None and not isinstance(val, list):
                    result.add_warning(
                        f"Процесс '{process_id}': шаг #{i + 1} -- "
                        f"поле '{list_field}' должно быть списком."
                    )

        # Проверяем последовательность order
        if orders_seen and len(orders_seen) > 1:
            if orders_seen != sorted(orders_seen):
                result.add_warning(
                    f"Процесс '{process_id}': шаги идут не в порядке "
                    "возрастания номеров (order)."
                )

        return result

    @staticmethod
    def _validate_decision(
        decision: Any, process_id: str, index: int
    ) -> ValidationResult:
        """Валидирует точку принятия решения."""
        result = ValidationResult()

        if not isinstance(decision, dict):
            result.add_error(
                f"Процесс '{process_id}': решение #{index} "
                "должно быть словарём."
            )
            return result

        for field in ("condition", "yes_branch", "no_branch"):
            val = decision.get(field)
            if not val or not isinstance(val, str):
                result.add_error(
                    f"Процесс '{process_id}': решение #{index} -- "
                    f"отсутствует или некорректно поле '{field}'."
                )

        return result

    @staticmethod
    def _validate_pain_point(
        pain_point: Any, process_id: str, index: int
    ) -> ValidationResult:
        """Валидирует болевую точку."""
        result = ValidationResult()

        if not isinstance(pain_point, dict):
            result.add_error(
                f"Процесс '{process_id}': болевая точка #{index} "
                "должна быть словарём."
            )
            return result

        # description
        desc = pain_point.get("description")
        if not desc or not isinstance(desc, str):
            result.add_error(
                f"Процесс '{process_id}': болевая точка #{index} -- "
                "отсутствует или некорректно поле 'description'."
            )

        # severity
        severity = pain_point.get("severity")
        if severity and severity not in _VALID_SEVERITIES:
            result.add_error(
                f"Процесс '{process_id}': болевая точка #{index} -- "
                f"некорректная серьёзность '{severity}'. "
                f"Допустимые: {', '.join(sorted(_VALID_SEVERITIES))}."
            )

        # category
        category = pain_point.get("category")
        if category and category not in _VALID_PAIN_CATEGORIES:
            result.add_error(
                f"Процесс '{process_id}': болевая точка #{index} -- "
                f"некорректная категория '{category}'. "
                f"Допустимые: {', '.join(sorted(_VALID_PAIN_CATEGORIES))}."
            )

        return result
