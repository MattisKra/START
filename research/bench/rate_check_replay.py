"""Replay saved original, revised and selective reader arms against completed public settlements."""
import argparse
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "research/live")]
from claimbot.pricing import _belief
from claimbot.schema import CaseEstimate
from lb_analyze import Source
from policy_family_replay import TEAM, reconstruct, savings
from g_replay_fixed import line_parts

ARMS = ("original", "revised", "selective")


def decisions(path):
    data = json.loads(path.read_text())
    result = {}
    for line in CaseEstimate.model_validate(data["estimate"]).lines:
        q, _, _, median = _belief(line)
        result[line.index + 1] = (round(.90 * median, 2), round(.55 * median, 2) if 1 - q < 1 / 3 else 0.)
    return result


def settled_field(src, matrix, game, positions):
    teams = {t["team_name"] for t in matrix["items"]}
    if len(teams) != matrix["total"]:
        raise ValueError("Incomplete tournament roster")
    rows = {}
    for team in sorted(teams):
        page = 1
        while True:
            data = src.get("transactions", game_id=game, team=team, page=page, page_size=500)
            if not data:
                raise ValueError(f"Missing settlements for game {game}, page {page}")
            for row in data["items"]:
                key = (row["line_item_index"], row["issuer"], row["reviewer"])
                if rows.setdefault(key, row) != row:
                    raise ValueError(f"Conflicting settlements in game {game}")
            if page >= data["total_pages"]:
                break
            page += 1
    if set(rows) != {(p, i, j) for p in positions for i, j in itertools.permutations(teams, 2)}:
        raise ValueError(f"Game {game} field and decision positions disagree")
    column = matrix["game_ids"].index(game)
    for t in matrix["items"]:
        name = t["team_name"]
        net = sum(r["amount"] * ((r["issuer"] == name) - (r["reviewer"] == name)) for r in rows.values())
        if abs(net - t["cells"][column]) > .011:
            raise ValueError(f"Game {game} conflicts with standings")
    return reconstruct(rows.values(), TEAM)


def compare(field, control, candidate):
    cost_lo = cost_hi = income_lo = income_hi = 0.
    if set(control) != set(candidate):
        raise ValueError("Candidate and control positions differ")
    for pos, state in field.items():
        old_a, old_b = control[pos]
        a, b = candidate[pos]
        lower, upper = savings(state, min(b, old_b), max(b, old_b))
        if b < old_b:
            lower, upper = -upper, -lower
        cost_lo += lower
        cost_hi += upper
        if a != old_a:
            new_lo, new_hi, *_ = line_parts(state, TEAM, a, 0.)
            old_lo, old_hi, *_ = line_parts(state, TEAM, old_a, 0.)
            income_lo += new_lo - old_hi
            income_hi += new_hi - old_lo
    return cost_lo, cost_hi, income_lo, income_hi


def main(games):
    src = Source()
    matrix = src.get("matrix", page=1, game_limit=max(games))
    for game in games:
        folder = ROOT / "runs/bench" / f"rate-check-game{game}"
        available = {arm: decisions(folder / f"final-{arm}.json") for arm in ARMS
                     if (folder / f"final-{arm}.json").is_file()}
        missing = [arm for arm in ARMS if arm not in available]
        if missing:
            print(f"{game}: incomplete three-reader comparison, missing {', '.join(missing)}", flush=True)
        if "original" not in available:
            continue
        original = available.pop("original")
        receipts = folder / "direct-fable-receipts.json"
        if receipts.exists():
            direct = {p: (0., 0.) for p in original}
            events = json.loads(receipts.read_text())
            for event in events:
                if event["on_time"]:
                    direct.update({r["index"]: (r["charge_price"], r["acceptance_limit"]) for r in event["values"]})
            available["direct-fable"] = direct
        if not available:
            continue
        field = settled_field(src, matrix, game, original)
        for arm, candidate in available.items():
            lo, hi, rev_lo, rev_hi = compare(field, original, candidate)
            print(f"{game} {arm}: reviewer savings [{lo:.2f}, {hi:.2f}], "
                  f"issuer change [{rev_lo:.2f}, {rev_hi:.2f}], "
                  f"net change [{lo + rev_lo:.2f}, {hi + rev_hi:.2f}] EUR", flush=True)
            if arm == "direct-fable":
                parts = [line_parts(st, TEAM, *candidate[p]) for p, st in field.items()]
                rl, rh, cl, ch, *_ = map(sum, zip(*parts))
                print(f"{game} direct-fable net [{rl - ch:.2f}, {rh - cl:.2f}] EUR", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("games", type=int, nargs="+")
    main(parser.parse_args().games)
