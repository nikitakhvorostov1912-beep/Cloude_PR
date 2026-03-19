"""Tests for transcription formatter."""
from src.transcription.formatter import _build_dialogue, _calculate_speaker_stats, _format_time, format_transcript


class TestFormatTime:
    def test_seconds_only(self):
        assert _format_time(45) == "00:45"

    def test_minutes_and_seconds(self):
        assert _format_time(125) == "02:05"

    def test_hours(self):
        assert _format_time(3661) == "01:01:01"

    def test_zero(self):
        assert _format_time(0) == "00:00"

    def test_over_24_hours(self):
        # BUG-004 regression: must handle >24h correctly
        assert _format_time(90000) == "25:00:00"

    def test_fractional_seconds(self):
        assert _format_time(65.7) == "01:05"


class TestBuildDialogue:
    def test_empty(self):
        assert _build_dialogue([]) == []

    def test_single_segment(self):
        result = _build_dialogue([
            {"speaker": "A", "text": "Hello", "start": 0, "end": 1},
        ])
        assert len(result) == 1
        assert result[0]["speaker"] == "A"
        assert result[0]["text"] == "Hello"

    def test_groups_consecutive_same_speaker(self):
        result = _build_dialogue([
            {"speaker": "A", "text": "Hello", "start": 0, "end": 1},
            {"speaker": "A", "text": "World", "start": 1, "end": 2},
            {"speaker": "B", "text": "Hi", "start": 2, "end": 3},
        ])
        assert len(result) == 2
        assert result[0]["text"] == "Hello World"
        assert result[1]["text"] == "Hi"

    def test_skips_empty_text(self):
        result = _build_dialogue([
            {"speaker": "A", "text": "Hello", "start": 0, "end": 1},
            {"speaker": "A", "text": "", "start": 1, "end": 2},
            {"speaker": "B", "text": "Hi", "start": 2, "end": 3},
        ])
        assert len(result) == 2


class TestCalculateSpeakerStats:
    def test_basic_stats(self):
        segments = [
            {"speaker": "A", "start": 0, "end": 5, "text": "hello world"},
            {"speaker": "B", "start": 5, "end": 10, "text": "one two three"},
            {"speaker": "A", "start": 10, "end": 15, "text": "four"},
        ]
        stats = _calculate_speaker_stats(segments)

        assert stats["A"]["duration_seconds"] == 10.0
        assert stats["A"]["word_count"] == 3
        assert stats["A"]["segment_count"] == 2
        assert stats["B"]["word_count"] == 3

    def test_empty(self):
        assert _calculate_speaker_stats([]) == {}


class TestFormatTranscript:
    def test_full_format(self, sample_raw_transcription):
        result = format_transcript(sample_raw_transcription)

        assert "segments" in result
        assert "dialogue" in result
        assert "full_text" in result
        assert "metadata" in result

        meta = result["metadata"]
        assert meta["language"] == "ru"
        assert meta["speaker_count"] == 2
        assert meta["total_segments"] == 4
        assert "SPEAKER_00" in meta["speakers"]
        assert "SPEAKER_01" in meta["speakers"]

    def test_segments_have_formatted_times(self, sample_raw_transcription):
        result = format_transcript(sample_raw_transcription)
        seg = result["segments"][0]
        assert "start_formatted" in seg
        assert "end_formatted" in seg

    def test_full_text_not_empty(self, sample_raw_transcription):
        result = format_transcript(sample_raw_transcription)
        assert len(result["full_text"]) > 0
        assert "SPEAKER_00" in result["full_text"]
