"""Audit G, step 4b: can the replay RANK policies?  Synthetic tournaments with known truth (no data in this file).

    python3 -I research/raw5/scripts/g_discrimination.py [--n 300] [--seed 3] [--replay PATH_TO_euro_replay.py]

A tournament = 8 games (1-7 lines, 12 teams: ~30 % silent, the rest price with a reader that shares a common error with ours, own multipliers, and
sometimes misjudges validity; ~35 % of the lines are excluded, t = 0). We 'actually' played KA 0.9 / KB 1.25 on the live reader answer; the candidates
are the 25 multiplier pairs KA x KB on ANOTHER saved draw of the same reader (exactly the situation of euro_eval.py). For every candidate we know the true
counterfactual net and compute the replay range from the settlement rows only. Reported: does lo / midpoint / hi rank the candidates like the truth,
how often is a truly better candidate 'surely better', and how wide is the range compared with the true differences between candidates.
The numbers depend on this generator (stated in the report); they are an order of magnitude, not a calibration of the real field.
"""
import importlib.util, math, random, statistics as st, sys, collections, itertools
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


sys.path.insert(0, str(HERE))
import g_common                                                   # noqa: E402
er, ER_LABEL = g_common.replay_under_test()
fx = g_common.fixed_reference()
KA = (0.6, 0.7, 0.8, 0.9, 1.0); KB = (0.6, 0.8, 0.9, 1.0, 1.25)
CANDS = [(ka, kb) for ka in KA for kb in KB]
BASE = (0.9, 1.25)


def pay(a, b, t, c):
    if a <= b:
        return min(a, c)
    return 1.5 * a if a <= t else 0.0


def r2(x):
    return round(x, 2)


def tournament(rng, n_games=8, n_teams=12, reader_sd=0.3, common_sd=0.35, p_excl=0.35, p_silent=0.3, p_valid_ok=0.85):
    games = []
    for g in range(n_games):
        n_lines = rng.choice([1, 1, 2, 2, 3, 4, 6, 7])
        team = {}
        for j in range(1, n_teams):
            team[j] = dict(silent=rng.random() < p_silent, ka=rng.uniform(0.6, 1.4), kb=rng.uniform(0.7, 1.6), sd=rng.choice([0.15, 0.3, 0.5]), free=rng.random() < 0.5)
        lines = []
        for ln in range(1, n_lines + 1):
            valid = rng.random() > p_excl
            ref = math.exp(rng.gauss(5.5, 1.2))
            t = r2(ref) if valid else 0.0
            c = r2(max(4 * t, 200.0) * (1 + 0.5 * rng.random()))
            common = rng.gauss(0, common_sd)
            strat = {}
            for j, T in team.items():
                if T["silent"]:
                    strat[j] = (0.0, 0.0); continue
                m = ref * math.exp(common + rng.gauss(0, T["sd"]))
                bel = valid if rng.random() < p_valid_ok else (not valid)
                strat[j] = (r2(T["ka"] * m) if (bel or T["free"]) else 0.0, r2(T["kb"] * m) if bel else 0.0)
            m0 = ref * math.exp(common + rng.gauss(0, reader_sd))
            bel0 = valid if rng.random() < p_valid_ok else (not valid)
            mb = ref * math.exp(common + rng.gauss(0, reader_sd))          # what the LIVE bot read at the time: another draw of the same reader
            belb = valid if rng.random() < p_valid_ok else (not valid)
            lines.append(dict(ln=ln, t=t, c=c, strat=strat, m0=m0, bel0=bel0, mb=mb, belb=belb))
        games.append(lines)
    return games


def policy(lines, ka, kb, live=False):
    m, bel = ("mb", "belb") if live else ("m0", "bel0")
    return {L["ln"]: (r2(ka * L[m]), r2(kb * L[m]) if L[bel] else 0.0) for L in lines}


def rows_of(lines, pol):
    rows = []
    for L in lines:
        S = dict(L["strat"]); S[0] = pol[L["ln"]]
        for i, (ai, _) in S.items():
            for j, (_, bj) in S.items():
                if i != j:
                    rows.append(dict(issuer=i, reviewer=j, line_item_index=L["ln"], accepted=ai <= bj, amount=pay(ai, bj, L["t"], L["c"])))
    return rows


def truth(lines, pol):
    tot = 0.0
    for L in lines:
        a0, b0 = pol[L["ln"]]
        for j, (aj, bj) in L["strat"].items():
            tot += pay(a0, bj, L["t"], L["c"]) - pay(aj, b0, L["t"], L["c"])
    return tot


def ranks(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y); mx, my = st.mean(rx), st.mean(ry)
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx)); sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy) if sx and sy else float("nan")


