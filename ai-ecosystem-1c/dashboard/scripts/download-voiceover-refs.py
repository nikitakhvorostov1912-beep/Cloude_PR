"""Download professional Russian female voice-over actress demo reels."""
from pathlib import Path
from urllib.request import urlopen, Request
from pydub import AudioSegment

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "pitch" / "audio" / "test-voices" / "references"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Clear old files
for f in OUTPUT_DIR.glob("ref_*.wav"):
    f.unlink()

# Professional voice actresses from voiceover-samples.com
BASE_URL = "http://russian.voiceoversamples.com"
ACTRESSES = [
    {"file": "RU_F_Alisa", "name": "Alisa", "desc": "Профессиональная актриса Алиса"},
    {"file": "RU_F_DashaCH", "name": "Dasha CH", "desc": "Актриса озвучки Даша"},
    {"file": "RU_F_MarinaN", "name": "Marina N", "desc": "Актриса озвучки Марина"},
    {"file": "RU_F_DianaB", "name": "Diana B", "desc": "Актриса озвучки Диана"},
    {"file": "RU_F_Katya", "name": "Katya", "desc": "Актриса озвучки Катя"},
    {"file": "RU_F_Kira", "name": "Kira", "desc": "Актриса озвучки Кира"},
    {"file": "RU_F_Victoria", "name": "Victoria", "desc": "Актриса озвучки Виктория"},
    {"file": "RU_F_OlgaT", "name": "Olga T", "desc": "Актриса озвучки Ольга"},
]

# Try both URL patterns
URL_PATTERNS = [
    "http://russian.voiceoversamples.com/{}.mp3",
    "http://russian.voiceover-samples.com/{}.mp3",
    "https://www.voiceover-samples.com/wp-content/uploads/{}.mp3",
]

print(f"Downloading {len(ACTRESSES)} voice actress demo reels...\n")

results = []
for i, actress in enumerate(ACTRESSES, 1):
    filename = f"ref_{i:02d}_{actress['name'].lower().replace(' ', '_')}.wav"
    filepath = OUTPUT_DIR / filename
    downloaded = False

    for pattern in URL_PATTERNS:
        url = pattern.format(actress["file"])
        try:
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.voiceover-samples.com/",
            })
            resp = urlopen(req, timeout=15)
            mp3_data = resp.read()

            if len(mp3_data) < 5000:  # Too small = error page
                continue

            temp = OUTPUT_DIR / f"temp_{i}.mp3"
            temp.write_bytes(mp3_data)

            audio = AudioSegment.from_mp3(str(temp))
            # Take 10s clip from middle of demo reel (skip intro music)
            total_ms = len(audio)
            start = min(15000, total_ms // 3)
            end = min(start + 10000, total_ms)
            clip = audio[start:end]
            clip = clip.set_channels(1).set_frame_rate(24000)
            clip.export(str(filepath), format="wav")
            temp.unlink(missing_ok=True)

            duration = len(clip) / 1000
            size_kb = filepath.stat().st_size / 1024
            print(f"  {i}. {actress['name']:15s} OK ({duration:.1f}s, {size_kb:.0f} KB)")
            results.append({"file": filename, "duration": duration, "name": actress["name"], "desc": actress["desc"]})
            downloaded = True
            break
        except Exception:
            continue

    if not downloaded:
        print(f"  {i}. {actress['name']:15s} FAIL (all URLs)")

# Generate HTML
html_path = OUTPUT_DIR / "index.html"
parts = ["""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Выбор голоса — актрисы озвучки</title>
<style>
  body { background: #0a0a1a; color: #e0e0e0; font-family: system-ui; padding: 40px; max-width: 700px; margin: 0 auto; }
  h1 { color: #a78bfa; }
  .info { color: #888; margin-bottom: 30px; line-height: 1.6; }
  .voice { background: #1a1a2e; border: 2px solid #ec4899; border-radius: 12px; padding: 20px; margin: 12px 0; }
  .voice h3 { margin: 0 0 6px; color: #c4b5fd; }
  .voice p { margin: 0 0 10px; color: #888; font-size: 14px; }
  audio { width: 100%; }
  .num { color: #ec4899; font-weight: bold; font-size: 1.2em; }
</style>
</head>
<body>
<h1>Выбери голос для Авроры</h1>
<p class="info">Профессиональные актрисы озвучки (игры, фильмы, реклама).<br>
F5-TTS скопирует тембр. Назови номер самого приятного голоса.</p>
"""]

for j, r in enumerate(results, 1):
    parts.append(f"""
<div class="voice">
  <h3><span class="num">{j}.</span> {r['name']} ({r['duration']:.1f}s)</h3>
  <p>{r['desc']}</p>
  <audio controls src="{r['file']}"></audio>
</div>
""")

parts.append("</body></html>")
html_path.write_text("".join(parts), encoding="utf-8")

print(f"\nSaved {len(results)} samples: {OUTPUT_DIR}")
print(f"Open: http://localhost:8899/references/")
