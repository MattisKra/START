"""Replay standard Fable and Fable with separate person-hours and equipment-days."""
import argparse
import json
from pathlib import Path

from factor_replay import gap
from rate_check_replay import Source, settled_field
from score_shadow import follow, prices
from claimbot_shadow.checks import nonnegative
from claimbot_shadow.trace import write_json


def read(path):
    return json.loads(path.read_text())


def breakdown(row):
    if "time_components" not in row:
        return dict(status="missing")
    parts = row["time_components"]
    if parts is None:
        return dict(status="declared_inapplicable")
    if not isinstance(parts, dict) or not nonnegative(parts.get("other_gross")):
        return dict(status="malformed")
    totals = {}
    for name, label, qty, rate in (("labour", "role", "person_hours", "gross_per_hour"),
                                   ("equipment", "item", "unit_days", "gross_per_day")):
        entries = parts.get(name)
        if not isinstance(entries, list) or any(
                not isinstance(e, dict) or not isinstance(e.get(label), str) or not e[label].strip()
                or not nonnegative(e.get(qty)) or not nonnegative(e.get(rate)) for e in entries):
            return dict(status="malformed")
        totals[name] = sum(e[qty] * e[rate] for e in entries)
    if not parts["labour"] and not parts["equipment"]:
        return dict(status="empty_components")
    total = sum(totals.values()) + parts["other_gross"]
    median = row.get("fair_median_gross_if_valid")
    status = "reconciled" if nonnegative(median) and abs(total - median) <= .500001 else "median_mismatch"
    return dict(status=status, details=parts, component_total_gross=round(total, 2),
                labour_gross=round(totals["labour"], 2), equipment_gross=round(totals["equipment"], 2))


def receipts(folder, arm):
    result = read(folder / "result.json")["final"][arm]
    path = folder / f"{arm}.jsonl"
    events = [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    writes = set()
    accepted = []
    for e in events:
        if e["event"] == "tool_result" and e["tool"] == "Write" and not e["failed"]:
            writes.add(e["id"])
        if e["event"] == "decision" and e["on_time"]:
            if e["trigger"]["tool_call"] not in writes:
                raise ValueError("Missing successful decision write")
            accepted.append(e)
    if (accepted[-1] if accepted else None) != result:
        raise ValueError("Trace and final receipt disagree")
    return accepted


def compare(field, items, a, b):
    old, new = prices(a), prices(b)
    if set(old) != set(new) or set(old) != set(field) or set(old) != set(items):
        raise ValueError("Positions differ across inputs, receipts or settlements")
    target = {p: state for p, state in field.items() if items[p]["target"]}
    control = {r["index"]: r for r in a["lines"]}
    lines = []
    for r in b["lines"]:
        p = r["index"]
        c = control[p]
        lines.append(dict(**items[p], control_actions=old[p], treatment_actions=new[p],
                          control_median=c.get("fair_median_gross_if_valid"),
                          treatment_median=r.get("fair_median_gross_if_valid"),
                          control_p_valid=c.get("p_valid"), treatment_p_valid=r.get("p_valid"),
                          control_evidence=c.get("evidence"), treatment_evidence=r.get("evidence"),
                          components=breakdown(r), **gap({p: field[p]}, old, new)))
    return dict(status="paired", control_s=a["elapsed_s"], treatment_s=b["elapsed_s"],
                **gap(field, old, new), target_positions=sorted(target),
                target_payoff=gap(target, old, new) if target else None, lines=lines)


def save(folder):
    inp = read(folder / "input.json")
    game = inp["game"]
    frozen = read(folder.parent / "manifest.json")["games"]
    meta = next(g for g in frozen if g["id"] == game and g["start_time"] == inp["release"])
    other = Path(meta["control_dir"])
    if not (other / "result.json").exists():
        raise ValueError("Awaiting standard Fable receipt")
    baseline = read(other / "input.json")
    if any(inp[k] != baseline[k] for k in ("game", "release", "positions", "archive_sha256")):
        raise ValueError("Control and treatment received different inputs")
    a, b = receipts(other, "fable"), receipts(folder, "time_components")
    report = dict(game=game, control_receipts_s=[r['elapsed_s'] for r in a],
                  treatment_receipts_s=[r['elapsed_s'] for r in b])
    if a and b:
        items = {r["position"]: r for r in read(folder / "time_items.json")}
        src = Source()
        matrix = src.get("matrix", page=1, game_limit=game)
        if not matrix or game not in matrix["game_ids"] or any(
                t["cells"][matrix["game_ids"].index(game)] is None for t in matrix["items"]):
            raise ValueError(f"Awaiting settlement for game {game}")
        field = settled_field(src, matrix, game, inp["positions"])
    for cutoff in (54, 60):
        aa, bb = ([r for r in arm if r["elapsed_s"] <= cutoff] for arm in (a, b))
        report[f"at_{cutoff}s"] = (compare(field, items, aa[-1], bb[-1]) if aa and bb else
                                   dict(status="unpaired", control_available=bool(aa), treatment_available=bool(bb)))
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
