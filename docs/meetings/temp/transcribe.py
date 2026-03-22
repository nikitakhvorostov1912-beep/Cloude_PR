"""Transcribe audio chunks via Groq Whisper API"""
import os
import sys
import json
from pathlib import Path

GROQ_API_KEY = "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"
TEMP_DIR = Path(__file__).parent

def transcribe_chunks(prefix: str, output_file: str):
    """Transcribe all chunks with given prefix and save combined result"""
    import httpx

    chunks = sorted(TEMP_DIR.glob(f"{prefix}_chunk_*.mp3"))
    print(f"Found {len(chunks)} chunks for {prefix}")

    all_segments = []
    time_offset = 0.0
    full_text = []

    for i, chunk_path in enumerate(chunks):
        size_mb = chunk_path.stat().st_size / (1024 * 1024)
        print(f"  Transcribing {chunk_path.name} ({size_mb:.1f}MB)...")

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

        if resp.status_code != 200:
            print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
            continue

        result = resp.json()
        text = result.get("text", "")
        segments = result.get("segments", [])

        # Adjust timestamps with offset
        for seg in segments:
            seg["start"] = seg.get("start", 0) + time_offset
            seg["end"] = seg.get("end", 0) + time_offset
            all_segments.append(seg)

        full_text.append(text)

        # Calculate offset for next chunk
        if segments:
            time_offset = segments[-1]["end"]
        else:
            # Estimate from file duration (21 min chunks)
            time_offset += 1260

        print(f"  OK: {len(text)} chars, {len(segments)} segments")

    # Save combined result
    output_path = TEMP_DIR / output_file
    combined = {
        "text": "\n".join(full_text),
        "segments": all_segments,
        "chunk_count": len(chunks),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_path} ({len(combined['text'])} chars, {len(all_segments)} segments)")
    return combined

if __name__ == "__main__":
    prefix = sys.argv[1] if len(sys.argv) > 1 else "m1"
    output = sys.argv[2] if len(sys.argv) > 2 else "transcript_m1.json"
    transcribe_chunks(prefix, output)
