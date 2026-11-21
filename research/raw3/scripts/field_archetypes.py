"""Anonymous archetype statistics for the active field + replay of our own losses. Rows live in a scratch dir. No data here.
usage: python3 -I arch.py LB_DIR OUR_TEAM"""
import sys, collections, statistics as st, math, importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("field", Path(__file__).with_name("field_reconstruct.py")); F = importlib.util.module_from_spec(spec)
sys.argv = sys.argv[:3]; spec.loader.exec_module(F)
D = F.load(); US = F.US; teams = F.teams; games = F.games
for k, L in D.items():
    L["t"] = (math.sqrt(L["t_lo"] * L["t_hi"]) if L["t_hi"] else L["t_lo"]) if L["t_lo"] > 0 else 0.0
valid = [k for k in D if D[k]["t"] > 0]; zero = [k for k in D if D[k]["t"] == 0]
def silent(t, g):
    return all(D[k]["A"][t][0] == "zero" for k in D if k[0] == g) and not any(acc and D[k]["A"][i][0] != "zero" for k in D if k[0] == g for (i, r), acc in D[k]["acc"].items() if r == t)
active = {g: [t for t in teams if not silent(t, g)] for g in games}
opp = [t for t in teams if t != US and any(t in active[g] for g in games)]
print("active teams per game:", {g: len(v) for g, v in active.items()}, "| opponents ever active:", len(opp))
# ---- own b relative to own a (same line), valid lines
ratio = collections.defaultdict(list)
for k in valid:
    L = D[k]
    for t in active[k[0]]:
        kind, a = L["A"][t]
        if not a: continue
        lo, hi = F.b_bracket(L, t)
        ratio[t].append((lo / a, hi / a))
def cls(v):
    below = sum(1 for lo, hi in v if hi <= 1.0); above = sum(1 for lo, hi in v if lo >= 1.0); n = len(v)
    return "b<a mostly" if below > n / 2 else "b>=a mostly" if above > n / 2 else "mixed/unclear"
c = collections.Counter(cls(v) for t, v in ratio.items() if t != US and len(v) >= 3)
print("active opponents by relation of own acceptance limit to own charge on valid lines:", dict(c), "| us:", cls(ratio[US]))
# ---- b relative to t on valid lines, per reviewer-line (active only)
pos = collections.Counter()
for k in valid:
    L = D[k]
    for t in active[k[0]]:
        if t == US: continue
        lo, hi = F.b_bracket(L, t)
        if hi <= 0.5 * L["t"]: pos["b < 0.5t (incl. b = 0 on a valid line)"] += 1
        elif hi <= L["t"] * 1.0001: pos["0.5t <= b < t (too strict)"] += 1
        elif lo >= 1.5 * L["t"]: pos["b >= 1.5t (lax)"] += 1
        elif lo >= L["t"] * 0.9999 and hi <= 1.5 * L["t"]: pos["t <= b < 1.5t"] += 1
        else: pos["bracket straddles t"] += 1
n = sum(pos.values()); print("active opponents' acceptance limit vs t on valid lines (reviewer-lines, n=%d):" % n, {k: f"{v / n:.0%}" for k, v in pos.items()})
# ---- zero lines: who sets b = 0, who charges
zc = collections.Counter(); chg = collections.Counter()
for k in zero:
    L = D[k]
    for t in active[k[0]]:
        if t == US: continue
        lo, hi = F.b_bracket(L, t)
        acc_pos = any(acc and D[k]["A"][i][0] != "zero" for (i, r), acc in L["acc"].items() if r == t)
        zc["accepted some positive charge" if acc_pos else "rejected every positive charge"] += 1
        chg["charged > 0" if L["A"][t][0] != "zero" else "charged 0"] += 1
print("zero lines, active opponents as reviewers:", dict(zc), "| as issuers:", dict(chg))
# ---- charges vs t by game (learning?)
print("\nby game: active opponents' positive charges on valid lines -> share fair, median a/t of the fair ones; reviewer error rates")
for g in games:
    fair, infl, xs = 0, 0, []
    wr = fr = wa = ia = 0
    for k in valid:
        if k[0] != g: continue
        L = D[k]
        for t in active[g]:
            if t == US: continue
            kind, a = L["A"][t]
            if kind == "fair": fair += 1; xs.append(a / L["t"])
            elif kind in ("infl", "infl_unseen"): infl += 1
        for (i, r), acc in L["acc"].items():
            if r == US or r not in active[g] or i == r: continue
            kind = L["A"][i][0]
            if kind == "fair": fr += 1; wr += (not acc)
            elif kind == "infl": ia += 1; wa += acc
    if fair + infl:
        print(f"  game {g}: charges {fair + infl}, fair {fair / (fair + infl):.0%}, median fair a/t {st.median(xs) if xs else float('nan'):.2f} | fair charges wrongly rejected {wr}/{fr} = {wr / max(fr, 1):.0%}; seen inflated charges accepted {wa}/{ia}")
