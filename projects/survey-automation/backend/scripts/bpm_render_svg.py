#!/usr/bin/env python3
"""
BPM Architect — SVG рендеринг BPMN диаграмм.
Генерирует SVG файл из BPMN JSON с визуализацией:
- Элементы (Start/End Events, Tasks, Gateways, Timer/Error Events, Sub-Process)
- Связи (Sequence Flow) со стрелками
- Lanes с подписями
- Pool с заголовком
- Message Flow (пунктирные линии)
"""

import json
import os
import sys
import html as html_mod

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT1_DIR = os.path.join(BASE_DIR, "data", "projects", "ecb4ac19b44f49bb9da0ab72d817251a", "processes")
PROJECT2_DIR = os.path.join(BASE_DIR, "data", "projects", "6fa5881144a34dcf9ea274c5ca448e07", "processes")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "visual")

# Colors
COLORS = {
    "start": "#4CAF50",
    "end": "#f44336",
    "end_error": "#B71C1C",
    "task": "#2196F3",
    "userTask": "#1976D2",
    "serviceTask": "#0D47A1",
    "gateway": "#FF9800",
    "timer": "#9C27B0",
    "error_intermediate": "#E91E63",
    "subProcess": "#00897B",
    "lane_bg": ["#E3F2FD", "#FFF3E0", "#E8F5E9", "#F3E5F5", "#FBE9E7", "#E0F7FA", "#FFF8E1"],
    "lane_border": "#B0BEC5",
    "pool_bg": "#ECEFF1",
    "pool_header": "#37474F",
    "flow": "#546E7A",
    "flow_label": "#37474F",
    "message_flow": "#E91E63",
}


def escape(text):
    return html_mod.escape(str(text)) if text else ""


def wrap_text(text, max_chars=18):
    """Wrap text for SVG display"""
    if not text:
        return [""]
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def render_start_event(elem, layout):
    x = layout["x"]
    y = layout["y"]
    w = layout["width"]
    h = layout["height"]
    cx = x + w / 2
    cy = y + h / 2
    r = min(w, h) / 2

    svg = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{COLORS["start"]}" stroke="#2E7D32" stroke-width="2"/>\n'
    # Label below
    lines = wrap_text(elem.get("name", ""), 20)
    for i, line in enumerate(lines):
        ty = cy + r + 14 + i * 12
        svg += f'<text x="{cx}" y="{ty}" text-anchor="middle" font-size="9" fill="#333" font-family="Arial">{escape(line)}</text>\n'
    return svg


def render_end_event(elem, layout):
    x = layout["x"]
    y = layout["y"]
    w = layout["width"]
    h = layout["height"]
    cx = x + w / 2
    cy = y + h / 2
    r = min(w, h) / 2
    is_error = elem.get("eventDefinition") == "errorEventDefinition"
    color = COLORS["end_error"] if is_error else COLORS["end"]
    stroke_w = 4 if is_error else 3

    svg = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" stroke="#B71C1C" stroke-width="{stroke_w}"/>\n'
    if is_error:
        # Lightning bolt symbol for error
        svg += f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-size="14" fill="white" font-weight="bold">!</text>\n'
    lines = wrap_text(elem.get("name", ""), 20)
    for i, line in enumerate(lines):
        ty = cy + r + 14 + i * 12
        svg += f'<text x="{cx}" y="{ty}" text-anchor="middle" font-size="9" fill="#333" font-family="Arial">{escape(line)}</text>\n'
    return svg


