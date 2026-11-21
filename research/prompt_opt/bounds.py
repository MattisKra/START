"""Derive per-line bounds on the hidden fair value t from public transactions.

Usage: python3 -I bounds.py GAME_ID   -> prints table, writes data/bounds_game_<id>.json

Rules (payoff matrix):
  rejected & amount > 0  -> charge a = amount/1.5 was fair -> t >= a
  rejected & amount == 0 & issuer's a > 0 known -> a > t
  accepted rows reveal min(a, c); a cap (different accepted amounts for one issuer, or
  accepted < a known from a rejection) gives c < a, and c >= 4t -> t <= c/4.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"


def derive(game: int) -> dict:
    tx = json.loads((DATA / f"tx_game_{game}.json").read_text())
    by_line = defaultdict(list)
    for t in tx:
        by_line[t["line_item_index"]].append(t)
    out = {}
    for line, rows in sorted(by_line.items()):
        charges = {}  # issuer -> a
        acc_amounts = defaultdict(set)
        for r in rows:
            if not r["accepted"] and r["amount"] > 0:
                charges[r["issuer"]] = round(r["amount"] / 1.5, 2)
            if r["accepted"]:
                acc_amounts[r["issuer"]].add(round(r["amount"], 2))
        cap_hi = None
        for iss, am in acc_amounts.items():
            if iss not in charges:
                charges[iss] = max(am)  # may be capped; true a >= this
            if len(am) > 1 or (iss in charges and max(am) < charges[iss] - 0.01):
                c = max(am) if len(am) == 1 else max(am)
                cap_hi = min(cap_hi, c / 4) if cap_hi else c / 4
        lo, hi = 0.0, float("inf")
        fair, unfair = [], []
        for r in rows:
            a = charges.get(r["issuer"], 0.0)
            if not r["accepted"] and r["amount"] > 0:
                lo = max(lo, a)
                fair.append((r["issuer"], a))
            elif not r["accepted"] and r["amount"] == 0 and a > 0:
                hi = min(hi, a)
                unfair.append((r["issuer"], a))
        if cap_hi is not None:
            hi = min(hi, cap_hi)
        # reviewers' b: accepted a -> b >= a ; rejected -> b < a
        b_lo, b_hi = defaultdict(float), defaultdict(lambda: float("inf"))
        for r in rows:
            a = charges.get(r["issuer"], 0.0)
            if r["accepted"]:
                b_lo[r["reviewer"]] = max(b_lo[r["reviewer"]], a)
            else:
                b_hi[r["reviewer"]] = min(b_hi[r["reviewer"]], a)
        out[line] = {
            "t_lo": lo,
            "t_hi": hi,
            "charges": charges,
            "fair": sorted(set(fair), key=lambda x: x[1]),
            "unfair": sorted(set(unfair), key=lambda x: x[1]),
            "b_range": {k: [b_lo[k], b_hi[k]] for k in sorted(set(b_lo) | set(b_hi))},
        }
    return out


def main() -> None:
    game = int(sys.argv[1])
    out = derive(game)
    for line, d in out.items():
        print(f"line {line}: t in [{d['t_lo']:.2f}, {d['t_hi']:.2f})")
        print("   charges:", {k: v for k, v in sorted(d["charges"].items(), key=lambda x: x[1])})
        print("   fair:", d["fair"])
        print("   unfair:", d["unfair"])
    ser = {
        str(k): {**v, "t_hi": (None if v["t_hi"] == float("inf") else v["t_hi"]),
                 "b_range": {t: [a, (None if b == float("inf") else b)] for t, (a, b) in v["b_range"].items()}}
        for k, v in out.items()
    }
    (DATA / f"bounds_game_{game}.json").write_text(json.dumps(ser, indent=1))


if __name__ == "__main__":
    main()
