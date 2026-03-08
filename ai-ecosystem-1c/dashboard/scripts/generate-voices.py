"""
Generate natural Russian voice audio files for Aurora AI-assistant demo.

Supports four TTS engines (priority order):
  1. ElevenLabs (Soft Female Russian) — Warmest voice, FREE tier (9/10)
  2. OpenAI TTS (shimmer/tts-1-hd) — Most natural (9/10)
  3. Yandex SpeechKit (marina/friendly) — Best Russian (10/10)
  4. Edge TTS (SvetlanaNeural) — Free fallback

Usage:
  # ElevenLabs (requires ELEVENLABS_API_KEY, FREE tier):
  python scripts/generate-voices.py --engine elevenlabs

  # OpenAI TTS (requires OPENAI_API_KEY):
  python scripts/generate-voices.py --engine openai

  # Yandex SpeechKit (requires YANDEX_API_KEY + YANDEX_FOLDER_ID):
  python scripts/generate-voices.py --engine yandex

  # Edge TTS (free, no API key):
  python scripts/generate-voices.py --engine edge

  # Auto-detect (tries ElevenLabs → OpenAI → Yandex → Edge):
  python scripts/generate-voices.py
"""

import asyncio
import argparse
import os
from pathlib import Path

# Load .env from project root (ai-ecosystem-1c/)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
OUTPUT_DIR = SCRIPT_DIR.parent / "public" / "pitch" / "audio"

# Dialogue script — must match demo-simulator.tsx SCRIPT array
LINES = [
    {
        "id": "op-1",
        "speaker": "aurora",
        "text": "Добрый день! Вас приветствует Аврора — AI-ассистент компании ИнтерСофт. Расскажите, что у вас случилось, я помогу разобраться.",
    },
    {
        "id": "cl-1",
        "speaker": "client",
        "text": "Добрый день! У нас тут всё встало. Программа ЗУП — после вчерашнего обновления не можем сформировать расчёт зарплаты. Пишет «Неверный расчётный период». Завтра выплата, 150 человек ждут зарплату!",
    },
    {
        "id": "op-2",
        "speaker": "aurora",
        "text": "Понимаю, ситуация срочная — сейчас разберёмся. Подскажите, какая у вас версия ЗУП? И обновление было плановым или автоматическим?",
    },
    {
        "id": "cl-2",
        "speaker": "client",
        "text": "Версия 3.1.28, обновление прилетело автоматически вчера вечером. С утра при открытии расчёта — ошибка. Пробовали перезапускать сервер — не помогает.",
    },
    {
        "id": "op-3",
        "speaker": "aurora",
        "text": "Нашла решение! Это известная проблема обновления 3.1.28. Откройте «Настройки расчёта зарплаты», в поле «Расчётный период» установите текущий месяц вручную, затем через «Сервис» обновите регламентный отчёт. После этого расчёт должен пройти.",
    },
    {
        "id": "cl-3",
        "speaker": "client",
        "text": "Сейчас попробую... Да! Заработало! Вот это скорость! Спасибо огромное, я думал, придётся вызывать программиста.",
    },
]


def load_env():
    """Load .env file into environment."""
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


# ══════════════════════════════════════════════════════════════
#  ElevenLabs Engine (Soft Female Russian / multilingual_v2)
# ══════════════════════════════════════════════════════════════

