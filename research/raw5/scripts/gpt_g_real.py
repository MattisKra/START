"""Audit the supplied public snapshot in memory. Prints aggregates only."""

import argparse
from collections import Counter, defaultdict
from decimal import Decimal as D
from itertools import permutations
import json
from pathlib import Path
from statistics import median

from gpt_g_support import ROOT, US, er, patched_module

CENT = D("0.01")
TOL = D("0.000000001")  # allows serialization noise, stricter than a fraction of a cent
RATIO = D("1.5")


def load(path):
    return json.loads(path.read_text(), parse_float=D)


def group(rows, key):
    result = defaultdict(list)
    for row in rows:
        result[row[key]].append(row)
    return result


def amt(row):
    return D(row["amount"])


def penalty_charge(row):
    return (amt(row) / RATIO).quantize(CENT)


def net_by_team(rows):
    net = defaultdict(D)
    for r in rows:
        net[r["issuer"]] += amt(r)
        net[r["reviewer"]] -= amt(r)
    return net


def feasible(issuers, reviewers, policy, max_x, fixed_cap):
    """Check feasibility by expressing strict inequalities on a cent grid.

    For exact cent-grid charges observed through cent/mil settlements, the
    witness uses a_i on the cent grid. t can sit between cent values.
    Infinite latent charges and an unknown positive cap floor need no estimate.
    """
    # Work in cents. For a_i < a_j the smallest increment is one cent.
    # Replace t by floor(t) in cents: fair/inflated status stays equivalent.
    threshold = object()
    lower = {threshold: 0}
    upper = {threshold: int(max_x * 25)} if fixed_cap else {}
    edges = []

    def bound(i, lo, hi=None):
        lower[i] = max(lower.get(i, 0), lo)
        if hi is not None:
            upper[i] = min(upper.get(i, hi), hi)

    for i, rs in issuers.items():
        bound(i, 0)
        for r in rs:
            x = r["amount"]
            if r["accepted"]:
                p = int(x * 100)
                bound(i, p, None if fixed_cap and x == max_x else p)
            elif x > 0:
                p = int(penalty_charge(r) * 100)
                bound(i, p, p)
                edges.append((i, threshold, 0))
            else:
                bound(i, 1)
                edges.append((threshold, i, 1))
    for rs in reviewers.values():
        yes = [r["issuer"] for r in rs if r["accepted"]]
        no = [r["issuer"] for r in rs if not r["accepted"]]
        edges.extend((i, k, 1) for i in yes for k in no)
    if policy is not None:
        a, b = (int(v * 100) for v in policy)
        bound(US, a, a)
        for r in reviewers[US]:
            bound(r["issuer"], 0, b) if r["accepted"] else bound(r["issuer"], b + 1)
    # Relax lower bounds. A cycle with a strict edge keeps increasing them.
    for _ in range(len(lower)):
        changed = False
        for src, dst, step in edges:
            target = lower[src] + step
            if target > lower[dst]:
                lower[dst] = target
                changed = True
        if not changed:
            return all(lower[i] <= limit for i, limit in upper.items())
    return False