def render_task(elem, layout):
    x = layout["x"]
    y = layout["y"]
    w = layout["width"]
    h = layout["height"]
    t = elem.get("type", "task")
    if t == "userTask":
        color = COLORS["userTask"]
    elif t == "serviceTask":
        color = COLORS["serviceTask"]
    else:
        color = COLORS["task"]

    svg = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" ry="8" fill="{color}" stroke="#1565C0" stroke-width="1.5"/>\n'

    # Task type icon
    if t == "userTask":
        svg += f'<text x="{x + 8}" y="{y + 14}" font-size="10" fill="white">&#x1f464;</text>\n'
    elif t == "serviceTask":
        svg += f'<text x="{x + 8}" y="{y + 14}" font-size="10" fill="white">&#x2699;</text>\n'

    lines = wrap_text(elem.get("name", ""), 16)
    total_h = len(lines) * 12
    start_y = y + (h - total_h) / 2 + 10
    for i, line in enumerate(lines):
        ty = start_y + i * 12
        svg += f'<text x="{x + w / 2}" y="{ty}" text-anchor="middle" font-size="9" fill="white" font-family="Arial" font-weight="bold">{escape(line)}</text>\n'
    return svg


def render_gateway(elem, layout):
    x = layout["x"]
    y = layout["y"]
    w = layout["width"]
    h = layout["height"]
    cx = x + w / 2
    cy = y + h / 2
    half = w / 2

    points = f"{cx},{cy - half} {cx + half},{cy} {cx},{cy + half} {cx - half},{cy}"
    svg = f'<polygon points="{points}" fill="{COLORS["gateway"]}" stroke="#E65100" stroke-width="1.5"/>\n'
    svg += f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-size="12" fill="white" font-weight="bold">X</text>\n'

    name = elem.get("name", "")
    if name:
        lines = wrap_text(name, 20)
        for i, line in enumerate(lines):
            ty = cy - half - 6 + i * 12
            svg += f'<text x="{cx}" y="{ty}" text-anchor="middle" font-size="9" fill="#333" font-family="Arial" font-style="italic">{escape(line)}</text>\n'
    return svg


def render_timer_event(elem, layout):
    x = layout["x"]
    y = layout["y"]
    w = layout["width"]
    h = layout["height"]
    cx = x + w / 2
    cy = y + h / 2
    r = min(w, h) / 2

    svg = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{COLORS["timer"]}" stroke="#6A1B9A" stroke-width="2"/>\n'
    svg += f'<circle cx="{cx}" cy="{cy}" r="{r - 3}" fill="none" stroke="white" stroke-width="1"/>\n'
    # Clock hands
    svg += f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - r + 6}" stroke="white" stroke-width="1.5"/>\n'
    svg += f'<line x1="{cx}" y1="{cy}" x2="{cx + r - 8}" y2="{cy}" stroke="white" stroke-width="1.5"/>\n'

    lines = wrap_text(elem.get("name", ""), 22)
    for i, line in enumerate(lines):
        ty = cy + r + 14 + i * 12
        svg += f'<text x="{cx}" y="{ty}" text-anchor="middle" font-size="8" fill="#6A1B9A" font-family="Arial" font-weight="bold">{escape(line)}</text>\n'
    return svg


def render_error_intermediate(elem, layout):
    x = layout["x"]
    y = layout["y"]
    w = layout["width"]
    h = layout["height"]
    cx = x + w / 2
    cy = y + h / 2
    r = min(w, h) / 2

    svg = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{COLORS["error_intermediate"]}" stroke="#880E4F" stroke-width="2"/>\n'
    svg += f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" font-size="16" fill="white" font-weight="bold">&#x26A0;</text>\n'

    lines = wrap_text(elem.get("name", ""), 22)
    for i, line in enumerate(lines):
        ty = cy + r + 14 + i * 12
        svg += f'<text x="{cx}" y="{ty}" text-anchor="middle" font-size="8" fill="#880E4F" font-family="Arial" font-weight="bold">{escape(line)}</text>\n'
    return svg


