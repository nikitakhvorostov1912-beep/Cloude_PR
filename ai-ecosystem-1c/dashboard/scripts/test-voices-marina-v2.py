"""Marina v2 — aggressive humanization with speed correction.

User feedback: "голос стал лучше, но слышится робот и тембр замедленный"
Fix: increase speed, stronger pitch jitter, formant warmth, less chorus (causes slowdown).
"""
import numpy as np
import soundfile as sf
from pathlib import Path
from pedalboard import (
    Pedalboard, Compressor, Gain, HighpassFilter,
    LowShelfFilter, HighShelfFilter, Reverb, PitchShift,
)
from pedalboard.io import AudioFile

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "pitch" / "audio" / "test-voices"

# Source: existing marina_friendly.mp3
SRC = OUTPUT_DIR / "marina_friendly.mp3"
if not SRC.exists():
    print(f"ERROR: {SRC} not found")
    exit(1)

print("Marina v2 — advanced humanization\n")


def add_pitch_jitter(audio_data, sr, jitter_cents=3.0, rate_hz=5.0):
    """Add micro pitch variations like a real human voice.

    Human voice naturally has ~2-5 cents of pitch jitter at 3-8 Hz.
    This is the #1 cue that makes synthetic speech sound robotic.
    """
    n = len(audio_data)
    t = np.arange(n) / sr

    # Multi-frequency modulation (more natural than single sine)
    mod = (
        jitter_cents * 0.6 * np.sin(2 * np.pi * rate_hz * t)
        + jitter_cents * 0.3 * np.sin(2 * np.pi * (rate_hz * 1.7) * t + 0.5)
        + jitter_cents * 0.1 * np.sin(2 * np.pi * (rate_hz * 3.1) * t + 1.2)
    )

    # Convert cents to sample offset
    # 1 cent = factor of 2^(1/1200)
    factor = 2.0 ** (mod / 1200.0)

    # Resample using linear interpolation
    cumulative = np.cumsum(factor)
    cumulative = cumulative / cumulative[-1] * (n - 1)

    indices = np.clip(cumulative, 0, n - 1)
    idx_floor = indices.astype(int)
    idx_ceil = np.minimum(idx_floor + 1, n - 1)
    frac = indices - idx_floor

    result = audio_data[idx_floor] * (1 - frac) + audio_data[idx_ceil] * frac
    return result.astype(np.float32)


def speed_up_audio(audio_data, sr, factor=1.08):
    """Speed up without changing pitch (simple resampling)."""
    n_out = int(len(audio_data) / factor)
    indices = np.linspace(0, len(audio_data) - 1, n_out)
    idx_floor = indices.astype(int)
    idx_ceil = np.minimum(idx_floor + 1, len(audio_data) - 1)
    frac = indices - idx_floor
    result = audio_data[idx_floor] * (1 - frac) + audio_data[idx_ceil] * frac
    return result.astype(np.float32)


def add_breath_noise(audio_data, sr, level=0.001):
    """Add very subtle breath-like noise for realism."""
    noise = np.random.randn(len(audio_data)).astype(np.float32) * level
    # Low-pass the noise to make it breath-like (not hiss)
    from scipy.signal import butter, lfilter
    b, a = butter(4, 2000 / (sr / 2), btype='low')
    noise = lfilter(b, a, noise).astype(np.float32)
    return audio_data + noise


# Read source audio
data, sr = sf.read(str(SRC), dtype='float32')
if data.ndim > 1:
    data = data[:, 0]  # mono

print(f"Source: {SRC.name} ({len(data)/sr:.1f}s, {sr}Hz)\n")

# ============================================
# Variant 1: Speed + Jitter + Warm EQ
# ============================================
name = "marina_v2_fast"
print(f"  {name}...", end=" ", flush=True)
out = speed_up_audio(data, sr, factor=1.10)  # 10% faster
out = add_pitch_jitter(out, sr, jitter_cents=4.0, rate_hz=5.5)
path = OUTPUT_DIR / f"{name}.wav"
sf.write(str(path), out, sr)
# Apply EQ via pedalboard
board = Pedalboard([
    HighpassFilter(cutoff_frequency_hz=90),
    Compressor(threshold_db=-18, ratio=2.0, attack_ms=5, release_ms=60),
    LowShelfFilter(cutoff_frequency_hz=280, gain_db=2.5),
    HighShelfFilter(cutoff_frequency_hz=6000, gain_db=1.0),
    Gain(gain_db=2.0),
    Reverb(room_size=0.03, wet_level=0.04, dry_level=1.0),
])
with AudioFile(str(path)) as f:
    with AudioFile(str(path) + ".tmp.wav", 'w', f.samplerate, f.num_channels) as o:
        while f.tell() < f.frames:
            chunk = f.read(int(f.samplerate))
            o.write(board(chunk, f.samplerate, reset=False))
Path(str(path) + ".tmp.wav").replace(path)
print(f"OK ({path.stat().st_size/1024:.0f} KB)")

