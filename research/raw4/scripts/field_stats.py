"""Aggregate, anonymous statistics of the field from public transaction rows (read in memory from LB_DIR, outside the repo).

    python3 -I research/raw4/scripts/field_stats.py LB_DIR --us "Team Name"

Prints only counts, shares and distributions (no team names, no per-team amounts) plus OUR OWN decomposition.
"""
import importlib.util, math, statistics as st, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("fr", Path(__file__).with_name("field_recon.py"))
fr = importlib.util.module_from_spec(spec); spec.loader.exec_module(fr)
INF = float("inf")


def tstar(L):
    """Point guess for t: midpoint of a two-sided bracket, else the lower bound (a LOWER bound for t), None if t looks like 0."""
    if L["t_lo"] > 0 and L["t_hi"] < INF:
        return math.sqrt(L["t_lo"] * L["t_hi"]), "tight"
    if L["t_lo"] > 0:
        return L["t_lo"], "lower"
    return None, "zero"


def main():
    D = fr.load(sys.argv[1])
    us = sys.argv[sys.argv.index("--us") + 1]
    teams = D["teams"]
    print("== per game: roles of the 12 teams")
    hist = {}
    for g, G in D["games"].items():
        valid = [ln for ln, L in G["lines"].items() if L["t_lo"] > 0]
        silent, charge0_acceptall, active, lax, strict = 0, 0, 0, 0, 0
        for t in teams:
            a_all0 = all(L["A"][t]["status"] == "zero" for L in G["lines"].values())
            rej_all = all(L["B"][t]["n_acc_pos"] == 0 for L in G["lines"].values())
            acc_all = all(L["B"][t]["n_rej"] == 0 for ln, L in G["lines"].items() if ln in valid)
            if a_all0 and rej_all:
                silent += 1; hist.setdefault(t, []).append("S")
            elif a_all0:
                charge0_acceptall += 1; hist.setdefault(t, []).append("Z")
            else:
                active += 1; hist.setdefault(t, []).append("A")
        print(f" game {g}: active {active}, silent (a=b=0) {silent}, charges 0 but accepts {charge0_acceptall}; lines {len(G['lines'])} (valid {len(valid)})")
    pats = sorted("".join(v) for v in hist.values())
    print(" participation patterns (S silent, A active, Z zero-charge/accepting), sorted, anonymous:", pats)

    print("\n== charges on lines with t > 0: a / t* (t* = bracket midpoint if two-sided, else the LOWER bound)")
    rat = {"tight": [], "lower": []}
    infl_share = []
    for g, G in D["games"].items():
        for ln, L in G["lines"].items():
            ts, kind = tstar(L)
            if ts is None:
                continue
            pos = [(v["a"], v["status"]) for v in L["A"].values() if v["status"] != "zero"]
            n_inf = sum(1 for a, s in pos if s == "inflated")
            n_unk = sum(1 for a, s in pos if a is None)
            rr = sorted(a / ts for a, s in pos if a)
            rat[kind] += rr
            infl_share.append((g, ln, kind, len(pos), n_inf, n_unk))
            q = lambda p: rr[min(int(p * len(rr)), len(rr) - 1)]
            print(f" g{g} L{ln} [{kind:5}] t*={ts:8.2f}  n_charges {len(pos):2d}  inflated {n_inf:2d} (of which a unseen {n_unk})  a/t*: min {rr[0]:.2f} q25 {q(.25):.2f} med {st.median(rr):.2f} q75 {q(.75):.2f} max {rr[-1]:.2f}")
    tot = sum(x[3] for x in infl_share); ti = sum(x[4] for x in infl_share)
    print(f" all valid lines: {ti}/{tot} = {ti / tot:.0%} of positive charges were inflated; by line share ranges from "
          f"{min(x[4] / x[3] for x in infl_share):.0%} to {max(x[4] / x[3] for x in infl_share):.0%}")
    for g in sorted(D["games"]):
        xs = [x for x in infl_share if x[0] == g]
        if xs:
            print(f"   game {g}: inflated {sum(x[4] for x in xs)}/{sum(x[3] for x in xs)}")

    print("\n== charges on lines with t = 0 or near 0 (excluded lines)")
    for g, G in D["games"].items():
        for ln, L in G["lines"].items():
            if L["t_lo"] > 0:
                continue
            pos = [v for v in L["A"].values() if v["status"] != "zero"]
            paid = sum(v["income"] for v in pos)
            nacc = sum(v["n_acc"] for v in pos)
            lax = sum(1 for t in teams if L["B"][t]["n_acc_pos"] > 0)
            hi = "inf" if L["t_hi"] == INF else f"{L['t_hi']:.2f}"
            print(f" g{g} L{ln}: t < {hi}; teams charging > 0: {len(pos)}; acceptances {nacc}; reviewers who accepted any: {lax}; total paid on the line {paid:.0f}")

    print("\n== reviewers on lines with t > 0: where is b relative to t*  (b bracket from accept/reject of known charges)")
    cnt = {"b_below_t (rejects fair)": 0, "b_about_t": 0, "b_above_t (accepts inflated)": 0, "unclear": 0}
    for g, G in D["games"].items():
        row = []
        for ln, L in G["lines"].items():
            ts, kind = tstar(L)
            if ts is None:
                continue
            c = {"below": 0, "about": 0, "above": 0, "silent": 0}
            for t in teams:
                B = L["B"][t]
                if B["b_hi"] <= ts and B["n_acc_pos"] == 0 and all(LL["A"][t]["status"] == "zero" for LL in G["lines"].values()):
                    c["silent"] += 1
                elif B["b_hi"] <= ts:
                    c["below"] += 1
                elif B["b_lo"] >= ts * (1.0 if kind == "tight" else 1.0001) and kind == "tight":
                    c["above"] += 1
                else:
                    c["about"] += 1
            row.append(f"L{ln}[{kind}] silent {c['silent']} below {c['below']} above {c['above']} straddle/unknown {c['about']}")
        print(f" game {g}: " + " | ".join(row))

    print("\n== reviewer outcomes per game over all teams (counts of reviews of positive charges)")
    for g, G in D["games"].items():
        acc_fair = acc_infl = rej_fair = rej_infl = acc_unk = 0
        cost_pen = cost_infl = 0.0
        for ln, L in G["lines"].items():
            for r in G["rows"]:
                if r["line_item_index"] != ln:
                    continue
                A = L["A"][r["issuer"]]
                if A["status"] == "zero":
                    continue
                if r["accepted"]:
                    if A["status"] == "fair": acc_fair += 1
                    elif A["status"] == "inflated": acc_infl += 1; cost_infl += r["amount"]
                    else: acc_unk += 1
                else:
                    if r["amount"] > 0: rej_fair += 1; cost_pen += r["amount"] / 3
                    else: rej_infl += 1
        n = acc_fair + acc_infl + rej_fair + rej_infl + acc_unk
        print(f" game {g}: reviews {n}: accept-fair {acc_fair}, ACCEPT-INFLATED {acc_infl} (cost {cost_infl:.0f}), REJECT-FAIR {rej_fair} (excess cost {cost_pen:.0f}), reject-inflated {rej_infl}, accepted-unknown {acc_unk}")

    print("\n== money: what the field lost to each reviewer error, and who got it (totals over teams, per game)")
    for g, G in D["games"].items():
        byteam = {t: dict(pen=0.0, infl=0.0, net=0.0) for t in teams}
        for r in G["rows"]:
            L = G["lines"][r["line_item_index"]]
            A = L["A"][r["issuer"]]
            byteam[r["issuer"]]["net"] += r["amount"]; byteam[r["reviewer"]]["net"] -= r["amount"]
            if not r["accepted"] and r["amount"] > 0:
                byteam[r["reviewer"]]["pen"] += r["amount"] / 3
            if r["accepted"] and A["status"] == "inflated":
                byteam[r["reviewer"]]["infl"] += r["amount"]
        nets = sorted(v["net"] for v in byteam.values())
        print(f" game {g}: net spread min {nets[0]:.0f} q25 {nets[2]:.0f} median {st.median(nets):.0f} q75 {nets[9]:.0f} max {nets[-1]:.0f};  "
              f"field penalty excess {sum(v['pen'] for v in byteam.values()):.0f}, paid for inflated {sum(v['infl'] for v in byteam.values()):.0f};  "
              f"US net {byteam[us]['net']:.0f} (rank {sorted((v['net'] for v in byteam.values()), reverse=True).index(byteam[us]['net']) + 1}), US penalty excess {byteam[us]['pen']:.0f}, US paid inflated {byteam[us]['infl']:.0f}")


if __name__ == "__main__":
    main()
