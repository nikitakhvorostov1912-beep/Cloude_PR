"""Convert BPMN JSON to standard BPMN 2.0 XML."""
import json
from pathlib import Path

from lxml import etree

from src.bpmn.layout import auto_layout


def _ensure_str(value, default="") -> str:
    """Ensure a value is a string — LLM sometimes returns dicts or lists instead."""
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("name", value.get("text", json.dumps(value, ensure_ascii=False)))
    if isinstance(value, (list, tuple)):
        return ", ".join(_ensure_str(v) for v in value)
    return str(value)

# BPMN 2.0 namespaces
BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"

XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

NSMAP = {
    "bpmn": BPMN_NS,
    "bpmndi": BPMNDI_NS,
    "dc": DC_NS,
    "di": DI_NS,
    "xsi": XSI_NS,
}

# BPMN element type to XML tag mapping
ELEMENT_TAG_MAP = {
    "startEvent": "startEvent",
    "endEvent": "endEvent",
    "userTask": "userTask",
    "serviceTask": "serviceTask",
    "scriptTask": "scriptTask",
    "manualTask": "manualTask",
    "task": "task",
    "exclusiveGateway": "exclusiveGateway",
    "parallelGateway": "parallelGateway",
    "eventBasedGateway": "eventBasedGateway",
    "intermediateCatchEvent": "intermediateCatchEvent",
    "intermediateThrowEvent": "intermediateThrowEvent",
    "subProcess": "subProcess",
}


