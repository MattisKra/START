"""Score timestamped hybrid decisions against always using either limit."""
import argparse
import json
from pathlib import Path

from factor_replay import gap
from rate_check_replay import Source, settled_field
from score_shadow import follow
from claimbot_shadow.trace import write_json


def compare_limits(field, rows):
    actions = {key: {r["index"]: (r["charge_price"], r[key]) for r in rows}
               for key in ("acceptance_limit", "factor_limit", "fable_limit")}
    selected = actions["acceptance_limit"]
    if set(field) != set(selected) or len(selected) != len(rows):
        raise ValueError("Hybrid positions disagree with settled field")
    def savings(subset, baseline):
        return gap(subset, actions[baseline], selected)["reviewer_saving"]
    return dict(vs_always_factor=savings(field, "factor_limit"), vs_always_fable=savings(field, "fable_limit"),
                switched_positions=[r["index"] for r in rows if r["selected"] == "fable"],
                differing_limits=sum(r["fable_limit"] != r["factor_limit"] for r in rows),
                lines=[dict(position=r["index"], selected=r["selected"], charge=r["charge_price"],
                            fable_limit=r["fable_limit"], factor_limit=r["factor_limit"],
                            vs_always_factor=savings({r["index"]: field[r["index"]]}, "factor_limit"),
                            vs_always_fable=savings({r["index"]: field[r["index"]]}, "fable_limit"))
                       for r in rows])


def save(folder):
    game = json.loads((folder / "result.json").read_text())
    receipt = game["final"]
    if not receipt or not receipt["on_time"]:
        report = dict(status="no_on_time_receipt")
    else:
        src = Source()
        gid = game["game"]
        matrix = src.get("matrix", page=1, game_limit=gid)
        if not matrix or gid not in matrix["game_ids"]:
            raise ValueError(f"Game {gid} has not settled")
        i = matrix["game_ids"].index(gid)
        if any(t["cells"][i] is None for t in matrix["items"]):
            raise ValueError(f"Game {gid} settlements incomplete")
        field = settled_field(src, matrix, gid, [r["index"] for r in receipt["lines"]])
        report = dict(status="settled", game=gid, elapsed_s=receipt["elapsed_s"], units="EUR",
                      **compare_limits(field, receipt["lines"]))
    write_json(folder / "score.json", report)
    print(folder.name, report["status"], report.get("vs_always_factor"), report.get("vs_always_fable"), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--follow", action="store_true")
    args = parser.parse_args()
    if args.follow:
        follow(args.folder, scorer=save)
    else:
        save(args.folder)
