"""Логика обработки входящих звонков.

Оркестрирует: идентификация клиента -> маршрутизация -> (Phase 2: AI).
Phase 1: идентификация клиента и дерево маршрутизации.
"""
from __future__ import annotations

import logging

from integrations.client_1c import OneCClient, OneCError
from models.task import (
    ClientInfo,
    Department,
    Priority,
    Product,
    RoutingResult,
    TaskType,
)

logger = logging.getLogger(__name__)

# Типовые продукты (не ERP, не кастомные)
STANDARD_PRODUCTS = {Product.BP, Product.KA, Product.ZUP, Product.UT, Product.RETAIL}


class CallHandler:
    """Обработчик входящих звонков."""

    def __init__(self, onec_client: OneCClient | None = None) -> None:
        self._onec = onec_client or OneCClient()

    async def identify_client(self, phone: str) -> ClientInfo | None:
        """Идентифицирует клиента по номеру телефона через 1С."""
        try:
            return await self._onec.get_client_by_phone(phone)
        except OneCError:
            logger.exception("Ошибка идентификации клиента: %s", phone)
            return None

    def route(
        self,
        client: ClientInfo | None,
        task_type: TaskType,
        product: Product,
    ) -> RoutingResult:
        """Маршрутизирует обращение по дереву правил из мастер-промпта."""
        # Новый клиент -> Пресейл
        if client is None:
            return RoutingResult(
                department=Department.PRESALE,
                priority=Priority.NORMAL,
                reason="Новый клиент -> Пресейл",
            )

        return self._route_existing_client(client, task_type, product)

    def _route_existing_client(
        self,
        client: ClientInfo,
        task_type: TaskType,
        product: Product,
    ) -> RoutingResult:
        """Маршрутизация для существующего клиента."""
        if task_type == TaskType.ERROR:
            return self._route_error(client, product)
        if task_type == TaskType.CONSULT:
            return self._route_consult(client, product)
        if task_type == TaskType.FEATURE:
            return RoutingResult(
                department=Department.DEVELOPMENT,
                priority=Priority.NORMAL,
                reason="Запрос на доработку -> Разработка",
            )
        if task_type == TaskType.UPDATE:
            return self._route_update(client, product)
        if task_type == TaskType.PROJECT:
            return RoutingResult(
                department=Department.IMPLEMENTATION,
                priority=Priority.NORMAL,
                reason="Крупный проект -> Внедрение",
            )

        # Fallback
        return RoutingResult(
            department=Department.SUPPORT,
            priority=Priority.NORMAL,
            reason="Не удалось классифицировать -> Поддержка (по умолчанию)",
        )

    def _route_error(self, client: ClientInfo, product: Product) -> RoutingResult:
        """Маршрутизация ошибок."""
        # ERP -> Внедрение, приоритет +1
        if product == Product.ERP:
            return RoutingResult(
                department=Department.IMPLEMENTATION,
                priority=Priority.HIGH,
                reason="Ошибка ERP -> Внедрение (приоритет +1)",
            )

        # Кастомный код -> Разработка
        if product == Product.CUSTOM:
            return RoutingResult(
                department=Department.DEVELOPMENT,
                priority=Priority.HIGH,
                reason="Ошибка кастомного кода -> Разработка",
            )

        # Типовой продукт + есть закреплённый специалист -> Специалист
        if product in STANDARD_PRODUCTS and client.assigned_specialist:
            return RoutingResult(
                department=Department.SPECIALIST,
                priority=Priority.NORMAL,
                reason=f"Ошибка типового продукта, специалист: {client.assigned_specialist}",
            )

        # Типовой продукт -> Поддержка
        return RoutingResult(
            department=Department.SUPPORT,
            priority=Priority.NORMAL,
            reason="Ошибка типового продукта -> Поддержка",
        )

    def _route_consult(self, client: ClientInfo, product: Product) -> RoutingResult:
        """Маршрутизация консультаций."""
        # ERP -> Внедрение
        if product == Product.ERP:
            return RoutingResult(
                department=Department.IMPLEMENTATION,
                priority=Priority.NORMAL,
                reason="Консультация ERP -> Внедрение",
            )

        # Кастом -> Разработка
        if product == Product.CUSTOM:
            return RoutingResult(
                department=Department.DEVELOPMENT,
                priority=Priority.NORMAL,
                reason="Консультация по кастомному коду -> Разработка",
            )

        # Типовой + специалист -> Специалист
        if product in STANDARD_PRODUCTS and client.assigned_specialist:
            return RoutingResult(
                department=Department.SPECIALIST,
                priority=Priority.NORMAL,
                reason=f"Консультация, специалист: {client.assigned_specialist}",
            )

        # Типовой -> Поддержка
        return RoutingResult(
            department=Department.SUPPORT,
            priority=Priority.NORMAL,
            reason="Консультация типового продукта -> Поддержка",
        )

    def _route_update(self, client: ClientInfo, product: Product) -> RoutingResult:
        """Маршрутизация обновлений."""
        # С доработками (кастом) -> Разработка
        if product == Product.CUSTOM:
            return RoutingResult(
                department=Department.DEVELOPMENT,
                priority=Priority.NORMAL,
                reason="Обновление с доработками -> Разработка",
            )

        # Типовое обновление -> Поддержка
        return RoutingResult(
            department=Department.SUPPORT,
            priority=Priority.NORMAL,
            reason="Типовое обновление -> Поддержка",
        )