def main(n, seed, mod, label, **kw):
    rng = random.Random(seed)
    rho = collections.defaultdict(list); C = collections.Counter(); regret = collections.defaultdict(list); rel_w = []; widths = []; spread = []
    for _ in range(n):
        T = tournament(rng, **kw)
        tr = [0.0] * len(CANDS); lo = [0.0] * len(CANDS); hi = [0.0] * len(CANDS); act = 0.0
        for lines in T:
            base = policy(lines, *BASE, live=True)
            rows = rows_of(lines, base)
            rec = mod.reconstruct(rows, 0, our_b={l: b for l, (a, b) in base.items()}, our_a={l: a for l, (a, b) in base.items()})
            act += truth(lines, base)
            for k, (ka, kb) in enumerate(CANDS):
                p = policy(lines, ka, kb)
                l, h, _ = mod.game_value(rec, 0, p)
                tr[k] += truth(lines, p); lo[k] += l; hi[k] += h
        mid = [(a + b) / 2 for a, b in zip(lo, hi)]
        for name, s in (("lo", lo), ("mid", mid), ("hi", hi)):
            rho[name].append(spearman(s, tr))
            pick = max(range(len(CANDS)), key=lambda k: s[k])
            C[f"top1_{name}"] += tr[pick] == max(tr)
            regret[name].append(max(tr) - tr[pick])
        regret["random"].append(max(tr) - st.mean(tr))
        C["tournaments"] += 1
        # soundness and power against the known actual
        for k in range(len(CANDS)):
            C["cands"] += 1
            C["truth_outside"] += not (lo[k] - 0.5 <= tr[k] <= hi[k] + 0.5)
            better = tr[k] > act + 1; worse = tr[k] < act - 1
            C["truly_better_than_actual"] += better; C["truly_worse_than_actual"] += worse
            C["surely_better & truly better"] += better and lo[k] > act
            C["surely_better & truly WORSE"] += worse and lo[k] > act
            C["surely_worse & truly worse"] += worse and hi[k] < act
            C["surely_worse & truly BETTER"] += better and hi[k] < act
            widths.append(hi[k] - lo[k])
        # candidate versus candidate
        for i, j in itertools.permutations(range(len(CANDS)), 2):
            if tr[i] > tr[j] + 1:
                C["pairs_truly_ordered"] += 1; C["pairs_separated (lo_i > hi_j)"] += lo[i] > hi[j]
                C["pairs_lo_orders_correctly"] += lo[i] > lo[j]; C["pairs_mid_orders_correctly"] += mid[i] > mid[j]
            elif tr[i] < tr[j] - 1:
                C["pairs_WRONGLY_separated"] += lo[i] > hi[j]
        srt = sorted(tr)
        spread.append(srt[-1] - srt[0]); gap = st.median([b - a for a, b in zip(srt, srt[1:])])
        rel_w.append(st.median([h - l for l, h in zip(lo, hi)]) / max(srt[-1] - srt[0], 1e-9))
    print(f"\n{label}: {C['tournaments']} tournaments x {len(CANDS)} candidates")
    print(f"  truth outside the tournament range: {C['truth_outside']}/{C['cands']}")
    for name in ("lo", "mid", "hi"):
        v = [x for x in rho[name] if x == x]
        print(f"  ranking by {name:3s}: Spearman with the truth median {st.median(v):+.2f} (10 % quantile {sorted(v)[len(v) // 10]:+.2f}, share negative {sum(x < 0 for x in v) / len(v):.0%}); "
              f"picks the truly best candidate in {C['top1_' + name] / C['tournaments']:.0%}; regret of its pick median {st.median(regret[name]):.0f} EUR, mean {st.mean(regret[name]):.0f} EUR")
    print(f"  (a random pick among the 25 has mean regret {st.mean(regret['random']):.0f} EUR; true best minus true worst candidate: median {st.median(spread):.0f} EUR)")
    tb, tw = C["truly_better_than_actual"], C["truly_worse_than_actual"]
    print(f"  versus the known ACTUAL: truly better {tb}, of which 'surely better' (lo > actual) {C['surely_better & truly better']} = power {C['surely_better & truly better'] / max(tb, 1):.0%}; "
          f"truly worse {tw}, of which 'surely worse' {C['surely_worse & truly worse']} = {C['surely_worse & truly worse'] / max(tw, 1):.0%}; "
          f"FALSE certain claims {C['surely_better & truly WORSE'] + C['surely_worse & truly BETTER']}")
    po = C["pairs_truly_ordered"]
    print(f"  candidate versus candidate: {po} truly ordered pairs, separated by the ranges (lo_i > hi_j) in {C['pairs_separated (lo_i > hi_j)'] / po:.1%}; wrongly separated {C['pairs_WRONGLY_separated']}; "
          f"lo orders the pair correctly in {C['pairs_lo_orders_correctly'] / po:.0%}, the midpoint in {C['pairs_mid_orders_correctly'] / po:.0%} (coin = 50 %)")
    print(f"  range width of a candidate over the tournament: median {st.median(widths):.0f} EUR = {st.median(rel_w):.1f} x the true spread between the best and the worst candidate")


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 300
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 3
    main(n, seed, er, f"UNDER TEST: {ER_LABEL}, default field")
    main(n, seed, fx, "REFERENCE g_replay_fixed.py, default field")
    main(n, seed, fx, "REFERENCE, no silent teams and nobody misjudges validity (best case for identification)", p_silent=0.0, p_valid_ok=1.0)
    main(n, seed, fx, "REFERENCE, half the field silent", p_silent=0.5)
    main(n, seed, fx, "REFERENCE, our reader much noisier (sd 0.6)", reader_sd=0.6)
