"""Download professional Russian voice clips from LibriVox audiobooks."""
from pathlib import Path
from urllib.request import urlopen, Request
from pydub import AudioSegment
import sys

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "pitch" / "audio" / "test-voices" / "references"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Clear old files
for f in OUTPUT_DIR.glob("ref_*.wav"):
    f.unlink()

# LibriVox Russian audiobooks - clips from different narrators
SOURCES = [
    {
        "url": "https://archive.org/download/childhood_russian_librivox/Leo-Tolstoy-Detstvo-RUSSIAN-02-Maman.mp3",
        "name": "ref_01_tolstoy_maman",
        "desc": "Толстой — Детство, глава Maman",
        "start_ms": 15000,
        "end_ms": 25000,
    },
    {
        "url": "https://archive.org/download/childhood_russian_librivox/Leo-Tolstoy-Detstvo-RUSSIAN-09-Chtoto-vrode-pervoi-liubvi.mp3",
        "name": "ref_02_tolstoy_love",
        "desc": "Толстой — Детство, глава 9",
        "start_ms": 10000,
        "end_ms": 20000,
    },
    {
        "url": "https://archive.org/download/childhood_russian_librivox/Leo-Tolstoy-Detstvo-RUSSIAN-15-Detstvo.mp3",
        "name": "ref_03_tolstoy_ch15",
        "desc": "Толстой — Детство, глава 15",
        "start_ms": 15000,
        "end_ms": 25000,
    },
    {
        "url": "https://archive.org/download/white_nights_librivox/1-fm-dostoevsky-belye-nochi-night1.mp3",
        "name": "ref_04_dostoevsky_wn1",
        "desc": "Достоевский — Белые Ночи, ч.1",
        "start_ms": 20000,
        "end_ms": 30000,
    },
    {
        "url": "https://archive.org/download/white_nights_librivox/4-fm-dostoevsky-belye-nochi-history_of_nastenka.mp3",
        "name": "ref_05_dostoevsky_nastenka",
        "desc": "Достоевский — История Настеньки",
        "start_ms": 15000,
        "end_ms": 25000,
    },
    {
        "url": "https://archive.org/download/white_nights_librivox/7-fm-dostoevsky-belye-nochi-morning.mp3",
        "name": "ref_06_dostoevsky_morning",
        "desc": "Достоевский — Утро",
        "start_ms": 10000,
        "end_ms": 20000,
    },
    {
        "url": "https://archive.org/download/05-fix-vs-crb/01_fix-vs-crb-.mp3",
        "name": "ref_07_fixiki",
        "desc": "Фиксики — аудиокнига",
        "start_ms": 10000,
        "end_ms": 20000,
    },
    {
        "url": "https://archive.org/download/Poezdka_Polesye_librivox/turgenev_poezdka_polesye_01_novikova_128kb.mp3",
        "name": "ref_08_turgenev",
        "desc": "Тургенев — Поездка в Полесье (Новикова)",
        "start_ms": 15000,
        "end_ms": 25000,
    },
]

print(f"Downloading {len(SOURCES)} clips from Russian audiobooks...\n")

results = []
for i, src in enumerate(SOURCES, 1):
    filename = f"{src['name']}.wav"
    filepath = OUTPUT_DIR / filename
    try:
        print(f"  {i}. {src['desc']}...", end=" ", flush=True)
        req = Request(src["url"], headers={"User-Agent": "Mozilla/5.0"})
        # Download only first 200KB (enough for 10s clip at 128kbps)
        resp = urlopen(req, timeout=30)
        # Read enough data for the clip
        chunk_size = 1024 * 1024  # 1MB should be plenty for 30s
        mp3_data = resp.read(chunk_size)

        temp = OUTPUT_DIR / f"temp_{i}.mp3"
        temp.write_bytes(mp3_data)

        audio = AudioSegment.from_mp3(str(temp))
        total_ms = len(audio)

        # Adjust if clip is beyond audio length
        start = min(src["start_ms"], total_ms - 10000) if total_ms > 10000 else 0
        end = min(src["end_ms"], total_ms)

        clip = audio[start:end]
        clip = clip.set_channels(1).set_frame_rate(24000)
        clip.export(str(filepath), format="wav")
        temp.unlink(missing_ok=True)

        duration = len(clip) / 1000
        size_kb = filepath.stat().st_size / 1024
        print(f"OK ({duration:.1f}s, {size_kb:.0f} KB)")
        results.append({"file": filename, "duration": duration, "desc": src["desc"]})
    except Exception as e:
        print(f"FAIL ({e})")

# Generate HTML
html_path = OUTPUT_DIR / "index.html"
parts = ["""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Выбор голоса — профессиональные дикторы</title>
<style>
  body { background: #0a0a1a; color: #e0e0e0; font-family: system-ui; padding: 40px; max-width: 700px; margin: 0 auto; }
  h1 { color: #a78bfa; }
  .info { color: #888; margin-bottom: 30px; line-height: 1.6; }
  .voice { background: #1a1a2e; border: 2px solid #f59e0b; border-radius: 12px; padding: 20px; margin: 12px 0; }
  .voice h3 { margin: 0 0 6px; color: #c4b5fd; }
  .voice p { margin: 0 0 10px; color: #888; font-size: 14px; }
  audio { width: 100%; }
  .num { color: #f59e0b; font-weight: bold; font-size: 1.2em; }
</style>
</head>
<body>
<h1>Выбери голос для клонирования</h1>
<p class="info">Это голоса из русских аудиокниг (LibriVox). F5-TTS скопирует тембр выбранного голоса.<br>
Мне нужен приятный женский голос — послушай и назови номер лучшего.</p>
"""]

for j, r in enumerate(results, 1):
    parts.append(f"""
<div class="voice">
  <h3><span class="num">{j}.</span> {r['desc']} ({r['duration']:.1f}s)</h3>
  <audio controls src="{r['file']}"></audio>
</div>
""")

parts.append("</body></html>")
html_path.write_text("".join(parts), encoding="utf-8")

print(f"\nSaved {len(results)} clips to: {OUTPUT_DIR}")
print(f"Open: http://localhost:8899/references/")
