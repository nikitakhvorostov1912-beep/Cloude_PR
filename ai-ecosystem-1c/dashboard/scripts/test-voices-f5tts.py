"""Test F5-TTS with Russian fine-tuned model for Aurora voice.

Monkey-patches torchaudio.load to use soundfile backend,
avoiding torchcodec/FFmpeg dependency on Windows.
"""
import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from pathlib import Path

# ---- Monkey-patch torchaudio.load to avoid torchcodec ----
import torch
import soundfile as sf
import numpy as np

def _patched_torchaudio_load(filepath, **kwargs):
    """Load audio using soundfile instead of torchcodec."""
    data, sr = sf.read(str(filepath), dtype="float32")
    if data.ndim == 1:
        tensor = torch.from_numpy(data).unsqueeze(0)  # (1, samples)
    else:
        tensor = torch.from_numpy(data.T)  # (channels, samples)
    return tensor, sr

import torchaudio
torchaudio.load = _patched_torchaudio_load

# Also patch torchaudio.save
def _patched_torchaudio_save(filepath, tensor, sample_rate, **kwargs):
    """Save audio using soundfile instead of torchcodec."""
    if tensor.dim() == 2:
        data = tensor.squeeze(0).numpy()
    else:
        data = tensor.numpy()
    sf.write(str(filepath), data, sample_rate)

torchaudio.save = _patched_torchaudio_save
# ---- End monkey-patch ----

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "public" / "pitch" / "audio" / "test-voices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REF_AUDIO = OUTPUT_DIR / "references" / "ref_05_katya.wav"
if not REF_AUDIO.exists():
    print(f"ERROR: Reference audio not found: {REF_AUDIO}")
    sys.exit(1)

TEXT_RU = "Добрый день! Вас приветствует Аврора — AI-ассистент компании ИнтерСофт. Расскажите, что у вас случилось, я помогу разобраться."

print("Step 1: Downloading Russian F5-TTS model...")
from huggingface_hub import hf_hub_download

MODEL_FILES = [
    ("Misha24-10/F5-TTS_RUSSIAN", "F5TTS_v1_Base_v2/model_last.pt"),
    ("Misha24-10/F5-TTS_RUSSIAN", "F5TTS_v1_Base_v2/model_last_inference.safetensors"),
    ("Misha24-10/F5-TTS_RUSSIAN", "F5TTS_v1_Base/model_240000.pt"),
]

ckpt_path = None
for repo, fname in MODEL_FILES:
    try:
        print(f"  Trying {fname}...", end=" ", flush=True)
        ckpt_path = hf_hub_download(repo_id=repo, filename=fname)
        print(f"OK ({Path(ckpt_path).stat().st_size / 1024 / 1024:.0f} MB)")
        break
    except Exception as e:
        print(f"SKIP ({e.__class__.__name__})")

if ckpt_path is None:
    print("  All model files failed. Using base F5-TTS model...")

print("\nStep 2: Initializing F5-TTS on CPU...")
from f5_tts.api import F5TTS

if ckpt_path:
    tts = F5TTS(
        model="F5TTS_v1_Base",
        ckpt_file=ckpt_path,
        device="cpu",
    )
else:
    tts = F5TTS(device="cpu")

print("  Model loaded OK")

print(f"\nStep 3: Generating voice sample on CPU...")
print(f"  Reference: {REF_AUDIO.name}")
print(f"  Text: {TEXT_RU[:60]}...\n")

filename = "f5tts_ru.wav"
filepath = OUTPUT_DIR / filename
try:
    print(f"  Generating (32 steps, CPU — may take 1-5 min)...", flush=True)
    ref_text = "Здравствуйте, меня зовут Катя, я профессиональная актриса озвучивания."
    wav, sr, _ = tts.infer(
        ref_file=str(REF_AUDIO),
        ref_text=ref_text,
        gen_text=TEXT_RU,
        file_wave=str(filepath),
        nfe_step=32,
        cfg_strength=2.0,
        speed=1.0,
    )
    size_kb = filepath.stat().st_size / 1024
    print(f"  OK: {filename} ({size_kb:.0f} KB)")
except Exception as e:
    print(f"  FAIL: {e}")
    import traceback
    traceback.print_exc()

print(f"\nFiles saved to: {OUTPUT_DIR}")
