"""Replay candidate a- and b-rules for OUR team against the real field (opponents held fixed), and fit an interval-censored
normal model to log(t / m), m = the median our live bot had for the line.

    python3 -I research/raw4/scripts/replay_rules.py LB_DIR --us "Team Name" [--outputs outputs/model_outputs.json]

Reads other teams' rows in memory from LB_DIR (outside the repo); prints only our own numbers and field aggregates.
Revenue of a charge a against reviewer j:  a if accepted, 1.5 a if rejected and fair, 0 if rejected and inflated.
Unknowns are bounded: 'pess' = accept only if a <= b_lo_j and fair only if a <= t_lo; 'opt' = accept if a < b_hi_j, fair if a < t_hi.
"""
import importlib.util, json, math, statistics as st, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("fr", Path(__file__).with_name("field_recon.py"))
fr = importlib.util.module_from_spec(spec); spec.loader.exec_module(fr)
INF = float("inf")
ROOT = Path(__file__).resolve().parents[3]


def revenue(a, L, us, mode):
    tot = 0.0
    for t, B in L["B"].items():
        if t == us:
            continue
        acc = a <= B["b_lo"] if mode == "pess" else a < B["b_hi"]
        if B["b_hi"] == INF and mode == "opt":
            acc = a <= max(B["b_lo"] * 1.25, B["b_lo"])     # a reviewer who accepted everything seen: assume up to 1.25 x the highest accepted
        fair = a <= L["t_lo"] if mode == "pess" else a < L["t_hi"]
        if L["t_hi"] == INF and mode == "opt":
            fair = a <= L["t_lo"] * 1.25                      # no upper bound seen: assume t is at most 1.25 x the highest fair charge
        tot += a if acc else (1.5 * a if fair else 0.0)
    return tot


def cost(b, L, us):
    """What we pay as reviewer with limit b; charges whose a is unknown (rejected by all) are treated as rejected for 0."""
    tot = 0.0
    for t, A in L["A"].items():
        if t == us or A["status"] == "zero" or A["a"] is None:
            continue
        if A["a"] <= b:
            tot += A["a"]
        elif A["status"] == "fair":
            tot += 1.5 * A["a"]
    return tot


def ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def fit_censored(obs):
    """obs: list of (lo, hi) in log units, lo may be -inf, hi may be +inf. Grid MLE of (mu, sigma)."""
    best = None
    for mi in range(-100, 101):
        mu = mi / 100
        for si in range(10, 151, 2):
            s = si / 100
            ll = 0.0
            for lo, hi in obs:
                p = ncdf((hi - mu) / s) - ncdf((lo - mu) / s) if hi != lo else 0
                ll += math.log(max(p, 1e-12))
            if best is None or ll > best[0]:
                best = (ll, mu, s)
    return best


