"""Retry failed interview processing: proizvodstvo (full) + prodazhi (BPMN only)."""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import AppConfig, ProjectDir
from src.analysis.process_extractor import extract_processes, generate_bpmn_json, check_ollama_available
from src.bpmn.json_to_bpmn import generate_bpmn_file
from src.bpmn.renderer import render_bpmn

CONFIG_PATH = PROJECT_ROOT / "config.yaml"
PROJECT_NAME = "ПВХ_Панели"


def txt_to_transcript(txt_path: Path) -> dict:
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
    config = AppConfig.from_yaml(str(CONFIG_PATH))
    config_dict = config.to_dict()
    project = ProjectDir(PROJECT_NAME, config.project.data_dir)

    print("Checking Ollama...")
    check_ollama_available(config_dict)
    print("  OK\n")

    # 1. Re-process interview_proizvodstvo.txt (full pipeline)
    print("=" * 60)
    print("RETRY 1: interview_proizvodstvo.txt (full)")
    print("=" * 60)
    txt_path = project.transcripts / "interview_proizvodstvo.txt"
    if txt_path.exists():
        transcript = txt_to_transcript(txt_path)
        transcript_path = project.transcripts / "interview_proizvodstvo.json"
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)

        try:
            processes = extract_processes(transcript, config_dict)
            proc_count = len(processes.get("processes", []))
            print(f"  Extracted {proc_count} processes")

            processes_path = project.processes / "interview_proizvodstvo_processes.json"
            with open(processes_path, "w", encoding="utf-8") as f:
                json.dump(processes, f, ensure_ascii=False, indent=2)

            for proc in processes.get("processes", []):
                proc_id = proc.get("id", "process_1")
                proc_name = proc.get("name", proc_id)
                try:
                    print(f"  BPMN for '{proc_name}'...")
                    bpmn_json = generate_bpmn_json(proc, config_dict, detail_level="high_level")
                    bpmn_file = generate_bpmn_file(bpmn_json, str(project.bpmn), proc_id, "high_level")
                    print(f"    XML: {Path(bpmn_file).name}")
                    rendered = render_bpmn(bpmn_file, str(project.bpmn), config_dict)
                    if rendered:
                        print(f"    SVG: {Path(rendered).name}")
                except Exception as e:
                    print(f"    ERROR: {e}")

            # Generate docs for proizvodstvo
            try:
                from src.docs.doc_generator import generate_documents
                doc_files = generate_documents(processes, str(project.root), config_dict)
                for df in doc_files:
                    print(f"  Doc: {Path(df).name}")
            except Exception as e:
                print(f"  Doc ERROR: {e}")

        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print(f"  File not found: {txt_path}")

    # 2. Re-generate BPMN for prodazhi proc_1 and proc_4
    print(f"\n{'=' * 60}")
    print("RETRY 2: prodazhi BPMN proc_1 + proc_4")
    print("=" * 60)
    prodazhi_path = project.processes / "interview_prodazhi_processes.json"
    if prodazhi_path.exists():
        with open(prodazhi_path, encoding="utf-8") as f:
            prodazhi_data = json.load(f)

        for proc in prodazhi_data.get("processes", []):
            proc_id = proc.get("id", "")
            if proc_id not in ("proc_1", "proc_4"):
                continue
            proc_name = proc.get("name", proc_id)
            try:
                print(f"  BPMN for '{proc_name}' ({proc_id})...")
                bpmn_json = generate_bpmn_json(proc, config_dict, detail_level="high_level")
                bpmn_file = generate_bpmn_file(bpmn_json, str(project.bpmn), proc_id, "high_level")
                print(f"    XML: {Path(bpmn_file).name}")
                rendered = render_bpmn(bpmn_file, str(project.bpmn), config_dict)
                if rendered:
                    print(f"    SVG: {Path(rendered).name}")
            except Exception as e:
                print(f"    ERROR: {e}")
    else:
        print(f"  File not found: {prodazhi_path}")

    print(f"\n{'=' * 60}")
    print("RETRY DONE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
