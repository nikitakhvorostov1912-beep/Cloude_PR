"""API маршруты: экспорт документов.

Эндпоинты для скачивания сгенерированных документов:
Visio-диаграммы, описания процессов (Word), требования (Excel/Word),
GAP-отчёты (Excel) и ZIP-архив со всеми файлами.
"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response, StreamingResponse

import re

from app.api.deps import get_export_service, get_project_service
from app.api.models import ErrorResponse
from app.bpmn.renderer import BPMNRenderer
from app.config import get_project_dir
from app.exceptions import AppError, NotFoundError, ValidationError
from app.services.export_service import ExportService
from app.services.project_service import ProjectService

# Валидация process_id: только безопасные символы
_SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _validate_process_id(process_id: str) -> None:
    """Проверяет process_id на безопасные символы (защита от path traversal)."""
    if not _SAFE_ID_PATTERN.match(process_id):
        raise ValidationError(
            f"Недопустимый идентификатор процесса: {process_id}",
            detail="Идентификатор может содержать только буквы, цифры, _ и -",
        )

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/export", tags=["export"])


def _make_content_disposition(filename: str) -> str:
    """Формирует заголовок Content-Disposition с поддержкой UTF-8 имён файлов."""
    encoded = quote(filename)
    return f"attachment; filename*=UTF-8''{encoded}"


def _make_inline_disposition(filename: str) -> str:
    """Формирует заголовок Content-Disposition для inline-отображения в браузере."""
    encoded = quote(filename)
    return f"inline; filename*=UTF-8''{encoded}"


# ----------------------------------------------------------------------
# Visio
# ----------------------------------------------------------------------


@router.get(
    "/visio/{process_id}",
    summary="Скачать Visio-диаграмму",
    description="Скачивает файл Visio (.vsdx) для указанного процесса.",
    responses={
        404: {"model": ErrorResponse, "description": "Файл не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def download_visio(
    project_id: str,
    process_id: str,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
) -> FileResponse:
    """Скачивает Visio-файл для процесса."""
    _validate_process_id(process_id)
    logger.info(
        "Скачивание Visio для процесса %s проекта %s", process_id, project_id
    )

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)

        # Сначала проверяем готовый файл
        visio_path = project_dir.get_visio_path(process_id)
        if not visio_path.is_file():
            # Пробуем сгенерировать через сервис
            visio_path = await export_service.export_visio(project_id, process_id)

        if not visio_path.is_file():
            raise NotFoundError(
                f"Visio-файл не найден для процесса: {process_id}",
            )

        filename = f"{process_id}.vsdx"
        return FileResponse(
            path=str(visio_path),
            media_type="application/vnd.ms-visio.drawing.main+xml",
            headers={"Content-Disposition": _make_content_disposition(filename)},
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception(
            "Ошибка при экспорте Visio для процесса %s: %s", process_id, exc
        )
        raise AppError(
            f"Не удалось экспортировать Visio-файл: {process_id}",
            detail=str(exc),
        ) from exc


# ----------------------------------------------------------------------
# SVG Preview (inline)
# ----------------------------------------------------------------------


@router.get(
    "/svg/{process_id}",
    summary="Просмотр SVG-диаграммы",
    description="Отдаёт SVG-файл диаграммы процесса для отображения в браузере.",
    responses={
        404: {"model": ErrorResponse, "description": "SVG-файл не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def preview_svg(
    project_id: str,
    process_id: str,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> Response:
    """Рендерит SVG-диаграмму из BPMN XML для inline-просмотра в браузере."""
    _validate_process_id(process_id)
    logger.info(
        "Просмотр SVG для процесса %s проекта %s", process_id, project_id
    )

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)
        bpmn_path = project_dir.bpmn / f"{process_id}.bpmn"

        if not bpmn_path.is_file():
            # Fallback to pre-generated SVG
            svg_path = project_dir.bpmn / f"{process_id}.svg"
            if not svg_path.is_file():
                raise NotFoundError(
                    f"BPMN-диаграмма не найдена для процесса: {process_id}",
                    detail="Сначала выполните этап генерации BPMN-диаграмм",
                )
            return FileResponse(
                path=str(svg_path),
                media_type="image/svg+xml",
                headers={
                    "Content-Disposition": _make_inline_disposition(
                        f"{process_id}.svg"
                    ),
                },
            )

        # Render SVG dynamically from BPMN XML
        bpmn_xml = bpmn_path.read_text(encoding="utf-8")
        renderer = BPMNRenderer()
        svg_content = renderer.render_svg(bpmn_xml)

        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={
                "Content-Disposition": _make_inline_disposition(
                    f"{process_id}.svg"
                ),
                "Access-Control-Allow-Origin": "*",
            },
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception(
            "Ошибка при рендеринге SVG для процесса %s: %s", process_id, exc
        )
        raise AppError(
            f"Не удалось загрузить SVG-диаграмму: {process_id}",
            detail=str(exc),
        ) from exc


# ----------------------------------------------------------------------
# BPMN XML Download
# ----------------------------------------------------------------------


@router.get(
    "/bpmn/{process_id}",
    summary="Скачать BPMN XML",
    description="Скачивает BPMN 2.0 XML-файл для указанного процесса.",
    responses={
        404: {"model": ErrorResponse, "description": "BPMN-файл не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def download_bpmn(
    project_id: str,
    process_id: str,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> FileResponse:
    """Скачивает BPMN 2.0 XML-файл."""
    _validate_process_id(process_id)
    logger.info(
        "Скачивание BPMN для процесса %s проекта %s", process_id, project_id
    )

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)
        bpmn_path = project_dir.bpmn / f"{process_id}.bpmn"

        if not bpmn_path.is_file():
            raise NotFoundError(
                f"BPMN-файл не найден для процесса: {process_id}",
                detail="Сначала выполните этап генерации BPMN-диаграмм",
            )

        filename = f"{process_id}.bpmn"
        return FileResponse(
            path=str(bpmn_path),
            media_type="application/xml",
            headers={"Content-Disposition": _make_content_disposition(filename)},
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception(
            "Ошибка при отдаче BPMN для процесса %s: %s", process_id, exc
        )
        raise AppError(
            f"Не удалось загрузить BPMN-файл: {process_id}",
            detail=str(exc),
        ) from exc


# ----------------------------------------------------------------------
# Описание процессов (Word)
# ----------------------------------------------------------------------


@router.get(
    "/process-doc",
    summary="Скачать описание процессов (Word)",
    description="Скачивает Word-документ с описаниями всех бизнес-процессов.",
    responses={
        404: {"model": ErrorResponse, "description": "Документ не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def download_process_doc(
    project_id: str,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
) -> FileResponse:
    """Скачивает Word-документ с описаниями процессов."""
    logger.info("Скачивание описания процессов для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)
        doc_path = project_dir.output / "Описание_процессов.docx"

        if not doc_path.is_file():
            doc_path = await export_service.export_process_doc(project_id)

        if not doc_path.is_file():
            raise NotFoundError(
                "Документ с описанием процессов не найден",
                detail="Сначала выполните этап генерации документации",
            )

        filename = "Описание_процессов.docx"
        return FileResponse(
            path=str(doc_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": _make_content_disposition(filename)},
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при экспорте описания процессов: %s", exc)
        raise AppError(
            "Не удалось экспортировать описание процессов",
            detail=str(exc),
        ) from exc


# ----------------------------------------------------------------------
# Требования (Excel)
# ----------------------------------------------------------------------


@router.get(
    "/requirements-excel",
    summary="Скачать требования (Excel)",
    description="Скачивает Excel-файл с реестром требований.",
    responses={
        404: {"model": ErrorResponse, "description": "Документ не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def download_requirements_excel(
    project_id: str,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
) -> FileResponse:
    """Скачивает Excel с требованиями."""
    logger.info("Скачивание требований (Excel) для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)
        excel_path = project_dir.output / "Реестр_требований.xlsx"

        if not excel_path.is_file():
            excel_path = await export_service.export_requirements_excel(project_id)

        if not excel_path.is_file():
            raise NotFoundError(
                "Excel-файл с требованиями не найден",
                detail="Сначала выполните этап генерации документации",
            )

        filename = "Реестр_требований.xlsx"
        return FileResponse(
            path=str(excel_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": _make_content_disposition(filename)},
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при экспорте требований (Excel): %s", exc)
        raise AppError(
            "Не удалось экспортировать требования в Excel",
            detail=str(exc),
        ) from exc


# ----------------------------------------------------------------------
# Требования (Word)
# ----------------------------------------------------------------------


@router.get(
    "/requirements-word",
    summary="Скачать требования (Word)",
    description="Скачивает Word-документ с реестром требований.",
    responses={
        404: {"model": ErrorResponse, "description": "Документ не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def download_requirements_word(
    project_id: str,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
) -> FileResponse:
    """Скачивает Word-документ с требованиями."""
    logger.info("Скачивание требований (Word) для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)
        doc_path = project_dir.output / "Реестр_требований.docx"

        if not doc_path.is_file():
            doc_path = await export_service.export_requirements_word(project_id)

        if not doc_path.is_file():
            raise NotFoundError(
                "Word-файл с требованиями не найден",
                detail="Сначала выполните этап генерации документации",
            )

        filename = "Реестр_требований.docx"
        return FileResponse(
            path=str(doc_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": _make_content_disposition(filename)},
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при экспорте требований (Word): %s", exc)
        raise AppError(
            "Не удалось экспортировать требования в Word",
            detail=str(exc),
        ) from exc


# ----------------------------------------------------------------------
# GAP-отчёт (Excel)
# ----------------------------------------------------------------------


@router.get(
    "/gap-report",
    summary="Скачать GAP-отчёт (Excel)",
    description="Скачивает Excel-файл с результатами GAP-анализа.",
    responses={
        404: {"model": ErrorResponse, "description": "Отчёт не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def download_gap_report(
    project_id: str,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
) -> FileResponse:
    """Скачивает Excel с результатами GAP-анализа."""
    logger.info("Скачивание GAP-отчёта для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)
        excel_path = project_dir.output / "GAP_анализ.xlsx"

        if not excel_path.is_file():
            excel_path = await export_service.export_gap_report(project_id)

        if not excel_path.is_file():
            raise NotFoundError(
                "Excel-файл с GAP-анализом не найден",
                detail="Сначала выполните этап GAP-анализа",
            )

        filename = "GAP_анализ.xlsx"
        return FileResponse(
            path=str(excel_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": _make_content_disposition(filename)},
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при экспорте GAP-отчёта: %s", exc)
        raise AppError(
            "Не удалось экспортировать GAP-отчёт",
            detail=str(exc),
        ) from exc


# ----------------------------------------------------------------------
# Полный архив (ZIP)
# ----------------------------------------------------------------------


@router.get(
    "/all",
    summary="Скачать все документы (ZIP)",
    description="Скачивает ZIP-архив со всеми сгенерированными документами проекта.",
    responses={
        404: {"model": ErrorResponse, "description": "Файлы не найдены"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def download_all(
    project_id: str,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
) -> StreamingResponse:
    """Скачивает ZIP-архив со всеми документами проекта."""
    logger.info("Скачивание всех документов для проекта %s", project_id)

    try:
        await project_service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)

        # Собираем файлы из различных директорий
        files_to_archive: list[tuple[Path, str]] = []

        # Visio-файлы
        if project_dir.visio.is_dir():
            for f in project_dir.visio.iterdir():
                if f.is_file() and f.suffix.lower() == ".vsdx":
                    files_to_archive.append((f, f"visio/{f.name}"))

        # BPMN-файлы
        if project_dir.bpmn.is_dir():
            for f in project_dir.bpmn.iterdir():
                if f.is_file() and f.suffix.lower() == ".bpmn":
                    files_to_archive.append((f, f"bpmn/{f.name}"))

        # Документы из output/
        if project_dir.output.is_dir():
            for f in project_dir.output.iterdir():
                if f.is_file() and f.suffix.lower() in {
                    ".docx", ".xlsx", ".pdf", ".json"
                }:
                    files_to_archive.append((f, f"documents/{f.name}"))

        if not files_to_archive:
            raise NotFoundError(
                "Нет файлов для экспорта",
                detail="Сначала выполните этапы генерации документации",
            )

        # Создаём ZIP в памяти
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path, archive_name in files_to_archive:
                zf.write(str(file_path), archive_name)

        buffer.seek(0)

        filename = f"Проект_{project_id}_документы.zip"
        logger.info(
            "ZIP-архив создан для проекта %s: %d файлов",
            project_id,
            len(files_to_archive),
        )

        return StreamingResponse(
            content=buffer,
            media_type="application/zip",
            headers={"Content-Disposition": _make_content_disposition(filename)},
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при создании ZIP-архива: %s", exc)
        raise AppError(
            "Не удалось создать архив с документами",
            detail=str(exc),
        ) from exc
