"""EUR replay: what would a saved model answer have earned against the REAL field of each completed game?

    python3 -I research/raw3/scripts/eur_replay.py LB_DIR "Our Team Name" [TMULT]

LB_DIR is a scratch directory OUTSIDE the repo holding tx_<game>.json (public leaderboard rows, see fetch in the report);
nothing about other teams is written anywhere, the output is our own counterfactual net per game. Stdlib only.
Per line and candidate (a, b), opponents held fixed:
  income  each opponent accepts if a <= lower end of its acceptance bracket, rejects if a >= upper end, 50/50 in between;
          fair (a <= t) pays a or 1.5a, inflated pays a if accepted else 0.
  cost    every opponent charge with a known value: fair -> a if a <= b else 1.5a; inflated -> a if a <= b else 0.
  t       geometric mean of the bracket if two-sided; t_lo * TMULT if only a lower bound exists (default 1.0 = conservative
          for high charges); 0 if no fair charge was seen.
Rules compared on the model's median gross total m and validity q:
  pricing.py   the a, b that claimbot/pricing.py produced (stored in the bench results)
  mult(ka,kb)  a = ka*m on every line; b = kb*m if q >= 2/3 else 0
  LOGO         (ka, kb) chosen on the other games, applied to the held-out game
"""
import collections, glob, importlib.util, itertools, json, math, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TMULT = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
spec = importlib.util.spec_from_file_location("field", Path(__file__).with_name("field_reconstruct.py"))
F = importlib.util.module_from_spec(spec); sys.argv = sys.argv[:3]; spec.loader.exec_module(F)
D = F.load(); US = F.US
for k, L in D.items():
    L["t"] = (math.sqrt(L["t_lo"] * L["t_hi"]) if L["t_hi"] else L["t_lo"] * TMULT) if L["t_lo"] > 0 else 0.0
    L["br"] = {t: F.b_bracket(L, t) for t in F.teams if t != US}


def net(L, a, b):
    fair = a <= L["t"]; inc = 0.0
    if a > 0:
        for lo, hi in L["br"].values():
            p = 1.0 if a <= lo else 0.0 if a >= hi else 0.5
            inc += a * (p + 1.5 * (1 - p)) if fair else a * p
    cost = 0.0
    for t, (kind, x) in L["A"].items():
        if t == US or not x: continue
        if kind == "fair": cost += x if x <= b else 1.5 * x
        elif kind == "infl": cost += x if x <= b else 0.0
    return inc - cost


actual = collections.Counter()
for (g, ln), L in D.items():
    for (i, r), amt in L["amt"].items():
        if i == US: actual[g] += amt
        if r == US: actual[g] -= amt
games = sorted(actual)
oracle = {g: sum(net(L, L["t"] if L["t"] > 0 else 0.0, L["t"]) for (gg, ln), L in D.items() if gg == g) for g in games}
print("our ACTUAL net per game:", {g: round(v) for g, v in actual.items()}, "total", round(sum(actual.values())))
print("net with a = b = t on every line (others fixed):", {g: round(v) for g, v in oracle.items()}, "total", round(sum(oracle.values())))

ans = collections.defaultdict(lambda: collections.defaultdict(list))   # (model, variant) -> (game, line) -> [(m, q, a, b)]
for f in sorted(glob.glob(str(ROOT / "runs/bench/results/bench_*.json"))):
    for r in json.load(open(f))["results"]:
        g = int(r["case"].split("_")[1])
        for l in r.get("lines") or []:
            if (g, l["line"]) in D:
                ans[(r["model"].split("/")[-1], r["variant"])][(g, l["line"])].append((l["t_med"], l["q"], l["a"], l["b"]))
KA = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.35]
KB = [0.7, 0.85, 1.0, 1.15, 1.3, 1.5, 2.0]


def game_net(rows, g, rule):
    """mean over repeats of the net on game g; rows[(g, ln)] = list of answers"""
    tot = 0.0
    for (gg, ln), L in D.items():
        if gg != g: continue
        xs = rows.get((g, ln))
        if not xs: return None
        tot += st.mean(net(L, *rule(m, q, a, b)) for m, q, a, b in xs)
    return tot


