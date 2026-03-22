"""Retry failed chunks for meeting 2 with backoff"""
import time
import json
import httpx
from pathlib import Path

GROQ_API_KEY = "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"
TEMP_DIR = Path(__file__).parent

# Load existing transcript
with open(TEMP_DIR / "transcript_m2.json", "r", encoding="utf-8") as f:
    existing = json.load(f)

# Need to transcribe chunks 02 and 03
chunks_to_do = [
    TEMP_DIR / "m2_chunk_02.mp3",
    TEMP_DIR / "m2_chunk_03.mp3",
]

# Time offset from existing segments
if existing["segments"]:
    time_offset = existing["segments"][-1]["end"]
else:
    time_offset = 2520.0  # 42 min

all_segments = existing["segments"]
full_text = [existing["text"]]

for chunk_path in chunks_to_do:
    if not chunk_path.exists():
        print(f"Skip {chunk_path.name} - not found")
        continue

    size_mb = chunk_path.stat().st_size / (1024 * 1024)

    for attempt in range(5):
        print(f"Transcribing {chunk_path.name} ({size_mb:.1f}MB), attempt {attempt+1}...")

        with open(chunk_path, "rb") as f:
            files = {"file": (chunk_path.name, f, "audio/mpeg")}
            data = {
                "model": "whisper-large-v3",
                "language": "ru",
                "response_format": "verbose_json",
                "temperature": "0.0",
            }
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

            resp = httpx.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
                timeout=120.0,
            )

        if resp.status_code == 200:
            result = resp.json()
            text = result.get("text", "")
            segments = result.get("segments", [])

            for seg in segments:
                seg["start"] = seg.get("start", 0) + time_offset
                seg["end"] = seg.get("end", 0) + time_offset
                all_segments.append(seg)

            full_text.append(text)
            if segments:
                time_offset = segments[-1]["end"]
            else:
                time_offset += 1260

            print(f"  OK: {len(text)} chars, {len(segments)} segments")
            break
        elif resp.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"  Rate limited. Waiting {wait}s...")
            time.sleep(wait)
        else:
            print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
            break

# Save updated transcript
combined = {
    "text": "\n".join(full_text),
    "segments": all_segments,
    "chunk_count": existing["chunk_count"],
}

with open(TEMP_DIR / "transcript_m2.json", "w", encoding="utf-8") as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)

print(f"\nFinal: {len(combined['text'])} chars, {len(all_segments)} segments")
