"""Replay through all completed games: one multiplier pair, a strict default, and a strict default with a lenient exception for
REPAIR-WORK lines (the invoice line names a repair of the damaged item, its labour, or a damage payment with a stated price).

    python3 -I research/raw4/scripts/strict_default_replay.py LB_DIR --us "Team Name"

m = the live bot's median (outputs/model_outputs.json), or our charge / 0.9 where the log is not committed (games 8-9).
REPAIR below is OUR reading of the invoice texts. It was fixed after game 9 was known: post hoc, see the report (section 2.3).
Other teams' rows are read in memory from LB_DIR (outside the repo). Prints our own replayed totals only.
"""
import importlib.util, json, sys
from pathlib import Path

here = Path(__file__).parent
spec = importlib.util.spec_from_file_location("rr", here / "replay_rules.py"); rr = importlib.util.module_from_spec(spec); spec.loader.exec_module(rr)
fr = rr.fr
ROOT = Path(__file__).resolve().parents[3]
REPAIR = {(2, 1), (2, 2), (3, 4), (3, 5), (4, 2), (4, 3), (5, 1), (6, 1)}     # every other priced line is 'other': service, cost head, replacement goods, mixed lump sum


def main():
    D = fr.load(sys.argv[1]); us = sys.argv[sys.argv.index("--us") + 1]
    outs = json.loads((ROOT / "outputs" / "model_outputs.json").read_text())["games"]
    lines = []
    for g, G in D["games"].items():
        sub = {s["index"] + 1: s for s in outs.get(str(g), {}).get("submitted", [])}
        for ln, L in G["lines"].items():
            if ln in sub:
                m, q = sub[ln]["t_median"], sub[ln]["q"]
            else:
                a = L["A"][us]["a"]
                if not a:
                    continue
                m, q = a / 0.9, (0.9 if L["B"][us]["n_acc_pos"] > 0 else 0.1)
            if q >= 2 / 3:
                lines.append((g, ln, L, m, "R" if (g, ln) in REPAIR else "X"))
    games = sorted(D["games"])
    print("priced lines:", len(lines), "repair:", sum(1 for x in lines if x[4] == "R"), "other:", sum(1 for x in lines if x[4] == "X"))
    for k in ("R", "X"):
        n = i = 0
        for g, ln, L, m, kk in lines:
            if kk != k:
                continue
            for t, A in L["A"].items():
                if A["status"] != "zero":
                    n += 1; i += A["status"] == "inflated"
        print(f"   all teams' positive charges on {k} lines: {i}/{n} = {i / n:.0%} inflated")

    def score(rule, label):
        ip = io = c = 0.0; per = {g: 0.0 for g in games}
        for g, ln, L, m, k in lines:
            ka, kb = rule[k]
            p, o, cc = rr.revenue(ka * m, L, us, "pess"), rr.revenue(ka * m, L, us, "opt"), rr.cost(kb * m, L, us)
            ip += p; io += o; c += cc; per[g] += p - cc
        print(f" {label:46s} income {ip:7.0f}..{io:7.0f}  cost {c:7.0f}  net {ip - c:7.0f}..{io - c:7.0f} | net (lower bound) per game " + " ".join(f"{per[g]:6.0f}" for g in games))

    score({"R": (0.90, 1.25), "X": (0.90, 1.25)}, "live: 0.90 / 1.25 everywhere")
    score({"R": (0.90, 0.50), "X": (0.90, 0.50)}, "strict default: 0.90 / 0.50 everywhere")
    score({"R": (0.70, 0.50), "X": (0.70, 0.50)}, "strict default: 0.70 / 0.50 everywhere")
    score({"R": (0.90, 0.00), "X": (0.90, 0.00)}, "0.90 / reject everything")
    score({"R": (0.90, 1.35), "X": (0.90, 0.50)}, "a 0.90; b: repair 1.35, other 0.50")
    score({"R": (0.90, 1.35), "X": (0.50, 0.50)}, "repair 0.90 / 1.35, other 0.50 / 0.50")
    score({"R": (0.90, 1.35), "X": (0.60, 0.40)}, "repair 0.90 / 1.35, other 0.60 / 0.40")
    score({"R": (1.00, 1.35), "X": (0.50, 0.40)}, "repair 1.00 / 1.35, other 0.50 / 0.40")


if __name__ == "__main__":
    main()
