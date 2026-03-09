"""Модуль транскрипции аудио.

Предоставляет инструменты для предобработки аудиофайлов,
распознавания речи через faster-whisper и форматирования
результатов транскрипции.
"""

from app.transcription.formatter import (
    DialogueLine,
    TranscriptFormatter,
    TranscriptionMetadata,
)
from app.transcription.preprocessor import AudioInfo, AudioPreprocessor
from app.transcription.transcriber import Segment, Transcriber, TranscriptionResult

__all__ = [
    # Preprocessor
    "AudioPreprocessor",
    "AudioInfo",
    # Transcriber
    "Transcriber",
    "TranscriptionResult",
    "Segment",
    # Formatter
    "TranscriptFormatter",
    "DialogueLine",
    "TranscriptionMetadata",
]
