"""API маршруты: данные (транскрипции, процессы, GAP, требования).

Эндпоинты для чтения и обновления данных, извлечённых на различных
этапах пайплайна обработки: транскрипции, бизнес-процессы,
результаты GAP-анализа и списки требований.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.deps import get_project_service
from app.api.models import (
    ErrorResponse,
    GapListResponse,
    ProcessListResponse,
    ProcessResponse,
    ProcessUpdate,
    RequirementListResponse,
    TranscriptResponse,
)
from app.config import get_project_dir
from app.exceptions import AppError, NotFoundError, ProcessingError
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}", tags=["data"])


# ----------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any]:
    """Загружает JSON-файл и возвращает словарь."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ProcessingError(
            f"Некорректный JSON в файле: {path.name}",
            detail=str(exc),
        ) from exc
    except OSError as exc:
        raise ProcessingError(
            f"Ошибка чтения файла: {path.name}",
            detail=str(exc),
        ) from exc

    if not isinstance(data, dict):
        raise ProcessingError(
            f"Ожидается JSON-объект в файле: {path.name}",
            detail=f"Получен тип: {type(data).__name__}",
        )
    return data


def _save_json(path: Path, data: dict[str, Any]) -> None:
    """Сохраняет словарь в JSON-файл."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise ProcessingError(
            f"Ошибка записи файла: {path.name}",
            detail=str(exc),
        ) from exc


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    """Загружает JSON-файл и возвращает список словарей."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ProcessingError(
            f"Некорректный JSON в файле: {path.name}",
            detail=str(exc),
        ) from exc
    except OSError as exc:
        raise ProcessingError(
            f"Ошибка чтения файла: {path.name}",
            detail=str(exc),
        ) from exc

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ProcessingError(
        f"Ожидается JSON-массив или объект в файле: {path.name}",
        detail=f"Получен тип: {type(data).__name__}",
    )


# ----------------------------------------------------------------------
# Транскрипции
# ----------------------------------------------------------------------


@router.get(
    "/transcripts",
    response_model=list[TranscriptResponse],
    summary="Список транскрипций",
    description="Возвращает список всех транскрипций проекта.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def list_transcripts(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> list[TranscriptResponse]:
    """Возвращает список транскрипций проекта."""
    logger.info("Запрос списка транскрипций для проекта %s", project_id)

    try:
        await service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)
        transcripts: list[TranscriptResponse] = []

        if not project_dir.transcripts.is_dir():
            return transcripts

        json_files = sorted(
            p for p in project_dir.transcripts.iterdir()
            if p.is_file() and p.suffix.lower() == ".json"
        )

        for json_path in json_files:
            try:
                data = _load_json(json_path)
                metadata = data.get("metadata", {})
                transcripts.append(TranscriptResponse(
                    id=json_path.stem,
                    filename=metadata.get("audio_file", json_path.name),
                    dialogue=data.get("dialogue", data.get("segments", [])),
                    full_text=data.get("full_text", ""),
                    metadata=metadata,
                    speaker_stats=data.get("speaker_stats", {}),
                ))
            except Exception as exc:
                logger.warning(
                    "Не удалось прочитать транскрипцию %s: %s",
                    json_path.name,
                    exc,
                )
                continue

        return transcripts
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при получении транскрипций: %s", exc)
        raise AppError(
            "Не удалось получить список транскрипций",
            detail=str(exc),
        ) from exc


