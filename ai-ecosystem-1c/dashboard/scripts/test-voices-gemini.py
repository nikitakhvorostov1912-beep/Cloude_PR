"""Test Google Gemini TTS with Russian female voices.

Uses Gemini 2.5 Flash TTS API to generate warm, natural-sounding Russian voices.
Tests 3 best female voices: Sulafat (warm), Achernar (soft), Vindemiatrix (gentle).
"""
import os
import sys
import json
import base64
import struct
import wave
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# Load API key from .env
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
API_KEY = None
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("GOOGLE_API_KEY="):
            API_KEY = line.split("=", 1)[1].strip()
            break

if not API_KEY:
    API_KEY = os.environ.get("GOOGLE_API_KEY", "")

if not API_KEY:
    print("ERROR: GOOGLE_API_KEY not found in .env or environment")
    sys.exit(1)

print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:]}")

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "public" / "pitch" / "audio" / "test-voices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEXT_RU = "Добрый день! Вас приветствует Аврора — AI-ассистент компании ИнтерСофт. Расскажите, что у вас случилось, я помогу разобраться."

# Best warm/soft female voices from Chirp 3 HD / Gemini TTS
VOICES = [
    {"name": "Sulafat", "style": "Warm (тёплый)", "tag": "warm"},
    {"name": "Achernar", "style": "Soft (мягкий)", "tag": "soft"},
    {"name": "Vindemiatrix", "style": "Gentle (нежный)", "tag": "gentle"},
    {"name": "Aoede", "style": "Breezy (лёгкий)", "tag": "breezy"},
    {"name": "Leda", "style": "Youthful (молодой)", "tag": "young"},
]

# Gemini TTS API endpoint
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={API_KEY}"

print(f"\nGenerating {len(VOICES)} voice samples via Gemini TTS...\n")

results = []
for i, voice in enumerate(VOICES, 1):
    filename = f"gemini_{voice['tag']}.wav"
    filepath = OUTPUT_DIR / filename

    print(f"  {i}. {voice['name']} ({voice['style']})...", end=" ", flush=True)

    payload = {
        "contents": [{
            "parts": [{"text": TEXT_RU}]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice["name"]
                    }
                }
            }
        }
    }

    try:
        req = Request(
            API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urlopen(req, timeout=60)
        result = json.loads(resp.read().decode("utf-8"))

        # Extract audio from response
        candidates = result.get("candidates", [])
        if not candidates:
            print(f"FAIL (no candidates in response)")
            continue

        parts = candidates[0].get("content", {}).get("parts", [])
        audio_part = None
        for part in parts:
            if "inlineData" in part:
                audio_part = part["inlineData"]
                break

        if not audio_part:
            print(f"FAIL (no audio in response)")
            print(f"  Response keys: {list(result.keys())}")
            if candidates:
                print(f"  Candidate keys: {list(candidates[0].keys())}")
            continue

        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_part["data"])
        mime = audio_part.get("mimeType", "audio/wav")

        # Save audio
        if "wav" in mime or "pcm" in mime or "L16" in mime:
            # Raw PCM or WAV - save as WAV
            # Gemini returns PCM 24kHz 16-bit mono typically
            if audio_bytes[:4] == b"RIFF":
                # Already WAV
                filepath.write_bytes(audio_bytes)
            else:
                # Raw PCM - wrap in WAV header
                sample_rate = 24000
                channels = 1
                sample_width = 2  # 16-bit
                with wave.open(str(filepath), 'wb') as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(sample_width)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_bytes)
        else:
            # MP3 or other format
            ext = "mp3" if "mp3" in mime else "wav"
            out_path = filepath.with_suffix(f".{ext}")
            out_path.write_bytes(audio_bytes)
            filepath = out_path
            filename = out_path.name

        size_kb = filepath.stat().st_size / 1024
        print(f"OK ({size_kb:.0f} KB) [{mime}]")
        results.append({
            "file": filename,
            "name": voice["name"],
            "style": voice["style"],
            "size_kb": size_kb,
        })

    except HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"FAIL (HTTP {e.code})")
        print(f"  Error: {error_body[:300]}")
    except URLError as e:
        print(f"FAIL (URL error: {e.reason})")
    except Exception as e:
        print(f"FAIL ({e.__class__.__name__}: {e})")

# Also try Cloud TTS Chirp 3 HD if Gemini didn't work
if not results:
    print("\n\nGemini TTS failed. Trying Cloud TTS REST API (Neural2)...\n")

    CLOUD_URL = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_KEY}"
    CLOUD_VOICES = [
        {"name": "ru-RU-Neural2-A", "tag": "neural2a"},
        {"name": "ru-RU-Neural2-C", "tag": "neural2c"},
        {"name": "ru-RU-Wavenet-A", "tag": "waveneta"},
        {"name": "ru-RU-Wavenet-C", "tag": "wavenetc"},
        {"name": "ru-RU-Chirp3-HD-Sulafat", "tag": "chirp_sulafat"},
        {"name": "ru-RU-Chirp3-HD-Achernar", "tag": "chirp_achernar"},
    ]

    for i, voice in enumerate(CLOUD_VOICES, 1):
        filename = f"google_{voice['tag']}.mp3"
        filepath = OUTPUT_DIR / filename

        print(f"  {i}. {voice['name']}...", end=" ", flush=True)

        payload = {
            "input": {"text": TEXT_RU},
            "voice": {
                "languageCode": "ru-RU",
                "name": voice["name"],
            },
            "audioConfig": {
                "audioEncoding": "MP3",
            }
        }

        try:
            req = Request(
                CLOUD_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urlopen(req, timeout=60)
            result = json.loads(resp.read().decode("utf-8"))

            audio_b64 = result.get("audioContent", "")
            if not audio_b64:
                print("FAIL (no audioContent)")
                continue

            audio_bytes = base64.b64decode(audio_b64)
            filepath.write_bytes(audio_bytes)

            size_kb = filepath.stat().st_size / 1024
            print(f"OK ({size_kb:.0f} KB)")
            results.append({
                "file": filename,
                "name": voice["name"],
                "style": "Cloud TTS",
                "size_kb": size_kb,
            })
        except HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            print(f"FAIL (HTTP {e.code})")
            print(f"  Error: {error_body[:300]}")
        except Exception as e:
            print(f"FAIL ({e.__class__.__name__}: {e})")

print(f"\n{'='*50}")
print(f"Generated {len(results)} samples")
for r in results:
    print(f"  - {r['file']} ({r['name']}, {r['style']}, {r['size_kb']:.0f} KB)")
print(f"\nFiles: {OUTPUT_DIR}")
print(f"Listen: http://localhost:8899")
