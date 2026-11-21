"""Audit G, step 4: adversarial synthetic soundness search for research/bench/euro_replay.py (and the fixed reference g_replay_fixed.py).

    python3 -I research/raw5/scripts/g_adversarial.py [--n 20000] [--seed 1] [--minimal]

Fields with KNOWN truth (t, cap, every team's a and b) are generated with the official payoff rule, settlement rows are produced exactly like the
platform does (unrounded amounts), the field is reconstructed from the ROWS ONLY and candidate policies are replayed. The true counterfactual must lie
inside [lo, hi]. Unlike euro_replay_check.py the test is done PER LINE (a game total lets slack on one pair hide a violation on another), with harder
fields: tiny fields, cap exactly 4t / at the floor, ties everywhere, identical charges, accept-everything and silent mixtures, charges equal to t / to
limits / to the cap, excluded lines with free-option charges, nobody fair, correlated errors. Synthetic only; contains no data.
"""
import importlib.util, math, random, statistics as st, sys, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


er = _load("er", ROOT / "research/bench/euro_replay.py")
fx = _load("fx", HERE / "g_replay_fixed.py")
BIG = 1e9


def pay(a, b, t, c):
    if a <= b:
        return min(a, c)
    return 1.5 * a if a <= t else 0.0


def r2(x):
    return round(x, 2)


def gen_line(rng, n_teams, mode):
    """One line: truth t, cap c and every team's (a, b). mode picks the family of field."""
    t = 0.0 if rng.random() < mode.get("p_t0", 0.3) else r2(math.exp(rng.gauss(5.0, 1.0)))
    cap_kind = rng.choice(mode.get("cap", ["4t", "floor", "loose"]))
    floor = rng.choice([20.0, 100.0, 500.0, 5000.0])
    c = {"4t": max(4 * t, floor if t == 0 else 4 * t), "floor": max(4 * t, floor), "loose": max(4 * t * (1 + rng.random()), floor)}[cap_kind]
    c = r2(c)
    ref = t if t > 0 else r2(math.exp(rng.gauss(4.5, 1.0)))          # what a team that believes the line is valid would think it is worth
    common = math.exp(rng.gauss(0, mode.get("common_sigma", 0.0)))   # correlated error of the whole field
    grid = mode.get("grid", False)
    kinds = mode.get("kinds", ["silent", "rational", "rational", "accept_all", "strict", "overcharge", "exact_t", "capper", "tiny", "free_option", "lax_low"])
    strat = {}
    for j in range(n_teams):
        k = rng.choice(kinds)
        e = common * math.exp(rng.gauss(0, rng.choice([0.05, 0.25, 0.6])))
        if grid:                                                     # few distinct values: ties between charges, limits, t and the cap
            a = rng.choice([0.0, 0.5 * ref, 0.8 * ref, ref, ref + 0.01, 1.2 * ref, 2 * ref, 4 * ref, c, c + 1, 3 * c])
            b = rng.choice([0.0, 0.5 * ref, 0.8 * ref, ref, 1.2 * ref, 2 * ref, 4 * ref, c, BIG])
        elif k == "silent": a, b = 0.0, 0.0
        elif k == "rational": a, b = ref * 0.8 * e, ref * e
        elif k == "accept_all": a, b = ref * 0.9 * e, BIG
        elif k == "strict": a, b = ref * 0.7 * e, ref * 0.6 * e
        elif k == "overcharge": a, b = ref * 1.5 * e, ref * 1.1 * e
        elif k == "exact_t": a, b = ref, ref
        elif k == "capper": a, b = c * rng.choice([0.5, 1.0, 1.5, 10.0]), ref * e
        elif k == "tiny": a, b = 0.01, 0.0
        elif k == "free_option": a, b = ref * 3 * e, 0.0
        else: a, b = ref * 0.3 * e, ref * 5 * e                      # lax_low: cheap charge, generous limit
        strat[j] = (r2(a), r2(b))
    if mode.get("copy", 0) and n_teams > 2 and rng.random() < mode["copy"]:   # several issuers with the identical charge
        src = rng.randrange(1, n_teams)
        for j in rng.sample(range(1, n_teams), k=min(n_teams - 1, 2)):
            strat[j] = (strat[src][0], strat[j][1])
    return dict(t=t, c=c, strat=strat, ref=ref)


def rows_of(truth, base, rounded=False):
    rows = []
    for ln, T in enumerate(truth, 1):
        for i, (ai, _) in T["strat"].items():
            a_i = base[ln][0] if i == 0 else ai
            for j, (_, bj) in T["strat"].items():
                if i == j:
                    continue
                b_j = base[ln][1] if j == 0 else bj
                amt = pay(a_i, b_j, T["t"], T["c"])
                rows.append(dict(issuer=i, reviewer=j, line_item_index=ln, accepted=a_i <= b_j, amount=round(amt, 2) if rounded else amt))
    return rows


