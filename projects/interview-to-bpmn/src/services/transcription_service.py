"""Transcription service — orchestrates audio preprocessing, transcription, and formatting."""
import json
import logging
from pathlib import Path

from src.config import ProjectDir
from src.transcription.formatter import format_transcript
from src.transcription.preprocessor import preprocess_audio
from src.transcription.transcriber import transcribe

logger = logging.getLogger(__name__)


def run_transcription(audio_path: Path, config_dict: dict, project: ProjectDir) -> dict:
    """Full transcription pipeline: preprocess → transcribe → format → save.

    Args:
        audio_path: Path to raw audio file.
        config_dict: Application config as dict.
        project: ProjectDir for output paths.

    Returns:
        Formatted transcript dict.
    """
    # Step 1: Preprocess
    logger.info(f"Preprocessing {audio_path.name}...")
    processed_path = preprocess_audio(str(audio_path), str(project.audio), config_dict)

    # Step 2: Transcribe
    logger.info(f"Transcribing {Path(processed_path).name}...")
    raw_result = transcribe(processed_path, config_dict)

    # Step 3: Format
    transcript = format_transcript(raw_result)

    # Step 4: Save
    transcript_path = project.transcripts / f"{audio_path.stem}.json"
    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)

    logger.info(f"Transcript saved: {transcript_path}")
    return transcript
