"""Check a Fable decision file without changing its actions."""
import math


def nonnegative(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def check(lines, positions):
    issues = []
    seen = set()
    if not isinstance(lines, list):
        return ["Expected a JSON array"]
    for row in lines:
        if not isinstance(row, dict):
            issues.append("Expected an object for each line")
            continue
        pos = row.get("index")
        if type(pos) is not int or pos not in positions or pos in seen:
            issues.append(f"Unexpected or duplicate index {pos!r}")
            continue
        seen.add(pos)
        for key in ("charge_price", "acceptance_limit", "fair_median_gross_if_valid"):
            if not nonnegative(row.get(key)):
                issues.append(f"Position {pos}: {key} requires a finite nonnegative amount")
        q = row.get("p_valid")
        if not nonnegative(q) or q > 1:
            issues.append(f"Position {pos}: p_valid must lie between 0 and 1")
        if not isinstance(row.get("evidence"), str) or not row["evidence"].strip():
            issues.append(f"Position {pos}: missing evidence")
    if missing := sorted(set(positions) - seen):
        issues.append(f"Missing positions {missing}")
    return issues
