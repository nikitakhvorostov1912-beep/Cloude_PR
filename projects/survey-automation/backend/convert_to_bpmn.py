"""Convert processes.json to individual BPMN JSON files."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from app.bpmn.process_to_bpmn import ProcessToBpmnConverter

project_id = sys.argv[1] if len(sys.argv) > 1 else "9bfe7c8b61614555a54273a7527218a1"
project_dir = f"data/projects/{project_id}"

with open(f"{project_dir}/processes/processes.json", "r", encoding="utf-8") as f:
    data = json.load(f)

converter = ProcessToBpmnConverter()
processes = data.get("processes", [])
print(f"Found {len(processes)} processes")

for proc in processes:
    pid = proc.get("id", proc.get("process_id", "unknown"))
    bpmn_json = converter.convert(proc)
    out_path = f"{project_dir}/processes/{pid}_bpmn.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bpmn_json, f, ensure_ascii=False, indent=2)
    print(f"  -> {out_path} ({len(bpmn_json.get('elements', []))} elements, {len(bpmn_json.get('flows', []))} flows)")

print("Done!")
