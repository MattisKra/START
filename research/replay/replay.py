"""Score submitted A/B values against a fixed game scenario."""

import argparse
import json
import math
import sys
from pathlib import Path


def amount(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"expected a finite nonnegative number, got {value!r}")
    return value


def payout(charge, limit, fair, cap):
    if charge <= limit:
        return min(charge, cap)
    return 1.5 * charge if charge <= fair else 0


def indexed(rows, fields):
    if not isinstance(rows, list):
        raise ValueError("expected an array of line items")
    result = {}
    for row in rows:
        index = row["index"]
        if type(index) is not int or index < 1 or index in result:
            raise ValueError(f"invalid or duplicate invoice index {index!r}")
        result[index] = tuple(amount(row[field]) for field in fields)
    return result


def score(case, submission):
    lines = indexed(case["lines"], ("fair_value", "cap"))
    opponents = [indexed(rows, ("charge_price", "acceptance_limit")) for rows in case["opponents"]]
    if any(set(rows) - lines.keys() for rows in opponents):
        raise ValueError("unknown opponent line index")
    if any(cap < 4 * fair for fair, cap in lines.values()):
        raise ValueError("scenario cap must be at least four times fair_value")

    selected = indexed(submission, ("charge_price", "acceptance_limit"))
    if set(selected) - lines.keys():
        raise ValueError("unknown invoice index")

    earned = paid = 0
    for index, (fair, cap) in lines.items():
        charge, limit = selected.get(index, (0, 0))
        for rows in opponents:
            other_charge, other_limit = rows.get(index, (0, 0))
            earned += payout(charge, other_limit, fair, cap)
            paid += payout(other_charge, limit, fair, cap)
    return dict(case_id=case["case_id"], defaulted_lines=len(lines) - len(selected),
                income=round(earned, 2), costs=round(paid, 2), net=round(earned - paid, 2))


def score_suite(suite, submissions=None):
    cases = suite["cases"]
    ids = {entry["scenario"]["case_id"] for entry in cases}
    if submissions is not None and (not isinstance(submissions, dict) or set(submissions) != ids):
        raise ValueError("expected A/B arrays keyed by every case ID: " + ", ".join(sorted(ids, key=int)))
    results = []
    for entry in cases:
        case = entry["scenario"]
        values = entry["baseline"] if submissions is None else submissions[case["case_id"]]
        results.append(score(case, values))
    totals = {k: round(sum(r[k] for r in results), 2) for k in ("income", "costs", "net")}
    return dict(revision=suite["revision"], cases=results, totals=totals)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", nargs="?", type=Path)
    parser.add_argument("--values", type=Path, help="suite submissions keyed by game ID; use - for stdin")
    parser.add_argument("submission", nargs="?", type=Path, help="A/B JSON array (default: stdin)")
    args = parser.parse_args()
    try:
        if args.case is None:
            from history import SUITE
            if not SUITE.exists():
                parser.error("prepare the historical suite first: python3 research/replay/history.py")
            values = None
            if args.values is not None:
                values = json.load(sys.stdin) if str(args.values) == "-" else json.loads(args.values.read_text())
            print(json.dumps(score_suite(json.loads(SUITE.read_text()), values), indent=2))
            return
        if args.values:
            parser.error("--values is for all-case replay")
        case = json.loads(args.case.read_text())
        submission = json.loads(args.submission.read_text()) if args.submission else json.load(sys.stdin)
        print(json.dumps(score(case, submission)))
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.exit(2, f"Replay input error: {exc}\n")


if __name__ == "__main__":
    main()
