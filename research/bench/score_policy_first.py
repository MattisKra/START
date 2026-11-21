"""Score paired policy-first and standard Fable receipts and audit policy access."""
import argparse
import json
from pathlib import Path

from factor_replay import gap
from rate_check_replay import Source, settled_field
from score_shadow import follow, prices
from claimbot_shadow.trace import write_json


def read(path):
    return json.loads(path.read_text())


def receipts(path):
    calls = {}
    access = {"Read": [], "Grep": []}
    access_at_write = {}
    accepted, rejected = [], []
    for line in path.read_text().splitlines() if path.exists() else []:
        event = json.loads(line)
        if event["event"] == "tool":
            tool, args = event["tool"], event["arguments"]
            calls[event["id"]] = (tool, Path(args.get("file_path") or args.get("path") or "").name)
            if tool == "Write":
                access_at_write[event["id"]] = {k: list(v) for k, v in access.items()}
        elif event["event"] == "tool_result" and not event["failed"]:
            tool, name = calls[event["id"]]
            if name == "policy.txt" and tool in access:
                access[tool].append(event["elapsed_s"])
        elif event["event"] == "policy_rejected":
            rejected.append(event["elapsed_s"])
        elif event["event"] == "decision" and event["on_time"]:
            event["policy_access_before_write"] = access_at_write[event["trigger"]["tool_call"]]
            accepted.append(event)
    return accepted, rejected


def compare(field, control, treatment):
    old, new = prices(control), prices(treatment)
    if set(old) != set(field) or set(new) != set(field):
        raise ValueError("Receipt and settled positions differ")
    lines = []
    original = {r["index"]: r for r in control["lines"]}
    for r in treatment["lines"]:
        p = r["index"]
        before = original[p]
        if (old[p], before.get("p_valid")) == (new[p], r.get("p_valid")):
            continue
        lines.append(dict(position=p, control_actions=old[p], treatment_actions=new[p],
                          control_p_valid=before.get("p_valid"), treatment_p_valid=r.get("p_valid"),
                          control_evidence=before.get("evidence"), treatment_evidence=r.get("evidence"),
                          **gap({p: field[p]}, old, new)))
    return dict(status="paired", control_s=control["elapsed_s"], treatment_s=treatment["elapsed_s"],
                control_policy_access=control["policy_access_before_write"],
                treatment_proof=treatment["trigger"]["policy_proof"], **gap(field, old, new), lines=lines)


def save(folder):
    game = read(folder / "result.json")["game"]
    meta = next(g for g in read(folder.parent / "manifest.json")["games"] if g["id"] == game)
    other = Path(meta["control_dir"])
    if not (other / "result.json").exists():
        raise ValueError("Awaiting standard Fable result")
    a, b = read(folder / "input.json"), read(other / "input.json")
    for key in ("game", "release", "positions", "archive_sha256"):
        if a[key] != b[key]:
            raise ValueError(f"Paired inputs differ on {key}")
    control, _ = receipts(other / "fable.jsonl")
    treatment, rejected = receipts(folder / "policy_first.jsonl")
    for name, events, source in (("fable", control, other), ("policy_first", treatment, folder)):
        last = read(source / "result.json")["final"].get(name)
        if (events[-1]["trigger"] if events else None) != (last["trigger"] if last else None):
            raise ValueError(f"Trace and final {name} result disagree")
    report = dict(game=game, receipts=dict(control=[r["elapsed_s"] for r in control],
                  policy_first=[r["elapsed_s"] for r in treatment]), rejected_writes=rejected)
    field = None
    if control and treatment:
        src = Source()
        matrix = src.get("matrix", page=1, game_limit=game)
        if not matrix or game not in matrix["game_ids"] or any(
                t["cells"][matrix["game_ids"].index(game)] is None for t in matrix["items"]):
            raise ValueError(f"Game {game} has not settled")
        field = settled_field(src, matrix, game, a["positions"])
    for name, cutoff, index in (("first", 60, 0), ("at_54s", 54, -1), ("at_60s", 60, -1)):
        eligible = [[r for r in events if r["elapsed_s"] <= cutoff] for events in (control, treatment)]
        if all(eligible):
            report[name] = compare(field, eligible[0][index], eligible[1][index])
        else:
            report[name] = dict(status="unpaired", control_available=bool(eligible[0]),
                                treatment_available=bool(eligible[1]))
    write_json(folder / "score.json", report)
    print(game, report["at_54s"]["status"], report["at_54s"].get("net"), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--follow", action="store_true")
    args = parser.parse_args()
    if args.follow:
        follow(args.folder, scorer=save)
    else:
        save(args.folder)
