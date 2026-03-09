"""Test all OpenAI TTS female voices with Aurora's first line."""
import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(ENV_PATH)

from openai import OpenAI

api_key = os.environ.get("OPENAI_API_KEY", "")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY must be set")

client = OpenAI(api_key=api_key)

TEXT = "Добрый день! Вас приветствует Аврора — AI-ассистент компании ИнтерСофт. Расскажите, что у вас случилось, я помогу разобраться."

# All OpenAI voices - testing which sound female/warm for Russian
VOICES = [
    {"voice": "alloy", "desc": "Alloy -- nejtral'nyj, androginnyj"},
    {"voice": "nova", "desc": "Nova -- zhenskij, teplyj"},
    {"voice": "shimmer", "desc": "Shimmer -- zhenskij, myagkij"},
    {"voice": "fable", "desc": "Fable -- ekspressivnyj"},
    {"voice": "coral", "desc": "Coral -- novyj zhenskij"},
    {"voice": "sage", "desc": "Sage -- novyj zhenskij"},
    {"voice": "ash", "desc": "Ash -- novyj"},
    {"voice": "ballad", "desc": "Ballad -- novyj ekspressivnyj"},
    {"voice": "verse", "desc": "Verse -- novyj"},
]

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "pitch" / "audio" / "test-voices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Generating {len(VOICES)} OpenAI voice samples...\n")

for v in VOICES:
    filename = f"openai_{v['voice']}.mp3"
    try:
        response = client.audio.speech.create(
            model="tts-1-hd",
            voice=v["voice"],
            input=TEXT,
            response_format="mp3",
            speed=0.95,
        )
        filepath = OUTPUT_DIR / filename
        response.stream_to_file(str(filepath))
        size_kb = filepath.stat().st_size / 1024
        print(f"  OK {filename:30s} ({size_kb:5.0f} KB) -- {v['desc']}")
    except Exception as e:
        err = str(e)[:100]
        print(f"  FAIL {filename:30s} -- {err}")

print(f"\nFiles saved to: {OUTPUT_DIR}")
