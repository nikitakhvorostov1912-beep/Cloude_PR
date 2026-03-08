"""Tests for deterministic routing rules."""

from __future__ import annotations

import pytest

from agents.classifier.routing_rules import apply_deterministic_rules
from models.api.task import Department, Priority, TaskType


class TestDeterministicRouting:
    """Test keyword-based routing rules."""

    def test_error_keywords_route_to_support(self) -> None:
        result = apply_deterministic_rules(
            "У нас ошибка при формировании отчёта, программа не работает"
        )
        assert result is not None
        assert result.department == Department.SUPPORT
        assert result.task_type == TaskType.ERROR
        assert result.confidence >= 0.70

    def test_consult_keywords_route_to_support(self) -> None:
        result = apply_deterministic_rules(
            "Подскажите, как сделать отчёт по зарплате"
        )
        assert result is not None
        assert result.department == Department.SUPPORT
        assert result.task_type == TaskType.CONSULT

    def test_feature_keywords_route_to_development(self) -> None:
        result = apply_deterministic_rules(
            "Нам нужно доработать печатную форму и автоматизировать процесс"
        )
        assert result is not None
        assert result.department == Department.DEVELOPMENT
        assert result.task_type == TaskType.FEATURE

    def test_update_keywords_route_to_implementation(self) -> None:
        result = apply_deterministic_rules(
            "Хотим обновить конфигурацию и перейти на новую версию платформы"
        )
        assert result is not None
        assert result.department == Department.IMPLEMENTATION
        assert result.task_type == TaskType.UPDATE

    def test_project_keywords_route_to_implementation(self) -> None:
        result = apply_deterministic_rules(
            "Планируем внедрение ERP и перенос данных из старой базы"
        )
        assert result is not None
        assert result.department == Department.IMPLEMENTATION
        assert result.task_type == TaskType.PROJECT

    def test_presale_keywords_route_to_presale(self) -> None:
        result = apply_deterministic_rules(
            "Сколько стоит лицензия на 1С Бухгалтерию?"
        )
        assert result is not None
        assert result.department == Department.PRESALE

    def test_specialist_request(self) -> None:
        result = apply_deterministic_rules(
            "Свяжите меня с моим менеджером, пожалуйста"
        )
        assert result is not None
        assert result.department == Department.SPECIALIST

    def test_escalation_request(self) -> None:
        result = apply_deterministic_rules(
            "Переведите на оператора, хочу поговорить с человеком"
        )
        assert result is not None
        assert result.rule == "escalation_request"
        assert result.confidence >= 0.90

    def test_critical_priority_detected(self) -> None:
        result = apply_deterministic_rules(
            "Ошибка! Не могу работать, бухгалтерия стоит, всё стоит!"
        )
        assert result is not None
        assert result.priority == Priority.CRITICAL

    def test_high_priority_detected(self) -> None:
        result = apply_deterministic_rules(
            "Срочно, ошибка в программе, мешает работать"
        )
        assert result is not None
        assert result.priority == Priority.HIGH

    def test_normal_priority_default(self) -> None:
        result = apply_deterministic_rules(
            "Не работает печать документов в бухгалтерии"
        )
        assert result is not None
        assert result.priority == Priority.NORMAL

    def test_ambiguous_returns_none(self) -> None:
        result = apply_deterministic_rules(
            "Добрый день, хотел бы обсудить один вопрос"
        )
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = apply_deterministic_rules("")
        assert result is None

    def test_confidence_threshold(self) -> None:
        result = apply_deterministic_rules(
            "Ошибка при проведении документа, программа вылетает и зависает"
        )
        assert result is not None
        assert result.confidence >= 0.70
        assert result.confidence <= 1.0
