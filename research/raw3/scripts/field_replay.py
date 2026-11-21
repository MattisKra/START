"""Empirical best-response replay against the observed field (rows in a scratch dir). Anonymised aggregates only. No data here.
usage: python3 -I replay.py LB_DIR OUR_TEAM [tmult]   tmult = assumed t / t_lo on lines with no upper bound (default 1.0)"""
import json, sys, collections, statistics as st, math, random, importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("field", Path(__file__).with_name("field_reconstruct.py")); F = importlib.util.module_from_spec(spec)
TM = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
sys.argv = sys.argv[:3]; spec.loader.exec_module(F)
D = F.load(); US = F.US; teams = F.teams; games = F.games
random.seed(1)
valid, zero = [], []
for key, L in D.items():
    if L["t_lo"] > 0:
        L["t"] = math.sqrt(L["t_lo"] * L["t_hi"]) if L["t_hi"] else L["t_lo"] * TM
        valid.append(key)
    else:
        zero.append(key)
print("valid lines", len(valid), "zero/near-zero lines", len(zero), "| lines with two-sided bracket", sum(1 for k in valid if D[k]["t_hi"]))
# ---------------- field distribution of charges on valid lines
xs_f, xs_i, unseen, zeros_on_valid = [], [], 0, 0
for k in valid:
    L = D[k]
    for t, (kind, a) in L["A"].items():
        if t == US: continue
        if kind == "fair": xs_f.append(a / L["t"])
        elif kind == "infl": xs_i.append(a / L["t"])
        elif kind == "infl_unseen": unseen += 1
n_pos = len(xs_f) + len(xs_i) + unseen
q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))]
print(f"\nopponents' positive charges on valid lines: {n_pos}; fair {len(xs_f)} ({len(xs_f) / n_pos:.0%}), inflated seen {len(xs_i)}, inflated rejected by all {unseen}")
print("  fair charges a/t: p10 %.2f p25 %.2f median %.2f p75 %.2f p90 %.2f  mean %.2f" % (q(xs_f, .1), q(xs_f, .25), st.median(xs_f), q(xs_f, .75), q(xs_f, .9), st.mean(xs_f)))
print("  inflated (seen) a/t: min %.2f median %.2f max %.2f" % (min(xs_i), st.median(xs_i), max(xs_i)))
allx = xs_f + xs_i
print("  log-sd of all seen charges around t: %.2f ; median log(a/t) %.2f" % (st.pstdev([math.log(x) for x in allx]), st.median([math.log(x) for x in allx])))
# per-line dispersion of active charges
disp = []
for k in valid:
    v = [math.log(a) for t, (kind, a) in D[k]["A"].items() if kind in ("fair", "infl")]
    if len(v) >= 3: disp.append(st.pstdev(v))
print("  within-line log-sd of active teams' charges: median %.2f (min %.2f, max %.2f) over %d lines" % (st.median(disp), min(disp), max(disp), len(disp)))
# zero lines
pz = [sum(1 for t, (kind, a) in D[k]["A"].items() if kind != "zero" and t != US) for k in zero]
az = [sum(1 for (i, r), acc in D[k]["acc"].items() if acc and D[k]["A"][i][0] != "zero" and r != US and i != US) for k in zero]
print(f"\nzero lines: opponents charging > 0 per line: {pz}; accepted (issuer,reviewer) pairs among opponents per line: {az}")
# ---------------- acceptance of opponents (active = not silent in that game) as function of x
def silent(t, g):
    return all(D[k]["A"][t][0] == "zero" for k in D if k[0] == g) and not any(acc and D[k]["A"][i][0] != "zero" for k in D if k[0] == g for (i, r), acc in D[k]["acc"].items() if r == t)
