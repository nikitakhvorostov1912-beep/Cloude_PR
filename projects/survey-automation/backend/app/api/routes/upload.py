"""API маршруты: загрузка файлов.

Эндпоинты для загрузки аудиофайлов, текстовых транскрипций
и импорта файлов из указанной папки на диске.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status

from app.api.deps import get_project_service
from app.api.models import (
    ErrorResponse,
    ImportFolderRequest,
    ImportFolderResponse,
    UploadResponse,
)
from app.config import get_project_dir
from app.exceptions import AppError, NotFoundError, ValidationError
from app.services.project_service import ProjectService


def _safe_filename(raw: str) -> str:
    """Извлекает безопасное имя файла, убирая компоненты пути."""
    return Path(raw).name

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}", tags=["upload"])

# Допустимые расширения файлов
AUDIO_EXTENSIONS: frozenset[str] = frozenset({".wav", ".mp3", ".ogg", ".m4a", ".flac", ".wma", ".aac"})
TRANSCRIPT_EXTENSIONS: frozenset[str] = frozenset({".txt", ".json"})
ALL_IMPORTABLE_EXTENSIONS: frozenset[str] = AUDIO_EXTENSIONS | TRANSCRIPT_EXTENSIONS

# Лимит размера: 500 МБ для аудио
MAX_AUDIO_SIZE: int = 500 * 1024 * 1024
# Лимит размера: 50 МБ для текстов
MAX_TRANSCRIPT_SIZE: int = 50 * 1024 * 1024


@router.post(
    "/upload/audio",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузить аудиофайл",
    description="Загружает аудиофайл интервью в проект.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        422: {"model": ErrorResponse, "description": "Некорректный формат файла"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def upload_audio(
    project_id: str,
    file: UploadFile,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> UploadResponse:
    """Загружает аудиофайл в директорию audio/ проекта."""
    logger.info("Загрузка аудиофайла в проект %s: %s", project_id, file.filename)

    # Проверяем существование проекта
    try:
        await service.get_project(project_id)
    except AppError:
        raise

    # Валидация расширения
    if not file.filename:
        raise ValidationError("Имя файла не указано")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in AUDIO_EXTENSIONS:
        raise ValidationError(
            f"Неподдерживаемый формат аудиофайла: {file_ext}",
            detail=f"Допустимые форматы: {', '.join(sorted(AUDIO_EXTENSIONS))}",
        )

    # Валидация размера
    if file.size is not None and file.size > MAX_AUDIO_SIZE:
        raise ValidationError(
            f"Файл слишком большой: {file.size / (1024 * 1024):.1f} МБ",
            detail=f"Максимальный размер: {MAX_AUDIO_SIZE / (1024 * 1024):.0f} МБ",
        )

    # Сохранение файла
    try:
        project_dir = get_project_dir(project_id)
        project_dir.ensure_dirs()
        safe_name = _safe_filename(file.filename)
        dest_path = project_dir.audio / safe_name
        file_id = Path(safe_name).stem

        with open(dest_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        logger.info(
            "Аудиофайл сохранён: %s (%s)",
            dest_path.name,
            f"{dest_path.stat().st_size / (1024 * 1024):.1f} МБ",
        )

        return UploadResponse(
            message=f"Аудиофайл '{file.filename}' успешно загружен",
            file_id=file_id,
            filename=file.filename,
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при сохранении аудиофайла: %s", exc)
        raise AppError(
            "Не удалось сохранить аудиофайл",
            detail=str(exc),
        ) from exc


@router.post(
    "/upload/transcript",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузить транскрипцию",
    description="Загружает файл транскрипции (.txt или .json) в проект.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        422: {"model": ErrorResponse, "description": "Некорректный формат файла"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def upload_transcript(
    project_id: str,
    file: UploadFile,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> UploadResponse:
    """Загружает файл транскрипции в директорию transcripts/ проекта."""
    logger.info("Загрузка транскрипции в проект %s: %s", project_id, file.filename)

    # Проверяем существование проекта
    try:
        await service.get_project(project_id)
    except AppError:
        raise

    # Валидация расширения
    if not file.filename:
        raise ValidationError("Имя файла не указано")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in TRANSCRIPT_EXTENSIONS:
        raise ValidationError(
            f"Неподдерживаемый формат транскрипции: {file_ext}",
            detail=f"Допустимые форматы: {', '.join(sorted(TRANSCRIPT_EXTENSIONS))}",
        )

    # Валидация размера
    if file.size is not None and file.size > MAX_TRANSCRIPT_SIZE:
        raise ValidationError(
            f"Файл слишком большой: {file.size / (1024 * 1024):.1f} МБ",
            detail=f"Максимальный размер: {MAX_TRANSCRIPT_SIZE / (1024 * 1024):.0f} МБ",
        )

    # Сохранение файла
    try:
        project_dir = get_project_dir(project_id)
        project_dir.ensure_dirs()
        safe_name = _safe_filename(file.filename)
        dest_path = project_dir.transcripts / safe_name
        file_id = Path(safe_name).stem

        content = await file.read()
        with open(dest_path, "wb") as f:
            f.write(content)

        logger.info("Транскрипция сохранена: %s", dest_path.name)

        return UploadResponse(
            message=f"Транскрипция '{file.filename}' успешно загружена",
            file_id=file_id,
            filename=file.filename,
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при сохранении транскрипции: %s", exc)
        raise AppError(
            "Не удалось сохранить файл транскрипции",
            detail=str(exc),
        ) from exc


@router.post(
    "/import-folder",
    response_model=ImportFolderResponse,
    summary="Импорт файлов из папки",
    description="Сканирует указанную папку на наличие аудио- и текстовых файлов и копирует их в проект.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект или папка не найдены"},
        422: {"model": ErrorResponse, "description": "Ошибка валидации"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def import_folder(
    project_id: str,
    body: ImportFolderRequest,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ImportFolderResponse:
    """Импортирует файлы из указанной папки в проект."""
    logger.info("Импорт файлов в проект %s из папки: %s", project_id, body.path)

    # Проверяем существование проекта
    try:
        await service.get_project(project_id)
    except AppError:
        raise

    # Проверяем существование папки
    source_path = Path(body.path)
    if not source_path.is_dir():
        raise NotFoundError(
            f"Папка не найдена: {body.path}",
            detail="Укажите корректный путь к существующей папке",
        )

    # Сканируем и копируем файлы
    try:
        project_dir = get_project_dir(project_id)
        project_dir.ensure_dirs()

        imported_files: list[str] = []
        skipped_files: list[str] = []

        for file_path in sorted(source_path.iterdir()):
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()
            if ext not in ALL_IMPORTABLE_EXTENSIONS:
                skipped_files.append(file_path.name)
                continue

            # Определяем целевую директорию
            if ext in AUDIO_EXTENSIONS:
                dest_dir = project_dir.audio
            else:
                dest_dir = project_dir.transcripts

            dest_path = dest_dir / file_path.name
            await asyncio.to_thread(shutil.copy2, str(file_path), str(dest_path))
            imported_files.append(file_path.name)
            logger.info("Импортирован файл: %s -> %s", file_path.name, dest_dir.name)

        message = f"Импортировано {len(imported_files)} файлов из папки"
        if skipped_files:
            message += f", пропущено {len(skipped_files)} файлов с неподдерживаемым форматом"

        logger.info(
            "Импорт завершён: %d импортировано, %d пропущено",
            len(imported_files),
            len(skipped_files),
        )

        return ImportFolderResponse(
            message=message,
            imported_files=imported_files,
            skipped_files=skipped_files,
            total_imported=len(imported_files),
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при импорте файлов: %s", exc)
        raise AppError(
            "Не удалось импортировать файлы из папки",
            detail=str(exc),
        ) from exc
