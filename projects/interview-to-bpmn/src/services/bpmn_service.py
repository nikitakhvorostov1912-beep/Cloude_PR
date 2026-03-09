"""BPMN service — orchestrates BPMN XML generation and rendering."""
import logging

from src.bpmn.json_to_bpmn import bpmn_json_to_xml, generate_bpmn_file
from src.bpmn.renderer import render_bpmn
from src.config import ProjectDir

logger = logging.getLogger(__name__)


def run_bpmn_generation(
    bpmn_json: dict,
    proc_id: str,
    level: str,
    project: ProjectDir,
    config_dict: dict,
) -> dict:
    """Generate BPMN XML file and render to image.

    Args:
        bpmn_json: BPMN JSON structure (from analysis_service).
        proc_id: Process identifier for filename.
        level: Detail level ("high_level" or "detailed").
        project: ProjectDir for output paths.
        config_dict: Application config as dict (for renderer).

    Returns:
        Dict with bpmn_path and rendered image path.
    """
    # Generate XML file
    bpmn_path = generate_bpmn_file(bpmn_json, str(project.bpmn), proc_id, level)
    logger.info(f"BPMN file generated: {bpmn_path}")

    # Render to image
    rendered = render_bpmn(bpmn_path, str(project.output), config_dict)
    logger.info(f"BPMN rendered: {rendered}")

    return {"bpmn_path": bpmn_path, "rendered_path": rendered}


def convert_json_to_xml(bpmn_json: dict) -> str:
    """Convert BPMN JSON to XML string without saving to file.

    Args:
        bpmn_json: BPMN JSON structure.

    Returns:
        BPMN 2.0 XML string.
    """
    return bpmn_json_to_xml(bpmn_json)
