"""Запись аудио и транскрипта диалога.

Записывает обе стороны диалога:
  - input: аудио от клиента (PCM 16-bit 8kHz)
  - output: аудио от агента (PCM 16-bit 8kHz)

Сохраняет:
  - data/recordings/{call_id}/input.pcm
  - data/recordings/{call_id}/output.pcm
  - data/recordings/{call_id}/combined.wav
  - data/transcripts/{call_id}.json
"""
from __future__ import annotations

import json
import logging
import struct
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data")
SAMPLE_RATE = 8000
CHANNELS = 1
BITS_PER_SAMPLE = 16


class AudioRecorder:
    """Запись аудио диалога.

    Usage:
        recorder = AudioRecorder("call-001")
        recorder.feed_input(client_audio_chunk)
        recorder.feed_output(agent_audio_chunk)
        result = await recorder.finalize()
    """

    def __init__(
        self,
        call_id: str,
        *,
        data_dir: Path | None = None,
    ) -> None:
        self._call_id = call_id
        self._data_dir = data_dir or DEFAULT_DATA_DIR
        self._input_buffer = bytearray()
        self._output_buffer = bytearray()
        self._messages: list[dict] = []
        self._started_at = time.time()

    def feed_input(self, chunk: bytes) -> None:
        """Добавляет аудио от клиента."""
        self._input_buffer.extend(chunk)

    def feed_output(self, chunk: bytes) -> None:
        """Добавляет аудио от агента."""
        self._output_buffer.extend(chunk)

    def add_message(
        self,
        role: str,
        text: str,
        *,
        timestamp: float | None = None,
        confidence: float | None = None,
    ) -> None:
        """Добавляет сообщение в транскрипт."""
        msg: dict = {
            "role": role,
            "text": text,
            "timestamp": timestamp or time.time(),
        }
        if confidence is not None:
            msg["confidence"] = confidence
        self._messages.append(msg)

    async def finalize(self) -> dict:
        """Финализирует запись и сохраняет файлы.

        Returns:
            Словарь с путями к файлам и метаданными.
        """
        recording_dir = self._data_dir / "recordings" / self._call_id
        recording_dir.mkdir(parents=True, exist_ok=True)

        transcript_dir = self._data_dir / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)

        result: dict = {
            "call_id": self._call_id,
            "duration_seconds": int(time.time() - self._started_at),
            "input_bytes": len(self._input_buffer),
            "output_bytes": len(self._output_buffer),
        }

        # Сохраняем raw PCM
        if self._input_buffer:
            input_path = recording_dir / "input.pcm"
            input_path.write_bytes(self._input_buffer)
            result["input_path"] = str(input_path)

        if self._output_buffer:
            output_path = recording_dir / "output.pcm"
            output_path.write_bytes(self._output_buffer)
            result["output_path"] = str(output_path)

        # Создаём WAV из объединённого аудио
        if self._input_buffer or self._output_buffer:
            combined_path = recording_dir / "combined.wav"
            combined_pcm = self._mix_audio(
                bytes(self._input_buffer),
                bytes(self._output_buffer),
            )
            wav_data = self._pcm_to_wav(combined_pcm)
            combined_path.write_bytes(wav_data)
            result["combined_path"] = str(combined_path)

        # Сохраняем транскрипт
        transcript_path = transcript_dir / f"{self._call_id}.json"
        transcript = {
            "call_id": self._call_id,
            "started_at": self._started_at,
            "duration_seconds": result["duration_seconds"],
            "messages": self._messages,
        }
        transcript_path.write_text(
            json.dumps(transcript, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result["transcript_path"] = str(transcript_path)

        logger.info(
            "Запись сохранена [%s]: input=%d bytes, output=%d bytes",
            self._call_id,
            len(self._input_buffer),
            len(self._output_buffer),
        )

        return result

    @staticmethod
    def _mix_audio(input_pcm: bytes, output_pcm: bytes) -> bytes:
        """Микширует два PCM-потока (16-bit signed, mono).

        Выравнивает длину по максимальному, складывает сэмплы
        с clipping prevention.
        """
        n_input = len(input_pcm) // 2
        n_output = len(output_pcm) // 2
        max_samples = max(n_input, n_output)

        if max_samples == 0:
            return b""

        # Распаковываем
        input_samples = list(struct.unpack(f"<{n_input}h", input_pcm[: n_input * 2]))
        output_samples = list(
            struct.unpack(f"<{n_output}h", output_pcm[: n_output * 2])
        )

        # Дополняем нулями
        input_samples.extend([0] * (max_samples - n_input))
        output_samples.extend([0] * (max_samples - n_output))

        # Микшируем с ограничением
        mixed = []
        for i in range(max_samples):
            s = input_samples[i] + output_samples[i]
            s = max(-32768, min(32767, s))
            mixed.append(s)

        return struct.pack(f"<{max_samples}h", *mixed)

    @staticmethod
    def _pcm_to_wav(pcm_data: bytes) -> bytes:
        """Конвертирует raw PCM в WAV формат."""
        byte_rate = SAMPLE_RATE * CHANNELS * BITS_PER_SAMPLE // 8
        block_align = CHANNELS * BITS_PER_SAMPLE // 8
        data_size = len(pcm_data)

        # WAV header (44 bytes)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,  # ChunkSize
            b"WAVE",
            b"fmt ",
            16,  # Subchunk1Size (PCM)
            1,  # AudioFormat (PCM)
            CHANNELS,
            SAMPLE_RATE,
            byte_rate,
            block_align,
            BITS_PER_SAMPLE,
            b"data",
            data_size,
        )

        return header + pcm_data
