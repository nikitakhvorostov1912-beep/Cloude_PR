"""Test all Yandex SpeechKit female voices with Aurora's first line."""
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(ENV_PATH)

api_key = os.environ.get("YANDEX_API_KEY", "")
folder_id = os.environ.get("YANDEX_FOLDER_ID", "")

if not api_key or not folder_id:
    raise RuntimeError("YANDEX_API_KEY and YANDEX_FOLDER_ID must be set in .env")

TEXT = "Добрый день! Вас приветствует Аврора — AI-ассистент компании ИнтерСофт. Расскажите, что у вас случилось, я помогу разобраться."

VOICES = [
    {"voice": "marina", "emotion": "friendly", "desc": "Марина (friendly) — текущий"},
    {"voice": "marina", "emotion": "whisper", "desc": "Марина (whisper) — шёпот"},
    {"voice": "marina", "emotion": "neutral", "desc": "Марина (neutral)"},
    {"voice": "alena", "emotion": "good", "desc": "Алёна (good) — радостная"},
    {"voice": "alena", "emotion": "neutral", "desc": "Алёна (neutral)"},
    {"voice": "jane", "emotion": "good", "desc": "Джейн (good) — радостная"},
    {"voice": "jane", "emotion": "neutral", "desc": "Джейн (neutral)"},
    {"voice": "dasha", "emotion": "friendly", "desc": "Даша (friendly)"},
    {"voice": "dasha", "emotion": "good", "desc": "Даша (good) — радостная"},
    {"voice": "julia", "emotion": "neutral", "desc": "Юлия (neutral)"},
    {"voice": "lera", "emotion": "friendly", "desc": "Лера (friendly)"},
    {"voice": "masha", "emotion": "friendly", "desc": "Маша (friendly)"},
    {"voice": "masha", "emotion": "good", "desc": "Маша (good) — радостная"},
]

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "pitch" / "audio" / "test-voices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
headers = {"Authorization": f"Api-Key {api_key}"}

print(f"Generating {len(VOICES)} voice samples...\n")

for v in VOICES:
    filename = f"{v['voice']}_{v['emotion']}.mp3"
    data = {
        "text": TEXT,
        "lang": "ru-RU",
        "voice": v["voice"],
        "emotion": v["emotion"],
        "format": "mp3",
        "folderId": folder_id,
        "speed": "0.95",
        "sampleRateHertz": "48000",
    }

    try:
        resp = requests.post(url, headers=headers, data=data)
        if resp.status_code == 200:
            filepath = OUTPUT_DIR / filename
            with open(filepath, "wb") as f:
                f.write(resp.content)
            size_kb = filepath.stat().st_size / 1024
            print(f"  OK {filename:30s} ({size_kb:5.0f} KB) -- {v['desc']}")
        else:
            print(f"  FAIL {filename:30s} -- HTTP {resp.status_code}: {resp.text[:80]}")
    except Exception as e:
        print(f"  FAIL {filename:30s} -- {e}")

print(f"\nFiles saved to: {OUTPUT_DIR}")
print(f"\nОткрой в браузере: http://localhost:3002/pitch/audio/test-voices/")
print("Послушай каждый файл и выбери лучший голос!")
