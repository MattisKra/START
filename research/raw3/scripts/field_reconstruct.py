"""Reconstruct per-line t brackets, each issuer's a and each reviewer's b bracket from public leaderboard rows.

    python3 -I research/raw3/scripts/field_reconstruct.py LB_DIR "Our Team Name" [--detail]

LB_DIR is a scratch directory OUTSIDE the repo (filled by fetch_public_rows.py). This file contains no data.
Without --detail it prints one anonymous summary line per invoice line. --detail prints per-team rows under hashed labels
for reading on screen only: never redirect that output into the repo (team data handling rule, research/03-leaderboard-findings.md).
Row semantics: accepted -> amount = a (or min(a, c) if inflated); rejected and fair -> 1.5a; rejected and inflated -> 0.
A charge of 0 is accepted by everyone for 0; a positive inflated charge rejected by everyone is visible only as 'infl_unseen'."""
import json, sys, collections, statistics as st, hashlib, math
from pathlib import Path
lb = Path(sys.argv[1]); US = sys.argv[2]; DETAIL = "--detail" in sys.argv
games = sorted(int(p.stem.split("_")[1]) for p in lb.glob("tx_*.json"))
rows = {g: json.loads((lb / f"tx_{g}.json").read_text()) for g in games}
teams = sorted({r["issuer"] for g in games for r in rows[g]})
anon = {t: ("US" if t == US else "T" + hashlib.sha1(t.encode()).hexdigest()[:3]) for t in teams}

def load():
    """-> dict[(g, line)] = dict(a={team: (kind, value)}, t_lo, t_hi, acc={(iss,rev): bool})"""
    out = {}
    for g in games:
        for ln in sorted({r["line_item_index"] for r in rows[g]}):
            rs = [r for r in rows[g] if r["line_item_index"] == ln]
            A = {}
            for t in teams:
                mine = [r for r in rs if r["issuer"] == t]
                if not mine: continue
                pos = [r["amount"] if r["accepted"] else r["amount"] / 1.5 for r in mine if r["amount"] > 0]
                rej_pos = any((not r["accepted"]) and r["amount"] > 0 for r in mine)
                rej_zero = any((not r["accepted"]) and r["amount"] == 0 for r in mine)
                if not pos:
                    A[t] = ("zero", 0.0) if all(r["accepted"] for r in mine) else ("infl_unseen", None)
                else:
                    a = st.mode([round(x, 2) for x in pos])
                    A[t] = ("fair", a) if rej_pos else ("infl", a) if rej_zero else ("all_acc", a)
            lo = max([v for k, v in A.values() if k == "fair"], default=0.0)
            his = [v for k, v in A.values() if k == "infl"]
            hi = min(his) if his else None
            out[(g, ln)] = dict(A=A, t_lo=lo, t_hi=hi, acc={(r["issuer"], r["reviewer"]): r["accepted"] for r in rs},
                                amt={(r["issuer"], r["reviewer"]): r["amount"] for r in rs})
    return out

def b_bracket(L, rev):
    """reviewer's b in [lo, hi): lo = max known a accepted, hi = min known a rejected"""
    lo, hi = 0.0, math.inf
    for iss, (k, a) in L["A"].items():
        if iss == rev or a is None or a <= 0: continue
        if L["acc"].get((iss, rev)): lo = max(lo, a)
        else: hi = min(hi, a)
    unseen_rej = sum(1 for iss, (k, a) in L["A"].items() if k == "infl_unseen" and iss != rev)
    return lo, hi

if __name__ == "__main__":
    D = load()
    for (g, ln), L in D.items():
        kinds = collections.Counter(k for k, _ in L["A"].values())
        print(f"\n=== game {g} line {ln}: t in [{L['t_lo']:.2f}, {L['t_hi'] if L['t_hi'] is not None else 'inf'})  issuers: {dict(kinds)}")
        if DETAIL:
            ref = L["t_lo"] if L["t_lo"] > 0 else (L["t_hi"] or 1)
            for t in teams:
                if t not in L["A"]: continue
                k, a = L["A"][t]; lo, hi = b_bracket(L, t)
                nacc = sum(1 for (i, r), v in L["acc"].items() if i == t and v)
                print(f"   {anon[t]:5s} a={('%9.2f' % a) if a is not None else '   unseen'} {k:11s} a/ref={(a / ref if a else 0):5.2f} accepted_by={nacc:2d}  b in [{lo:9.2f},{hi:9.2f}) b/ref=[{lo / ref:5.2f},{(hi / ref) if hi < math.inf else float('inf'):5.2f})")
