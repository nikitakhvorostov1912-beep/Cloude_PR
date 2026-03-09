"""Test ALL Yandex SpeechKit female voices with different emotions.

Uses existing Yandex API key from .env. Tests voices not yet tried:
- Alena (joyful) - бывший oksana, радостный
- Jane (joyful) - 3 эмоции
- Masha (friendly, joyful) - v3
- Marina (whisper) - шёпот, мягче
- Julia (neutral) - v3
"""
import os
import sys
import json
import base64
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# Load keys from .env
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
API_KEY = ""
FOLDER_ID = ""
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("YANDEX_API_KEY="):
            API_KEY = line.split("=", 1)[1].strip()
        if line.startswith("YANDEX_FOLDER_ID="):
            FOLDER_ID = line.split("=", 1)[1].strip()

if not API_KEY or not FOLDER_ID:
    print("ERROR: YANDEX_API_KEY or YANDEX_FOLDER_ID not found")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "public" / "pitch" / "audio" / "test-voices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEXT_RU = "Добрый день! Вас приветствует Аврора — AI-ассистент компании ИнтерСофт. Расскажите, что у вас случилось, я помогу разобраться."

# V1 API voices (alena, jane, marina, omazh)
V1_VOICES = [
    {"voice": "alena", "emotion": "good", "label": "Alena (радостная)", "tag": "alena_joy"},
    {"voice": "alena", "emotion": "neutral", "label": "Alena (нейтральная)", "tag": "alena_neutral"},
    {"voice": "jane", "emotion": "good", "label": "Jane (радостная)", "tag": "jane_joy"},
    {"voice": "jane", "emotion": "neutral", "label": "Jane (нейтральная)", "tag": "jane_neutral"},
    {"voice": "marina", "emotion": "whisper", "label": "Marina (шёпот)", "tag": "marina_whisper"},
    {"voice": "omazh", "emotion": "neutral", "label": "Omazh (нейтральная)", "tag": "omazh_neutral"},
]

# V3 API voices (dasha, julia, lera, masha, etc.)
V3_VOICES = [
    {"voice": "masha", "role": "friendly", "label": "Masha (дружелюбная)", "tag": "masha_friendly"},
    {"voice": "masha", "role": "good", "label": "Masha (радостная)", "tag": "masha_joy"},
    {"voice": "julia", "role": "neutral", "label": "Julia (нейтральная)", "tag": "julia_neutral"},
    {"voice": "julia", "role": "strict", "label": "Julia (строгая)", "tag": "julia_strict"},
    {"voice": "dasha", "role": "good", "label": "Dasha (радостная)", "tag": "dasha_joy"},
    {"voice": "lera", "role": "friendly", "label": "Lera (дружелюбная v2)", "tag": "lera_friendly2"},
]

V1_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
V3_URL = "https://tts.api.cloud.yandex.net/tts/v3/utteranceSynthesis"

results = []

print(f"Generating Yandex V1 voices...\n")
for i, v in enumerate(V1_VOICES, 1):
    filename = f"yandex_{v['tag']}.mp3"
    filepath = OUTPUT_DIR / filename
    print(f"  {i}. {v['label']}...", end=" ", flush=True)

    params = f"text={TEXT_RU}&voice={v['voice']}&emotion={v['emotion']}&lang=ru-RU&format=mp3&folderId={FOLDER_ID}"
    try:
        req = Request(V1_URL, data=params.encode("utf-8"), headers={
            "Authorization": f"Api-Key {API_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        })
        resp = urlopen(req, timeout=30)
        audio = resp.read()
        filepath.write_bytes(audio)
        size_kb = len(audio) / 1024
        print(f"OK ({size_kb:.0f} KB)")
        results.append({"file": filename, "label": v["label"], "size_kb": size_kb, "api": "v1"})
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        print(f"FAIL (HTTP {e.code}: {body})")
    except Exception as e:
        print(f"FAIL ({e})")

print(f"\nGenerating Yandex V3 voices...\n")
for i, v in enumerate(V3_VOICES, 1):
    filename = f"yandex_{v['tag']}.mp3"
    filepath = OUTPUT_DIR / filename
    print(f"  {i}. {v['label']}...", end=" ", flush=True)

    payload = {
        "text": TEXT_RU,
        "outputAudioSpec": {
            "containerAudio": {"containerAudioType": "MP3"}
        },
        "hints": [
            {"voice": v["voice"]},
            {"role": v["role"]},
        ],
        "loudnessNormalizationType": "LUFS",
    }

    try:
        req = Request(V3_URL, data=json.dumps(payload).encode("utf-8"), headers={
            "Authorization": f"Api-Key {API_KEY}",
            "Content-Type": "application/json",
            "x-folder-id": FOLDER_ID,
        })
        resp = urlopen(req, timeout=30)

        # V3 returns streaming chunks as JSON lines
        audio_chunks = []
        raw = resp.read()

        # Try parsing as JSON lines (each line is a JSON with audioChunk.data)
        for line in raw.split(b"\n"):
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
                if "result" in chunk and "audioChunk" in chunk["result"]:
                    audio_b64 = chunk["result"]["audioChunk"]["data"]
                    audio_chunks.append(base64.b64decode(audio_b64))
            except:
                pass

        if audio_chunks:
            audio_data = b"".join(audio_chunks)
            filepath.write_bytes(audio_data)
            size_kb = len(audio_data) / 1024
            print(f"OK ({size_kb:.0f} KB)")
            results.append({"file": filename, "label": v["label"], "size_kb": size_kb, "api": "v3"})
        else:
            # Maybe raw audio response
            if len(raw) > 1000:
                filepath.write_bytes(raw)
                size_kb = len(raw) / 1024
                print(f"OK-raw ({size_kb:.0f} KB)")
                results.append({"file": filename, "label": v["label"], "size_kb": size_kb, "api": "v3"})
            else:
                print(f"FAIL (empty audio, response: {raw[:200]})")
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        print(f"FAIL (HTTP {e.code}: {body})")
    except Exception as e:
        print(f"FAIL ({e})")

print(f"\n{'='*50}")
print(f"Generated {len(results)} samples total")
for r in results:
    print(f"  - {r['file']} — {r['label']} ({r['size_kb']:.0f} KB) [{r['api']}]")
print(f"\nListen: http://localhost:8899")