bins = [(0, .5), (.5, .7), (.7, .85), (.85, 1.0001), (1.0001, 1.25), (1.25, 1.6), (1.6, 2.5), (2.5, 99)]
acc_b = collections.defaultdict(lambda: [0, 0])
for k in valid:
    L = D[k]; act = [t for t in teams if not silent(t, k[0])]
    for iss, (kind, a) in L["A"].items():
        if kind not in ("fair", "infl"): continue
        x = a / L["t"]
        for r in act:
            if r == iss: continue
            b = next(i for i, (lo, hi) in enumerate(bins) if lo <= x < hi)
            acc_b[b][0] += L["acc"][(iss, r)]; acc_b[b][1] += 1
print("\nP(an ACTIVE reviewer accepts a charge) by a/t on valid lines:")
for i, (lo, hi) in enumerate(bins):
    if acc_b[i][1]: print(f"   a/t in [{lo:.2f},{hi:.2f}): {acc_b[i][0] / acc_b[i][1]:.2f}  (n={acc_b[i][1]})")
nsil = st.mean(sum(silent(t, g) for t in teams) for g in games)
print("mean silent teams per game: %.1f of %d" % (nsil, len(teams)))
# ---------------- our b: regret per line (in units of t) as function of multiplier on a noisy estimate
def b_regret(L, b):
    r = 0.0
    for t, (kind, a) in L["A"].items():
        if t == US or a is None or a <= 0: continue
        if kind == "fair" and a > b: r += 0.5 * a
        if kind == "infl" and a <= b: r += a
    return r / L["t"]
print("\nOUR b = k * t_hat, t_hat = t*exp(N(bias, sigma)):  mean regret per valid line in units of t (lower is better)")
ks = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.35, 1.5, 2.0, 1e9]
print("   sigma bias | " + " ".join(f"{('acc-all' if k > 1e8 else 'k=%.2f' % k):>8s}" for k in ks))
for sig in [0.0, 0.15, 0.3, 0.5]:
    for bias in [0.0, -0.3]:
        row = []
        for k in ks:
            tot = 0.0; n = 0
            for _ in range(400 if sig else 1):
                for key in valid:
                    L = D[key]; tot += b_regret(L, L["t"] * math.exp(random.gauss(bias, sig)) * k); n += 1
            row.append(tot / n)
        print(f"   {sig:4.2f} {bias:5.2f} | " + " ".join(f"{v:8.3f}" for v in row))
print("   (b = 0 on a valid line: regret %.3f)" % st.mean(b_regret(D[k], 0) for k in valid))
# zero lines: cost of a positive b, in EUR per line
print("zero lines: mean EUR paid per line if we accepted every seen positive charge: %.0f; if b = 0: 0" % st.mean(sum(a for t, (kind, a) in D[k]["A"].items() if t != US and a) for k in zero))
# ---------------- our a: revenue per valid line in units of t, as function of multiplier
def a_rev(L, a):
    fair = a <= L["t"]; r = 0.0
    for t in teams:
        if t == US: continue
        lo, hi = F.b_bracket(L, t)
        p = 1.0 if a <= lo else 0.0 if a >= hi else 0.5
        r += a * (p + 1.5 * (1 - p)) if fair else a * p
    return r / L["t"]
print("\nOUR a = k * t_hat:  mean revenue per valid line in units of t (max possible at a=t: %.2f)" % st.mean(a_rev(D[k], D[k]["t"]) for k in valid))
ks = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.1, 1.25]
print("   sigma bias | " + " ".join(f"k={k:<5.2f}" for k in ks))
for sig in [0.0, 0.15, 0.3, 0.5]:
    for bias in [0.0, -0.3]:
        row = []
        for k in ks:
            tot = 0.0; n = 0
            for _ in range(400 if sig else 1):
                for key in valid:
                    L = D[key]; tot += a_rev(L, L["t"] * math.exp(random.gauss(bias, sig)) * k); n += 1
            row.append(tot / n)
        print(f"   {sig:4.2f} {bias:5.2f} | " + " ".join(f"{v:7.2f}" for v in row))