def render_subprocess(elem, layout):
    x = layout["x"]
    y = layout["y"]
    w = layout["width"]
    h = layout["height"]

    svg = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" ry="10" fill="{COLORS["subProcess"]}" stroke="#004D40" stroke-width="2" stroke-dasharray="8,4"/>\n'
    # Plus icon
    cx = x + w / 2
    by = y + h - 14
    svg += f'<rect x="{cx - 8}" y="{by - 2}" width="16" height="10" rx="2" fill="white" stroke="#004D40"/>\n'
    svg += f'<text x="{cx}" y="{by + 6}" text-anchor="middle" font-size="10" fill="#004D40" font-weight="bold">+</text>\n'

    lines = wrap_text(elem.get("name", ""), 30)
    total_h = len(lines) * 14
    start_y = y + (h - total_h) / 2 + 6
    for i, line in enumerate(lines):
        ty = start_y + i * 14
        svg += f'<text x="{cx}" y="{ty}" text-anchor="middle" font-size="11" fill="white" font-family="Arial" font-weight="bold">{escape(line)}</text>\n'
    return svg


def render_flow(flow, waypoints, is_message=False):
    if not waypoints or len(waypoints) < 2:
        return ""

    color = COLORS["message_flow"] if is_message else COLORS["flow"]
    dash = ' stroke-dasharray="6,3"' if is_message else ""

    points = " ".join(f"{p['x']},{p['y']}" for p in waypoints)
    svg = f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.5"{dash}/>\n'

    # Arrowhead at last point
    if len(waypoints) >= 2:
        p1 = waypoints[-2]
        p2 = waypoints[-1]
        dx = p2["x"] - p1["x"]
        dy = p2["y"] - p1["y"]
        import math
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            dx /= length
            dy /= length
            ax = p2["x"] - dx * 8
            ay = p2["y"] - dy * 8
            px = -dy * 4
            py = dx * 4
            arrow_points = f"{p2['x']},{p2['y']} {ax + px},{ay + py} {ax - px},{ay - py}"
            svg += f'<polygon points="{arrow_points}" fill="{color}"/>\n'

    # Flow label
    name = flow.get("name", "")
    if name and len(waypoints) >= 2:
        mid_idx = len(waypoints) // 2
        mx = waypoints[mid_idx - 1]["x"]
        my = waypoints[mid_idx - 1]["y"]
        if mid_idx < len(waypoints):
            mx = (mx + waypoints[mid_idx]["x"]) / 2
            my = (my + waypoints[mid_idx]["y"]) / 2
        svg += f'<rect x="{mx - 20}" y="{my - 12}" width="40" height="14" rx="3" fill="white" stroke="{color}" stroke-width="0.5"/>\n'
        svg += f'<text x="{mx}" y="{my - 2}" text-anchor="middle" font-size="8" fill="{COLORS["flow_label"]}" font-family="Arial" font-weight="bold">{escape(name)}</text>\n'

    return svg


def render_lanes(data, participants_map):
    svg = ""
    lanes = data.get("layout", {}).get("lanes", {})

    for i, (lane_id, lane_layout) in enumerate(lanes.items()):
        x = lane_layout["x"]
        y = lane_layout["y"]
        w = lane_layout["width"]
        h = lane_layout["height"]
        color_idx = i % len(COLORS["lane_bg"])

        svg += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{COLORS["lane_bg"][color_idx]}" stroke="{COLORS["lane_border"]}" stroke-width="1" opacity="0.6"/>\n'

        # Lane label (rotated on left side)
        lane_name = participants_map.get(lane_id, lane_id)
        lx = x + 14
        ly = y + h / 2
        svg += f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="11" fill="#37474F" font-family="Arial" font-weight="bold" transform="rotate(-90,{lx},{ly})">{escape(lane_name)}</text>\n'

    return svg