def inspect_line(rows, roster, our, stats):
    keys = [(r["issuer"], r["reviewer"]) for r in rows]
    expected = set(permutations(roster, 2))
    stats.update(lines=1, rows=len(rows), duplicate=len(keys) - len(set(keys)),
                 missing=len(expected - set(keys)), extra=len(set(keys) - expected))
    issuers, reviewers = group(rows, "issuer"), group(rows, "reviewer")
    stats.update(issuer_groups=len(issuers), reviewer_groups=len(reviewers))
    known = {}
    max_x = max((amt(r) for r in rows if r["accepted"]), default=D(0))
    max_pen = max((penalty_charge(r) for r in rows if not r["accepted"] and amt(r) > 0),
                  default=D(0))
    cap_lo = max(max_x, 4 * max_pen)
    if our is not None:
        our_a, our_b = our
    for i, rs in issuers.items():
        acc = [amt(r) for r in rs if r["accepted"]]
        pos = [amt(r) for r in rs if not r["accepted"] and amt(r) > 0]
        zero = [amt(r) for r in rs if not r["accepted"] and amt(r) == 0]
        stats.update(acc_groups=bool(acc), pos_rej_groups=bool(pos),
                     acc_disagreement=len(set(acc)) > 1,
                     penalty_disagreement=len(set(pos)) > 1,
                     positive_and_zero_reject=bool(pos and zero),
                     accepted_zero_and_reject=bool(acc and min(acc) == 0 and (pos or zero)),
                     accepted_penalty_groups=bool(acc and pos),
                     nonmatching_accepted_penalty=bool(acc and pos and
                         any(abs(x * RATIO - y) > TOL for x in acc for y in pos)),
                     accepted_max_no_reject=bool(acc and max(acc) == cap_lo and cap_lo > 0 and not (pos or zero)),
                     all_zero_reject=len(zero) == len(rs))
        if pos:
            known[i] = penalty_charge(next(r for r in rs if not r["accepted"] and amt(r) > 0))
        elif acc and (max(acc) < cap_lo or max(acc) == 0):
            known[i] = max(acc)
        if our is not None and i == US:
            if i in known:
                stats["own_exact_charge_mismatch"] += abs(known[i] - our_a) > TOL
            known[US] = our_a
            for r in rs:
                x = amt(r)
                if r["accepted"]:
                    stats["own_accepted_exceeds_charge"] += x > our_a + TOL
                elif x > 0:
                    stats["own_penalties"] += 1
                    stats["own_penalty_mismatch"] += abs(x - RATIO * our_a) > TOL
    for r in rows:
        x = amt(r)
        stats["invalid_row"] += type(r["accepted"]) is not bool or not x.is_finite() or x < 0
        if r["accepted"]:
            stats["accepted_non_cent"] += x != x.quantize(CENT)
        elif x > 0:
            stats["positive_rejects"] += 1
            diff = abs(x - RATIO * penalty_charge(r))
            stats["penalty_grid_violation"] += diff > TOL
            stats["penalty_non_cent"] += x != x.quantize(CENT)
        if our is not None and r["reviewer"] == US and r["issuer"] in known:
            stats["own_limit_mismatch"] += r["accepted"] != (known[r["issuer"]] <= our_b)
    for rs in reviewers.values():
        yes = [known[r["issuer"]] for r in rs if r["accepted"] and r["issuer"] in known]
        no = [known[r["issuer"]] for r in rs if not r["accepted"] and r["issuer"] in known]
        stats["known_monotonicity_violation"] += bool(yes and no and max(yes) >= min(no))
    uncapped = feasible(issuers, reviewers, our, max_x, False)
    capped = max_x > 0 and feasible(issuers, reviewers, our, max_x, True)
    stats.update(infeasible=not (uncapped or capped), needs_cap=capped and not uncapped,
                 cap_possible=capped)


