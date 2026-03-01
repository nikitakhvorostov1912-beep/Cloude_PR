"""Generate WAV audio files from text interviews using edge-tts."""
import asyncio
import sys
from pathlib import Path

import edge_tts

PROJECT_ROOT = Path(__file__).parent.parent
PROJECT_NAME = "ПВХ_Панели"
DATA_DIR = PROJECT_ROOT / "data" / "projects" / PROJECT_NAME

TXT_DIR = DATA_DIR / "transcripts"
AUDIO_DIR = DATA_DIR / "audio"

# Use male voice for interviewer-heavy files, female for others
VOICE_MAP = {
    "interview_buhgalteria.txt": "ru-RU-SvetlanaNeural",   # female respondent
    "interview_logistika.txt": "ru-RU-DmitryNeural",       # male respondent
    "interview_prodazhi.txt": "ru-RU-DmitryNeural",        # male respondent
    "interview_proizvodstvo.txt": "ru-RU-DmitryNeural",    # male respondent
    "interview_zakupki.txt": "ru-RU-SvetlanaNeural",       # female respondent
}

DEFAULT_VOICE = "ru-RU-DmitryNeural"


async def generate_audio(txt_path: Path, wav_path: Path, voice: str):
    """Generate WAV from text using edge-tts."""
    text = txt_path.read_text(encoding="utf-8")

    # Trim to ~3000 chars to keep audio files manageable (~3-4 min)
    if len(text) > 3000:
        # Find a sentence boundary near 3000 chars
        cut = text.rfind(".", 0, 3000)
        if cut == -1:
            cut = 3000
        text = text[:cut + 1]

    mp3_path = wav_path.with_suffix(".mp3")

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(mp3_path))

    # Convert MP3 to WAV using pydub
    from pydub import AudioSegment
    audio = AudioSegment.from_mp3(str(mp3_path))
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(str(wav_path), format="wav")

    # Remove temp MP3
    mp3_path.unlink(missing_ok=True)

    return wav_path


async def main():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(TXT_DIR.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {TXT_DIR}")
        sys.exit(1)

    print(f"Generating audio for {len(txt_files)} interviews...\n")

    for txt_path in txt_files:
        voice = VOICE_MAP.get(txt_path.name, DEFAULT_VOICE)
        wav_name = txt_path.stem + ".wav"
        wav_path = AUDIO_DIR / wav_name

        print(f"  {txt_path.name} -> {wav_name} (voice: {voice})...")
        try:
            result = await generate_audio(txt_path, wav_path, voice)
            size_kb = result.stat().st_size / 1024
            print(f"    OK: {size_kb:.0f} KB")
        except Exception as e:
            print(f"    ERROR: {e}")

    print("\nDone! Audio files in:", AUDIO_DIR)


if __name__ == "__main__":
    asyncio.run(main())