@router.get(
    "/transcripts/{transcript_id}",
    response_model=TranscriptResponse,
    summary="Детали транскрипции",
    description="Возвращает полные данные транскрипции по идентификатору.",
    responses={
        404: {"model": ErrorResponse, "description": "Транскрипция не найдена"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def get_transcript(
    project_id: str,
    transcript_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> TranscriptResponse:
    """Возвращает данные транскрипции по идентификатору."""
    logger.info(
        "Запрос транскрипции %s для проекта %s", transcript_id, project_id
    )

    try:
        await service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)
        json_path = project_dir.get_transcript_path(transcript_id, ext=".json")

        if not json_path.is_file():
            raise NotFoundError(
                f"Транскрипция не найдена: {transcript_id}",
                detail=str(json_path),
            )

        data = _load_json(json_path)
        metadata = data.get("metadata", {})

        return TranscriptResponse(
            id=transcript_id,
            filename=metadata.get("audio_file", json_path.name),
            dialogue=data.get("dialogue", data.get("segments", [])),
            full_text=data.get("full_text", ""),
            metadata=metadata,
            speaker_stats=data.get("speaker_stats", {}),
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception(
            "Ошибка при получении транскрипции %s: %s", transcript_id, exc
        )
        raise AppError(
            f"Не удалось получить транскрипцию: {transcript_id}",
            detail=str(exc),
        ) from exc


# ----------------------------------------------------------------------
# Процессы
# ----------------------------------------------------------------------


@router.get(
    "/processes",
    response_model=ProcessListResponse,
    summary="Список процессов",
    description="Возвращает список извлечённых бизнес-процессов проекта.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def list_processes(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProcessListResponse:
    """Возвращает список бизнес-процессов проекта."""
    logger.info("Запрос списка процессов для проекта %s", project_id)

    try:
        await service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)
        processes: list[ProcessResponse] = []

        if not project_dir.processes.is_dir():
            return ProcessListResponse(processes=[], total=0)

        json_files = sorted(
            p for p in project_dir.processes.iterdir()
            if p.is_file()
            and p.suffix.lower() == ".json"
            and not p.name.startswith("_")
            and not p.name.endswith("_bpmn.json")
            and not p.name.endswith("_gap.json")
            and not p.name.endswith("_tobe.json")
        )

        for json_path in json_files:
            try:
                data = _load_json(json_path)
                # Файл может содержать список процессов или один процесс
                if isinstance(data.get("processes"), list):
                    for i, proc in enumerate(data["processes"]):
                        proc_id = proc.get("id", f"{json_path.stem}_{i}")
                        processes.append(ProcessResponse(
                            id=proc_id,
                            name=proc.get("name", ""),
                            department=proc.get("department", ""),
                            description=proc.get("description", ""),
                            status=proc.get("status", "draft"),
                            trigger=proc.get("trigger", ""),
                            result=proc.get("result", ""),
                            participants=proc.get("participants", []),
                            steps=proc.get("steps", []),
                            decisions=proc.get("decisions", []),
                            pain_points=proc.get("pain_points", []),
                            integrations=proc.get("integrations", []),
                            metrics=proc.get("metrics", {}),
                        ))
                else:
                    processes.append(ProcessResponse(
                        id=data.get("id", json_path.stem),
                        name=data.get("name", ""),
                        department=data.get("department", ""),
                        description=data.get("description", ""),
                        status=data.get("status", "draft"),
                        trigger=data.get("trigger", ""),
                        result=data.get("result", ""),
                        participants=data.get("participants", []),
                        steps=data.get("steps", []),
                        decisions=data.get("decisions", []),
                        pain_points=data.get("pain_points", []),
                        integrations=data.get("integrations", []),
                        metrics=data.get("metrics", {}),
                    ))
            except Exception as exc:
                logger.warning(
                    "Не удалось прочитать процесс %s: %s", json_path.name, exc
                )
                continue

        return ProcessListResponse(processes=processes, total=len(processes))
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при получении списка процессов: %s", exc)
        raise AppError(
            "Не удалось получить список процессов",
            detail=str(exc),
        ) from exc


@router.get(
    "/processes/{process_id}",
    response_model=ProcessResponse,
    summary="Детали процесса",
    description="Возвращает данные бизнес-процесса по идентификатору.",
    responses={
        404: {"model": ErrorResponse, "description": "Процесс не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def get_process(
    project_id: str,
    process_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProcessResponse:
    """Возвращает данные процесса по идентификатору."""
    logger.info("Запрос процесса %s для проекта %s", process_id, project_id)

    try:
        await service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)
        process_data = _find_process_by_id(project_dir, process_id)

        if process_data is None:
            raise NotFoundError(
                f"Процесс не найден: {process_id}",
            )

        return ProcessResponse(**process_data)
    except AppError:
        raise
    except Exception as exc:
        logger.exception(
            "Ошибка при получении процесса %s: %s", process_id, exc
        )
        raise AppError(
            f"Не удалось получить данные процесса: {process_id}",
            detail=str(exc),
        ) from exc


@router.put(
    "/processes/{process_id}",
    response_model=ProcessResponse,
    summary="Обновить процесс",
    description="Обновляет данные бизнес-процесса (пользовательские правки).",
    responses={
        404: {"model": ErrorResponse, "description": "Процесс не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def update_process(
    project_id: str,
    process_id: str,
    body: ProcessUpdate,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProcessResponse:
    """Обновляет данные процесса."""
    logger.info("Обновление процесса %s для проекта %s", process_id, project_id)

    try:
        await service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)

        # Ищем файл, содержащий процесс
        process_data, file_path, index_in_list = _find_process_location(
            project_dir, process_id
        )

        if process_data is None or file_path is None:
            raise NotFoundError(
                f"Процесс не найден: {process_id}",
            )

        # Обновляем только заполненные поля
        update_dict = body.model_dump(exclude_none=True)
        process_data.update(update_dict)

        # Сохраняем обратно в файл
        file_data = _load_json(file_path)
        if isinstance(file_data.get("processes"), list) and index_in_list is not None:
            file_data["processes"][index_in_list] = process_data
        else:
            file_data.update(process_data)

        _save_json(file_path, file_data)

        logger.info("Процесс %s обновлён", process_id)
        return ProcessResponse(**process_data)
    except AppError:
        raise
    except Exception as exc:
        logger.exception(
            "Ошибка при обновлении процесса %s: %s", process_id, exc
        )
        raise AppError(
            f"Не удалось обновить процесс: {process_id}",
            detail=str(exc),
        ) from exc


# ----------------------------------------------------------------------
# GAP-анализ
# ----------------------------------------------------------------------


@router.get(
    "/gaps",
    response_model=GapListResponse,
    summary="Результаты GAP-анализа",
    description="Возвращает результаты GAP-анализа процессов.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def get_gaps(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> GapListResponse:
    """Возвращает результаты GAP-анализа."""
    logger.info("Запрос GAP-анализа для проекта %s", project_id)

    try:
        await service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)

        # Ищем GAP-данные в нескольких местах
        gaps_path = project_dir.root / "gaps" / "gap_analysis.json"
        if not gaps_path.is_file():
            gaps_path = project_dir.output / "gap_analysis.json"
        if not gaps_path.is_file():
            gaps_path = project_dir.processes / "_gap_analysis.json"
        if not gaps_path.is_file():
            return GapListResponse(gaps=[], total=0, summary={})

        with open(gaps_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # Данные могут быть dict с ключом "gaps" или list
        gap_items: list[dict[str, Any]] = []
        summary: dict[str, Any] = {}
        if isinstance(raw_data, dict):
            gap_items = raw_data.get("gaps", [])
            summary = raw_data.get("summary", {})
        elif isinstance(raw_data, list):
            gap_items = raw_data

        result: list[dict[str, Any]] = []
        for i, gap in enumerate(gap_items):
            result.append({
                "id": gap.get("id", f"gap_{i}"),
                "process_id": gap.get("process_id", ""),
                "process_name": gap.get("process_name", ""),
                "function_name": gap.get("function_name", ""),
                "coverage": gap.get("coverage", 0),
                "erp_module": gap.get("erp_module", ""),
                "erp_document": gap.get("erp_document", ""),
                "gap_description": gap.get("gap_description", ""),
                "recommendation": gap.get("recommendation", ""),
                "effort_days": gap.get("effort_days", 0),
                "priority": gap.get("priority", ""),
            })

        return GapListResponse(gaps=result, total=len(result), summary=summary)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при получении GAP-анализа: %s", exc)
        raise AppError(
            "Не удалось получить результаты GAP-анализа",
            detail=str(exc),
        ) from exc


# ----------------------------------------------------------------------
# Требования
# ----------------------------------------------------------------------


@router.get(
    "/requirements",
    response_model=RequirementListResponse,
    summary="Список требований",
    description="Возвращает список требований, сформированных по результатам анализа.",
    responses={
        404: {"model": ErrorResponse, "description": "Проект не найден"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def get_requirements(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> RequirementListResponse:
    """Возвращает список требований проекта."""
    logger.info("Запрос требований для проекта %s", project_id)

    try:
        await service.get_project(project_id)
    except AppError:
        raise

    try:
        project_dir = get_project_dir(project_id)

        # Ищем требования в нескольких местах
        requirements_path = project_dir.processes / "_requirements.json"
        if not requirements_path.is_file():
            requirements_path = project_dir.output / "requirements.json"
        if not requirements_path.is_file():
            requirements_path = project_dir.root / "requirements" / "requirements.json"
        if not requirements_path.is_file():
            return RequirementListResponse(requirements=[], total=0)

        with open(requirements_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # Данные могут быть dict с ключом "requirements" или list
        req_items: list[dict[str, Any]] = []
        if isinstance(raw_data, dict):
            req_items = raw_data.get("requirements", [raw_data])
        elif isinstance(raw_data, list):
            req_items = raw_data

        return RequirementListResponse(requirements=req_items, total=len(req_items))
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Ошибка при получении требований: %s", exc)
        raise AppError(
            "Не удалось получить список требований",
            detail=str(exc),
        ) from exc


# ----------------------------------------------------------------------
# Вспомогательные функции для процессов
# ----------------------------------------------------------------------


def _find_process_by_id(
    project_dir: Any,
    process_id: str,
) -> dict[str, Any] | None:
    """Ищет процесс по ID во всех файлах директории processes/."""
    if not project_dir.processes.is_dir():
        return None

    json_files = sorted(
        p for p in project_dir.processes.iterdir()
        if p.is_file() and p.suffix.lower() == ".json"
    )

    for json_path in json_files:
        try:
            data = _load_json(json_path)

            # Файл с массивом процессов
            if isinstance(data.get("processes"), list):
                for proc in data["processes"]:
                    if proc.get("id") == process_id:
                        return proc

            # Одиночный процесс
            if data.get("id") == process_id:
                return data

            # Процесс без id, но имя файла совпадает
            if json_path.stem == process_id:
                data.setdefault("id", process_id)
                return data
        except Exception as exc:
            logger.warning(
                "Не удалось прочитать файл процессов %s: %s", json_path.name, exc
            )
            continue

    return None


def _find_process_location(
    project_dir: Any,
    process_id: str,
) -> tuple[dict[str, Any] | None, Path | None, int | None]:
    """Ищет процесс и возвращает данные, путь к файлу и индекс в списке."""
    if not project_dir.processes.is_dir():
        return None, None, None

    json_files = sorted(
        p for p in project_dir.processes.iterdir()
        if p.is_file() and p.suffix.lower() == ".json"
    )

    for json_path in json_files:
        try:
            data = _load_json(json_path)

            # Файл с массивом процессов
            if isinstance(data.get("processes"), list):
                for i, proc in enumerate(data["processes"]):
                    if proc.get("id") == process_id:
                        return proc, json_path, i

            # Одиночный процесс
            if data.get("id") == process_id:
                return data, json_path, None

            # По имени файла
            if json_path.stem == process_id:
                data.setdefault("id", process_id)
                return data, json_path, None
        except Exception as exc:
            logger.warning(
                "Не удалось прочитать файл процессов %s: %s", json_path.name, exc
            )
            continue

    return None, None, None
