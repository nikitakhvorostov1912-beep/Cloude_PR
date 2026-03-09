"""Test Edge TTS — free Microsoft neural voices for Russian.

No API key needed. Uses the same voices as Microsoft Edge browser.
Generates multiple variations with pitch/rate adjustments for warmth.
"""
import asyncio
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "public" / "pitch" / "audio" / "test-voices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEXT_RU = "Добрый день! Вас приветствует Аврора — AI-ассистент компании ИнтерСофт. Расскажите, что у вас случилось, я помогу разобраться."

# All available Russian female voices + pitch/rate variations
VOICES = [
    # Dariya — newer voice, potentially warmer
    {"voice": "ru-RU-DariyaNeural", "tag": "dariya", "label": "Dariya (стандарт)", "pitch": "+0Hz", "rate": "+0%"},
    {"voice": "ru-RU-DariyaNeural", "tag": "dariya_warm", "label": "Dariya (тёплый)", "pitch": "-2Hz", "rate": "-5%"},
    {"voice": "ru-RU-DariyaNeural", "tag": "dariya_soft", "label": "Dariya (мягкий)", "pitch": "+1Hz", "rate": "-10%"},
    # Svetlana — classic voice
    {"voice": "ru-RU-SvetlanaNeural", "tag": "svetlana", "label": "Svetlana (стандарт)", "pitch": "+0Hz", "rate": "+0%"},
    {"voice": "ru-RU-SvetlanaNeural", "tag": "svetlana_warm", "label": "Svetlana (тёплый)", "pitch": "-2Hz", "rate": "-8%"},
]


async def generate_all():
    import edge_tts

    results = []
    print(f"Generating {len(VOICES)} Edge TTS samples (free, no API key)...\n")

    for i, v in enumerate(VOICES, 1):
        filename = f"edge_{v['tag']}.mp3"
        filepath = OUTPUT_DIR / filename
        print(f"  {i}. {v['label']}...", end=" ", flush=True)

        try:
            communicate = edge_tts.Communicate(
                TEXT_RU,
                v["voice"],
                pitch=v["pitch"],
                rate=v["rate"],
            )
            await communicate.save(str(filepath))
            size_kb = filepath.stat().st_size / 1024
            print(f"OK ({size_kb:.0f} KB)")
            results.append({
                "file": filename,
                "label": v["label"],
                "size_kb": size_kb,
            })
        except Exception as e:
            print(f"FAIL ({e})")

    return results


results = asyncio.run(generate_all())

print(f"\n{'='*50}")
print(f"Generated {len(results)} samples")
for r in results:
    print(f"  - {r['file']} — {r['label']} ({r['size_kb']:.0f} KB)")
print(f"\nListen: http://localhost:8899")
