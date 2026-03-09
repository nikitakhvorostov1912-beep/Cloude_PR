"""Download multiple Russian voice references for user to choose from."""
import json
import sys
from pathlib import Path
from urllib.request import urlopen, Request

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "pitch" / "audio" / "test-voices" / "references"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

API_URL = "https://datasets-server.huggingface.co/rows"
DATASET = "Sh1man/common_voice_21_ru"

print("Downloading Russian voice samples for selection...\n")

samples = []
seen_durations = set()

# Scan rows to find diverse samples with good duration (5-15s)
for offset in range(0, 500, 10):
    params = f"dataset={DATASET}&config=default&split=test&offset={offset}&length=10"
    url = f"{API_URL}?{params}"
    req = Request(url, headers={"User-Agent": "Python/3.12"})
    try:
        resp = urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  API error at offset {offset}: {e}")
        continue

    rows = data.get("rows", [])
    for row_data in rows:
        row = row_data.get("row", {})
        info = row.get("json", {})
        duration = info.get("duration", 0)
        text = info.get("text", "")
        sample_id = info.get("id", "")
        mp3_list = row.get("mp3", [])

        if isinstance(mp3_list, list) and len(mp3_list) > 0:
            audio_url = mp3_list[0].get("src", "")
            # Filter: 5-15 seconds, avoid near-duplicates
            dur_key = round(duration, 0)
            if 5.0 <= duration <= 15.0 and audio_url and dur_key not in seen_durations:
                seen_durations.add(dur_key)
                samples.append({
                    "url": audio_url,
                    "duration": duration,
                    "text": text,
                    "id": sample_id,
                })

    if len(samples) >= 10:
        break

print(f"Found {len(samples)} suitable samples. Downloading...\n")

# Download each sample
from pydub import AudioSegment

metadata = []
for i, s in enumerate(samples):
    idx = i + 1
    filename = f"ref_{idx:02d}.wav"
    filepath = OUTPUT_DIR / filename
    try:
        req = Request(s["url"], headers={"User-Agent": "Python/3.12"})
        audio_data = urlopen(req, timeout=60).read()
        temp = OUTPUT_DIR / f"temp_{idx}.mp3"
        temp.write_bytes(audio_data)

        audio_seg = AudioSegment.from_mp3(str(temp))
        audio_seg = audio_seg.set_channels(1).set_frame_rate(24000)
        audio_seg.export(str(filepath), format="wav")
        temp.unlink(missing_ok=True)

        size_kb = filepath.stat().st_size / 1024
        real_dur = len(audio_seg) / 1000
        print(f"  {idx:2d}. ref_{idx:02d}.wav  ({real_dur:.1f}s, {size_kb:.0f} KB)")

        metadata.append({
            "file": filename,
            "duration": real_dur,
            "text": s["text"],
            "id": s["id"],
        })
    except Exception as e:
        print(f"  {idx:2d}. FAIL: {e}")

# Save metadata
meta_path = OUTPUT_DIR / "metadata.json"
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

# Generate HTML player
html_path = OUTPUT_DIR / "index.html"
html_parts = ["""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Выбор референсного голоса для Авроры</title>
<style>
  body { background: #0a0a1a; color: #e0e0e0; font-family: system-ui; padding: 40px; max-width: 700px; margin: 0 auto; }
  h1 { color: #a78bfa; }
  p.desc { color: #888; margin-bottom: 30px; }
  .voice { background: #1a1a2e; border: 2px solid #f59e0b; border-radius: 12px; padding: 20px; margin: 12px 0; }
  .voice h3 { margin: 0 0 6px; color: #c4b5fd; }
  .voice p { margin: 0 0 10px; color: #888; font-size: 14px; }
  audio { width: 100%; }
  .num { color: #f59e0b; font-weight: bold; font-size: 1.2em; }
</style>
</head>
<body>
<h1>Выбери голос для клонирования</h1>
<p class="desc">Это реальные люди из Common Voice. F5-TTS скопирует тембр выбранного голоса.<br>
Послушай и назови номер лучшего.</p>
"""]

for m in metadata:
    idx = metadata.index(m) + 1
    html_parts.append(f"""
<div class="voice">
  <h3><span class="num">{idx}.</span> {m['file']} ({m['duration']:.1f}s)</h3>
  <audio controls src="{m['file']}"></audio>
</div>
""")

html_parts.append("</body></html>")
html_path.write_text("".join(html_parts), encoding="utf-8")

print(f"\nSaved {len(metadata)} samples to: {OUTPUT_DIR}")
print(f"HTML player: {html_path}")