def render_pool(data, pool_layout, pool_name):
    if not pool_layout:
        return ""
    x = pool_layout["x"]
    y = pool_layout["y"]
    w = pool_layout["width"]
    h = pool_layout["height"]

    svg = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{COLORS["pool_header"]}" stroke-width="2" rx="4"/>\n'
    # Pool header
    svg += f'<rect x="{x}" y="{y}" width="30" height="{h}" fill="{COLORS["pool_header"]}" rx="4"/>\n'
    svg += f'<text x="{x + 15}" y="{y + h / 2}" text-anchor="middle" font-size="12" fill="white" font-family="Arial" font-weight="bold" transform="rotate(-90,{x + 15},{y + h / 2})">{escape(pool_name)}</text>\n'
    return svg


def render_message_flows(data):
    """Render message flow info as annotations"""
    svg = ""
    mflows = data.get("message_flows", [])
    if not mflows:
        return svg

    # Put message flow legend at bottom
    y_start = 50
    svg += f'<rect x="60" y="{y_start}" width="300" height="{len(mflows) * 20 + 30}" rx="6" fill="#FCE4EC" stroke="{COLORS["message_flow"]}" stroke-width="1" opacity="0.9"/>\n'
    svg += f'<text x="210" y="{y_start + 18}" text-anchor="middle" font-size="11" fill="{COLORS["message_flow"]}" font-family="Arial" font-weight="bold">Message Flow (межпроцессные связи)</text>\n'

    for i, mf in enumerate(mflows):
        ty = y_start + 36 + i * 18
        svg += f'<line x1="70" y1="{ty - 3}" x2="110" y2="{ty - 3}" stroke="{COLORS["message_flow"]}" stroke-width="1.5" stroke-dasharray="4,2"/>\n'
        label = f'{mf.get("source_process", "")} → {mf.get("target_process", "")}: {mf.get("name", "")}'
        svg += f'<text x="115" y="{ty}" font-size="9" fill="#333" font-family="Arial">{escape(label)}</text>\n'

    return svg


