"""Fix: convert all WAV to MP3 for browser compatibility + improve Nova processing."""
import numpy as np
import soundfile as sf
from pathlib import Path
from pydub import AudioSegment
from pedalboard import (
    Pedalboard, Compressor, Gain, HighpassFilter,
    LowShelfFilter, HighShelfFilter, Reverb, PitchShift,
)
from pedalboard.io import AudioFile

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "pitch" / "audio" / "test-voices"


def wav_to_mp3(wav_path, mp3_path):
    """Convert WAV to MP3 for browser compatibility."""
    audio = AudioSegment.from_wav(str(wav_path))
    audio.export(str(mp3_path), format="mp3", bitrate="192k")


def add_pitch_jitter(audio_data, sr, jitter_cents=4.0, rate_hz=5.0):
    """Add micro pitch variations like real human voice."""
    n = len(audio_data)
    t = np.arange(n) / sr
    mod = (
        jitter_cents * 0.6 * np.sin(2 * np.pi * rate_hz * t)
        + jitter_cents * 0.3 * np.sin(2 * np.pi * (rate_hz * 1.7) * t + 0.5)
        + jitter_cents * 0.1 * np.sin(2 * np.pi * (rate_hz * 3.1) * t + 1.2)
    )
    factor = 2.0 ** (mod / 1200.0)
    cumulative = np.cumsum(factor)
    cumulative = cumulative / cumulative[-1] * (n - 1)
    indices = np.clip(cumulative, 0, n - 1)
    idx_floor = indices.astype(int)
    idx_ceil = np.minimum(idx_floor + 1, n - 1)
    frac = indices - idx_floor
    return (audio_data[idx_floor] * (1 - frac) + audio_data[idx_ceil] * frac).astype(np.float32)


def speed_up_audio(audio_data, sr, factor=1.08):
    """Speed up via resampling."""
    n_out = int(len(audio_data) / factor)
    indices = np.linspace(0, len(audio_data) - 1, n_out)
    idx_floor = indices.astype(int)
    idx_ceil = np.minimum(idx_floor + 1, len(audio_data) - 1)
    frac = indices - idx_floor
    return (audio_data[idx_floor] * (1 - frac) + audio_data[idx_ceil] * frac).astype(np.float32)


def add_breath_noise(audio_data, sr, level=0.0006):
    """Add subtle breath noise."""
    from scipy.signal import butter, lfilter
    noise = np.random.randn(len(audio_data)).astype(np.float32) * level
    b, a = butter(4, 2000 / (sr / 2), btype='low')
    return audio_data + lfilter(b, a, noise).astype(np.float32)


# ============================================
# Step 1: Convert existing Marina v2 WAV → MP3
# ============================================
print("Step 1: Converting WAV -> MP3...\n")
wav_files = [
    "marina_v2_fast", "marina_v2_alive", "marina_v2_bright",
    "marina_v2_max", "alena_v2_alive"
]
for name in wav_files:
    wav = OUTPUT_DIR / f"{name}.wav"
    mp3 = OUTPUT_DIR / f"{name}.mp3"
    if wav.exists():
        print(f"  {name}.wav -> .mp3...", end=" ", flush=True)
        wav_to_mp3(wav, mp3)
        print(f"OK ({mp3.stat().st_size/1024:.0f} KB)")

# ============================================
# Step 2: Process Nova more aggressively
# ============================================
print("\nStep 2: Nova -- aggressive processing...\n")

