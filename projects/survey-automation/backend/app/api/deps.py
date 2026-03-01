"""Зависимости для API endpoints.

Фабричные функции для внедрения зависимостей через FastAPI Depends().
Каждая функция создаёт экземпляр соответствующего сервиса.
"""

from __future__ import annotations

from app.services.project_service import ProjectService
from app.services.transcription_service import TranscriptionService
from app.services.analysis_service import AnalysisService
from app.services.bpmn_service import BPMNService
from app.services.export_service import ExportService
from app.services.pipeline_service import PipelineService


def get_project_service() -> ProjectService:
    """Создаёт экземпляр сервиса управления проектами."""
    return ProjectService()


def get_transcription_service() -> TranscriptionService:
    """Создаёт экземпляр сервиса транскрипции."""
    return TranscriptionService()


def get_analysis_service() -> AnalysisService:
    """Создаёт экземпляр сервиса анализа процессов."""
    return AnalysisService()


def get_bpmn_service() -> BPMNService:
    """Создаёт экземпляр сервиса генерации BPMN."""
    return BPMNService()


def get_export_service() -> ExportService:
    """Создаёт экземпляр сервиса экспорта документов."""
    return ExportService()


def get_pipeline_service() -> PipelineService:
    """Создаёт экземпляр сервиса управления пайплайном."""
    return PipelineService()
