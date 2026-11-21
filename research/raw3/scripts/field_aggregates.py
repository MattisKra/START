"""Aggregate, anonymised field statistics from public rows held in a scratch dir. No data in this file.
usage: python3 -I agg.py LB_DIR OUR_TEAM"""
import json, sys, collections, statistics as st, math, importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("field", Path(__file__).with_name("field_reconstruct.py")); F = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2]]; spec.loader.exec_module(F)
D = F.load(); US = F.US; teams = F.teams; games = F.games
# ---- per-team per-game components
comp = collections.defaultdict(lambda: collections.Counter())
cnt = collections.defaultdict(lambda: collections.Counter())
for (g, ln), L in D.items():
    lo, hi = L["t_lo"], L["t_hi"]
    for (iss, rev), acc in L["acc"].items():
        amt = L["amt"][(iss, rev)]
        k, a = L["A"][iss]
        if k == "zero": continue
        if acc:
            if k == "fair": kind = "fair_acc"
            elif k in ("infl",): kind = "infl_acc"
            else: kind = "unk_acc"       # accepted by everyone: fair or inflated unknown
        else:
            kind = "fair_rej" if amt > 0 else "infl_rej"
        comp[(iss, g)]["inc_" + kind] += amt; comp[(rev, g)]["cost_" + kind] += amt
        cnt[(iss, g)]["n_inc_" + kind] += 1; cnt[(rev, g)]["n_cost_" + kind] += 1
net = {t: {g: sum(v for k, v in comp[(t, g)].items() if k.startswith("inc_")) - sum(v for k, v in comp[(t, g)].items() if k.startswith("cost_")) for g in games} for t in teams}
tot = {t: sum(net[t].values()) for t in teams}
order = sorted(teams, key=lambda t: -tot[t])
# silent per game: zero charge on all lines and rejects every positive charge
def silent(t, g):
    lines = [L for (gg, ln), L in D.items() if gg == g]
    return all(L["A"][t][0] == "zero" for L in lines) and cnt[(t, g)]["n_cost_fair_acc"] + cnt[(t, g)]["n_cost_infl_acc"] + cnt[(t, g)]["n_cost_unk_acc"] == 0
sil = {g: [t for t in teams if silent(t, g)] for g in games}
print("teams", len(teams), "games", games)
print("silent teams per game:", {g: len(v) for g, v in sil.items()}, "| always silent:", len(set.intersection(*map(set, sil.values()))), "| ever silent:", len(set.union(*map(set, sil.values()))))
print("our rank:", order.index(US) + 1, "of", len(teams), " our total %.0f" % tot[US], " per game", {g: round(net[US][g]) for g in games})
tv = [tot[t] for t in order]
print("field totals: max %.0f  3rd %.0f  median %.0f  min %.0f" % (tv[0], tv[2], st.median(tv), tv[-1]))
print("rank of us by game:", {g: sorted(teams, key=lambda t: -net[t][g]).index(US) + 1 for g in games})
# ---- groups
alw = set.intersection(*map(set, sil.values()))
active = [t for t in order if t not in alw]
top = active[:3]; mid = [t for t in active[3:]]
def grp(name, ts):
    c = collections.Counter(); n = collections.Counter()
    for t in ts:
        for g in games:
            c.update(comp[(t, g)]); n.update(cnt[(t, g)])
    k = max(len(ts), 1)
    inc = sum(v for kk, v in c.items() if kk.startswith("inc_")); cost = sum(v for kk, v in c.items() if kk.startswith("cost_"))
    print(f"\n[{name}] n={len(ts)}  mean net {((inc - cost) / k):.0f}  mean income {inc / k:.0f}  mean cost {cost / k:.0f}")
    for kk in ["inc_fair_acc", "inc_fair_rej", "inc_infl_acc", "inc_unk_acc", "cost_fair_acc", "cost_fair_rej", "cost_infl_acc", "cost_unk_acc"]:
        print(f"    {kk:15s} mean EUR {c[kk] / k:9.0f}   mean count {n['n_' + kk] / k:6.1f}")
    print(f"    charges rejected as inflated (count/team) {n['n_inc_infl_rej'] / k:.1f}; rightly rejected incoming {n['n_cost_infl_rej'] / k:.1f}")
    # excess cost definitions
    pen_excess = c["cost_fair_rej"] / 3; fraud_paid = c["cost_infl_acc"]
    print(f"    reviewer errors per team: penalty excess (0.5a on wrongly rejected fair) {pen_excess / k:.0f}; paid for inflated {fraud_paid / k:.0f}")
grp("top 3 active", top); grp("other active", mid); grp("US", [US]); grp("always silent", list(alw))
