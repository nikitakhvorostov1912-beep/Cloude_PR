"""API маршруты: управление проектами.

CRUD-операции для проектов: создание, получение списка,
получение деталей и удаление.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_project_service
from app.api.models import (
    ErrorResponse,
    MessageResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
)
from app.exceptions import AppError, NotFoundError
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать проект",
    description="Создаёт новый проект с указанным именем и описанием.",
    responses={
        422: {"model": ErrorResponse, "description": "Ошибка валидации"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def create_project(
    body: ProjectCreate,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    """Создаёт новый проект."""
    logger.info("Создание проекта: %s", body.name)
    try:
        project_data = await service.create_project(
            name=body.name,
            description=body.description,
        )
        return ProjectResponse(**project_data)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при создании проекта: %s", exc)
        raise AppError(
            "Не удалось создать проект",
            detail=str(exc),
        ) from exc


@router.get(
    "/",
    response_model=ProjectListResponse,
    summary="Список проектов",
    description="Возвращает список всех проектов.",
    responses={
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def list_projects(
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectListResponse:
    """Возвращает список всех проектов."""
    logger.info("Запрос списка проектов")
    try:
        projects_data = await service.list_projects()
        projects = [ProjectResponse(**p) for p in projects_data]
        return ProjectListResponse(projects=projects, total=len(projects))
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при получении списка проектов: %s", exc)
        raise AppError(
            "Не удалось получить список проектов",
            detail=str(exc),
        ) from exc


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Детали проекта",
    description="Возвращает подробную информацию о проекте.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def get_project(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    """Возвращает данные проекта по идентификатору."""
    logger.info("Запрос проекта: %s", project_id)
    try:
        project_data = await service.get_project(project_id)
        return ProjectResponse(**project_data)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при получении проекта %s: %s", project_id, exc)
        raise AppError(
            f"Не удалось получить данные проекта: {project_id}",
            detail=str(exc),
        ) from exc


@router.delete(
    "/{project_id}",
    response_model=MessageResponse,
    summary="Удалить проект",
    description="Удаляет проект и все связанные данные.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def delete_project(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> MessageResponse:
    """Удаляет проект по идентификатору."""
    logger.info("Удаление проекта: %s", project_id)
    try:
        await service.delete_project(project_id)
        return MessageResponse(message=f"Проект '{project_id}' успешно удалён")
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при удалении проекта %s: %s", project_id, exc)
        raise AppError(
            f"Не удалось удалить проект: {project_id}",
            detail=str(exc),
        ) from exc
