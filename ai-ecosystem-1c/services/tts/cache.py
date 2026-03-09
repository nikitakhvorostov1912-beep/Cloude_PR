"""LRU cache for frequently synthesized TTS phrases."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True)
class CachedAudio:
    audio_data: bytes
    duration_ms: float


class TTSCache:
    """Simple LRU cache for TTS audio data."""

    def __init__(self, max_size: int = 50) -> None:
        self._cache: OrderedDict[str, CachedAudio] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> CachedAudio | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, audio_data: bytes, duration_ms: float) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            self._cache[key] = CachedAudio(audio_data=audio_data, duration_ms=duration_ms)

    @property
    def size(self) -> int:
        return len(self._cache)
