"""Improve existing TTS voices:
1. OpenAI Nova → gpt-4o-mini-tts with Russian accent instructions
2. Yandex Marina → post-process with pedalboard to reduce roboticness
"""
import os
import sys
import json
import base64
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "public" / "pitch" / "audio" / "test-voices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load keys from .env
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
YANDEX_API_KEY = ""
YANDEX_FOLDER_ID = ""
OPENAI_API_KEY = ""
for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
    if line.startswith("YANDEX_API_KEY="): YANDEX_API_KEY = line.split("=", 1)[1].strip()
    if line.startswith("YANDEX_FOLDER_ID="): YANDEX_FOLDER_ID = line.split("=", 1)[1].strip()
    if line.startswith("OPENAI_API_KEY="): OPENAI_API_KEY = line.split("=", 1)[1].strip()

TEXT_RU = "Добрый день! Вас приветствует Аврора — AI-ассистент компании ИнтерСофт. Расскажите, что у вас случилось, я помогу разобраться."

# =============================================
# PART 1: Post-process Yandex Marina to reduce roboticness
# =============================================

def humanize_audio(input_path, output_path, intensity="medium"):
    """Add micro-variations, compression, warmth to make robotic voice more human."""
    from pedalboard import (
        Pedalboard, Chorus, Compressor, Gain,
        HighpassFilter, LowShelfFilter, Reverb,
    )
    from pedalboard.io import AudioFile

    if intensity == "light":
        effects = [
            HighpassFilter(cutoff_frequency_hz=80),
            Compressor(threshold_db=-20, ratio=2.0, attack_ms=5, release_ms=50),
            LowShelfFilter(cutoff_frequency_hz=300, gain_db=1.5),
            Gain(gain_db=1.5),
            Reverb(room_size=0.04, wet_level=0.05, dry_level=1.0),
        ]
    elif intensity == "medium":
        effects = [
            HighpassFilter(cutoff_frequency_hz=80),
            Chorus(rate_hz=0.3, depth=0.04, mix=0.12, feedback=0.0, centre_delay_ms=5),
            Compressor(threshold_db=-18, ratio=2.5, attack_ms=3, release_ms=80),
            LowShelfFilter(cutoff_frequency_hz=250, gain_db=2.0),
            Gain(gain_db=2.5),
            Reverb(room_size=0.06, wet_level=0.07, dry_level=1.0, damping=0.7),
        ]
    else:  # strong
        effects = [
            HighpassFilter(cutoff_frequency_hz=80),
            Chorus(rate_hz=0.4, depth=0.06, mix=0.18, feedback=0.0, centre_delay_ms=6),
            Compressor(threshold_db=-16, ratio=3.0, attack_ms=2, release_ms=60),
            LowShelfFilter(cutoff_frequency_hz=250, gain_db=3.0),
            Gain(gain_db=3.0),
            Reverb(room_size=0.08, wet_level=0.10, dry_level=1.0, damping=0.6),
        ]

    board = Pedalboard(effects)

    with AudioFile(str(input_path)) as f:
        with AudioFile(str(output_path), 'w', f.samplerate, f.num_channels) as o:
            while f.tell() < f.frames:
                chunk = f.read(int(f.samplerate))
                effected = board(chunk, f.samplerate, reset=False)
                o.write(effected)


print("=" * 50)
print("PART 1: Humanize Yandex Marina (post-processing)")
print("=" * 50)

