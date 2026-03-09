"""Tests for Pydantic domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.api.task import (
    ClassificationResult,
    Department,
    Priority,
    Product,
    RoutingResult,
    TaskCreate,
    TaskType,
)
from models.api.call import CallEventType, MangoCallEvent
from models.api.client import ClientContext


class TestEnums:
    def test_department_values(self) -> None:
        assert Department.SUPPORT == "support"
        assert Department.DEVELOPMENT == "development"

    def test_product_values(self) -> None:
        assert Product.BP == "БП"
        assert Product.ZUP == "ЗУП"

    def test_task_type_values(self) -> None:
        assert TaskType.ERROR == "error"
        assert TaskType.CONSULT == "consult"

    def test_priority_values(self) -> None:
        assert Priority.CRITICAL == "critical"
        assert Priority.LOW == "low"


class TestClassificationResult:
    def test_valid_classification(self) -> None:
        result = ClassificationResult(
            department=Department.SUPPORT,
            department_confidence=0.92,
            department_reason="Test",
            task_type=TaskType.ERROR,
            task_type_confidence=0.85,
            priority=Priority.HIGH,
            priority_confidence=0.80,
            priority_reason="Test",
            description="Test description",
            summary="Test summary",
        )
        assert result.department == Department.SUPPORT
        assert result.department_confidence == 0.92

    def test_frozen_model(self) -> None:
        result = ClassificationResult(
            department=Department.SUPPORT,
            department_confidence=0.92,
            department_reason="Test",
            task_type=TaskType.ERROR,
            task_type_confidence=0.85,
            priority=Priority.HIGH,
            priority_confidence=0.80,
            priority_reason="Test",
            description="Test",
            summary="Test",
        )
        with pytest.raises(ValidationError):
            result.department = Department.DEVELOPMENT  # type: ignore[misc]

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ClassificationResult(
                department=Department.SUPPORT,
                department_confidence=1.5,  # > 1.0
                department_reason="Test",
                task_type=TaskType.ERROR,
                task_type_confidence=0.85,
                priority=Priority.HIGH,
                priority_confidence=0.80,
                priority_reason="Test",
                description="Test",
                summary="Test",
            )


class TestMangoCallEvent:
    def test_valid_event(self) -> None:
        event = MangoCallEvent(
            call_id="test-call-001",
            **{"from": "+74951234567"},
            to="+74957654321",
            event_type=CallEventType.INCOMING,
        )
        assert event.call_id == "test-call-001"
        assert event.from_number == "+74951234567"

    def test_from_alias(self) -> None:
        """Test that 'from' field is aliased to 'from_number'."""
        event = MangoCallEvent(
            call_id="test",
            **{"from": "+71111111111"},
            to="+72222222222",
            event_type=CallEventType.INCOMING,
        )
        assert event.from_number == "+71111111111"


class TestClientContext:
    def test_default_not_found(self) -> None:
        ctx = ClientContext(found=False, name="")
        assert not ctx.found
        assert ctx.recent_tasks == []

    def test_full_context(self) -> None:
        ctx = ClientContext(
            found=True,
            name="ООО Ромашка",
            sakura_id="SAK-001",
            onec_id="1C-001",
            product="БП",
        )
        assert ctx.found
        assert ctx.name == "ООО Ромашка"