def generate_bpmn_file(bpmn_json: dict, output_dir: str, proc_id: str, level: str) -> str:
    """Convert BPMN JSON to XML and save as .bpmn file.

    Args:
        bpmn_json: Pre-generated BPMN JSON structure (from LLM or other source).
        output_dir: Directory for output .bpmn files.
        proc_id: Process identifier for filename.
        level: Detail level ("high_level" or "detailed") for filename suffix.

    Returns:
        Path to the generated .bpmn file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    xml_string = bpmn_json_to_xml(bpmn_json)

    suffix = "_detailed" if level == "detailed" else "_overview"
    filename = f"{proc_id}{suffix}.bpmn"
    filepath = Path(output_dir) / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(xml_string)

    return str(filepath)


def bpmn_json_to_xml(bpmn_json: dict) -> str:
    """Convert BPMN JSON structure to BPMN 2.0 XML string.

    Args:
        bpmn_json: BPMN JSON with elements, flows, pools, lanes.

    Returns:
        BPMN 2.0 XML string.
    """
    # Root element
    definitions = etree.Element(
        f"{{{BPMN_NS}}}definitions",
        nsmap=NSMAP,
        attrib={
            "id": "Definitions_1",
            "targetNamespace": "http://bpmn.io/schema/bpmn",
        },
    )

    process_id = _ensure_str(bpmn_json.get("process_id", "Process_1"))
    process_name = _ensure_str(bpmn_json.get("process_name", "Process"))

    # Check if we have pools
    pools = bpmn_json.get("pools", [])

    if pools:
        # Create collaboration for pools
        collaboration = etree.SubElement(
            definitions, f"{{{BPMN_NS}}}collaboration", id="Collaboration_1"
        )

        for pool in pools:
            etree.SubElement(
                collaboration,
                f"{{{BPMN_NS}}}participant",
                id=_ensure_str(pool.get("id", "pool_1")),
                name=_ensure_str(pool.get("name", "")),
                processRef=f"{process_id}_{_ensure_str(pool.get('id', 'pool_1'))}",
            )

    # Create process
    process = etree.SubElement(
        definitions,
        f"{{{BPMN_NS}}}process",
        id=process_id,
        name=process_name,
        isExecutable="false",
    )

    # Add lanes if pools have them
    if pools:
        for pool in pools:
            lanes = pool.get("lanes", [])
            if lanes:
                lane_set = etree.SubElement(process, f"{{{BPMN_NS}}}laneSet", id=f"LaneSet_{pool['id']}")
                for lane in lanes:
                    lane_elem = etree.SubElement(
                        lane_set,
                        f"{{{BPMN_NS}}}lane",
                        id=_ensure_str(lane.get("id", "lane_1")),
                        name=_ensure_str(lane.get("name", "")),
                    )
                    for elem_id in lane.get("elements", []):
                        flow_node_ref = etree.SubElement(lane_elem, f"{{{BPMN_NS}}}flowNodeRef")
                        flow_node_ref.text = _ensure_str(elem_id)

    # Add elements
    elements = bpmn_json.get("elements", [])
    for elem in elements:
        elem_type = _ensure_str(elem.get("type", "task"))
        tag = ELEMENT_TAG_MAP.get(elem_type, "task")
        elem_xml = etree.SubElement(
            process,
            f"{{{BPMN_NS}}}{tag}",
            id=_ensure_str(elem.get("id", "elem_1")),
            name=_ensure_str(elem.get("name", "")),
        )

        # Add incoming/outgoing references
        for incoming in elem.get("incoming", []):
            inc = etree.SubElement(elem_xml, f"{{{BPMN_NS}}}incoming")
            inc.text = _ensure_str(incoming)
        for outgoing in elem.get("outgoing", []):
            out = etree.SubElement(elem_xml, f"{{{BPMN_NS}}}outgoing")
            out.text = _ensure_str(outgoing)

    # Add sequence flows
    flows = bpmn_json.get("flows", [])
    for flow in flows:
        flow_attrib = {
            "id": _ensure_str(flow.get("id", "flow_1")),
            "sourceRef": _ensure_str(flow.get("source", flow.get("sourceRef", ""))),
            "targetRef": _ensure_str(flow.get("target", flow.get("targetRef", ""))),
        }
        flow_name = flow.get("name")
        if flow_name:
            flow_attrib["name"] = _ensure_str(flow_name)

        flow_xml = etree.SubElement(
            process, f"{{{BPMN_NS}}}sequenceFlow", **flow_attrib
        )

        if flow.get("condition"):
            condition = etree.SubElement(
                flow_xml,
                f"{{{BPMN_NS}}}conditionExpression",
                attrib={f"{{{XSI_NS}}}type": "bpmn:tFormalExpression"},
            )
            condition.text = _ensure_str(flow["condition"])

    # Add diagram information (DI)
    positions = auto_layout(bpmn_json)
    _add_diagram(definitions, process_id, bpmn_json, positions)

    # Serialize to string
    return etree.tostring(
        definitions,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    ).decode("utf-8")


def _add_diagram(definitions, process_id, bpmn_json, positions):
    """Add BPMN DI (Diagram Interchange) elements for visual layout."""
    diagram = etree.SubElement(
        definitions, f"{{{BPMNDI_NS}}}BPMNDiagram", id="BPMNDiagram_1"
    )
    plane = etree.SubElement(
        diagram,
        f"{{{BPMNDI_NS}}}BPMNPlane",
        id="BPMNPlane_1",
        bpmnElement=process_id,
    )

    # Add shapes for elements
    for elem in bpmn_json.get("elements", []):
        eid = _ensure_str(elem.get("id", "elem_1"))
        pos = positions.get(eid, {"x": 100, "y": 100, "width": 100, "height": 80})

        shape = etree.SubElement(
            plane,
            f"{{{BPMNDI_NS}}}BPMNShape",
            id=f"{eid}_di",
            bpmnElement=eid,
        )

        etree.SubElement(
            shape,
            f"{{{DC_NS}}}Bounds",
            x=str(pos["x"]),
            y=str(pos["y"]),
            width=str(pos["width"]),
            height=str(pos["height"]),
        )

    # Add edges for flows
    for flow in bpmn_json.get("flows", []):
        fid = _ensure_str(flow.get("id", "flow_1"))
        source_key = _ensure_str(flow.get("source", flow.get("sourceRef", "")))
        target_key = _ensure_str(flow.get("target", flow.get("targetRef", "")))
        source_pos = positions.get(source_key, {"x": 100, "y": 140})
        target_pos = positions.get(target_key, {"x": 300, "y": 140})

        edge = etree.SubElement(
            plane,
            f"{{{BPMNDI_NS}}}BPMNEdge",
            id=f"{fid}_di",
            bpmnElement=fid,
        )

        # Source waypoint (right side of source)
        src_x = source_pos["x"] + source_pos.get("width", 100)
        src_y = source_pos["y"] + source_pos.get("height", 80) // 2
        etree.SubElement(
            edge, f"{{{DI_NS}}}waypoint", x=str(src_x), y=str(src_y)
        )

        # Target waypoint (left side of target)
        tgt_x = target_pos["x"]
        tgt_y = target_pos["y"] + target_pos.get("height", 80) // 2
        etree.SubElement(
            edge, f"{{{DI_NS}}}waypoint", x=str(tgt_x), y=str(tgt_y)
        )
