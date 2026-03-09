"""Format raw transcription results into structured JSON."""


def format_transcript(raw_result: dict) -> dict:
    """Format raw transcription result into a structured transcript.

    Args:
        raw_result: Raw result from transcriber (segments with speaker labels).

    Returns:
        Structured transcript with speakers, timeline, and full text.
    """
    segments = raw_result.get("segments", [])

    # Build formatted segments
    formatted_segments = []
    speakers = set()

    for seg in segments:
        speaker = seg.get("speaker", "SPEAKER_UNKNOWN")
        speakers.add(speaker)

        formatted_segments.append({
            "speaker": speaker,
            "start": round(seg.get("start", 0), 2),
            "end": round(seg.get("end", 0), 2),
            "text": seg.get("text", "").strip(),
            "start_formatted": _format_time(seg.get("start", 0)),
            "end_formatted": _format_time(seg.get("end", 0)),
        })

    # Build speaker-grouped dialogue
    dialogue = _build_dialogue(formatted_segments)

    # Build full text
    full_text = "\n".join(
        f"[{s['start_formatted']}] {s['speaker']}: {s['text']}"
        for s in formatted_segments
        if s["text"]
    )

    # Statistics
    total_duration = max((s["end"] for s in formatted_segments), default=0)
    speaker_stats = _calculate_speaker_stats(formatted_segments)

    return {
        "segments": formatted_segments,
        "dialogue": dialogue,
        "full_text": full_text,
        "metadata": {
            "language": raw_result.get("language", "ru"),
            "audio_path": raw_result.get("audio_path", ""),
            "total_duration_seconds": round(total_duration, 2),
            "total_duration_formatted": _format_time(total_duration),
            "total_segments": len(formatted_segments),
            "speakers": sorted(list(speakers)),
            "speaker_count": len(speakers),
            "speaker_stats": speaker_stats,
        },
    }


def _build_dialogue(segments: list) -> list:
    """Group consecutive segments by the same speaker into dialogue turns."""
    if not segments:
        return []

    dialogue = []
    current_speaker = None
    current_texts = []
    current_start = 0
    current_end = 0

    for seg in segments:
        if not seg["text"]:
            continue

        if seg["speaker"] != current_speaker:
            if current_speaker is not None:
                dialogue.append({
                    "speaker": current_speaker,
                    "text": " ".join(current_texts),
                    "start": current_start,
                    "end": current_end,
                    "start_formatted": _format_time(current_start),
                    "end_formatted": _format_time(current_end),
                })
            current_speaker = seg["speaker"]
            current_texts = [seg["text"]]
            current_start = seg["start"]
            current_end = seg["end"]
        else:
            current_texts.append(seg["text"])
            current_end = seg["end"]

    # Don't forget the last turn
    if current_speaker is not None:
        dialogue.append({
            "speaker": current_speaker,
            "text": " ".join(current_texts),
            "start": current_start,
            "end": current_end,
            "start_formatted": _format_time(current_start),
            "end_formatted": _format_time(current_end),
        })

    return dialogue


def _calculate_speaker_stats(segments: list) -> dict:
    """Calculate speaking time and word count per speaker."""
    stats = {}
    for seg in segments:
        speaker = seg["speaker"]
        if speaker not in stats:
            stats[speaker] = {"duration_seconds": 0, "word_count": 0, "segment_count": 0}

        stats[speaker]["duration_seconds"] += seg["end"] - seg["start"]
        stats[speaker]["word_count"] += len(seg["text"].split())
        stats[speaker]["segment_count"] += 1

    # Round durations
    for speaker in stats:
        stats[speaker]["duration_seconds"] = round(stats[speaker]["duration_seconds"], 2)
        stats[speaker]["duration_formatted"] = _format_time(stats[speaker]["duration_seconds"])

    return stats


def _format_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS (handles >24h correctly)."""
    total_secs = int(seconds)
    hours, remainder = divmod(total_secs, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