def generate_elevenlabs(line: dict) -> None:
    """Generate MP3 via ElevenLabs API (multilingual_v2, warm Russian voices)."""
    from elevenlabs import ElevenLabs

    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY must be set in environment or .env\n"
            "Get FREE key at: https://elevenlabs.io/app/settings/api-keys"
        )

    client = ElevenLabs(api_key=api_key)

    # Aurora = soft warm female voice, Client = male voice
    if line["speaker"] == "aurora":
        # "Soft Female Russian" from Voice Library — warm, gentle, expressive
        voice_id = "ymDCYd8puC7gYjxIamPt"
    else:
        # "Adam" — default male voice (good for Russian too)
        voice_id = "pNInz6obpgDQGcFmaJgB"

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=line["text"],
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    filepath = OUTPUT_DIR / f"{line['id']}.mp3"
    with open(filepath, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    size_kb = filepath.stat().st_size / 1024
    print(f"  OK {line['id']}.mp3 ({size_kb:.0f} KB) - elevenlabs/{voice_id[:8]}")


# ══════════════════════════════════════════════════════════════
#  OpenAI TTS Engine (shimmer / tts-1-hd)
# ══════════════════════════════════════════════════════════════

def generate_openai(line: dict) -> None:
    """Generate MP3 via OpenAI TTS API (nova for Aurora, echo for client)."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY must be set in environment or .env\n"
            "Get it at: https://platform.openai.com/api-keys"
        )

    client = OpenAI(api_key=api_key)

    # Aurora = nova (warm, natural female — best for Russian)
    # Client = echo (male)
    if line["speaker"] == "aurora":
        voice = "nova"
        speed = 0.95  # slightly slower for warmth
    else:
        voice = "echo"
        speed = 1.0

    response = client.audio.speech.create(
        model="tts-1-hd",
        voice=voice,
        input=line["text"],
        response_format="mp3",
        speed=speed,
    )

    filepath = OUTPUT_DIR / f"{line['id']}.mp3"
    response.stream_to_file(str(filepath))

    size_kb = filepath.stat().st_size / 1024
    print(f"  OK {line['id']}.mp3 ({size_kb:.0f} KB) - openai/{voice}/tts-1-hd")


# ══════════════════════════════════════════════════════════════
#  Yandex SpeechKit Engine
# ══════════════════════════════════════════════════════════════

def generate_yandex(line: dict) -> None:
    """Generate MP3 via Yandex SpeechKit API (marina/friendly)."""
    import requests

    api_key = os.environ.get("YANDEX_API_KEY", "")
    folder_id = os.environ.get("YANDEX_FOLDER_ID", "")

    if not api_key or not folder_id:
        raise RuntimeError(
            "YANDEX_API_KEY and YANDEX_FOLDER_ID must be set in .env\n"
            "Get them at: https://yandex.cloud/ru/docs/speechkit/quickstart"
        )

    # Aurora = marina/friendly, Client = filipp/neutral
    if line["speaker"] == "aurora":
        voice = "marina"
        emotion = "friendly"
        speed = "0.95"
    else:
        voice = "filipp"
        emotion = "neutral"
        speed = "1.0"

    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    headers = {"Authorization": f"Api-Key {api_key}"}
    data = {
        "text": line["text"],
        "lang": "ru-RU",
        "voice": voice,
        "emotion": emotion,
        "format": "mp3",
        "folderId": folder_id,
        "speed": speed,
        "sampleRateHertz": "48000",
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 200:
        raise RuntimeError(
            f"Yandex SpeechKit error {response.status_code}: {response.text[:200]}"
        )

    filepath = OUTPUT_DIR / f"{line['id']}.mp3"
    with open(filepath, "wb") as f:
        f.write(response.content)

    size_kb = filepath.stat().st_size / 1024
    print(f"  OK {line['id']}.mp3 ({size_kb:.0f} KB) - yandex/{voice}/{emotion}")


# ══════════════════════════════════════════════════════════════
#  Edge TTS Engine (Free Fallback)
# ══════════════════════════════════════════════════════════════

async def generate_edge(line: dict) -> None:
    """Generate MP3 via Microsoft Edge TTS (SvetlanaNeural)."""
    import edge_tts

    # Aurora = SvetlanaNeural (female), Client = DmitryNeural
    if line["speaker"] == "aurora":
        voice = "ru-RU-SvetlanaNeural"
        rate = "-5%"
    else:
        voice = "ru-RU-DmitryNeural"
        rate = "+0%"

    filepath = OUTPUT_DIR / f"{line['id']}.mp3"
    communicate = edge_tts.Communicate(
        text=line["text"],
        voice=voice,
        rate=rate,
    )
    await communicate.save(str(filepath))

    size_kb = filepath.stat().st_size / 1024
    print(f"  OK {line['id']}.mp3 ({size_kb:.0f} KB) - edge/{voice}")


# ══════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════

def detect_engine() -> str:
    """Auto-detect best available engine: ElevenLabs → OpenAI → Yandex → Edge."""
    if os.environ.get("ELEVENLABS_API_KEY", ""):
        return "elevenlabs"
    if os.environ.get("OPENAI_API_KEY", ""):
        return "openai"
    if os.environ.get("YANDEX_API_KEY", "") and os.environ.get("YANDEX_FOLDER_ID", ""):
        return "yandex"
    return "edge"


async def main():
    parser = argparse.ArgumentParser(description="Generate voice files for Aurora demo")
    parser.add_argument(
        "--engine",
        choices=["elevenlabs", "openai", "yandex", "edge", "auto"],
        default="auto",
        help="TTS engine: elevenlabs (warm, free), openai, yandex, edge (free), auto",
    )
    args = parser.parse_args()

    load_env()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    engine = args.engine if args.engine != "auto" else detect_engine()
    print(f"Engine: {engine.upper()}")
    print(f"Generating {len(LINES)} audio files...\n")

    for line in LINES:
        if engine == "elevenlabs":
            generate_elevenlabs(line)
        elif engine == "openai":
            generate_openai(line)
        elif engine == "yandex":
            generate_yandex(line)
        else:
            await generate_edge(line)

    print(f"\nDone! Files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
