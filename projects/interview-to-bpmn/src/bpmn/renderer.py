"""Render BPMN XML to images (PNG/SVG/PDF)."""
import os
import shutil
import subprocess
from pathlib import Path


def render_bpmn(bpmn_path: str, output_dir: str, config: dict) -> str:
    """Render a .bpmn file to an image.

    Uses bpmn-to-image (Node.js) if available, otherwise falls back to
    a basic SVG generation.

    Args:
        bpmn_path: Path to .bpmn file.
        output_dir: Directory for output images.
        config: Application config.

    Returns:
        Path to rendered image file.
    """
    os.makedirs(output_dir, exist_ok=True)

    output_format = config.get("bpmn", {}).get("output_format", "png")
    scale = config.get("bpmn", {}).get("scale", 2)

    bpmn_file = Path(bpmn_path)
    output_path = Path(output_dir) / f"{bpmn_file.stem}.{output_format}"

    # Try bpmn-to-image (Node.js tool)
    if _has_bpmn_to_image():
        return _render_with_bpmn_to_image(
            str(bpmn_file), str(output_path), output_format, scale
        )

    # Fallback: generate basic SVG
    return _render_fallback_svg(str(bpmn_file), str(output_dir))


def _has_bpmn_to_image() -> bool:
    """Check if bpmn-to-image is installed."""
    return shutil.which("bpmn-to-image") is not None


def _render_with_bpmn_to_image(
    bpmn_path: str, output_path: str, fmt: str, scale: int
) -> str:
    """Render using bpmn-to-image CLI tool."""
    cmd = [
        "bpmn-to-image",
        f"{bpmn_path}:{output_path}",
    ]

    # bpmn-to-image supports --min-dimensions and --title
    if scale > 1:
        # Use min-dimensions for larger output
        cmd.extend(["--min-dimensions", f"{800 * scale}x{600 * scale}"])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"bpmn-to-image error: {result.stderr}")

    return output_path


def _render_fallback_svg(bpmn_path: str, output_dir: str) -> str:
    """Generate a basic SVG representation as fallback when bpmn-to-image is not available."""
    from lxml import etree

    # Parse BPMN XML
    tree = etree.parse(bpmn_path)
    root = tree.getroot()

    ns = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
          "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
          "dc": "http://www.omg.org/spec/DD/20100524/DC",
          "di": "http://www.omg.org/spec/DD/20100524/DI"}

    # Find all shapes
    shapes = root.findall(".//bpmndi:BPMNShape", ns)
    edges = root.findall(".//bpmndi:BPMNEdge", ns)

    # Determine canvas size
    max_x, max_y = 800, 600
    elements_info = []

    for shape in shapes:
        bounds = shape.find("dc:Bounds", ns)
        if bounds is not None:
            x = float(bounds.get("x", 0))
            y = float(bounds.get("y", 0))
            w = float(bounds.get("width", 100))
            h = float(bounds.get("height", 80))
            bpmn_elem_id = shape.get("bpmnElement", "")

            max_x = max(max_x, x + w + 50)
            max_y = max(max_y, y + h + 50)

            # Find element name
            name = ""
            for elem in root.iter():
                if elem.get("id") == bpmn_elem_id:
                    name = elem.get("name", "")
                    break

            elements_info.append({
                "id": bpmn_elem_id,
                "x": x, "y": y, "w": w, "h": h,
                "name": name,
                "tag": _get_element_tag(root, bpmn_elem_id, ns),
            })

    # Generate SVG
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(max_x)}" height="{int(max_y)}" '
        f'viewBox="0 0 {int(max_x)} {int(max_y)}">',
        '<defs>',
        '<style>',
        '  .task { fill: #fff; stroke: #333; stroke-width: 2; rx: 10; }',
        '  .event-start { fill: #fff; stroke: #52b415; stroke-width: 2; }',
        '  .event-end { fill: #fff; stroke: #e53935; stroke-width: 3; }',
        '  .gateway { fill: #fff; stroke: #f9a825; stroke-width: 2; }',
        '  .label { font-family: Arial, sans-serif; font-size: 12px; text-anchor: middle; }',
        '  .flow { fill: none; stroke: #333; stroke-width: 1.5; marker-end: url(#arrow); }',
        '</style>',
        '<marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '  <path d="M 0 0 L 10 5 L 0 10 z" fill="#333" />',
        '</marker>',
        '</defs>',
    ]

    # Draw elements
    for info in elements_info:
        tag = info["tag"]
        x, y, w, h = info["x"], info["y"], info["w"], info["h"]
        name = info["name"]

        if "startEvent" in tag:
            cx, cy, r = x + w/2, y + h/2, w/2
            svg_parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" class="event-start"/>')
        elif "endEvent" in tag:
            cx, cy, r = x + w/2, y + h/2, w/2
            svg_parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" class="event-end"/>')
        elif "Gateway" in tag:
            cx, cy = x + w/2, y + h/2
            points = f"{cx},{y} {x+w},{cy} {cx},{y+h} {x},{cy}"
            svg_parts.append(f'<polygon points="{points}" class="gateway"/>')
        else:
            svg_parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="task" rx="10"/>')

        if name:
            tx = x + w / 2
            lines = _wrap_text(name, max_chars=15)
            # Center vertically based on number of lines
            line_height = 14
            start_y = y + h / 2 - (len(lines) - 1) * line_height / 2 + 4
            text_parts = [f'<text x="{tx}" class="label">']
            for i, line in enumerate(lines):
                dy = 0 if i == 0 else line_height
                text_parts.append(
                    f'  <tspan x="{tx}" dy="{dy}">{_escape_xml(line)}</tspan>'
                )
            text_parts.append('</text>')
            # Set y on first tspan
            text_parts[1] = text_parts[1].replace('dy="0"', f'y="{start_y}"')
            svg_parts.extend(text_parts)

    # Draw edges
    for edge in edges:
        waypoints = edge.findall("di:waypoint", ns)
        if len(waypoints) >= 2:
            points = " ".join(f"{wp.get('x')},{wp.get('y')}" for wp in waypoints)
            svg_parts.append(f'<polyline points="{points}" class="flow"/>')

    svg_parts.append("</svg>")

    # Save SVG
    bpmn_file = Path(bpmn_path)
    svg_path = Path(output_dir) / f"{bpmn_file.stem}.svg"
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))

    return str(svg_path)


def _get_element_tag(root, elem_id: str, ns: dict) -> str:
    """Get the BPMN tag of an element by ID."""
    for elem in root.iter():
        if elem.get("id") == elem_id:
            tag = elem.tag
            # Strip namespace
            if "}" in tag:
                tag = tag.split("}")[1]
            return tag
    return "task"


def _wrap_text(text: str, max_chars: int = 15) -> list[str]:
    """Wrap text into lines of approximately max_chars width."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines or [text]


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
