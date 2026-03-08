"""Tests for AudioBuffer."""

from __future__ import annotations

import pytest

from services.stt.buffer import AudioBuffer


class TestAudioBuffer:
    """Test audio chunk accumulation."""

    def test_append_returns_empty_when_below_chunk_size(self) -> None:
        buf = AudioBuffer(chunk_size=100)
        chunks = buf.append(b"\x00" * 50)
        assert chunks == []
        assert buf.pending_bytes == 50

    def test_append_returns_chunk_when_full(self) -> None:
        buf = AudioBuffer(chunk_size=100)
        chunks = buf.append(b"\x00" * 150)
        assert len(chunks) == 1
        assert len(chunks[0]) == 100
        assert buf.pending_bytes == 50

    def test_append_returns_multiple_chunks(self) -> None:
        buf = AudioBuffer(chunk_size=100)
        chunks = buf.append(b"\x00" * 350)
        assert len(chunks) == 3
        assert buf.pending_bytes == 50

    def test_flush_returns_remaining(self) -> None:
        buf = AudioBuffer(chunk_size=100)
        buf.append(b"\x00" * 50)
        remaining = buf.flush()
        assert remaining is not None
        assert len(remaining) == 50
        assert buf.pending_bytes == 0

    def test_flush_empty_returns_none(self) -> None:
        buf = AudioBuffer(chunk_size=100)
        assert buf.flush() is None

    def test_total_bytes_tracked(self) -> None:
        buf = AudioBuffer(chunk_size=100)
        buf.append(b"\x00" * 50)
        buf.append(b"\x00" * 30)
        assert buf.total_bytes == 80

    def test_reset_clears_everything(self) -> None:
        buf = AudioBuffer(chunk_size=100)
        buf.append(b"\x00" * 50)
        buf.reset()
        assert buf.pending_bytes == 0
        assert buf.total_bytes == 0
