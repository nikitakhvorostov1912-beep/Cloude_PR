"""Транскрипция аудио с помощью faster-whisper.

Модуль обеспечивает загрузку модели Whisper, распознавание речи
с поддержкой GPU/CPU-фоллбэка и формирование структурированных
результатов транскрипции с временными метками.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable, Protocol

from pydantic import BaseModel, Field

from app.config import TranscriptionConfig, get_config
from app.exceptions import ProcessingError

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Модели данных
# ------------------------------------------------------------------


class Segment(BaseModel):
    """Один сегмент транскрипции с временными метками."""

    start: float = Field(ge=0, description="Начало сегмента (секунды)")
    end: float = Field(ge=0, description="Конец сегмента (секунды)")
    text: str = Field(description="Распознанный текст сегмента")
    speaker: str | None = Field(
        default=None,
        description="Идентификатор говорящего (если определён)",
    )

    @property
    def duration(self) -> float:
        """Длительность сегмента в секундах."""
        return self.end - self.start


class TranscriptionResult(BaseModel):
    """Полный результат транскрипции аудиофайла."""

    segments: list[Segment] = Field(
        default_factory=list,
        description="Список сегментов с временными метками",
    )
    full_text: str = Field(default="", description="Полный текст транскрипции")
    language: str = Field(default="ru", description="Определённый язык")
    duration: float = Field(
        default=0.0,
        ge=0,
        description="Общая длительность аудио (секунды)",
    )

    @property
    def segments_count(self) -> int:
        """Количество сегментов в транскрипции."""
        return len(self.segments)

    @property
    def is_empty(self) -> bool:
        """Проверяет, пуста ли транскрипция."""
        return len(self.segments) == 0 and not self.full_text.strip()


# ------------------------------------------------------------------
# Протокол обратного вызова прогресса
# ------------------------------------------------------------------


class ProgressCallback(Protocol):
    """Протокол функции обратного вызова для отчёта о прогрессе."""

    def __call__(self, current: float, total: float, message: str) -> None:
        """Вызывается при обновлении прогресса.

        Args:
            current: Текущее значение прогресса (секунды обработанного аудио).
            total: Общее значение (длительность аудио в секундах).
            message: Текстовое описание текущего этапа.
        """
        ...


# ------------------------------------------------------------------
# Основной класс
# ------------------------------------------------------------------


class Transcriber:
    """Транскрибер аудио на основе faster-whisper.

    Поддерживает ленивую загрузку модели, автоматический фоллбэк
    с GPU на CPU при ошибках CUDA, а также обратные вызовы прогресса.

    Args:
        config: Конфигурация транскрипции. Если не указана,
            загружается из config.yaml.
    """

    def __init__(self, config: TranscriptionConfig | None = None) -> None:
        self._config = config or get_config().transcription
        self._model = None
        self._actual_device: str = self._config.device
        self._actual_compute_type: str = self._config.compute_type

    # ------------------------------------------------------------------
    # Свойства
    # ------------------------------------------------------------------

    @property
    def config(self) -> TranscriptionConfig:
        """Текущая конфигурация транскрипции."""
        return self._config

    @property
    def is_model_loaded(self) -> bool:
        """Загружена ли модель в память."""
        return self._model is not None

    @property
    def actual_device(self) -> str:
        """Фактическое устройство, используемое для инференса."""
        return self._actual_device

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def load_model(self) -> None:
        """Загружает модель Whisper в память.

        При ошибке загрузки на GPU автоматически переключается на CPU.

        Raises:
            ProcessingError: Если модель не удалось загрузить
                ни на GPU, ни на CPU.
        """
        if self._model is not None:
            logger.debug("Модель уже загружена, пропускаем повторную загрузку")
            return

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ProcessingError(
                "Библиотека faster-whisper не установлена. "
                "Выполните: pip install faster-whisper",
                detail=str(exc),
            ) from exc

        # Попытка загрузки на указанном устройстве
        if self._config.device == "cuda":
            try:
                self._model = self._create_model(
                    WhisperModel,
                    device="cuda",
                    compute_type=self._config.compute_type,
                )
                self._actual_device = "cuda"
                self._actual_compute_type = self._config.compute_type
                logger.info(
                    "Модель Whisper '%s' загружена на GPU (compute_type=%s)",
                    self._config.model_size,
                    self._config.compute_type,
                )
                return
            except Exception as gpu_err:
                logger.warning(
                    "Не удалось загрузить модель на GPU: %s. "
                    "Переключение на CPU.",
                    gpu_err,
                )

        # Фоллбэк на CPU
        try:
            self._model = self._create_model(
                WhisperModel,
                device="cpu",
                compute_type="int8",
            )
            self._actual_device = "cpu"
            self._actual_compute_type = "int8"
            logger.info(
                "Модель Whisper '%s' загружена на CPU (compute_type=int8)",
                self._config.model_size,
            )
        except Exception as cpu_err:
            raise ProcessingError(
                "Не удалось загрузить модель Whisper. "
                "Проверьте установку faster-whisper и наличие свободной памяти.",
                detail=str(cpu_err),
            ) from cpu_err

    def transcribe(
        self,
        audio_path: Path,
        *,
        progress_callback: Callable[[float, float, str], None] | None = None,
    ) -> TranscriptionResult:
        """Транскрибирует аудиофайл.

        Загружает модель при первом вызове (ленивая инициализация),
        выполняет распознавание речи и возвращает структурированный
        результат с сегментами и временными метками.

        Args:
            audio_path: Путь к аудиофайлу (предпочтительно WAV 16 кГц моно).
            progress_callback: Опциональная функция обратного вызова
                для отчёта о прогрессе транскрипции.

        Returns:
            TranscriptionResult с сегментами, полным текстом,
            языком и длительностью.

        Raises:
            ProcessingError: Если файл не найден, модель не загрузилась,
                или произошла ошибка при транскрипции.
        """
        self._validate_audio_path(audio_path)

        # Ленивая загрузка модели
        if self._model is None:
            if progress_callback:
                progress_callback(0, 100, "Загрузка модели Whisper...")
            self.load_model()

        logger.info("Начало транскрипции: %s", audio_path.name)
        start_time = time.monotonic()

        if progress_callback:
            progress_callback(0, 100, "Распознавание речи...")

        try:
            segments_iter, info = self._model.transcribe(
                str(audio_path),
                language=self._config.language,
                beam_size=self._config.beam_size,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
                word_timestamps=False,
            )
        except Exception as exc:
            raise ProcessingError(
                "Ошибка при транскрипции аудио. "
                "Проверьте формат файла и целостность аудиозаписи.",
                detail=str(exc),
            ) from exc

        total_duration = getattr(info, "duration", 0.0) or 0.0
        detected_language = getattr(info, "language", self._config.language)

        # Собираем сегменты
        segments: list[Segment] = []
        try:
            for seg in segments_iter:
                text = seg.text.strip()
                if not text:
                    continue

                segments.append(Segment(
                    start=round(seg.start, 3),
                    end=round(seg.end, 3),
                    text=text,
                ))

                if progress_callback and total_duration > 0:
                    progress = min(seg.end / total_duration * 100, 99.0)
                    progress_callback(
                        progress,
                        100,
                        f"Обработано {seg.end:.0f}/{total_duration:.0f} сек.",
                    )
        except Exception as exc:
            raise ProcessingError(
                "Ошибка при обработке результатов транскрипции",
                detail=str(exc),
            ) from exc

        # Формируем полный текст
        full_text = " ".join(seg.text for seg in segments)

        elapsed = time.monotonic() - start_time
        logger.info(
            "Транскрипция завершена: %s "
            "(сегментов: %d, длительность аудио: %.1f сек., "
            "время обработки: %.1f сек., устройство: %s)",
            audio_path.name,
            len(segments),
            total_duration,
            elapsed,
            self._actual_device,
        )

        if progress_callback:
            progress_callback(100, 100, "Транскрипция завершена")

        return TranscriptionResult(
            segments=segments,
            full_text=full_text,
            language=detected_language or self._config.language,
            duration=total_duration,
        )

    def unload_model(self) -> None:
        """Выгружает модель из памяти для освобождения ресурсов."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Модель Whisper выгружена из памяти")

            # Попытка очистить кэш CUDA
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.debug("Кэш CUDA очищен")
            except ImportError:
                pass

    # ------------------------------------------------------------------
    # Приватные методы
    # ------------------------------------------------------------------

    def _create_model(
        self,
        model_class: type,
        *,
        device: str,
        compute_type: str,
    ) -> object:
        """Создаёт экземпляр WhisperModel с указанными параметрами.

        Args:
            model_class: Класс WhisperModel из faster_whisper.
            device: Устройство ('cuda' или 'cpu').
            compute_type: Тип вычислений ('float16', 'int8' и т.д.).

        Returns:
            Загруженная модель Whisper.
        """
        logger.info(
            "Загрузка модели Whisper: model_size=%s, device=%s, compute_type=%s",
            self._config.model_size,
            device,
            compute_type,
        )
        return model_class(
            self._config.model_size,
            device=device,
            compute_type=compute_type,
        )

    @staticmethod
    def _validate_audio_path(audio_path: Path) -> None:
        """Проверяет существование и доступность аудиофайла."""
        if not audio_path.exists():
            raise ProcessingError(
                "Аудиофайл не найден",
                detail=str(audio_path),
            )
        if not audio_path.is_file():
            raise ProcessingError(
                "Указанный путь не является файлом",
                detail=str(audio_path),
            )
        if audio_path.stat().st_size == 0:
            raise ProcessingError(
                "Аудиофайл пуст (размер 0 байт)",
                detail=str(audio_path),
            )
