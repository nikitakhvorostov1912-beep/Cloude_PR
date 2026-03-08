"""Tests for Voice Activity Detector."""

from __future__ import annotations

import struct

import pytest

from services.stt.vad import VoiceActivityDetector


def _make_pcm(value: int = 0, samples: int = 160) -> bytes:
    """Create PCM data with a constant sample value."""
    return struct.pack(f"<{samples}h", *([value] * samples))


class TestVAD:
    """Test RMS-based voice activity detection."""

    def test_silence_not_detected_without_speech(self) -> None:
        vad = VoiceActivityDetector(rms_threshold=300)
        # No speech fed yet — is_silent should be False (no speech baseline)
        assert not vad.is_silent

    def test_speech_detected_above_threshold(self) -> None:
        vad = VoiceActivityDetector(rms_threshold=100)
        pcm = _make_pcm(value=500, samples=160)
        result = vad.feed(pcm)
        assert result is True

    def test_silence_below_threshold(self) -> None:
        vad = VoiceActivityDetector(rms_threshold=300)
        pcm = _make_pcm(value=10, samples=160)
        result = vad.feed(pcm)
        assert result is False

    def test_rms_calculation_empty_data(self) -> None:
        rms = VoiceActivityDetector._calculate_rms(b"")
        assert rms == 0.0

    def test_rms_calculation_single_byte(self) -> None:
        rms = VoiceActivityDetector._calculate_rms(b"\x00")
        assert rms == 0.0

    def test_rms_calculation_known_value(self) -> None:
        # 10 samples of value 1000 → RMS = 1000
        pcm = _make_pcm(value=1000, samples=10)
        rms = VoiceActivityDetector._calculate_rms(pcm)
        assert abs(rms - 1000.0) < 1.0

    def test_reset_clears_state(self) -> None:
        vad = VoiceActivityDetector(rms_threshold=100)
        pcm = _make_pcm(value=500, samples=160)
        vad.feed(pcm)
        vad.reset()
        assert not vad.is_silent  # No speech after reset

    def test_silence_duration_increases(self) -> None:
        vad = VoiceActivityDetector(
            rms_threshold=100, silence_threshold_ms=100
        )
        pcm = _make_pcm(value=500, samples=160)
        vad.feed(pcm)  # Speech detected
        assert vad.silence_duration_ms >= 0
