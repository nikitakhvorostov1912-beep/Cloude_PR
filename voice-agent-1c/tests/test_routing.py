"""Тесты дерева маршрутизации обращений."""
from __future__ import annotations

import pytest

from models.task import ClientInfo, Department, Priority, Product, TaskType
from orchestrator.call_handler import CallHandler


@pytest.fixture
def handler():
    return CallHandler(onec_client=None)


@pytest.fixture
def client_with_specialist():
    return ClientInfo(
        id="001",
        name="ООО Ромашка",
        product="КА",
        contract_status="active",
        assigned_specialist="Иванов Иван",
        sla_level="standard",
    )


@pytest.fixture
def client_no_specialist():
    return ClientInfo(
        id="002",
        name="ИП Петров",
        product="БП",
        contract_status="active",
        assigned_specialist=None,
        sla_level="standard",
    )


# --- Новый клиент ---


class TestNewClientRouting:
    def test_new_client_goes_to_presale(self, handler):
        """Новый клиент -> Пресейл."""
        result = handler.route(None, TaskType.ERROR, Product.BP)
        assert result.department == Department.PRESALE

    def test_new_client_any_task_type(self, handler):
        """Новый клиент всегда -> Пресейл, независимо от типа."""
        for task_type in TaskType:
            result = handler.route(None, task_type, Product.BP)
            assert result.department == Department.PRESALE


# --- Ошибки ---


class TestErrorRouting:
    def test_error_standard_with_specialist(self, handler, client_with_specialist):
        """Ошибка + типовой + специалист -> Специалист."""
        result = handler.route(client_with_specialist, TaskType.ERROR, Product.KA)
        assert result.department == Department.SPECIALIST

    def test_error_standard_no_specialist(self, handler, client_no_specialist):
        """Ошибка + типовой + нет специалиста -> Поддержка."""
        result = handler.route(client_no_specialist, TaskType.ERROR, Product.BP)
        assert result.department == Department.SUPPORT

    def test_error_erp(self, handler, client_no_specialist):
        """Ошибка ERP -> Внедрение + HIGH."""
        result = handler.route(client_no_specialist, TaskType.ERROR, Product.ERP)
        assert result.department == Department.IMPLEMENTATION
        assert result.priority == Priority.HIGH

    def test_error_custom(self, handler, client_no_specialist):
        """Ошибка кастомного кода -> Разработка."""
        result = handler.route(client_no_specialist, TaskType.ERROR, Product.CUSTOM)
        assert result.department == Department.DEVELOPMENT


# --- Консультации ---


class TestConsultRouting:
    def test_consult_standard(self, handler, client_no_specialist):
        """Консультация типового -> Поддержка."""
        result = handler.route(client_no_specialist, TaskType.CONSULT, Product.BP)
        assert result.department == Department.SUPPORT

    def test_consult_erp(self, handler, client_no_specialist):
        """Консультация ERP -> Внедрение."""
        result = handler.route(client_no_specialist, TaskType.CONSULT, Product.ERP)
        assert result.department == Department.IMPLEMENTATION

    def test_consult_with_specialist(self, handler, client_with_specialist):
        """Консультация + специалист -> Специалист."""
        result = handler.route(client_with_specialist, TaskType.CONSULT, Product.KA)
        assert result.department == Department.SPECIALIST


# --- Доработки и проекты ---


class TestOtherRouting:
    def test_feature_goes_to_development(self, handler, client_no_specialist):
        """Доработка -> Разработка."""
        result = handler.route(client_no_specialist, TaskType.FEATURE, Product.BP)
        assert result.department == Department.DEVELOPMENT

    def test_project_goes_to_implementation(self, handler, client_no_specialist):
        """Крупный проект -> Внедрение."""
        result = handler.route(client_no_specialist, TaskType.PROJECT, Product.ERP)
        assert result.department == Department.IMPLEMENTATION

    def test_update_standard_goes_to_support(self, handler, client_no_specialist):
        """Типовое обновление -> Поддержка."""
        result = handler.route(client_no_specialist, TaskType.UPDATE, Product.BP)
        assert result.department == Department.SUPPORT

    def test_update_custom_goes_to_development(self, handler, client_no_specialist):
        """Обновление с доработками -> Разработка."""
        result = handler.route(client_no_specialist, TaskType.UPDATE, Product.CUSTOM)
        assert result.department == Department.DEVELOPMENT
