"""Audit G, step 3: GENUINE out-of-sample tests of research/bench/euro_replay.py on the real public settlement rows.

    python3 -I research/raw5/scripts/g_loo.py FIELD_DIR --us "Team Name"

FIELD_DIR = scratch folder written by research/raw4/scripts/fetch_field.py (OUTSIDE the repo). Prints our own numbers and anonymous aggregates only.

 (0) LOG FAITHFULNESS  our logged (a, b) per line versus what our own rows reveal (a where a row shows it, b inside the accept / reject bracket).
 (1) LEAVE-OUR-ROWS-OUT  the field is reconstructed from the rows that do NOT involve us at all (neither as issuer nor as reviewer) and without our
     log; our logged actual (a, b) is replayed; the true actual net (from all rows) must lie inside the range. Nothing about us leaks into the field.
 (2) LEAVE-ONE-TEAM-OUT  the same for every team X in turn (12 x more tests). X's policy is not logged, so the test uses what its rows prove:
     a_X where a row reveals it exactly (otherwise the revenue side is skipped for that line), and b_X := the highest charge X accepted (every
     outcome of X as reviewer is the same for any limit inside its bracket, so this reproduces X's real outcomes). The field is reconstructed
     WITHOUT any row of X; X's real income and real cost on the line must lie inside the evaluator's revenue and cost range.
"""
import collections, importlib.util, json, statistics as st, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


er = _load("er", ROOT / "research/bench/euro_replay.py")
fx = _load("fx", HERE / "g_replay_fixed.py")
INF = float("inf")
TOL = 0.02

field_dir, us = sys.argv[1], sys.argv[sys.argv.index("--us") + 1]
games = er.load_field(field_dir)
logs = json.loads((ROOT / "outputs/model_outputs.json").read_text())["games"]


def line_net(rows, team, ln):
    inc = sum(r["amount"] for r in rows if r["issuer"] == team and r["line_item_index"] == ln)
    cost = sum(r["amount"] for r in rows if r["reviewer"] == team and r["line_item_index"] == ln)
    return inc, cost


# ---------------------------------------------------------------- (0) is the log what was live?
print("(0) LOG FAITHFULNESS: logged (a, b) vs our own rows")
bad = n = 0
for g, rows in games.items():
    sub = {s["index"] + 1: (s["a"], s["b"]) for s in logs.get(str(g), {}).get("submitted", [])}
    if not sub:
        print(f"  game {g}: no logged submission in outputs/model_outputs.json -> cannot be replayed"); continue
    full = er.reconstruct(rows, us)
    for ln, (a, b) in sorted(sub.items()):
        me = full[ln]["A"][us]; Bu = full[ln]["B"][us]
        n += 1
        a_ok = (me["status"] == "hidden") or (me["a"] is not None and (abs(me["a"] - a) < 0.011 if me["exact"] else a >= me["a"] - 0.011))
        b_ok = Bu["lo"] - 0.011 <= b < Bu["hi"] + 0.011 or (b >= Bu["lo"] - 0.011 and Bu["hi"] == INF)
        if not (a_ok and b_ok):
            bad += 1
            print(f"  game {g} line {ln}: log a={a} b={b} but rows show a={me['a']} ({me['status']}, exact={me['exact']}), b in [{Bu['lo']}, {Bu['hi']})")
print(f"  {n} logged lines checked, {bad} inconsistent with our own rows")


# ---------------------------------------------------------------- (1) leave-our-rows-out
def loo_us(mod, label):
    print(f"\n(1) LEAVE-OUR-ROWS-OUT with {label}: field from rows that do not involve us, no log; replay of our logged (a, b)")
    print(f"  {'game':>4s} {'actual net':>11s} {'lo':>11s} {'hi':>11s} {'width':>10s} {'ident':>6s}  inside?   lines with truth outside (line: actual vs range)")
    ok = tot = 0; widths = []; ln_ok = ln_tot = 0
    for g, rows in games.items():
        sub = {s["index"] + 1: (s["a"], s["b"]) for s in logs.get(str(g), {}).get("submitted", [])}
        if not sub:
            continue
        wo = [r for r in rows if r["issuer"] != us and r["reviewer"] != us]
        lines = mod.reconstruct(wo, us)
        lo, hi, idn = mod.game_value(lines, us, sub)
        act = er.actual_net(rows, us)
        inside = lo - TOL <= act <= hi + TOL
        outs = []
        for ln, (a, b) in sorted(sub.items()):
            l, h, _, _ = mod.line_value(lines[ln], us, a, b)
            inc, cost = line_net(rows, us, ln)
            ln_tot += 1
            if l - TOL <= inc - cost <= h + TOL:
                ln_ok += 1
            else:
                outs.append(f"{ln}: {inc - cost:.2f} vs [{l:.2f}, {h:.2f}]")
        ok += inside; tot += 1; widths.append(hi - lo)
        print(f"  {g:>4d} {act:>11.2f} {lo:>11.2f} {hi:>11.2f} {hi - lo:>10.2f} {idn:>6.0%}  {'yes' if inside else 'NO '}      {'; '.join(outs)}")
    print(f"  game totals inside: {ok}/{tot}; lines inside: {ln_ok}/{ln_tot}; median width {st.median(widths):.0f} EUR, mean {st.mean(widths):.0f} EUR")