# ---- identical submissions (same value by two teams)
dup = 0; tot = 0
for k, L in D.items():
    vals = collections.Counter(round(a, 2) for t, (kind, a) in L["A"].items() if a)
    tot += sum(vals.values()); dup += sum(v for v in vals.values() if v > 1)
print(f"\nidentical positive charges shared by two or more teams on the same line: {dup} of {tot} charges")
# ---- issuer efficiency & reviewer regret per active team, anonymous distribution
def a_rev(L, a, me):
    fair = a <= L["t"]; r = 0.0
    for t in teams:
        if t == me: continue
        acc = None
        lo, hi = F.b_bracket(L, t)
        p = 1.0 if a <= lo else 0.0 if a >= hi else 0.5
        r += a * (p + 1.5 * (1 - p)) if fair else a * p
    return r
eff, reg = {}, {}
for t in set(opp) | {US}:
    got = pot = 0.0; pen = fraud = 0.0
    for k in valid:
        L = D[k]
        if t not in active[k[0]]: continue
        got += sum(L["amt"][(i, r)] for (i, r) in L["amt"] if i == t)
        pot += a_rev(L, L["t"], t)
    for k, L in D.items():
        if t not in active[k[0]]: continue
        for (i, r), acc in L["acc"].items():
            if r != t: continue
            kind = L["A"][i][0]
            if kind == "fair" and not acc: pen += L["amt"][(i, r)] / 3
            if kind == "infl" and acc: fraud += L["amt"][(i, r)]
    eff[t] = got / pot if pot else 0; reg[t] = (pen, fraud)
ev = sorted(eff[t] for t in opp)
print("issuer efficiency on valid lines (income / income at a = t, others fixed), active opponents: min %.2f median %.2f max %.2f | us %.2f" % (ev[0], st.median(ev), ev[-1], eff[US]))
rv = sorted(sum(reg[t]) for t in opp)
print("reviewer regret EUR over all games (penalty excess + paid for seen inflated), active opponents: min %.0f median %.0f max %.0f | us %.0f (penalty excess %.0f, inflated paid %.0f)" % (rv[0], st.median(rv), rv[-1], sum(reg[US]), *reg[US]))
# correlation of rank with efficiency vs regret (Spearman, tiny n)
import itertools
net = collections.Counter()
for k, L in D.items():
    for (i, r), amt in L["amt"].items(): net[i] += amt; net[r] -= amt
ts = [t for t in set(opp) | {US}]
def rank(v): s = sorted(v); return [s.index(x) for x in v]
def spear(x, y):
    rx, ry = rank(x), rank(y); n = len(x); return 1 - 6 * sum((a - b) ** 2 for a, b in zip(rx, ry)) / (n * (n * n - 1))
print("Spearman (n=%d active teams): net vs issuer efficiency %.2f ; net vs reviewer regret %.2f" % (len(ts), spear([net[t] for t in ts], [eff[t] for t in ts]), spear([net[t] for t in ts], [sum(reg[t]) for t in ts])))
# ---- our own replay
print("\nOUR replay by line (others fixed):")
tot = collections.Counter()
for k in sorted(D):
    L = D[k]; kind, a = L["A"][US]
    got = sum(L["amt"][(i, r)] for (i, r) in L["amt"] if i == US)
    pen = sum(L["amt"][(i, r)] / 3 for (i, r), acc in L["acc"].items() if r == US and L["A"][i][0] == "fair" and not acc)
    fraud = sum(L["amt"][(i, r)] for (i, r), acc in L["acc"].items() if r == US and acc and (L["A"][i][0] == "infl" or (L["t"] == 0 and L["A"][i][0] != "zero")))
    if L["t"] > 0:
        pot = a_rev(L, L["t"], US); p90 = a_rev(L, 0.9 * L["t"], US)
        tag = "INFLATED" if kind in ("infl", "infl_unseen") else "fair, a/t=%.2f" % (a / L["t"])
        print(f"  game {k[0]} line {k[1]}: t~{L['t']:.0f}{'' if L['t_hi'] else '+'}  our a {tag:16s} income {got:7.0f}  at a=t {pot:7.0f}  at a=0.9t {p90:7.0f} | b: penalty excess {pen:6.0f}, inflated paid {fraud:6.0f}")
        tot["a_gap_infl" if kind in ("infl", "infl_unseen") else "a_gap_under"] += pot - got; tot["income_valid"] += got; tot["pot"] += pot; tot["p90"] += p90
    else:
        print(f"  game {k[0]} line {k[1]}: t~0 (bracket < {L['t_hi']})  our a {'>0' if kind != 'zero' else '0'}: free-option income {got:6.0f} | b: inflated paid {fraud:6.0f}")
        tot["free_option"] += got
    tot["pen"] += pen; tot["fraud"] += fraud
print("  totals:", {k: round(v) for k, v in tot.items()})
