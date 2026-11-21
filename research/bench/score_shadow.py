"""Score completed paired shadow receipts against the same public, settled field."""
import argparse
import json
from pathlib import Path

from rate_check_replay import Source, TEAM, compare, settled_field
from claimbot_shadow.trace import write_json


def score(folder):
    result = json.loads((folder / "result.json").read_text())
    game = result["game"]
    receipts = result["final"]
    absent = [name for name in ("python", "fable") if not receipts.get(name)]
    if absent:
        return dict(status="missing_on_time_receipt", missing=absent)
    src = Source()
    matrix = src.get("matrix", page=1, game_limit=game)
    if not matrix or game not in matrix["game_ids"]:
        raise ValueError(f"Game {game} unavailable in standings")
    col = matrix["game_ids"].index(game)
    team = next(t for t in matrix["items"] if t["team_name"] == TEAM)
    if team["cells"][col] is None:
        raise ValueError(f"Game {game} awaiting settlements")
    arms = {name: {r["index"]: (r["charge_price"], r["acceptance_limit"])
                   for r in receipt["lines"]} for name, receipt in receipts.items()}
    field = settled_field(src, matrix, game, arms["python"])
    by_line = []
    for position, state in field.items():
        lo, hi, il, ih = compare({position: state}, arms["python"], arms["fable"])
        by_line.append(dict(position=position, reviewer_saving=[lo, hi],
                            issuer_change=[il, ih], net_change=[lo + il, hi + ih]))
    totals = {k: [round(sum(row[k][i] for row in by_line), 2) for i in (0, 1)]
              for k in ("reviewer_saving", "issuer_change", "net_change")}
    return dict(status="settled", game=game, official_team_net=team["cells"][col],
                fable_minus_python_eur=totals, lines=by_line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_folder", type=Path)
    folder = parser.parse_args().game_folder
    report = score(folder)
    write_json(folder / "score.json", report)
    print(report.get("fable_minus_python_eur", report))
