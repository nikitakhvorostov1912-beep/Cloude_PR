"""API маршруты: пайплайн обработки.

Эндпоинты для запуска отдельных этапов конвейера обработки:
транскрипция, извлечение процессов, генерация BPMN, GAP-анализ,
генерация TO-BE и документации. Длительные операции запускаются
в фоновых задачах через BackgroundTasks.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.deps import get_pipeline_service, get_project_service
from app.api.models import (
    ErpConfigRequest,
    ErrorResponse,
    MessageResponse,
    PipelineStatusResponse,
)
from app.exceptions import AppError
from app.services.pipeline_service import PipelineService
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/pipeline", tags=["pipeline"])


# ----------------------------------------------------------------------
# Вспомогательные функции для фоновых задач
# ----------------------------------------------------------------------


async def _run_transcription(project_id: str, service: PipelineService) -> None:
    """Фоновая задача: транскрипция аудиофайлов проекта."""
    try:
        logger.info("Фоновая задача: транскрипция для проекта %s", project_id)
        await service.run_transcription(project_id)
        logger.info("Транскрипция завершена для проекта %s", project_id)
    except Exception as exc:
        logger.exception(
            "Ошибка транскрипции для проекта %s: %s", project_id, exc
        )


async def _run_extraction(project_id: str, service: PipelineService) -> None:
    """Фоновая задача: извлечение бизнес-процессов."""
    try:
        logger.info("Фоновая задача: извлечение процессов для проекта %s", project_id)
        await service.run_extraction(project_id)
        logger.info("Извлечение процессов завершено для проекта %s", project_id)
    except Exception as exc:
        logger.exception(
            "Ошибка извлечения процессов для проекта %s: %s", project_id, exc
        )


async def _run_bpmn_generation(project_id: str, service: PipelineService) -> None:
    """Фоновая задача: генерация BPMN-диаграмм."""
    try:
        logger.info("Фоновая задача: генерация BPMN для проекта %s", project_id)
        await service.run_bpmn_generation(project_id)
        logger.info("Генерация BPMN завершена для проекта %s", project_id)
    except Exception as exc:
        logger.exception(
            "Ошибка генерации BPMN для проекта %s: %s", project_id, exc
        )


async def _run_gap_analysis(
    project_id: str,
    service: PipelineService,
    erp_config: dict,
) -> None:
    """Фоновая задача: GAP-анализ."""
    try:
        logger.info("Фоновая задача: GAP-анализ для проекта %s", project_id)
        await service.run_gap_analysis(project_id, erp_config=erp_config)
        logger.info("GAP-анализ завершён для проекта %s", project_id)
    except Exception as exc:
        logger.exception(
            "Ошибка GAP-анализа для проекта %s: %s", project_id, exc
        )


async def _run_tobe_generation(project_id: str, service: PipelineService) -> None:
    """Фоновая задача: генерация TO-BE процессов."""
    try:
        logger.info("Фоновая задача: генерация TO-BE для проекта %s", project_id)
        await service.run_tobe_generation(project_id)
        logger.info("Генерация TO-BE завершена для проекта %s", project_id)
    except Exception as exc:
        logger.exception(
            "Ошибка генерации TO-BE для проекта %s: %s", project_id, exc
        )


async def _run_doc_generation(project_id: str, service: PipelineService) -> None:
    """Фоновая задача: генерация документации."""
    try:
        logger.info("Фоновая задача: генерация документов для проекта %s", project_id)
        await service.run_doc_generation(project_id)
        logger.info("Генерация документов завершена для проекта %s", project_id)
    except Exception as exc:
        logger.exception(
            "Ошибка генерации документов для проекта %s: %s", project_id, exc
        )


# ----------------------------------------------------------------------
# Эндпоинты
# ----------------------------------------------------------------------


@router.post(
    "/transcribe",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Запустить транскрипцию",
    description="Запускает транскрипцию всех аудиофайлов проекта в фоновом режиме.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def run_transcription(
    project_id: str,
    background_tasks: BackgroundTasks,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    pipeline_service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> MessageResponse:
    """Запускает этап транскрипции аудиофайлов."""
    logger.info("Запуск транскрипции для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    background_tasks.add_task(_run_transcription, project_id, pipeline_service)
    return MessageResponse(message="Транскрипция запущена в фоновом режиме")


@router.post(
    "/extract",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Запустить извлечение процессов",
    description="Запускает извлечение бизнес-процессов из транскрипций в фоновом режиме.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def run_extraction(
    project_id: str,
    background_tasks: BackgroundTasks,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    pipeline_service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> MessageResponse:
    """Запускает этап извлечения бизнес-процессов."""
    logger.info("Запуск извлечения процессов для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    background_tasks.add_task(_run_extraction, project_id, pipeline_service)
    return MessageResponse(message="Извлечение процессов запущено в фоновом режиме")


@router.post(
    "/generate-bpmn",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Запустить генерацию BPMN",
    description="Запускает генерацию BPMN-диаграмм для извлечённых процессов в фоновом режиме.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def run_bpmn_generation(
    project_id: str,
    background_tasks: BackgroundTasks,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    pipeline_service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> MessageResponse:
    """Запускает этап генерации BPMN-диаграмм."""
    logger.info("Запуск генерации BPMN для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    background_tasks.add_task(_run_bpmn_generation, project_id, pipeline_service)
    return MessageResponse(message="Генерация BPMN запущена в фоновом режиме")


@router.post(
    "/gap-analysis",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Запустить GAP-анализ",
    description="Запускает GAP-анализ процессов относительно ERP-системы в фоновом режиме.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def run_gap_analysis(
    project_id: str,
    background_tasks: BackgroundTasks,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    pipeline_service: Annotated[PipelineService, Depends(get_pipeline_service)],
    erp_config: ErpConfigRequest | None = None,
) -> MessageResponse:
    """Запускает этап GAP-анализа."""
    logger.info("Запуск GAP-анализа для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    config_dict = erp_config.model_dump() if erp_config else {}
    background_tasks.add_task(
        _run_gap_analysis, project_id, pipeline_service, config_dict
    )
    return MessageResponse(message="GAP-анализ запущен в фоновом режиме")


@router.post(
    "/generate-tobe",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Запустить генерацию TO-BE",
    description="Запускает генерацию целевых (TO-BE) процессов в фоновом режиме.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def run_tobe_generation(
    project_id: str,
    background_tasks: BackgroundTasks,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    pipeline_service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> MessageResponse:
    """Запускает этап генерации TO-BE процессов."""
    logger.info("Запуск генерации TO-BE для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    background_tasks.add_task(_run_tobe_generation, project_id, pipeline_service)
    return MessageResponse(message="Генерация TO-BE процессов запущена в фоновом режиме")


@router.post(
    "/generate-docs",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Запустить генерацию документации",
    description="Запускает генерацию итоговой документации в фоновом режиме.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def run_doc_generation(
    project_id: str,
    background_tasks: BackgroundTasks,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    pipeline_service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> MessageResponse:
    """Запускает этап генерации документации."""
    logger.info("Запуск генерации документов для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    background_tasks.add_task(_run_doc_generation, project_id, pipeline_service)
    return MessageResponse(message="Генерация документации запущена в фоновом режиме")


@router.get(
    "/status",
    response_model=PipelineStatusResponse,
    summary="Статус пайплайна",
    description="Возвращает текущий статус конвейера обработки проекта.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def get_pipeline_status(
    project_id: str,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    pipeline_service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> PipelineStatusResponse:
    """Возвращает текущий статус пайплайна обработки."""
    logger.info("Запрос статуса пайплайна для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    try:
        status_data = await pipeline_service.get_status(project_id)
        return PipelineStatusResponse(**status_data)
    except AppError:
        raise
    except Exception as exc:
        logger.exception(
            "Ошибка при получении статуса пайплайна для проекта %s: %s",
            project_id,
            exc,
        )
        raise AppError(
            "Не удалось получить статус пайплайна",
            detail=str(exc),
        ) from exc
