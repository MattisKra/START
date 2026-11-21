"""Compare frozen limit choices directly against the same historical opponents."""
import argparse
import json
from pathlib import Path

from factor_replay import gap
from rate_check_replay import Source, settled_field
from score_shadow import follow
from claimbot_shadow.trace import write_json

COMPARISONS = (("label_only", "factor"), ("vote_only", "factor"), ("hybrid", "factor"),
               ("label_only", "vote_only"), ("hybrid", "label_only"), ("hybrid", "vote_only"))


def compare(field, receipt):
    if not receipt:
        return dict(status="no_complete_receipt")
    rows = receipt["lines"]
    if len(rows) != len(field) or {r["index"] for r in rows} != set(field):
        raise ValueError("Receipt and settlement positions differ")
    results = {}
    for arm, base in COMPARISONS:
        actions = {name: {r["index"]: (r["charge_price"], r[name]) for r in rows} for name in (arm, base)}
        changed = [r["index"] for r in rows if r[arm] != r[base]]
        results[f"{arm}_vs_{base}"] = dict(
            reviewer_saving=gap(field, actions[base], actions[arm])["reviewer_saving"],
            changed_lines={p: gap({p: field[p]}, actions[base], actions[arm])["reviewer_saving"] for p in changed})
    eligible = [r for r in rows if r["factor"] != r["fable"]]
    return dict(status="scored", source_s=receipt["source_s"], observed_s=receipt["observed_s"],
                positions=len(rows), differing_limits=len(eligible),
                same_hybrid_label=sum(r["hybrid"] == r["label_only"] for r in eligible),
                results=results)


def save(folder):
    game = json.loads((folder / "result.json").read_text())["game"]
    events = [json.loads(s) for s in (folder / "decisions.jsonl").read_text().splitlines()]
    def last(cutoff):
        return next((e for e in reversed(events) if 0 <= e["observed_s"] <= cutoff and
                     0 <= e["source_s"] <= cutoff), None)
    final = last(60)
    if final is None:
        report = dict(status="no_complete_receipt", game=game)
    else:
        src = Source()
        matrix = src.get("matrix", page=1, game_limit=game)
        if not matrix or game not in matrix["game_ids"]:
            raise ValueError(f"Game {game} has not settled")
        i = matrix["game_ids"].index(game)
        if any(t["cells"][i] is None for t in matrix["items"]):
            raise ValueError(f"Game {game} settlements incomplete")
        field = settled_field(src, matrix, game, [r["index"] for r in final["lines"]])
        report = dict(status="settled", game=game, units="EUR", at_60s=compare(field, final),
                      at_54s=compare(field, last(54)))
    write_json(folder / "score.json", report)
    print(game, report["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--follow", action="store_true")
    args = parser.parse_args()
    if args.follow:
        follow(args.folder, scorer=save)
    else:
        save(args.folder)
