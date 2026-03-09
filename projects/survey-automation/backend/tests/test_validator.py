"""Тесты: валидация данных процессов, BPMN JSON, GAP-анализа и требований."""
import pytest

from app.analysis.validator import ProcessValidator, ValidationResult


@pytest.fixture
def validator():
    """Create a ProcessValidator instance."""
    return ProcessValidator()


# -------------------------------------------------------------------
# validate_process
# -------------------------------------------------------------------


def test_validate_valid_process(validator, sample_processes):
    """Valid process from sample data passes validation."""
    process = sample_processes["processes"][0]
    result = validator.validate_process(process)
    assert result.valid


def test_validate_process_missing_name(validator):
    """Process without 'name' field is invalid."""
    process = {"id": "test_proc", "steps": []}
    result = validator.validate_process(process)
    assert not result.valid
    assert len(result.errors) > 0


def test_validate_process_missing_id(validator):
    """Process without 'id' field is invalid."""
    process = {"name": "Тест", "steps": []}
    result = validator.validate_process(process)
    assert not result.valid


def test_validate_process_empty_steps(validator):
    """Process with empty steps list gets a warning."""
    process = {"id": "test_proc", "name": "Тест", "steps": []}
    result = validator.validate_process(process)
    # Empty steps should produce a warning
    assert len(result.warnings) > 0


def test_validate_process_no_steps_field(validator):
    """Process without steps field at all gets a warning."""
    process = {"id": "test_proc", "name": "Тест"}
    result = validator.validate_process(process)
    assert len(result.warnings) > 0


def test_validate_process_not_dict(validator):
    """Non-dict input is invalid."""
    result = validator.validate_process("not a dict")
    assert not result.valid
    assert len(result.errors) > 0


def test_validate_process_with_decisions(validator):
    """Process with well-formed decisions passes validation."""
    process = {
        "id": "proc_test",
        "name": "Тестовый процесс",
        "steps": [
            {"order": 1, "name": "Шаг 1", "performer": "Менеджер"},
        ],
        "decisions": [
            {
                "condition": "Условие",
                "yes_branch": "Да",
                "no_branch": "Нет",
            }
        ],
    }
    result = validator.validate_process(process)
    assert result.valid


def test_validate_process_invalid_decision(validator):
    """Decision missing required fields produces errors."""
    process = {
        "id": "proc_test",
        "name": "Тестовый процесс",
        "steps": [{"order": 1, "name": "Шаг 1", "performer": "Менеджер"}],
        "decisions": [{"condition": "Условие"}],  # missing yes_branch, no_branch
    }
    result = validator.validate_process(process)
    assert not result.valid


def test_validate_all_sample_processes(validator, sample_processes):
    """All processes from sample data pass validation."""
    for process in sample_processes["processes"]:
        result = validator.validate_process(process)
        assert result.valid, (
            f"Process '{process.get('id')}' failed validation: {result.errors}"
        )


# -------------------------------------------------------------------
# validate_bpmn_json
# -------------------------------------------------------------------


def test_validate_bpmn_json_valid(validator):
    """Valid minimal BPMN JSON passes validation."""
    bpmn_json = {
        "process_id": "test_proc",
        "process_name": "Тест",
        "elements": [
            {"id": "start_1", "type": "startEvent", "name": "Начало"},
            {"id": "task_1", "type": "task", "name": "Задача"},
            {"id": "end_1", "type": "endEvent", "name": "Конец"},
        ],
        "flows": [
            {"id": "flow_1", "source": "start_1", "target": "task_1"},
            {"id": "flow_2", "source": "task_1", "target": "end_1"},
        ],
    }
    result = validator.validate_bpmn_json(bpmn_json)
    assert result.valid


def test_validate_bpmn_json_missing_start_event(validator):
    """BPMN JSON without startEvent is invalid."""
    bpmn_json = {
        "process_id": "test_proc",
        "process_name": "Тест",
        "elements": [
            {"id": "task_1", "type": "task", "name": "Задача"},
            {"id": "end_1", "type": "endEvent", "name": "Конец"},
        ],
        "flows": [
            {"id": "flow_1", "source": "task_1", "target": "end_1"},
        ],
    }
    result = validator.validate_bpmn_json(bpmn_json)
    assert not result.valid


