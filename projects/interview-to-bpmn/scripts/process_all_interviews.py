"""Process all text interviews through the full pipeline."""
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import AppConfig, ProjectDir
from src.analysis.process_extractor import extract_processes, generate_bpmn_json, check_ollama_available
from src.bpmn.json_to_bpmn import generate_bpmn_file
from src.bpmn.renderer import render_bpmn

CONFIG_PATH = PROJECT_ROOT / "config.yaml"
PROJECT_NAME = "ПВХ_Панели"


def txt_to_transcript(txt_path: Path) -> dict:
    """Convert a .txt file to transcript JSON format."""
    content = txt_path.read_text(encoding="utf-8")
    return {
        "text": content,
        "full_text": content,
        "segments": [{"text": content, "start": 0, "end": 0, "speaker": "Спикер_1"}],
        "dialogue": [{"speaker": "Спикер_1", "text": content, "start": "00:00:00", "end": "00:00:00"}],
        "metadata": {
            "source": txt_path.name,
            "type": "text_import",
            "duration_seconds": 0,
            "language": "ru",
        },
    }


def main():
    # Load config
    config = AppConfig.from_yaml(str(CONFIG_PATH))
    config_dict = config.to_dict()

    # Setup project directory
    project = ProjectDir(PROJECT_NAME, config.project.data_dir)
    project.ensure_dirs()

    # Check Ollama
    print("Checking Ollama availability...")
    try:
        check_ollama_available(config_dict)
        print(f"  OK: Ollama is running, model: {config_dict['analysis']['ollama']['model']}")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    # Find all .txt files
    txt_dir = project.transcripts
    txt_files = sorted(txt_dir.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in {txt_dir}")
        sys.exit(1)

    print(f"\nFound {len(txt_files)} interview files:")
    for f in txt_files:
        print(f"  - {f.name}")

    # Process each interview
    for i, txt_path in enumerate(txt_files, 1):
        stem = txt_path.stem
        print(f"\n{'='*60}")
        print(f"[{i}/{len(txt_files)}] Processing: {txt_path.name}")
        print(f"{'='*60}")

        # Step 1: Convert txt to transcript JSON
        print("  Step 1: Converting text to transcript JSON...")
        transcript = txt_to_transcript(txt_path)
        transcript_path = project.transcripts / f"{stem}.json"
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
        print(f"    Saved: {transcript_path.name}")

        # Step 2: Extract processes via Ollama
        print("  Step 2: Extracting processes via Ollama (this may take a few minutes)...")
        try:
            processes = extract_processes(transcript, config_dict)
            proc_count = len(processes.get("processes", []))
            print(f"    Extracted {proc_count} processes")

            processes_path = project.processes / f"{stem}_processes.json"
            with open(processes_path, "w", encoding="utf-8") as f:
                json.dump(processes, f, ensure_ascii=False, indent=2)
            print(f"    Saved: {processes_path.name}")
        except Exception as e:
            print(f"    ERROR extracting processes: {e}")
            continue

        # Step 3: Generate BPMN for each process
        print("  Step 3: Generating BPMN diagrams...")
        for proc in processes.get("processes", []):
            proc_id = proc.get("id", "process_1")
            proc_name = proc.get("name", proc_id)

            for level in ["high_level"]:
                try:
                    print(f"    Generating BPMN for '{proc_name}' ({level})...")
                    bpmn_json = generate_bpmn_json(proc, config_dict, detail_level=level)
                    bpmn_file = generate_bpmn_file(bpmn_json, str(project.bpmn), proc_id, level)
                    print(f"      BPMN XML: {Path(bpmn_file).name}")

                    rendered = render_bpmn(bpmn_file, str(project.bpmn), config_dict)
                    if rendered:
                        print(f"      Rendered: {Path(rendered).name}")
                except Exception as e:
                    print(f"      ERROR: {e}")

        print(f"  Done with {txt_path.name}")

    # Step 4: Generate documents
    print(f"\n{'='*60}")
    print("Generating Word documents...")
    print(f"{'='*60}")
    try:
        from src.docs.doc_generator import generate_documents
        proc_files = sorted(project.processes.glob("*_processes.json"))
        for pf in proc_files:
            with open(pf, encoding="utf-8") as f:
                data = json.load(f)
            doc_files = generate_documents(data, str(project.root), config_dict)
            for df in doc_files:
                print(f"  Document: {Path(df).name}")
    except Exception as e:
        print(f"  ERROR generating documents: {e}")

    print(f"\n{'='*60}")
    print("ALL DONE!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
