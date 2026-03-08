"""Test Yandex SpeechKit v3 female voices (dasha, julia, lera, masha)."""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(ENV_PATH)

api_key = os.environ.get("YANDEX_API_KEY", "")
folder_id = os.environ.get("YANDEX_FOLDER_ID", "")

if not api_key or not folder_id:
    raise RuntimeError("YANDEX_API_KEY and YANDEX_FOLDER_ID must be set in .env")

TEXT = "Dobryj den'! Vas privetstvuet Avrora -- AI-assistent kompanii InterSoft. Rasskazhite, chto u vas sluchilos', ya pomogu razobrat'sya."
TEXT_RU = "Добрый день! Вас приветствует Аврора — AI-ассистент компании ИнтерСофт. Расскажите, что у вас случилось, я помогу разобраться."

VOICES = [
    {"voice": "dasha", "role": "friendly", "desc": "Dasha (friendly)"},
    {"voice": "dasha", "role": "good", "desc": "Dasha (good)"},
    {"voice": "dasha", "role": "neutral", "desc": "Dasha (neutral)"},
    {"voice": "julia", "role": "neutral", "desc": "Julia (neutral)"},
    {"voice": "julia", "role": "strict", "desc": "Julia (strict)"},
    {"voice": "lera", "role": "friendly", "desc": "Lera (friendly)"},
    {"voice": "lera", "role": "neutral", "desc": "Lera (neutral)"},
    {"voice": "masha", "role": "friendly", "desc": "Masha (friendly)"},
    {"voice": "masha", "role": "good", "desc": "Masha (good)"},
    {"voice": "masha", "role": "strict", "desc": "Masha (strict)"},
]

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "pitch" / "audio" / "test-voices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

url = "https://tts.api.cloud.yandex.net/tts/v3/utteranceSynthesis"
headers = {
    "Authorization": f"Api-Key {api_key}",
    "x-folder-id": folder_id,
    "Content-Type": "application/json",
}

print(f"Generating {len(VOICES)} v3 voice samples...\n")

for v in VOICES:
    filename = f"{v['voice']}_{v['role']}.mp3"
    payload = {
        "text": TEXT_RU,
        "hints": [
            {"voice": v["voice"]},
            {"role": v["role"]},
            {"speed": 0.95},
        ],
        "outputAudioSpec": {
            "containerAudio": {
                "containerAudioType": "MP3",
            }
        },
        "loudnessNormalizationType": "LUFS",
    }

    try:
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            # v3 returns JSON with base64 audio or binary
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = resp.json()
                # v3 REST returns audioChunk in result
                if "result" in data and "audioChunk" in data["result"]:
                    import base64
                    audio_bytes = base64.b64decode(data["result"]["audioChunk"]["data"])
                    filepath = OUTPUT_DIR / filename
                    with open(filepath, "wb") as f:
                        f.write(audio_bytes)
                    size_kb = filepath.stat().st_size / 1024
                    print(f"  OK {filename:30s} ({size_kb:5.0f} KB) -- {v['desc']}")
                else:
                    print(f"  FAIL {filename:30s} -- unexpected JSON: {json.dumps(data)[:120]}")
            else:
                # Binary response
                filepath = OUTPUT_DIR / filename
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                size_kb = filepath.stat().st_size / 1024
                print(f"  OK {filename:30s} ({size_kb:5.0f} KB) -- {v['desc']}")
        else:
            print(f"  FAIL {filename:30s} -- HTTP {resp.status_code}: {resp.text[:120]}")
    except Exception as e:
        print(f"  FAIL {filename:30s} -- {e}")

print(f"\nFiles saved to: {OUTPUT_DIR}")
