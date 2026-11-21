"""Score completed paired shadow receipts against the same public, settled field."""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from factor_replay import replay
from rate_check_replay import Source, TEAM, compare, settled_field
from claimbot_shadow.reasons import save as save_reasons
from claimbot_shadow.trace import write_json


def prices(receipt):
    return {r["index"]: (r["charge_price"], r["acceptance_limit"]) for r in receipt["lines"]}


def revision_scores(path, field):
    previous = None
    revisions = []
    for raw in path.read_text().splitlines():
        event = json.loads(raw)
        if event["event"] != "decision" or not event["on_time"]:
            continue
        current = prices(event)
        if previous is not None:
            lo, hi, il, ih = compare(field, previous, current)
            revisions.append(dict(elapsed_s=event["elapsed_s"],
                                  trigger=event["trigger"].get("member") or event["trigger"].get("tool_call"),
                                  positions=[r["index"] for r in event["changes"]],
                                  reviewer_saving=[round(lo, 2), round(hi, 2)],
                                  issuer_change=[round(il, 2), round(ih, 2)],
                                  net_change=[round(lo + il, 2), round(hi + ih, 2)]))
        previous = current
    return revisions


def score(folder):
    result = json.loads((folder / "result.json").read_text())
    game = result["game"]
    receipts = result["final"]
    companion = folder.parent / "verified-fable" / str(game)
    extra = None
    if (companion / "result.json").exists():
        for case_folder in (companion, folder):
            if not (case_folder / "input.json").exists():
                raise ValueError("Missing case digest for companion comparison")
        same_input = [json.loads((d / "input.json").read_text())["archive_sha256"] for d in (folder, companion)]
        if same_input[0] != same_input[1]:
            raise ValueError("Companion and frozen arms received different archives")
        extra = json.loads((companion / "result.json").read_text())["final"]["fable"]
    absent = [name for name in ("python", "fable") if not receipts.get(name)]
    if not receipts.get("python") or (absent and not extra):
        return dict(status="missing_on_time_receipt", missing=absent)
    src = Source()
    matrix = src.get("matrix", page=1, game_limit=game)
    if not matrix or game not in matrix["game_ids"]:
        raise ValueError(f"Game {game} unavailable in standings")
    col = matrix["game_ids"].index(game)
    team = next(t for t in matrix["items"] if t["team_name"] == TEAM)
    if team["cells"][col] is None:
        raise ValueError(f"Game {game} awaiting settlements")
    arms = {name: prices(receipt) for name, receipt in receipts.items() if receipt}
    field = settled_field(src, matrix, game, arms["python"])
    events = map(json.loads, (folder / "python.jsonl").read_text().splitlines())
    config = next(e for e in events if e["event"] == "configured")
    factors = {}
    if companion.exists():
        factors["verified_fable"] = (replay(field, arms["python"], extra, config) if extra
                                     else {"status": "no_on_time_receipt_available"})
    if absent:
        return dict(status="missing_on_time_receipt", missing=absent, factor_replay=factors)
    factors["primary_fable"] = replay(field, arms["python"], receipts["fable"], config)
    by_line = []
    for position, state in field.items():
        lo, hi, il, ih = compare({position: state}, arms["python"], arms["fable"])
        by_line.append(dict(position=position, reviewer_saving=[lo, hi],
                            issuer_change=[il, ih], net_change=[lo + il, hi + ih]))
    totals = {k: [round(sum(row[k][i] for row in by_line), 2) for i in (0, 1)]
              for k in ("reviewer_saving", "issuer_change", "net_change")}
    return dict(status="settled", game=game, factor_replay=factors, official_team_net=team["cells"][col],
                fable_minus_python_eur=totals, lines=by_line,
                successive_revision_eur={name: revision_scores(folder / f"{name}.jsonl", field)
                                         for name in arms})


def save(folder):
    if not (folder / "decision_reasons.json").exists():
        save_reasons(folder)
    report = score(folder)
    write_json(folder / "score.json", report)
    print(folder.name, report.get("fable_minus_python_eur", report), flush=True)


def follow(run):
    games = json.loads((run / "manifest.json").read_text())["games"]
    for game in games:
        release = datetime.fromisoformat(game["start_time"]).timestamp()
        folder = run / str(game["id"])
        time.sleep(max(0, release + 62 - time.time()))
        detail = "Awaiting local result"
        while time.time() < release + 900:
            if (folder / "error.json").exists():
                detail = "Case preparation failed; see error.json"
                break
            if (folder / "result.json").exists():
                try:
                    save(folder)
                    break
                except ValueError as exc:
                    detail = str(exc)
            time.sleep(30)
        if not (folder / "score.json").exists():
            print(game["id"], detail, flush=True)
            folder.mkdir(exist_ok=True)
            write_json(folder / "score.json", dict(status="unscored", detail=detail))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--follow", action="store_true", help="Follow the frozen manifest in a run folder")
    args = parser.parse_args()
    if args.follow:
        follow(args.folder)
    else:
        save(args.folder)
