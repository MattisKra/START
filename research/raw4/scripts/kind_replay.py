"""Replay: one multiplier pair for all lines versus multipliers by LINE KIND (work on the damaged object vs ancillary service).

    python3 -I research/raw4/scripts/kind_replay.py LB_DIR --us "Team Name"

Line kinds below are OUR reading of the invoice texts (assigned after the outcomes were known: post hoc, see the report).
m = the live bot's median for the line (outputs/model_outputs.json; game 8: our charge / 0.9 because the log was not committed yet).
Other teams' rows are read in memory from LB_DIR (outside the repo). Prints our own replayed totals only.
"""
import importlib.util, json, sys
from pathlib import Path

here = Path(__file__).parent
spec = importlib.util.spec_from_file_location("rr", here / "replay_rules.py"); rr = importlib.util.module_from_spec(spec); spec.loader.exec_module(rr)
fr = rr.fr
ROOT = Path(__file__).resolve().parents[3]
# (game, line) -> kind.  O = work on the damaged object (repair / replacement and its labour), S = ancillary service
# (attendance, call-out, diagnostics, vehicle, recovery, disposal), M = mixed lump sum.
KIND = {(1, 1): "O", (2, 1): "O", (2, 2): "O", (2, 4): "S", (3, 4): "O", (3, 5): "O", (3, 6): "S", (4, 1): "S", (4, 2): "O", (4, 3): "O",
        (5, 1): "O", (6, 1): "O", (7, 1): "M", (8, 1): "S", (8, 2): "S", (8, 3): "S", (8, 4): "S"}


def main():
    D = fr.load(sys.argv[1]); us = sys.argv[sys.argv.index("--us") + 1]
    outs = json.loads((ROOT / "outputs" / "model_outputs.json").read_text())["games"]
    lines = []
    for g, G in D["games"].items():
        sub = {s["index"] + 1: s for s in outs.get(str(g), {}).get("submitted", [])}
        for ln, L in G["lines"].items():
            if (g, ln) not in KIND:
                continue
            if ln in sub:
                m = sub[ln]["t_median"]
            else:
                a = L["A"][us]["a"]
                if not a:
                    continue
                m = a / 0.9
            lines.append((g, ln, L, m, KIND[(g, ln)]))
    print("lines used:", [(g, ln, k, round(m)) for g, ln, L, m, k in lines])
    print("\nlog-ratio t/m by kind (bracket):")
    import math
    for g, ln, L, m, k in lines:
        lo = f"{L['t_lo'] / m:.2f}" if L["t_lo"] > 0 else "0"
        hi = f"{L['t_hi'] / m:.2f}" if L["t_hi"] < rr.INF else "inf"
        print(f"   g{g} L{ln} kind {k}: t/m in [{lo}, {hi})")

    def score(rule, label, mixed_as):
        inc_p = inc_o = cst = 0.0; per = {}
        for g, ln, L, m, k in lines:
            kk = mixed_as if k == "M" else k
            ka, kb = rule[kk]
            ip, io, c = rr.revenue(ka * m, L, us, "pess"), rr.revenue(ka * m, L, us, "opt"), rr.cost(kb * m, L, us)
            inc_p += ip; inc_o += io; cst += c
            per[g] = per.get(g, 0.0) + ip - c
        print(f" {label:44s} mixed as {mixed_as}: income pess {inc_p:8.0f} opt {inc_o:8.0f}  cost {cst:8.0f}  net pess {inc_p - cst:8.0f} opt {inc_o - cst:8.0f} | per game pess " + " ".join(f"g{g}:{v:6.0f}" for g, v in sorted(per.items())))

    print("\nrules (KA, KB) applied to the live median m; cost counts only lines listed above")
    for mixed_as in ("S", "O"):
        score({"O": (0.75, 0.80), "S": (0.75, 0.80)}, "one pair 0.75 / 0.80 (old argmax, 1/3-quantile)", mixed_as)
        score({"O": (0.90, 1.25), "S": (0.90, 1.25)}, "one pair 0.90 / 1.25 (live now)", mixed_as)
        score({"O": (1.00, 1.00), "S": (1.00, 1.00)}, "one pair 1.00 / 1.00", mixed_as)
        score({"O": (1.00, 1.25), "S": (0.50, 0.55)}, "by kind: O 1.00/1.25, S 0.50/0.55", mixed_as)
        score({"O": (1.10, 1.50), "S": (0.45, 0.50)}, "by kind: O 1.10/1.50, S 0.45/0.50", mixed_as)
        score({"O": (1.00, 1.25), "S": (0.60, 0.70)}, "by kind: O 1.00/1.25, S 0.60/0.70 (half-way)", mixed_as)
        score({"O": (0.90, 1.25), "S": (0.90, 0.00)}, "a 0.90 all; b: O 1.25, S reject all", mixed_as)
        print()


if __name__ == "__main__":
    main()
