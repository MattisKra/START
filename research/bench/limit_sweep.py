"""Cost side only (the part of the euro replay the audits say is measured): what would the acceptance limit b = k x median have cost?

    uv run --with pyzipper python research/bench/limit_sweep.py FIELD_DIR --us "Team Name"

b = k x median on lines with P(valid) >= 2/3, else 0 (the live rule with B_VALID_MULT = k). Our charge a is set to 0 so only reviewer cost remains;
the printed numbers are cost RANGES (lower, upper) in EUR from the patched, audited euro_replay.py, per source of medians:
  live  = the live ensemble's own logged medians and P(valid) (outputs/model_outputs.json, games 1-9)
  luna  = the cheap reader through claimbot_fable.engine (saved answers, games 1-14; games 11-14 are the freshest)
Only our own numbers are printed. Other teams' rows stay in memory (FIELD_DIR is outside the repo).
"""
import importlib.util, json, sys, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
def load(name, rel):
    sp = importlib.util.spec_from_file_location(name, ROOT / rel); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
er = load("er", "research/bench/euro_replay.py"); ab = load("ab", "research/bench/arch_bench.py")
from claimbot_fable.schema import ReaderCase
field_dir, US = sys.argv[1], sys.argv[sys.argv.index("--us") + 1]
games = er.load_field(field_dir)
logs = json.loads((ROOT / "outputs/model_outputs.json").read_text())["games"]
saved = ab.load_saved()
live = {int(g): {s["index"] + 1: (s["t_median"], s["q"], s["a"], s["b"]) for s in v["submitted"]} for g, v in logs.items()}
luna = {}
for g in games:
    r = saved.get((ab.LUNA, f"case_{g:03d}"))
    if r:
        luna[g] = {x.index + 1: (x.m, x.q, None, None) for x in ab.engine.compute(ReaderCase.model_validate(r["est"]), ab.P)}
actual_cost = {g: sum(r["amount"] for r in rows if r["reviewer"] == US) for g, rows in games.items()}
rec = {}
for g in games:
    sub = live.get(g, {})
    rec[g] = er.reconstruct(games[g], US, our_b={l: v[3] for l, v in sub.items()}, our_a={l: v[2] for l, v in sub.items()})
def cost_range(g, med, k):
    lo = hi = 0.0
    for ln in rec[g]:
        m, q = med[g][ln][0], med[g][ln][1]
        b = k * m if q >= 2 / 3 else 0.0
        l, h, *_ = er.line_value(rec[g][ln], US, 0.0, b)      # a = 0 -> revenue 0, net = -cost
        lo += -h; hi += -l
    return lo, hi
KS = (0.0, 0.3, 0.45, 0.6, 0.8, 1.0, 1.25, 1.5)
for name, med in (("LIVE medians (games 1-9)", live), ("LUNA reader medians (games 1-14)", luna)):
    G = sorted(g for g in med if g in games and all(ln in med[g] for ln in rec[g]))
    act = sum(actual_cost[g] for g in G)
    print(f"\n=== {name}: games {G[0]}-{G[-1]} ({len(G)} games); our ACTUAL reviewer cost over them: {act:,.0f}")
    print(f"{'k':>6s}{'cost range':>22s}{'saved vs actual (lo..hi)':>28s}   per game: cost range at this k")
    for k in KS:
        lo = hi = 0.0; per = []
        for g in G:
            l, h = cost_range(g, med, k); lo += l; hi += h; per.append((l, h))
        print(f"{k:>6.2f}{f'[{lo:,.0f}, {hi:,.0f}]':>22s}{f'{act - hi:+,.0f} .. {act - lo:+,.0f}':>28s}   " + " ".join(f"{(l + h) / 2:>6.0f}" for l, h in per))
    print(f"{'actual':>6s}{'':>22s}{'':>28s}   " + " ".join(f"{actual_cost[g]:>6.0f}" for g in G) + f"      (games {G})")
