"""Transcription + diarization: faster-whisper CPU, WhisperX GPU, or Whisper API."""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache for WhisperModel to avoid reloading (~5GB RAM, 15-30sec) on every call
_whisper_model_cache = {"key": None, "model": None}


def transcribe(audio_path: str, config: dict) -> dict:
    """Transcribe audio with speaker diarization.

    Args:
        audio_path: Path to preprocessed WAV file.
        config: Application config dict.

    Returns:
        Raw transcription result with segments and speaker labels.
    """
    mode = config.get("transcription", {}).get("mode", "local_cpu")

    if mode == "local_cpu":
        return _transcribe_local_cpu(audio_path, config)
    elif mode == "local":
        return _transcribe_local(audio_path, config)
    elif mode == "api":
        return _transcribe_api(audio_path, config)
    else:
        raise ValueError(f"Unknown transcription mode: {mode}")


# ---------------------------------------------------------------------------
# Mode 1: faster-whisper on CPU (бесплатный, без GPU)
# ---------------------------------------------------------------------------

def _transcribe_local_cpu(audio_path: str, config: dict) -> dict:
    """Transcribe using faster-whisper on CPU — no GPU required."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "faster-whisper не установлен. Установите: pip install faster-whisper\n"
            "Это бесплатная транскрипция на CPU, GPU не нужен."
        )

    cpu_cfg = config.get("transcription", {}).get("local_cpu", {})
    model_name = cpu_cfg.get("model", "medium")
    language = cpu_cfg.get("language", "ru")
    compute_type = cpu_cfg.get("compute_type", "int8")
    beam_size = cpu_cfg.get("beam_size", 5)

    # Load model on CPU (cached to avoid reloading on every call)
    cache_key = f"{model_name}_{compute_type}"
    if _whisper_model_cache["key"] != cache_key:
        logger.info(f"Загрузка модели {model_name} (compute_type={compute_type})...")
        _whisper_model_cache["model"] = WhisperModel(
            model_name,
            device="cpu",
            compute_type=compute_type,
        )
        _whisper_model_cache["key"] = cache_key
    model = _whisper_model_cache["model"]

    # Transcribe
    segments_gen, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=beam_size,
        vad_filter=True,           # Voice Activity Detection — убирает тишину
        vad_parameters=dict(
            min_silence_duration_ms=500,
        ),
    )

    # Collect segments
    raw_segments = []
    for seg in segments_gen:
        raw_segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "speaker": "SPEAKER_UNKNOWN",
        })

    # Simple diarization by pauses (fallback без pyannote)
    raw_segments = _simple_diarize(raw_segments, config)

    return {
        "segments": raw_segments,
        "language": language,
        "audio_path": audio_path,
        "transcription_info": {
            "model": model_name,
            "device": "cpu",
            "compute_type": compute_type,
            "detected_language": getattr(info, "language", language),
            "language_probability": getattr(info, "language_probability", 0),
            "duration": getattr(info, "duration", 0),
        },
    }


def _simple_diarize(segments: list, config: dict) -> list:
    """Simple speaker diarization based on pauses between segments.

    Assigns speaker labels by detecting long pauses (>2 seconds) which
    typically indicate a speaker change in interview settings.
    This is a basic fallback when pyannote is not available.
    """
    if not segments:
        return segments

    diarize_cfg = config.get("diarization", {})
    max_speakers = diarize_cfg.get("max_speakers", 2)
    if max_speakers <= 0:
        max_speakers = 2  # Default for interviews: interviewer + interviewee

    # Detect speaker changes by pause duration
    PAUSE_THRESHOLD = 1.5  # seconds — pause that suggests speaker change
    current_speaker = 0
    speaker_changes = []

    for i, seg in enumerate(segments):
        if i == 0:
            seg["speaker"] = f"SPEAKER_{current_speaker:02d}"
            continue

        pause = seg["start"] - segments[i - 1]["end"]

        if pause > PAUSE_THRESHOLD:
            # Likely speaker change
            current_speaker = (current_speaker + 1) % max_speakers
            speaker_changes.append(i)

        seg["speaker"] = f"SPEAKER_{current_speaker:02d}"

    return segments


# ---------------------------------------------------------------------------
# Mode 2: WhisperX on GPU (local or remote)
# ---------------------------------------------------------------------------

def _transcribe_local(audio_path: str, config: dict) -> dict:
    """Transcribe using WhisperX on local GPU or remote GPU server."""
    local_config = config.get("transcription", {}).get("local", {})
    server_url = local_config.get("server_url", "")

    # If server URL is set and use_remote is enabled, use remote GPU server
    use_remote = local_config.get("use_remote", bool(server_url))
    if server_url and use_remote:
        return _transcribe_remote_gpu(audio_path, server_url, config)

    # Otherwise, try local WhisperX
    try:
        import whisperx  # noqa: F401 — also requires torch
    except ImportError:
        raise RuntimeError(
            "WhisperX не установлен. Установите: pip install whisperx\n"
            "Или используйте CPU режим: transcription.mode: 'local_cpu' в config.yaml"
        )

    device = local_config.get("device", "cuda")
    model_name = local_config.get("model", "large-v3")
    language = local_config.get("language", "ru")
    batch_size = local_config.get("batch_size", 16)
    compute_type = local_config.get("compute_type", "float16")

    # Load model
    model = whisperx.load_model(
        model_name,
        device=device,
        compute_type=compute_type,
        language=language,
    )

    # Transcribe
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=batch_size, language=language)

    # Align timestamps
    model_a, metadata = whisperx.load_align_model(
        language_code=language, device=device
    )
    result = whisperx.align(
        result["segments"], model_a, metadata, audio, device,
        return_char_alignments=False,
    )

    # Speaker diarization
    diarize_config = config.get("diarization", {})
    hf_token = diarize_config.get("hf_token") or os.environ.get("HF_TOKEN", "")

    if hf_token:
        diarize_model = whisperx.DiarizationPipeline(
            use_auth_token=hf_token, device=device
        )

        diarize_kwargs = {}
        min_speakers = diarize_config.get("min_speakers", 0)
        max_speakers = diarize_config.get("max_speakers", 0)
        if min_speakers > 0:
            diarize_kwargs["min_speakers"] = min_speakers
        if max_speakers > 0:
            diarize_kwargs["max_speakers"] = max_speakers

        diarize_segments = diarize_model(audio, **diarize_kwargs)
        result = whisperx.assign_word_speakers(diarize_segments, result)

    return {
        "segments": result.get("segments", []),
        "language": language,
        "audio_path": audio_path,
    }


def _transcribe_remote_gpu(audio_path: str, server_url: str, config: dict) -> dict:
    """Send audio to remote GPU server for transcription."""
    import requests

    url = f"{server_url.rstrip('/')}/transcribe"

    with open(audio_path, "rb") as f:
        files = {"file": (Path(audio_path).name, f, "audio/wav")}
        data = {
            "language": config.get("transcription", {}).get("local", {}).get("language", "ru"),
            "min_speakers": config.get("diarization", {}).get("min_speakers", 0),
            "max_speakers": config.get("diarization", {}).get("max_speakers", 0),
        }
        response = requests.post(url, files=files, data=data, timeout=600)

    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Mode 3: OpenAI Whisper API (платный)
# ---------------------------------------------------------------------------

def _transcribe_api(audio_path: str, config: dict) -> dict:
    """Transcribe using OpenAI Whisper API."""
    api_config = config.get("transcription", {}).get("api", {})
    api_key = api_config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")

    if not api_key:
        raise ValueError(
            "OpenAI API key not set. Set OPENAI_API_KEY env var or "
            "transcription.api.api_key in config.yaml\n"
            "Или используйте бесплатный CPU режим: transcription.mode: 'local_cpu'"
        )

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    with open(audio_path, "rb") as audio_file:
        result = client.audio.transcriptions.create(
            model=api_config.get("model", "whisper-1"),
            file=audio_file,
            language=api_config.get("language", "ru"),
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = []
    for seg in (result.segments or []):
        segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
            "speaker": "SPEAKER_UNKNOWN",
        })

    return {
        "segments": segments,
        "language": api_config.get("language", "ru"),
        "audio_path": audio_path,
        "note": "API mode: no speaker diarization.",
    }