def render_process(bpmn_path, output_path):
    """Render a BPMN JSON file to SVG"""
    with open(bpmn_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    process_name = data.get("process_name", data.get("process_id", "Unknown"))
    layout = data.get("layout", {})
    elements_layout = layout.get("elements", {})
    flows_layout = layout.get("flows", {})
    lanes_layout = layout.get("lanes", {})

    # Build participants map
    participants_map = {}
    for p in data.get("participants", []):
        if p.get("lane_id"):
            participants_map[p["lane_id"]] = p.get("name", p["id"])

    # Calculate SVG dimensions
    max_x = 100
    max_y = 100
    for el_layout in elements_layout.values():
        max_x = max(max_x, el_layout["x"] + el_layout["width"] + 200)
        max_y = max(max_y, el_layout["y"] + el_layout["height"] + 100)
    for lane_layout in lanes_layout.values():
        max_x = max(max_x, lane_layout["x"] + lane_layout["width"] + 200)
        max_y = max(max_y, lane_layout["y"] + lane_layout["height"] + 100)

    svg_width = max_x + 50
    svg_height = max_y + 50

    svg_parts = []
    svg_parts.append(f'<?xml version="1.0" encoding="UTF-8"?>\n')
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">\n')
    svg_parts.append(f'<style>text {{ font-family: Arial, sans-serif; }}</style>\n')

    # Background
    svg_parts.append(f'<rect width="{svg_width}" height="{svg_height}" fill="#FAFAFA"/>\n')

    # Title
    svg_parts.append(f'<text x="{svg_width / 2}" y="22" text-anchor="middle" font-size="16" fill="#37474F" font-weight="bold">{escape(process_name)}</text>\n')

    # Pool
    pool_key = None
    pool_layout = None
    for p in data.get("participants", []):
        if p.get("processRef"):
            pool_key = p["id"]
            pool_name = p.get("name", "")
            pool_layout_data = layout.get("participants", {}).get(pool_key)
            if pool_layout_data:
                svg_parts.append(render_pool(data, pool_layout_data, pool_name))
            break

    # Lanes
    svg_parts.append(render_lanes(data, participants_map))

    # Flows (render before elements so elements are on top)
    elements_map = {e["id"]: e for e in data.get("elements", [])}
    for flow in data.get("flows", []):
        fid = flow["id"]
        waypoints = flows_layout.get(fid, [])
        if waypoints:
            svg_parts.append(render_flow(flow, waypoints))

    # Elements
    for elem in data.get("elements", []):
        eid = elem["id"]
        el_layout = elements_layout.get(eid)
        if not el_layout:
            continue

        etype = elem.get("type", "")
        event_def = elem.get("eventDefinition", "")

        if etype == "startEvent":
            svg_parts.append(render_start_event(elem, el_layout))
        elif etype == "endEvent":
            svg_parts.append(render_end_event(elem, el_layout))
        elif etype in ("exclusiveGateway", "parallelGateway", "inclusiveGateway"):
            svg_parts.append(render_gateway(elem, el_layout))
        elif etype in ("intermediateCatchEvent", "intermediateThrowEvent") and event_def == "timerEventDefinition":
            svg_parts.append(render_timer_event(elem, el_layout))
        elif etype in ("intermediateCatchEvent", "intermediateThrowEvent") and event_def == "errorEventDefinition":
            svg_parts.append(render_error_intermediate(elem, el_layout))
        elif etype == "subProcess":
            svg_parts.append(render_subprocess(elem, el_layout))
        elif "task" in etype.lower() or etype == "task":
            svg_parts.append(render_task(elem, el_layout))

    # Message flows legend
    svg_parts.append(render_message_flows(data))

    # Legend
    legend_y = max_y - 20
    svg_parts.append(f'<rect x="60" y="{legend_y}" width="580" height="30" rx="4" fill="white" stroke="#B0BEC5" stroke-width="1"/>\n')
    legend_items = [
        ("#4CAF50", "Start Event"),
        ("#f44336", "End Event"),
        ("#2196F3", "Task"),
        ("#FF9800", "Gateway (XOR)"),
        ("#9C27B0", "Timer Event"),
        ("#B71C1C", "Error Event"),
        ("#00897B", "Sub-Process"),
    ]
    lx = 70
    for color, label in legend_items:
        svg_parts.append(f'<rect x="{lx}" y="{legend_y + 9}" width="12" height="12" rx="2" fill="{color}"/>\n')
        svg_parts.append(f'<text x="{lx + 16}" y="{legend_y + 19}" font-size="9" fill="#333">{label}</text>\n')
        lx += 80

    svg_parts.append('</svg>')

    svg_content = "".join(svg_parts)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f"  [SVG] {output_path}")
    return svg_content


