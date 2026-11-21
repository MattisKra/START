"""Replay one or more COMPLETED games and compare the official result with the evaluator.

    uv run --with pyzipper python research/bench/euro_game_report.py FIELD_DIR --us "Team Name" --games 9,10 [--lines]

For each game: our official net (exact, from the public rows), the evaluator's range for our logged actual submission (if we have it), and the
net RANGE of candidate policies built from the saved reader answers (luna / terra / fable through claimbot_fable.engine). With --lines the
per-line breakdown of the last game is printed (our actual income and cost per line next to each candidate's range).
Only our own numbers are printed; other teams' rows stay in memory.
"""
import importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
def load(name, rel):
    sp = importlib.util.spec_from_file_location(name, ROOT / rel); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
er = load("er", "research/bench/euro_replay.py"); ab = load("ab", "research/bench/arch_bench.py")
from claimbot_fable.schema import ReaderCase
engine = ab.engine
field_dir, US = sys.argv[1], sys.argv[sys.argv.index("--us") + 1]
G = [int(x) for x in sys.argv[sys.argv.index("--games") + 1].split(",")]
games = er.load_field(field_dir)
logs = json.loads((ROOT / "outputs/model_outputs.json").read_text())["games"]
saved = ab.load_saved()
P = engine.Params
def rec(g):
    sub = {s["index"] + 1: (s["a"], s["b"]) for s in logs.get(str(g), {}).get("submitted", [])}
    return er.reconstruct(games[g], US, our_b={l: b for l, (a, b) in sub.items()}, our_a={l: a for l, (a, b) in sub.items()}), sub
def policy(reader, g, params):
    est = ReaderCase.model_validate(saved[(reader, f"case_{g:03d}")]["est"])
    return {x.index + 1: (x.a, x.b) for x in engine.compute(est, params)}
CANDS = [
    ("luna KA .7 / KB .9   (shortlist, chosen before games 9-10)", ab.LUNA, P(ka_open=.7, kb_open=.9, ka_pinned=.65, kb_pinned=.9)),
    ("luna KA .6 / KB .6   (shortlist)", ab.LUNA, P(ka_open=.6, kb_open=.6, ka_pinned=.55, kb_pinned=.6)),
    ("luna KA .8 / KB .8   (shortlist)", ab.LUNA, P(ka_open=.8, kb_open=.8, ka_pinned=.75, kb_pinned=.8)),
    ("terra KA .8 / KB .8  (shortlist)", ab.TERRA, P(ka_open=.8, kb_open=.8, ka_pinned=.75, kb_pinned=.8)),
    ("luna engine defaults (KA .9 / KB 1.25)", ab.LUNA, P()),
    ("fable engine defaults (KA .9 / KB 1.25)", ab.FABLE, P()),
    ("luna 'strict interim' KA .8 / KB .45 (formulated after game 9)", ab.LUNA, P(ka_open=.8, kb_open=.45, ka_pinned=.75, kb_pinned=.45)),
    ("fable 'strict interim' KA .8 / KB .45", ab.FABLE, P(ka_open=.8, kb_open=.45, ka_pinned=.75, kb_pinned=.45)),
    ("luna charge .8, reject everything (b = 0)", ab.LUNA, P(ka_open=.8, kb_open=0.0, ka_pinned=.75, kb_pinned=0.0, b_zero_below=2.0)),
]
tot = {n: [0.0, 0.0] for n, *_ in CANDS}; act_tot = 0.0
print(f"{'':62s}" + "".join(f"{('game ' + str(g)):>22s}" for g in G) + f"{'sum':>22s}")
rows = []
for g in G:
    lines, sub = rec(g)
    act = er.actual_net(games[g], US); act_tot += act
    row = [("OFFICIAL net (exact, from the public rows)", act, act)]
    if sub:
        lo, hi, idn = er.game_value(lines, US, sub); row.append(("evaluator replay of our logged actual submission", lo, hi))
    for n, rd, par in CANDS:
        if (rd, f"case_{g:03d}") not in saved:
            continue
        lo, hi, _ = er.game_value(lines, US, policy(rd, g, par)); row.append((n, lo, hi)); tot[n][0] += lo; tot[n][1] += hi
    rows.append(row)
names = [r[0] for r in rows[0]] + [n for n, *_ in CANDS if all(any(x[0] == n for x in r) for r in rows) and n not in [r[0] for r in rows[0]]]
for nm in names:
    cells = []; slo = shi = 0.0
    for r in rows:
        x = next((x for x in r if x[0] == nm), None)
        if x:
            cells.append(f"[{x[1]:7.0f}, {x[2]:7.0f}]"); slo += x[1]; shi += x[2]
        else:
            cells.append("-")
    print(f"{nm:62s}" + "".join(f"{c:>22s}" for c in cells) + f"{f'[{slo:7.0f}, {shi:7.0f}]':>22s}")
print(f"\nout of sample verdict (sum over games {G}): our official net {act_tot:+.0f}; a candidate is surely better only if its LOWER bound exceeds that.")
for n, rd, par in CANDS:
    lo, hi = tot[n]
    if lo or hi:
        print(f"  {n:62s} lower bound {lo - act_tot:+9.0f}  upper bound {hi - act_tot:+9.0f}   {'SURELY BETTER' if lo > act_tot else ('surely worse' if hi < act_tot else 'unclear')}")
if "--lines" in sys.argv:
    g = G[-1]; lines, sub = rec(g)
    print(f"\nper-line, game {g}: our actual income / cost per line (exact) and the t bracket")
    for ln in sorted(lines):
        inc = sum(r["amount"] for r in games[g] if r["issuer"] == US and r["line_item_index"] == ln)
        cost = sum(r["amount"] for r in games[g] if r["reviewer"] == US and r["line_item_index"] == ln)
        L, U = lines[ln]["L"], lines[ln]["U"]
        print(f"  line {ln}: t in [{L:8.2f}, {'inf' if U == float('inf') else f'{U:.2f}'}) | actual income {inc:8.2f} cost {cost:8.2f} net {inc - cost:+9.2f}" + (f" | logged a {sub[ln][0]:.0f} b {sub[ln][1]:.0f}" if ln in sub else ""))
