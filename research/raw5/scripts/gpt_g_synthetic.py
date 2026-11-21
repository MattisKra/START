"""Independent rule simulator, targeted regressions and ranking diagnostics."""

from collections import Counter, defaultdict
from itertools import combinations
import math
import random
from statistics import correlation, median

from gpt_g_support import er, patched_module


def settlement(a, b, t, c):
    if a <= b:
        return min(a, c)
    if a <= t:
        return 3 * a / 2
    return 0


def rows_from(field, quantize=None):
    rows = []
    for ln, (t, c, teams, _) in enumerate(field, 1):
        for i, (a, _) in enumerate(teams):
            for j, (_, b) in enumerate(teams):
                if i != j:
                    y = settlement(a, b, t, c)
                    rows.append(dict(issuer=i, reviewer=j, line_item_index=ln,
                                     accepted=a <= b, amount=y if quantize is None else round(y, quantize)))
    return rows


def truth(field, policy):
    return sum(settlement(a, bj, t, c) - settlement(aj, b, t, c)
               for ln, (t, c, teams, _) in enumerate(field, 1)
               for a, b in [policy.get(ln, (0, 0))] for aj, bj in teams[1:])


def reconstruction(module, field, quantize=None):
    rows = rows_from(field, quantize)
    a = {ln: teams[0][0] for ln, (_, _, teams, _) in enumerate(field, 1)}
    b = {ln: teams[0][1] for ln, (_, _, teams, _) in enumerate(field, 1)}
    return module.reconstruct(rows, 0, b, a)


def targeted(modules):
    cases = [
        ("max-all-accepted, incoming fair", (10, 100, [(0, 10), (10, 0)], 10), (0, 0), None),
        ("max-all-accepted, outgoing fair", (10, 100, [(1, 10), (10, 0)], 10), (10, 10), None),
        ("hidden and floor", (0, 500, [(0, 0), (500, 0)], 100), (0, 500), None),
        ("hidden and small limit", (0, 500, [(0, 0), (500, 0)], 100), (0, 1), None),
        ("cap ties and identical x", (10, 40, [(0, 80), (40, 0), (75, 100)], 10), (40, 40), None),
        ("exact settlement, sub-cent inputs", (100, 400, [(0, 0), (99.996, 0)], 100),
         (0, 99.997), None),
        ("rounded settlement, sub-cent inputs", (100, 400, [(0, 0), (99.996, 0)], 100),
         (0, 99.99), 2),
        ("zero displayed from accepted micropayment", (0, 100, [(0, 1), (.004, 0)], 1),
         (0, 1), 2),
        ("omitted fair line", (10, 100, [(0, 0), (10, 0)], 10), None, None),
    ]
    for label, state, modification, precision in cases:
        field = [state]
        candidate = {} if modification is None else {1: modification}
        print(label, "true", round(truth(field, candidate), 6),
              [(round(lo, 6), round(hi, 6)) for m in modules
               for lo, hi, _ in [m.game_value(reconstruction(m, field, precision), 0, candidate)]])


KINDS = ("correlated", "ties", "all_inflated", "zero_floor", "silent_mix", "boundary")
MULTIPLIERS = ((.9, 1.25), (.8, 1), (.8, .8), (.7, .9), (.9, .7), (1, 1), (.6, .6))


def generate(rng, kind):
    n = rng.choice((2, 3, 4, 12, 12, 12))
    field = []
    shared_error = rng.choice((.45, .65, .9, 1.1, 1.4, 2, 3))
    for _ in range(rng.choice((1, 1, 2, 4, 7))):
        t = rng.choice((0, 10, 25, 100, 400))
        if kind == "zero_floor":
            t = 0
        elif kind == "all_inflated" and t == 0:
            t = 25
        ref = t or rng.choice((10, 50, 150))
        c = max(4 * t, rng.choice((25, 100, 500)))
        if kind == "boundary" and t:
            c = max(4 * t, 25)
        elif rng.random() < .25:
            c *= rng.choice((2, 4, 10))
        typical = round(ref * shared_error)
        estimate = round(ref * shared_error * rng.choice((.7, .85, 1, 1.15, 1.3)))
        teams = []
        for _ in range(n):
            if kind == "ties":
                levels = (0, t, t, t + 1, typical, c, c + 1)
                a, b = rng.choice(levels), rng.choice(levels)
            elif kind == "all_inflated":
                a = t + rng.choice((1, 1, 5, t, 2*t, 10*t))
                b = rng.choice((0, t, t + 1, a, c * 2, c * 10))
            elif kind == "zero_floor":
                a = rng.choice((0, 1, ref, c - 1, c, c + 1, c * 2, c * 4))
                b = rng.choice((0, 0, 1, ref, c, c * 4))
            elif kind == "silent_mix":
                a, b = rng.choice(((0, 0), (0, 0), (0, 0), (t, c * 10),
                                   (typical, c * 10), (c + 1, 0), (t, t)))
            elif kind == "boundary":
                a = rng.choice((0, max(0, t - 1), t, t + 1, c, c + 1))
                b = rng.choice((0, max(0, t - 1), t, t + 1, c, c + 1))
            else:
                a = round(typical * rng.choice((.65, .8, 1, 1, 1.2, 2)))
                b = round(typical * rng.choice((.5, .8, 1, 1, 1.25, 2)))
            teams.append((a, b))
        field.append((t, c, teams, estimate))
    return field


