"""Analysis service — orchestrates process extraction, validation, and BPMN JSON generation."""
import json
import logging
from pathlib import Path

from src.analysis.process_extractor import extract_processes, generate_bpmn_json, generate_to_be
from src.analysis.validator import validate_bpmn_json, validate_processes
from src.config import ProjectDir

logger = logging.getLogger(__name__)


def run_extraction(transcript_path: Path, config_dict: dict, project: ProjectDir) -> dict:
    """Extract AS IS processes from a transcript file.

    Args:
        transcript_path: Path to transcript JSON file.
        config_dict: Application config as dict.
        project: ProjectDir for output paths.

    Returns:
        Dict with extracted processes and validation results.
    """
    with open(transcript_path, encoding="utf-8") as f:
        transcript = json.load(f)

    logger.info(f"Extracting processes from {transcript_path.name}...")
    processes = extract_processes(transcript, config_dict)

    validation = validate_processes(processes)

    # Save
    output_path = project.processes / f"{transcript_path.stem}_processes.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processes, f, ensure_ascii=False, indent=2)

    logger.info(f"Extracted {validation.get('process_count', 0)} processes → {output_path}")
    return {"processes": processes, "validation": validation, "path": output_path}


def run_to_be_generation(process_path: Path, config_dict: dict, project: ProjectDir) -> dict:
    """Generate TO BE processes from AS IS.

    Args:
        process_path: Path to AS IS processes JSON file.
        config_dict: Application config as dict.
        project: ProjectDir for output paths.

    Returns:
        Dict with TO BE processes.
    """
    with open(process_path, encoding="utf-8") as f:
        as_is = json.load(f)

    logger.info("Generating TO BE processes...")
    to_be = generate_to_be(as_is, config_dict)

    output_path = project.processes / f"{process_path.stem}_to_be.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(to_be, f, ensure_ascii=False, indent=2)

    logger.info(f"TO BE processes saved: {output_path}")
    return to_be


def run_bpmn_json_generation(process: dict, config_dict: dict, detail_level: str = "high_level") -> dict:
    """Generate and validate BPMN JSON for a single process.

    Args:
        process: Single process dict.
        config_dict: Application config as dict.
        detail_level: "high_level" or "detailed".

    Returns:
        Dict with bpmn_json and validation result.
    """
    bpmn_json = generate_bpmn_json(process, config_dict, detail_level=detail_level)
    validation = validate_bpmn_json(bpmn_json)
    return {"bpmn_json": bpmn_json, "validation": validation}