def true_parts(T, a0, b0):
    rev = sum(pay(a0, bj, T["t"], T["c"]) for j, (aj, bj) in T["strat"].items() if j != 0)
    cost = sum(pay(aj, b0, T["t"], T["c"]) for j, (aj, bj) in T["strat"].items() if j != 0)
    return rev, cost


def candidates(rng, T, base_ab, k=8):
    """Candidate (a, b) for one line: random multiples plus every critical value of the line (ties with others' charges, limits, t, the cap)."""
    ref, t, c = T["ref"], T["t"], T["c"]
    crit = {0.0, t, r2(t + 0.01), r2(max(t - 0.01, 0)), c, r2(c + 0.01), r2(c - 0.01), 4 * t, BIG, base_ab[0], base_ab[1]}
    for j, (a, b) in T["strat"].items():
        if j:
            crit |= {a, b, r2(a + 0.01), r2(max(a - 0.01, 0)), r2(b + 0.01), r2(max(b - 0.01, 0))}
    crit = sorted(crit)
    out = []
    for _ in range(k):
        if rng.random() < 0.5:
            out.append((rng.choice(crit), rng.choice(crit)))
        else:
            out.append((r2(ref * rng.choice([0, 0.5, 0.8, 0.95, 1.0, 1.1, 2.0, 5.0])), r2(ref * rng.choice([0, 0.6, 1.0, 1.25, 3.0, 20.0]))))
    return out


MODES = {
    "author-like": dict(kinds=["silent", "rational", "rational", "rational", "accept_all", "strict", "overcharge"], cap=["loose"], p_t0=0.25),
    "mixed": dict(),
    "no-silent (everyone accepts something)": dict(kinds=["rational", "accept_all", "lax_low", "accept_all", "exact_t"]),
    "accept-all heavy": dict(kinds=["accept_all", "accept_all", "accept_all", "rational", "lax_low"], cap=["4t", "floor"]),
    "silent heavy": dict(kinds=["silent", "silent", "silent", "rational", "free_option", "overcharge"]),
    "grid ties": dict(grid=True),
    "excluded lines, free options": dict(p_t0=1.0, kinds=["silent", "free_option", "free_option", "tiny", "accept_all", "rational"]),
    "cappers": dict(kinds=["capper", "capper", "accept_all", "rational", "silent"], cap=["4t", "floor"]),
    "correlated errors": dict(common_sigma=0.5, kinds=["rational", "rational", "strict", "overcharge", "silent"]),
    "identical charges": dict(copy=0.8),
}


def run(mod, n, seed, sizes=(12, 6, 4, 3, 2), with_logs=True, collect=None, rounded=False):
    """Returns per mode: counts of line-level violations of the lower / upper bound, and the worst excess in EUR."""
    res = {}
    for name, mode in MODES.items():
        rng = random.Random(seed)
        C = collections.Counter(); worst_lo = worst_hi = 0.0
        for g in range(n):
            nt = rng.choice(sizes)
            T = gen_line(rng, nt, mode)
            base_kind = rng.random()
            base = (T["strat"][0] if base_kind < 0.6 else (r2(T["ref"] * rng.choice([0, 0.5, 1, 2, 6])), r2(T["ref"] * rng.choice([0, 0.5, 1, 2, 6, BIG / max(T["ref"], 1)]))))
            rows = rows_of([T], {1: base}, rounded)
            kw = dict(our_b={1: base[1]}, our_a={1: base[0]}) if with_logs else {}
            line = mod.reconstruct(rows, 0, **kw)[1]
            for (a_c, b_c) in candidates(rng, T, base):
                lo, hi, _, _ = mod.line_value(line, 0, a_c, b_c)
                rev, cost = true_parts(T, a_c, b_c)
                tn = rev - cost
                C["cases"] += 1
                tol = 0.02 if not rounded else 0.02 * nt
                if tn < lo - tol:
                    C["lo_violated"] += 1; worst_lo = max(worst_lo, lo - tn)
                    if collect is not None:
                        collect.append(("lo", lo - tn, nt, name, T, base, (a_c, b_c), (lo, hi, tn)))
                if tn > hi + tol:
                    C["hi_violated"] += 1; worst_hi = max(worst_hi, tn - hi)
                    if collect is not None:
                        collect.append(("hi", tn - hi, nt, name, T, base, (a_c, b_c), (lo, hi, tn)))
        res[name] = (C, worst_lo, worst_hi)
    return res


