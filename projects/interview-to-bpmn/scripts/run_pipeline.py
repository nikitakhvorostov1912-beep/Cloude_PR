"""Run the full processing pipeline programmatically (without Streamlit UI)."""
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import AppConfig, ProjectDir

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def import_txt_files(project: ProjectDir):
    """Import .txt files from transcripts/ directory as transcript JSONs."""
    txt_files = sorted(project.transcripts.glob("*.txt"))
    if not txt_files:
        logger.warning("Нет .txt файлов в %s", project.transcripts)
        return

    for txt_file in txt_files:
        stem = txt_file.stem
        json_file = project.transcripts / f"{stem}.json"
        if json_file.exists():
            logger.info("Транскрипт %s.json уже существует, пропуск", stem)
            continue

        logger.info("Импорт текстового файла: %s", txt_file.name)
        content = txt_file.read_text(encoding="utf-8")

        transcript = {
            "text": content,
            "full_text": content,
            "segments": [{"text": content, "start": 0, "end": 0, "speaker": "Спикер_1"}],
            "dialogue": [
                {"speaker": "Спикер_1", "text": content, "start": "00:00:00", "end": "00:00:00"}
            ],
            "metadata": {
                "source": txt_file.name,
                "type": "text_import",
                "duration_seconds": 0,
                "language": "ru",
            },
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
        logger.info("  -> %s", json_file.name)


def run_extraction(project: ProjectDir, config_dict: dict):
    """Stage 3: Extract processes from transcripts via LLM."""
    from src.analysis.process_extractor import check_ollama_available, extract_processes

    check_ollama_available(config_dict)

    transcript_files = sorted(project.transcripts.glob("*.json"))
    existing_procs = {f.stem.replace("_processes", "") for f in project.processes.glob("*_processes.json")}

    to_analyze = [f for f in transcript_files if f.stem not in existing_procs]
    if not to_analyze:
        logger.info("Все транскрипты уже обработаны")
        return

    for idx, tf in enumerate(to_analyze, 1):
        logger.info("Извлечение процессов [%d/%d]: %s", idx, len(to_analyze), tf.name)
        t0 = time.time()

        with open(tf, encoding="utf-8") as f:
            transcript = json.load(f)

        try:
            result = extract_processes(transcript, config_dict)
        except Exception as e:
            logger.error("  ОШИБКА извлечения для %s: %s", tf.name, e)
            continue

        # Add source reference
        result["source"] = tf.name
        from datetime import datetime
        result["extracted_at"] = datetime.now().isoformat()

        out_file = project.processes / f"{tf.stem}_processes.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        elapsed = time.time() - t0
        n_procs = len(result.get("processes", []))
        logger.info("  -> %s (%d процессов, %.0f сек)", out_file.name, n_procs, elapsed)


def run_bpmn_generation(project: ProjectDir, config_dict: dict, detail: str = "high_level"):
    """Stage 4: Generate BPMN XML and render SVG."""
    from src.analysis.process_extractor import generate_bpmn_json
    from src.bpmn.json_to_bpmn import generate_bpmn_file
    from src.bpmn.renderer import render_bpmn

    proc_files = sorted(project.processes.glob("*_processes.json"))
    if not proc_files:
        logger.warning("Нет файлов процессов для генерации BPMN")
        return

    levels = ["high_level", "detailed"] if detail == "both" else [detail]
    total = 0
    errors = 0

    for pf in proc_files:
        with open(pf, encoding="utf-8") as f:
            data = json.load(f)

        processes = data.get("processes", [])
        logger.info("BPMN для %s (%d процессов)", pf.name, len(processes))

        for proc in processes:
            proc_id = proc.get("id", f"process_{total + 1}")
            for lvl in levels:
                total += 1
                logger.info("  [%d] %s (%s)", total, proc.get("name", proc_id), lvl)
                t0 = time.time()
                try:
                    bj = generate_bpmn_json(proc, config_dict, detail_level=lvl)
                    bf = generate_bpmn_file(bj, str(project.bpmn), proc_id, lvl)
                    render_bpmn(bf, str(project.output), config_dict)
                    logger.info("    OK (%.0f сек)", time.time() - t0)
                except Exception as e:
                    errors += 1
                    logger.error("    ОШИБКА: %s", e)

    logger.info("BPMN итого: %d создано, %d ошибок", total - errors, errors)


def run_document_generation(project: ProjectDir, config_dict: dict):
    """Stage 5: Generate Word documents."""
    from src.docs.doc_generator import generate_documents

    proc_files = sorted(project.processes.glob("*_processes.json"))
    if not proc_files:
        logger.warning("Нет файлов процессов для генерации документов")
        return

    for pf in proc_files:
        logger.info("Документы для %s", pf.name)
        t0 = time.time()
        with open(pf, encoding="utf-8") as f:
            data = json.load(f)
        try:
            result = generate_documents(data, str(project.root), config_dict)
            logger.info("  -> %d документов (%.0f сек)", len(result) if result else 0, time.time() - t0)
        except Exception as e:
            logger.error("  ОШИБКА: %s", e)


def print_summary(project: ProjectDir):
    """Print summary of all generated files."""
    print("\n" + "=" * 60)
    print(f"ПРОЕКТ: {project.root.name}")
    print("=" * 60)

    for name, path in [
        ("Транскрипты (.json)", project.transcripts),
        ("Процессы (.json)", project.processes),
        ("BPMN (.bpmn)", project.bpmn),
        ("Визуализация (.svg)", project.output),
    ]:
        files = sorted(path.glob("*")) if path.exists() else []
        files = [f for f in files if f.is_file()]
        print(f"\n{name}: {len(files)} файлов")
        for f in files:
            size = f.stat().st_size
            print(f"  {f.name} ({size:,} bytes)")

    # Word documents
    docx_files = sorted(project.root.glob("*.docx"))
    print(f"\nДокументы (.docx): {len(docx_files)} файлов")
    for f in docx_files:
        size = f.stat().st_size
        print(f"  {f.name} ({size:,} bytes)")

    print("\n" + "=" * 60)


def main():
    config = AppConfig.from_yaml(str(PROJECT_ROOT / "config.yaml"))
    project = ProjectDir("ПВХ_Панели")
    project.ensure_dirs()
    config_dict = config.to_dict()

    print(f"\nПроект: {project.root}")
    print(f"Ollama: {config_dict['analysis']['ollama']['url']}")
    print(f"Модель: {config_dict['analysis']['ollama']['model']}")

    # Step 1: Import .txt files
    logger.info("=" * 40)
    logger.info("ШАГ 1: Импорт текстовых файлов")
    import_txt_files(project)

    # Step 2: Extract processes via LLM
    logger.info("=" * 40)
    logger.info("ШАГ 2: Извлечение процессов (Ollama)")
    run_extraction(project, config_dict)

    # Step 3: Generate BPMN
    logger.info("=" * 40)
    logger.info("ШАГ 3: Генерация BPMN")
    run_bpmn_generation(project, config_dict, detail="high_level")

    # Step 4: Generate documents
    logger.info("=" * 40)
    logger.info("ШАГ 4: Генерация документов")
    run_document_generation(project, config_dict)

    # Summary
    print_summary(project)


if __name__ == "__main__":
    main()
