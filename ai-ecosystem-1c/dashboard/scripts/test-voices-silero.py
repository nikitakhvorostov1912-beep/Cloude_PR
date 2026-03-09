"""Test Silero TTS v5 female voices for Aurora."""
import torch
import scipy.io.wavfile as wavfile
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "pitch" / "audio" / "test-voices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEXT = "Добрый день! Вас приветствует Аврора - AI-ассистент компании ИнтерСофт. Расскажите, что у вас случилось, я помогу разобраться."

print("Loading Silero TTS v5 model...")
model, _ = torch.hub.load(
    repo_or_dir='snakers4/silero-models',
    model='silero_tts',
    language='ru',
    speaker='v3_1_ru'
)
model.to('cpu')

# Female voices available in Silero ru v3_1
VOICES = ['xenia', 'kseniya', 'baya']

print(f"\nGenerating {len(VOICES)} Silero v5 voice samples...\n")

for voice in VOICES:
    filename = f"silero_{voice}.wav"
    try:
        audio = model.apply_tts(
            text=TEXT,
            speaker=voice,
            sample_rate=48000,
            put_accent=True,
            put_yo=True
        )
        filepath = OUTPUT_DIR / filename
        audio_np = (audio.numpy() * 32767).astype(np.int16)
        wavfile.write(str(filepath), 48000, audio_np)
        size_kb = filepath.stat().st_size / 1024
        print(f"  OK {filename:30s} ({size_kb:5.0f} KB) -- {voice}")
    except Exception as e:
        print(f"  FAIL {filename:30s} -- {e}")

# Also try all available speakers to find more female voices
print("\nAll available speakers:")
print(model.speakers)
print(f"\nFiles saved to: {OUTPUT_DIR}")