def report(title, res):
    print(f"\n{title}")
    print(f"  {'field family':42s} {'cases':>7s} {'truth<lo':>9s} {'worst':>10s} {'truth>hi':>9s} {'worst':>10s}")
    tot = collections.Counter()
    for name, (C, wl, wh) in res.items():
        print(f"  {name:42s} {C['cases']:>7d} {C['lo_violated']:>9d} {wl:>10.2f} {C['hi_violated']:>9d} {wh:>10.2f}")
        tot.update(C)
    print(f"  {'ALL':42s} {tot['cases']:>7d} {tot['lo_violated']:>9d} {'':>10s} {tot['hi_violated']:>9d}   "
          f"-> lower bound wrong in {tot['lo_violated'] / tot['cases']:.2%}, upper bound wrong in {tot['hi_violated'] / tot['cases']:.2%} of line replays")


def explain(v):
    kind, excess, nt, name, T, base, cand, (lo, hi, tn) = v
    print(f"  [{kind} bound broken by {excess:.2f} EUR] family '{name}', {nt} teams: t = {T['t']}, cap = {T['c']}")
    print(f"     we (team 0) actually played a = {base[0]}, b = {base[1]};  candidate a' = {cand[0]}, b' = {cand[1]}")
    print("     others (a, b): " + ", ".join(f"T{j}({a}, {b})" for j, (a, b) in T["strat"].items() if j))
    print(f"     evaluator range [{lo:.2f}, {hi:.2f}]   TRUE counterfactual net {tn:.2f}")


def by_cause_and_size(n, seed):
    """Attribute the violations of the original: switch one fix on at a time; and split by field size."""
    print("\nATTRIBUTION (line replays with the truth outside the range, all families pooled, with our own log)")
    print(f"  {'variant':58s} {'cases':>7s} {'truth<lo':>9s} {'truth>hi':>9s}")
    for label, f1, f2 in (("original logic (no fix)", False, False), ("only FIX 1 (top accepted amount is not 'inflated')", True, False),
                          ("only FIX 2 (hidden charge ceiling = b')", False, True), ("FIX 1 + FIX 2", True, True)):
        fx.FLAGS.update(fix1=f1, fix2=f2)
        tot = collections.Counter()
        for C, _, _ in run(fx, n, seed).values():
            tot.update(C)
        print(f"  {label:58s} {tot['cases']:>7d} {tot['lo_violated']:>9d} {tot['hi_violated']:>9d}")
    fx.FLAGS.update(fix1=True, fix2=True)
    print("\nBY FIELD SIZE, original euro_replay.py (all families pooled)")
    for nt in (12, 6, 4, 3, 2):
        tot = collections.Counter(); wl = wh = 0.0
        for C, a, b in run(er, n, seed, sizes=(nt,)).values():
            tot.update(C); wl = max(wl, a); wh = max(wh, b)
        print(f"  {nt:>2d} teams: {tot['cases']} cases, truth<lo {tot['lo_violated']} ({tot['lo_violated'] / tot['cases']:.2%}, worst {wl:.0f} EUR), truth>hi {tot['hi_violated']} ({tot['hi_violated'] / tot['cases']:.2%}, worst {wh:.0f} EUR)")


def author_generator(n_games, seed=7):
    """The author's OWN generator and candidates (euro_replay_check.py), unchanged, but checked per line and per game with a 2 ct tolerance."""
    ck = _load("ck", ROOT / "research/bench/euro_replay_check.py")
    rng = random.Random(seed)
    C = collections.Counter(); worst = 0.0; worst_game = 0.0
    for g in range(n_games):
        truth = ck.make_game(rng)
        base = {ln: (math.exp(rng.gauss(5, 1)) * 0.8, math.exp(rng.gauss(5, 1))) for ln in range(1, len(truth) + 1)}
        rows = ck.rows_from(truth, base)
        lines = er.reconstruct(rows, 0, our_b={ln: b for ln, (a, b) in base.items()}, our_a={ln: a for ln, (a, b) in base.items()})
        for _ in range(6):
            cand = {}
            for ln, T in enumerate(truth, 1):
                ref = T["t"] if T["t"] > 0 else 80.0
                cand[ln] = (ref * rng.choice([0.0, 0.5, 0.8, 0.95, 1.1, 2.0]), ref * rng.choice([0.0, 0.6, 1.0, 1.25, 3.0]))
            glo = ghi = gt = 0.0
            for ln, T in enumerate(truth, 1):
                lo, hi, _, _ = er.line_value(lines[ln], 0, *cand[ln])
                tn = sum(pay(cand[ln][0], bj, T["t"], T["c"]) - pay(aj, cand[ln][1], T["t"], T["c"]) for j, (aj, bj) in T["strat"].items() if j != 0)
                C["line_cases"] += 1
                if tn < lo - 0.25:
                    C["line_lo_violated"] += 1; worst = max(worst, lo - tn)
                C["line_hi_violated"] += tn > hi + 0.25
                glo += lo; ghi += hi; gt += tn
            C["game_cases"] += 1
            if gt < glo - 1.0:
                C["game_lo_violated"] += 1; worst_game = max(worst_game, glo - gt)
            C["game_hi_violated"] += gt > ghi + 1.0
    print(f"\nAUTHOR'S OWN generator and candidates ({n_games} games x 6 candidates, 12 teams, 4 lines), ORIGINAL replay:")
    print(f"  per GAME (the published test, 1 EUR tolerance): truth below lo in {C['game_lo_violated']}/{C['game_cases']} (worst {worst_game:.2f}), above hi in {C['game_hi_violated']}")
    print(f"  per LINE (25 ct tolerance):                     truth below lo in {C['line_lo_violated']}/{C['line_cases']} (worst {worst:.2f} EUR), above hi in {C['line_hi_violated']}")


