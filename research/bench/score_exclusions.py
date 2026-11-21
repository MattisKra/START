"""Score the incremental exclusion/endorsement check against policy-first Fable."""
import argparse
from pathlib import Path

from factor_replay import gap
from rate_check_replay import Source, settled_field
from score_shadow import follow, prices
from score_time_components import read, receipts
from claimbot_shadow.trace import write_json


def comparison(field, control, treatment):
    old, new = prices(control), prices(treatment)
    if set(old) != set(field) or set(new) != set(field):
        raise ValueError("Receipt and settlement positions differ")
    baseline = {r["index"]: r for r in control["lines"]}
    audits = {r["index"]: r for r in treatment["trigger"]["coverage_audit"]}
    if set(audits) != set(field):
        raise ValueError("Audit and settlement positions differ")
    lines = []
    for r in treatment["lines"]:
        p = r["index"]
        c = baseline[p]
        lines.append(dict(position=p, control_actions=old[p], treatment_actions=new[p],
                          control_p_valid=c.get("p_valid"), treatment_p_valid=r.get("p_valid"),
                          control_median=c.get("fair_median_gross_if_valid"),
                          treatment_median=r.get("fair_median_gross_if_valid"),
                          control_evidence=c.get("evidence"), treatment_evidence=r.get("evidence"),
                          coverage_check=r.get("coverage_check"), audit=audits[p],
                          **gap({p: field[p]}, old, new)))
    return dict(status="paired", control_s=control["elapsed_s"], treatment_s=treatment["elapsed_s"],
                lines=lines, **gap(field, old, new))


def save(folder):
    inputs = read(folder / "input.json")
    game = inputs["game"]
    manifest = read(folder.parent / "manifest.json")
    if (read(folder / "result.json")["game"] != game or
        not any((g["id"], g["start_time"]) == (game, inputs["release"]) for g in manifest["games"])):
        raise ValueError("Frozen game and inputs differ")
    arms = {name: receipts(folder, name) for name in ("policy_first", "exclusions")}
    a, b = arms.values()
    report = dict(game=game, receipt_times={n: [e["elapsed_s"] for e in es] for n, es in arms.items()})
    if a and b:
        source = Source()
        matrix = source.get("matrix", page=1, game_limit=game)
        if not matrix or game not in matrix["game_ids"] or any(
                t["cells"][matrix["game_ids"].index(game)] is None for t in matrix["items"]):
            raise ValueError(f"Awaiting settlement for game {game}")
        field = settled_field(source, matrix, game, inputs["positions"])
    for label, cutoff, idx in (("first", 60, 0), ("at_54s", 54, -1), ("at_60s", 60, -1)):
        aa, bb = ([e for e in arm if e["elapsed_s"] <= cutoff] for arm in (a, b))
        report[label] = (comparison(field, aa[idx], bb[idx]) if aa and bb else
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
