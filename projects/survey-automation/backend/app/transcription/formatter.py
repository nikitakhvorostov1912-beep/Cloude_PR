"""Форматирование и сериализация результатов транскрипции.

Обеспечивает преобразование TranscriptionResult в различные форматы
(диалог, текст, JSON), а также обратный парсинг из JSON и plain text.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.exceptions import ValidationError
from app.transcription.transcriber import Segment, TranscriptionResult

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Модели данных
# ------------------------------------------------------------------


class DialogueLine(BaseModel):
    """Одна реплика в диалоговом формате."""

    speaker: str = Field(description="Имя или метка говорящего")
    text: str = Field(description="Текст реплики")
    start: float = Field(ge=0, description="Начало реплики (секунды)")
    end: float = Field(ge=0, description="Конец реплики (секунды)")


class TranscriptionMetadata(BaseModel):
    """Метаданные транскрипции для сериализации."""

    audio_file: str | None = Field(
        default=None, description="Имя исходного аудиофайла",
    )
    duration: float = Field(ge=0, description="Длительность аудио (секунды)")
    segments_count: int = Field(ge=0, description="Количество сегментов")
    speakers: list[str] = Field(
        default_factory=list, description="Список уникальных говорящих",
    )
    language: str = Field(default="ru", description="Язык транскрипции")
    created_at: str = Field(
        default="", description="Дата и время создания (ISO 8601)",
    )


# ------------------------------------------------------------------
# Основной класс
# ------------------------------------------------------------------


class TranscriptFormatter:
    """Форматирование и парсинг результатов транскрипции.

    Предоставляет методы для преобразования TranscriptionResult
    в диалоговый формат, полный текст, JSON-представление, а также
    обратный парсинг из JSON и plain text.

    Args:
        default_speaker: Метка говорящего по умолчанию, если speaker
            не определён в сегменте.
    """

    # Регулярное выражение для парсинга строк формата [ЧЧ:ММ:СС - ЧЧ:ММ:СС] Спикер: Текст
    _DIALOGUE_PATTERN: re.Pattern[str] = re.compile(
        r"^\[(\d{2}:\d{2}:\d{2})\s*[-–—]\s*(\d{2}:\d{2}:\d{2})\]\s*"
        r"(.+?):\s*(.+)$"
    )

    # Регулярное выражение для парсинга меток Спикер: Текст (без таймкодов)
    _SPEAKER_LABEL_PATTERN: re.Pattern[str] = re.compile(
        r"^(Спикер\s*\d+|Speaker\s*\d+|Интервьюер|Респондент|[А-ЯA-Z][а-яa-z]+):\s*(.+)$"
    )

    def __init__(self, default_speaker: str = "Спикер") -> None:
        self._default_speaker = default_speaker

    # ------------------------------------------------------------------
    # Форматирование
    # ------------------------------------------------------------------

    def format_dialogue(
        self,
        result: TranscriptionResult,
    ) -> list[DialogueLine]:
        """Преобразует результат транскрипции в список реплик диалога.

        Объединяет последовательные сегменты одного говорящего в единую
        реплику для более естественного представления диалога.

        Args:
            result: Результат транскрипции.

        Returns:
            Список реплик DialogueLine.
        """
        if result.is_empty:
            return []

        lines: list[DialogueLine] = []
        current_speaker: str | None = None
        current_texts: list[str] = []
        current_start: float = 0.0
        current_end: float = 0.0

        for segment in result.segments:
            speaker = segment.speaker or self._default_speaker

            if speaker == current_speaker and current_texts:
                # Продолжение реплики того же говорящего
                current_texts.append(segment.text)
                current_end = segment.end
            else:
                # Новый говорящий — сохраняем предыдущую реплику
                if current_texts and current_speaker is not None:
                    lines.append(DialogueLine(
                        speaker=current_speaker,
                        text=" ".join(current_texts),
                        start=current_start,
                        end=current_end,
                    ))
                current_speaker = speaker
                current_texts = [segment.text]
                current_start = segment.start
                current_end = segment.end

        # Последняя реплика
        if current_texts and current_speaker is not None:
            lines.append(DialogueLine(
                speaker=current_speaker,
                text=" ".join(current_texts),
                start=current_start,
                end=current_end,
            ))

        logger.debug(
            "Сформирован диалог: %d реплик из %d сегментов",
            len(lines),
            result.segments_count,
        )
        return lines

    def format_full_text(self, result: TranscriptionResult) -> str:
        """Форматирует результат транскрипции в полный текст.

        Если в сегментах есть информация о говорящих, текст оформляется
        с метками спикеров. Иначе — сплошной текст с разбивкой на абзацы.

        Args:
            result: Результат транскрипции.

        Returns:
            Отформатированный текст транскрипции.
        """
        if result.is_empty:
            return ""

        has_speakers = any(seg.speaker for seg in result.segments)

        if has_speakers:
            return self._format_with_speakers(result)
        return self._format_plain(result)

    def to_json(
        self,
        result: TranscriptionResult,
        *,
        audio_file: str | None = None,
    ) -> dict[str, Any]:
        """Сериализует результат транскрипции в словарь для JSON.

        Формирует полную структуру с метаданными, сегментами
        и отформатированным текстом.

        Args:
            result: Результат транскрипции.
            audio_file: Имя исходного аудиофайла (для метаданных).

        Returns:
            Словарь, готовый к сериализации в JSON.
        """
        speakers = sorted({
            seg.speaker
            for seg in result.segments
            if seg.speaker
        })

        metadata = TranscriptionMetadata(
            audio_file=audio_file,
            duration=result.duration,
            segments_count=result.segments_count,
            speakers=speakers,
            language=result.language,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        segments_data: list[dict[str, Any]] = []
        for seg in result.segments:
            seg_dict: dict[str, Any] = {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
            }
            if seg.speaker:
                seg_dict["speaker"] = seg.speaker
            segments_data.append(seg_dict)

        return {
            "metadata": metadata.model_dump(),
            "segments": segments_data,
            "full_text": result.full_text,
            "dialogue": [
                line.model_dump()
                for line in self.format_dialogue(result)
            ],
        }

    # ------------------------------------------------------------------
    # Парсинг
    # ------------------------------------------------------------------

    def from_json(self, data: dict[str, Any]) -> TranscriptionResult:
        """Восстанавливает TranscriptionResult из JSON-словаря.

        Поддерживает как формат, созданный методом to_json(),
        так и упрощённые структуры с минимальным набором полей.

        Args:
            data: Словарь с данными транскрипции.

        Returns:
            Восстановленный TranscriptionResult.

        Raises:
            ValidationError: Если структура данных некорректна.
        """
        if not isinstance(data, dict):
            raise ValidationError(
                "Ожидается JSON-объект (словарь) верхнего уровня",
                detail=f"Получен тип: {type(data).__name__}",
            )

        # Извлекаем сегменты
        raw_segments = data.get("segments", [])
        if not isinstance(raw_segments, list):
            raise ValidationError(
                "Поле 'segments' должно быть списком",
                detail=f"Получен тип: {type(raw_segments).__name__}",
            )

        segments: list[Segment] = []
        for i, raw_seg in enumerate(raw_segments):
            if not isinstance(raw_seg, dict):
                raise ValidationError(
                    f"Сегмент #{i + 1} должен быть объектом",
                    detail=f"Получен тип: {type(raw_seg).__name__}",
                )
            try:
                segments.append(Segment(
                    start=float(raw_seg.get("start", 0)),
                    end=float(raw_seg.get("end", 0)),
                    text=str(raw_seg.get("text", "")),
                    speaker=raw_seg.get("speaker"),
                ))
            except (ValueError, TypeError) as exc:
                raise ValidationError(
                    f"Ошибка парсинга сегмента #{i + 1}",
                    detail=str(exc),
                ) from exc

        # Извлекаем полный текст
        full_text = data.get("full_text", "")
        if not full_text and segments:
            full_text = " ".join(seg.text for seg in segments)

        # Извлекаем метаданные
        metadata = data.get("metadata", {})
        if isinstance(metadata, dict):
            language = metadata.get("language", data.get("language", "ru"))
            duration = metadata.get("duration", data.get("duration", 0.0))
        else:
            language = data.get("language", "ru")
            duration = data.get("duration", 0.0)

        # Если длительность не указана, вычисляем по последнему сегменту
        if not duration and segments:
            duration = max(seg.end for seg in segments)

        try:
            duration = float(duration)
        except (ValueError, TypeError):
            duration = 0.0

        logger.debug(
            "Загружена транскрипция из JSON: %d сегментов, "
            "длительность %.1f сек.",
            len(segments),
            duration,
        )

        return TranscriptionResult(
            segments=segments,
            full_text=str(full_text),
            language=str(language),
            duration=duration,
        )

    def from_text(self, text: str) -> TranscriptionResult:
        """Восстанавливает TranscriptionResult из plain text.

        Пытается распознать формат:
        1. Диалог с таймкодами: ``[00:00:00 - 00:01:30] Спикер: Текст``
        2. Диалог с метками: ``Спикер 1: Текст``
        3. Простой текст — разбивается на абзацы.

        Args:
            text: Текстовое содержимое транскрипции.

        Returns:
            TranscriptionResult, восстановленный из текста.

        Raises:
            ValidationError: Если текст пуст.
        """
        if not text or not text.strip():
            raise ValidationError(
                "Текст транскрипции пуст",
                detail="Загруженный файл не содержит текста",
            )

        text = text.strip()
        lines = text.splitlines()

        # Пробуем парсинг диалога с таймкодами
        segments = self._parse_timestamped_dialogue(lines)
        if segments:
            full_text = " ".join(seg.text for seg in segments)
            duration = max(seg.end for seg in segments) if segments else 0.0
            logger.debug(
                "Загружена транскрипция из текста (с таймкодами): "
                "%d сегментов",
                len(segments),
            )
            return TranscriptionResult(
                segments=segments,
                full_text=full_text,
                language="ru",
                duration=duration,
            )

        # Пробуем парсинг диалога с метками спикеров
        segments = self._parse_speaker_dialogue(lines)
        if segments:
            full_text = " ".join(seg.text for seg in segments)
            logger.debug(
                "Загружена транскрипция из текста (с метками): "
                "%d сегментов",
                len(segments),
            )
            return TranscriptionResult(
                segments=segments,
                full_text=full_text,
                language="ru",
                duration=0.0,
            )

        # Простой текст — разбиваем на абзацы
        segments = self._parse_plain_text(text)
        full_text = " ".join(seg.text for seg in segments) if segments else text
        logger.debug(
            "Загружена транскрипция из текста (plain): %d сегментов",
            len(segments),
        )
        return TranscriptionResult(
            segments=segments,
            full_text=full_text,
            language="ru",
            duration=0.0,
        )

    # ------------------------------------------------------------------
    # Вспомогательные: форматирование
    # ------------------------------------------------------------------

    def _format_with_speakers(self, result: TranscriptionResult) -> str:
        """Форматирует текст с метками говорящих и таймкодами."""
        dialogue = self.format_dialogue(result)
        lines: list[str] = []
        for line in dialogue:
            timestamp = self._format_timestamp_range(line.start, line.end)
            lines.append(f"[{timestamp}] {line.speaker}: {line.text}")
        return "\n\n".join(lines)

    def _format_plain(self, result: TranscriptionResult) -> str:
        """Форматирует текст сплошным потоком с разбивкой на абзацы."""
        paragraphs: list[str] = []
        current_paragraph: list[str] = []

        for i, seg in enumerate(result.segments):
            current_paragraph.append(seg.text)

            # Новый абзац каждые ~5 сегментов или при длинной паузе
            is_last = (i == len(result.segments) - 1)
            has_long_pause = (
                not is_last
                and result.segments[i + 1].start - seg.end > 2.0
            )

            if len(current_paragraph) >= 5 or has_long_pause or is_last:
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []

        return "\n\n".join(paragraphs)

    # ------------------------------------------------------------------
    # Вспомогательные: парсинг
    # ------------------------------------------------------------------

    def _parse_timestamped_dialogue(
        self,
        lines: list[str],
    ) -> list[Segment]:
        """Парсит строки формата [ЧЧ:ММ:СС - ЧЧ:ММ:СС] Спикер: Текст."""
        segments: list[Segment] = []
        matched_count = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = self._DIALOGUE_PATTERN.match(line)
            if match:
                start_str, end_str, speaker, text = match.groups()
                segments.append(Segment(
                    start=self._parse_timestamp(start_str),
                    end=self._parse_timestamp(end_str),
                    text=text.strip(),
                    speaker=speaker.strip(),
                ))
                matched_count += 1

        # Считаем формат валидным, если распознано >= 50% непустых строк
        non_empty_lines = sum(1 for line in lines if line.strip())
        if non_empty_lines > 0 and matched_count / non_empty_lines >= 0.5:
            return segments
        return []

    def _parse_speaker_dialogue(self, lines: list[str]) -> list[Segment]:
        """Парсит строки формата Спикер: Текст (без таймкодов)."""
        segments: list[Segment] = []
        matched_count = 0
        time_offset: float = 0.0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = self._SPEAKER_LABEL_PATTERN.match(line)
            if match:
                speaker, text = match.groups()
                # Примерная длительность: ~0.07 сек. на символ
                estimated_duration = len(text) * 0.07
                segments.append(Segment(
                    start=round(time_offset, 3),
                    end=round(time_offset + estimated_duration, 3),
                    text=text.strip(),
                    speaker=speaker.strip(),
                ))
                time_offset += estimated_duration + 0.5
                matched_count += 1

        non_empty_lines = sum(1 for line in lines if line.strip())
        if non_empty_lines > 0 and matched_count / non_empty_lines >= 0.5:
            return segments
        return []

    def _parse_plain_text(self, text: str) -> list[Segment]:
        """Разбивает простой текст на сегменты по абзацам."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        if not paragraphs:
            return [Segment(start=0, end=0, text=text.strip())] if text.strip() else []

        segments: list[Segment] = []
        time_offset: float = 0.0

        for para in paragraphs:
            estimated_duration = len(para) * 0.07
            segments.append(Segment(
                start=round(time_offset, 3),
                end=round(time_offset + estimated_duration, 3),
                text=para,
            ))
            time_offset += estimated_duration + 1.0

        return segments

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    @staticmethod
    def _format_timestamp_range(start: float, end: float) -> str:
        """Форматирует диапазон времени как ЧЧ:ММ:СС - ЧЧ:ММ:СС."""
        return (
            f"{TranscriptFormatter._seconds_to_timestamp(start)} - "
            f"{TranscriptFormatter._seconds_to_timestamp(end)}"
        )

    @staticmethod
    def _seconds_to_timestamp(seconds: float) -> str:
        """Преобразует секунды в строку формата ЧЧ:ММ:СС."""
        total = int(max(seconds, 0))
        hours = total // 3600
        minutes = (total % 3600) // 60
        secs = total % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _parse_timestamp(timestamp: str) -> float:
        """Парсит строку ЧЧ:ММ:СС в секунды."""
        parts = timestamp.strip().split(":")
        if len(parts) != 3:
            raise ValidationError(
                f"Некорректный формат таймкода: «{timestamp}»",
                detail="Ожидается формат ЧЧ:ММ:СС",
            )
        try:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError as exc:
            raise ValidationError(
                f"Некорректные числа в таймкоде: «{timestamp}»",
                detail=str(exc),
            ) from exc

        return float(hours * 3600 + minutes * 60 + seconds)