def targeted():
    """Hand-built minimal fields (anonymous, synthetic)."""
    print("\nTARGETED MINIMAL COUNTEREXAMPLES (original euro_replay.py; one line; team 0 = us)")
    cases = [
        ("A  hidden charge ceiling (FIX 2): a charge everybody rejected for 0, our candidate limit above it",
         dict(t=100.0, c=5000.0, ref=100.0, strat={0: (0.0, 0.0), 1: (900.0, 0.0), 2: (0.0, 0.0)}), (0.0, 0.0), (0.0, 1000.0)),
        ("B  fair charge that nobody rejected is the line's highest accepted amount (FIX 1): we would reject it",
         dict(t=100.0, c=400.0, ref=100.0, strat={0: (0.0, 100.0), 1: (95.0, 0.0), 2: (0.0, 1e9)}), (0.0, 100.0), (0.0, 90.0)),
        ("C  same field, our candidate CHARGE is between that amount and t (FIX 1): fair, rejected by a strict reviewer",
         dict(t=100.0, c=400.0, ref=100.0, strat={0: (0.0, 100.0), 1: (95.0, 0.0), 2: (0.0, 1e9), 3: (0.0, 96.0)}), (0.0, 100.0), (98.0, 100.0)),
        ("D  12 teams: one fair charge that all 11 reviewers accepted (every limit is above it); our candidate limit is below it",
         dict(t=100.0, c=400.0, ref=100.0, strat={0: (80.0, 120.0), **{j: (0.0, 150.0) for j in range(1, 11)}, 11: (90.0, 150.0)}), (80.0, 120.0), (85.0, 85.0)),
    ]
    for title, T, base, cand in cases:
        rows = rows_of([T], {1: base})
        line = er.reconstruct(rows, 0, our_b={1: base[1]}, our_a={1: base[0]})[1]
        lo, hi, n_, idn = er.line_value(line, 0, *cand)
        lf, hf, _, _ = fx.line_value(fx.reconstruct(rows, 0, our_b={1: base[1]}, our_a={1: base[0]})[1], 0, *cand)
        rev, cost = true_parts(T, *cand)
        print(f"  {title}")
        print(f"     t = {T['t']}, cap = {T['c']}; we played (a, b) = {base}; others (a, b): " + ", ".join(f"T{j}{ab}" for j, ab in T["strat"].items() if j))
        print(f"     candidate (a', b') = {cand}: evaluator [{lo:.2f}, {hi:.2f}], {idn}/{n_} pairs 'identified';  TRUTH {rev - cost:.2f};  fixed replay [{lf:.2f}, {hf:.2f}]")


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 4000
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    for label, mod in (("ORIGINAL euro_replay.py", er), ("FIXED g_replay_fixed.py", fx)):
        for logs in (True, False):
            coll = []
            res = run(mod, n, seed, with_logs=logs, collect=coll)
            report(f"{label}, {'with' if logs else 'WITHOUT'} our own log (our_a / our_b), unrounded amounts, {n} lines per family x 8 candidates", res)
            if "--minimal" in sys.argv and coll:
                for kind in ("lo", "hi"):
                    small = sorted([v for v in coll if v[0] == kind and v[1] > 1.0], key=lambda v: (v[2], len([1 for a, b in v[4]['strat'].values() if a > 0]), -v[1]))
                    seen = set()
                    for v in small:
                        if v[3] in seen:
                            continue
                        seen.add(v[3]); explain(v)
                        if len(seen) >= 3:
                            break
    report("FIXED, amounts rounded to cents (tolerance 2 ct per pair)", run(fx, n, seed, rounded=True))
    by_cause_and_size(n, seed)
    author_generator(2000)
    targeted()
