"""Group-level aggregates (top two always-active teams, the other always-active teams, late joiners, us) and our own loss decomposition.

    python3 -I research/raw4/scripts/group_aggregates.py LB_DIR --us "Team Name"

Reads other teams' rows in memory from LB_DIR (outside the repo). Prints group means only, never a single other team. Contains no data.
"""
import importlib.util, math, statistics as st, sys, json
from pathlib import Path
spec = importlib.util.spec_from_file_location("fr", Path(__file__).with_name("field_recon.py"))
fr = importlib.util.module_from_spec(spec); spec.loader.exec_module(fr)
INF=float("inf")
D = fr.load(sys.argv[1]); us = sys.argv[sys.argv.index("--us") + 1]
tot = {t["team_name"]: t["total"] for t in D["matrix"]["items"]}
ng = len(D["games"])
def active_games(t):
    return sum(1 for G in D["games"].values() if not all(L["A"][t]["status"]=="zero" for L in G["lines"].values()))
always = [t for t in tot if active_games(t) == ng]
always.sort(key=lambda t: -tot[t])
print("always-active teams:", len(always), "; our position among them:", always.index(us)+1)
top2 = [t for t in always if t != us][:2]; mid = [t for t in always if t != us][2:]
def agg(ts):
    x = dict(inc=0, inc_pen=0, inc_infl=0, cost=0, cost_pen=0, cost_infl=0, at=[], b_lt_a=0, b_ge_a=0, n=0, topfair=0, nvalid=0, infl=0, fair=0)
    for g, G in D["games"].items():
        for r in G["rows"]:
            A = G["lines"][r["line_item_index"]]["A"][r["issuer"]]
            if r["issuer"] in ts:
                x["inc"] += r["amount"]
                if not r["accepted"] and r["amount"]>0: x["inc_pen"] += r["amount"]
                if r["accepted"] and A["status"]=="inflated": x["inc_infl"] += r["amount"]
            if r["reviewer"] in ts:
                x["cost"] += r["amount"]
                if not r["accepted"] and r["amount"]>0: x["cost_pen"] += r["amount"]/3
                if r["accepted"] and A["status"]=="inflated": x["cost_infl"] += r["amount"]
        for ln, L in G["lines"].items():
            if L["t_lo"] <= 0: continue
            ts_ = math.sqrt(L["t_lo"]*L["t_hi"]) if L["t_hi"]<INF else L["t_lo"]
            for t in ts:
                A, B = L["A"][t], L["B"][t]
                x["nvalid"] += 1
                if A["status"]=="fair": x["fair"] += 1
                if A["status"]=="inflated": x["infl"] += 1
                if A["a"]:
                    x["at"].append(A["a"]/ts_)
                    if A["status"]=="fair" and abs(A["a"]-L["t_lo"])<0.01: x["topfair"] += 1
                    x["n"] += 1
                    if B["b_hi"] <= A["a"]: x["b_lt_a"] += 1
                    elif B["b_lo"] >= A["a"]: x["b_ge_a"] += 1
    k = len(ts)
    return (f"n={k}: income/team/game {x['inc']/k/ng:6.0f} (penalties received {x['inc_pen']/x['inc']:.0%}, from accepted inflated {x['inc_infl']/x['inc']:.0%}); "
            f"cost/team/game {x['cost']/k/ng:6.0f} (penalty excess {x['cost_pen']/k/ng:5.0f}, paid inflated {x['cost_infl']/k/ng:5.0f}); "
            f"charges on valid lines: fair {x['fair']}/{x['nvalid']}, inflated {x['infl']}/{x['nvalid']}, highest fair charge of the line {x['topfair']}/{x['nvalid']}; median a/t* {st.median(x['at']):.2f}; "
            f"own limit certainly below own charge {x['b_lt_a']}/{x['n']}, certainly at/above {x['b_ge_a']}/{x['n']}")
print("top 2 always-active (excl. us):", agg(top2))
print("other always-active (excl. us):", agg(mid))
print("us:", agg([us]))
late = [t for t in tot if t not in always]
print("late joiners:", len(late), agg(late))
# our own decomposition through all games
inc_act = cost_act = 0; lost_infl = lost_under = 0; pen = infl = 0; avail = 0
for g, G in D["games"].items():
    for ln, L in G["lines"].items():
        A = L["A"][us]
        inc_act += A["income"]
        if L["t_lo"] > 0:
            n_rej = lambda a: sum(1 for t,B in L["B"].items() if t != us and a > B["b_lo"])  # pess: rejected unless certainly accepted
            best = sum((L["t_lo"] if L["t_lo"] <= B["b_lo"] else 1.5*L["t_lo"]) for t,B in L["B"].items() if t != us)
            avail += best
            if A["status"] == "inflated": lost_infl += best - A["income"]
            else: lost_under += best - A["income"]
        B = L["B"][us]; cost_act += B["cost"]
        for r in G["rows"]:
            if r["reviewer"] == us and r["line_item_index"] == ln:
                Ai = L["A"][r["issuer"]]
                if not r["accepted"] and r["amount"] > 0: pen += r["amount"]/3
                if r["accepted"] and Ai["status"] == "inflated": infl += r["amount"]
print(f"US through game {max(D['games'])}: income {inc_act:.0f}, cost {cost_act:.0f}; available at a = highest fair charge on valid lines {avail:.0f}; lost because our charge was inflated {lost_infl:.0f}, because we charged below {lost_under:.0f}; reviewer: paid for inflated {infl:.0f}, penalty excess {pen:.0f}")
