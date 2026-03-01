"""Сервис оркестрации транскрипции аудио.

Координирует полный цикл транскрипции: предобработку аудио,
распознавание речи, форматирование и сохранение результатов.
Также поддерживает импорт готовых транскрипций из текста и JSON.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from app.config import ProjectDir
from app.exceptions import NotFoundError, ProcessingError, ValidationError
from app.transcription.formatter import TranscriptFormatter
from app.transcription.preprocessor import AudioPreprocessor
from app.transcription.transcriber import Transcriber, TranscriptionResult

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Оркестрация конвейера транскрипции.

    Управляет полным жизненным циклом транскрипции от загрузки аудио
    до сохранения структурированного результата.

    Args:
        transcriber: Экземпляр транскрибера Whisper.
        preprocessor: Экземпляр препроцессора аудио.
        formatter: Экземпляр форматировщика транскрипций.
    """

    def __init__(
        self,
        transcriber: Transcriber | None = None,
        preprocessor: AudioPreprocessor | None = None,
        formatter: TranscriptFormatter | None = None,
    ) -> None:
        self._transcriber = transcriber or Transcriber()
        self._preprocessor = preprocessor
        self._formatter = formatter or TranscriptFormatter()

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    async def transcribe_audio(
        self,
        project_dir: ProjectDir,
        audio_filename: str,
        on_progress: Callable[[float, float, str], None] | None = None,
    ) -> dict[str, Any]:
        """Выполняет полный цикл транскрипции аудиофайла.

        Этапы:
            1. Поиск аудиофайла в директории проекта.
            2. Предобработка (нормализация, конвертация).
            3. Транскрипция через Whisper.
            4. Форматирование и сохранение результата.

        Args:
            project_dir: Директория проекта.
            audio_filename: Имя аудиофайла в директории audio/.
            on_progress: Опциональный колбэк прогресса (current, total, message).

        Returns:
            Словарь с данными транскрипции, включая метаданные и сегменты.

        Raises:
            NotFoundError: Если аудиофайл не найден.
            ProcessingError: При ошибке обработки аудио или транскрипции.
        """
        audio_path = project_dir.audio / audio_filename
        if not audio_path.is_file():
            raise NotFoundError(
                f"Аудиофайл не найден: {audio_filename}",
                detail=str(audio_path),
            )

        if on_progress:
            on_progress(0, 100, "Подготовка аудиофайла...")

        # Этап 1: Предобработка
        processed_path = audio_path
        if self._preprocessor is not None:
            try:
                if on_progress:
                    on_progress(5, 100, "Нормализация аудио...")
                processed_path = self._preprocessor.normalize_audio(audio_path)
            except ProcessingError:
                raise
            except Exception as exc:
                raise ProcessingError(
                    "Ошибка при предобработке аудиофайла",
                    detail=str(exc),
                ) from exc

        # Этап 2: Транскрипция
        if on_progress:
            on_progress(10, 100, "Запуск транскрипции...")

        def _transcription_progress(current: float, total: float, message: str) -> None:
            """Пересчитывает прогресс транскрипции в общий прогресс (10-90%)."""
            if on_progress:
                scaled = 10 + (current / max(total, 1)) * 80
                on_progress(scaled, 100, message)

        try:
            result: TranscriptionResult = self._transcriber.transcribe(
                processed_path,
                progress_callback=_transcription_progress,
            )
        except ProcessingError:
            raise
        except Exception as exc:
            raise ProcessingError(
                "Ошибка транскрипции аудиофайла",
                detail=str(exc),
            ) from exc

        if result.is_empty:
            raise ProcessingError(
                "Транскрипция не содержит распознанного текста",
                detail=f"Аудиофайл: {audio_filename}",
            )

        # Этап 3: Форматирование и сохранение
        if on_progress:
            on_progress(90, 100, "Сохранение результатов...")

        transcript_data = self._formatter.to_json(result, audio_file=audio_filename)
        transcript_id = Path(audio_filename).stem

        self._save_transcript(project_dir, transcript_id, transcript_data)

        # Сохраняем текстовую версию
        full_text = self._formatter.format_full_text(result)
        self._save_transcript_text(project_dir, transcript_id, full_text)

        if on_progress:
            on_progress(100, 100, "Транскрипция завершена")

        logger.info(
            "Транскрипция завершена: %s -> %s (%d сегментов)",
            audio_filename,
            transcript_id,
            result.segments_count,
        )
        return transcript_data

    async def import_transcript(
        self,
        project_dir: ProjectDir,
        text: str,
        filename: str,
    ) -> dict[str, Any]:
        """Импортирует транскрипцию из текста или JSON.

        Поддерживает формат:
            - JSON (dict с полями segments, full_text).
            - Диалог с таймкодами.
            - Диалог с метками спикеров.
            - Простой текст.

        Args:
            project_dir: Директория проекта.
            text: Содержимое файла транскрипции.
            filename: Исходное имя файла (для определения формата).

        Returns:
            Словарь с данными импортированной транскрипции.

        Raises:
            ValidationError: Если текст пуст или имеет некорректный формат.
            ProcessingError: При ошибке сохранения.
        """
        if not text or not text.strip():
            raise ValidationError(
                "Текст транскрипции пуст",
                detail=f"Файл: {filename}",
            )

        transcript_id = Path(filename).stem

        # Пробуем парсинг как JSON
        if filename.lower().endswith(".json"):
            try:
                data = json.loads(text)
                result = self._formatter.from_json(data)
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    "Некорректный формат JSON",
                    detail=str(exc),
                ) from exc
        else:
            result = self._formatter.from_text(text)

        if result.is_empty:
            raise ValidationError(
                "Не удалось извлечь текст из загруженного файла",
                detail=f"Файл: {filename}",
            )

        transcript_data = self._formatter.to_json(result, audio_file=filename)
        self._save_transcript(project_dir, transcript_id, transcript_data)

        # Сохраняем текстовую версию
        full_text = self._formatter.format_full_text(result)
        self._save_transcript_text(project_dir, transcript_id, full_text)

        logger.info(
            "Транскрипция импортирована: %s -> %s (%d сегментов)",
            filename,
            transcript_id,
            result.segments_count,
        )
        return transcript_data

    async def list_transcripts(
        self,
        project_dir: ProjectDir,
    ) -> list[dict[str, Any]]:
        """Возвращает список транскрипций проекта.

        Args:
            project_dir: Директория проекта.

        Returns:
            Список словарей с метаданными каждой транскрипции.
        """
        transcripts: list[dict[str, Any]] = []

        json_files = sorted(
            p for p in project_dir.transcripts.iterdir()
            if p.is_file() and p.suffix.lower() == ".json"
        ) if project_dir.transcripts.is_dir() else []

        for json_path in json_files:
            try:
                data = self._load_json_file(json_path)
                metadata = data.get("metadata", {})
                transcripts.append({
                    "id": json_path.stem,
                    "audio_file": metadata.get("audio_file"),
                    "duration": metadata.get("duration", 0),
                    "segments_count": metadata.get("segments_count", 0),
                    "language": metadata.get("language", "ru"),
                    "created_at": metadata.get("created_at", ""),
                })
            except Exception as exc:
                logger.warning(
                    "Не удалось прочитать транскрипцию %s: %s",
                    json_path.name,
                    exc,
                )
                continue

        return transcripts

    async def get_transcript(
        self,
        project_dir: ProjectDir,
        transcript_id: str,
    ) -> dict[str, Any]:
        """Возвращает полные данные транскрипции по идентификатору.

        Args:
            project_dir: Директория проекта.
            transcript_id: Идентификатор транскрипции (имя файла без расширения).

        Returns:
            Полные данные транскрипции.

        Raises:
            NotFoundError: Если транскрипция не найдена.
        """
        json_path = project_dir.get_transcript_path(transcript_id, ext=".json")
        if not json_path.is_file():
            raise NotFoundError(
                f"Транскрипция не найдена: {transcript_id}",
                detail=str(json_path),
            )
        return self._load_json_file(json_path)

    # ------------------------------------------------------------------
    # Приватные методы
    # ------------------------------------------------------------------

    def _save_transcript(
        self,
        project_dir: ProjectDir,
        transcript_id: str,
        data: dict[str, Any],
    ) -> Path:
        """Сохраняет данные транскрипции в JSON-файл."""
        project_dir.ensure_dirs()
        json_path = project_dir.get_transcript_path(transcript_id, ext=".json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise ProcessingError(
                "Ошибка сохранения транскрипции",
                detail=str(exc),
            ) from exc
        return json_path

    def _save_transcript_text(
        self,
        project_dir: ProjectDir,
        transcript_id: str,
        text: str,
    ) -> Path:
        """Сохраняет текстовую версию транскрипции."""
        project_dir.ensure_dirs()
        txt_path = project_dir.get_transcript_path(transcript_id, ext=".txt")
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError as exc:
            raise ProcessingError(
                "Ошибка сохранения текста транскрипции",
                detail=str(exc),
            ) from exc
        return txt_path

    @staticmethod
    def _load_json_file(path: Path) -> dict[str, Any]:
        """Загружает и парсит JSON-файл."""
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
