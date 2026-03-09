"""Validate extracted process data for completeness and consistency."""


def validate_processes(processes: dict) -> dict:
    """Validate extracted processes and return validation report.

    Args:
        processes: Extracted processes dict.

    Returns:
        Validation report with warnings and errors.
    """
    errors = []
    warnings = []

    # Check top-level structure
    if not processes.get("processes"):
        errors.append("No processes extracted from transcript")
        return {"valid": False, "errors": errors, "warnings": warnings}

    for i, proc in enumerate(processes["processes"]):
        proc_name = proc.get("name", f"Process #{i+1}")
        prefix = f"[{proc_name}]"

        # Required fields
        if not proc.get("name"):
            errors.append(f"{prefix} Missing process name")
        if not proc.get("trigger"):
            warnings.append(f"{prefix} Missing trigger/start event")
        if not proc.get("result"):
            warnings.append(f"{prefix} Missing result/end state")

        # Steps validation
        steps = proc.get("steps", [])
        if not steps:
            errors.append(f"{prefix} No steps defined")
        elif len(steps) < 2:
            warnings.append(f"{prefix} Only {len(steps)} step(s) — may be incomplete")

        for j, step in enumerate(steps):
            step_name = step.get("name", f"Step #{j+1}")
            if not step.get("name"):
                warnings.append(f"{prefix} Step #{j+1} has no name")
            if not step.get("performer"):
                warnings.append(f"{prefix} Step '{step_name}' has no performer assigned")

        # Participants validation
        participants = proc.get("participants", [])
        if not participants:
            warnings.append(f"{prefix} No participants defined")

        # Check that step performers match participants
        participant_roles = {p.get("role", "").lower() for p in participants}
        for step in steps:
            performer = step.get("performer", "").lower()
            if performer and participant_roles and performer not in participant_roles:
                warnings.append(
                    f"{prefix} Step performer '{step.get('performer')}' "
                    f"not in participants list"
                )

        # Decisions validation
        for dec in proc.get("decisions", []):
            if not dec.get("options"):
                warnings.append(
                    f"{prefix} Decision '{dec.get('question', '?')}' has no options"
                )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "process_count": len(processes.get("processes", [])),
        "total_steps": sum(
            len(p.get("steps", [])) for p in processes.get("processes", [])
        ),
    }


def validate_bpmn_json(bpmn_json: dict) -> dict:
    """Validate BPMN JSON structure before XML conversion.

    Args:
        bpmn_json: BPMN JSON from LLM.

    Returns:
        Validation report.
    """
    errors = []
    warnings = []

    elements = bpmn_json.get("elements", [])
    flows = bpmn_json.get("flows", [])

    if not elements:
        errors.append("No BPMN elements defined")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Check for start and end events
    element_types = [e.get("type") for e in elements]
    if "startEvent" not in element_types:
        errors.append("Missing startEvent")
    if "endEvent" not in element_types:
        errors.append("Missing endEvent")

    # Build element ID set for reference checking
    element_ids = {e.get("id") for e in elements}

    # Validate flows
    for flow in flows:
        source = flow.get("source")
        target = flow.get("target")
        if source not in element_ids:
            errors.append(f"Flow '{flow.get('id')}' references unknown source: {source}")
        if target not in element_ids:
            errors.append(f"Flow '{flow.get('id')}' references unknown target: {target}")

    # Check connectivity — every non-start element should have incoming flow
    flow_targets = {f.get("target") for f in flows}
    flow_sources = {f.get("source") for f in flows}

    for elem in elements:
        eid = elem.get("id")
        etype = elem.get("type")

        if etype != "startEvent" and eid not in flow_targets:
            warnings.append(f"Element '{eid}' ({etype}) has no incoming flow")
        if etype != "endEvent" and eid not in flow_sources:
            warnings.append(f"Element '{eid}' ({etype}) has no outgoing flow")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "element_count": len(elements),
        "flow_count": len(flows),
    }