# First generate fresh Marina friendly
print("\n  Generating fresh Marina friendly...", end=" ", flush=True)
marina_raw = OUTPUT_DIR / "marina_friendly_raw.mp3"
params = f"text={TEXT_RU}&voice=marina&emotion=friendly&lang=ru-RU&format=mp3&folderId={YANDEX_FOLDER_ID}"
try:
    req = Request(
        "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
        data=params.encode("utf-8"),
        headers={
            "Authorization": f"Api-Key {YANDEX_API_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
    )
    resp = urlopen(req, timeout=30)
    marina_raw.write_bytes(resp.read())
    print(f"OK ({marina_raw.stat().st_size / 1024:.0f} KB)")
except Exception as e:
    print(f"FAIL ({e})")
    marina_raw = OUTPUT_DIR / "marina_friendly.mp3"  # Use existing

# Apply 3 levels of humanization
for level in ["light", "medium", "strong"]:
    out_path = OUTPUT_DIR / f"marina_humanized_{level}.wav"
    print(f"  Humanizing ({level})...", end=" ", flush=True)
    try:
        humanize_audio(str(marina_raw), str(out_path), intensity=level)
        print(f"OK ({out_path.stat().st_size / 1024:.0f} KB)")
    except Exception as e:
        print(f"FAIL ({e})")

# Also humanize Alena (joy) - was good in previous test
alena_src = OUTPUT_DIR / "yandex_alena_joy.mp3"
if alena_src.exists():
    out_path = OUTPUT_DIR / "alena_humanized.wav"
    print(f"\n  Humanizing Alena (joy, medium)...", end=" ", flush=True)
    try:
        humanize_audio(str(alena_src), str(out_path), intensity="medium")
        print(f"OK ({out_path.stat().st_size / 1024:.0f} KB)")
    except Exception as e:
        print(f"FAIL ({e})")

# =============================================
# PART 2: OpenAI gpt-4o-mini-tts with instructions
# =============================================

print("\n" + "=" * 50)
print("PART 2: OpenAI gpt-4o-mini-tts with Russian instructions")
print("=" * 50)

if not OPENAI_API_KEY:
    # Try environment variable
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if OPENAI_API_KEY:
    instructions_variants = [
        {
            "tag": "nova_native",
            "label": "Nova (native Russian)",
            "voice": "nova",
            "instructions": (
                "You are a native Russian speaker from Moscow. "
                "Speak with perfect Russian pronunciation, natural warm intonation. "
                "No foreign accent whatsoever. Pronounce all Russian phonemes correctly: "
                "soft consonants, rolled R, proper stress on vowels. "
                "Speak at a natural conversational pace, warmly and friendly."
            ),
        },
        {
            "tag": "coral_native",
            "label": "Coral (native Russian)",
            "voice": "coral",
            "instructions": (
                "Ты — носитель русского языка из Москвы. "
                "Говори с идеальным русским произношением, тёплой и дружелюбной интонацией. "
                "Никакого иностранного акцента. Правильные ударения, мягкие согласные. "
                "Естественный разговорный темп."
            ),
        },
        {
            "tag": "shimmer_native",
            "label": "Shimmer (native Russian)",
            "voice": "shimmer",
            "instructions": (
                "You are a professional Russian voice actress. "
                "Speak warmly and naturally in Russian. Perfect pronunciation. "
                "No English accent. Sound like Yandex Alisa - friendly and human."
            ),
        },
    ]

    for v in instructions_variants:
        filename = f"openai_{v['tag']}.mp3"
        filepath = OUTPUT_DIR / filename
        print(f"\n  {v['label']}...", end=" ", flush=True)

        payload = {
            "model": "gpt-4o-mini-tts",
            "voice": v["voice"],
            "input": TEXT_RU,
            "instructions": v["instructions"],
        }

        try:
            req = Request(
                "https://api.openai.com/v1/audio/speech",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            resp = urlopen(req, timeout=60)
            audio = resp.read()
            filepath.write_bytes(audio)
            size_kb = len(audio) / 1024
            print(f"OK ({size_kb:.0f} KB)")

            # Also create humanized version
            humanized = OUTPUT_DIR / f"openai_{v['tag']}_warm.wav"
            print(f"    + humanizing...", end=" ", flush=True)
            humanize_audio(str(filepath), str(humanized), intensity="light")
            print(f"OK ({humanized.stat().st_size / 1024:.0f} KB)")
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:200]
            print(f"FAIL (HTTP {e.code}: {body})")
        except Exception as e:
            print(f"FAIL ({e})")
else:
    print("\n  SKIP: No OPENAI_API_KEY in .env")
    print("  To test, add OPENAI_API_KEY=sk-... to .env")

# Also humanize existing OpenAI nova
nova_src = OUTPUT_DIR / "openai_nova.mp3"
if nova_src.exists():
    out_path = OUTPUT_DIR / "openai_nova_warm.wav"
    print(f"\n  Humanizing existing Nova (light)...", end=" ", flush=True)
    try:
        humanize_audio(str(nova_src), str(out_path), intensity="light")
        print(f"OK ({out_path.stat().st_size / 1024:.0f} KB)")
    except Exception as e:
        print(f"FAIL ({e})")

print(f"\n{'=' * 50}")
print("Done! Listen at: http://localhost:8899")
