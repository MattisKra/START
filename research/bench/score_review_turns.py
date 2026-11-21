"""Measure extra reviews against the same session's last initial-turn decision."""
import argparse
import json
from pathlib import Path

from factor_replay import gap
from rate_check_replay import Source, settled_field
from score_shadow import follow, prices
from claimbot_shadow.checks import check
from claimbot_shadow.trace import write_json


def compare_at(receipts, field, cutoff):
    eligible = [r for r in receipts if r["on_time"] and r["elapsed_s"] <= cutoff]
    baseline = [r for r in eligible if not r["trigger"].get("review_pass")]
    if not baseline:
        return dict(status="missing_initial")
    initial, final = baseline[-1], eligible[-1]
    return dict(status="paired", initial_s=initial["elapsed_s"], final_s=final["elapsed_s"],
                reviews=len(eligible) - len(baseline), **gap(field, prices(initial), prices(final)))


def audit(events, positions, final):
    decisions, attempts, results = [], [], []
    requested, successful = {}, {}
    for e in events:
        kind = e["event"]
        if kind == "tool":
            requested[e["id"]] = e
        elif kind == "tool_result" and not e["failed"]:
            successful[e["id"]] = e
        elif kind == "result":
            results.append(e)
        elif kind == "review_started":
            attempts.append(dict(number=e["number"], position=e["position"], exposure=e["exposure"],
                                 start_s=e["elapsed_s"], status="no_receipt", errors=[]))
        elif kind == "invalid_review" and attempts:
            attempts[-1]["errors"].append(dict(elapsed_s=e["elapsed_s"], error=e["error"]))
        elif kind == "decision":
            trigger = e["trigger"]
            if check(e["lines"], positions) or trigger["tool_call"] not in successful:
                raise ValueError("Invalid decision or absent successful write")
            decisions.append(e)
            if number := trigger.get("review_pass"):
                attempt = attempts[-1]
                if number != attempt["number"] or trigger["position"] != attempt["position"]:
                    raise ValueError("Receipt does not match active review")
                sources = []
                for key in trigger["source_calls"]:
                    source, done = requested[key], successful[key]
                    write = requested[trigger["tool_call"]]
                    if not attempt["start_s"] <= source["elapsed_s"] <= done["elapsed_s"] <= write["elapsed_s"]:
                        raise ValueError("Source check did not precede the review write")
                    sources.append(dict(id=key, tool=source["tool"], arguments=source["arguments"],
                                        read_s=done["elapsed_s"]))
                if not sources:
                    raise ValueError("Review lacks a source check")
                attempt.update(status=trigger["action"] if e["on_time"] else "late", receipt_s=e["elapsed_s"],
                               action=trigger["action"], updates=trigger["updates"], reason=trigger["reason"],
                               sources=sources, changes=e["changes"])
    eligible = [r for r in decisions if r["on_time"]]
    if (eligible[-1] if eligible else None) != final:
        raise ValueError("Final stored receipt disagrees with event trace")
    return decisions, attempts, results


def save(folder):
    inputs = json.loads((folder / "input.json").read_text())
    result = json.loads((folder / "result.json").read_text())
    game, positions = inputs["game"], set(inputs["positions"])
    manifest = json.loads((folder.parent / "manifest.json").read_text())
    if result["game"] != game or not any((g["id"], g["start_time"]) == (game, inputs["release"])
                                        for g in manifest["games"]):
        raise ValueError("Frozen game does not match result")
    path = folder / "review.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    receipts, attempts, results = audit(events, positions, result["final"]["review"])
    eligible = [r for r in receipts if r["on_time"]]
    field = {}
    if eligible:
        src = Source()
        matrix = src.get("matrix", page=1, game_limit=game)
        if not matrix or game not in matrix["game_ids"] or any(
                t["cells"][matrix["game_ids"].index(game)] is None for t in matrix["items"]):
            raise ValueError(f"Awaiting settlement for game {game}")
        field = settled_field(src, matrix, game, positions)
        if set(field) != positions:
            raise ValueError("Settlement and printed positions differ")
    for prev, r in zip(eligible, eligible[1:]):
        if number := r["trigger"].get("review_pass"):
            attempts[number - 1]["versus_preceding"] = gap(field, prices(prev), prices(r))
    report = dict(game=game, first_decision_s=eligible[0]["elapsed_s"] if eligible else None,
                  initial_receipts_s=[r["elapsed_s"] for r in eligible if not r["trigger"].get("review_pass")],
                  attempts=attempts, model_results=results,
                  lifecycle=[e for e in events if e["event"] in {"deadline", "arm_error", "exit"}])
    for cutoff in (54, 60):
        report[f"at_{cutoff}s"] = compare_at(receipts, field, cutoff)
    write_json(folder / "score.json", report)
    print(game, report["at_54s"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--follow", action="store_true")
    args = parser.parse_args()
    if args.follow:
        follow(args.folder, scorer=save)
    else:
        save(args.folder)
