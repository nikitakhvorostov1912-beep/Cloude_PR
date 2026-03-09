"""Audio preprocessing: convert any format to 16kHz mono WAV."""
import os
import shutil
import subprocess
from pathlib import Path


def preprocess_audio(input_path: str, output_dir: str, config: dict) -> str:
    """Convert audio to 16kHz mono WAV for transcription.

    Args:
        input_path: Path to input audio file.
        output_dir: Directory for preprocessed output.
        config: Application config dict.

    Returns:
        Path to preprocessed WAV file.
    """
    input_file = Path(input_path)
    os.makedirs(output_dir, exist_ok=True)

    output_path = Path(output_dir) / f"{input_file.stem}.wav"

    sample_rate = config.get("audio", {}).get("sample_rate", 16000)
    channels = config.get("audio", {}).get("channels", 1)

    supported = config.get("audio", {}).get("supported_formats", [])
    ext = input_file.suffix.lower().lstrip(".")
    if supported and ext not in supported:
        raise ValueError(f"Unsupported audio format: .{ext}. Supported: {supported}")

    # If already WAV with correct parameters, just copy
    if ext == "wav":
        # Still convert to ensure correct sample rate and channels
        pass

    # Use FFmpeg for conversion
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError(
            "FFmpeg not found. Please install FFmpeg: https://ffmpeg.org/download.html"
        )

    cmd = [
        ffmpeg_path,
        "-i", str(input_file),
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-acodec", "pcm_s16le",
        "-y",  # overwrite
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timeout: конвертация заняла более 10 минут")
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {result.stderr}")

    return str(output_path)


def get_audio_info(file_path: str) -> dict:
    """Get audio file metadata using FFprobe."""
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        return {"error": "ffprobe not found"}

    cmd = [
        ffprobe_path,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": result.stderr}

    import json
    info = json.loads(result.stdout)
    fmt = info.get("format", {})
    streams = info.get("streams", [])

    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    return {
        "duration_seconds": float(fmt.get("duration", 0)),
        "format": fmt.get("format_name", "unknown"),
        "sample_rate": int(audio_stream.get("sample_rate", 0)),
        "channels": int(audio_stream.get("channels", 0)),
        "codec": audio_stream.get("codec_name", "unknown"),
        "file_size_mb": round(int(fmt.get("size", 0)) / (1024 * 1024), 2),
    }
