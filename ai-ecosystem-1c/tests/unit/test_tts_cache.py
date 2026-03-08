"""Tests for TTS LRU cache."""

from __future__ import annotations

import pytest

from services.tts.cache import TTSCache


class TestTTSCache:
    """Test LRU cache behavior."""

    def test_put_and_get(self) -> None:
        cache = TTSCache(max_size=5)
        cache.put("hello", b"audio_data", 500.0)
        result = cache.get("hello")
        assert result is not None
        assert result.audio_data == b"audio_data"
        assert result.duration_ms == 500.0

    def test_get_missing_returns_none(self) -> None:
        cache = TTSCache(max_size=5)
        assert cache.get("nonexistent") is None

    def test_eviction_on_max_size(self) -> None:
        cache = TTSCache(max_size=3)
        cache.put("a", b"1", 100)
        cache.put("b", b"2", 100)
        cache.put("c", b"3", 100)
        cache.put("d", b"4", 100)  # Should evict "a"

        assert cache.get("a") is None
        assert cache.get("b") is not None
        assert cache.get("d") is not None
        assert cache.size == 3

    def test_get_moves_to_end(self) -> None:
        cache = TTSCache(max_size=3)
        cache.put("a", b"1", 100)
        cache.put("b", b"2", 100)
        cache.put("c", b"3", 100)

        # Access "a" — it should move to end (most recently used)
        cache.get("a")
        cache.put("d", b"4", 100)  # Should evict "b" (least recently used)

        assert cache.get("a") is not None
        assert cache.get("b") is None

    def test_put_existing_updates_position(self) -> None:
        cache = TTSCache(max_size=3)
        cache.put("a", b"1", 100)
        cache.put("b", b"2", 100)
        cache.put("c", b"3", 100)
        cache.put("a", b"1_updated", 200)  # Update "a" — moves to end

        cache.put("d", b"4", 100)  # Should evict "b"
        assert cache.get("b") is None
        assert cache.get("a") is not None

    def test_size_property(self) -> None:
        cache = TTSCache(max_size=5)
        assert cache.size == 0
        cache.put("a", b"1", 100)
        assert cache.size == 1
        cache.put("b", b"2", 100)
        assert cache.size == 2