nova_src = OUTPUT_DIR / "openai_nova.mp3"
if nova_src.exists():
    data, sr = sf.read(str(nova_src), dtype='float32')
    if data.ndim > 1:
        data = data[:, 0]

    # Nova v2a: pitch down (lower = less "English" brightness) + speed + jitter
    name = "nova_v2_deep"
    print(f"  {name}...", end=" ", flush=True)
    out = add_pitch_jitter(data, sr, jitter_cents=3.0, rate_hz=4.0)
    tmp = OUTPUT_DIR / f"{name}.wav"
    sf.write(str(tmp), out, sr)
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=70),
        PitchShift(semitones=-1.0),  # Pitch down 1 semitone — darker, less English
        Compressor(threshold_db=-20, ratio=2.0, attack_ms=5, release_ms=60),
        LowShelfFilter(cutoff_frequency_hz=300, gain_db=3.0),  # Strong warmth
        HighShelfFilter(cutoff_frequency_hz=7000, gain_db=-2.0),  # Cut brightness
        Gain(gain_db=2.0),
        Reverb(room_size=0.04, wet_level=0.05, dry_level=1.0),
    ])
    with AudioFile(str(tmp)) as f:
        with AudioFile(str(tmp) + ".tmp.wav", 'w', f.samplerate, f.num_channels) as o:
            while f.tell() < f.frames:
                chunk = f.read(int(f.samplerate))
                o.write(board(chunk, f.samplerate, reset=False))
    Path(str(tmp) + ".tmp.wav").replace(tmp)
    mp3 = OUTPUT_DIR / f"{name}.mp3"
    wav_to_mp3(tmp, mp3)
    print(f"OK ({mp3.stat().st_size/1024:.0f} KB)")

    # Nova v2b: pitch down less + warm + speed up slightly
    name = "nova_v2_warm"
    print(f"  {name}...", end=" ", flush=True)
    out = speed_up_audio(data, sr, factor=1.05)
    out = add_pitch_jitter(out, sr, jitter_cents=3.0, rate_hz=5.0)
    tmp = OUTPUT_DIR / f"{name}.wav"
    sf.write(str(tmp), out, sr)
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=75),
        PitchShift(semitones=-0.5),  # Slightly lower
        Compressor(threshold_db=-18, ratio=2.0, attack_ms=4, release_ms=50),
        LowShelfFilter(cutoff_frequency_hz=280, gain_db=2.5),
        HighShelfFilter(cutoff_frequency_hz=6500, gain_db=-1.5),  # Reduce brightness
        Gain(gain_db=1.5),
        Reverb(room_size=0.03, wet_level=0.04, dry_level=1.0),
    ])
    with AudioFile(str(tmp)) as f:
        with AudioFile(str(tmp) + ".tmp.wav", 'w', f.samplerate, f.num_channels) as o:
            while f.tell() < f.frames:
                chunk = f.read(int(f.samplerate))
                o.write(board(chunk, f.samplerate, reset=False))
    Path(str(tmp) + ".tmp.wav").replace(tmp)
    mp3 = OUTPUT_DIR / f"{name}.mp3"
    wav_to_mp3(tmp, mp3)
    print(f"OK ({mp3.stat().st_size/1024:.0f} KB)")

    # Nova v2c: max processing — deep pitch + breath + strong EQ
    name = "nova_v2_russian"
    print(f"  {name}...", end=" ", flush=True)
    out = speed_up_audio(data, sr, factor=1.03)
    out = add_pitch_jitter(out, sr, jitter_cents=4.0, rate_hz=4.5)
    out = add_breath_noise(out, sr, level=0.0005)
    tmp = OUTPUT_DIR / f"{name}.wav"
    sf.write(str(tmp), out, sr)
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=70),
        PitchShift(semitones=-1.5),  # Strong pitch down — very different character
        Compressor(threshold_db=-16, ratio=2.5, attack_ms=3, release_ms=45),
        LowShelfFilter(cutoff_frequency_hz=350, gain_db=4.0),  # Maximum warmth
        HighShelfFilter(cutoff_frequency_hz=5500, gain_db=-3.0),  # Strong high cut
        Gain(gain_db=3.0),
        Reverb(room_size=0.05, wet_level=0.06, dry_level=1.0, damping=0.6),
    ])
    with AudioFile(str(tmp)) as f:
        with AudioFile(str(tmp) + ".tmp.wav", 'w', f.samplerate, f.num_channels) as o:
            while f.tell() < f.frames:
                chunk = f.read(int(f.samplerate))
                o.write(board(chunk, f.samplerate, reset=False))
    Path(str(tmp) + ".tmp.wav").replace(tmp)
    mp3 = OUTPUT_DIR / f"{name}.mp3"
    wav_to_mp3(tmp, mp3)
    print(f"OK ({mp3.stat().st_size/1024:.0f} KB)")

print(f"\nDone! All files as MP3.")
