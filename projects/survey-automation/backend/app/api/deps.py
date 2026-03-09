"""Зависимости для API endpoints.

Фабричные функции для внедрения зависимостей через FastAPI Depends().
Каждая функция создаёт экземпляр соответствующего сервиса.
"""

from __future__ import annotations

from app.services.export_service import ExportService
from app.services.pipeline_service import PipelineService
from app.services.project_service import ProjectService


def get_project_service() -> ProjectService:
    """Создаёт экземпляр сервиса управления проектами."""
    return ProjectService()


def get_export_service() -> ExportService:
    """Создаёт экземпляр сервиса экспорта документов."""
    return ExportService()


def get_pipeline_service() -> PipelineService:
    """Создаёт экземпляр сервиса управления пайплайном."""
    return PipelineService()