def policies(rng, field):
    for a_mult, b_mult in MULTIPLIERS:
        yield {ln: (round(est * a_mult), round(est * b_mult))
               for ln, (_, _, _, est) in enumerate(field, 1)}
    for _ in range(7):
        yield {ln: (rng.choice((0, t, t + 1, c, *[b for _, b in teams])),
                    rng.choice((0, 0, t, c, c * 5, *[a for a, _ in teams])))
               for ln, (t, c, teams, _) in enumerate(field, 1)}


def ranks(values):
    out = [0.0] * len(values)
    groups = defaultdict(list)
    for i, value in enumerate(values):
        groups[value].append(i)
    rank = 0
    for value in sorted(groups):
        inds = groups[value]
        for i in inds:
            out[i] = rank + (len(inds) + 1) / 2
        rank += len(inds)
    return out


def compare(s, scored, true):
    lo, hi = zip(*scored)
    for field, values in (("lo", lo), ("midpoint", [(l + h) / 2 for l, h in scored])):
        if len(set(values)) > 1 and len(set(true)) > 1:
            s[field].append(correlation(ranks(values), ranks(true)))
    s["width"].extend(h - l for l, h in scored)
    for i, j in combinations(range(len(true)), 2):
        if true[i] == true[j]:
            continue
        better, worse = (i, j) if true[i] > true[j] else (j, i)
        gap = true[better] - true[worse]
        s["gap"].append(gap)
        s["ratio"].append(((hi[i] - lo[i]) + (hi[j] - lo[j])) / (2 * gap))
        s["sure"].append(lo[better] > hi[worse])
        s["bad_sure"].append(lo[worse] > hi[better])
    for i in range(1, len(true)):
        if true[i] > true[0]:
            s["base_better"].append(lo[i] > hi[0])
            s["exact_base_better"].append(lo[i] > true[0])
        if true[i] < true[0]:
            s["base_worse"].append(hi[i] < lo[0])
            s["exact_base_worse"].append(hi[i] < true[0])


def simulate(modules, n=3000, seed=290137):
    rng = random.Random(seed)
    coverage = defaultdict(Counter)
    ranking = defaultdict(lambda: defaultdict(list))
    worst = defaultdict(float)
    for i in range(n):
        kind = KINDS[i % len(KINDS)]
        field = generate(rng, kind)
        candidates = list(policies(rng, field))
        exact = [truth(field, policy) for policy in candidates]
        for name, module in zip(("original", "core"), modules):
            lines = reconstruction(module, field)
            scored = [module.game_value(lines, 0, policy)[:2] for policy in candidates]
            compare(ranking[name], scored[:len(MULTIPLIERS)], exact[:len(MULTIPLIERS)])
            for j, ((lo, hi), target) in enumerate(zip(scored, exact)):
                for key in ((name, kind), (name, "all"), (name, "sensible" if j < len(MULTIPLIERS) else "stress")):
                    coverage[key].update(n=1, below=target < lo - .01, above=target > hi + .01,
                                         inverted=lo > hi, miss=(target < lo - .01 or target > hi + .01))
                    worst[key] = max(worst[key], lo - target, target - hi, 0)
    for k, values in coverage.items():
        print("coverage", k, dict(values), "max miss", worst[k])
    for name, stats in ranking.items():
        for key, values in stats.items():
            n_true = f" successes {sum(values)}" if key in {
                "sure", "bad_sure", "base_better", "exact_base_better", "base_worse", "exact_base_worse"
            } else ""
            print("ranking", name, key, "n", len(values), "median", round(median(values), 4),
                  "mean", round(sum(values) / len(values), 6), n_true)


if __name__ == "__main__":
    replay_versions = (er, patched_module())
    targeted(replay_versions)
    simulate(replay_versions)
