"""Profile the OTHER teams' strategies from the public settlement rows. Prints to the terminal only, teams anonymised by cumulative rank.

    uv run --with numpy --with pyzipper python research/bench/field_strategies.py FIELD_DIR --us "Team Name"

FIELD_DIR is the scratch folder from research/raw4/scripts/fetch_field.py (OUTSIDE the repo). Nothing is written. Contains no data.
Per team (anonymised R1 = best cumulative net): issuer behaviour (share of its positive charges that were fair / inflated, charge relative to the
highest fair charge L), reviewer behaviour (limit provably below L / above the lowest inflated charge U / unresolved; limit vs its own charge),
use of the excluded-line option, activity per game, and the correlation of its log-charges with OUR readers' estimates (stack fingerprint).
"""
import collections, importlib.util, json, math, statistics as st, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
def load(name, rel):
    sp = importlib.util.spec_from_file_location(name, ROOT / rel); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
er = load("er", "research/bench/euro_replay.py"); ab = load("ab", "research/bench/arch_bench.py")
from claimbot_fable.schema import ReaderCase
INF = float("inf")
field_dir, US = sys.argv[1], sys.argv[sys.argv.index("--us") + 1]
games = er.load_field(field_dir)
matrix = json.loads((Path(field_dir) / "matrix.json").read_text())
tot = {t["team_name"]: sum(t["cells"]) for t in matrix["items"]}
order = sorted(tot, key=lambda t: -tot[t])
label = {t: ("US" if t == US else f"R{order.index(t) + 1}") for t in order}
saved = ab.load_saved()
reader_m = {}                                   # (game, line) -> {reader: m}
for g in games:
    for nm, rd in (("luna", ab.LUNA), ("terra", ab.TERRA), ("fable", ab.FABLE)):
        r = saved.get((rd, f"case_{g:03d}"))
        if r:
            for x in ab.engine.compute(ReaderCase.model_validate(r["est"]), ab.P):
                reader_m.setdefault((g, x.index + 1), {})[nm] = x.m
S = collections.defaultdict(lambda: collections.defaultdict(list))
charges = collections.defaultdict(dict)          # team -> {(g, line): a}
active = collections.defaultdict(dict)           # team -> {g: bool silent}
for g, rows in games.items():
    lines = er.reconstruct(rows, US)
    for ln, Ln in lines.items():
        L, U = Ln["L"], Ln["U"]
        for t, A in Ln["A"].items():
            if t == US:
                continue
            S[t]["lines"].append(1)
            if A["status"] == "zero":
                S[t]["zero"].append(1)
                if L == 0 and U == INF: S[t]["excl_zero"].append(1)
                continue
            if L == 0:
                S[t]["excl_pos"].append(1)               # positive charge on a line where no fair charge exists (probably excluded)
                continue
            S[t]["pos"].append(1)
            if A["status"] == "fair": S[t]["fair"].append(1)
            elif A["status"] in ("inflated", "hidden"): S[t]["infl"].append(1)
            if A["a"]: S[t]["ratio"].append(A["a"] / L); charges[t][(g, ln)] = A["a"]
        for t, B in Ln["B"].items():
            if t == US:
                continue
            S[t]["rev_lines"].append(1)
            if L > 0:
                if B["hi"] <= L: S[t]["b_below_L"].append(1)           # provably rejects some fair charge level
                elif B["lo"] >= U: S[t]["b_above_U"].append(1)          # accepts at least the lowest inflated charge
                elif B["lo"] >= L: S[t]["b_ok"].append(1)
                else: S[t]["b_unres"].append(1)
            a_own = Ln["A"].get(t, {}).get("a")
            if a_own and a_own > 0:
                if B["lo"] >= a_own: S[t]["b_ge_a"].append(1)
                elif B["hi"] <= a_own: S[t]["b_lt_a"].append(1)
    for t in {r["issuer"] for r in rows}:
        mine = [r for r in rows if r["issuer"] == t]
        active[t][g] = all(r["amount"] == 0 and r["accepted"] for r in mine)       # charged nothing
