"""Automatic layout for BPMN elements."""

# Element dimensions by type
DIMENSIONS = {
    "startEvent": {"width": 36, "height": 36},
    "endEvent": {"width": 36, "height": 36},
    "exclusiveGateway": {"width": 50, "height": 50},
    "parallelGateway": {"width": 50, "height": 50},
    "eventBasedGateway": {"width": 50, "height": 50},
    "intermediateCatchEvent": {"width": 36, "height": 36},
    "intermediateThrowEvent": {"width": 36, "height": 36},
    "subProcess": {"width": 150, "height": 100},
}

DEFAULT_DIM = {"width": 100, "height": 80}

# Layout constants
H_SPACING = 60  # Horizontal spacing between elements
V_SPACING = 100  # Vertical spacing for parallel branches
START_X = 180
START_Y = 200
LANE_HEIGHT = 200
LANE_HEADER_WIDTH = 30


def auto_layout(bpmn_json: dict) -> dict:
    """Calculate positions for all BPMN elements.

    Uses a simple left-to-right layout following the flow structure.

    Args:
        bpmn_json: BPMN JSON with elements and flows.

    Returns:
        Dict mapping element ID to position {x, y, width, height}.
    """
    elements = bpmn_json.get("elements", [])
    flows = bpmn_json.get("flows", [])
    pools = bpmn_json.get("pools", [])

    if not elements:
        return {}

    # Build adjacency list
    outgoing = {}  # element_id -> [target_ids]
    incoming = {}  # element_id -> [source_ids]
    for flow in flows:
        src = flow.get("source")
        tgt = flow.get("target")
        outgoing.setdefault(src, []).append(tgt)
        incoming.setdefault(tgt, []).append(src)

    # Build element lookup
    elem_by_id = {e["id"]: e for e in elements}

    # Find start elements (no incoming flows)
    start_ids = [e["id"] for e in elements if e.get("type") == "startEvent"]
    if not start_ids:
        # Fallback: elements with no incoming
        start_ids = [e["id"] for e in elements if e["id"] not in incoming]
    if not start_ids and elements:
        start_ids = [elements[0]["id"]]

    # BFS to assign columns (x positions)
    positions = {}
    visited = set()
    queue = []

    for sid in start_ids:
        queue.append((sid, 0, 0))  # (id, column, row)

    col_count = {}  # column -> count of elements in that column

    while queue:
        eid, col, row = queue.pop(0)
        if eid in visited:
            continue
        visited.add(eid)

        # Track how many elements in each column
        if col not in col_count:
            col_count[col] = 0
        current_row = col_count[col]
        col_count[col] += 1

        elem = elem_by_id.get(eid, {})
        etype = elem.get("type", "task")
        dims = DIMENSIONS.get(etype, DEFAULT_DIM)

        x = START_X + col * (DEFAULT_DIM["width"] + H_SPACING)
        y = START_Y + current_row * (DEFAULT_DIM["height"] + V_SPACING)

        # Center events and gateways vertically
        if etype in ("startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent"):
            y += (DEFAULT_DIM["height"] - dims["height"]) // 2
            x += (DEFAULT_DIM["width"] - dims["width"]) // 2

        if etype in ("exclusiveGateway", "parallelGateway", "eventBasedGateway"):
            y += (DEFAULT_DIM["height"] - dims["height"]) // 2
            x += (DEFAULT_DIM["width"] - dims["width"]) // 2

        positions[eid] = {
            "x": x,
            "y": y,
            "width": dims["width"],
            "height": dims["height"],
        }

        # Add successors to queue, spread parallel branches vertically
        targets = outgoing.get(eid, [])
        for i, target in enumerate(targets):
            if target not in visited:
                queue.append((target, col + 1, i))

    # Resolve collisions: shift overlapping elements down
    _resolve_collisions(positions)

    # Handle any unvisited elements
    max_col = max(col_count.keys(), default=0) + 1
    for elem in elements:
        if elem["id"] not in positions:
            etype = elem.get("type", "task")
            dims = DIMENSIONS.get(etype, DEFAULT_DIM)
            positions[elem["id"]] = {
                "x": START_X + max_col * (DEFAULT_DIM["width"] + H_SPACING),
                "y": START_Y,
                "width": dims["width"],
                "height": dims["height"],
            }
            max_col += 1

    # If pools/lanes exist, adjust Y positions
    if pools:
        _adjust_for_lanes(positions, pools, elem_by_id)

    return positions


def _resolve_collisions(positions: dict) -> None:
    """Shift overlapping elements down to avoid visual collision."""
    padding = 20
    ids = list(positions.keys())
    changed = True
    max_iterations = 50
    iteration = 0
    while changed and iteration < max_iterations:
        changed = False
        iteration += 1
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = positions[ids[i]], positions[ids[j]]
                # Check overlap: same x-range and y-range
                if (a["x"] < b["x"] + b["width"] and a["x"] + a["width"] > b["x"]
                        and a["y"] < b["y"] + b["height"] and a["y"] + a["height"] > b["y"]):
                    # Push b down below a
                    b["y"] = a["y"] + a["height"] + padding
                    changed = True


def _adjust_for_lanes(positions: dict, pools: list, elem_by_id: dict):
    """Adjust Y positions to fit elements within their lanes."""
    lane_y = START_Y
    padding = 20

    for pool in pools:
        for lane in pool.get("lanes", []):
            lane_elements = lane.get("elements", [])

            # Sort elements by their current x position to maintain flow order
            lane_elems_with_pos = [
                (eid, positions[eid]) for eid in lane_elements if eid in positions
            ]
            lane_elems_with_pos.sort(key=lambda ep: ep[1]["x"])

            # Group elements by column (same x position) and stack vertically
            current_y = lane_y + padding
            prev_x = None
            for eid, pos in lane_elems_with_pos:
                if prev_x is not None and pos["x"] != prev_x:
                    # New column — reset y
                    current_y = lane_y + padding
                positions[eid]["y"] = current_y
                current_y += pos["height"] + padding
                prev_x = pos["x"]

            # Calculate required lane height based on elements
            max_elem_bottom = max(
                (positions[eid]["y"] + positions[eid]["height"]
                 for eid in lane_elements if eid in positions),
                default=lane_y,
            )
            actual_height = max(LANE_HEIGHT, max_elem_bottom - lane_y + padding)
            lane_y += actual_height