def test_validate_bpmn_json_missing_end_event(validator):
    """BPMN JSON without endEvent is invalid."""
    bpmn_json = {
        "process_id": "test_proc",
        "process_name": "Тест",
        "elements": [
            {"id": "start_1", "type": "startEvent", "name": "Начало"},
            {"id": "task_1", "type": "task", "name": "Задача"},
        ],
        "flows": [
            {"id": "flow_1", "source": "start_1", "target": "task_1"},
        ],
    }
    result = validator.validate_bpmn_json(bpmn_json)
    assert not result.valid


def test_validate_bpmn_json_empty_elements(validator):
    """BPMN JSON with empty elements list is invalid."""
    bpmn_json = {
        "process_id": "test_proc",
        "process_name": "Тест",
        "elements": [],
        "flows": [],
    }
    result = validator.validate_bpmn_json(bpmn_json)
    assert not result.valid


def test_validate_bpmn_json_invalid_flow_reference(validator):
    """BPMN JSON with flow referencing nonexistent element is invalid."""
    bpmn_json = {
        "process_id": "test_proc",
        "process_name": "Тест",
        "elements": [
            {"id": "start_1", "type": "startEvent", "name": "Начало"},
            {"id": "end_1", "type": "endEvent", "name": "Конец"},
        ],
        "flows": [
            {"id": "flow_1", "source": "start_1", "target": "nonexistent"},
        ],
    }
    result = validator.validate_bpmn_json(bpmn_json)
    assert not result.valid


# -------------------------------------------------------------------
# validate_gap_analysis
# -------------------------------------------------------------------


def test_validate_gap_analysis_valid(validator):
    """Valid GAP analysis data passes validation."""
    data = {
        "process_id": "proc_001",
        "config_name": "1С:ERP",
        "coverage_summary": {
            "total_steps": 5,
            "full_coverage": 3,
            "partial_coverage": 1,
            "custom_required": 1,
            "absent": 0,
            "coverage_percent": 80.0,
        },
        "step_analysis": [
            {"step_name": "Шаг 1", "coverage": "full", "priority": "Must"},
            {"step_name": "Шаг 2", "coverage": "partial", "priority": "Should"},
        ],
    }
    result = validator.validate_gap_analysis(data)
    assert result.valid


def test_validate_gap_analysis_missing_required(validator):
    """GAP analysis missing required fields is invalid."""
    data = {}
    result = validator.validate_gap_analysis(data)
    assert not result.valid


# -------------------------------------------------------------------
# validate_requirements
# -------------------------------------------------------------------


def test_validate_requirements_valid(validator):
    """Valid requirements list passes validation."""
    data = {
        "requirements": [
            {
                "id": "FR-001",
                "name": "Регистрация заказа",
                "type": "FR",
                "priority": "Must",
                "description": "Система должна позволять...",
            },
            {
                "id": "NFR-001",
                "name": "Производительность",
                "type": "NFR",
                "priority": "Should",
                "description": "Время ответа...",
            },
        ]
    }
    result = validator.validate_requirements(data)
    assert result.valid


def test_validate_requirements_empty_list(validator):
    """Empty requirements list produces a warning."""
    data = {"requirements": []}
    result = validator.validate_requirements(data)
    assert len(result.warnings) > 0


def test_validate_requirements_missing_field(validator):
    """Requirements without 'requirements' field is invalid."""
    data = {}
    result = validator.validate_requirements(data)
    assert not result.valid


# -------------------------------------------------------------------
# ValidationResult
# -------------------------------------------------------------------


def test_validation_result_add_error():
    """add_error marks result as invalid."""
    result = ValidationResult()
    assert result.valid
    result.add_error("Ошибка")
    assert not result.valid
    assert len(result.errors) == 1


def test_validation_result_add_warning():
    """add_warning does not change valid flag."""
    result = ValidationResult()
    result.add_warning("Предупреждение")
    assert result.valid
    assert len(result.warnings) == 1


def test_validation_result_merge():
    """merge combines errors and warnings from both results."""
    result1 = ValidationResult()
    result1.add_warning("Предупреждение 1")

    result2 = ValidationResult()
    result2.add_error("Ошибка 1")

    result1.merge(result2)
    assert not result1.valid
    assert len(result1.errors) == 1
    assert len(result1.warnings) == 1