n = lambda t, k: len(S[t][k])
print(f"games {sorted(games)}; {len(order) - 1} opponents; labels R1..R{len(order)} = cumulative rank (US = us)\n")
print(f"{'team':5s}{'net':>8s}{'silent games':>13s}{'lines':>6s}{'pos chg':>8s}{'%fair':>7s}{'%infl':>7s}{'med a/L':>8s}{'excl chg':>9s}{'rev: b<L':>9s}{'b>=U':>6s}{'ok':>5s}{'?':>5s}{'b>=own a':>9s}")
rows_out = []
for t in order:
    if t == US: continue
    pos = n(t, "pos") or 1; rv = (n(t, "b_below_L") + n(t, "b_above_U") + n(t, "b_ok") + n(t, "b_unres")) or 1
    ex = n(t, "excl_pos") + n(t, "excl_zero")
    ba = (n(t, "b_ge_a") + n(t, "b_lt_a")) or 1
    sg = sum(1 for g, z in active[t].items() if z)
    print(f"{label[t]:5s}{tot[t]:8.0f}{sg:>8d}/{len(active[t]):<4d}{n(t, 'lines'):>6d}{n(t, 'pos'):>8d}{n(t, 'fair') / pos:>7.0%}{n(t, 'infl') / pos:>7.0%}"
          f"{(st.median(S[t]['ratio']) if S[t]['ratio'] else float('nan')):>8.2f}{(n(t, 'excl_pos') / ex if ex else float('nan')):>9.0%}"
          f"{n(t, 'b_below_L') / rv:>9.0%}{n(t, 'b_above_U') / rv:>6.0%}{n(t, 'b_ok') / rv:>5.0%}{n(t, 'b_unres') / rv:>5.0%}{n(t, 'b_ge_a') / ba:>9.0%}")
# fingerprint: correlation of log charges with our readers' estimates
print("\nstack fingerprint: Pearson r of log(charge) with log(our reader's estimate) over the team's known charges (n lines), and median log ratio (level)")
print(f"{'team':5s}{'n':>4s}" + "".join(f"{r:>14s}" for r in ("luna", "terra", "fable")))
fp = {}
for t in order:
    if t == US: continue
    cells = []
    for nm in ("luna", "terra", "fable"):
        pts = [(math.log(a), math.log(reader_m[k][nm])) for k, a in charges[t].items() if k in reader_m and nm in reader_m[k] and reader_m[k][nm] > 0 and a > 0]
        if len(pts) >= 6:
            x, y = np.array(pts).T
            cells.append((np.corrcoef(x, y)[0, 1], float(np.median(x - y)), len(pts)))
        else:
            cells.append(None)
    fp[t] = cells
    nn = max([c[2] for c in cells if c], default=0)
    print(f"{label[t]:5s}{nn:>4d}" + "".join(f"{(f'r={c[0]:.2f} lvl{c[1]:+.2f}' if c else '-'):>14s}" for c in cells))
# similarity between teams: same lines, correlation of log charges
print("\nteam pairs whose charges are almost the same on shared lines (>= 8 shared lines, r >= 0.97 and median |log ratio| <= 0.08):")
pairs = []
ts = [t for t in order if t != US]
for i, a in enumerate(ts):
    for b in ts[i + 1:]:
        keys = [k for k in charges[a] if k in charges[b]]
        if len(keys) >= 8:
            x = np.log([charges[a][k] for k in keys]); y = np.log([charges[b][k] for k in keys])
            if np.std(x) > 0 and np.std(y) > 0 and np.corrcoef(x, y)[0, 1] >= 0.97 and np.median(np.abs(x - y)) <= 0.08:
                pairs.append((label[a], label[b], len(keys)))
print("  " + (", ".join(f"{a}~{b} ({n_} lines)" for a, b, n_ in pairs) if pairs else "none"))
# dynamics: share of fair among positive charges and median a/L per game for the active teams
print("\nfield by game (opponents, aggregated): positive charges on lines with a fair benchmark: share fair | median a/L | share of reviewers provably below L")
for g, rows in sorted(games.items()):
    lines = er.reconstruct(rows, US); f = i = 0; rt = []; bl = tt = 0
    for ln, Ln in lines.items():
        if Ln["L"] <= 0: continue
        for t, A in Ln["A"].items():
            if t == US or A["status"] == "zero": continue
            if A["status"] == "fair": f += 1
            elif A["status"] in ("inflated", "hidden"): i += 1
            if A["a"]: rt.append(A["a"] / Ln["L"])
        for t, B in Ln["B"].items():
            if t != US: tt += 1; bl += int(B["hi"] <= Ln["L"])
    print(f"  game {g}: {f}/{f + i} fair ({f / max(f + i, 1):.0%}) | median a/L {st.median(rt) if rt else float('nan'):.2f} | reviewers provably below L: {bl}/{tt}")
