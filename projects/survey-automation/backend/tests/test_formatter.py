"""Тесты: форматирование и парсинг транскриптов."""
import json

import pytest

from app.transcription.formatter import TranscriptFormatter
from app.transcription.transcriber import Segment, TranscriptionResult


@pytest.fixture
def formatter():
    """Create a TranscriptFormatter instance."""
    return TranscriptFormatter()


# -------------------------------------------------------------------
# from_text
# -------------------------------------------------------------------


def test_from_text_plain(formatter):
    """from_text with plain text (no speaker labels) returns a TranscriptionResult."""
    text = "Это простой текст транскрипции без разметки спикеров."
    result = formatter.from_text(text)
    assert isinstance(result, TranscriptionResult)
    assert result.full_text
    assert len(result.segments) >= 1


def test_from_text_with_speakers(formatter):
    """from_text with speaker-labelled lines parses speakers correctly."""
    text = "Интервьюер: Как устроен процесс?\nРеспондент: Мы используем Excel."
    result = formatter.from_text(text)
    assert isinstance(result, TranscriptionResult)
    assert len(result.segments) >= 2
    # Check that speakers are parsed
    speakers = {seg.speaker for seg in result.segments if seg.speaker}
    assert len(speakers) >= 2


def test_from_text_with_timestamps(formatter):
    """from_text with timestamped dialogue lines parses times and speakers."""
    text = (
        "[00:00:00 - 00:00:15] Аналитик: Расскажите о вашем процессе.\n"
        "[00:00:16 - 00:00:45] Менеджер: Мы принимаем заказы по телефону.\n"
    )
    result = formatter.from_text(text)
    assert isinstance(result, TranscriptionResult)
    assert len(result.segments) >= 2
    assert result.segments[0].start == 0.0
    assert result.segments[0].end == 15.0
    assert result.segments[0].speaker == "Аналитик"


def test_from_text_empty_raises(formatter):
    """from_text with empty string raises ValidationError."""
    from app.exceptions import ValidationError

    with pytest.raises(ValidationError):
        formatter.from_text("")

    with pytest.raises(ValidationError):
        formatter.from_text("   ")


# -------------------------------------------------------------------
# to_json / from_json roundtrip
# -------------------------------------------------------------------


def test_to_json_and_from_json_roundtrip(formatter):
    """to_json followed by from_json restores a TranscriptionResult."""
    segments = [
        Segment(start=0.0, end=2.0, text="Вопрос", speaker="Аналитик"),
        Segment(start=2.5, end=5.0, text="Ответ", speaker="Менеджер"),
    ]
    original = TranscriptionResult(
        segments=segments,
        full_text="Вопрос Ответ",
        language="ru",
        duration=5.0,
    )

    json_dict = formatter.to_json(original, audio_file="test.wav")
    assert isinstance(json_dict, dict)
    assert "metadata" in json_dict
    assert "segments" in json_dict
    assert "full_text" in json_dict
    assert "dialogue" in json_dict
    assert json_dict["metadata"]["audio_file"] == "test.wav"

    restored = formatter.from_json(json_dict)
    assert isinstance(restored, TranscriptionResult)
    assert len(restored.segments) == 2
    assert restored.segments[0].text == "Вопрос"
    assert restored.segments[1].text == "Ответ"


def test_from_json_invalid_type_raises(formatter):
    """from_json with non-dict raises ValidationError."""
    from app.exceptions import ValidationError

    with pytest.raises(ValidationError):
        formatter.from_json("not a dict")


def test_from_json_minimal(formatter):
    """from_json with minimal valid data works correctly."""
    data = {
        "segments": [
            {"start": 0, "end": 1.5, "text": "Привет"},
        ],
    }
    result = formatter.from_json(data)
    assert len(result.segments) == 1
    assert result.segments[0].text == "Привет"


# -------------------------------------------------------------------
# format_dialogue
# -------------------------------------------------------------------


def test_format_dialogue(formatter):
    """format_dialogue merges consecutive segments from the same speaker."""
    segments = [
        Segment(start=0.0, end=1.0, text="Первая часть", speaker="Аналитик"),
        Segment(start=1.0, end=2.0, text="вторая часть", speaker="Аналитик"),
        Segment(start=2.5, end=5.0, text="Ответ", speaker="Менеджер"),
    ]
    result = TranscriptionResult(
        segments=segments,
        full_text="Первая часть вторая часть Ответ",
        language="ru",
        duration=5.0,
    )

    dialogue = formatter.format_dialogue(result)
    assert len(dialogue) == 2
    assert dialogue[0].speaker == "Аналитик"
    assert "Первая часть" in dialogue[0].text
    assert "вторая часть" in dialogue[0].text
    assert dialogue[1].speaker == "Менеджер"
    assert dialogue[1].text == "Ответ"


def test_format_dialogue_empty(formatter):
    """format_dialogue with empty TranscriptionResult returns empty list."""
    result = TranscriptionResult(segments=[], full_text="", language="ru", duration=0)
    dialogue = formatter.format_dialogue(result)
    assert dialogue == []


# -------------------------------------------------------------------
# format_full_text
# -------------------------------------------------------------------


def test_format_full_text_with_speakers(formatter):
    """format_full_text with speakers includes speaker labels and timestamps."""
    segments = [
        Segment(start=0.0, end=2.0, text="Вопрос", speaker="Аналитик"),
        Segment(start=2.5, end=5.0, text="Ответ", speaker="Менеджер"),
    ]
    result = TranscriptionResult(
        segments=segments,
        full_text="Вопрос Ответ",
        language="ru",
        duration=5.0,
    )

    text = formatter.format_full_text(result)
    assert "Аналитик" in text
    assert "Менеджер" in text


def test_format_full_text_plain(formatter):
    """format_full_text without speakers returns plain text."""
    segments = [
        Segment(start=0.0, end=2.0, text="Первый сегмент"),
        Segment(start=2.5, end=5.0, text="Второй сегмент"),
    ]
    result = TranscriptionResult(
        segments=segments,
        full_text="Первый сегмент Второй сегмент",
        language="ru",
        duration=5.0,
    )

    text = formatter.format_full_text(result)
    assert "Первый сегмент" in text
    assert "Второй сегмент" in text
