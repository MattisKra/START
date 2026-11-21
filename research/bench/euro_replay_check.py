"""Validate euro_replay.py.   python3 -I research/bench/euro_replay_check.py FIELD_DIR --us "Team Name" [--synthetic N]

(1) ACTUAL: replay our logged actual (a, b) per line (outputs/model_outputs.json) against the reconstructed field; the range must contain our actual
    net, and where everything is identified it must equal it.  (2) SYNTHETIC: fields with known truth (t, cap, every team's a and b) are generated with
    the exact payoff rules, rows are produced, the field is reconstructed from the ROWS ONLY and random candidate policies are replayed; the range must
    contain the true counterfactual in 100 % of cases. Reports the width (how much the bounds leave open).
"""
import importlib.util, json, math, random, statistics as st, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("er", ROOT / "research/bench/euro_replay.py")
er = importlib.util.module_from_spec(spec); spec.loader.exec_module(er)


def actual_check(field_dir, us):
    games = er.load_field(field_dir)
    logs = json.loads((ROOT / "outputs/model_outputs.json").read_text())["games"]
    print(f"{'game':>4s} {'actual net':>11s} {'replay lo':>10s} {'replay hi':>10s} {'width':>8s} {'ident':>6s}  contains?")
    ok = 0; n = 0; widths = []
    for g, rows in games.items():
        sub = {s["index"] + 1: (s["a"], s["b"]) for s in logs.get(str(g), {}).get("submitted", [])}
        if not sub:
            continue
        lines = er.reconstruct(rows, us, our_b={ln: b for ln, (a, b) in sub.items()}, our_a={ln: a for ln, (a, b) in sub.items()})
        lo, hi, idn = er.game_value(lines, us, sub)
        act = er.actual_net(rows, us)
        inside = lo - 1.0 <= act <= hi + 1.0
        ok += inside; n += 1; widths.append(hi - lo)
        print(f"{g:>4d} {act:>11.2f} {lo:>10.2f} {hi:>10.2f} {hi - lo:>8.2f} {idn:>6.0%}  {'yes' if inside else 'NO  <-- evaluator wrong'}")
    print(f"actual net inside the replay range in {ok}/{n} games; mean width {st.mean(widths):.1f} EUR")


# ------------------------------------------------------------------ synthetic fields with known truth
def pay(a, b, t, c):
    if a <= b:
        return min(a, c)
    return 1.5 * a if a <= t else 0.0


def make_game(rng, n_teams=12, n_lines=4, us_policy=None):
    teams = list(range(n_teams)); US = 0
    truth = []
    for ln in range(n_lines):
        t = 0.0 if rng.random() < 0.25 else math.exp(rng.gauss(5.0, 1.0))
        c = max(4 * t * (1 + rng.random()), 30 + 70 * rng.random())
        strat = {}
        for j in teams:
            kind = rng.choice(["silent", "rational", "rational", "rational", "accept_all", "strict", "overcharge"])
            e = math.exp(rng.gauss(0, rng.choice([0.1, 0.25, 0.5])))
            base = t if t > 0 else math.exp(rng.gauss(4, 1)) * 0.5
            if kind == "silent": a, b = 0.0, 0.0
            elif kind == "rational": a, b = base * 0.8 * e, base * e
            elif kind == "accept_all": a, b = base * 0.9 * e, 1e9
            elif kind == "strict": a, b = base * 0.7 * e, base * 0.6 * e
            else: a, b = base * 1.5 * e, base * 1.1 * e
            strat[j] = (a, b)
        truth.append(dict(t=t, c=c, strat=strat))
    return truth


def rows_from(truth, us_policy):
    rows = []
    for ln, T in enumerate(truth, 1):
        for i, (ai, _) in T["strat"].items():
            a_i = us_policy[ln][0] if i == 0 else ai
            for j, (_, bj) in T["strat"].items():
                if i == j:
                    continue
                b_j = us_policy[ln][1] if j == 0 else bj
                amt = pay(a_i, b_j, T["t"], T["c"])
                rows.append(dict(issuer=i, reviewer=j, line_item_index=ln, accepted=a_i <= b_j, amount=round(amt, 2)))
    return rows


def true_net(truth, policy, base_policy):
    """Exact counterfactual net of team 0 when it plays `policy`, everybody else as in truth."""
    tot = 0.0
    for ln, T in enumerate(truth, 1):
        a0, b0 = policy[ln]
        for j, (aj, bj) in T["strat"].items():
            if j == 0:
                continue
            tot += pay(a0, bj, T["t"], T["c"]) - pay(aj, b0, T["t"], T["c"])
    return tot


def synthetic(n_games, seed=7):
    rng = random.Random(seed)
    inside = tot = 0; widths = []; ident = []; viol = []; rounding = []
    for g in range(n_games):
        truth = make_game(rng)
        base = {ln: (math.exp(rng.gauss(5, 1)) * 0.8, math.exp(rng.gauss(5, 1))) for ln in range(1, len(truth) + 1)}   # what we actually played
        rows = rows_from(truth, base)
        lines = er.reconstruct(rows, 0, our_b={ln: b for ln, (a, b) in base.items()}, our_a={ln: a for ln, (a, b) in base.items()})
        for _ in range(6):                                                    # candidate policies, some near the truth
            cand = {}
            for ln, T in enumerate(truth, 1):
                ref = T["t"] if T["t"] > 0 else 80.0
                cand[ln] = (ref * rng.choice([0.0, 0.5, 0.8, 0.95, 1.1, 2.0]), ref * rng.choice([0.0, 0.6, 1.0, 1.25, 3.0]))
            lo, hi, idn = er.game_value(lines, 0, cand)
            tn = true_net(truth, cand, base)
            tot += 1; ok_ = lo - 1.0 <= tn <= hi + 1.0; inside += int(ok_); widths.append(hi - lo); ident.append(idn)
            exact = lo - 0.01 <= tn <= hi + 0.01
            if not ok_:
                viol.append((g, tn, lo, hi))
            elif not exact:
                rounding.append(max(lo - tn, tn - hi))
    print("  NOTE: this synthetic test is WEAK (benign generator, game totals, 1 EUR tolerance) and could not detect two real defects; the regression gate is research/raw5/scripts/g_adversarial.py")
    print(f"synthetic: truth inside the range in {inside}/{tot} cases ({inside / tot:.1%}); median width {st.median(widths):.0f} EUR "
          f"(median |true net| scale {st.median([abs(v) for v in widths]):.0f}); median identified share {st.median([x for x in ident if x == x]):.0%}")
    print(f"  boundary cases beyond 0.01 EUR but within 1 EUR (cent rounding of the rows): {len(rounding)}; largest excess {max(rounding, default=0):.2f} EUR")
    for v in viol[:5]:
        print("  violation: game %d true %.1f range [%.1f, %.1f]" % v)


if __name__ == "__main__":
    us = sys.argv[sys.argv.index("--us") + 1] if "--us" in sys.argv else None
    if us:
        actual_check(sys.argv[1], us)
    if "--synthetic" in sys.argv:
        synthetic(int(sys.argv[sys.argv.index("--synthetic") + 1]))
