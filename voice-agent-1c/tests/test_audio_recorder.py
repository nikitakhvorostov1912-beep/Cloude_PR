"""Тесты AudioRecorder."""
from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from services.audio_recorder import AudioRecorder


@pytest.fixture
def tmp_data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def recorder(tmp_data_dir):
    return AudioRecorder("call-001", data_dir=tmp_data_dir)


# --- Запись аудио ---


class TestAudioRecording:
    def test_feed_input(self, recorder):
        """feed_input добавляет данные в буфер."""
        recorder.feed_input(b"\x01\x02" * 100)
        assert len(recorder._input_buffer) == 200

    def test_feed_output(self, recorder):
        """feed_output добавляет данные в буфер."""
        recorder.feed_output(b"\x03\x04" * 100)
        assert len(recorder._output_buffer) == 200

    def test_multiple_feeds(self, recorder):
        """Несколько feed добавляются к буферу."""
        recorder.feed_input(b"\x00" * 100)
        recorder.feed_input(b"\x00" * 100)
        assert len(recorder._input_buffer) == 200


# --- Транскрипт ---


class TestTranscript:
    def test_add_message(self, recorder):
        """add_message добавляет сообщение."""
        recorder.add_message("user", "Привет")
        recorder.add_message("assistant", "Здравствуйте!")
        assert len(recorder._messages) == 2
        assert recorder._messages[0]["role"] == "user"
        assert recorder._messages[0]["text"] == "Привет"

    def test_add_message_with_confidence(self, recorder):
        """add_message с confidence."""
        recorder.add_message("user", "Тест", confidence=0.95)
        assert recorder._messages[0]["confidence"] == 0.95


# --- Финализация ---


class TestFinalize:
    @pytest.mark.asyncio
    async def test_finalize_creates_files(self, recorder, tmp_data_dir):
        """finalize создаёт файлы записи."""
        recorder.feed_input(b"\x00\x01" * 100)
        recorder.feed_output(b"\x01\x00" * 100)
        recorder.add_message("user", "Тест")

        result = await recorder.finalize()

        assert result["call_id"] == "call-001"
        assert "input_path" in result
        assert "output_path" in result
        assert "combined_path" in result
        assert "transcript_path" in result

        # Проверяем что файлы существуют
        assert Path(result["input_path"]).exists()
        assert Path(result["output_path"]).exists()
        assert Path(result["combined_path"]).exists()
        assert Path(result["transcript_path"]).exists()

    @pytest.mark.asyncio
    async def test_finalize_transcript_content(self, recorder, tmp_data_dir):
        """finalize сохраняет транскрипт в JSON."""
        recorder.add_message("user", "Документы не проводятся")
        recorder.add_message("assistant", "Какой продукт используете?")

        result = await recorder.finalize()

        transcript = json.loads(Path(result["transcript_path"]).read_text("utf-8"))
        assert transcript["call_id"] == "call-001"
        assert len(transcript["messages"]) == 2

    @pytest.mark.asyncio
    async def test_finalize_empty_buffers(self, recorder, tmp_data_dir):
        """finalize с пустыми буферами."""
        result = await recorder.finalize()
        assert result["input_bytes"] == 0
        assert result["output_bytes"] == 0
        assert "input_path" not in result  # Нет файла для пустого буфера


# --- WAV ---


class TestWAVConversion:
    def test_pcm_to_wav_header(self):
        """PCM -> WAV содержит правильный заголовок."""
        pcm = b"\x00" * 16000  # 1 sec at 8kHz 16-bit
        wav = AudioRecorder._pcm_to_wav(pcm)

        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"
        assert wav[12:16] == b"fmt "
        assert wav[36:40] == b"data"
        # Data size
        data_size = struct.unpack("<I", wav[40:44])[0]
        assert data_size == 16000

    def test_pcm_to_wav_length(self):
        """WAV = 44 байт заголовок + PCM данные."""
        pcm = b"\x00" * 1000
        wav = AudioRecorder._pcm_to_wav(pcm)
        assert len(wav) == 44 + 1000


# --- Микширование ---


class TestAudioMixing:
    def test_mix_equal_length(self):
        """Микширование двух потоков одинаковой длины."""
        a = struct.pack("<4h", 1000, 2000, 3000, 4000)
        b = struct.pack("<4h", 500, 500, 500, 500)

        mixed = AudioRecorder._mix_audio(a, b)
        samples = struct.unpack(f"<{len(mixed) // 2}h", mixed)

        assert samples == (1500, 2500, 3500, 4500)

    def test_mix_different_length(self):
        """Микширование потоков разной длины (короткий дополняется нулями)."""
        a = struct.pack("<4h", 1000, 2000, 3000, 4000)
        b = struct.pack("<2h", 500, 500)

        mixed = AudioRecorder._mix_audio(a, b)
        samples = struct.unpack(f"<{len(mixed) // 2}h", mixed)

        assert samples == (1500, 2500, 3000, 4000)

    def test_mix_clipping(self):
        """Микширование с ограничением (clipping)."""
        a = struct.pack("<2h", 30000, -30000)
        b = struct.pack("<2h", 10000, -10000)

        mixed = AudioRecorder._mix_audio(a, b)
        samples = struct.unpack(f"<{len(mixed) // 2}h", mixed)

        assert samples[0] == 32767   # clipped
        assert samples[1] == -32768  # clipped

    def test_mix_empty(self):
        """Микширование пустых буферов."""
        mixed = AudioRecorder._mix_audio(b"", b"")
        assert mixed == b""
