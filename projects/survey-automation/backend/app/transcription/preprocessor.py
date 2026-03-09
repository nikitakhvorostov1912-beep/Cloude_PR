"""Препроцессор аудиофайлов на основе FFmpeg.

Выполняет нормализацию громкости, конвертацию в формат,
пригодный для Whisper (16 кГц, моно, WAV), а также
разбиение длинных записей на фрагменты.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Final

from pydantic import BaseModel, Field

from app.exceptions import ProcessingError

logger = logging.getLogger(__name__)

# Максимальная допустимая длительность аудио (6 часов)
_MAX_DURATION_SECONDS: Final[int] = 6 * 60 * 60

# Расширения аудиофайлов, допускаемые к обработке
SUPPORTED_AUDIO_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".aac", ".wma", ".opus"}
)


# ------------------------------------------------------------------
# Модели данных
# ------------------------------------------------------------------


class AudioInfo(BaseModel):
    """Информация об аудиофайле, полученная через ffprobe."""

    path: Path = Field(description="Путь к аудиофайлу")
    duration: float = Field(ge=0, description="Длительность в секундах")
    format_name: str = Field(description="Формат контейнера (wav, mp3 и т.д.)")
    channels: int = Field(ge=0, description="Количество каналов")
    sample_rate: int = Field(ge=0, description="Частота дискретизации (Гц)")
    codec: str = Field(default="unknown", description="Аудиокодек")
    bit_rate: int | None = Field(default=None, description="Битрейт (бит/с)")
    file_size: int = Field(ge=0, description="Размер файла в байтах")


# ------------------------------------------------------------------
# Основной класс
# ------------------------------------------------------------------


class AudioPreprocessor:
    """Предварительная обработка аудиофайлов через FFmpeg.

    Предоставляет методы для нормализации громкости, получения метаданных
    аудио и разбиения длинных записей на фрагменты заданной длительности.

    Attributes:
        target_sample_rate: Целевая частота дискретизации (по умолчанию 16000 Гц).
        target_channels: Целевое количество каналов (по умолчанию 1 — моно).
    """

    def __init__(
        self,
        target_sample_rate: int = 16000,
        target_channels: int = 1,
    ) -> None:
        self.target_sample_rate: Final[int] = target_sample_rate
        self.target_channels: Final[int] = target_channels
        self._verify_ffmpeg()

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def normalize_audio(self, input_path: Path) -> Path:
        """Нормализует громкость и конвертирует аудио в WAV 16 кГц моно.

        Выполняет двухпроходную нормализацию (loudnorm) для стабильного
        уровня громкости, затем конвертирует результат в формат,
        оптимальный для транскрипции Whisper.

        Args:
            input_path: Путь к исходному аудиофайлу.

        Returns:
            Путь к нормализованному WAV-файлу (размещается рядом с исходным
            с суффиксом ``_normalized.wav``).

        Raises:
            ProcessingError: Если файл не найден, формат не поддерживается
                или FFmpeg вернул ошибку.
        """
        self._validate_audio_path(input_path)

        output_path = input_path.parent / f"{input_path.stem}_normalized.wav"

        # Первый проход — анализ громкости
        loudnorm_stats = self._analyze_loudness(input_path)

        # Второй проход — нормализация + конвертация
        cmd: list[str] = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-af", (
                f"loudnorm=I=-16:TP=-1.5:LRA=11:"
                f"measured_I={loudnorm_stats['input_i']}:"
                f"measured_TP={loudnorm_stats['input_tp']}:"
                f"measured_LRA={loudnorm_stats['input_lra']}:"
                f"measured_thresh={loudnorm_stats['input_thresh']}:"
                f"offset={loudnorm_stats['target_offset']}:"
                f"linear=true:print_format=summary"
            ),
            "-ar", str(self.target_sample_rate),
            "-ac", str(self.target_channels),
            "-c:a", "pcm_s16le",
            "-f", "wav",
            str(output_path),
        ]

        self._run_ffmpeg(cmd, error_msg="Ошибка нормализации аудио")

        logger.info(
            "Аудио нормализовано: %s -> %s",
            input_path.name,
            output_path.name,
        )
        return output_path

    def get_audio_info(self, path: Path) -> AudioInfo:
        """Получает метаданные аудиофайла через ffprobe.

        Args:
            path: Путь к аудиофайлу.

        Returns:
            AudioInfo с полной информацией об аудио.

        Raises:
            ProcessingError: Если файл не найден или ffprobe не смог
                прочитать метаданные.
        """
        self._validate_audio_path(path)

        cmd: list[str] = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]

        result = self._run_ffmpeg(
            cmd,
            error_msg="Ошибка получения информации об аудиофайле",
            capture_stdout=True,
        )

        try:
            probe_data = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ProcessingError(
                "Не удалось разобрать метаданные аудиофайла",
                detail=str(exc),
            ) from exc

        return self._parse_probe_data(probe_data, path)

    def split_audio(
        self,
        path: Path,
        chunk_seconds: int = 600,
    ) -> list[Path]:
        """Разбивает длинный аудиофайл на фрагменты заданной длительности.

        Фрагменты сохраняются в формате WAV рядом с исходным файлом
        с суффиксами ``_chunk_001.wav``, ``_chunk_002.wav`` и т.д.

        Args:
            path: Путь к аудиофайлу.
            chunk_seconds: Длительность одного фрагмента в секундах
                (по умолчанию 600 — 10 минут).

        Returns:
            Список путей к фрагментам, отсортированный по порядку.

        Raises:
            ProcessingError: Если файл не найден, слишком длинный,
                или произошла ошибка FFmpeg.
        """
        if chunk_seconds < 10:
            raise ProcessingError(
                "Минимальная длительность фрагмента — 10 секунд",
                detail=f"Указано: {chunk_seconds}",
            )

        info = self.get_audio_info(path)

        if info.duration > _MAX_DURATION_SECONDS:
            raise ProcessingError(
                "Аудиофайл слишком длинный для обработки",
                detail=(
                    f"Длительность: {info.duration:.0f} сек., "
                    f"максимум: {_MAX_DURATION_SECONDS} сек."
                ),
            )

        # Если файл короче одного фрагмента — возвращаем как есть
        if info.duration <= chunk_seconds:
            logger.info(
                "Аудио короче %d сек., разбиение не требуется: %s",
                chunk_seconds,
                path.name,
            )
            return [path]

        total_chunks = int(info.duration // chunk_seconds) + (
            1 if info.duration % chunk_seconds > 0 else 0
        )

        output_dir = path.parent
        chunks: list[Path] = []

        for i in range(total_chunks):
            start_time = i * chunk_seconds
            chunk_path = output_dir / f"{path.stem}_chunk_{i + 1:03d}.wav"

            cmd: list[str] = [
                "ffmpeg",
                "-y",
                "-i", str(path),
                "-ss", str(start_time),
                "-t", str(chunk_seconds),
                "-ar", str(self.target_sample_rate),
                "-ac", str(self.target_channels),
                "-c:a", "pcm_s16le",
                "-f", "wav",
                str(chunk_path),
            ]

            self._run_ffmpeg(
                cmd,
                error_msg=f"Ошибка при нарезке фрагмента {i + 1}/{total_chunks}",
            )
            chunks.append(chunk_path)

        logger.info(
            "Аудио разбито на %d фрагментов по %d сек.: %s",
            len(chunks),
            chunk_seconds,
            path.name,
        )
        return chunks

    # ------------------------------------------------------------------
    # Приватные методы
    # ------------------------------------------------------------------

    def _verify_ffmpeg(self) -> None:
        """Проверяет наличие FFmpeg и ffprobe в системе."""
        for tool in ("ffmpeg", "ffprobe"):
            if shutil.which(tool) is None:
                raise ProcessingError(
                    f"Утилита {tool} не найдена в системе. "
                    f"Установите FFmpeg: https://ffmpeg.org/download.html",
                )

    def _validate_audio_path(self, path: Path) -> None:
        """Проверяет существование файла и допустимость его расширения."""
        if not path.exists():
            raise ProcessingError(
                "Аудиофайл не найден",
                detail=str(path),
            )
        if not path.is_file():
            raise ProcessingError(
                "Указанный путь не является файлом",
                detail=str(path),
            )
        if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            raise ProcessingError(
                f"Формат аудио «{path.suffix}» не поддерживается",
                detail=f"Поддерживаемые форматы: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}",
            )

    def _analyze_loudness(self, input_path: Path) -> dict[str, str]:
        """Первый проход loudnorm — анализ уровня громкости."""
        cmd: list[str] = [
            "ffmpeg",
            "-i", str(input_path),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
            "-f", "null",
            "-",
        ]

        result = self._run_ffmpeg(
            cmd,
            error_msg="Ошибка анализа громкости аудио",
            capture_stdout=True,
        )

        # loudnorm выводит JSON-статистику в stderr
        stderr_text = result.stderr or ""
        return self._extract_loudnorm_stats(stderr_text)

    def _extract_loudnorm_stats(self, stderr: str) -> dict[str, str]:
        """Извлекает JSON-статистику loudnorm из stderr FFmpeg."""
        # Ищем JSON-блок в выводе
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1

        if json_start == -1 or json_end <= json_start:
            raise ProcessingError(
                "Не удалось получить статистику громкости из FFmpeg",
                detail="JSON-блок loudnorm не найден в выводе",
            )

        try:
            stats = json.loads(stderr[json_start:json_end])
        except json.JSONDecodeError as exc:
            raise ProcessingError(
                "Не удалось разобрать статистику громкости",
                detail=str(exc),
            ) from exc

        required_keys = {
            "input_i", "input_tp", "input_lra",
            "input_thresh", "target_offset",
        }
        missing = required_keys - set(stats.keys())
        if missing:
            raise ProcessingError(
                "Неполная статистика громкости от FFmpeg",
                detail=f"Отсутствуют ключи: {', '.join(sorted(missing))}",
            )

        return stats

    def _parse_probe_data(self, data: dict, path: Path) -> AudioInfo:
        """Парсит вывод ffprobe в структуру AudioInfo."""
        fmt = data.get("format", {})
        streams = data.get("streams", [])

        # Ищем первый аудиопоток
        audio_stream: dict = {}
        for stream in streams:
            if stream.get("codec_type") == "audio":
                audio_stream = stream
                break

        if not audio_stream and not fmt:
            raise ProcessingError(
                "Не удалось определить параметры аудиофайла",
                detail=f"ffprobe не вернул данные о потоках: {path}",
            )

        try:
            duration = float(fmt.get("duration", 0))
        except (ValueError, TypeError):
            duration = 0.0

        try:
            sample_rate = int(audio_stream.get("sample_rate", 0))
        except (ValueError, TypeError):
            sample_rate = 0

        try:
            channels = int(audio_stream.get("channels", 0))
        except (ValueError, TypeError):
            channels = 0

        bit_rate_raw = fmt.get("bit_rate")
        bit_rate: int | None = None
        if bit_rate_raw is not None:
            try:
                bit_rate = int(bit_rate_raw)
            except (ValueError, TypeError):
                bit_rate = None

        try:
            file_size = int(fmt.get("size", 0))
        except (ValueError, TypeError):
            file_size = path.stat().st_size if path.exists() else 0

        return AudioInfo(
            path=path,
            duration=duration,
            format_name=fmt.get("format_name", "unknown"),
            channels=channels,
            sample_rate=sample_rate,
            codec=audio_stream.get("codec_name", "unknown"),
            bit_rate=bit_rate,
            file_size=file_size,
        )

    @staticmethod
    def _run_ffmpeg(
        cmd: list[str],
        *,
        error_msg: str,
        capture_stdout: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Запускает команду FFmpeg/ffprobe и обрабатывает ошибки.

        Args:
            cmd: Команда и аргументы для subprocess.run.
            error_msg: Сообщение об ошибке на русском для пользователя.
            capture_stdout: Если True, захватывает stdout (для ffprobe).

        Returns:
            Результат выполнения команды.

        Raises:
            ProcessingError: При ошибке выполнения или ненулевом коде возврата.
        """
        logger.debug("FFmpeg команда: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ProcessingError(
                "FFmpeg не найден. Убедитесь, что FFmpeg установлен и доступен в PATH",
                detail=str(exc),
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ProcessingError(
                "Превышено время ожидания обработки аудио (10 минут)",
                detail=str(exc),
            ) from exc
        except OSError as exc:
            raise ProcessingError(
                f"Системная ошибка при запуске FFmpeg: {exc}",
                detail=str(exc),
            ) from exc

        if result.returncode != 0:
            stderr_tail = (result.stderr or "")[-500:]
            logger.error(
                "FFmpeg ошибка (код %d): %s",
                result.returncode,
                stderr_tail,
            )
            raise ProcessingError(
                error_msg,
                detail=f"FFmpeg код возврата: {result.returncode}. "
                       f"Вывод: {stderr_tail}",
            )

        return result