# ============================================
# Variant 2: Speed + Strong Jitter + Breath
# ============================================
name = "marina_v2_alive"
print(f"  {name}...", end=" ", flush=True)
out = speed_up_audio(data, sr, factor=1.12)  # 12% faster
out = add_pitch_jitter(out, sr, jitter_cents=5.0, rate_hz=4.5)
out = add_breath_noise(out, sr, level=0.0008)
path = OUTPUT_DIR / f"{name}.wav"
sf.write(str(path), out, sr)
board = Pedalboard([
    HighpassFilter(cutoff_frequency_hz=85),
    Compressor(threshold_db=-16, ratio=2.5, attack_ms=3, release_ms=50),
    LowShelfFilter(cutoff_frequency_hz=300, gain_db=3.0),
    HighShelfFilter(cutoff_frequency_hz=5500, gain_db=1.5),
    Gain(gain_db=2.5),
    Reverb(room_size=0.04, wet_level=0.05, dry_level=1.0),
])
with AudioFile(str(path)) as f:
    with AudioFile(str(path) + ".tmp.wav", 'w', f.samplerate, f.num_channels) as o:
        while f.tell() < f.frames:
            chunk = f.read(int(f.samplerate))
            o.write(board(chunk, f.samplerate, reset=False))
Path(str(path) + ".tmp.wav").replace(path)
print(f"OK ({path.stat().st_size/1024:.0f} KB)")

# ============================================
# Variant 3: Speed + Jitter + Pitch up slightly
# ============================================
name = "marina_v2_bright"
print(f"  {name}...", end=" ", flush=True)
out = speed_up_audio(data, sr, factor=1.08)
out = add_pitch_jitter(out, sr, jitter_cents=4.0, rate_hz=6.0)
path = OUTPUT_DIR / f"{name}.wav"
sf.write(str(path), out, sr)
board = Pedalboard([
    HighpassFilter(cutoff_frequency_hz=90),
    PitchShift(semitones=0.5),  # Slightly higher pitch
    Compressor(threshold_db=-18, ratio=2.0, attack_ms=5, release_ms=70),
    LowShelfFilter(cutoff_frequency_hz=250, gain_db=2.0),
    HighShelfFilter(cutoff_frequency_hz=5000, gain_db=2.0),
    Gain(gain_db=2.0),
    Reverb(room_size=0.03, wet_level=0.04, dry_level=1.0),
])
with AudioFile(str(path)) as f:
    with AudioFile(str(path) + ".tmp.wav", 'w', f.samplerate, f.num_channels) as o:
        while f.tell() < f.frames:
            chunk = f.read(int(f.samplerate))
            o.write(board(chunk, f.samplerate, reset=False))
Path(str(path) + ".tmp.wav").replace(path)
print(f"OK ({path.stat().st_size/1024:.0f} KB)")

# ============================================
# Variant 4: Maximum humanization — jitter + speed + pitch up + breath + warm
# ============================================
name = "marina_v2_max"
print(f"  {name}...", end=" ", flush=True)
out = speed_up_audio(data, sr, factor=1.15)  # 15% faster
out = add_pitch_jitter(out, sr, jitter_cents=6.0, rate_hz=5.0)
out = add_breath_noise(out, sr, level=0.0006)
path = OUTPUT_DIR / f"{name}.wav"
sf.write(str(path), out, sr)
board = Pedalboard([
    HighpassFilter(cutoff_frequency_hz=85),
    PitchShift(semitones=0.7),
    Compressor(threshold_db=-15, ratio=3.0, attack_ms=2, release_ms=40),
    LowShelfFilter(cutoff_frequency_hz=280, gain_db=2.5),
    HighShelfFilter(cutoff_frequency_hz=5000, gain_db=2.0),
    Gain(gain_db=3.0),
    Reverb(room_size=0.05, wet_level=0.06, dry_level=1.0, damping=0.6),
])
with AudioFile(str(path)) as f:
    with AudioFile(str(path) + ".tmp.wav", 'w', f.samplerate, f.num_channels) as o:
        while f.tell() < f.frames:
            chunk = f.read(int(f.samplerate))
            o.write(board(chunk, f.samplerate, reset=False))
Path(str(path) + ".tmp.wav").replace(path)
print(f"OK ({path.stat().st_size/1024:.0f} KB)")

# ============================================
# Variant 5: Alena joy — same treatment (best Yandex voice)
# ============================================
alena_src = OUTPUT_DIR / "yandex_alena_joy.mp3"
if alena_src.exists():
    name = "alena_v2_alive"
    print(f"  {name}...", end=" ", flush=True)
    adata, asr = sf.read(str(alena_src), dtype='float32')
    if adata.ndim > 1:
        adata = adata[:, 0]
    out = speed_up_audio(adata, asr, factor=1.10)
    out = add_pitch_jitter(out, asr, jitter_cents=4.5, rate_hz=5.0)
    out = add_breath_noise(out, asr, level=0.0006)
    path = OUTPUT_DIR / f"{name}.wav"
    sf.write(str(path), out, asr)
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=85),
        PitchShift(semitones=0.3),
        Compressor(threshold_db=-17, ratio=2.5, attack_ms=4, release_ms=60),
        LowShelfFilter(cutoff_frequency_hz=280, gain_db=2.5),
        HighShelfFilter(cutoff_frequency_hz=5500, gain_db=1.5),
        Gain(gain_db=2.0),
        Reverb(room_size=0.04, wet_level=0.05, dry_level=1.0),
    ])
    with AudioFile(str(path)) as f:
        with AudioFile(str(path) + ".tmp.wav", 'w', f.samplerate, f.num_channels) as o:
            while f.tell() < f.frames:
                chunk = f.read(int(f.samplerate))
                o.write(board(chunk, f.samplerate, reset=False))
    Path(str(path) + ".tmp.wav").replace(path)
    print(f"OK ({path.stat().st_size/1024:.0f} KB)")

print(f"\nDone! Listen: http://localhost:8899")