def mult(ka, kb): return lambda m, q, a, b: (ka * m, kb * m if q >= 2 / 3 else 0.0)
team = lambda m, q, a, b: (a, b)
print(f"\n{'model':20s}{'variant':16s}{'games':>6s} | {'pricing.py':>10s} {'mult(.8,.9)':>11s} {'mult(1,1.15)':>12s} {'best in-sample':>20s} {'LOGO mult':>10s} | actual on same games")
summary = collections.defaultdict(list)
for (m_, v), rows in sorted(ans.items()):
    gs = [g for g in games if game_net(rows, g, team) is not None]
    if len(gs) < 3: continue
    tn = sum(game_net(rows, g, team) for g in gs)
    grid = {(ka, kb): {g: game_net(rows, g, mult(ka, kb)) for g in gs} for ka in KA for kb in KB}
    best = max(grid, key=lambda k: sum(grid[k].values()))
    logo = 0.0
    for held in gs:
        pick = max(grid, key=lambda k: sum(v for g, v in grid[k].items() if g != held))
        logo += grid[pick][held]
    act = sum(actual[g] for g in gs)
    print(f"{m_:20s}{v:16s}{len(gs):>6d} | {tn:10.0f} {sum(grid[(0.8, 0.85)].values()):11.0f} {sum(grid[(1.0, 1.15)].values()):12.0f} {sum(grid[best].values()):12.0f} {str(best):>8s} {logo:10.0f} | {act:.0f}")
    if len(gs) == len(games):
        summary["pricing.py"].append(tn); summary["mult(0.8,0.85)"].append(sum(grid[(0.8, 0.85)].values()))
        summary["mult(1.0,1.15)"].append(sum(grid[(1.0, 1.15)].values())); summary["LOGO mult"].append(logo)
        for k, v in grid.items(): summary[("grid", k)].append(sum(v.values()))
print(f"\nmean over model x variant rows that cover all {len(games)} games (n={len(summary['pricing.py'])}):")
for k in ["pricing.py", "mult(0.8,0.85)", "mult(1.0,1.15)", "LOGO mult"]:
    print(f"  {k:16s} {st.mean(summary[k]):8.0f}")
print("  grid of mean net by (ka rows, kb cols):")
print("        " + " ".join(f"kb={kb:<5.2f}" for kb in KB))
for ka in KA:
    print(f"  ka={ka:<4.2f} " + " ".join(f"{st.mean(summary[('grid', (ka, kb))]):8.0f}" for kb in KB))
# crowd of cheap models: median m over models (one variant), mean q
for v in ["v1_current", "v2_policy_math"]:
    for names in [None, ("gpt-6-luna", "gemini-3.8-flash", "claude-haiku-5.5")]:
        crowd = collections.defaultdict(list)
        for (m_, vv), rows in ans.items():
            if vv != v or (names and m_ not in names): continue
            for key, xs in rows.items():
                crowd[key].append((st.median(x[0] for x in xs), st.mean(x[1] for x in xs)))
        rows = {key: [(st.median(x[0] for x in xs), st.mean(x[1] for x in xs), 0, 0)] for key, xs in crowd.items()}
        gs = [g for g in games if game_net(rows, g, team) is not None]
        if len(gs) < len(games): continue
        print(f"  crowd median, {v}, {'3 cheap models' if names else 'all 7 models'}: mult(0.8,0.85) {sum(game_net(rows, g, mult(0.8, 0.85)) for g in gs):.0f}   mult(1.0,1.15) {sum(game_net(rows, g, mult(1.0, 1.15)) for g in gs):.0f}   mult(0.9,1.0) {sum(game_net(rows, g, mult(0.9, 1.0)) for g in gs):.0f}")

# ---- per game: variants (mean over models) and crowd vs single, fixed multipliers (no fitting)
print("\nper game, fixed rule mult(0.9, 1.0), mean over the models that answered that game:")
for v in ["v0_original", "v1_current", "v2_policy_math"]:
    out = {}
    for g in games:
        xs = [game_net(rows, g, mult(0.9, 1.0)) for (m_, vv), rows in ans.items() if vv == v]
        xs = [x for x in xs if x is not None]
        out[g] = (round(st.mean(xs)), len(xs)) if xs else None
    print(f"  single model, {v:15s}", out)
for v in ["v1_current", "v2_policy_math"]:
    crowd = collections.defaultdict(list)
    for (m_, vv), rows in ans.items():
        if vv != v: continue
        for key, xs in rows.items():
            crowd[key].append((st.median(x[0] for x in xs), st.mean(x[1] for x in xs)))
    rows = {key: [(st.median(x[0] for x in xs), st.mean(x[1] for x in xs), 0, 0)] for key, xs in crowd.items()}
    print(f"  crowd median,  {v:15s}", {g: round(game_net(rows, g, mult(0.9, 1.0))) for g in games if game_net(rows, g, mult(0.9, 1.0)) is not None})
print("  actual live bot               ", {g: round(v) for g, v in actual.items()})
print("  a = b = t                     ", {g: round(v) for g, v in oracle.items()})
