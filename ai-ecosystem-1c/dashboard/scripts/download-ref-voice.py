"""Download a Russian voice reference from Common Voice via HuggingFace API."""
import json
import sys
from pathlib import Path
from urllib.request import urlopen, Request

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "pitch" / "audio" / "test-voices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REF_PATH = OUTPUT_DIR / "ref_female_ru.wav"

API_URL = "https://datasets-server.huggingface.co/rows"
DATASET = "Sh1man/common_voice_21_ru"

print("Searching for suitable Russian voice sample (6-12s)...\n")

best_url = None
best_dur = 0
best_text = ""

# Scan rows in batches to find one with good duration
for offset in range(0, 200, 20):
    params = f"dataset={DATASET}&config=default&split=test&offset={offset}&length=20"
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
        mp3_list = row.get("mp3", [])

        if isinstance(mp3_list, list) and len(mp3_list) > 0:
            audio_url = mp3_list[0].get("src", "")
            if 6.0 <= duration <= 12.0 and audio_url:
                best_url = audio_url
                best_dur = duration
                best_text = text
                print(f"  Found! Duration: {duration:.1f}s")
                print(f"  Text: {text}")
                break
            elif duration > best_dur and duration >= 4.0 and duration <= 15.0 and audio_url:
                best_url = audio_url
                best_dur = duration
                best_text = text

    if best_dur >= 6.0:
        break

if not best_url:
    print("No suitable sample found.")
    sys.exit(1)

print(f"\n  Best sample: {best_dur:.1f}s")
print(f"  Text: {best_text}")
print(f"  Downloading...")

# Download MP3
req = Request(best_url, headers={"User-Agent": "Python/3.12"})
audio_data = urlopen(req, timeout=60).read()
temp_mp3 = OUTPUT_DIR / "temp_ref.mp3"
temp_mp3.write_bytes(audio_data)

# Convert to WAV 24kHz mono
from pydub import AudioSegment
audio_seg = AudioSegment.from_mp3(str(temp_mp3))
audio_seg = audio_seg.set_channels(1).set_frame_rate(24000)
audio_seg.export(str(REF_PATH), format="wav")
temp_mp3.unlink(missing_ok=True)

size_kb = REF_PATH.stat().st_size / 1024
real_dur = len(audio_seg) / 1000
print(f"\n  OK: {REF_PATH.name}")
print(f"  Duration: {real_dur:.1f}s | SR: 24000Hz | Size: {size_kb:.0f} KB")
