"""Checks for the case-memory text helpers (claimbot/memtext.py). Reads past-cases/ as text only.

    uv run python -I research/bench/test_clause_parser.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from claimbot import memtext as mt  # noqa: E402

PAST = ROOT / "past-cases"
fails = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


# 1. the wrapped cross-reference in case_001/policy.txt:761 ("2.3.3 and no other; ...") is not a heading
p1 = (PAST / "case_001" / "policy.txt").read_text()
lines = p1.splitlines()
trap = next(i for i, l in enumerate(lines) if l.strip().startswith("2.3.3 and no other"))
cl = mt.parse_clauses(p1)
ids = [c.id for c in cl]
check(ids.count("2.3.3") == 1, f"case_001: exactly one clause 2.3.3 (found {ids.count('2.3.3')}); trap at line {trap + 1}")
c233 = next(c for c in cl if c.id == "2.3.3")
check(c233.line == 115, f"case_001: 2.3.3 starts at line 115 (got {c233.line})")
check("one half of the amount otherwise payable" in " ".join(c233.text.split()), "2.3.3 contains the halving rule")
check("where nothing is established either way, no reduction is made" in mt.norm(c233.text), "2.3.3 contains 'nothing established -> no reduction'")
check("endorsement waiving the overvoltage protection requirement" in mt.norm(c233.text), "2.3.3 contains the endorsement exception")
c915 = next(c for c in cl if c.id == "9.1.5")
check("2.3.3 and no other" in c915.text, "the cross-reference stays inside 9.1.5")
check(ids == sorted(ids, key=mt._key), "case_001: clause numbers are monotone")

# 2. every past policy parses into a monotone outline with plenty of clauses
for d in sorted(PAST.glob("case_*")):
    cs = mt.parse_clauses((d / "policy.txt").read_text())
    ks = [mt._key(c.id) for c in cs]
    check(len(cs) >= 4 and ks == sorted(ks) and len(set(ks)) == len(ks), f"{d.name}: {len(cs)} clauses, monotone, unique")

# 3. clauses that differ only in an amount have different exact hashes; identical text has the same hash
a = mt.Clause("4.2.2", "Sub-limit", "4.2.2 Sub-limit\nIndemnity is limited to EUR 500 including VAT.", 1)
b = mt.Clause("4.2.2", "Sub-limit", "4.2.2 Sub-limit\nIndemnity is limited to EUR 5,000 including VAT.", 1)
c = mt.Clause("5.1.1", "Sub-limit", "5.1.1 Sub-limit\nIndemnity is   limited to EUR 500\nincluding VAT.", 9)
check(mt.exact_hash(a) != mt.exact_hash(b), "500 vs 5,000: different exact hash")
check(mt.exact_hash(a) == mt.exact_hash(c), "same wording, other number and wrapping: same exact hash")
check(mt.numbers(a.body) != mt.numbers(b.body), "numbers() tells 500 from 5,000")

# 4. same edition in two games (case_002 and case_006): all clauses match exactly
h2 = {mt.exact_hash(c) for c in mt.parse_clauses((PAST / "case_002" / "policy.txt").read_text())}
h6 = {mt.exact_hash(c) for c in mt.parse_clauses((PAST / "case_006" / "policy.txt").read_text())}
check(h2 == h6, f"case_002 and case_006 (same edition): identical clause hashes ({len(h2)})")
check(mt.edition((PAST / "case_002" / "policy.txt").read_text()) == "WD-2026 Portable Equipment, Repair and Replacement",
      "edition of case_002")

# 5. invoice lines
inv = {d.name: mt.parse_invoice_lines((d / "invoice.txt").read_text()) for d in sorted(PAST.glob("case_*"))}
check([(l["pos"], l["qty"], l["unit"]) for l in inv["case_000"]] == [(1, 2.0, "hrs"), (2, 1.0, "pcs"), (3, 0.2, "m2"), (4, 1.0, "pcs")],
      f"case_000 quantities {[(l['pos'], l['qty'], l['unit']) for l in inv['case_000']]}")
check(inv["case_000"][2]["text"].endswith("approx. 0.2 m2"), f"case_000 L3 keeps 'approx. 0.2 m2' in the text: {inv['case_000'][2]['text']!r}")
check(inv["case_003"][4]["text"] == "Repair and refinish of scratched and chipped wooden shelf" and inv["case_003"][4]["unit"] == "flat rate",
      f"case_003 L5 wrapped: {inv['case_003'][4]}")
check(len(inv["case_003"]) == 6 and inv["case_003"][5]["text"] == "Vehicle costs", "case_003 has 6 lines")
check(inv["case_005"][0]["text"].startswith("Laptop damage payment") and "lower-right-corner" in inv["case_005"][0]["text"],
      f"case_005 hyphen wrap: {inv['case_005'][0]['text']!r}")
check([l["pos"] for l in inv["case_007"]] == [1, 2], "case_007: two invoices, positions 1 and 2")
check(mt.trade_of((PAST / "case_007" / "invoice.txt").read_text()) == "Plumbing / Painting", "case_007 trades")

# 6. MinHash: a reworded clause is a candidate, an unrelated one is not
try:
    import numpy as np
    x = c233.body
    y = x.replace("Where nothing is established either way", "If nothing is established either way")
    sim = lambda u, v: float(np.mean(mt.minhash(u) == mt.minhash(v)))
    check(sim(x, y) >= 0.8, f"minhash reworded clause {sim(x, y):.2f} >= 0.8")
    check(sim(x, c915.body) < 0.3, f"minhash unrelated clause {sim(x, c915.body):.2f} < 0.3")
except ImportError:
    print("skip minhash checks (numpy not installed)")

print(f"\n{'ALL OK' if not fails else f'{len(fails)} FAILED'}")
sys.exit(1 if fails else 0)
