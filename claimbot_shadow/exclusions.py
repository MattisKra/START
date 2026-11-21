"""Audit Fable's line-level exclusions and endorsements against prior policy reads."""
import asyncio

from . import fable_arm

INSTRUCTION = """
Before your first decision, check BOTH exclusions and endorsements for every line.
Search policy.txt for the specific peril, equipment, location and work, plus exclusions,
exceptions and endorsements. Read plausible clauses in context, including cross-references.
Check the released description, schedule wording and other relevant case evidence to see
whether an endorsement was actually agreed. A standard form offering an endorsement is
not proof it was agreed. Do not infer absence from silence or invent a missing schedule.
Keep uncovered, partly covered and covered scope distinct. Never reject merely because
a clause mentions the item. If nothing relevant is found, say so without forcing a change.
Each row must add coverage_check with exclusion and endorsement objects. Each has:
status (exclusion: applies, partial, does_not_apply, none_found, uncertain;
endorsement: present, explicitly_absent, not_evidenced, none_relevant, uncertain),
clause (number or null), quote (at least six consecutive body words from that clause
read in policy.txt, or null when none is identified), and basis (a brief case fact and
document supporting the status). If a condition or endorsement restores cover, apply it.
In the normal evidence field state the resulting payable scope. Keep entries concise.
"""

STATES = {
    "exclusion": {"applies", "partial", "does_not_apply", "none_found", "uncertain"},
    "endorsement": {"present", "explicitly_absent", "not_evidenced", "none_relevant", "uncertain"},
}


def audit(rows, gate, prior):
    evidence = []
    for row in rows:
        fields = row.get("coverage_check")
        finding = {"index": row["index"]}
        for name, states in STATES.items():
            part = fields.get(name) if isinstance(fields, dict) else None
            if not isinstance(part, dict) or not isinstance(part.get("status"), str) or part["status"] not in states:
                finding[name] = {"audit": "missing_or_invalid"}
                continue
            claim = dict(index=row["index"], policy_clause=part.get("clause"), policy_quote=part.get("quote"))
            proof = gate.proof([claim], prior)
            if not isinstance(part.get("basis"), str) or not part["basis"].strip():
                status = "missing_basis"
            elif proof:
                status = "verified_policy_quote"
            elif (part.get("clause") or part.get("quote") or
                  (name == "exclusion" and part["status"] in {"applies", "partial", "does_not_apply"})):
                status = "unverified_policy_quote"
            else:
                status = "case_claim_without_policy_quote"
            finding[name] = dict(audit=status, reported_status=part["status"], proof=proof)
        evidence.append(finding)
    return evidence


def run(case, trace):
    asyncio.run(fable_arm.run_case(case, trace, require_policy=True, prompt_addition=INSTRUCTION,
                                   coverage_audit=audit))
