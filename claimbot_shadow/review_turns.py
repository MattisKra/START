"""Continue the same Fable session with bounded, single-line reviews."""
import json

from .checks import check

MAX_PASSES = 2
START_BEFORE_S = 54
INSTRUCTION = """Review position {index}, the largest remaining charge or limit (€{exposure}).
You have about {safe:.1f}s to the 54s checkpoint and {left:.1f}s to the absolute deadline.
Independently check the weakest assumption behind this amount. Read or search a relevant
case source again, inspect the image, or obtain a comparable tariff if feasible. Check
payable hours/units, duplicated work, VAT or clause scope as appropriate. Report what
specific evidence supports keeping or changing the numbers. A justified keep is valuable.
Write ONLY review.json for this follow-up, with integer pass={number}, integer index={index},
action ("keep" or "revise"), reason (a short source-grounded conclusion), and updates
(an object with only changed numeric fields: charge_price, acceptance_limit,
fair_median_gross_if_valid or p_valid; empty for keep). Your earlier complete decision
is already recorded. Keep other lines untouched and finish immediately after the receipt.
For a rejected review see decision_check.json. The same market-search privacy rules apply."""


async def send(proc, prompt):
    msg = dict(type="user", message=dict(role="user", content=prompt))
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    await proc.stdin.drain()


class ReviewTurns:
    def __init__(self, case_sources):
        self.case_sources = frozenset(case_sources)
        self.targets = []
        self.complete = False
        self.sources = {}

    def next(self, trace, elapsed):
        last = trace.last_on_time
        if not last or elapsed >= START_BEFORE_S or len(self.targets) >= MAX_PASSES:
            return None
        if self.targets and not self.complete:
            return None
        remaining = [r for r in last["lines"] if r["index"] not in self.targets]
        if not remaining:
            return None
        def exposure(row):
            return max(row["charge_price"], row["acceptance_limit"])
        row = max(remaining, key=lambda r: (exposure(r), -r["index"]))
        self.targets.append(row["index"])
        self.complete = False
        self.sources.clear()
        trace.log("review_started", number=len(self.targets), position=row["index"], exposure=exposure(row),
                  base_elapsed_s=last["elapsed_s"])
        return INSTRUCTION.format(index=row["index"], exposure=exposure(row), number=len(self.targets),
                                  safe=max(0., 54 - elapsed), left=max(0., 60 - elapsed))

    def source(self, key, turn, tool, args, failed, work):
        if not self.targets or failed:
            return
        if tool in {"Read", "Grep"}:
            path = (work / (args.get("file_path") or args.get("path") or "")).resolve()
            if path not in self.case_sources:
                return
        elif tool not in {"WebSearch", "WebFetch"}:
            return
        self.sources[key] = turn

    def prior_sources(self, turn):
        return [k for k, t in self.sources.items() if t != turn]

    def record(self, trace, patch, source_ids, write_id):
        if not self.targets or self.complete or not isinstance(patch, dict):
            raise ValueError("Expected one review per pass")
        pos = self.targets[-1]
        if (type(patch.get("pass")) is not int or patch["pass"] != len(self.targets) or
                type(patch.get("index")) is not int or patch["index"] != pos):
            raise ValueError("Review does not match assigned pass and position")
        reason, updates, action = patch.get("reason"), patch.get("updates"), patch.get("action")
        allowed = {"charge_price", "acceptance_limit", "fair_median_gross_if_valid", "p_valid"}
        if not source_ids or not isinstance(reason, str) or not reason.strip():
            raise ValueError("Review needs a completed source check and a stated reason")
        if not isinstance(updates, dict) or updates.keys() - allowed:
            raise ValueError("Only the assigned position's numeric decision fields can change")
        if action not in {"keep", "revise"} or bool(updates) != (action == "revise"):
            raise ValueError("Use keep with empty updates, or revise with changed fields")
        base = trace.last_on_time
        before = next(r for r in base["lines"] if r["index"] == pos)
        if updates and all(before[k] == v for k, v in updates.items()):
            raise ValueError("Revision contains no changed values")
        lines = [dict(r, **updates, evidence=reason) if updates and r["index"] == pos else r for r in base["lines"]]
        issues = check(lines, trace.positions)
        if issues:
            raise ValueError(" | ".join(issues))
        trace.record(lines, dict(tool_call=write_id, policy_proof=base["trigger"]["policy_proof"],
                                 review_pass=len(self.targets), position=pos, action=action, reason=reason,
                                 updates=updates, source_calls=source_ids))
        self.complete = True
