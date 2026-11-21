"""Verify that a decision cites policy text returned before the decision was proposed."""
import re
from pathlib import Path

from claimbot.memtext import norm, parse_clauses

INSTRUCTION = """
Before deciding any prices, find the controlling clause for a material line, then use Read
on policy.txt to inspect the actual wording. Wait for the result before composing decision.json.
On at least one material line include policy_clause (the numbered heading, e.g. "5.2.2")
and policy_quote (at least six consecutive words from its body that you read). In that
line's evidence say how the clause affects your decision. A search, heading, or guessed
citation alone does not pass. Keep this evidence in every revision. If a write is rejected,
read decision_check.json, correct it and write again within the same deadline.
"""


class PolicyGate:
    def __init__(self, work, policy):
        self.path = work / "policy.txt"
        self.clauses = {c.id: norm(c.body.removeprefix(c.title)) for c in parse_clauses(policy)}
        self.reads = {}

    def result(self, call_id, turn, name, args, block):
        if name != "Read" or block.get("is_error") or not args.get("file_path"):
            return
        if (self.path.parent / args["file_path"]).resolve() != self.path:
            return
        content = block.get("content", "")
        texts = [content] if isinstance(content, str) else [b.get("text", "") for b in content if b.get("type") == "text"]
        passage = "\n".join(texts)
        passage = re.sub(r"(?m)^[ \t]*\d+(?:\t|→|\s*\|)\s*", "", passage)
        self.reads[call_id] = (turn, norm(passage))

    def prior_reads(self, write_turn):
        return [key for key, (turn, _) in self.reads.items() if turn != write_turn]

    def proof(self, rows, prior):
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            clause = str(row.get("policy_clause", "")).strip()
            quote = row.get("policy_quote")
            if not isinstance(quote, str) or len(quote.split()) < 6:
                continue
            quote = norm(quote)
            if quote not in self.clauses.get(clause, ""):
                continue
            for key in prior:
                if quote in self.reads[key][1]:
                    return dict(index=row.get("index"), clause=clause, quote=quote, policy_read_id=key)
        return None
