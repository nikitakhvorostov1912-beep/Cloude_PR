"""
BPM Architect: Повторный аудит всех процессов после исправлений.
Проверяет структуру, логику, layout, полноту.
"""

import json
from pathlib import Path


def audit_process(filepath: Path) -> dict:
    """Полный аудит одного процесса."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = {
        "name": data.get("process_name", "?"),
        "elements_count": len(data.get("elements", [])),
        "flows_count": len(data.get("flows", [])),
        "errors": [],
        "warnings": [],
    }

    elements = data.get("elements", [])
    flows = data.get("flows", [])
    layout = data.get("layout", {})

    elem_ids = {e["id"] for e in elements}
    elem_map = {e["id"]: e for e in elements}

    # СТРУКТУРА
    # Start Event
    start_events = [e for e in elements if e.get("type") == "startEvent"]
    if not start_events:
        results["errors"].append("Нет Start Event")
    else:
        results["warnings"].append(f"Start Events: {len(start_events)}")

    # End Event
    end_events = [e for e in elements if e.get("type") == "endEvent"]
    if not end_events:
        results["errors"].append("Нет End Event")
    else:
        results["warnings"].append(f"End Events: {len(end_events)}")

    # Gateway входящие/исходящие
    for elem in elements:
        if "Gateway" in elem.get("type", ""):
            eid = elem["id"]
            incoming = [f for f in flows if f.get("target") == eid]
            outgoing = [f for f in flows if f.get("source") == eid]
            if not incoming:
                results["errors"].append(f"Gateway {eid} без входящих потоков")
            if not outgoing:
                results["errors"].append(f"Gateway {eid} без исходящих потоков")

    # Висящие элементы
    for elem in elements:
        eid = elem["id"]
        etype = elem.get("type", "")
        incoming = [f for f in flows if f.get("target") == eid]
        outgoing = [f for f in flows if f.get("source") == eid]

        if etype == "startEvent" and not outgoing:
            results["errors"].append(f"Start Event {eid} без исходящих потоков")
        elif etype == "endEvent" and not incoming:
            results["errors"].append(f"End Event {eid} без входящих потоков")
        elif etype not in ("startEvent", "endEvent"):
            if not incoming and not outgoing:
                results["errors"].append(f"Элемент {eid} полностью изолирован")

    # Некорректные ссылки в flows
    for flow in flows:
        src = flow.get("source", "")
        tgt = flow.get("target", "")
        if src not in elem_ids:
            results["errors"].append(f"Flow {flow.get('id')}: source '{src}' не существует")
        if tgt not in elem_ids:
            results["errors"].append(f"Flow {flow.get('id')}: target '{tgt}' не существует")

    # Дубликаты элементов
    seen = set()
    for elem in elements:
        if elem["id"] in seen:
            results["errors"].append(f"Дубликат элемента: {elem['id']}")
        seen.add(elem["id"])

    # ЛОГИКА
    # Gateway подписи
    for elem in elements:
        if "Gateway" in elem.get("type", "") and "split" in elem.get("id", ""):
            if not elem.get("name"):
                results["warnings"].append(f"Split gateway {elem['id']} без названия")

    # XOR gateway подписи на потоках
    for elem in elements:
        if elem.get("type") == "exclusiveGateway" and "split" in elem.get("id", ""):
            outgoing = [f for f in flows if f.get("source") == elem["id"]]
            for flow in outgoing:
                if not flow.get("name"):
                    results["warnings"].append(
                        f"Поток {flow.get('id')} из XOR gateway без подписи"
                    )

    # Дубликаты названий
    names = [e.get("name", "") for e in elements if e.get("name")]
    duplicates = set(n for n in names if names.count(n) > 1)
    for dup in duplicates:
        results["warnings"].append(f"Дублирующееся название: '{dup}'")

    # Обрезанные названия (заканчиваются на ...)
    for elem in elements:
        name = elem.get("name", "")
        if name.endswith("...") or name.endswith("…"):
            results["warnings"].append(f"Обрезанное название: {elem['id']} = '{name}'")

    # LAYOUT
    element_positions = layout.get("elements", {})
    lane_positions = layout.get("lanes", {})

    # Элементы внутри lanes
    for elem in elements:
        eid = elem.get("id", "")
        lane = elem.get("lane", "")
        epos = element_positions.get(eid)
        lpos = lane_positions.get(lane)
        if epos and lpos:
            if epos["y"] < lpos["y"] - 5 or epos["y"] + epos["height"] > lpos["y"] + lpos["height"] + 5:
                results["errors"].append(
                    f"Элемент {eid} выходит за границы lane {lane}"
                )

    # Lanes подписаны
    participants = data.get("participants", [])
    for part in participants:
        if part.get("lane_id") and not part.get("name"):
            results["warnings"].append(f"Lane {part.get('lane_id')} без названия")

    return results


def main():
    base_dir = Path(__file__).resolve().parent.parent / "data" / "projects"

    process_files = [
        base_dir / "ecb4ac19b44f49bb9da0ab72d817251a" / "processes" / "proc_001_bpmn.json",
        base_dir / "ecb4ac19b44f49bb9da0ab72d817251a" / "processes" / "proc_002_bpmn.json",
        base_dir / "ecb4ac19b44f49bb9da0ab72d817251a" / "processes" / "proc_003_bpmn.json",
        base_dir / "ecb4ac19b44f49bb9da0ab72d817251a" / "processes" / "proc_004_bpmn.json",
        base_dir / "6fa5881144a34dcf9ea274c5ca448e07" / "processes" / "proc_purchase_bpmn.json",
    ]

    all_ok = True
    for filepath in process_files:
        result = audit_process(filepath)

        grade = "A" if not result["errors"] and len(result["warnings"]) <= 5 else \
                "B" if not result["errors"] else \
                "C" if len(result["errors"]) <= 3 else "D"

        print(f"\n{'='*60}")
        print(f"  {result['name']}")
        print(f"  Элементов: {result['elements_count']} | Потоков: {result['flows_count']}")
        print(f"  ОЦЕНКА: {grade}")
        print(f"{'='*60}")

        if result["errors"]:
            print("  ОШИБКИ:")
            for err in result["errors"]:
                print(f"    [ERROR] {err}")
            all_ok = False

        if result["warnings"]:
            print("  ЗАМЕЧАНИЯ:")
            for warn in result["warnings"]:
                print(f"    [WARN]  {warn}")

    print(f"\n{'='*60}")
    if all_ok:
        print("  ИТОГ: ВСЕ ПРОЦЕССЫ ПРОШЛИ АУДИТ")
    else:
        print("  ИТОГ: ЕСТЬ ОШИБКИ, ТРЕБУЕТСЯ ИСПРАВЛЕНИЕ")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
