"""Index recorded explanations by printed invoice position, without another model call."""
import json
from pathlib import Path

from .trace import write_json


def collect(folder):
    inputs = json.loads((folder / "input.json").read_text())
    positions = {str(p): {"fable": [], "python": []} for p in inputs["positions"]}
    audit = dict(game=inputs["game"], positions=positions, fable_revisions=[], python_configuration=None)
    for arm in ("fable", "python"):
        path = folder / f"{arm}.jsonl"
        if not path.exists():
            continue
        requests = {}
        consulted = []
        for raw in path.read_text().splitlines():
            event = json.loads(raw)
            kind = event["event"]
            if kind == "configured" and arm == "python":
                audit["python_configuration"] = event
            if kind == "tool" and event["tool"] in {"Read", "Grep", "Glob"}:
                requests[event["id"]] = event
            if kind == "tool_result" and event["id"] in requests:
                request = requests.pop(event["id"])
                if not event["failed"]:
                    args = dict(request["arguments"])
                    if "file_path" in args:
                        args["file_path"] = Path(args["file_path"]).name
                    consulted.append(dict(tool=request["tool"], arguments=args, elapsed_s=event["elapsed_s"]))
            if kind != "decision":
                continue
            changes = {r["index"]: r for r in event["changes"]}
            trigger = event["trigger"]
            if arm == "fable":
                audit["fable_revisions"].append(dict(write=trigger["tool_call"], elapsed_s=event["elapsed_s"],
                                                     successful_reads_since_previous=consulted))
                consulted = []
            for line in event["lines"]:
                idx = line["index"]
                change = changes.get(idx)
                row = dict(elapsed_s=event["elapsed_s"], on_time=event["on_time"], change=change,
                           charge_price=line["charge_price"], acceptance_limit=line["acceptance_limit"])
                if arm == "fable":
                    row.update(write=trigger["tool_call"], stated_reason=line.get("evidence") or None)
                else:
                    estimate = line.get("arriving_reader") or {}
                    row.update(reader=trigger["member"], stated_reason=estimate.get("rationale") or None,
                               reader_estimate={k: v for k, v in estimate.items() if k != "rationale"},
                               combined_median=line["median"], combined_validity=line["validity"])
                positions[str(idx)][arm].append(row)
    return audit


def save(folder):
    write_json(folder / "decision_reasons.json", collect(folder))