def render_l0_map(l0_path, output_path):
    """Render L0 process map as SVG"""
    with open(l0_path, 'r', encoding='utf-8') as f:
        l0 = json.load(f)

    svg_width = 1200
    svg_height = 900

    svg = []
    svg.append(f'<?xml version="1.0" encoding="UTF-8"?>\n')
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">\n')
    svg.append(f'<rect width="{svg_width}" height="{svg_height}" fill="#FAFAFA"/>\n')
    svg.append(f'<text x="600" y="35" text-anchor="middle" font-size="20" fill="#37474F" font-weight="bold" font-family="Arial">КАРТА ПРОЦЕССОВ ПРЕДПРИЯТИЯ (L0)</text>\n')

    y_offset = 60
    for ent in l0.get("enterprises", []):
        # Enterprise header
        svg.append(f'<rect x="40" y="{y_offset}" width="1120" height="40" rx="6" fill="#37474F"/>\n')
        svg.append(f'<text x="600" y="{y_offset + 26}" text-anchor="middle" font-size="14" fill="white" font-weight="bold">{escape(ent["name"])} ({escape(ent.get("type", ""))})</text>\n')
        y_offset += 50

        categories = [
            ("ОСНОВНЫЕ ПРОЦЕССЫ", ent.get("processes", {}).get("core", []), "#4CAF50"),
            ("ПОДДЕРЖИВАЮЩИЕ ПРОЦЕССЫ", ent.get("processes", {}).get("support", []), "#2196F3"),
            ("УПРАВЛЕНЧЕСКИЕ ПРОЦЕССЫ", ent.get("processes", {}).get("management", []), "#FF9800"),
        ]

        for cat_name, procs, color in categories:
            if not procs:
                continue
            svg.append(f'<rect x="60" y="{y_offset}" width="1080" height="28" rx="4" fill="{color}" opacity="0.15"/>\n')
            svg.append(f'<text x="600" y="{y_offset + 19}" text-anchor="middle" font-size="11" fill="{color}" font-weight="bold">{cat_name}</text>\n')
            y_offset += 35

            x_offset = 80
            for proc in procs:
                box_w = 320
                box_h = 110
                if x_offset + box_w > 1140:
                    x_offset = 80
                    y_offset += box_h + 15

                svg.append(f'<rect x="{x_offset}" y="{y_offset}" width="{box_w}" height="{box_h}" rx="8" fill="white" stroke="{color}" stroke-width="2"/>\n')
                svg.append(f'<rect x="{x_offset}" y="{y_offset}" width="{box_w}" height="28" rx="8" fill="{color}"/>\n')
                svg.append(f'<rect x="{x_offset}" y="{y_offset + 14}" width="{box_w}" height="14" fill="{color}"/>\n')
                svg.append(f'<text x="{x_offset + box_w / 2}" y="{y_offset + 19}" text-anchor="middle" font-size="11" fill="white" font-weight="bold">{escape(proc["name"])}</text>\n')

                details = [
                    f'ID: {proc["id"]}',
                    f'Отдел: {proc.get("department", "")}',
                    f'Элементов: {proc.get("elements_count", "?")}',
                    f'Уровень: {proc.get("level", "L1")}',
                ]
                for j, detail in enumerate(details):
                    svg.append(f'<text x="{x_offset + 10}" y="{y_offset + 45 + j * 15}" font-size="9" fill="#555" font-family="Arial">{escape(detail)}</text>\n')

                # Sub-processes
                subs = proc.get("sub_processes", [])
                if subs:
                    svg.append(f'<text x="{x_offset + 10}" y="{y_offset + 45 + len(details) * 15}" font-size="8" fill="#00897B" font-family="Arial" font-weight="bold">Sub: {", ".join(subs)}</text>\n')

                x_offset += box_w + 20

            y_offset += 130

    # Inter-process flows
    flows = l0.get("inter_process_flows", [])
    if flows:
        svg.append(f'<rect x="60" y="{y_offset}" width="1080" height="{len(flows) * 22 + 35}" rx="6" fill="#FCE4EC" stroke="#E91E63"/>\n')
        svg.append(f'<text x="600" y="{y_offset + 20}" text-anchor="middle" font-size="12" fill="#E91E63" font-weight="bold">МЕЖПРОЦЕССНЫЕ СВЯЗИ (Message Flow)</text>\n')
        for i, flow in enumerate(flows):
            fy = y_offset + 38 + i * 20
            svg.append(f'<text x="80" y="{fy}" font-size="10" fill="#333" font-family="Arial">{escape(flow["source"])} → {escape(flow["target"])}: {escape(flow["name"])} — {escape(flow.get("description", ""))}</text>\n')
        y_offset += len(flows) * 22 + 45

    svg_height = max(svg_height, y_offset + 40)
    svg[2] = f'<rect width="{svg_width}" height="{svg_height}" fill="#FAFAFA"/>\n'
    svg[1] = f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">\n'

    svg.append('</svg>')
    svg_content = "".join(svg)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f"  [SVG] L0 карта: {output_path}")


def create_index_html(output_dir, svg_files):
    """Create index.html that shows all SVGs"""
    html = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BPM Architect — Визуальная верификация</title>
