"""Process audio files through the full pipeline: Whisper → Ollama → BPMN → Docs."""
import json
import os
import sys
from pathlib import Path

# Ensure ffmpeg is in PATH
FFMPEG_DIR = r"C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin"
if os.path.isdir(FFMPEG_DIR) and FFMPEG_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import AppConfig, ProjectDir
from src.transcription.preprocessor import preprocess_audio
from src.transcription.transcriber import transcribe
from src.transcription.formatter import format_transcript
from src.analysis.process_extractor import extract_processes, generate_bpmn_json, check_ollama_available
from src.bpmn.json_to_bpmn import generate_bpmn_file
from src.bpmn.renderer import render_bpmn

CONFIG_PATH = PROJECT_ROOT / "config.yaml"
PROJECT_NAME = "ПВХ_Панели_audio"  # Separate project to not overwrite text results


def main():
    config = AppConfig.from_yaml(str(CONFIG_PATH))
    config_dict = config.to_dict()

    project = ProjectDir(PROJECT_NAME, config.project.data_dir)
    project.ensure_dirs()

    # Check ffmpeg
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ERROR: ffmpeg not found in PATH")
        sys.exit(1)
    print(f"FFmpeg: {ffmpeg}")

    # Check Ollama
    print("Checking Ollama...")
    check_ollama_available(config_dict)
    print("  OK\n")

    # Find audio files from the text project's audio dir
    audio_source = PROJECT_ROOT / "data" / "projects" / "ПВХ_Панели" / "audio"
    wav_files = sorted(audio_source.glob("*.wav"))

    if not wav_files:
        print(f"No .wav files found in {audio_source}")
        sys.exit(1)

    print(f"Found {len(wav_files)} audio files:")
    for f in wav_files:
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.0f} KB)")

    # Process only the first file to validate, then ask to continue
    files_to_process = wav_files
    if "--all" not in sys.argv:
        files_to_process = wav_files[:1]
        print(f"\nProcessing first file only. Use --all to process all {len(wav_files)} files.\n")

    for i, wav_path in enumerate(files_to_process, 1):
        stem = wav_path.stem
        print(f"\n{'='*60}")
        print(f"[{i}/{len(files_to_process)}] Processing: {wav_path.name}")
        print(f"{'='*60}")

        # Step 1: Preprocess audio
        print("  Step 1: Preprocessing audio...")
        try:
            processed = preprocess_audio(str(wav_path), str(project.audio), config_dict)
            print(f"    Preprocessed: {Path(processed).name}")
        except Exception as e:
            print(f"    ERROR: {e}")
            continue

        # Step 2: Transcribe with faster-whisper
        print("  Step 2: Transcribing with faster-whisper (this may take several minutes)...")
        try:
            raw_result = transcribe(processed, config_dict)
            transcript = format_transcript(raw_result)

            # Save transcript
            transcript_path = project.transcripts / f"{stem}.json"
            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)

            seg_count = len(transcript.get("segments", []))
            text_len = len(transcript.get("full_text", ""))
            print(f"    Segments: {seg_count}, Text length: {text_len} chars")
            print(f"    Saved: {transcript_path.name}")

            # Show first 200 chars of transcript
            preview = transcript.get("full_text", "")[:200]
            print(f"    Preview: {preview}...")
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback
            traceback.print_exc()
            continue

        # Step 3: Extract processes via Ollama
        print("  Step 3: Extracting processes via Ollama...")
        try:
            processes = extract_processes(transcript, config_dict)
            proc_count = len(processes.get("processes", []))
            print(f"    Extracted {proc_count} processes")

            processes_path = project.processes / f"{stem}_processes.json"
            with open(processes_path, "w", encoding="utf-8") as f:
                json.dump(processes, f, ensure_ascii=False, indent=2)
            print(f"    Saved: {processes_path.name}")
        except Exception as e:
            print(f"    ERROR: {e}")
            continue

        # Step 4: Generate BPMN
        print("  Step 4: Generating BPMN diagrams...")
        for proc in processes.get("processes", []):
            proc_id = proc.get("id", "process_1")
            proc_name = proc.get("name", proc_id)
            try:
                print(f"    BPMN for '{proc_name}'...")
                bpmn_json = generate_bpmn_json(proc, config_dict, detail_level="high_level")
                bpmn_file = generate_bpmn_file(bpmn_json, str(project.bpmn), proc_id, "high_level")
                print(f"      XML: {Path(bpmn_file).name}")
                rendered = render_bpmn(bpmn_file, str(project.bpmn), config_dict)
                if rendered:
                    print(f"      SVG: {Path(rendered).name}")
            except Exception as e:
                print(f"      ERROR: {e}")

        # Step 5: Generate docs
        print("  Step 5: Generating documents...")
        try:
            from src.docs.doc_generator import generate_documents
            doc_files = generate_documents(processes, str(project.root), config_dict)
            for df in doc_files:
                print(f"    Doc: {Path(df).name}")
        except Exception as e:
            print(f"    Doc ERROR: {e}")

        print(f"  Done with {wav_path.name}")

    print(f"\n{'='*60}")
    print("AUDIO PIPELINE DONE!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
