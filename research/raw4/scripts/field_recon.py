"""Reconstruct every team's charge a and acceptance-limit bracket for b per line from public transaction rows (in memory).

    python3 -I research/raw4/scripts/field_recon.py LB_DIR [--us "Team Name"] [--detail]

LB_DIR is the scratch directory written by fetch_field.py (outside the repo). This file contains no data.
Row semantics: amount = what the reviewer paid the issuer. accepted -> a (or min(a, c) if inflated); rejected & fair -> 1.5 a; rejected & inflated -> 0.
Importable: load(lb_dir) -> dict with per-game reconstruction.
"""
import collections, json, statistics as st, sys
from pathlib import Path

INF = float("inf")


def load(lb_dir):
    lb = Path(lb_dir)
    games = sorted(int(p.stem.split("_g")[1]) for p in lb.glob("tx_g*.json"))
    matrix = json.loads((lb / "matrix.json").read_text())
    teams = [t["team_name"] for t in matrix["items"]]
    out = {"teams": teams, "games": {}, "matrix": matrix}
    for g in games:
        rows = json.loads((lb / f"tx_g{g}.json").read_text())
        lines = sorted({r["line_item_index"] for r in rows})
        G = {"rows": rows, "lines": {}}
        for ln in lines:
            rl = [r for r in rows if r["line_item_index"] == ln]
            by_iss = collections.defaultdict(list)
            for r in rl:
                by_iss[r["issuer"]].append(r)
            A = {}       # issuer -> dict(a, status)
            for iss, rs in by_iss.items():
                vals = [(r["amount"] if r["accepted"] else r["amount"] / 1.5) for r in rs if r["amount"] > 0]
                rej_fair = any((not r["accepted"]) and r["amount"] > 0 for r in rs)
                rej_infl = any((not r["accepted"]) and r["amount"] == 0 for r in rs)
                acc_pos = any(r["accepted"] and r["amount"] > 0 for r in rs)
                acc_zero = any(r["accepted"] and r["amount"] == 0 for r in rs)
                a = round(st.mode([round(v, 2) for v in vals]), 2) if vals else None
                if rej_fair:
                    status = "fair"
                elif rej_infl:
                    status = "inflated"
                elif acc_pos:
                    status = "all_accepted"       # fair or inflated: unknown from rows
                else:
                    status = "zero"; a = 0.0
                if status == "inflated" and a is None:
                    a = None                         # rejected by everyone for 0: a unknown, but a > t
                A[iss] = dict(a=a, status=status, n_acc=sum(r["accepted"] for r in rs), n=len(rs), acc_zero=acc_zero,
                              income=sum(r["amount"] for r in rs))
            fair = [v["a"] for v in A.values() if v["status"] == "fair"]
            infl = [v["a"] for v in A.values() if v["status"] == "inflated" and v["a"] is not None]
            t_lo, t_hi = max(fair, default=0.0), min(infl, default=INF)
            # reviewer brackets for b: b >= max accepted a ; b < min rejected a (when that issuer's a is known)
            B = {}
            for rev in out["teams"]:
                rs = [r for r in rl if r["reviewer"] == rev]
                acc = [A[r["issuer"]]["a"] for r in rs if r["accepted"] and A[r["issuer"]]["a"]]
                rej = [A[r["issuer"]]["a"] for r in rs if not r["accepted"] and A[r["issuer"]]["a"]]
                n_rej_unknown = sum(1 for r in rs if not r["accepted"] and not A[r["issuer"]]["a"])
                B[rev] = dict(b_lo=max(acc, default=0.0), b_hi=min(rej, default=INF), n_acc_pos=len(acc), n_rej=len(rej) + n_rej_unknown,
                              n_in_pos=sum(1 for r in rs if A[r["issuer"]]["status"] != "zero"),
                              cost=sum(r["amount"] for r in rs),
                              pen=sum(r["amount"] for r in rs if not r["accepted"] and r["amount"] > 0),
                              n_pen=sum(1 for r in rs if not r["accepted"] and r["amount"] > 0))
            G["lines"][ln] = dict(A=A, B=B, t_lo=t_lo, t_hi=t_hi)
        out["games"][g] = G
    return out


def main():
    lb_dir = sys.argv[1]
    us = sys.argv[sys.argv.index("--us") + 1] if "--us" in sys.argv else None
    D = load(lb_dir)
    tot = {t["team_name"]: t["total"] for t in D["matrix"]["items"]}
    order = sorted(tot, key=lambda t: -tot[t])
    tag = {t: ("US" if t == us else f"T{i + 1:02d}") for i, t in enumerate(order)}   # rank label, terminal only
    print("teams by total (terminal only):", ", ".join(f"{tag[t]}={tot[t]:.0f}" for t in order))
    for g, G in D["games"].items():
        print(f"\n=== game {g}")
        for ln, L in G["lines"].items():
            hi = "inf" if L["t_hi"] == INF else f"{L['t_hi']:.2f}"
            print(f" line {ln}: t in [{L['t_lo']:.2f}, {hi})")
            for t in order:
                A, B = L["A"][t], L["B"][t]
                a = "?" if A["a"] is None else f"{A['a']:.2f}"
                bh = "inf" if B["b_hi"] == INF else f"{B['b_hi']:.2f}"
                print(f"   {tag[t]:>3} a={a:>9} {A['status']:<12} acc {A['n_acc']:>2}/{A['n']:<2} inc {A['income']:>9.2f} | b in [{B['b_lo']:>8.2f},{bh:>9}) accpos {B['n_acc_pos']:>2} rej {B['n_rej']:>2} pen {B['n_pen']} cost {B['cost']:>9.2f}")


if __name__ == "__main__":
    main()