<style>
body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }
h1 { color: #37474F; text-align: center; }
h2 { color: #546E7A; border-bottom: 2px solid #B0BEC5; padding-bottom: 8px; }
.process-card {
    background: white; border-radius: 12px; padding: 20px; margin: 20px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow-x: auto;
}
.process-card img, .process-card object {
    max-width: 100%; height: auto;
}
.stats { display: flex; gap: 20px; flex-wrap: wrap; margin: 10px 0; }
.stat { background: #E3F2FD; padding: 8px 16px; border-radius: 20px; font-size: 13px; }
.stat.error { background: #FFEBEE; color: #B71C1C; }
.stat.timer { background: #F3E5F5; color: #6A1B9A; }
.stat.message { background: #FCE4EC; color: #E91E63; }
.stat.sub { background: #E0F2F1; color: #004D40; }
a { color: #1976D2; }
.legend { text-align: center; margin: 20px; color: #777; font-size: 12px; }
</style>
</head>
<body>
<h1>BPM ARCHITECT — ВИЗУАЛЬНАЯ ВЕРИФИКАЦИЯ</h1>
<p style="text-align:center;color:#777;">Все диаграммы сгенерированы из BPMN JSON. Каждый файл можно открыть отдельно.</p>
"""

    for svg_file in svg_files:
        name = os.path.basename(svg_file).replace(".svg", "")
        html += f"""
<div class="process-card">
<h2>{name}</h2>
<p><a href="{os.path.basename(svg_file)}" target="_blank">Открыть SVG в новой вкладке</a></p>
<object data="{os.path.basename(svg_file)}" type="image/svg+xml" style="width:100%;min-height:400px;"></object>
</div>
"""

    html += """
<div class="legend">
BPM Architect — Визуальная верификация BPMN процессов | Автоматически сгенерировано
</div>
</body>
</html>"""

    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  [HTML] Индексная страница: {index_path}")


def main():
    print("=" * 60)
    print("  BPM ARCHITECT — SVG РЕНДЕРИНГ")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    svg_files = []

    # Render all processes
    processes = [
        (os.path.join(PROJECT1_DIR, "proc_001_bpmn.json"), os.path.join(OUTPUT_DIR, "proc_001_bpmn.svg")),
        (os.path.join(PROJECT1_DIR, "proc_002_bpmn.json"), os.path.join(OUTPUT_DIR, "proc_002_bpmn.svg")),
        (os.path.join(PROJECT1_DIR, "proc_003_bpmn.json"), os.path.join(OUTPUT_DIR, "proc_003_bpmn.svg")),
        (os.path.join(PROJECT1_DIR, "proc_004_bpmn.json"), os.path.join(OUTPUT_DIR, "proc_004_bpmn.svg")),
        (os.path.join(PROJECT2_DIR, "proc_purchase_bpmn.json"), os.path.join(OUTPUT_DIR, "proc_purchase_bpmn.svg")),
    ]

    for bpmn_path, svg_path in processes:
        print(f"\n  Рендеринг: {os.path.basename(bpmn_path)}")
        render_process(bpmn_path, svg_path)
        svg_files.append(svg_path)

    # Render L0 map
    l0_path = os.path.join(PROJECT1_DIR, "L0_process_map.json")
    l0_svg_path = os.path.join(OUTPUT_DIR, "L0_process_map.svg")
    print(f"\n  Рендеринг: L0 карта процессов")
    render_l0_map(l0_path, l0_svg_path)
    svg_files.append(l0_svg_path)

    # Create index HTML
    create_index_html(OUTPUT_DIR, svg_files)

    print("\n" + "=" * 60)
    print(f"  ВСЕ ВИЗУАЛИЗАЦИИ СОЗДАНЫ В: {OUTPUT_DIR}")
    print(f"  Файлов: {len(svg_files)} SVG + 1 HTML")
    print("=" * 60)


if __name__ == "__main__":
    main()
