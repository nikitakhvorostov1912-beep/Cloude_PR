"""Сервис оркестрации пайплайна (6 стадий)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import ProjectDir, get_config, get_project_dir
from app.exceptions import (
    NotFoundError,
    PipelineError,
    ProcessingError,
    ValidationError,
)
from app.services.analysis_service import AnalysisService
from app.services.bpmn_service import BPMNService
from app.services.export_service import ExportService
from app.services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)


# Определение стадий конвейера в порядке выполнения
PIPELINE_STAGES: list[str] = [
    "transcribe",
    "extract",
    "generate-bpmn",
    "gap-analysis",
    "generate-tobe",
    "generate-docs",
]

#: Человекочитаемые названия стадий
STAGE_LABELS: dict[str, str] = {
    "transcribe": "Транскрипция",
    "extract": "Извлечение процессов",
    "generate-bpmn": "Генерация BPMN",
    "gap-analysis": "GAP-анализ",
    "generate-tobe": "Генерация TO-BE",
    "generate-docs": "Генерация документов",
}


class PipelineService:
    """Оркестрация конвейера обработки проекта.

    Управляет последовательным выполнением 6 стадий конвейера:
    транскрипция -> извлечение процессов -> генерация BPMN ->
    GAP-анализ -> генерация TO-BE -> генерация документов.

    Каждая стадия зависит от предыдущих. Повторный запуск стадии
    допускается (перезапуск при ошибке).

    Args:
        transcription_service: Сервис транскрипции.
        analysis_service: Сервис анализа.
        bpmn_service: Сервис BPMN.
        export_service: Сервис экспорта.
    """

    def __init__(
        self,
        transcription_service: TranscriptionService | None = None,
        analysis_service: AnalysisService | None = None,
        bpmn_service: BPMNService | None = None,
        export_service: ExportService | None = None,
    ) -> None:
        self._transcription = transcription_service or TranscriptionService()
        self._analysis = analysis_service or AnalysisService()
        self._bpmn = bpmn_service or BPMNService()
        self._export = export_service or ExportService()

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    async def run_stage(
        self,
        project_id: str,
        stage: str,
    ) -> dict[str, Any]:
        """Запускает указанную стадию конвейера.

        Args:
            project_id: Идентификатор проекта.
            stage: Имя стадии (одно из PIPELINE_STAGES).

        Returns:
            Обновлённый статус конвейера.

        Raises:
            ValidationError: Если стадия неизвестна или предыдущие не завершены.
            NotFoundError: Если проект не найден.
            PipelineError: При ошибке выполнения стадии.
        """
        if stage not in PIPELINE_STAGES:
            raise ValidationError(
                f"Неизвестная стадия конвейера: {stage}",
                detail={
                    "stage": stage,
                    "available_stages": PIPELINE_STAGES,
                },
            )

        project_dir = self._ensure_project_exists(project_id)

        # Проверяем зависимости: все предыдущие стадии должны быть завершены
        self._validate_dependencies(project_dir, stage)

        # Обновляем статус: стадия запущена
        self._update_stage_status(
            project_dir, stage,
            status="running", progress=0, error=None,
        )

        stage_label = STAGE_LABELS.get(stage, stage)
        logger.info(
            "Запуск стадии '%s' (%s) для проекта: %s",
            stage, stage_label, project_id,
        )

        try:
            # Выполняем стадию
            await self._execute_stage(project_dir, project_id, stage)

            # Обновляем статус: стадия завершена
            self._update_stage_status(
                project_dir, stage,
                status="completed", progress=100, error=None,
            )
            self._mark_stage_completed(project_dir, stage)

            logger.info(
                "Стадия '%s' завершена успешно для проекта: %s",
                stage, project_id,
            )

        except (NotFoundError, ValidationError, ProcessingError, PipelineError) as exc:
            # Помечаем стадию как проваленную
            self._update_stage_status(
                project_dir, stage,
                status="failed", progress=0, error=exc.message,
            )
            logger.error(
                "Стадия '%s' завершилась с ошибкой для проекта %s: %s",
                stage, project_id, exc.message,
            )
            raise PipelineError(
                f"Ошибка на стадии «{stage_label}»: {exc.message}",
                detail={"stage": stage, "original_error": str(exc)},
            ) from exc

        except Exception as exc:
            self._update_stage_status(
                project_dir, stage,
                status="failed", progress=0, error=str(exc),
            )
            logger.exception(
                "Непредвиденная ошибка на стадии '%s' для проекта %s",
                stage, project_id,
            )
            raise PipelineError(
                f"Непредвиденная ошибка на стадии «{stage_label}»",
                detail={"stage": stage, "error": str(exc)},
            ) from exc

        return await self.get_status(project_id)

    async def get_status(self, project_id: str) -> dict[str, Any]:
        """Возвращает текущий статус конвейера проекта.

        Args:
            project_id: Идентификатор проекта.

        Returns:
            Словарь с информацией о статусе каждой стадии:
            ``{stages: [{name, label, status, progress, error}], completed_stages: [...]}``

        Raises:
            NotFoundError: Если проект не найден.
        """
        project_dir = self._ensure_project_exists(project_id)
        pipeline_state = self._load_pipeline_state(project_dir)
        completed = pipeline_state.get("completed_stages", [])

        stages_info: list[dict[str, Any]] = []
        for stage_name in PIPELINE_STAGES:
            stage_data = pipeline_state.get(f"stage_{stage_name}", {})
            stages_info.append({
                "name": stage_name,
                "label": STAGE_LABELS.get(stage_name, stage_name),
                "status": stage_data.get("status", "pending"),
                "progress": stage_data.get("progress", 0),
                "error": stage_data.get("error"),
                "completed": stage_name in completed,
            })

        # Определяем текущую стадию
        current_stage = pipeline_state.get("stage")

        return {
            "project_id": project_id,
            "current_stage": current_stage,
            "stages": stages_info,
            "completed_stages": completed,
            "overall_progress": self._calculate_overall_progress(completed),
        }

    # ------------------------------------------------------------------
    # Выполнение стадий
    # ------------------------------------------------------------------

    async def _execute_stage(
        self,
        project_dir: ProjectDir,
        project_id: str,
        stage: str,
    ) -> None:
        """Выполняет указанную стадию конвейера."""

        def _progress_callback(current: float, total: float, message: str) -> None:
            """Обновляет прогресс стадии."""
            pct = int((current / max(total, 1)) * 100)
            self._update_stage_status(
                project_dir, stage,
                status="running", progress=pct, error=None,
            )

        if stage == "transcribe":
            await self._run_transcription(project_dir, _progress_callback)

        elif stage == "extract":
            await self._analysis.extract_processes(
                project_id, on_progress=_progress_callback,
            )

        elif stage == "generate-bpmn":
            await self._bpmn.generate_bpmn(
                project_id, on_progress=_progress_callback,
            )

        elif stage == "gap-analysis":
            await self._analysis.run_gap_analysis(
                project_id, on_progress=_progress_callback,
            )

        elif stage == "generate-tobe":
            await self._analysis.generate_tobe(
                project_id, on_progress=_progress_callback,
            )

        elif stage == "generate-docs":
            await self._run_doc_generation(project_id, _progress_callback)

    async def _run_transcription(
        self,
        project_dir: ProjectDir,
        on_progress: Any,
    ) -> None:
        """Транскрибирует все аудиофайлы проекта."""
        audio_files = project_dir.list_audio_files()

        if not audio_files:
            # Если нет аудио, проверяем наличие готовых транскрипций
            existing = project_dir.list_transcripts()
            if existing:
                logger.info(
                    "Аудиофайлы отсутствуют, но найдены %d готовых транскрипций",
                    len(existing),
                )
                return
            raise NotFoundError(
                "Аудиофайлы не найдены в проекте. "
                "Загрузите аудиофайлы или импортируйте транскрипции.",
            )

        total = len(audio_files)
        for idx, audio_path in enumerate(audio_files):
            if on_progress:
                pct = (idx / total) * 100
                on_progress(pct, 100, f"Транскрипция: {audio_path.name}...")

            await self._transcription.transcribe_audio(
                project_dir, audio_path.name,
            )

        if on_progress:
            on_progress(100, 100, "Транскрипция завершена")

    async def _run_doc_generation(
        self,
        project_id: str,
        on_progress: Any,
    ) -> None:
        """Генерирует все выходные документы."""
        stages = [
            (0, "Генерация описания процессов...", self._export.export_process_doc),
            (25, "Генерация требований (Excel)...", self._export.export_requirements_excel),
            (50, "Генерация требований (Word)...", self._export.export_requirements_word),
            (75, "Генерация GAP-отчёта...", self._export.export_gap_report),
        ]

        for pct, message, export_fn in stages:
            if on_progress:
                on_progress(pct, 100, message)
            try:
                await export_fn(project_id)
            except NotFoundError:
                logger.warning("Пропущен этап: %s (данные отсутствуют)", message)
                continue

        if on_progress:
            on_progress(100, 100, "Генерация документов завершена")

    # ------------------------------------------------------------------
    # Валидация зависимостей
    # ------------------------------------------------------------------

    def _validate_dependencies(
        self,
        project_dir: ProjectDir,
        stage: str,
    ) -> None:
        """Проверяет, что все предыдущие стадии завершены.

        Raises:
            ValidationError: Если предыдущие стадии не завершены.
        """
        pipeline_state = self._load_pipeline_state(project_dir)
        completed = set(pipeline_state.get("completed_stages", []))

        stage_index = PIPELINE_STAGES.index(stage)
        required_stages = PIPELINE_STAGES[:stage_index]

        missing = [s for s in required_stages if s not in completed]

        if missing:
            missing_labels = [STAGE_LABELS.get(s, s) for s in missing]
            raise ValidationError(
                f"Невозможно запустить стадию «{STAGE_LABELS.get(stage, stage)}». "
                f"Сначала завершите: {', '.join(missing_labels)}",
                detail={
                    "stage": stage,
                    "missing_stages": missing,
                },
            )

    # ------------------------------------------------------------------
    # Управление состоянием конвейера
    # ------------------------------------------------------------------

    @staticmethod
    def _load_pipeline_state(project_dir: ProjectDir) -> dict[str, Any]:
        """Загружает состояние конвейера из project.json."""
        project_json = project_dir.root / "project.json"
        if not project_json.is_file():
            return {"completed_stages": []}

        try:
            with open(project_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("pipeline_state", {"completed_stages": []})
        except Exception:
            return {"completed_stages": []}

    @staticmethod
    def _save_pipeline_state(
        project_dir: ProjectDir,
        pipeline_state: dict[str, Any],
    ) -> None:
        """Сохраняет состояние конвейера в project.json."""
        project_json = project_dir.root / "project.json"

        try:
            if project_json.is_file():
                with open(project_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except Exception:
            data = {}

        data["pipeline_state"] = pipeline_state
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            with open(project_json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.error("Ошибка сохранения состояния конвейера: %s", exc)

    def _update_stage_status(
        self,
        project_dir: ProjectDir,
        stage: str,
        *,
        status: str,
        progress: int,
        error: str | None,
    ) -> None:
        """Обновляет статус конкретной стадии."""
        pipeline_state = self._load_pipeline_state(project_dir)
        pipeline_state["stage"] = stage
        pipeline_state[f"stage_{stage}"] = {
            "status": status,
            "progress": progress,
            "error": error,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_pipeline_state(project_dir, pipeline_state)

    def _mark_stage_completed(
        self,
        project_dir: ProjectDir,
        stage: str,
    ) -> None:
        """Отмечает стадию как завершённую."""
        pipeline_state = self._load_pipeline_state(project_dir)
        completed = pipeline_state.get("completed_stages", [])
        if stage not in completed:
            completed.append(stage)
        pipeline_state["completed_stages"] = completed
        pipeline_state["progress"] = self._calculate_overall_progress(completed)
        self._save_pipeline_state(project_dir, pipeline_state)

    @staticmethod
    def _calculate_overall_progress(completed_stages: list[str]) -> int:
        """Вычисляет общий прогресс конвейера в процентах."""
        total = len(PIPELINE_STAGES)
        if total == 0:
            return 0
        done = sum(1 for s in completed_stages if s in PIPELINE_STAGES)
        return int((done / total) * 100)

    @staticmethod
    def _ensure_project_exists(project_id: str) -> ProjectDir:
        """Проверяет существование проекта."""
        project_dir = get_project_dir(project_id)
        if not project_dir.exists():
            raise NotFoundError(
                f"Проект не найден: {project_id}",
                detail={"project_id": project_id},
            )
        return project_dir