def main():
    D = fr.load(sys.argv[1])
    us = sys.argv[sys.argv.index("--us") + 1]
    outp = Path(sys.argv[sys.argv.index("--outputs") + 1]) if "--outputs" in sys.argv else ROOT / "outputs" / "model_outputs.json"
    outs = json.loads(outp.read_text())["games"]
    lines = []
    for g, G in D["games"].items():
        sub = {s["index"] + 1: s for s in outs.get(str(g), {}).get("submitted", [])}
        for ln, L in G["lines"].items():
            if ln in sub:
                lines.append((g, ln, L, sub[ln]))
    valid = [x for x in lines if x[2]["t_lo"] > 0]
    excl = [x for x in lines if x[2]["t_lo"] == 0]

    print("== our lines: m (our median), t bracket, our a and b, log(t/m) bracket")
    obs = []
    for g, ln, L, s in lines:
        m = s["t_median"]; hi = L["t_hi"]
        lo_l = math.log(L["t_lo"] / m) if L["t_lo"] > 0 and m > 0 else -INF
        hi_l = math.log(hi / m) if hi < INF and m > 0 else INF
        if L["t_lo"] > 0:
            obs.append((lo_l, hi_l))
        print(f" g{g} L{ln}: m {m:8.2f} q {s['q']:.2f}  t in [{L['t_lo']:8.2f}, {'inf' if hi == INF else f'{hi:.2f}':>8})  a {s['a']:8.2f} b {s['b']:8.2f}   log(t/m) in [{lo_l:+.2f}, {hi_l:+.2f}]")
    ll, mu, s = fit_censored(obs)
    print(f"\n== interval-censored normal fit of log(t/m) on {len(obs)} valid lines: mu {mu:+.2f}, sigma {s:.2f}  (1/3-quantile of t = {math.exp(mu - 0.4307 * s):.2f} x m; median {math.exp(mu):.2f} x m)")
    for drop in range(len(obs)):
        o2 = obs[:drop] + obs[drop + 1:]
        l2, m2, s2 = fit_censored(o2)
        print(f"    leave-one-out {drop}: mu {m2:+.2f} sigma {s2:.2f}  1/3-quantile {math.exp(m2 - 0.4307 * s2):.2f} x m")

    print("\n== a-rule replay on valid lines: a = k x m ; revenue summed over valid lines (pess / opt), per game pess")
    games = sorted({x[0] for x in valid})
    act_p = sum(revenue(s["a"], L, us, "pess") for g, ln, L, s in valid); act_o = sum(revenue(s["a"], L, us, "opt") for g, ln, L, s in valid)
    print(f"   actual a:      pess {act_p:9.0f}  opt {act_o:9.0f}")
    for k in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0):
        rp = sum(revenue(k * s["t_median"], L, us, "pess") for g, ln, L, s in valid)
        ro = sum(revenue(k * s["t_median"], L, us, "opt") for g, ln, L, s in valid)
        per = [sum(revenue(k * s["t_median"], L, us, "pess") for g, ln, L, s in valid if g == gg) for gg in games]
        print(f"   k_a {k:4.2f}:     pess {rp:9.0f}  opt {ro:9.0f}   per game pess " + " ".join(f"{x:7.0f}" for x in per))
    # oracle: best a per line given the field (pess)
    orc = 0.0
    for g, ln, L, s in valid:
        cands = sorted({L["t_lo"]} | {B["b_lo"] for B in L["B"].values() if B["b_lo"] > 0} | {v["a"] for v in L["A"].values() if v["a"]})
        orc += max(revenue(c, L, us, "pess") for c in cands)
    print(f"   oracle (best a per line among observed levels, pess): {orc:9.0f};   a = t_lo on every line: {sum(revenue(L['t_lo'], L, us, 'pess') for g, ln, L, s in valid):9.0f}")

    print("\n== b-rule replay: b = k x m on lines we thought valid (q >= 2/3), 0 otherwise ; cost summed over ALL our lines, per game")
    allg = sorted({x[0] for x in lines})
    def tot_cost(fn):
        return [sum(cost(fn(s), L, us) for g, ln, L, s in lines if g == gg) for gg in allg]
    act = tot_cost(lambda s: s["b"])
    orc = [sum(sum(A["a"] for t, A in L["A"].items() if t != us and A["status"] == "fair") for g, ln, L, s in lines if g == gg) for gg in allg]
    print(f"   oracle (accept fair only): {sum(orc):9.0f}   per game " + " ".join(f"{x:7.0f}" for x in orc))
    print(f"   actual b:                  {sum(act):9.0f}   per game " + " ".join(f"{x:7.0f}" for x in act))
    for k in (0.0, 0.5, 0.67, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0, 99):
        c = tot_cost(lambda s, k=k: k * s["t_median"] if s["q"] >= 2 / 3 else 0.0)
        print(f"   k_b {k:5.2f}:                {sum(c):9.0f}   per game " + " ".join(f"{x:7.0f}" for x in c) + f"   regret {sum(c) - sum(orc):8.0f}")

    print("\n== free option on lines WE judged excluded (q < 0.5): what our positive charge earned")
    for g, ln, L, s in lines:
        if s["q"] < 0.5:
            A = L["A"][us]
            print(f"   g{g} L{ln}: our a {s['a']:.2f} -> accepted by {A['n_acc']}/{A['n']}, income {A['income']:.2f}; line t_lo {L['t_lo']:.2f}")


if __name__ == "__main__":
    main()