def replay(rows, sub, oracle):
    baseline = net_by_team(rows)[US]
    float_rows = [dict(r, amount=float(r["amount"])) for r in rows]
    candidate = {ln: tuple(map(float, ab)) for ln, ab in sub.items()}
    withheld = [r for r in float_rows if US not in (r["issuer"], r["reviewer"])]
    assert len(withheld) == 110 * len(sub)
    full = oracle.reconstruct(float_rows, US, {ln: b for ln, (_, b) in candidate.items()},
                             {ln: a for ln, (a, _) in candidate.items()})
    held = oracle.reconstruct(withheld, US)
    stats = Counter()
    for ln, ab in candidate.items():
        lo, hi, _, _ = oracle.line_value(held[ln], US, *ab)
        exact = float(net_by_team([r for r in rows if r["line_item_index"] == ln])[US])
        if exact < lo - .01:
            stats["line_below"] += 1
        if exact > hi + .01:
            stats["line_above"] += 1
    return float(baseline), oracle.game_value(full, US, candidate), oracle.game_value(held, US, candidate), stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("field", type=Path)
    p.add_argument("--through-game", type=int, default=10)
    args = p.parse_args()
    matrix = load(args.field / "matrix.json")
    performance = load(args.field / "performance.json")
    official = load(args.field / "games.json")
    roster = {t["team_name"] for t in matrix["items"]}
    logs = load(ROOT / "outputs/model_outputs.json")["games"]
    games = {g: load(args.field / f"tx_g{g}.json") for g in matrix["game_ids"]
             if g <= args.through_game}
    patched = patched_module()
    leftovers = {f.name for f in args.field.glob("tx_g*.json")} - {f"tx_g{g}.json" for g in games}
    print("matrix game IDs, completed metadata game count, extra transaction files:",
          list(games), sum(x["status"] == "completed" for x in official["items"]), len(leftovers))
    totals = Counter()
    widths = [[], []]
    for g in games:
        rows = games[g]
        by_line = group(rows, "line_item_index")
        sub = {s["index"] + 1: (D(s["a"]), D(s["b"]))
               for s in logs.get(str(g), {}).get("submitted", [])}
        if sub:
            assert by_line.keys() == sub.keys()
        stats = Counter()
        for ln, line in by_line.items():
            inspect_line(line, roster, sub.get(ln), stats)
        nets = net_by_team(rows)
        n = matrix["game_ids"].index(g)
        residuals = [abs(nets[t["team_name"]] - D(t["cells"][n])) for t in matrix["items"]]
        profile_sum = sum(nets.values())
        matrix_sum = sum(D(t["cells"][n]) for t in matrix["items"])
        stats.update(matrix_over_cent=sum(d > CENT + TOL for d in residuals),
                     matrix_over_tolerance=sum(d > TOL for d in residuals))
        totals.update(stats)
        print(f"g{g}: rows={len(rows)} lines={len(by_line)} row net residual={profile_sum:.9f} "
              f"matrix net residual={matrix_sum:.9f} max team-game reconciliation error={max(residuals):.9f} "
              f"ambiguous={stats['accepted_max_no_reject']} needs_cap={stats['needs_cap']}")
        if not sub:
            print("   no logged policy, excluded from holdout")
            continue
        actual, full, held, misses = replay(rows, sub, er)
        _, full_core, changed, new_misses = replay(rows, sub, patched)
        totals.update(holdout_ambiguous_max=sum(
            a["a"] is not None and not a["exact"] and a["status"] == "inflated"
            and not any(not r["accepted"] for r in rows if
                        r["line_item_index"] == ln and r["issuer"] == i and r["reviewer"] != US)
            for ln, state in er.reconstruct([dict(r, amount=float(r["amount"])) for r in rows
                if US not in (r["issuer"], r["reviewer"])], US).items()
            for i, a in state["A"].items()))
        for values, store in zip((held, changed), widths):
            store.append(values[1] - values[0])
        for suffix, d in (("old", misses), ("core", new_misses)):
            totals.update({f"{k}_{suffix}": v for k, v in d.items()})
        print(f"   actual={actual:.4f} full=[{full[0]:.4f}, {full[1]:.4f}] "
              f"full_core=[{full_core[0]:.4f}, {full_core[1]:.4f}] "
              f"held=[{held[0]:.4f}, {held[1]:.4f}] width={widths[0][-1]:.4f} "
              f"id={held[2]:.1%} miss={max(held[0]-actual, actual-held[1], 0):.4f} "
              f"core=[{changed[0]:.4f}, {changed[1]:.4f}] width={widths[1][-1]:.4f} "
              f"core_miss={max(changed[0]-actual, actual-changed[1], 0):.4f}")
    print("aggregate", dict(sorted(totals.items())))
    print("median and sum of widths", [(median(x), sum(x)) for x in widths])
    if set(performance) == roster and list(games) == matrix["game_ids"]:
        snapshots = [sum(net_by_team(rows).get(team, D(0)) for rows in games.values()) for team in roster]
        differences = [abs(D(performance[t]["net"]) - v) for t, v in zip(roster, snapshots)]
        print("performance snapshot team residuals over 1 cent:", sum(d > CENT + TOL for d in differences))


if __name__ == "__main__":
    main()
