"""Voice Activity Detection — RMS energy-based silence detection."""

from __future__ import annotations

import struct
import time


class VoiceActivityDetector:
    """Detects speech vs silence in LINEAR16 PCM audio streams."""

    def __init__(
        self,
        *,
        rms_threshold: int = 300,
        silence_threshold_ms: int = 800,
        sample_rate: int = 8000,
    ) -> None:
        self._rms_threshold = rms_threshold
        self._silence_threshold_sec = silence_threshold_ms / 1000.0
        self._sample_rate = sample_rate
        self._last_speech_time: float = time.monotonic()
        self._has_speech: bool = False

    def feed(self, pcm_data: bytes) -> bool:
        """Feed audio chunk. Returns True if speech is detected (not silent)."""
        rms = self._calculate_rms(pcm_data)
        now = time.monotonic()

        if rms >= self._rms_threshold:
            self._last_speech_time = now
            self._has_speech = True
            return True

        return False

    @property
    def is_silent(self) -> bool:
        """True if silence has exceeded the threshold since last speech."""
        if not self._has_speech:
            return False
        elapsed = time.monotonic() - self._last_speech_time
        return elapsed >= self._silence_threshold_sec

    @property
    def silence_duration_ms(self) -> float:
        return (time.monotonic() - self._last_speech_time) * 1000.0

    def reset(self) -> None:
        self._last_speech_time = time.monotonic()
        self._has_speech = False

    @staticmethod
    def _calculate_rms(pcm_data: bytes) -> float:
        """RMS energy of LINEAR16 PCM samples."""
        if len(pcm_data) < 2:
            return 0.0
        n_samples = len(pcm_data) // 2
        samples = struct.unpack(f"<{n_samples}h", pcm_data[: n_samples * 2])
        if not samples:
            return 0.0
        sum_sq = sum(s * s for s in samples)
        return (sum_sq / n_samples) ** 0.5