# ---------------------------------------------------------------- (2) leave-one-team-out, every team
def loo_all(mod, label):
    C = collections.Counter(); viol = []; w_rev = []; w_cost = []; rel = []
    for g, rows in games.items():
        teams = sorted({r["issuer"] for r in rows})
        full = er.reconstruct(rows, None)
        for X in teams:
            wo = [r for r in rows if r["issuer"] != X and r["reviewer"] != X]
            lines = mod.reconstruct(wo, X)
            for ln in sorted(lines):
                me = full[ln]["A"][X]; bX = full[ln]["B"][X]["lo"]
                inc, cost = line_net(rows, X, ln)
                l0, h0, _, _ = mod.line_value(lines[ln], X, 0.0, bX)          # a = 0: range of minus the cost
                c_lo, c_hi = -h0, -l0
                C["cost_tests"] += 1; w_cost.append(c_hi - c_lo)
                if not (c_lo - TOL <= cost <= c_hi + TOL):
                    C["cost_outside"] += 1; C["cost_above_hi (lower bound of the net broken)"] += cost > c_hi + TOL
                    C["cost_below_lo (upper bound of the net broken)"] += cost < c_lo - TOL
                    viol.append(("cost", g, ln, cost, c_lo, c_hi))
                if me["status"] in ("hidden",) or not me["exact"]:
                    C["revenue_skipped (charge not revealed exactly)"] += 1
                    continue
                l1, h1, _, _ = mod.line_value(lines[ln], X, me["a"], bX)
                r_lo, r_hi = l1 - l0, h1 - h0
                C["revenue_tests"] += 1; w_rev.append(r_hi - r_lo)
                if not (r_lo - TOL <= inc <= r_hi + TOL):
                    C["revenue_outside"] += 1; C["revenue_below_lo (lower bound of the net broken)"] += inc < r_lo - TOL
                    C["revenue_above_hi (upper bound of the net broken)"] += inc > r_hi + TOL
                    viol.append(("revenue", g, ln, inc, r_lo, r_hi))
                C["revenue_exact (width 0)"] += abs(r_hi - r_lo) < TOL
            # whole game for X where every line is replayable
    print(f"\n(2) LEAVE-ONE-TEAM-OUT with {label}: every team in turn, field rebuilt without any of its rows")
    for k in sorted(C):
        print(f"  {k:<52s} {C[k]}")
    print(f"  cost range width: median {st.median(w_cost):.0f}, mean {st.mean(w_cost):.0f} EUR;  revenue range width: median {st.median(w_rev):.0f}, mean {st.mean(w_rev):.0f} EUR")
    if viol:
        ex = sorted(viol, key=lambda v: -max(v[3] - v[5], v[4] - v[3]))
        print("  violations, anonymous (kind, game, line, real value, range, excess EUR):")
        for kind, g, ln, v, lo, hi in ex[:12]:
            print(f"    {kind:8s} g{g} l{ln}: real {v:.2f} vs [{lo:.2f}, {hi:.2f}]  excess {max(v - hi, lo - v):.2f}")
        print(f"    total excess over all violations: {sum(max(v - hi, lo - v) for _, _, _, v, lo, hi in viol):.0f} EUR in {len(viol)} line tests")


for mod, label in ((er, "ORIGINAL euro_replay.py"), (fx, "FIXED g_replay_fixed.py")):
    loo_us(mod, label)
    loo_all(mod, label)
